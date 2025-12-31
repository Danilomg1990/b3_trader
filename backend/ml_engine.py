import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor, ExtraTreesRegressor
from sklearn.feature_selection import SelectFromModel

def calculate_institutional_indicators(df):
    """
    Engenharia de Features Nível Institucional.
    Calcula Fluxo, Tendência, Volatilidade e Momentum.
    """
    df = df.copy()
    
    # Tratamento de dados zerados
    df['close'] = df['close'].replace(0, np.nan)
    df['volume'] = df['volume'].replace(0, np.nan)

    # --- 1. FLUXO (SMART MONEY) ---
    # VWAP: Preço Médio Ponderado por Volume
    df['VWAP'] = (df['close'] * df['volume']).rolling(window=21).sum() / df['volume'].rolling(window=21).sum()
    
    # OBV: Saldo de Agressão
    df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    
    # MFI: Índice de Fluxo de Dinheiro
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']
    pos_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(window=14).sum()
    neg_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(window=14).sum()
    df['MFI'] = 100 - (100 / (1 + (pos_flow / neg_flow)))

    # --- 2. TENDÊNCIA E MÉDIAS ---
    df['SMA_14'] = df['close'].rolling(window=14).mean() # Rápida
    df['SMA_20'] = df['close'].rolling(window=20).mean() # Base Bollinger
    df['SMA_50'] = df['close'].rolling(window=50).mean() # Intermediária
    df['SMA_200'] = df['close'].rolling(window=200).mean() # Secular

    # MACD
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26

    # --- 3. VOLATILIDADE E RISCO ---
    # Bollinger
    df['STD_20'] = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['BB_Lower'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    # ATR (Volatilidade Real)
    tr1 = df['high'] - df['low']
    tr2 = np.abs(df['high'] - df['close'].shift())
    tr3 = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()

    # --- 4. OSCILADORES ---
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    # --- 5. FEATURES DERIVADAS ---
    df['Dist_VWAP'] = (df['close'] - df['VWAP']) / df['VWAP']
    df['Dist_SMA200'] = (df['close'] - df['SMA_200']) / df['SMA_200']
    
    return df

def get_adaptive_ensemble(model_type='classifier'):
    """
    Retorna um Ensemble (Conselho de IAs) robusto para séries temporais.
    Substitui o Stacking para evitar o erro de particionamento.
    """
    if model_type == 'classifier':
        # Classificação (Direção)
        clf1 = GradientBoostingClassifier(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42)
        clf2 = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42)
        
        # Soft Voting: Média das probabilidades (mais preciso)
        return VotingClassifier(estimators=[('gb', clf1), ('rf', clf2)], voting='soft')
    else:
        # Regressão (Preço)
        reg1 = GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42)
        reg2 = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
        reg3 = ExtraTreesRegressor(n_estimators=200, max_depth=10, random_state=42)
        
        # VotingRegressor: Média das previsões dos 3 especialistas
        return VotingRegressor(estimators=[('gb', reg1), ('rf', reg2), ('et', reg3)])

def analyze_full(df, days_ahead=5, selected_features=None):
    """
    Executa a análise com Ponderação Temporal (Adaptive Learning) e Ensemble.
    """
    # Validação mínima
    if len(df) < 50: return None

    # 1. Feature Engineering (Calcula o que for possível)
    df = calculate_institutional_indicators(df)
    
    # 2. Definição de Alvos
    df['Target_Signal'] = (df['close'].shift(-days_ahead) > df['close']).astype(int)
    # Retorno Logarítmico (Melhor para matemática financeira)
    df['Target_Return'] = np.log(df['close'].shift(-days_ahead) / df['close'])
    
    df.dropna(inplace=True)
    if len(df) < 10: return None

    # 3. Seleção de Features
    institutional = ['VWAP', 'OBV', 'MFI', 'Dist_VWAP', 'Dist_SMA200', 'ATR', 'volume']
    base = ['close', 'RSI', 'MACD', 'SMA_14', 'SMA_50', 'SMA_200', 'BB_Upper', 'BB_Lower']
    
    # Monta lista de features disponíveis
    all_possible = institutional + base
    available = [f for f in all_possible if f in df.columns]
    
    if not selected_features:
        features_to_use = available
    else:
        # Garante features essenciais se existirem
        must_have = ['Dist_VWAP', 'Dist_SMA200', 'ATR'] 
        candidates = list(set(selected_features + must_have))
        features_to_use = [f for f in candidates if f in df.columns]
    
    if not features_to_use: return None

    X = df[features_to_use]
    y_signal = df['Target_Signal']
    y_return = df['Target_Return']

    # --- 4. ADAPTIVE LEARNING: PESOS TEMPORAIS ---
    # Dados recentes (fim do array) têm peso 1.0. Dados antigos têm peso próximo de 0.1.
    # Isso força a IA a priorizar o momento atual do mercado.
    sample_weights = np.linspace(0.1, 1.0, len(X))

    # --- 5. FILTRAGEM DE RUÍDO (Feature Selection) ---
    try:
        selector = SelectFromModel(
            GradientBoostingRegressor(n_estimators=50, random_state=42), 
            threshold="median"
        )
        selector.fit(X, y_return, sample_weight=sample_weights)
        X_new = pd.DataFrame(selector.transform(X), columns=X.columns[selector.get_support()], index=X.index)
        final_features_names = X_new.columns.tolist()
    except:
        # Fallback se a seleção falhar
        X_new = X
        final_features_names = features_to_use

    # --- 6. TREINAMENTO DO ENSEMBLE ---
    
    # Direção (Classificação)
    ensemble_clf = get_adaptive_ensemble('classifier')
    ensemble_clf.fit(X_new, y_signal, sample_weight=sample_weights)
    
    last_day = X_new.iloc[[-1]]
    signal_pred = ensemble_clf.predict(last_day)[0]
    signal_prob = ensemble_clf.predict_proba(last_day)[0][signal_pred]
    
    # Preço (Regressão)
    ensemble_reg = get_adaptive_ensemble('regressor')
    ensemble_reg.fit(X_new, y_return, sample_weight=sample_weights)
    predicted_log_return = ensemble_reg.predict(last_day)[0]
    
    # --- 7. REGRAS DE CONSISTÊNCIA DE MERCADO ---
    current_price = df.iloc[-1]['close']
    final_signal = "COMPRA 🚀" if signal_pred == 1 else "VENDA 🔻"
    
    # Filtro Institucional (VWAP) - Se existir
    if 'VWAP' in df.columns:
        current_vwap = df.iloc[-1]['VWAP']
        # Se a IA manda comprar, mas o preço está abaixo do preço médio dos bancos -> Perigo
        if signal_pred == 1 and current_price < current_vwap:
            signal_prob -= 0.15 
        elif signal_pred == 0 and current_price > current_vwap:
            signal_prob -= 0.15 

    # Margem de segurança
    if signal_prob < 0.55: 
        final_signal = "NEUTRO ⚠️"

    # Converte retorno logarítmico de volta para preço real
    predicted_price = current_price * np.exp(predicted_log_return)
    
    return {
        "signal": final_signal,
        "confidence": signal_prob,
        "predicted_price": predicted_price,
        "used_features": final_features_names
    }