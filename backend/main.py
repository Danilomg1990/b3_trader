from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
import pandas as pd
import numpy as np
import os

# Importações locais
from . import services, models, database, ml_engine

# Cria tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="B3 AI Trader V7 - Institutional")

# --- CONFIGURAÇÃO DE PASTAS ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return RedirectResponse(url="/app/")

# --- AUDITORIA ---
def audit_predictions(db: Session, ticker: str):
    """Verifica acertos de previsões passadas."""
    pending = db.query(models.Prediction).filter(
        models.Prediction.ticker == ticker,
        models.Prediction.target_date <= date.today(),
        models.Prediction.actual_close == None
    ).all()
    
    count = 0
    for p in pending:
        history = db.query(models.StockHistory).filter(
            models.StockHistory.ticker == ticker,
            models.StockHistory.date == p.target_date
        ).first()
        
        if history:
            p.actual_close = history.close
            diff = abs(p.predicted_price - history.close)
            p.error_pct = (diff / history.close) * 100
            # Considera acerto se erro < 2%
            p.is_correct = "✅" if p.error_pct < 2.0 else "❌"
            count += 1
    db.commit()
    return count

# --- ENDPOINTS ---

@app.post("/sync/{ticker}")
def sync_stock_data(ticker: str, db: Session = Depends(database.get_db)):
    """Baixa histórico MÁXIMO da B3 para permitir médias longas."""
    hist = services.fetch_stock_history(ticker, period="max") # Força histórico máximo
    
    if hist is None or hist.empty:
        raise HTTPException(status_code=404, detail="Ação não encontrada ou sem dados.")

    # Limpa dados antigos
    db.query(models.StockHistory).filter(models.StockHistory.ticker == ticker).delete()
    
    data_list = []
    for _, row in hist.iterrows():
        data_list.append(models.StockHistory(
            ticker=ticker,
            date=row['Date'].date(),
            open=row['Open'],
            high=row['High'],
            low=row['Low'],
            close=row['Close'],
            volume=row['Volume']
        ))
    
    db.add_all(data_list)
    db.commit()
    
    audited_count = audit_predictions(db, ticker)
    return {"message": f"Dados atualizados. {audited_count} previsões conferidas."}

@app.get("/analyze/{ticker}")
def analyze_stock(
    ticker: str, 
    days: int = 5, 
    timeframe: str = Query("D", description="D=Diario, W=Semanal, M=Mensal, Y=Anual"), 
    indicators: List[str] = Query(["VWAP", "OBV"]), 
    db: Session = Depends(database.get_db)
):
    """Gera previsão e prepara dados para o gráfico avançado."""
    
    # 1. Busca do Banco
    records = db.query(models.StockHistory).filter(models.StockHistory.ticker == ticker).order_by(models.StockHistory.date).all()
    if not records: raise HTTPException(status_code=404, detail="Execute /sync primeiro.")

    # 2. Prepara DataFrame
    data = [r.__dict__.copy() for r in records]
    for d in data: d.pop('_sa_instance_state', None)
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # 3. Timeframe Resampling (Transforma D para W/M/Y)
    if timeframe != 'D':
        logic = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        try:
            if timeframe == 'W': df = df.resample('W').agg(logic)
            elif timeframe == 'M': df = df.resample('ME').agg(logic)
            elif timeframe == 'Y': df = df.resample('YE').agg(logic)
        except:
            # Fallback para pandas antigo
            if timeframe == 'M': df = df.resample('M').agg(logic)
            elif timeframe == 'Y': df = df.resample('A').agg(logic)
        df.dropna(inplace=True)

    df.reset_index(inplace=True)

    # 4. Cálculo de Indicadores (ML Engine Inteligente)
    # A função calcula apenas o que é possível (ex: ignora SMA_200 se não tiver dados)
    df = ml_engine.calculate_institutional_indicators(df)
    result = ml_engine.analyze_full(df, days_ahead=days, selected_features=indicators)
    
    if not result:
        raise HTTPException(status_code=400, detail="Dados insuficientes para análise neste timeframe.")

    # 5. Salvar Previsão (Apenas Diário por enquanto)
    if timeframe == 'D':
        last_date = df.iloc[-1]['date'].date()
        target_dt = last_date + timedelta(days=days)
        indicators_str = ", ".join(indicators)
        
        existing = db.query(models.Prediction).filter(
            models.Prediction.ticker == ticker,
            models.Prediction.created_at == last_date,
            models.Prediction.target_date == target_dt,
            models.Prediction.indicators == indicators_str
        ).first()
        
        if not existing:
            new_pred = models.Prediction(
                ticker=ticker,
                created_at=last_date,
                target_date=target_dt,
                predicted_signal=result['signal'],
                predicted_price=result['predicted_price'],
                confidence=result['confidence'],
                indicators=indicators_str
            )
            db.add(new_pred)
            db.commit()

    current_price = df.iloc[-1]['close']
    variation = ((result['predicted_price'] - current_price) / current_price) * 100
    
    # 6. Preparar Dados para Gráfico (BLINDAGEM CONTRA ERROS)
    candles = []
    vwap_line = []
    bb_upper = []
    bb_lower = []
    sma_14 = []
    sma_50 = []
    
    # Função auxiliar para pegar valor seguro (evita crash se coluna não existir)
    def safe_get(row, col_name):
        if col_name not in df.columns: return None
        val = row[col_name]
        return None if pd.isna(val) else val

    for index, row in df.iterrows():
        ts = int(row['date'].timestamp() * 1000)
        
        # Vela
        candles.append({
            "x": ts,
            "y": [row['open'], row['high'], row['low'], row['close']]
        })
        
        # Indicadores
        vwap_line.append({"x": ts, "y": safe_get(row, 'VWAP')})
        bb_upper.append({"x": ts, "y": safe_get(row, 'BB_Upper')})
        bb_lower.append({"x": ts, "y": safe_get(row, 'BB_Lower')})
        
        # Novas Médias
        sma_14.append({"x": ts, "y": safe_get(row, 'SMA_14')})
        sma_50.append({"x": ts, "y": safe_get(row, 'SMA_50')})

    return {
        "ticker": ticker,
        "current_price": current_price,
        "signal": result['signal'],
        "confidence": f"{result['confidence']*100:.1f}%",
        "predicted_price": round(result['predicted_price'], 2),
        "variation_pct": round(variation, 2),
        "chart_data": {
            "candles": candles,
            "vwap": vwap_line,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "sma_14": sma_14, # Enviando para o Front
            "sma_50": sma_50  # Enviando para o Front
        },
        "used_features": result.get('used_features', [])
    }

@app.get("/history/stats")
def get_global_stats(db: Session = Depends(database.get_db)):
    predictions = db.query(models.Prediction).filter(models.Prediction.actual_close != None).all()
    stats = {}
    for p in predictions:
        if p.ticker not in stats:
            stats[p.ticker] = {"total": 0, "correct": 0, "error_sum": 0, "conf_sum": 0}
        
        s = stats[p.ticker]
        s["total"] += 1
        if p.is_correct == "✅": s["correct"] += 1
        s["error_sum"] += (p.error_pct if p.error_pct else 0)
        s["conf_sum"] += (p.confidence if p.confidence else 0)

    result = []
    for ticker, data in stats.items():
        total = data["total"]
        if total > 0:
            result.append({
                "ticker": ticker,
                "total_predictions": total,
                "accuracy": round((data["correct"] / total) * 100, 1),
                "avg_error": round(data["error_sum"] / total, 2),
                "avg_confidence": round((data["conf_sum"] / total) * 100, 1)
            })
    
    result.sort(key=lambda x: x['accuracy'], reverse=True)
    return result

@app.get("/history/log")
def get_history_log(db: Session = Depends(database.get_db)):
    logs = db.query(models.Prediction).order_by(
        models.Prediction.created_at.desc(), 
        models.Prediction.id.desc()
    ).all()
    
    result = []
    for log in logs:
        result.append({
            "date": log.created_at,
            "target_date": log.target_date,
            "ticker": log.ticker,
            "predicted": log.predicted_price,
            "real": log.actual_close,
            "result": log.is_correct if log.is_correct else "⏳",
            "indicators": log.indicators
        })
    return result