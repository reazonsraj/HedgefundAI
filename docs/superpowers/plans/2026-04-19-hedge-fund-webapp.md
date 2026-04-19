# AI Hedge Fund Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone React + FastAPI web application for the AI Hedge Fund with streaming analysis results, portfolio management, and SQLite persistence.

**Architecture:** New `webapp/` directory with `frontend/` (React+Vite+Tailwind+shadcn) and `backend/` (FastAPI+SQLAlchemy+SQLite). Backend imports from existing `src/` for all hedge fund logic. SSE streaming delivers real-time agent results to the frontend.

**Tech Stack:** React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, FastAPI, SQLAlchemy, SQLite, SSE (EventSource)

---

### Task 1: Backend — Database Models and Session Setup

**Files:**
- Create: `webapp/backend/__init__.py`
- Create: `webapp/backend/database.py`
- Create: `webapp/backend/models.py`

- [ ] **Step 1: Create backend package and database setup**

Create `webapp/backend/__init__.py` (empty file).

Create `webapp/backend/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hedge_fund.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 2: Create SQLAlchemy models**

Create `webapp/backend/models.py`:
```python
from sqlalchemy import Column, Integer, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from webapp.backend.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, default="My Portfolio")
    tickers = Column(JSON, default=list)
    initial_cash = Column(Float, default=100000.0)
    margin_requirement = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    runs = relationship("AnalysisRun", back_populates="portfolio", cascade="all, delete-orphan")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    model_name = Column(Text)
    model_provider = Column(Text)
    selected_analysts = Column(JSON, default=list)
    tickers = Column(JSON, default=list)
    start_date = Column(Text)
    end_date = Column(Text)
    status = Column(Text, default="pending")
    decisions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    portfolio = relationship("Portfolio", back_populates="runs")
    results = relationship("AnalysisResult", back_populates="run", cascade="all, delete-orphan")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"))
    agent_name = Column(Text)
    ticker = Column(Text)
    signal = Column(Text)
    confidence = Column(Float)
    reasoning = Column(Text)
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("AnalysisRun", back_populates="results")
```

- [ ] **Step 3: Verify models load**

Run from project root:
```bash
cd /c/Users/USER/ai-hedge-fund && PYTHONIOENCODING=utf-8 poetry run python -c "
from webapp.backend.database import init_db, engine
from webapp.backend.models import Portfolio, AnalysisRun, AnalysisResult
init_db()
print('Tables created:', engine.table_names() if hasattr(engine, 'table_names') else list(Base.metadata.tables.keys()))
print('OK')
"
```
Expected: prints table names and "OK", creates `webapp/backend/hedge_fund.db`.

- [ ] **Step 4: Commit**

```bash
git add webapp/backend/
git commit -m "feat(webapp): add database models and session setup"
```

---

### Task 2: Backend — Asset Presets and Config Endpoints

**Files:**
- Create: `webapp/backend/assets.py`
- Create: `webapp/backend/routes_assets.py`
- Create: `webapp/backend/routes_config.py`

- [ ] **Step 1: Create asset presets data**

Create `webapp/backend/assets.py`:
```python
ASSET_PRESETS = {
    "stocks": [
        {"ticker": "AAPL", "name": "Apple Inc."},
        {"ticker": "MSFT", "name": "Microsoft"},
        {"ticker": "NVDA", "name": "NVIDIA"},
        {"ticker": "AMZN", "name": "Amazon"},
        {"ticker": "GOOGL", "name": "Alphabet"},
        {"ticker": "META", "name": "Meta Platforms"},
        {"ticker": "TSLA", "name": "Tesla"},
        {"ticker": "JPM", "name": "JPMorgan Chase"},
        {"ticker": "V", "name": "Visa"},
        {"ticker": "UNH", "name": "UnitedHealth"},
        {"ticker": "BRK.B", "name": "Berkshire Hathaway"},
        {"ticker": "JNJ", "name": "Johnson & Johnson"},
        {"ticker": "MA", "name": "Mastercard"},
        {"ticker": "PG", "name": "Procter & Gamble"},
        {"ticker": "HD", "name": "Home Depot"},
        {"ticker": "AVGO", "name": "Broadcom"},
        {"ticker": "COST", "name": "Costco"},
        {"ticker": "NFLX", "name": "Netflix"},
        {"ticker": "CRM", "name": "Salesforce"},
        {"ticker": "AMD", "name": "AMD"},
    ],
    "etfs": [
        {"ticker": "SPY", "name": "S&P 500 ETF"},
        {"ticker": "QQQ", "name": "NASDAQ-100 ETF"},
        {"ticker": "IWM", "name": "Russell 2000 ETF"},
        {"ticker": "DIA", "name": "Dow Jones ETF"},
        {"ticker": "VTI", "name": "Total Stock Market ETF"},
        {"ticker": "VOO", "name": "Vanguard S&P 500 ETF"},
        {"ticker": "ARKK", "name": "ARK Innovation ETF"},
        {"ticker": "XLF", "name": "Financial Select ETF"},
        {"ticker": "XLE", "name": "Energy Select ETF"},
        {"ticker": "XLK", "name": "Technology Select ETF"},
    ],
    "forex": [
        {"ticker": "EURUSD", "name": "EUR/USD"},
        {"ticker": "GBPUSD", "name": "GBP/USD"},
        {"ticker": "USDJPY", "name": "USD/JPY"},
        {"ticker": "USDCHF", "name": "USD/CHF"},
        {"ticker": "AUDUSD", "name": "AUD/USD"},
        {"ticker": "USDCAD", "name": "USD/CAD"},
        {"ticker": "NZDUSD", "name": "NZD/USD"},
        {"ticker": "EURGBP", "name": "EUR/GBP"},
        {"ticker": "EURJPY", "name": "EUR/JPY"},
        {"ticker": "GBPJPY", "name": "GBP/JPY"},
    ],
}


def search_assets(query: str) -> list[dict]:
    query = query.upper().strip()
    if not query:
        return []
    results = []
    for category, assets in ASSET_PRESETS.items():
        for asset in assets:
            if query in asset["ticker"] or query in asset["name"].upper():
                results.append({**asset, "category": category})
    return results
```

- [ ] **Step 2: Create asset routes**

Create `webapp/backend/routes_assets.py`:
```python
from fastapi import APIRouter, Query
from webapp.backend.assets import ASSET_PRESETS, search_assets

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/presets")
def get_presets():
    return ASSET_PRESETS


@router.get("/search")
def search(q: str = Query("")):
    return search_assets(q)
```

- [ ] **Step 3: Create config routes**

Create `webapp/backend/routes_config.py`:
```python
import json
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["config"])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
MODELS_PATH = os.path.join(PROJECT_ROOT, "src", "llm", "api_models.json")

API_KEY_PROVIDERS = [
    {"env_var": "OPENAI_API_KEY", "provider": "OpenAI"},
    {"env_var": "ANTHROPIC_API_KEY", "provider": "Anthropic"},
    {"env_var": "DEEPSEEK_API_KEY", "provider": "DeepSeek"},
    {"env_var": "GROQ_API_KEY", "provider": "Groq"},
    {"env_var": "GOOGLE_API_KEY", "provider": "Google"},
    {"env_var": "XAI_API_KEY", "provider": "xAI"},
    {"env_var": "OPENROUTER_API_KEY", "provider": "OpenRouter"},
    {"env_var": "GIGACHAT_API_KEY", "provider": "GigaChat"},
]


@router.get("/models")
def get_models():
    with open(MODELS_PATH, "r") as f:
        return json.load(f)


@router.get("/api-keys")
def get_api_keys():
    return [
        {"provider": p["provider"], "env_var": p["env_var"], "is_set": bool(os.environ.get(p["env_var"]))}
        for p in API_KEY_PROVIDERS
    ]


class ApiKeyUpdate(BaseModel):
    keys: dict[str, str]


@router.put("/api-keys")
def update_api_keys(body: ApiKeyUpdate):
    # Read existing .env
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

    # Update or add keys
    for env_var, value in body.keys.items():
        if not value:
            continue
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{env_var}="):
                lines[i] = f"{env_var}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{env_var}={value}\n")
        os.environ[env_var] = value

    with open(ENV_PATH, "w") as f:
        f.writelines(lines)

    return {"status": "ok"}
```

- [ ] **Step 4: Commit**

```bash
git add webapp/backend/assets.py webapp/backend/routes_assets.py webapp/backend/routes_config.py
git commit -m "feat(webapp): add asset presets and config endpoints"
```

---

### Task 3: Backend — Portfolio CRUD Endpoints

**Files:**
- Create: `webapp/backend/routes_portfolio.py`

- [ ] **Step 1: Create portfolio routes**

Create `webapp/backend/routes_portfolio.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from webapp.backend.database import get_db
from webapp.backend.models import Portfolio
from datetime import datetime, timezone

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


class PortfolioCreate(BaseModel):
    name: str = "My Portfolio"
    tickers: list[str] = []
    initial_cash: float = 100000.0
    margin_requirement: float = 0.0


class PortfolioUpdate(BaseModel):
    name: str | None = None
    tickers: list[str] | None = None
    initial_cash: float | None = None
    margin_requirement: float | None = None


def _portfolio_to_dict(p: Portfolio) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "tickers": p.tickers,
        "initial_cash": p.initial_cash,
        "margin_requirement": p.margin_requirement,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def list_portfolios(db: Session = Depends(get_db)):
    portfolios = db.query(Portfolio).order_by(Portfolio.updated_at.desc()).all()
    return [_portfolio_to_dict(p) for p in portfolios]


@router.post("")
def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)):
    portfolio = Portfolio(
        name=body.name,
        tickers=body.tickers,
        initial_cash=body.initial_cash,
        margin_requirement=body.margin_requirement,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return _portfolio_to_dict(portfolio)


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return _portfolio_to_dict(portfolio)


@router.put("/{portfolio_id}")
def update_portfolio(portfolio_id: int, body: PortfolioUpdate, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.name is not None:
        portfolio.name = body.name
    if body.tickers is not None:
        portfolio.tickers = body.tickers
    if body.initial_cash is not None:
        portfolio.initial_cash = body.initial_cash
    if body.margin_requirement is not None:
        portfolio.margin_requirement = body.margin_requirement
    portfolio.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(portfolio)
    return _portfolio_to_dict(portfolio)


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()
    return {"status": "deleted"}
```

- [ ] **Step 2: Commit**

```bash
git add webapp/backend/routes_portfolio.py
git commit -m "feat(webapp): add portfolio CRUD endpoints"
```

---

### Task 4: Backend — Analysis Run and SSE Streaming

**Files:**
- Create: `webapp/backend/routes_analysis.py`

- [ ] **Step 1: Create analysis routes with SSE streaming**

Create `webapp/backend/routes_analysis.py`:
```python
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

# Track active run globally (single concurrent run)
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
        "id": run.id,
        "portfolio_id": run.portfolio_id,
        "model_name": run.model_name,
        "model_provider": run.model_provider,
        "selected_analysts": run.selected_analysts,
        "tickers": run.tickers,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "status": run.status,
        "decisions": run.decisions,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _result_to_dict(r: AnalysisResult) -> dict:
    return {
        "id": r.id,
        "run_id": r.run_id,
        "agent_name": r.agent_name,
        "ticker": r.ticker,
        "signal": r.signal,
        "confidence": r.confidence,
        "reasoning": r.reasoning,
        "raw_data": r.raw_data,
    }


def _run_analysis_thread(run_id: int, tickers: list[str], portfolio_dict: dict,
                          start_date: str, end_date: str, selected_analysts: list[str],
                          model_name: str, model_provider: str, loop: asyncio.AbstractEventLoop):
    global _active_run_id
    db = SessionLocal()
    queue = _run_queues.get(run_id)

    def send_event(event_type: str, data: dict):
        if queue:
            asyncio.run_coroutine_threadsafe(
                queue.put({"event": event_type, "data": data}), loop
            )

    try:
        # Update status to running
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        run.status = "running"
        db.commit()
        send_event("run_status", {"status": "running"})

        # Import here to avoid circular imports at module level
        from src.main import run_hedge_fund
        from src.utils.progress import progress

        # Register handler to capture agent updates
        def on_agent_update(agent_name, ticker, status, analysis, timestamp):
            if status.lower() == "done" and analysis:
                try:
                    analysis_data = json.loads(analysis) if isinstance(analysis, str) else analysis
                except (json.JSONDecodeError, TypeError):
                    analysis_data = {}

                # Save each ticker result
                if isinstance(analysis_data, dict):
                    for tk, signal_data in analysis_data.items():
                        if isinstance(signal_data, dict) and "signal" in signal_data:
                            result = AnalysisResult(
                                run_id=run_id,
                                agent_name=agent_name,
                                ticker=tk,
                                signal=signal_data.get("signal", "neutral"),
                                confidence=signal_data.get("confidence", 0),
                                reasoning=str(signal_data.get("reasoning", "")),
                                raw_data=signal_data,
                            )
                            db.add(result)
                            db.commit()
                            send_event("agent_complete", {
                                "agent_name": agent_name,
                                "ticker": tk,
                                "signal": signal_data.get("signal", "neutral"),
                                "confidence": signal_data.get("confidence", 0),
                                "reasoning": str(signal_data.get("reasoning", "")),
                            })

            elif status.lower() != "done":
                send_event("agent_start", {
                    "agent_name": agent_name,
                    "ticker": ticker,
                    "status": status,
                })

        progress.register_handler(on_agent_update)

        try:
            result = run_hedge_fund(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                portfolio=portfolio_dict,
                show_reasoning=True,
                selected_analysts=selected_analysts,
                model_name=model_name,
                model_provider=model_provider,
            )
        finally:
            progress.unregister_handler(on_agent_update)

        # Save final decisions
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        run.decisions = result.get("decisions")
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        send_event("run_complete", {
            "decisions": result.get("decisions"),
            "analyst_signals": result.get("analyst_signals"),
        })

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
        portfolio_id=body.portfolio_id,
        model_name=body.model_name,
        model_provider=body.model_provider,
        selected_analysts=body.selected_analysts,
        tickers=tickers,
        start_date=body.start_date,
        end_date=body.end_date,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    _active_run_id = run.id
    _run_queues[run.id] = asyncio.Queue()

    portfolio_dict = {
        "cash": portfolio.initial_cash,
        "margin_requirement": portfolio.margin_requirement,
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
        # Run already finished — return existing results
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
    return {
        **_run_to_dict(run),
        "results": [_result_to_dict(r) for r in results],
    }
```

- [ ] **Step 2: Commit**

```bash
git add webapp/backend/routes_analysis.py
git commit -m "feat(webapp): add analysis run and SSE streaming endpoints"
```

---

### Task 5: Backend — FastAPI App Entry Point

**Files:**
- Create: `webapp/backend/main.py`

- [ ] **Step 1: Create the FastAPI app**

Create `webapp/backend/main.py`:
```python
import sys
import os

# Add project root to Python path so src/ imports work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from webapp.backend.database import init_db
from webapp.backend.routes_assets import router as assets_router
from webapp.backend.routes_config import router as config_router
from webapp.backend.routes_portfolio import router as portfolio_router
from webapp.backend.routes_analysis import router as analysis_router
from src.utils.analysts import ANALYST_CONFIG

app = FastAPI(title="AI Hedge Fund")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router)
app.include_router(config_router)
app.include_router(portfolio_router)
app.include_router(analysis_router)


@app.get("/api/analysts")
def get_analysts():
    return [
        {
            "key": key,
            "display_name": config["display_name"],
            "description": config["description"],
            "order": config["order"],
        }
        for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])
    ]


@app.on_event("startup")
def startup():
    init_db()
```

- [ ] **Step 2: Test the backend starts**

```bash
cd /c/Users/USER/ai-hedge-fund && PYTHONIOENCODING=utf-8 poetry run uvicorn webapp.backend.main:app --port 8000 --timeout-keep-alive 300
```
Expected: Server starts on port 8000. Visit `http://localhost:8000/api/assets/presets` in browser — should see JSON of preset tickers.

Press Ctrl+C to stop.

- [ ] **Step 3: Commit**

```bash
git add webapp/backend/main.py
git commit -m "feat(webapp): add FastAPI app entry point with all routes"
```

---

### Task 6: Frontend — Scaffold React + Vite + Tailwind + shadcn

**Files:**
- Create: `webapp/frontend/` (entire Vite project)

- [ ] **Step 1: Scaffold Vite React TypeScript project**

```bash
cd /c/Users/USER/ai-hedge-fund/webapp && npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd /c/Users/USER/ai-hedge-fund/webapp/frontend && npm install && npm install -D tailwindcss @tailwindcss/vite && npm install react-router-dom lucide-react clsx tailwind-merge
```

- [ ] **Step 3: Configure Tailwind**

Replace `webapp/frontend/src/index.css` with:
```css
@import "tailwindcss";
```

Update `webapp/frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Update `webapp/frontend/tsconfig.json` — add paths:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Verify it starts**

```bash
cd /c/Users/USER/ai-hedge-fund/webapp/frontend && npm run dev
```
Expected: Vite dev server at `http://localhost:5173`.

Press Ctrl+C to stop.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/USER/ai-hedge-fund && git add webapp/frontend/
git commit -m "feat(webapp): scaffold React + Vite + Tailwind frontend"
```

---

### Task 7: Frontend — Types, API Service, and Layout

**Files:**
- Create: `webapp/frontend/src/types/index.ts`
- Create: `webapp/frontend/src/services/api.ts`
- Create: `webapp/frontend/src/components/layout/TopNav.tsx`
- Create: `webapp/frontend/src/components/layout/Layout.tsx`
- Modify: `webapp/frontend/src/App.tsx`
- Modify: `webapp/frontend/src/main.tsx`

- [ ] **Step 1: Create TypeScript types**

Create `webapp/frontend/src/types/index.ts`:
```typescript
export interface Asset {
  ticker: string;
  name: string;
  category?: string;
}

export interface AssetPresets {
  stocks: Asset[];
  etfs: Asset[];
  forex: Asset[];
}

export interface Portfolio {
  id: number;
  name: string;
  tickers: string[];
  initial_cash: number;
  margin_requirement: number;
  created_at: string;
  updated_at: string;
}

export interface Analyst {
  key: string;
  display_name: string;
  description: string;
  order: number;
}

export interface ModelInfo {
  display_name: string;
  model_name: string;
  provider: string;
}

export interface AnalysisResult {
  id: number;
  run_id: number;
  agent_name: string;
  ticker: string;
  signal: "bullish" | "bearish" | "neutral";
  confidence: number;
  reasoning: string;
  raw_data: Record<string, unknown>;
}

export interface AnalysisRun {
  id: number;
  portfolio_id: number;
  model_name: string;
  model_provider: string;
  selected_analysts: string[];
  tickers: string[];
  start_date: string;
  end_date: string;
  status: "pending" | "running" | "completed" | "failed";
  decisions: Record<string, {
    action: string;
    quantity: number;
    confidence: number;
    reasoning: string;
  }> | null;
  created_at: string;
  completed_at: string | null;
  results?: AnalysisResult[];
}

export interface ApiKeyStatus {
  provider: string;
  env_var: string;
  is_set: boolean;
}
```

- [ ] **Step 2: Create API service**

Create `webapp/frontend/src/services/api.ts`:
```typescript
const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  assets: {
    presets: () => request<import("@/types").AssetPresets>("/assets/presets"),
    search: (q: string) => request<import("@/types").Asset[]>(`/assets/search?q=${q}`),
  },
  portfolios: {
    list: () => request<import("@/types").Portfolio[]>("/portfolios"),
    create: (data: { name: string; tickers: string[]; initial_cash: number; margin_requirement: number }) =>
      request<import("@/types").Portfolio>("/portfolios", { method: "POST", body: JSON.stringify(data) }),
    get: (id: number) => request<import("@/types").Portfolio>(`/portfolios/${id}`),
    update: (id: number, data: Partial<{ name: string; tickers: string[]; initial_cash: number; margin_requirement: number }>) =>
      request<import("@/types").Portfolio>(`/portfolios/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<{ status: string }>(`/portfolios/${id}`, { method: "DELETE" }),
  },
  analysis: {
    run: (data: { portfolio_id: number; model_name: string; model_provider: string; selected_analysts: string[]; start_date: string; end_date: string }) =>
      request<{ run_id: number }>("/analysis/run", { method: "POST", body: JSON.stringify(data) }),
    history: () => request<import("@/types").AnalysisRun[]>("/analysis/history"),
    get: (id: number) => request<import("@/types").AnalysisRun>(`/analysis/${id}`),
    streamUrl: (runId: number) => `${BASE}/analysis/stream/${runId}`,
  },
  config: {
    models: () => request<import("@/types").ModelInfo[]>("/config/models"),
    apiKeys: () => request<import("@/types").ApiKeyStatus[]>("/config/api-keys"),
    updateApiKeys: (keys: Record<string, string>) =>
      request<{ status: string }>("/config/api-keys", { method: "PUT", body: JSON.stringify({ keys }) }),
  },
  analysts: () => request<import("@/types").Analyst[]>("/analysts"),
};
```

- [ ] **Step 3: Create TopNav component**

Create `webapp/frontend/src/components/layout/TopNav.tsx`:
```tsx
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Search, Briefcase, History, Settings } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assets", label: "Assets", icon: Search },
  { to: "/portfolio", label: "Portfolio", icon: Briefcase },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function TopNav() {
  return (
    <nav className="border-b border-[#222] bg-[#111] px-6 h-14 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <span className="text-white font-bold text-lg tracking-tight">AI Hedge Fund</span>
        <div className="flex gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  isActive ? "bg-[#1a1a1a] text-white" : "text-[#666] hover:text-[#999]"
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Create Layout component**

Create `webapp/frontend/src/components/layout/Layout.tsx`:
```tsx
import { Outlet } from "react-router-dom";
import { TopNav } from "./TopNav";

export function Layout() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <TopNav />
      <main className="max-w-7xl mx-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 5: Set up App with router**

Replace `webapp/frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { DashboardPage } from "@/pages/DashboardPage";
import { AssetsPage } from "@/pages/AssetsPage";
import { PortfolioPage } from "@/pages/PortfolioPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/assets" element={<AssetsPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

Replace `webapp/frontend/src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 6: Create placeholder pages**

Create each page file with a minimal placeholder so the app compiles:

Create `webapp/frontend/src/pages/DashboardPage.tsx`:
```tsx
export function DashboardPage() {
  return <div><h1 className="text-2xl font-bold">Dashboard</h1></div>;
}
```

Create `webapp/frontend/src/pages/AssetsPage.tsx`:
```tsx
export function AssetsPage() {
  return <div><h1 className="text-2xl font-bold">Assets</h1></div>;
}
```

Create `webapp/frontend/src/pages/PortfolioPage.tsx`:
```tsx
export function PortfolioPage() {
  return <div><h1 className="text-2xl font-bold">Portfolio</h1></div>;
}
```

Create `webapp/frontend/src/pages/HistoryPage.tsx`:
```tsx
export function HistoryPage() {
  return <div><h1 className="text-2xl font-bold">History</h1></div>;
}
```

Create `webapp/frontend/src/pages/SettingsPage.tsx`:
```tsx
export function SettingsPage() {
  return <div><h1 className="text-2xl font-bold">Settings</h1></div>;
}
```

- [ ] **Step 7: Verify it compiles and nav works**

Start both backend and frontend:
```bash
# Terminal 1:
cd /c/Users/USER/ai-hedge-fund && poetry run uvicorn webapp.backend.main:app --port 8000

# Terminal 2:
cd /c/Users/USER/ai-hedge-fund/webapp/frontend && npm run dev
```

Open `http://localhost:5173`. Verify: dark background, top nav bar with 5 tabs, clicking tabs navigates.

- [ ] **Step 8: Commit**

```bash
cd /c/Users/USER/ai-hedge-fund && git add webapp/frontend/src/
git commit -m "feat(webapp): add types, API service, layout, and page routing"
```

---

### Task 8: Frontend — Assets Page

**Files:**
- Rewrite: `webapp/frontend/src/pages/AssetsPage.tsx`

- [ ] **Step 1: Build the Assets page with tabs, search, and add-to-portfolio**

Replace `webapp/frontend/src/pages/AssetsPage.tsx`:
```tsx
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { Asset, AssetPresets, Portfolio } from "@/types";
import { Search, Plus, Check } from "lucide-react";

const TABS = [
  { key: "stocks" as const, label: "Stocks" },
  { key: "etfs" as const, label: "ETFs / Indices" },
  { key: "forex" as const, label: "Forex" },
];

export function AssetsPage() {
  const [presets, setPresets] = useState<AssetPresets | null>(null);
  const [tab, setTab] = useState<"stocks" | "etfs" | "forex">("stocks");
  const [search, setSearch] = useState("");
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [customTicker, setCustomTicker] = useState("");

  useEffect(() => {
    api.assets.presets().then(setPresets);
    // Get or create default portfolio
    api.portfolios.list().then((ps) => {
      if (ps.length > 0) {
        setPortfolio(ps[0]);
      } else {
        api.portfolios.create({ name: "My Portfolio", tickers: [], initial_cash: 100000, margin_requirement: 0 }).then(setPortfolio);
      }
    });
  }, []);

  const assets = presets ? presets[tab] : [];
  const filtered = search
    ? assets.filter((a) => a.ticker.includes(search.toUpperCase()) || a.name.toUpperCase().includes(search.toUpperCase()))
    : assets;

  const inPortfolio = new Set(portfolio?.tickers || []);

  const toggleTicker = async (ticker: string) => {
    if (!portfolio) return;
    const newTickers = inPortfolio.has(ticker)
      ? portfolio.tickers.filter((t) => t !== ticker)
      : [...portfolio.tickers, ticker];
    const updated = await api.portfolios.update(portfolio.id, { tickers: newTickers });
    setPortfolio(updated);
  };

  const addCustom = async () => {
    const ticker = customTicker.trim().toUpperCase();
    if (!ticker || !portfolio || inPortfolio.has(ticker)) return;
    const updated = await api.portfolios.update(portfolio.id, { tickers: [...portfolio.tickers, ticker] });
    setPortfolio(updated);
    setCustomTicker("");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Assets</h1>
        <span className="text-sm text-[#666]">{portfolio?.tickers.length || 0} in portfolio</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-md text-sm transition-colors ${
              tab === key ? "bg-[#1a1a1a] text-white" : "text-[#666] hover:text-[#999]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Search + Custom Add */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#666]" size={16} />
          <input
            type="text"
            placeholder="Search tickers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#111] border border-[#222] rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-[#666] focus:outline-none focus:border-[#6366f1]"
          />
        </div>
        <div className="flex gap-1">
          <input
            type="text"
            placeholder="Custom ticker"
            value={customTicker}
            onChange={(e) => setCustomTicker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCustom()}
            className="bg-[#111] border border-[#222] rounded-lg px-3 py-2.5 text-sm text-white placeholder-[#666] focus:outline-none focus:border-[#6366f1] w-36"
          />
          <button onClick={addCustom} className="bg-[#6366f1] hover:bg-[#5558e6] text-white px-3 py-2 rounded-lg text-sm">
            Add
          </button>
        </div>
      </div>

      {/* Asset Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {filtered.map((asset) => {
          const added = inPortfolio.has(asset.ticker);
          return (
            <button
              key={asset.ticker}
              onClick={() => toggleTicker(asset.ticker)}
              className={`flex items-center justify-between p-3 rounded-lg border text-left transition-colors ${
                added
                  ? "bg-[#6366f1]/10 border-[#6366f1]/40"
                  : "bg-[#111] border-[#222] hover:border-[#333]"
              }`}
            >
              <div>
                <div className="text-white text-sm font-medium">{asset.ticker}</div>
                <div className="text-[#666] text-xs truncate max-w-[120px]">{asset.name}</div>
              </div>
              {added ? (
                <Check size={16} className="text-[#6366f1] shrink-0" />
              ) : (
                <Plus size={16} className="text-[#666] shrink-0" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

With both servers running, navigate to `http://localhost:5173/assets`. Verify: tabs switch between Stocks/ETFs/Forex, search filters, clicking a ticker adds it (shows checkmark), clicking again removes it.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/USER/ai-hedge-fund && git add webapp/frontend/src/pages/AssetsPage.tsx
git commit -m "feat(webapp): build Assets page with tabs, search, and portfolio add"
```

---

### Task 9: Frontend — Portfolio Page with Run Config

**Files:**
- Rewrite: `webapp/frontend/src/pages/PortfolioPage.tsx`
- Create: `webapp/frontend/src/hooks/useAnalysisStream.ts`

- [ ] **Step 1: Create SSE streaming hook**

Create `webapp/frontend/src/hooks/useAnalysisStream.ts`:
```typescript
import { useState, useCallback, useRef } from "react";
import { api } from "@/services/api";

export interface AgentEvent {
  agent_name: string;
  ticker?: string;
  signal?: string;
  confidence?: number;
  reasoning?: string;
  status?: string;
}

export interface StreamState {
  isRunning: boolean;
  events: AgentEvent[];
  decisions: Record<string, { action: string; quantity: number; confidence: number; reasoning: string }> | null;
  error: string | null;
  runId: number | null;
}

export function useAnalysisStream() {
  const [state, setState] = useState<StreamState>({
    isRunning: false,
    events: [],
    decisions: null,
    error: null,
    runId: null,
  });
  const esRef = useRef<EventSource | null>(null);

  const startRun = useCallback(async (config: {
    portfolio_id: number;
    model_name: string;
    model_provider: string;
    selected_analysts: string[];
    start_date: string;
    end_date: string;
  }) => {
    setState({ isRunning: true, events: [], decisions: null, error: null, runId: null });

    try {
      const { run_id } = await api.analysis.run(config);
      setState((s) => ({ ...s, runId: run_id }));

      const es = new EventSource(api.analysis.streamUrl(run_id));
      esRef.current = es;

      es.addEventListener("agent_start", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({ ...s, events: [...s.events, data] }));
      });

      es.addEventListener("agent_complete", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({
          ...s,
          events: [...s.events.filter((ev) => !(ev.agent_name === data.agent_name && !ev.signal)), data],
        }));
      });

      es.addEventListener("run_complete", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({ ...s, isRunning: false, decisions: data.decisions }));
        es.close();
      });

      es.addEventListener("run_error", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({ ...s, isRunning: false, error: data.error }));
        es.close();
      });

      es.onerror = () => {
        setState((s) => ({ ...s, isRunning: false, error: "Connection lost" }));
        es.close();
      };
    } catch (err: unknown) {
      setState((s) => ({ ...s, isRunning: false, error: err instanceof Error ? err.message : "Failed to start" }));
    }
  }, []);

  const cancel = useCallback(() => {
    esRef.current?.close();
    setState((s) => ({ ...s, isRunning: false }));
  }, []);

  return { ...state, startRun, cancel };
}
```

- [ ] **Step 2: Build the Portfolio page**

Replace `webapp/frontend/src/pages/PortfolioPage.tsx`:
```tsx
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { Portfolio, Analyst, ModelInfo } from "@/types";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { X, Play, Loader2 } from "lucide-react";

const SIGNAL_COLORS: Record<string, string> = {
  bullish: "text-[#22c55e]",
  bearish: "text-[#ef4444]",
  neutral: "text-[#eab308]",
};

const ACTION_COLORS: Record<string, string> = {
  buy: "text-[#22c55e]",
  short: "text-[#ef4444]",
  hold: "text-[#eab308]",
  cover: "text-[#22c55e]",
  sell: "text-[#ef4444]",
};

export function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [analysts, setAnalysts] = useState<Analyst[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedAnalysts, setSelectedAnalysts] = useState<string[]>([]);
  const [modelName, setModelName] = useState("claude-sonnet-4-6");
  const [modelProvider, setModelProvider] = useState("Anthropic");
  const [initialCash, setInitialCash] = useState(100000);
  const [marginReq, setMarginReq] = useState(0);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 3);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const stream = useAnalysisStream();

  useEffect(() => {
    api.portfolios.list().then((ps) => {
      if (ps.length > 0) setPortfolio(ps[0]);
    });
    api.analysts().then((a) => {
      setAnalysts(a);
      setSelectedAnalysts(a.map((x) => x.key));
    });
    api.config.models().then(setModels);
  }, []);

  const removeTicker = async (ticker: string) => {
    if (!portfolio) return;
    const updated = await api.portfolios.update(portfolio.id, {
      tickers: portfolio.tickers.filter((t) => t !== ticker),
    });
    setPortfolio(updated);
  };

  const handleRun = () => {
    if (!portfolio || portfolio.tickers.length === 0) return;
    stream.startRun({
      portfolio_id: portfolio.id,
      model_name: modelName,
      model_provider: modelProvider,
      selected_analysts: selectedAnalysts,
      start_date: startDate,
      end_date: endDate,
    });
  };

  const toggleAllAnalysts = () => {
    if (selectedAnalysts.length === analysts.length) {
      setSelectedAnalysts([]);
    } else {
      setSelectedAnalysts(analysts.map((a) => a.key));
    }
  };

  const handleModelChange = (modelNameValue: string) => {
    setModelName(modelNameValue);
    const model = models.find((m) => m.model_name === modelNameValue);
    if (model) setModelProvider(model.provider);
  };

  // Group models by provider
  const modelsByProvider: Record<string, ModelInfo[]> = {};
  models.forEach((m) => {
    if (!modelsByProvider[m.provider]) modelsByProvider[m.provider] = [];
    modelsByProvider[m.provider].push(m);
  });

  // Completed agent signals (deduplicated by agent_name)
  const completedAgents = stream.events.filter((e) => e.signal);
  const agentNames = [...new Set(completedAgents.map((e) => e.agent_name))];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        {stream.isRunning && (
          <div className="flex items-center gap-2 text-sm text-[#6366f1]">
            <Loader2 size={16} className="animate-spin" /> Analysis running...
          </div>
        )}
      </div>

      {!stream.isRunning && !stream.decisions && (
        <>
          {/* Tickers */}
          <div className="bg-[#111] border border-[#222] rounded-lg p-4 mb-4">
            <h2 className="text-sm font-medium text-[#999] mb-3">Selected Tickers</h2>
            {portfolio && portfolio.tickers.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {portfolio.tickers.map((t) => (
                  <span key={t} className="flex items-center gap-1 bg-[#1a1a1a] px-3 py-1.5 rounded-md text-sm">
                    {t}
                    <button onClick={() => removeTicker(t)} className="text-[#666] hover:text-[#ef4444]">
                      <X size={14} />
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[#666]">No tickers selected. Go to Assets to add some.</p>
            )}
          </div>

          {/* Config */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">Initial Cash</label>
              <input type="number" value={initialCash} onChange={(e) => setInitialCash(Number(e.target.value))}
                className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">Margin Requirement (%)</label>
              <input type="number" value={marginReq} onChange={(e) => setMarginReq(Number(e.target.value))}
                className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
          </div>

          {/* Model Selector */}
          <div className="bg-[#111] border border-[#222] rounded-lg p-4 mb-4">
            <label className="block text-xs text-[#666] mb-1">Model</label>
            <select value={modelName} onChange={(e) => handleModelChange(e.target.value)}
              className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]">
              {Object.entries(modelsByProvider).map(([provider, providerModels]) => (
                <optgroup key={provider} label={provider}>
                  {providerModels.map((m) => (
                    <option key={m.model_name} value={m.model_name}>{m.display_name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Analyst Selector */}
          <div className="bg-[#111] border border-[#222] rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs text-[#666]">Analysts</label>
              <button onClick={toggleAllAnalysts} className="text-xs text-[#6366f1] hover:underline">
                {selectedAnalysts.length === analysts.length ? "Deselect All" : "Select All"}
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {analysts.map((a) => {
                const selected = selectedAnalysts.includes(a.key);
                return (
                  <button key={a.key}
                    onClick={() => setSelectedAnalysts(selected ? selectedAnalysts.filter((k) => k !== a.key) : [...selectedAnalysts, a.key])}
                    className={`text-left p-2 rounded-md border text-xs transition-colors ${
                      selected ? "border-[#6366f1]/40 bg-[#6366f1]/10 text-white" : "border-[#222] text-[#666] hover:text-[#999]"
                    }`}>
                    <div className="font-medium">{a.display_name}</div>
                    <div className="text-[#666] truncate">{a.description}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Run Button */}
          <button onClick={handleRun}
            disabled={!portfolio || portfolio.tickers.length === 0 || selectedAnalysts.length === 0}
            className="w-full bg-[#6366f1] hover:bg-[#5558e6] disabled:opacity-40 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium flex items-center justify-center gap-2">
            <Play size={18} /> Run Analysis
          </button>
        </>
      )}

      {/* Streaming Results */}
      {(stream.isRunning || stream.decisions) && (
        <div>
          {/* Progress */}
          {stream.isRunning && (
            <div className="w-full bg-[#222] rounded-full h-2 mb-6">
              <div className="bg-[#6366f1] h-2 rounded-full transition-all" style={{ width: `${Math.min((agentNames.length / Math.max(selectedAnalysts.length + 2, 1)) * 100, 100)}%` }} />
            </div>
          )}

          {/* Agent Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
            {agentNames.map((agentName) => {
              const agentEvents = completedAgents.filter((e) => e.agent_name === agentName);
              const displayName = agentName.replace(/_agent$/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              const isExpanded = expandedAgent === agentName;
              return (
                <button key={agentName} onClick={() => setExpandedAgent(isExpanded ? null : agentName)}
                  className="bg-[#111] border border-[#222] rounded-lg p-4 text-left hover:border-[#333] transition-colors">
                  <div className="font-medium text-sm mb-2">{displayName}</div>
                  <div className="space-y-1">
                    {agentEvents.map((ev, i) => (
                      <div key={i} className="flex justify-between text-xs">
                        <span className="text-[#999]">{ev.ticker}</span>
                        <span className={SIGNAL_COLORS[ev.signal || "neutral"]}>
                          {ev.signal?.toUpperCase()} {ev.confidence ? `${Math.round(ev.confidence)}%` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                  {isExpanded && agentEvents[0]?.reasoning && (
                    <p className="mt-3 text-xs text-[#666] border-t border-[#222] pt-3 max-h-40 overflow-y-auto">
                      {agentEvents[0].reasoning.slice(0, 500)}{agentEvents[0].reasoning.length > 500 ? "..." : ""}
                    </p>
                  )}
                </button>
              );
            })}
          </div>

          {/* Final Decisions */}
          {stream.decisions && (
            <div className="bg-[#111] border border-[#6366f1]/30 rounded-lg p-4">
              <h2 className="text-sm font-medium text-white mb-3">Portfolio Decisions</h2>
              <div className="space-y-2">
                {Object.entries(stream.decisions).map(([ticker, d]) => (
                  <div key={ticker} className="flex items-center justify-between py-2 border-b border-[#1a1a1a] last:border-0">
                    <span className="text-white font-medium text-sm">{ticker}</span>
                    <div className="flex items-center gap-4">
                      <span className={`font-medium text-sm ${ACTION_COLORS[d.action.toLowerCase()] || "text-white"}`}>
                        {d.action.toUpperCase()} {d.quantity}
                      </span>
                      <span className="text-xs text-[#666]">{d.confidence}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {stream.error && (
            <div className="bg-[#ef4444]/10 border border-[#ef4444]/30 rounded-lg p-4 text-[#ef4444] text-sm">
              Error: {stream.error}
            </div>
          )}

          {/* New Run button */}
          {!stream.isRunning && (
            <button onClick={() => { stream.cancel(); }} className="mt-4 text-sm text-[#6366f1] hover:underline">
              Start New Analysis
            </button>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /c/Users/USER/ai-hedge-fund && git add webapp/frontend/src/pages/PortfolioPage.tsx webapp/frontend/src/hooks/useAnalysisStream.ts
git commit -m "feat(webapp): build Portfolio page with run config and streaming results"
```

---

### Task 10: Frontend — Dashboard, History, and Settings Pages

**Files:**
- Rewrite: `webapp/frontend/src/pages/DashboardPage.tsx`
- Rewrite: `webapp/frontend/src/pages/HistoryPage.tsx`
- Rewrite: `webapp/frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Build Dashboard page**

Replace `webapp/frontend/src/pages/DashboardPage.tsx`:
```tsx
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { AnalysisRun, Portfolio } from "@/types";
import { useNavigate } from "react-router-dom";

const ACTION_COLORS: Record<string, string> = {
  buy: "text-[#22c55e]", short: "text-[#ef4444]", hold: "text-[#eab308]",
  cover: "text-[#22c55e]", sell: "text-[#ef4444]",
};

export function DashboardPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [lastRun, setLastRun] = useState<AnalysisRun | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.portfolios.list().then((ps) => ps.length > 0 && setPortfolio(ps[0]));
    api.analysis.history().then((runs) => {
      if (runs.length > 0) {
        api.analysis.get(runs[0].id).then(setLastRun);
      }
    });
  }, []);

  const decisions = lastRun?.decisions || {};
  const decisionList = Object.entries(decisions);
  const buys = decisionList.filter(([, d]) => d.action.toLowerCase() === "buy").length;
  const shorts = decisionList.filter(([, d]) => d.action.toLowerCase() === "short").length;
  const holds = decisionList.filter(([, d]) => d.action.toLowerCase() === "hold").length;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">PORTFOLIO VALUE</div>
          <div className="text-xl font-semibold">${(portfolio?.initial_cash || 100000).toLocaleString()}</div>
        </div>
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">POSITIONS</div>
          <div className="text-xl font-semibold">{portfolio?.tickers.length || 0}</div>
        </div>
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">LAST RUN</div>
          <div className="text-xl font-semibold">
            {lastRun ? new Date(lastRun.created_at).toLocaleDateString() : "None"}
          </div>
        </div>
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">SIGNALS</div>
          <div className="text-xl font-semibold">
            {lastRun ? (
              <span>
                <span className="text-[#22c55e]">{buys} Buy</span>
                {" / "}
                <span className="text-[#ef4444]">{shorts} Short</span>
                {holds > 0 && <span className="text-[#eab308]"> / {holds} Hold</span>}
              </span>
            ) : "—"}
          </div>
        </div>
      </div>

      {/* Recent Run */}
      {lastRun && decisionList.length > 0 ? (
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[#999]">Latest Analysis — {lastRun.model_provider} / {lastRun.model_name}</h2>
            <span className="text-xs text-[#666]">{new Date(lastRun.created_at).toLocaleString()}</span>
          </div>
          <div className="space-y-2">
            {decisionList.map(([ticker, d]) => (
              <div key={ticker} className="flex items-center justify-between py-2 border-b border-[#1a1a1a] last:border-0">
                <span className="text-white font-medium">{ticker}</span>
                <div className="flex items-center gap-4">
                  <span className={`font-medium ${ACTION_COLORS[d.action.toLowerCase()] || "text-white"}`}>
                    {d.action.toUpperCase()} {d.quantity}
                  </span>
                  <span className="text-xs text-[#666]">{d.confidence}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-[#111] border border-[#222] rounded-lg p-8 text-center">
          <p className="text-[#666] mb-4">No analysis runs yet.</p>
          <button onClick={() => navigate("/portfolio")} className="bg-[#6366f1] hover:bg-[#5558e6] text-white px-6 py-2 rounded-lg text-sm">
            Run Your First Analysis
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build History page**

Replace `webapp/frontend/src/pages/HistoryPage.tsx`:
```tsx
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { AnalysisRun } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  completed: "text-[#22c55e]", failed: "text-[#ef4444]", running: "text-[#eab308]", pending: "text-[#666]",
};
const ACTION_COLORS: Record<string, string> = {
  buy: "text-[#22c55e]", short: "text-[#ef4444]", hold: "text-[#eab308]",
  cover: "text-[#22c55e]", sell: "text-[#ef4444]",
};

export function HistoryPage() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [detail, setDetail] = useState<AnalysisRun | null>(null);

  useEffect(() => {
    api.analysis.history().then(setRuns);
  }, []);

  const expand = async (id: number) => {
    if (expanded === id) { setExpanded(null); setDetail(null); return; }
    setExpanded(id);
    const run = await api.analysis.get(id);
    setDetail(run);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">History</h1>
      {runs.length === 0 ? (
        <p className="text-[#666]">No analysis runs yet.</p>
      ) : (
        <div className="space-y-2">
          {runs.map((run) => {
            const decisions = run.decisions || {};
            const decisionList = Object.entries(decisions);
            const summary = decisionList.map(([, d]) => d.action.toLowerCase());
            const buys = summary.filter((a) => a === "buy").length;
            const shorts = summary.filter((a) => a === "short").length;
            const holds = summary.filter((a) => a === "hold").length;

            return (
              <div key={run.id}>
                <button onClick={() => expand(run.id)}
                  className="w-full bg-[#111] border border-[#222] rounded-lg p-4 text-left hover:border-[#333] transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-white">{new Date(run.created_at).toLocaleString()}</span>
                      <span className="text-xs text-[#666]">{run.tickers.join(", ")}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs text-[#666]">{run.model_provider}/{run.model_name}</span>
                      {run.status === "completed" && (
                        <span className="text-xs">
                          <span className="text-[#22c55e]">{buys}B</span> / <span className="text-[#ef4444]">{shorts}S</span> / <span className="text-[#eab308]">{holds}H</span>
                        </span>
                      )}
                      <span className={`text-xs ${STATUS_COLORS[run.status]}`}>{run.status}</span>
                    </div>
                  </div>
                </button>

                {expanded === run.id && detail && (
                  <div className="bg-[#0a0a0a] border border-[#222] border-t-0 rounded-b-lg p-4 space-y-4">
                    {/* Decisions */}
                    {detail.decisions && (
                      <div>
                        <h3 className="text-xs text-[#666] mb-2">DECISIONS</h3>
                        {Object.entries(detail.decisions).map(([ticker, d]) => (
                          <div key={ticker} className="flex justify-between py-1 text-sm">
                            <span>{ticker}</span>
                            <span className={ACTION_COLORS[d.action.toLowerCase()] || "text-white"}>
                              {d.action.toUpperCase()} {d.quantity} ({d.confidence}%)
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    {/* Agent Results */}
                    {detail.results && detail.results.length > 0 && (
                      <div>
                        <h3 className="text-xs text-[#666] mb-2">AGENT SIGNALS</h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {detail.results.map((r) => (
                            <div key={r.id} className="bg-[#111] border border-[#222] rounded p-2 text-xs">
                              <div className="flex justify-between">
                                <span className="text-[#999]">{r.agent_name.replace(/_agent$/, "").replace(/_/g, " ")}</span>
                                <span className={`${r.signal === "bullish" ? "text-[#22c55e]" : r.signal === "bearish" ? "text-[#ef4444]" : "text-[#eab308]"}`}>
                                  {r.ticker}: {r.signal}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build Settings page**

Replace `webapp/frontend/src/pages/SettingsPage.tsx`:
```tsx
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { ApiKeyStatus } from "@/types";
import { Eye, EyeOff, Save } from "lucide-react";

export function SettingsPage() {
  const [keys, setKeys] = useState<ApiKeyStatus[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.config.apiKeys().then(setKeys);
  }, []);

  const handleSave = async () => {
    const nonEmpty = Object.fromEntries(Object.entries(values).filter(([, v]) => v));
    if (Object.keys(nonEmpty).length === 0) return;
    await api.config.updateApiKeys(nonEmpty);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    api.config.apiKeys().then(setKeys);
    setValues({});
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="bg-[#111] border border-[#222] rounded-lg p-4">
        <h2 className="text-sm font-medium text-[#999] mb-4">API Keys</h2>
        <div className="space-y-3">
          {keys.map((k) => (
            <div key={k.env_var} className="flex items-center gap-3">
              <div className="w-32">
                <span className="text-sm">{k.provider}</span>
                {k.is_set && <span className="ml-2 text-xs text-[#22c55e]">Set</span>}
              </div>
              <div className="flex-1 relative">
                <input
                  type={visible[k.env_var] ? "text" : "password"}
                  placeholder={k.is_set ? "********" : "Enter API key"}
                  value={values[k.env_var] || ""}
                  onChange={(e) => setValues({ ...values, [k.env_var]: e.target.value })}
                  className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white placeholder-[#666] focus:outline-none focus:border-[#6366f1]"
                />
                <button onClick={() => setVisible({ ...visible, [k.env_var]: !visible[k.env_var] })}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[#666]">
                  {visible[k.env_var] ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={handleSave} className="bg-[#6366f1] hover:bg-[#5558e6] text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2">
            <Save size={14} /> Save Keys
          </button>
          {saved && <span className="text-sm text-[#22c55e]">Saved!</span>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify all pages in browser**

With both servers running, test all 5 pages:
- Dashboard: shows summary cards, empty state or last run
- Assets: tabs, search, add/remove tickers
- Portfolio: shows selected tickers, config, run button
- History: lists past runs, expandable
- Settings: API key inputs with show/hide

- [ ] **Step 5: Commit**

```bash
cd /c/Users/USER/ai-hedge-fund && git add webapp/frontend/src/pages/
git commit -m "feat(webapp): build Dashboard, History, and Settings pages"
```

---

### Task 11: Final Integration Test

**Files:** No new files. End-to-end verification.

- [ ] **Step 1: Start both servers**

Terminal 1 — Backend:
```bash
cd /c/Users/USER/ai-hedge-fund && PYTHONIOENCODING=utf-8 poetry run uvicorn webapp.backend.main:app --port 8000 --timeout-keep-alive 300
```

Terminal 2 — Frontend:
```bash
cd /c/Users/USER/ai-hedge-fund/webapp/frontend && npm run dev
```

- [ ] **Step 2: Test full flow**

1. Open `http://localhost:5173`
2. Settings: verify Anthropic key shows as "Set"
3. Assets: add AAPL, SPY, EURUSD to portfolio
4. Portfolio: verify tickers appear, select Claude Sonnet 4.6, select all analysts
5. Click "Run Analysis" — verify streaming agent cards appear
6. Wait for completion — verify final decisions table
7. Dashboard: verify last run shows
8. History: verify run appears, click to expand

- [ ] **Step 3: Commit final state**

```bash
cd /c/Users/USER/ai-hedge-fund && git add -A && git status
git commit -m "feat(webapp): complete web application with all pages and streaming"
```
