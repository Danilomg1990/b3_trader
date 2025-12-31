# 🚀 DMG B3 Trader Pro

**Plataforma de Inteligência Institucional para Análise de Ações da B3**

Sistema completo de análise quantitativa com Machine Learning para previsão de preços e sinais de trading, inspirado em metodologias de grandes instituições financeiras.

---

## 📋 **Funcionalidades**

### ✅ **Implementadas**

- ⚡ **Consulta Rápida**: Preço atual e estatísticas de 52 semanas
- 🧠 **Laboratório IA**: Análise com 3 perfis institucionais (JPM, XP, BTG)
- 📊 **Gráficos Interativos**: Candlesticks + Indicadores Técnicos (VWAP, SMA)
- 🎯 **Previsão de Preço**: Machine Learning com ensemble de modelos
- 📈 **Histórico de Operações**: Auditoria automática de assertividade
- 📅 **Múltiplos Timeframes**: Diário, Semanal, Mensal, Anual

### 🎨 **Perfis de Análise**

| Perfil     | Instituição      | Estratégia                    | Indicadores Principais     |
| ---------- | ---------------- | ----------------------------- | -------------------------- |
| **JPM** 🏛️ | JP Morgan        | Risk Management (Conservador) | VWAP, ATR, SMA_200         |
| **XP** 🚀  | XP Investimentos | Trader/Momentum (Agressivo)   | RSI, MACD, Bollinger Bands |
| **BTG** 📈 | BTG Pactual      | Trend Following (Equilibrado) | SMA_50, SMA_200, OBV       |

---

## 🛠️ **Instalação**

### **1. Pré-requisitos**

- Python 3.11+
- pip ou conda

### **2. Estrutura do Projeto**

```
b3_trader/
├── backend/
│   ├── __init__.py          # ⚠️ CRIAR ESTE ARQUIVO
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── services.py
│   └── ml_engine.py
├── frontend/
│   ├── statics/
│   │   ├── css/
│   │   │   ├── styles.css
│   │   │   └── history.css
│   │   └── js/
│   │       ├── script.js
│   │       ├── chart_logic.js
│   │       └── history.js
│   └── template/
│       ├── index.html
│       ├── chart.html
│       └── history.html
├── requirements.txt
├── b3_stocks.db            # Criado automaticamente
└── README.md
```

### **3. Instalação de Dependências**

```bash
# Clone ou baixe o projeto
cd b3_trader

# Crie um ambiente virtual (recomendado)
python -m venv venv

# Ative o ambiente
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### **4. Criar o arquivo `__init__.py`**

⚠️ **IMPORTANTE**: Crie o arquivo `backend/__init__.py` com o seguinte conteúdo:

```python
# backend/__init__.py
"""
Backend do DMG B3 Trader Pro
Plataforma de Inteligência Institucional para Análise de Ações
"""

__version__ = "8.0.0"
__author__ = "DMG Trading Systems"
```

---

## 🚀 **Executar o Projeto**

### **Método 1: Desenvolvimento (Recomendado)**

```bash
# Na raiz do projeto (b3_trader/)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### **Método 2: Produção**

```bash
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### **Acessar a Aplicação**

Abra o navegador em: **http://localhost:8000**

Você será redirecionado automaticamente para: **http://localhost:8000/app/**

---

## 📚 **Como Usar**

### **1. Consulta Rápida de Preço**

1. Digite o código do ativo (ex: `PETR4`, `VALE3`)
2. Clique em **Consultar**
3. Veja preço atual, mínima/máxima de 52 semanas

### **2. Análise IA com Previsão**

1. **Ativo Alvo**: Digite o código (ex: `ITUB4`)
2. **Horizonte**: Escolha 5, 20 ou 60 dias
3. **Gráfico**: Selecione timeframe (Diário, Semanal, etc)
4. **Perfil IA**: Escolha JPM, XP ou BTG
5. Clique em **Processar e Abrir Gráfico**
6. Aguarde o processamento (10-30 segundos)
7. Visualize o gráfico interativo com previsão

### **3. Histórico de Operações**

1. Clique em **📊 Histórico** no canto superior direito
2. Veja:
   - **Ranking de Assertividade**: Taxa de acerto por ativo
   - **Registro Detalhado**: Todas as análises realizadas
3. Sistema audita automaticamente previsões quando a data alvo é atingida

---

## 🔧 **Endpoints da API**

### **Base URL**: `http://localhost:8000`

| Método | Endpoint            | Descrição                    |
| ------ | ------------------- | ---------------------------- |
| GET    | `/`                 | Redireciona para a aplicação |
| GET    | `/health`           | Verifica status da API       |
| POST   | `/sync/{ticker}`    | Baixa histórico da B3        |
| GET    | `/quote/{ticker}`   | Cotação atual + 52 semanas   |
| GET    | `/analyze/{ticker}` | Análise IA com previsão      |
| GET    | `/history/stats`    | Ranking de assertividade     |
| GET    | `/history/log`      | Log detalhado de previsões   |

### **Exemplo de Uso (cURL)**

```bash
# Sincronizar dados
curl -X POST http://localhost:8000/sync/PETR4

# Análise IA
curl "http://localhost:8000/analyze/PETR4?days=5&timeframe=D&profile=JPM"

# Cotação
curl http://localhost:8000/quote/VALE3
```

---

## 🧠 **Como Funciona a IA**

### **1. Indicadores Técnicos Calculados**

- **VWAP**: Volume-Weighted Average Price
- **RSI**: Relative Strength Index
- **MACD**: Moving Average Convergence Divergence
- **MFI**: Money Flow Index
- **OBV**: On-Balance Volume
- **ATR**: Average True Range
- **Bollinger Bands**: Bandas de volatilidade
- **SMA**: Simple Moving Averages (14, 20, 50, 200)

### **2. Modelos de Machine Learning**

- **Ensemble de Classificadores**: Gradient Boosting + Random Forest
- **Ensemble de Regressores**: Gradient Boosting + Random Forest + Extra Trees
- **Voting Classifier**: Combina previsões com pesos específicos por perfil
- **Sample Weighting**: Dá mais importância a dados recentes

### **3. Lógica de Previsão**

1. Calcula todos os indicadores técnicos
2. Seleciona features baseado no perfil escolhido
3. Treina modelos com dados históricos (peso exponencial)
4. Gera 2 previsões independentes:
   - **Sinal Direcional**: COMPRA/VENDA/NEUTRO (classificação)
   - **Preço Alvo**: Valor estimado (regressão)
5. Combina ambos com nível de confiança

### **4. Auditoria Automática**

- Sistema compara previsão com preço real quando a data alvo é atingida
- Calcula erro percentual
- Considera acerto se erro < 3%
- Gera estatísticas de performance

---

## ⚠️ **Problemas Comuns e Soluções**

### **1. Erro: "No module named 'backend'"**

**Causa**: Falta o arquivo `__init__.py` na pasta backend

**Solução**:

```bash
# Crie o arquivo
touch backend/__init__.py
# Ou no Windows:
echo. > backend\__init__.py
```

### **2. Erro: "Ativo não encontrado"**

**Causa**: Ticker digitado incorretamente ou ativo não existe na B3

**Solução**: Verifique o código correto no site da B3 (ex: `PETR4`, não `PETR3`)

### **3. Erro: "Dados insuficientes para análise"**

**Causa**: Timeframe muito longo para o histórico disponível

**Solução**: Use timeframe menor (Diário ou Semanal)

### **4. Gráfico não carrega**

**Causa**: Dados não foram salvos corretamente

**Solução**:

- Certifique-se que o backend está rodando
- Verifique console do navegador (F12)
- Execute `/sync/{ticker}` primeiro

### **5. Porta 8000 já em uso**

**Solução**:

```bash
# Use outra porta
uvicorn backend.main:app --reload --port 8080
```

---

## 📊 **Tecnologias Utilizadas**

### **Backend**

- **FastAPI**: Framework web moderno
- **SQLAlchemy**: ORM para banco de dados
- **Pandas**: Manipulação de dados
- **Scikit-learn**: Machine Learning
- **yfinance**: Dados do Yahoo Finance (B3)

### **Frontend**

- **TailwindCSS**: Framework CSS
- **ApexCharts**: Gráficos interativos
- **Vanilla JavaScript**: Sem dependências pesadas

### **Banco de Dados**

- **SQLite**: Desenvolvimento (pode migrar para PostgreSQL)

---

## 🔒 **Segurança e Disclaimer**

⚠️ **AVISO IMPORTANTE**:

- Este sistema é para **fins educacionais e de pesquisa**
- **NÃO é uma recomendação de investimento**
- Mercado financeiro envolve riscos
- Consulte sempre um profissional certificado
- O desenvolvedor não se responsabiliza por perdas financeiras

---

## 🚀 **Próximos Passos / Roadmap**

- [ ] Adicionar mais indicadores (Ichimoku, Fibonacci)
- [ ] Implementar backtesting automático
- [ ] Criar relatórios PDF exportáveis
- [ ] Adicionar alertas por email/SMS
- [ ] Suporte a criptomoedas
- [ ] API de integração com corretoras
- [ ] Dashboard de múltiplos ativos
- [ ] Sistema de login e carteira virtual

---

## 📞 **Suporte**

Para dúvidas ou problemas:

1. Verifique a seção **Problemas Comuns**
2. Consulte a documentação da API em `/docs` (Swagger UI automático)
3. Abra uma issue no repositório

---

## 📄 **Licença**

MIT License - Uso livre para fins educacionais

---

## 👨‍💻 **Desenvolvido por**

**DMG Trading Systems**  
Plataforma de Inteligência Institucional  
Versão 8.0.0 - 2025

---

**⭐ Se este projeto foi útil, considere dar uma estrela!**
