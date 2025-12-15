from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from . import services
from . import models, database, ml_engine

# Criar as tabelas
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="B3 AI Trader")

# Permitir que o Frontend acesse o Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/sync/{ticker}")
def sync_stock_data(ticker: str, db: Session = Depends(database.get_db)):
    """Sincroniza dados históricos da ação para o banco de dados"""
    hist = services.fetch_stock_history(ticker)
    
    if hist.empty:
        raise HTTPException(status_code=404, detail="Ação não encontrada")

    # Limpa dados antigos desse ticker (Simplificação para MVP)
    db.query(models.StockHistory).filter(models.StockHistory.ticker == ticker).delete()
    
    data_list = []
    for date, row in hist.iterrows():
        data_list.append(models.StockHistory(
            ticker=ticker,
            date=date.date(),
            open=row['Open'],
            high=row['High'],
            low=row['Low'],
            close=row['Close'],
            volume=row['Volume']
        ))
    
    db.add_all(data_list)
    db.commit()
    return {"message": f"Dados de {ticker} atualizados com {len(data_list)} registros."}

@app.get("/analyze/{ticker}")
def analyze_stock(ticker: str, db: Session = Depends(database.get_db)):
    """Busca dados do banco e roda a IA"""
    records = db.query(models.StockHistory).filter(models.StockHistory.ticker == ticker).order_by(models.StockHistory.date).all()
    
    if not records:
        raise HTTPException(status_code=404, detail="Dados não encontrados. Execute /sync primeiro.")

    # Converte para DataFrame do Pandas
    df = pd.DataFrame([vars(r) for r in records])
    df = df.drop(columns=['_sa_instance_state']) # Limpeza do SQLAlchemy
    
    # Roda a IA
    prediction, accuracy, prob = ml_engine.train_and_predict(df)

    sentiment = "COMPRA 🚀" if prediction == 1 else "VENDA 🔻"
    
    # Prepara dados para o gráfico do frontend
    chart_data = {
        "dates": [r.date.isoformat() for r in records],
        "prices": [r.close for r in records]
    }

    return {
        "ticker": ticker,
        "current_price": records[-1].close,
        "ai_recommendation": sentiment,
        "ai_confidence": f"{prob*100:.1f}%",
        "model_accuracy": f"{accuracy*100:.1f}%",
        "chart_data": chart_data
    }