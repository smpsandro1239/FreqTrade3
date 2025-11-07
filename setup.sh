#!/bin/bash

# ===========================================
# 🚀 SCRIPT DE INSTALAÇÃO AUTOMÁTICA - FREQTRADE3
# ===========================================
# Este script automatiza a configuração inicial do FreqTrade3
# Execute com: bash setup.sh
# ===========================================

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Função para verificar comando
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Função para gerar chave de criptografia
generate_encryption_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "default_key_32_characters_long_for_security"
}

# Função para verificar se arquivo existe
file_exists() {
    [ -f "$1" ]
}

echo "=========================================="
echo "🚀 FREQTRADE3 - INSTALAÇÃO AUTOMÁTICA"
echo "=========================================="
echo ""

# 1. Verificar pré-requisitos
log_info "Verificando pré-requisitos..."

# Verificar Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python encontrado: $PYTHON_VERSION"

    # Verificar versão mínima (3.11+)
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        log_success "Versão do Python OK (3.11+)"
    else
        log_error "Python 3.11+ é obrigatório. Versão atual: $PYTHON_VERSION"
        exit 1
    fi
else
    log_error "Python 3.11+ não encontrado. Instale primeiro."
    exit 1
fi

# Verificar Git
if command_exists git; then
    log_success "Git encontrado"
else
    log_error "Git não encontrado. Instale primeiro."
    exit 1
fi

# 2. Criar ambiente virtual
log_info "Criando ambiente virtual..."
if [ ! -d "freqtrade_env" ]; then
    python3 -m venv freqtrade_env
    log_success "Ambiente virtual criado"
else
    log_warning "Ambiente virtual já existe"
fi

# 3. Ativar ambiente virtual e instalar dependências
log_info "Ativando ambiente virtual..."
source freqtrade_env/bin/activate

log_info "Atualizando pip..."
pip install --upgrade pip

log_info "Instalando dependências..."
if file_exists "requirements.txt"; then
    pip install -r requirements.txt
    log_success "Dependências instaladas com sucesso"
else
    log_warning "requirements.txt não encontrado, pulando instalação de dependências"
fi

# 4. Criar diretórios necessários
log_info "Criando estrutura de diretórios..."
mkdir -p logs
mkdir -p data
mkdir -p user_data/strategies
mkdir -p user_data/plot_html
mkdir -p backtest_results
mkdir -p reports
mkdir -p certificates

log_success "Estrutura de diretórios criada"

# 5. Configurar arquivo .env
log_info "Configurando variáveis de ambiente..."
if [ ! -f ".env" ]; then
    if file_exists "configs/.env.example"; then
        cp configs/.env.example .env
        log_success "Arquivo .env criado a partir do template"

        # Gerar chaves de segurança
        ENCRYPTION_KEY=$(generate_encryption_key)
        WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "webhook_secret_key_for_security")

        # Atualizar chaves no .env
        if command_exists sed; then
            sed -i.bak "s/your_32_character_encryption_key_here/$ENCRYPTION_KEY/g" .env
            sed -i.bak "s/super_secret_webhook_key_123/$WEBHOOK_SECRET/g" .env
            rm .env.bak
            log_success "Chaves de segurança geradas e configuradas"
        fi

        log_warning "IMPORTANTE: Configure suas chaves API Binance no arquivo .env"
    else
        log_error "configs/.env.example não encontrado"
    fi
else
    log_warning "Arquivo .env já existe, pulando configuração"
fi

# 6. Configurar permissões
log_info "Configurando permissões..."
chmod 600 .env  # Restringir acesso ao .env
chmod +x *.sh 2>/dev/null || true
log_success "Permissões configuradas"

# 7. Verificar instalação
log_info "Verificando instalação..."

# Testar importações Python críticas
if python3 -c "import flask, pandas, numpy" 2>/dev/null; then
    log_success "Dependências Python OK"
else
    log_warning "Algumas dependências podem estar faltando"
fi

# 8. Instruções finais
echo ""
echo "=========================================="
echo "✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "=========================================="
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1. 🎯 Configure suas chaves API:"
echo "   nano .env"
echo ""
echo "2. 🔐 Configure chave da Binance:"
echo "   BINANCE_API_KEY=sua_chave_aqui"
echo "   BINANCE_API_SECRET=seu_secret_aqui"
echo ""
echo "3. 🚀 Inicie o sistema (MODO TESTE):"
echo "   source freqtrade_env/bin/activate"
echo "   python painel_profissional_freqtrade3_clean.py"
echo ""
echo "4. 🌐 Acesse a interface:"
echo "   http://localhost:8081"
echo ""
echo "📚 DOCUMENTAÇÃO:"
echo "   - README.md: Documentação principal"
echo "   - SECURITY_CHECKLIST.md: Guia de segurança"
echo "   - GUIA_INSTALACAO_COMPLETA.md: Instalação detalhada"
echo ""
echo "⚠️  LEMBRETE IMPORTANTE:"
echo "   - SEMPRE teste em modo dry-run primeiro"
echo "   - NUNCA use quantias que não pode perder"
echo "   - Configure stop loss adequados"
echo ""
log_success "Setup automático concluído! 🎉"
echo ""
echo "Para suporte, visite: https://github.com/smpsandro1239/FreqTrade3"
echo "=========================================="
