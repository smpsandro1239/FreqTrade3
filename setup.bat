@echo off
REM ===========================================
REM 🚀 SCRIPT DE INSTALAÇÃO AUTOMÁTICA - FREQTRADE3
REM ===========================================
REM Este script automatiza a configuração inicial do FreqTrade3
REM Execute com: setup.bat
REM ===========================================

setlocal enabledelayedexpansion

echo ==========================================
echo 🚀 FREQTRADE3 - INSTALAÇÃO AUTOMÁTICA
echo ==========================================
echo.

REM 1. Verificar Python
echo [INFO] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python não encontrado. Instale Python 3.11+ primeiro.
    pause
    exit /b 1
) else (
    echo [SUCCESS] Python encontrado
)

REM 2. Verificar Git
echo [INFO] Verificando Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Git não encontrado. Recomenda-se instalar.
) else (
    echo [SUCCESS] Git encontrado
)

REM 3. Criar ambiente virtual
echo [INFO] Criando ambiente virtual...
if not exist "freqtrade_env" (
    python -m venv freqtrade_env
    echo [SUCCESS] Ambiente virtual criado
) else (
    echo [WARNING] Ambiente virtual já existe
)

REM 4. Ativar ambiente virtual e instalar dependências
echo [INFO] Ativando ambiente virtual...
call freqtrade_env\Scripts\activate.bat

echo [INFO] Atualizando pip...
python -m pip install --upgrade pip

echo [INFO] Instalando dependências...
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo [SUCCESS] Dependências instaladas
) else (
    echo [WARNING] requirements.txt não encontrado
)

REM 5. Criar diretórios
echo [INFO] Criando estrutura de diretórios...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "user_data\strategies" mkdir user_data\strategies
if not exist "user_data\plot_html" mkdir user_data\plot_html
if not exist "backtest_results" mkdir backtest_results
if not exist "reports" mkdir reports
if not exist "certificates" mkdir certificates
echo [SUCCESS] Estrutura criada

REM 6. Configurar .env
echo [INFO] Configurando variáveis de ambiente...
if not exist ".env" (
    if exist "configs\.env.example" (
        copy "configs\.env.example" ".env"
        echo [SUCCESS] Arquivo .env criado
        echo [WARNING] IMPORTANTE: Configure suas chaves API Binance no arquivo .env
    ) else (
        echo [ERROR] configs\.env.example não encontrado
    )
) else (
    echo [WARNING] Arquivo .env já existe
)

echo.
echo ==========================================
echo ✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!
echo ==========================================
echo.
echo 📋 PRÓXIMOS PASSOS:
echo.
echo 1. 🎯 Configure suas chaves API:
echo    editar .env
echo.
echo 2. 🔐 Configure chave da Binance:
echo    BINANCE_API_KEY=sua_chave_aqui
echo    BINANCE_API_SECRET=seu_secret_aqui
echo.
echo 3. 🚀 Inicie o sistema (MODO TESTE):
echo    freqtrade_env\Scripts\activate.bat
echo    python painel_profissional_freqtrade3_clean.py
echo.
echo 4. 🌐 Acesse a interface:
echo    http://localhost:8081
echo.
echo 📚 DOCUMENTAÇÃO:
echo    - README.md: Documentação principal
echo    - SECURITY_CHECKLIST.md: Guia de segurança
echo    - GUIA_INSTALACAO_COMPLETA.md: Instalação detalhada
echo.
echo ⚠️  LEMBRETE IMPORTANTE:
echo    - SEMPRE teste em modo dry-run primeiro
echo    - NUNCA use quantias que não pode perder
echo    - Configure stop loss adequados
echo.
echo [SUCCESS] Setup automático concluído! 🎉
echo.
echo Para suporte, visite: https://github.com/smpsandro1239/FreqTrade3
echo ==========================================

pause
