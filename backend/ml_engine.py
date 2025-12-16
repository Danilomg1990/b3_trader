import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

def calculate_technical_indicators(df):
    """Calcula indicadores técnicos avançados"""
    df = df.copy()
    
    # 1. RSI (14 períodos)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. MACD
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    
    # 3. Bandas de Bollinger & SMA 20 (Média de 20 é a base da Bollinger)
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['STD_20'] = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['BB_Lower'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    # --- NOVOS INDICADORES SOLICITADOS ---
    
    # 4. Média Móvel Curta (14 períodos) - Rápida
    df['SMA_14'] = df['close'].rolling(window=14).mean()
    
    # 5. Média Móvel Longa (200 períodos) - Tendência Secular
    df['SMA_200'] = df['close'].rolling(window=200).mean()

    # 6. Momentum (ROC)
    df['ROC'] = df['close'].pct_change(periods=10) * 100
    
    # 7. Cruzamento Dourado (Golden Cross Signal)
    # 1 se a média curta (50) estiver acima da longa (200)
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    df['Golden_Cross'] = (df['SMA_50'] > df['SMA_200']).astype(int)

    return df

def analyze_full(df, days_ahead=5, selected_features=None):
    """
    Treina a IA com os indicadores selecionados
    """
    # Aumentamos a segurança: SMA 200 precisa de pelo menos 200 dias de histórico
    if len(df) < 210:
        print("DEBUG: Dados insuficientes para calcular SMA 200.")
        return None

    # Calcula indicadores
    df = calculate_technical_indicators(df)
    
    # Prepara Targets
    df['Target_Signal'] = (df['close'].shift(-1) > df['close']).astype(int)
    df['Target_Price'] = df['close'].shift(-days_ahead)
    
    # Remove linhas vazias (os primeiros 200 dias serão apagados aqui)
    df.dropna(inplace=True)

    # Definição de Features
    base_features = ['open', 'high', 'low', 'close', 'volume']
    
    if not selected_features:
        selected_features = ['RSI', 'MACD', 'SMA_20', 'SMA_200'] 
        
    # Filtra apenas o que existe no DataFrame
    features_to_use = base_features + [f for f in selected_features if f in df.columns]
    
    X = df[features_to_use]
    
    # --- MODELAGEM ---
    # Classificação (Sinal)
    y_signal = df['Target_Signal']
    clf = GradientBoostingClassifier(n_estimators=100, random_state=42)
    clf.fit(X.iloc[:-days_ahead], y_signal.iloc[:-days_ahead])
    
    last_day = X.iloc[[-1]]
    signal_pred = clf.predict(last_day)[0]
    signal_prob = clf.predict_proba(last_day)[0][signal_pred]
    
    # Regressão (Preço)
    y_price = df['Target_Price']
    reg = GradientBoostingRegressor(n_estimators=100, random_state=42)
    reg.fit(X, y_price)
    price_pred = reg.predict(last_day)[0]
    
    return {
        "signal": "COMPRA 🚀" if signal_pred == 1 else "VENDA 🔻",
        "confidence": signal_prob,
        "predicted_price": price_pred,
        "used_features": selected_features
    }