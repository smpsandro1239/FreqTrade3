#!/bin/bash

# ========================================
# FREQTRADE3 - SCRIPT DE INSTALAÇÃO AUTOMÁTICA
# ========================================
# Script para instalação completa e segura do FreqTrade3
# Executar como: chmod +x install.sh && ./install.sh

set -e  # Parar se qualquer comando falhar

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner inicial
echo "================================================================"
echo "🚀 FREQTRADE3 - INSTALAÇÃO AUTOMÁTICA SEGURA"
echo "================================================================"
echo
echo "Este script irá configurar um ambiente FreqTrade3 completo e seguro."
echo "⚠️  IMPORTANTE: Use apenas capital que pode perder!"
echo

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   print_error "Este script NÃO deve ser executado como root!"
   echo "Execute como usuário normal para maior segurança."
   exit 1
fi

# Verificar sistema operacional
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    print_status "Sistema detectado: Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    print_status "Sistema detectado: macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    print_status "Sistema detectado: Windows"
else
    print_error "Sistema operacional não suportado: $OSTYPE"
    exit 1
fi

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 não encontrado!"
    echo "Por favor, instale Python 3.8+ primeiro:"
    echo "  - Linux: sudo apt update && sudo apt install python3 python3-pip"
    echo "  - macOS: brew install python3"
    echo "  - Windows: Baixe de https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_status "Python detectado: $PYTHON_VERSION"

# Verificar versão do Python
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8) ]]; then
    print_error "Python 3.8+ necessário. Versão atual: $PYTHON_VERSION"
    exit 1
fi

# Verificar se pip está disponível
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 não encontrado!"
    echo "Instale pip primeiro:"
    echo "  - Linux: sudo apt install python3-pip"
    echo "  - macOS: pip já instalado com Python3"
    exit 1
fi

print_status "pip3 detectado: $(pip3 --version)"

# Criar diretório do projeto se não existir
PROJECT_DIR=$(pwd)
print_status "Diretório do projeto: $PROJECT_DIR"

# Criar estrutura de diretórios
print_status "Criando estrutura de diretórios..."

mkdir -p user_data/{data,strategies,notebooks}
mkdir -p logs
mkdir -p backups
mkdir -p temp

print_success "Estrutura de diretórios criada"

# Criar ambiente virtual Python
print_status "Criando ambiente virtual Python..."

if [[ -d ".venv" ]]; then
    print_warning "Ambiente virtual já existe. Removendo..."
    rm -rf .venv
fi

python3 -m venv .venv
source .venv/bin/activate

print_success "Ambiente virtual criado e ativado"

# Atualizar pip no ambiente virtual
print_status "Atualizando pip..."
pip install --upgrade pip setuptools wheel

# Instalar dependências básicas do sistema
print_status "Instalando dependências do sistema..."

if [[ $OS == "linux" ]]; then
    # Verificar se é Ubuntu/Debian
    if command -v apt &> /dev/null; then
        print_status "Detectado Ubuntu/Debian"
        # Tentar instalar dependências (pode falhar se não tiver sudo)
        if sudo apt update >/dev/null 2>&1 && sudo apt install -y python3-dev python3-venv build-essential >/dev/null 2>&1; then
            print_success "Dependências do sistema instaladas"
        else
            print_warning "Não foi possível instalar dependências do sistema (sem sudo)"
        fi
    fi
fi

# Instalar FreqTrade
print_status "Instalando FreqTrade..."
pip install freqtrade

# Instalar FreqUI (interface web)
print_status "Instalando FreqUI..."
pip install "freqtrade[all]"

print_success "FreqTrade e FreqUI instalados"

# Verificar instalação do FreqTrade
print_status "Verificando instalação..."
if ! freqtrade --version >/dev/null 2>&1; then
    print_error "Erro na instalação do FreqTrade"
    exit 1
fi

FREQTRADE_VERSION=$(freqtrade --version)
print_success "FreqTrade instalado: $FREQTRADE_VERSION"

# Configurar FreqUI
print_status "Configurando FreqUI..."
freqtrade install-ui

# Criar arquivo de configuração de exemplo
print_status "Criando configuração inicial..."

if [[ ! -f "config.json" ]]; then
    if [[ -f "configs/config_template_dryrun.json" ]]; then
        cp configs/config_template_dryrun.json config.json
        print_success "Configuração dry-run criada (config.json)"
        print_warning "IMPORTANTE: Configure suas API keys antes de usar!"
    else
        freqtrade new-config --config config.json
        print_success "Configuração padrão criada"
    fi
else
    print_warning "config.json já existe, mantendo atual"
fi

# Configurar arquivo .env.example
if [[ -f "configs/.env.example" ]]; then
    cp configs/.env.example .env.example
    print_success "Arquivo .env.example criado"
    print_warning "Copie para .env e configure suas chaves API"
fi

# Tornar scripts executáveis
if [[ -f "scripts/security_monitor.py" ]]; then
    chmod +x scripts/security_monitor.py
    print_success "Permissões de scripts configuradas"
fi

# Executar verificação de segurança inicial
print_status "Executando verificação inicial de segurança..."

if [[ -f "scripts/security_monitor.py" ]]; then
    python3 scripts/security_monitor.py --check-all --output logs/security_initial.json >/dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        print_success "Verificação de segurança executada (logs/security_initial.json)"
    else
        print_warning "Problemas de segurança detectados - revisar logs/security_initial.json"
    fi
else
    print_warning "Script de segurança não encontrado"
fi

# Baixar dados históricos (opcional)
echo
read -p "Deseja baixar dados históricos para backtesting? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Baixando dados históricos (isso pode levar alguns minutos)..."

    # Baixar dados para os principais pares
    if freqtrade download-data --pairs BTC/USDT ETH/USDT --timeframes 1h 4h >/dev/null 2>&1; then
        print_success "Dados históricos baixados com sucesso"
    else
        print_warning "Erro ao baixar dados históricos (pode tentar manualmente depois)"
    fi
fi

# Testar FreqUI
print_status "Testando interface FreqUI..."
freqtrade test-ui >/dev/null 2>&1
if [[ $? -eq 0 ]]; then
    print_success "FreqUI funcionando corretamente"
else
    print_warning "FreqUI pode ter problemas - verifique logs"
fi

# Mostrar resumo final
echo
echo "================================================================"
echo "✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "================================================================"
echo
echo "📋 PRÓXIMOS PASSOS:"
echo
echo "1. 📧 CONFIGURAR API KEYS:"
echo "   cp .env.example .env"
echo "   nano .env  # Adicione suas chaves API"
echo
echo "2. 🔧 CONFIGURAR ESTRATÉGIA:"
echo "   # Edite config.json e escolha uma estratégia:"
echo "   # - template_strategy.py (básico)"
echo "   # - EMA200RSI.py (conservador)"
echo
echo "3. 🧪 TESTAR (SEMPRE PRIMEIRO!):"
echo "   source .venv/bin/activate"
echo "   freqtrade backtesting --strategy EMA200RSI"
echo "   freqtrade trade --strategy EMA200RSI --dry-run"
echo
echo "4. 🌐 ABRIR INTERFACE WEB:"
echo "   freqtrade trade --strategy EMA200RSI --ui-enable"
echo "   # Acesse: http://localhost:8080"
echo
echo "5. 📊 VERIFICAR SEGURANÇA:"
echo "   python3 scripts/security_monitor.py --check-all"
echo
echo "⚠️  AVISOS IMPORTANTES:"
echo "   • SEMPRE teste em dry-run primeiro!"
echo "   • Configure stop-loss sempre!"
echo "   • NUNCA use mais dinheiro que pode perder!"
echo "   • Monitore logs regularmente!"
echo "   • Faça backup das configurações!"
echo
echo "📞 SUPORTE:"
echo "   • GitHub: https://github.com/smpsandro1239/FreqTrade3"
echo "   • Documentação: SECURITY.md"
echo "   • Logs: ./logs/"
echo
echo "🚀 BONS TRADINGS!"
echo
print_success "FreqTrade3 instalado e pronto para uso!"
