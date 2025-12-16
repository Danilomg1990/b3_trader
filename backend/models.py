from sqlalchemy import Column, Integer, String, Float, Date
from .database import Base

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
    created_at = Column(Date)       # Data da análise
    target_date = Column(Date)      # Data alvo
    
    predicted_signal = Column(String)
    predicted_price = Column(Float)
    confidence = Column(Float, nullable=True)
    
    # --- NOVO CAMPO ---
    # Vai guardar texto simples, ex: "RSI, MACD, SMA_200"
    indicators = Column(String, nullable=True) 
    
    # Auditoria
    actual_close = Column(Float, nullable=True)
    is_correct = Column(String, nullable=True)
    error_pct = Column(Float, nullable=True)