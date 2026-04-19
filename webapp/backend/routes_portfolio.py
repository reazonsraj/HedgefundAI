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
    portfolio = Portfolio(name=body.name, tickers=body.tickers, initial_cash=body.initial_cash, margin_requirement=body.margin_requirement)
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
