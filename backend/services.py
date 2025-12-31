# backend/services.py
import yfinance as yf
import pandas as pd

def fetch_stock_history(ticker: str, period: str = "max"):
    if not ticker.endswith(".SA"): full_ticker = f"{ticker}.SA"
    else: full_ticker = ticker

    try:
        stock = yf.Ticker(full_ticker)
        history = stock.history(period=period)
        if history.empty: return None
        history.reset_index(inplace=True)
        return history
    except Exception as e:
        print(f"Erro histórico: {e}")
        return None

def get_quote_data(ticker: str):
    """
    Busca dados de tempo real e estatísticas de 52 semanas.
    """
    if not ticker.endswith(".SA"): full_ticker = f"{ticker}.SA"
    else: full_ticker = ticker
    
    try:
        stock = yf.Ticker(full_ticker)
        # Tenta pegar do fast_info (mais rápido) ou info (mais completo)
        info = stock.fast_info
        
        current = info.last_price
        # Alguns dados ficam em .info (metadados), outros em fast_info
        # Para 52 semanas, as vezes precisamos do histórico se o metadata falhar
        
        # Estratégia Híbrida para garantir dados
        try:
            low_52 = info.year_low
            high_52 = info.year_high
        except:
            # Fallback: calcula no braço com histórico de 1 ano
            hist = stock.history(period="1y")
            low_52 = hist['Low'].min()
            high_52 = hist['High'].max()

        avg_52 = (low_52 + high_52) / 2
        
        return {
            "symbol": ticker.upper(),
            "price": current,
            "low_52k": low_52,
            "high_52k": high_52,
            "avg_52k": avg_52
        }
    except Exception as e:
        print(f"Erro cotação: {e}")
        return None