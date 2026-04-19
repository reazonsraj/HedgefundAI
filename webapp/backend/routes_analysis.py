import asyncio
import json
import threading
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from webapp.backend.database import get_db, SessionLocal
from webapp.backend.models import AnalysisRun, AnalysisResult, Portfolio

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

_active_run_id: int | None = None
_run_queues: dict[int, asyncio.Queue] = {}


class RunRequest(BaseModel):
    portfolio_id: int
    model_name: str
    model_provider: str
    selected_analysts: list[str]
    start_date: str
    end_date: str


def _run_to_dict(run: AnalysisRun) -> dict:
    return {
        "id": run.id, "portfolio_id": run.portfolio_id,
        "model_name": run.model_name, "model_provider": run.model_provider,
        "selected_analysts": run.selected_analysts, "tickers": run.tickers,
        "start_date": run.start_date, "end_date": run.end_date,
        "status": run.status, "decisions": run.decisions,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _result_to_dict(r: AnalysisResult) -> dict:
    return {
        "id": r.id, "run_id": r.run_id, "agent_name": r.agent_name,
        "ticker": r.ticker, "signal": r.signal, "confidence": r.confidence,
        "reasoning": r.reasoning, "raw_data": r.raw_data,
    }


def _run_analysis_thread(run_id: int, tickers: list[str], portfolio_dict: dict,
                          start_date: str, end_date: str, selected_analysts: list[str],
                          model_name: str, model_provider: str, loop: asyncio.AbstractEventLoop):
    global _active_run_id
    db = SessionLocal()
    queue = _run_queues.get(run_id)

    def send_event(event_type: str, data: dict):
        if queue:
            asyncio.run_coroutine_threadsafe(queue.put({"event": event_type, "data": data}), loop)

    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        run.status = "running"
        db.commit()
        send_event("run_status", {"status": "running"})

        from src.main import run_hedge_fund
        from src.utils.progress import progress

        def on_agent_update(agent_name, ticker, status, analysis, timestamp):
            if status.lower() == "done" and analysis:
                try:
                    analysis_data = json.loads(analysis) if isinstance(analysis, str) else analysis
                except (json.JSONDecodeError, TypeError):
                    analysis_data = {}

                if isinstance(analysis_data, dict):
                    for tk, signal_data in analysis_data.items():
                        if isinstance(signal_data, dict) and "signal" in signal_data:
                            result = AnalysisResult(
                                run_id=run_id, agent_name=agent_name, ticker=tk,
                                signal=signal_data.get("signal", "neutral"),
                                confidence=signal_data.get("confidence", 0),
                                reasoning=str(signal_data.get("reasoning", "")),
                                raw_data=signal_data,
                            )
                            db.add(result)
                            db.commit()
                            send_event("agent_complete", {
                                "agent_name": agent_name, "ticker": tk,
                                "signal": signal_data.get("signal", "neutral"),
                                "confidence": signal_data.get("confidence", 0),
                                "reasoning": str(signal_data.get("reasoning", "")),
                            })
            elif status.lower() != "done":
                send_event("agent_start", {"agent_name": agent_name, "ticker": ticker, "status": status})

        progress.register_handler(on_agent_update)
        try:
            result = run_hedge_fund(
                tickers=tickers, start_date=start_date, end_date=end_date,
                portfolio=portfolio_dict, show_reasoning=True,
                selected_analysts=selected_analysts, model_name=model_name, model_provider=model_provider,
            )
        finally:
            progress.unregister_handler(on_agent_update)

        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        run.decisions = result.get("decisions")
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        send_event("run_complete", {"decisions": result.get("decisions"), "analyst_signals": result.get("analyst_signals")})

    except Exception as e:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        send_event("run_error", {"error": str(e)})
    finally:
        _active_run_id = None
        if queue:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)
        db.close()


@router.post("/run")
def start_run(body: RunRequest, db: Session = Depends(get_db)):
    global _active_run_id
    if _active_run_id is not None:
        raise HTTPException(status_code=409, detail="An analysis is already running")

    portfolio = db.query(Portfolio).filter(Portfolio.id == body.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    tickers = portfolio.tickers
    if not tickers:
        raise HTTPException(status_code=400, detail="Portfolio has no tickers")

    run = AnalysisRun(
        portfolio_id=body.portfolio_id, model_name=body.model_name, model_provider=body.model_provider,
        selected_analysts=body.selected_analysts, tickers=tickers, start_date=body.start_date, end_date=body.end_date, status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    _active_run_id = run.id
    _run_queues[run.id] = asyncio.Queue()

    portfolio_dict = {
        "cash": portfolio.initial_cash, "margin_requirement": portfolio.margin_requirement,
        "margin_used": 0.0,
        "positions": {t: {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0, "short_margin_used": 0.0} for t in tickers},
        "realized_gains": {t: {"long": 0.0, "short": 0.0} for t in tickers},
    }

    loop = asyncio.get_event_loop()
    thread = threading.Thread(
        target=_run_analysis_thread,
        args=(run.id, tickers, portfolio_dict, body.start_date, body.end_date,
              body.selected_analysts, body.model_name, body.model_provider, loop),
        daemon=True,
    )
    thread.start()
    return {"run_id": run.id}


@router.get("/stream/{run_id}")
async def stream_run(run_id: int):
    queue = _run_queues.get(run_id)
    if queue is None:
        db = SessionLocal()
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        db.close()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        async def finished_stream():
            db2 = SessionLocal()
            results = db2.query(AnalysisResult).filter(AnalysisResult.run_id == run_id).all()
            for r in results:
                yield f"event: agent_complete\ndata: {json.dumps(_result_to_dict(r))}\n\n"
            run2 = db2.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run2.status == "completed":
                yield f"event: run_complete\ndata: {json.dumps({'decisions': run2.decisions})}\n\n"
            elif run2.status == "failed":
                yield f"event: run_error\ndata: {json.dumps({'error': 'Run failed'})}\n\n"
            db2.close()

        return StreamingResponse(finished_stream(), media_type="text/event-stream")

    async def event_stream():
        try:
            while True:
                msg = await queue.get()
                if msg is None:
                    break
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
        finally:
            _run_queues.pop(run_id, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    runs = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(50).all()
    return [_run_to_dict(r) for r in runs]


@router.get("/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    results = db.query(AnalysisResult).filter(AnalysisResult.run_id == run_id).all()
    return {**_run_to_dict(run), "results": [_result_to_dict(r) for r in results]}
