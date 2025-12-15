# backend/services.py
import yfinance as yf
import pandas as pd
from datetime import datetime

def fetch_stock_history(ticker: str, period: str = "2y"):
    """
    Busca dados históricos da B3 usando o yfinance.
    Adiciona o sufixo .SA automaticamente se não estiver presente.
    """
    # Garante que o ticker tenha o formato da B3 (ex: PETR4.SA)
    if not ticker.endswith(".SA"):
        full_ticker = f"{ticker}.SA"
    else:
        full_ticker = ticker

    try:
        stock = yf.Ticker(full_ticker)
        # Baixa o histórico
        history = stock.history(period=period)
        
        if history.empty:
            return None

        # O yfinance retorna o index como Datetime, vamos resetar para facilitar
        history.reset_index(inplace=True)
        return history

    except Exception as e:
        print(f"Erro ao buscar dados para {full_ticker}: {e}")
        return None

def get_current_price(ticker: str):
    """Pega apenas o preço atual (para features de tempo real futuramente)"""
    if not ticker.endswith(".SA"):
        ticker = f"{ticker}.SA"
    
    stock = yf.Ticker(ticker)
    # fast_info é mais rápido que baixar o histórico todo
    return stock.fast_info.last_price