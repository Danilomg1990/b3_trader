from sqlalchemy import Column, Integer, String, Float, Date
from .database import Base

class StockHistory(Base):
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)  # Ex: PETR4.SA
    date = Column(Date)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)