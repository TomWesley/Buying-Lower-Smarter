from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String, primary_key=True)
    industry = Column(String)
    dividend_yield = Column(Float)
    volume = Column(Integer)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    hold_period_years = Column(Integer, nullable=False)  # 2 or 5
    run_type = Column(String, nullable=False)  # 'training' or 'analysis'
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0-100
    scoring_model_id = Column(Integer, ForeignKey("scoring_models.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    picks = relationship("StockPick", back_populates="run", cascade="all, delete-orphan")


class StockPick(Base):
    __tablename__ = "stock_picks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    loser_date = Column(Date, nullable=False)  # Day stock was identified as loser
    purchase_date = Column(Date)  # Day after loser_date when we buy at open
    purchase_price = Column(Float)  # Open price on purchase_date
    ticker = Column(String, nullable=False)
    daily_loss_pct = Column(Float, nullable=False)
    ranking = Column(Integer, nullable=False)  # 1-5 among losers that day
    industry = Column(String)
    dividend_yield = Column(Float)
    volume = Column(Integer)
    confidence_score = Column(Float)
    return_2y = Column(Float)
    return_5y = Column(Float)
    spy_return_2y = Column(Float)
    spy_return_5y = Column(Float)

    run = relationship("AnalysisRun", back_populates="picks")


class ScoringModel(Base):
    __tablename__ = "scoring_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    training_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=True)
    # Full formula JSON with structure:
    # {"factor_name": {"weight": 25.5, "condition": "HAS"/"NOT", "category": "dividend", ...}, ...}
    formula = Column(Text)
    # Legacy weights field for backwards compatibility
    weights = Column(Text)  # JSON string: {"industry": 15, "volume": 20, ...}
    threshold = Column(Float, default=65.0)
    avg_return = Column(Float)
    win_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class PriceCache(Base):
    """Cache for historical stock prices to avoid repeated API calls"""
    __tablename__ = "price_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)

    __table_args__ = (
        # Composite unique constraint
        {"sqlite_autoincrement": True},
    )
