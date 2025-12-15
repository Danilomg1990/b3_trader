import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

def train_and_predict(df):
    """
    Recebe um DataFrame com histórico.
    Retorna: Previsão (1=Subir, 0=Cair), Acurácia do modelo e Probabilidade.
    """
    if len(df) < 50:
        return None, 0, 0  # Dados insuficientes

    df = df.copy()
    
    # Feature Engineering (Criar dados para a IA aprender)
    # Target: 1 se o preço de fechamento de amanhã for maior que hoje
    df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # Features (O que a IA vai olhar): Médias móveis, Retorno diário
    df['SMA_5'] = df['close'].rolling(window=5).mean()
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['RSI'] = df['close'].pct_change() # Simplificação de momentum
    
    df.dropna(inplace=True)

    features = ['open', 'high', 'low', 'close', 'volume', 'SMA_5', 'SMA_20']
    X = df[features]
    y = df['Target']

    # Separa dados de treino e teste
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

    # Modelo: Random Forest (Robusto para iniciantes)
    model = RandomForestClassifier(n_estimators=100, min_samples_split=10, random_state=1)
    model.fit(X_train, y_train)

    # Avaliar precisão
    preds = model.predict(X_test)
    accuracy = accuracy_score(y_test, preds)

    # Prever o futuro (usando o último dia disponível)
    last_day = X.iloc[[-1]]
    prediction = model.predict(last_day)[0]
    probability = model.predict_proba(last_day)[0][prediction]

    return prediction, accuracy, probability