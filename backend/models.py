from sqlalchemy import Column, Integer, String, Float, Date, DateTime,ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class StockHistory(Base):
    __tablename__ = "stock_history"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    date = Column(Date)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    created_at = Column(Date)
    target_date = Column(Date)
    predicted_signal = Column(String)
    predicted_price = Column(Float)
    confidence = Column(Float, nullable=True)
    indicators = Column(String, nullable=True)
    actual_close = Column(Float, nullable=True)
    is_correct = Column(String, nullable=True)
    error_pct = Column(Float, nullable=True)

class MarketData(Base):
    __tablename__ = "market_data"
    
    ticker = Column(String, primary_key=True, index=True)
    category = Column(String)
    price = Column(Float)
    change_pct = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Ex: "Carteira Pai"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento com os ativos
    assets = relationship("PortfolioAsset", back_populates="portfolio", cascade="all, delete-orphan")

class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    ticker = Column(String) # Ex: PETR4
    avg_price = Column(Float) # Preço Médio que o usuário pagou
    quantity = Column(Integer, default=1) # Opcional, deixamos 1 por padrão
    
    portfolio = relationship("Portfolio", back_populates="assets")