from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
import pandas as pd
import os

# Importações locais (seus arquivos)
from . import services, models, database, ml_engine

# 1. Cria tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="B3 AI Trader V4")

# --- CONFIGURAÇÃO DE PASTAS ---
# Garante que acha a pasta 'frontend' independente de onde o script roda
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

# Monta arquivos estáticos (HTML/CSS/JS) para acesso pelo navegador
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

# Configuração de CORS (Permitir acesso do navegador)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROTAS GERAIS ---

@app.get("/")
def read_root():
    """Redireciona a raiz (http://localhost:8000/) para a aplicação (/app/)"""
    return RedirectResponse(url="/app/")

# --- FUNÇÃO AUXILIAR: AUDITORIA ---
def audit_predictions(db: Session, ticker: str):
    """
    Verifica se previsões passadas acertaram ou erraram
    baseado nos dados reais que acabaram de chegar via Sync.
    """
    # Busca previsões que já venceram (target_date <= hoje) e ainda não têm resultado real (actual_close == None)
    pending = db.query(models.Prediction).filter(
        models.Prediction.ticker == ticker,
        models.Prediction.target_date <= date.today(),
        models.Prediction.actual_close == None
    ).all()
    
    count = 0
    for p in pending:
        # Busca o preço real que aconteceu naquele dia histórico
        history = db.query(models.StockHistory).filter(
            models.StockHistory.ticker == ticker,
            models.StockHistory.date == p.target_date
        ).first()
        
        if history:
            # Atualiza a tabela com a verdade
            p.actual_close = history.close
            
            # Checa erro percentual do preço (Regressão)
            diff = abs(p.predicted_price - history.close)
            p.error_pct = (diff / history.close) * 100
            
            # Checa se o acerto foi bom (Erro menor que 2%)
            p.is_correct = "✅" if p.error_pct < 2.0 else "❌"
            
            count += 1
    
    db.commit()
    return count

# --- ENDPOINTS ---

@app.post("/sync/{ticker}")
def sync_stock_data(ticker: str, db: Session = Depends(database.get_db)):
    """Baixa dados novos da B3, salva no banco e roda a auditoria"""
    hist = services.fetch_stock_history(ticker)
    
    if hist is None or hist.empty:
        raise HTTPException(status_code=404, detail="Ação não encontrada ou sem dados na B3.")

    # Limpa dados antigos para evitar duplicidade e garantir frescor
    db.query(models.StockHistory).filter(models.StockHistory.ticker == ticker).delete()
    
    data_list = []
    # Itera sobre o DataFrame
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
    
    # Roda a auditoria nas previsões antigas agora que temos dados novos
    audited_count = audit_predictions(db, ticker)
    
    return {"message": f"Dados atualizados com sucesso. {audited_count} previsões antigas foram conferidas."}


@app.get("/analyze/{ticker}")
def analyze_stock(
    ticker: str, 
    days: int = 5, 
    # Recebe lista de indicadores da URL (ex: &indicators=RSI&indicators=MACD...)
    indicators: List[str] = Query(["RSI", "MACD"]), 
    db: Session = Depends(database.get_db)
):
    """Gera nova previsão usando os indicadores selecionados e salva no banco"""
    
    # 1. Busca Histórico do Banco
    records = db.query(models.StockHistory).filter(models.StockHistory.ticker == ticker).order_by(models.StockHistory.date).all()
    
    if not records:
        raise HTTPException(status_code=404, detail="Dados não encontrados. Execute /sync primeiro.")

    # 2. Converte para DataFrame (BLINDAGEM CONTRA ERRO SQLALCHEMY)
    # Isso evita o erro 'UnmappedInstanceError' ao manipular os objetos depois
    data = [r.__dict__.copy() for r in records]
    for d in data:
        d.pop('_sa_instance_state', None)
    
    df = pd.DataFrame(data)
    
    # 3. Roda a Inteligência Artificial (Passando os indicadores escolhidos)
    result = ml_engine.analyze_full(df, days_ahead=days, selected_features=indicators)
    
    if not result:
        # Se não tiver dados suficientes (ex: < 210 linhas para SMA 200)
        raise HTTPException(status_code=400, detail="Dados insuficientes para IA calcular os indicadores (mínimo ~210 dias úteis).")

    # 4. Salva a Previsão (Prediction) no Banco para auditoria futura
    last_date = df.iloc[-1]['date']
    target_dt = last_date + timedelta(days=days)
    
    # Converte a lista de indicadores para string (ex: "RSI, MACD") para salvar no banco
    indicators_str = ", ".join(indicators)

    # Verifica se já não salvamos essa previsão hoje (evita duplicatas)
    existing = db.query(models.Prediction).filter(
        models.Prediction.ticker == ticker,
        models.Prediction.created_at == last_date,
        models.Prediction.target_date == target_dt,
        models.Prediction.indicators == indicators_str # Diferencia se mudou a estratégia
    ).first()
    
    if not existing:
        new_pred = models.Prediction(
            ticker=ticker,
            created_at=last_date,
            target_date=target_dt,
            predicted_signal=result['signal'],
            predicted_price=result['predicted_price'],
            confidence=result['confidence'],
            indicators=indicators_str # Salva os indicadores usados
        )
        db.add(new_pred)
        db.commit()

    # 5. Prepara o Retorno para o Frontend
    current_price = df.iloc[-1]['close']
    variation = ((result['predicted_price'] - current_price) / current_price) * 100
    
    chart_data = {
        "dates": [d.isoformat() for d in df['date']],
        "prices": df['close'].tolist()
    }
    
    return {
        "ticker": ticker,
        "current_price": current_price,
        "signal": result['signal'],
        "confidence": f"{result['confidence']*100:.1f}%",
        "predicted_price": round(result['predicted_price'], 2),
        "variation_pct": round(variation, 2),
        "chart_data": chart_data,
        "used_features": result.get('used_features', [])
    }

@app.get("/history/stats")
def get_global_stats(db: Session = Depends(database.get_db)):
    """Retorna estatísticas consolidadas de acerto de todas as ações"""
    predictions = db.query(models.Prediction).filter(
        models.Prediction.actual_close != None
    ).all()
    
    stats = {}
    
    for p in predictions:
        if p.ticker not in stats:
            stats[p.ticker] = {"total": 0, "correct": 0, "error_sum": 0, "conf_sum": 0}
        
        s = stats[p.ticker]
        s["total"] += 1
        if p.is_correct == "✅":
            s["correct"] += 1
        
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
    
    # Ordena por acurácia (maior primeiro)
    result.sort(key=lambda x: x['accuracy'], reverse=True)
    return result

@app.get("/history/log")
def get_history_log(db: Session = Depends(database.get_db)):
    """Retorna todas as pesquisas feitas (Log Detalhado), da mais recente para a antiga"""
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
            "result": log.is_correct if log.is_correct else "⏳ Aguardando",
            "indicators": log.indicators if log.indicators else "Padrão" # Envia pro frontend
        })
    return result