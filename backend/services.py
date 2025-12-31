# backend/services.py
import yfinance as yf
import pandas as pd
from datetime import datetime

def fetch_stock_history(ticker: str, period: str = "max"): # <--- MUDANÇA AQUI: de "2y" para "max"
    """
    Busca dados históricos da B3 usando o yfinance.
    Baixa o histórico COMPLETO ('max') para permitir análise semanal/mensal com SMA 200.
    """
    # Garante que o ticker tenha o formato da B3 (ex: PETR4.SA)
    if not ticker.endswith(".SA"):
        full_ticker = f"{ticker}.SA"
    else:
        full_ticker = ticker

    try:
        stock = yf.Ticker(full_ticker)
        
        # Baixa o histórico máximo disponível
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