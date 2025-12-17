import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor, ExtraTreesRegressor
from sklearn.feature_selection import SelectFromModel

def calculate_institutional_indicators(df):
    """Calcula indicadores técnicos e de fluxo (Smart Money)."""
    df = df.copy()
    
    # Tratamento básico
    df['close'] = df['close'].replace(0, np.nan)
    df['volume'] = df['volume'].replace(0, np.nan)

    # 1. VWAP (Preço Médio Ponderado por Volume)
    df['VWAP'] = (df['close'] * df['volume']).rolling(window=21).sum() / df['volume'].rolling(window=21).sum()
    
    # 2. OBV (Saldo de Volume)
    df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    
    # 3. MFI (Money Flow Index)
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']
    pos_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(window=14).sum()
    neg_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(window=14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))

    # 4. Clássicos
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26

    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_200'] = df['close'].rolling(window=200).mean()
    
    df['STD_20'] = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['BB_Lower'] = df['SMA_20'] - (df['STD_20'] * 2)

    df['Dist_VWAP'] = (df['close'] - df['VWAP']) / df['VWAP']
    
    return df

def get_ensemble_model(model_type='classifier'):
    """
    Cria um 'Conselho de IAs' (Ensemble) para maior precisão.
    Combina Gradient Boosting, Random Forest e Extra Trees.
    """
    if model_type == 'classifier':
        # Votação para direção (Sobe/Desce)
        clf1 = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        clf2 = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        
        # VotingClassifier: 'soft' usa a média das probabilidades
        ensemble = VotingClassifier(estimators=[
            ('gb', clf1), ('rf', clf2)
        ], voting='soft')
        return ensemble
    
    else:
        # Votação para preço (Regressão)
        reg1 = GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42)
        reg2 = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
        reg3 = ExtraTreesRegressor(n_estimators=200, max_depth=8, random_state=42)
        
        # VotingRegressor: Tira a média das previsões dos 3 modelos
        ensemble = VotingRegressor(estimators=[
            ('gb', reg1), ('rf', reg2), ('et', reg3)
        ])
        return ensemble

def analyze_full(df, days_ahead=5, selected_features=None):
    if len(df) < 210: return None

    # 1. Indicadores
    df = calculate_institutional_indicators(df)
    
    # 2. Targets
    df['Target_Signal'] = (df['close'].shift(-days_ahead) > df['close']).astype(int)
    df['Target_Return'] = (df['close'].shift(-days_ahead) - df['close']) / df['close']
    
    df.dropna(inplace=True)

    # 3. Seleção de Features
    institutional = ['VWAP', 'OBV', 'MFI', 'Dist_VWAP', 'volume']
    base = ['close', 'RSI', 'MACD', 'SMA_200', 'BB_Upper', 'BB_Lower']
    
    if not selected_features:
        all_cols = institutional + base
        features_to_use = [f for f in all_cols if f in df.columns]
    else:
        must_have = ['Dist_VWAP', 'volume', 'VWAP'] # Features essenciais de fluxo
        candidates = list(set(selected_features + must_have))
        features_to_use = [f for f in candidates if f in df.columns]
    
    X = df[features_to_use]
    y_signal = df['Target_Signal']
    y_return = df['Target_Return']

    # 4. Feature Selection Inteligente
    # Usa um modelo leve para descartar lixo antes de treinar o Ensemble
    selector = SelectFromModel(GradientBoostingClassifier(n_estimators=50, random_state=42), threshold="mean")
    selector.fit(X, y_signal)
    X_new = pd.DataFrame(selector.transform(X), columns=X.columns[selector.get_support()], index=X.index)
    final_features_names = X_new.columns.tolist()

    # 5. Treinamento do Ensemble (Conselho de IAs)
    
    # Classificação
    ensemble_clf = get_ensemble_model('classifier')
    ensemble_clf.fit(X_new, y_signal)
    
    last_day = X_new.iloc[[-1]]
    signal_pred = ensemble_clf.predict(last_day)[0]
    signal_prob = ensemble_clf.predict_proba(last_day)[0][signal_pred]
    
    # Regressão
    ensemble_reg = get_ensemble_model('regressor')
    ensemble_reg.fit(X_new, y_return)
    predicted_return = ensemble_reg.predict(last_day)[0]
    
    # 6. Refinamento de Mercado
    current_price = df.iloc[-1]['close']
    current_vwap = df.iloc[-1]['VWAP']
    
    final_signal = "COMPRA 🚀" if signal_pred == 1 else "VENDA 🔻"
    
    # Filtro de VWAP (Smart Money Filter)
    if signal_pred == 1 and current_price < current_vwap:
        signal_prob -= 0.15 # Penaliza compra contra fluxo
    elif signal_pred == 0 and current_price > current_vwap:
        signal_prob -= 0.15 # Penaliza venda contra fluxo

    if signal_prob < 0.55: final_signal = "NEUTRO ⚠️"

    predicted_price = current_price * (1 + predicted_return)
    
    return {
        "signal": final_signal,
        "confidence": signal_prob,
        "predicted_price": predicted_price,
        "used_features": final_features_names
    }