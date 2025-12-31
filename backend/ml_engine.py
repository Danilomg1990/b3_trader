# backend/ml_engine.py
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor, ExtraTreesRegressor
from sklearn.feature_selection import SelectFromModel

# ... (Mantenha a função calculate_institutional_indicators IGUAL à anterior) ...
# COPIE A FUNÇÃO calculate_institutional_indicators DA VERSÃO ANTERIOR AQUI
def calculate_institutional_indicators(df):
    df = df.copy()
    df['close'] = df['close'].replace(0, np.nan)
    df['volume'] = df['volume'].replace(0, np.nan)
    
    # VWAP
    if len(df) >= 21:
        df['VWAP'] = (df['close'] * df['volume']).rolling(window=21).sum() / df['volume'].rolling(window=21).sum()
        df['Dist_VWAP'] = (df['close'] - df['VWAP']) / df['VWAP']
    
    df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    
    if len(df) >= 14:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        
        typ_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typ_price * df['volume']
        pos_flow = money_flow.where(typ_price > typ_price.shift(1), 0).rolling(window=14).sum()
        neg_flow = money_flow.where(typ_price < typ_price.shift(1), 0).rolling(window=14).sum()
        df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))
        
        df['SMA_14'] = df['close'].rolling(window=14).mean()
        tr1 = df['high'] - df['low']; tr2 = np.abs(df['high'] - df['close'].shift()); tr3 = np.abs(df['low'] - df['close'].shift())
        df['ATR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(window=14).mean()

    if len(df) >= 26:
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26

    if len(df) >= 20:
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['STD_20'] = df['close'].rolling(window=20).std()
        df['BB_Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['BB_Lower'] = df['SMA_20'] - (df['STD_20'] * 2)

    if len(df) >= 50: df['SMA_50'] = df['close'].rolling(window=50).mean()
    
    if len(df) >= 200:
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['Dist_SMA200'] = (df['close'] - df['SMA_200']) / df['SMA_200']
    
    return df

def get_profile_model(profile='JPM', model_type='classifier'):
    """
    Retorna o modelo ajustado para o perfil do banco escolhido.
    """
    if model_type == 'classifier':
        # Classificadores Base
        gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        
        # Pesos de Votação
        if profile == 'XP': # Agressivo
            return VotingClassifier(estimators=[('gb', gb), ('rf', rf)], voting='soft', weights=[2, 1])
        elif profile == 'BTG': # Tendência
            return VotingClassifier(estimators=[('gb', gb), ('rf', rf)], voting='soft', weights=[1, 1])
        else: # JPM (Conservador)
            return VotingClassifier(estimators=[('gb', gb), ('rf', rf)], voting='soft', weights=[1, 2])
            
    else: # Regressor (Preço)
        gb = GradientBoostingRegressor(n_estimators=200, max_depth=4, random_state=42)
        rf = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
        et = ExtraTreesRegressor(n_estimators=200, max_depth=10, random_state=42)
        
        if profile == 'XP': # Momentum (Prioriza Boosting que pega viradas rápidas)
            return VotingRegressor(estimators=[('gb', gb), ('rf', rf), ('et', et)], weights=[3, 1, 1])
        
        elif profile == 'BTG': # Tendência (Equilibrado)
            return VotingRegressor(estimators=[('gb', gb), ('rf', rf), ('et', et)], weights=[1, 1, 1])
        
        else: # JPM (Conservador - Prioriza Random Forest e Extra Trees que reduzem ruído)
            return VotingRegressor(estimators=[('gb', gb), ('rf', rf), ('et', et)], weights=[1, 2, 2])

def analyze_full(df, days_ahead=5, selected_features=None, profile='JPM'):
    if len(df) < 50: return None

    df = calculate_institutional_indicators(df)
    
    df['Target_Signal'] = (df['close'].shift(-days_ahead) > df['close']).astype(int)
    df['Target_Return'] = np.log(df['close'].shift(-days_ahead) / df['close'])
    
    df.dropna(inplace=True)
    if len(df) < 10: return None

    # Seleção de Features baseada no Perfil
    all_features = ['VWAP', 'OBV', 'MFI', 'RSI', 'MACD', 'SMA_14', 'SMA_50', 'SMA_200', 'BB_Upper', 'BB_Lower', 'ATR', 'Dist_VWAP']
    
    # Se o usuário não selecionou nada, o perfil dita as regras
    if not selected_features:
        if profile == 'XP': features_to_use = ['RSI', 'MACD', 'BB_Upper', 'BB_Lower', 'MFI'] # Trader
        elif profile == 'BTG': features_to_use = ['SMA_50', 'SMA_200', 'OBV', 'VWAP'] # Trend
        else: features_to_use = ['VWAP', 'ATR', 'Dist_VWAP', 'SMA_200'] # JPM Risk
        
        # Garante que existam no DF
        features_to_use = [f for f in features_to_use if f in df.columns]
    else:
        candidates = list(set(selected_features + ['Dist_VWAP', 'ATR']))
        features_to_use = [f for f in candidates if f in df.columns]

    if not features_to_use: return None

    X = df[features_to_use]
    y_signal = df['Target_Signal']
    y_return = df['Target_Return']

    sample_weights = np.linspace(0.1, 1.0, len(X))

    # Treina com o Perfil Escolhido
    ensemble_clf = get_profile_model(profile, 'classifier')
    ensemble_clf.fit(X, y_signal, sample_weight=sample_weights)
    
    ensemble_reg = get_profile_model(profile, 'regressor')
    ensemble_reg.fit(X, y_return, sample_weight=sample_weights)
    
    last_day = X.iloc[[-1]]
    signal_pred = ensemble_clf.predict(last_day)[0]
    signal_prob = ensemble_clf.predict_proba(last_day)[0][signal_pred]
    predicted_log_return = ensemble_reg.predict(last_day)[0]
    
    # Consistência
    current_price = df.iloc[-1]['close']
    final_signal = "COMPRA 🚀" if signal_pred == 1 else "VENDA 🔻"
    if signal_prob < 0.55: final_signal = "NEUTRO ⚠️"

    predicted_price = current_price * np.exp(predicted_log_return)
    
    return {
        "signal": final_signal,
        "confidence": signal_prob,
        "predicted_price": predicted_price,
        "used_features": features_to_use,
        "profile_used": profile
    }