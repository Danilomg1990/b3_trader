from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import os
import sys

# Importações locais
from backend import services, models, database, ml_engine

# Cria tabelas no banco de dados
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="B3 AI Trader Pro",
    version="8.0.0",
    description="Plataforma de Inteligência Institucional"
)

# ========================================================
# CONFIGURAÇÃO DE PASTAS (MVC)
# ========================================================

# Identifica a pasta raiz do projeto
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print(f"📂 Diretório base: {base_dir}")

# Pastas do Frontend
static_path = os.path.join(base_dir, "frontend", "statics")
template_path = os.path.join(base_dir, "frontend", "template")

print(f"📂 Caminho estáticos: {static_path}")
print(f"📂 Caminho templates: {template_path}")

# Verifica se as pastas existem
if not os.path.exists(static_path):
    print(f"❌ ERRO: Pasta statics não encontrada!")
    print(f"   Procurando em: {static_path}")
    sys.exit(1)

if not os.path.exists(template_path):
    print(f"❌ ERRO: Pasta template não encontrada!")
    print(f"   Procurando em: {template_path}")
    sys.exit(1)

# Monta as rotas de arquivos estáticos
app.mount("/static", StaticFiles(directory=static_path), name="static")
print(f"✅ Estáticos carregados: {static_path}")

app.mount("/app", StaticFiles(directory=template_path, html=True), name="app")
print(f"✅ Templates carregados: {template_path}")

# ========================================================
# CORS
# ========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --- SCHEMAS (Validação de Dados que vem do Site) ---
class PortfolioCreate(BaseModel):
    name: str

class AssetCreate(BaseModel):
    ticker: str
    avg_price: float

# ========================================================
# ROTAS BÁSICAS
# ========================================================

@app.get("/")
def read_root():
    """Redireciona para o aplicativo principal"""
    return RedirectResponse(url="/app/index.html")

@app.get("/health")
def health_check():
    """Verifica se a API está operacional"""
    return {
        "status": "operational",
        "version": "8.0.0",
        "service": "DMG B3 Trader Pro"
    }

# ========================================================
# FUNÇÕES AUXILIARES
# ========================================================

def audit_predictions(db: Session, ticker: str) -> int:
    """Audita previsões passadas"""
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
            p.is_correct = "✅" if p.error_pct < 3.0 else "❌"
            count += 1
    
    if count > 0:
        db.commit()
    
    return count

# ========================================================
# ENDPOINTS DA API
# ========================================================

@app.post("/sync/{ticker}")
def sync_stock_data(ticker: str, db: Session = Depends(database.get_db)):
    """Sincroniza dados históricos"""
    try:
        hist = services.fetch_stock_history(ticker, period="max")
        
        if hist is None or hist.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"Ação {ticker} não encontrada ou sem dados disponíveis."
            )

        # Limpa dados antigos
        db.query(models.StockHistory).filter(
            models.StockHistory.ticker == ticker
        ).delete()
        
        # Insere novos dados
        data_list = []
        for _, row in hist.iterrows():
            data_list.append(models.StockHistory(
                ticker=ticker,
                date=row['Date'].date(),
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            ))
        
        db.bulk_save_objects(data_list)
        db.commit()
        
        audited_count = audit_predictions(db, ticker)
        
        return {
            "status": "success",
            "ticker": ticker,
            "records_synced": len(data_list),
            "predictions_audited": audited_count,
            "message": f"✅ Dados atualizados com sucesso!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/quote/{ticker}")
def get_quote(ticker: str):
    """Retorna cotação em tempo real"""
    try:
        data = services.get_quote_data(ticker)
        if not data:
            raise HTTPException(status_code=404, detail=f"Ativo {ticker} não encontrado")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/analyze/{ticker}")
def analyze_stock(
    ticker: str,
    days: int = Query(5, ge=1, le=90),
    timeframe: str = Query("D", regex="^(D|W|M|Y)$"),
    profile: str = Query("JPM", regex="^(JPM|XP|BTG)$"),
    indicators: Optional[List[str]] = Query(None),
    db: Session = Depends(database.get_db)
):
    """Gera previsão de preço com IA"""
    try:
        # Busca histórico
        records = db.query(models.StockHistory).filter(
            models.StockHistory.ticker == ticker
        ).order_by(models.StockHistory.date).all()
        
        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"Execute /sync/{ticker} primeiro"
            )

        # Prepara DataFrame
        data = []
        for r in records:
            data.append({
                'date': r.date,
                'open': r.open,
                'high': r.high,
                'low': r.low,
                'close': r.close,
                'volume': r.volume
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Resampling
        if timeframe != 'D':
            logic = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            
            if timeframe == 'W':
                df = df.resample('W').agg(logic)
            elif timeframe == 'M':
                try:
                    df = df.resample('ME').agg(logic)
                except:
                    df = df.resample('M').agg(logic)
            elif timeframe == 'Y':
                try:
                    df = df.resample('YE').agg(logic)
                except:
                    df = df.resample('A').agg(logic)
            
            df.dropna(inplace=True)

        df.reset_index(inplace=True)

        # Análise com IA
        df = ml_engine.calculate_institutional_indicators(df)
        result = ml_engine.analyze_full(
            df, 
            days_ahead=days,
            selected_features=indicators or [],
            profile=profile
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Dados insuficientes para análise"
            )

        # Salva previsão
        if timeframe == 'D':
            last_date = df.iloc[-1]['date'].date()
            target_dt = last_date + timedelta(days=days)
            indicators_str = ", ".join(indicators) if indicators else f"Perfil {profile}"
            
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

        # Prepara resposta
        current_price = float(df.iloc[-1]['close'])
        variation = ((result['predicted_price'] - current_price) / current_price) * 100
        
        # Dados para gráfico
        candles = []
        vwap_line = []
        sma_14 = []
        sma_50 = []
        
        for index, row in df.iterrows():
            ts = int(row['date'].timestamp() * 1000)
            
            candles.append({
                "x": ts,
                "y": [
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close'])
                ]
            })
            
            vwap_line.append({
                "x": ts,
                "y": float(row['VWAP']) if 'VWAP' in row and pd.notna(row['VWAP']) else None
            })
            
            sma_14.append({
                "x": ts,
                "y": float(row['SMA_14']) if 'SMA_14' in row and pd.notna(row['SMA_14']) else None
            })
            
            sma_50.append({
                "x": ts,
                "y": float(row['SMA_50']) if 'SMA_50' in row and pd.notna(row['SMA_50']) else None
            })

        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "signal": result['signal'],
            "confidence": f"{result['confidence']*100:.1f}%",
            "predicted_price": round(result['predicted_price'], 2),
            "variation_pct": round(variation, 2),
            "profile": profile,
            "chart_data": {
                "candles": candles,
                "vwap": vwap_line,
                "sma_14": sma_14,
                "sma_50": sma_50
            },
            "used_features": result.get('used_features', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/history/stats")
def get_global_stats(db: Session = Depends(database.get_db)):
    """Estatísticas de assertividade"""
    try:
        predictions = db.query(models.Prediction).filter(
            models.Prediction.actual_close != None
        ).all()
        
        if not predictions:
            return []
        
        stats = {}
        for p in predictions:
            if p.ticker not in stats:
                stats[p.ticker] = {
                    "total": 0,
                    "correct": 0,
                    "error_sum": 0,
                    "conf_sum": 0
                }
            
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
        
        result.sort(key=lambda x: x['accuracy'], reverse=True)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/history/log")
def get_history_log(db: Session = Depends(database.get_db)):
    """Log detalhado de previsões"""
    try:
        logs = db.query(models.Prediction).order_by(
            models.Prediction.created_at.desc(),
            models.Prediction.id.desc()
        ).all()
        
        result = []
        for log in logs:
            result.append({
                "date": str(log.created_at),
                "target_date": str(log.target_date),
                "ticker": log.ticker,
                "predicted": round(log.predicted_price, 2) if log.predicted_price else None,
                "real": round(log.actual_close, 2) if log.actual_close else None,
                "result": log.is_correct if log.is_correct else "⏳",
                "indicators": log.indicators or "Padrão"
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
    
@app.get("/market/overview")
def get_market_overview_api(db: Session = Depends(database.get_db)): # <--- 1. Adicione o Depends aqui
    """Retorna o painel de mercado (Cacheado no Banco)."""
    
    # 2. Passe o 'db' para a função do serviço
    data = services.get_market_overview(db) 
    
    if not data:
        raise HTTPException(status_code=500, detail="Erro ao buscar dados de mercado")
    return data
# --- ROTAS DE CARTEIRA ---

# 1. Criar Nova Carteira
@app.post("/portfolios/")
def create_portfolio(portfolio: PortfolioCreate, db: Session = Depends(database.get_db)):
    db_portfolio = models.Portfolio(name=portfolio.name)
    db.add(db_portfolio)
    try:
        db.commit()
        db.refresh(db_portfolio)
        return db_portfolio
    except:
        raise HTTPException(status_code=400, detail="Carteira já existe")

# 2. Listar Todas Carteiras
@app.get("/portfolios/")
def read_portfolios(db: Session = Depends(database.get_db)):
    return db.query(models.Portfolio).all()

# 3. Adicionar Ativo na Carteira
@app.post("/portfolios/{portfolio_id}/assets")
def add_asset_to_portfolio(portfolio_id: int, asset: AssetCreate, db: Session = Depends(database.get_db)):
    # Limpa ticker
    clean_ticker = asset.ticker.upper().replace(".SA", "").strip()
    
    new_asset = models.PortfolioAsset(
        portfolio_id=portfolio_id,
        ticker=clean_ticker,
        avg_price=asset.avg_price
    )
    db.add(new_asset)
    db.commit()
    return {"message": "Ativo adicionado"}

# 4. Ver Detalhes da Carteira (Com Cotação Atualizada)
@app.get("/portfolios/{portfolio_id}/view")
def view_portfolio(portfolio_id: int, db: Session = Depends(database.get_db)):
    data = services.get_portfolio_overview(portfolio_id, db)
    return data

# 5. Deletar Ativo
@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(database.get_db)):
    db.query(models.PortfolioAsset).filter(models.PortfolioAsset.id == asset_id).delete()
    db.commit()
    return {"message": "Deletado"}