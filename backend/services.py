import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import MarketData,Portfolio, PortfolioAsset

def fetch_stock_history(ticker: str, period: str = "max"):
    """
    Busca histórico da B3 para análise da IA.
    """
    if not ticker.endswith(".SA"):
        full_ticker = f"{ticker}.SA"
    else:
        full_ticker = ticker

    print(f"\n📥 BUSCANDO HISTÓRICO DE {ticker}...")

    try:
        # Usa yfinance diretamente (sem session customizada para evitar erros)
        stock = yf.Ticker(full_ticker)
        history = stock.history(period=period)
        
        if history.empty:
            print("⚠️ Histórico vazio.")
            return None

        history.reset_index(inplace=True)
        
        # Remove fuso horário para compatibilidade com SQLite
        if 'Date' in history.columns:
            history['Date'] = history['Date'].dt.tz_localize(None)
            
        return history

    except Exception as e:
        print(f"❌ Erro no histórico: {e}")
        return None

def get_quote_data(ticker: str):
    """
    Busca cotação em tempo real e estatísticas de 52 semanas.
    Usa BRAPI como primária e YFINANCE como fallback.
    """
    clean_ticker = ticker.replace(".SA", "").upper()
    
    # 1. TENTATIVA RÁPIDA: BRAPI
    try:
        url = f"https://brapi.dev/api/quote/{clean_ticker}?range=1y&interval=1d&fundamental=false"
        resp = requests.get(url, timeout=3)
        
        if resp.status_code == 200:
            data = resp.json()['results'][0]
            return {
                "symbol": data['symbol'],
                "price": data['regularMarketPrice'],
                "low_52k": data.get('regularMarketDayLow') or data['regularMarketPrice'] * 0.8,
                "high_52k": data.get('regularMarketDayHigh') or data['regularMarketPrice'] * 1.2,
                "avg_52k": data['regularMarketPrice'] # Simplificação se faltar dados
            }
    except:
        pass 

    # 2. TENTATIVA ROBUSTA: YFINANCE
    try:
        full_ticker = f"{clean_ticker}.SA"
        stock = yf.Ticker(full_ticker)
        info = stock.fast_info
        
        current = info.last_price
        
        # Tenta pegar high/low de 52 semanas
        try:
            low_52 = info.year_low
            high_52 = info.year_high
        except:
            hist = stock.history(period="1y")
            if not hist.empty:
                low_52 = hist['Low'].min()
                high_52 = hist['High'].max()
            else:
                low_52 = current * 0.9
                high_52 = current * 1.1

        avg_52 = (low_52 + high_52) / 2
        
        return {
            "symbol": clean_ticker,
            "price": current,
            "low_52k": low_52,
            "high_52k": high_52,
            "avg_52k": avg_52
        }

    except Exception as e:
        print(f"❌ Erro na cotação: {e}")
        return generate_mock_quote(clean_ticker)

def get_market_overview(db: Session):
    """
    Retorna o panorama de mercado (Cacheado no Banco).
    """
    # 1. Tenta pegar do Cache (Banco de Dados)
    last_update = db.query(func.max(MarketData.updated_at)).scalar()
    
    if last_update and (datetime.utcnow() - last_update < timedelta(minutes=15)):
        print("⚡ Cache de mercado válido encontrado.")
        cached_data = db.query(MarketData).all()
        result = {}
        for item in cached_data:
            if item.category not in result: result[item.category] = []
            result[item.category].append({
                "ticker": item.ticker,
                "price": item.price,
                "change": item.change_pct
            })
        return result

    # 2. Se não tem cache, baixa da internet
    print("🌐 Atualizando dados de mercado...")
    
    market_map = {
        "🏦 Bancos": ["ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "SANB11.SA", "BPAC11.SA"],
        "🛢️ Petróleo": ["PETR4.SA", "PRIO3.SA", "UGPA3.SA", "CSAN3.SA", "VBBR3.SA"],
        "⛏️ Mineração": ["VALE3.SA", "GGBR4.SA", "CSNA3.SA", "USIM5.SA", "CMIN3.SA"],
        "💡 Energia": ["ELET3.SA", "WEGE3.SA", "CMIG4.SA", "CPLE6.SA", "EQTL3.SA"],
        "🏗️ FIIs": ["HGLG11.SA", "KNIP11.SA", "MXRF11.SA", "XPML11.SA", "VISC11.SA"],
        "₿ Cripto": ["BTC-USD", "ETH-USD", "SOL-USD", "USDT-USD"]
    }

    all_tickers = [t for cat in market_map.values() for t in cat]
    tickers_data = yf.Tickers(" ".join(all_tickers))
    
    # Limpa banco antigo
    db.query(MarketData).delete()
    
    result = {}
    db_items = []

    for category, symbols in market_map.items():
        cat_data = []
        for symbol in symbols:
            try:
                info = tickers_data.tickers[symbol].fast_info
                price = info.last_price
                prev = info.previous_close
                
                if price and prev:
                    change = ((price - prev) / prev) * 100
                    clean = symbol.replace(".SA", "").replace("-USD", "")
                    
                    item = {"ticker": clean, "price": price, "change": change}
                    cat_data.append(item)
                    
                    db_items.append(MarketData(
                        ticker=clean, category=category, price=price, 
                        change_pct=change, updated_at=datetime.utcnow()
                    ))
            except: continue
        
        if cat_data: result[category] = cat_data

    if db_items:
        db.add_all(db_items)
        db.commit()

    return result

def generate_mock_quote(ticker):
    """Dados falsos para teste se tudo falhar"""
    return {
        "symbol": ticker,
        "price": 50.00,
        "low_52k": 40.00,
        "high_52k": 60.00,
        "avg_52k": 50.00
    }

def get_portfolio_overview(portfolio_id: int, db: Session):
    """
    Busca os ativos de uma carteira e atualiza com preços em tempo real.
    """
    # 1. Pega os ativos do banco de dados
    assets = db.query(PortfolioAsset).filter(PortfolioAsset.portfolio_id == portfolio_id).all()
    
    if not assets:
        return []

    # 2. Lista de tickers para o Yahoo Finance
    tickers_list = [a.ticker + ".SA" if not a.ticker.endswith(".SA") and not a.ticker.endswith("-USD") else a.ticker for a in assets]
    tickers_str = " ".join(tickers_list)
    
    result = []
    
    try:
        # 3. Baixa dados em tempo real (Batch)
        yf_data = yf.Tickers(tickers_str)
        
        for asset in assets:
            ticker_fmt = asset.ticker + ".SA" if not asset.ticker.endswith(".SA") and "USD" not in asset.ticker else asset.ticker
            
            try:
                info = yf_data.tickers[ticker_fmt].fast_info
                current = info.last_price
                
                # Tenta pegar 52 semanas (Year High/Low)
                try:
                    low_52 = info.year_low
                    high_52 = info.year_high
                except:
                    # Fallback simples
                    low_52 = current * 0.8
                    high_52 = current * 1.2
                
                # Calcula rentabilidade
                profit_pct = ((current - asset.avg_price) / asset.avg_price) * 100
                
                result.append({
                    "id": asset.id,
                    "ticker": asset.ticker,
                    "avg_price": asset.avg_price,
                    "current_price": current,
                    "low_52k": low_52,
                    "high_52k": high_52,
                    "profit_pct": profit_pct
                })
            except:
                # Se falhar o Yahoo, devolve só o que tem no banco
                result.append({
                    "id": asset.id,
                    "ticker": asset.ticker,
                    "avg_price": asset.avg_price,
                    "current_price": 0.0,
                    "low_52k": 0.0, 
                    "high_52k": 0.0,
                    "profit_pct": 0.0
                })
                
        return result

    except Exception as e:
        print(f"Erro portfolio: {e}")
        return []