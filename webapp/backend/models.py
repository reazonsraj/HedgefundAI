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
