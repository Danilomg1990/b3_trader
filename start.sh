#!/bin/bash

# ================================================
# DMG B3 Trader Pro - Script de Inicialização
# ================================================

echo "🚀 Iniciando DMG B3 Trader Pro..."
echo ""

# Verifica se está na raiz do projeto
if [ ! -d "backend" ]; then
    echo "❌ Erro: Execute este script na raiz do projeto (pasta b3_trader)"
    exit 1
fi

# Verifica se o __init__.py existe
if [ ! -f "backend/__init__.py" ]; then
    echo "⚠️  Criando backend/__init__.py..."
    cat > backend/__init__.py << 'EOF'
# backend/__init__.py
"""
Backend do DMG B3 Trader Pro
Plataforma de Inteligência Institucional para Análise de Ações
"""

__version__ = "8.0.0"
__author__ = "DMG Trading Systems"
EOF
    echo "✅ Arquivo criado com sucesso!"
fi

# Verifica se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo "⚠️  Ambiente virtual não encontrado. Criando..."
    python3 -m venv venv
    echo "✅ Ambiente virtual criado!"
fi

# Ativa o ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Instala/Atualiza dependências
echo "📦 Verificando dependências..."
pip install -q -r requirements.txt

echo ""
echo "✅ Ambiente configurado com sucesso!"
echo ""
echo "================================================"
echo "  DMG B3 Trader Pro - Servidor Iniciando..."
echo "================================================"
echo ""
echo "📍 URL: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"
echo ""
echo "Pressione CTRL+C para parar o servidor"
echo ""

# Inicia o servidor
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000