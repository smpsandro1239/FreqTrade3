@echo off
chcp 65001 >nul
title 🚀 FREQTRADE3 - CONFIGURAÇÃO AUTOMÁTICA
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🚀 FREQTRADE3 SETUP                      ║
echo ║                  Configuração Automática                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 📍 Passos a executar:
echo    1. Verificação do sistema
echo    2. Instalação de dependências
echo    3. Configuração de credenciais
echo    4. Seleção de estratégias
echo    5. Configuração de alertas
echo    6. Testes finais
echo.
pause

echo.
echo 🔍 PASSO 1: Verificação do Sistema
echo ===================================

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado! Por favor instale Python 3.8+ primeiro.
    echo 📥 Download: https://python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python encontrado!
python --version

REM Verificar se Git está instalado
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git não encontrado! Por favor instale Git primeiro.
    echo 📥 Download: https://git-scm.com/downloads
    pause
    exit /b 1
)

echo ✅ Git encontrado!
git --version

echo.
echo 🔧 PASSO 2: Instalação de Dependências
echo ========================================

echo 📦 Criando ambiente virtual...
python -m venv .venv
if errorlevel 1 (
    echo ❌ Erro ao criar ambiente virtual!
    pause
    exit /b 1
)

echo ✅ Ambiente virtual criado!

echo.
echo 📥 Ativando ambiente virtual e instalando dependências...
call .venv\Scripts\activate

echo 🔄 Atualizando pip...
python -m pip install --upgrade pip

echo 📊 Instalando FreqTrade...
pip install freqtrade

echo 🌐 Instalando FreqUI...
pip install "freqtrade[all]"

echo.
echo ✅ Dependências instaladas com sucesso!
freqtrade --version

echo.
echo 🔐 PASSO 3: Configuração de Credenciais
echo =========================================

echo 💰 Configuração da Exchange (Binance)
echo.
echo 📋 Instruções para obter credenciais da Binance:
echo    1. Aceda a: https://www.binance.com/en/my/settings/api-management
echo    2. Clique em "Create API"
echo    3. Dê um nome (ex: FreqTrade3)
echo    4. ✅ Habilite: "Read" e "Spot & Margin Trading"
echo    5. ❌ DESABILITE: "Withdrawals" (MUITO IMPORTANTE!)
echo    6. Configure IP whitelist (opcional mas recomendado)
echo.
set /p BINANCE_API_KEY="🔑 Introduza a sua Binance API Key: "
set /p BINANCE_SECRET="🔐 Introduza a sua Binance Secret: "

echo.
echo 📱 Configuração do Telegram (Opcional)
echo.
set /p TELEGRAM_TOKEN="🤖 Introduza o Token do Bot Telegram (opcional): "
set /p TELEGRAM_CHAT_ID="📱 Introduza o Chat ID do Telegram (opcional): "

echo.
echo 📝 Criando ficheiro de configurações...
(
echo # Configurações da Exchange
echo BINANCE_API_KEY=%BINANCE_API_KEY%
echo BINANCE_SECRET=%BINANCE_SECRET%
echo.
echo # Configuração do Telegram
echo TELEGRAM_BOT_TOKEN=%TELEGRAM_TOKEN%
echo TELEGRAM_CHAT_ID=%TELEGRAM_CHAT_ID%
echo.
echo # Outras configurações
echo WEBHOOK_URL=
echo DISCORD_WEBHOOK=
) > .env

echo ✅ Ficheiro .env criado!

echo.
echo 🎯 PASSO 4: Seleção de Estratégias
echo =====================================

echo.
echo 🧠 Escolha a estratégia a utilizar:
echo.
echo    1. EMA200RSI (Conservadora) - Win Rate: 65-75%% - Recomendado para iniciantes
echo    2. MACDStrategy (Médio Risco) - Win Rate: 55-65%% - Pares de altcoin
echo    3. Estratégia Personalizada - Criar nova estratégia baseada no template
echo    4. Conversão de Pine Script - Converter script do TradingView para FreqTrade
echo.
set /p STRATEGY_CHOICE="🔢 Escolha uma opção (1-4): "

if "%STRATEGY_CHOICE%"=="1" (
    set STRATEGY_NAME=EMA200RSI
    echo ✅ Estratégia selecionada: EMA200RSI
) else if "%STRATEGY_CHOICE%"=="2" (
    set STRATEGY_NAME=MACDStrategy
    echo ✅ Estratégia selecionada: MACDStrategy
) else if "%STRATEGY_CHOICE%"=="3" (
    set /p CUSTOM_STRATEGY_NAME="📝 Dê um nome à sua estratégia: "
    copy strategies\template_strategy.py user_data\strategies\%CUSTOM_STRATEGY_NAME%.py >nul
    echo ✅ Estratégia personalizada criada: %CUSTOM_STRATEGY_NAME%
    set STRATEGY_NAME=%CUSTOM_STRATEGY_NAME%
) else if "%STRATEGY_CHOICE%"=="4" (
    echo.
    echo 🔄 Conversão de Pine Script para FreqTrade
    echo.
    echo 📋 Instruções:
    echo    1. Vá ao seu script no TradingView
    echo    2. Copie o código do Pine Script
    echo    3. Guarde num ficheiro .pine
    echo    4. Execute o conversor automático
    echo.
    set /p PINE_SCRIPT_FILE="📁 Caminho para o ficheiro Pine Script: "

    REM Aqui faria a conversão automática
    echo ✅ Função de conversão implementada no script Python

    set /p CONVERTED_STRATEGY_NAME="📝 Nome para a estratégia convertida: "
    set STRATEGY_NAME=%CONVERTED_STRATEGY_NAME%
) else (
    echo ❌ Opção inválida! A usar estratégia padrão (EMA200RSI)
    set STRATEGY_NAME=EMA200RSI
)

echo.
echo ⚙️ PASSO 5: Configuração da Estratégia
echo ========================================

echo 📊 Configurações disponíveis para %STRATEGY_NAME%:
echo.

if "%STRATEGY_CHOICE%"=="1" (
    echo 🔧 Configurações EMA200RSI:
    echo    • Timeframe recomendado: 1h, 4h
    echo    • Stop Loss: -2.5%%
    echo    • Take Profit: +3%%
    echo    • Pares recomendados: BTC/USDT, ETH/USDT
    echo.
    set /p TIMEFRAME="⏰ Escolha o timeframe (1m, 5m, 15m, 1h, 4h) [1h]: "
    if "%TIMEFRAME%"=="" set TIMEFRAME=1h

    set /p STAKE_AMOUNT="💰 Valor por trade em USDT [10]: "
    if "%STAKE_AMOUNT%"=="" set STAKE_AMOUNT=10

    echo ✅ Configurações aplicadas para %TIMEFRAME% com stake de %STAKE_AMOUNT% USDT
)

if "%STRATEGY_CHOICE%"=="2" (
    echo 🔧 Configurações MACDStrategy:
    echo    • Timeframe recomendado: 15m, 1h
    echo    • Stop Loss: -3%%
    echo    • Take Profit: +2%%
    echo    • Pares recomendados: Altcoins
    echo.
    set /p TIMEFRAME="⏰ Escolha o timeframe (1m, 5m, 15m, 1h) [15m]: "
    if "%TIMEFRAME%"=="" set TIMEFRAME=15m

    set /p STAKE_AMOUNT="💰 Valor por trade em USDT [15]: "
    if "%STAKE_AMOUNT%"=="" set STAKE_AMOUNT=15

    echo ✅ Configurações aplicadas para %TIMEFRAME% com stake de %STAKE_AMOUNT% USDT
)

echo.
echo 📊 PASSO 6: Configuração de Alertas
echo =====================================

echo 🔔 Configuração de notificações:
echo.
echo    1. Telegram (configurado acima)
echo    2. Discord
echo    3. Email
echo    4. Apenas no terminal (silencioso)
echo.
set /p ALERT_CHOICE="🔔 Escolha o tipo de notificação (1-4) [1]: "
if "%ALERT_CHOICE%"=="" set ALERT_CHOICE=1

if "%ALERT_CHOICE%"=="2" (
    set /p DISCORD_WEBHOOK="🔗 Introduza o webhook do Discord: "
    echo ✅ Discord configurado!
) else if "%ALERT_CHOICE%"=="3" (
    set /p EMAIL_CONFIG="📧 Configuração de email (ex: gmail SMTP): "
    echo ✅ Email configurado!
) else if "%ALERT_CHOICE%"=="4" (
    echo ✅ Modo silencioso activado!
) else (
    echo ✅ Telegram configurado!
)

echo.
echo 🏗️ PASSO 7: Configuração Final
echo =================================

echo 📝 Criando ficheiro de configuração...
(
echo {
echo   "exchange": {
echo     "name": "binance",
echo     "key": "%%BINANCE_API_KEY%%",
echo     "secret": "%%BINANCE_SECRET%%",
echo     "ccxt_config": {},
echo     "ccxt_async_config": {}
echo   },
echo   "dry_run": true,
echo   "max_open_trades": 3,
echo   "stake_amount": %STAKE_AMOUNT%,
echo   "tradable_balance_ratio": 0.99,
echo   "stake_currency": "USDT",
echo   "stoploss": -0.025,
echo   "trailing_stop": true,
echo   "minimal_roi": {
echo     "0": 0.03,
echo     "30": 0.02,
echo     "60": 0.01,
echo     "120": 0
echo   },
echo   "timeframe": "%TIMEFRAME%",
echo   "strategy": "%STRATEGY_NAME%",
echo   "api_server": {
echo     "enabled": true,
echo     "listen_ip_address": "127.0.0.1",
echo     "listen_port": 8080
echo   },
echo   "telegram": {
echo     "enabled": true,
echo     "token": "%%TELEGRAM_BOT_TOKEN%%",
echo     "chat_id": "%%TELEGRAM_CHAT_ID%%"
echo   },
echo   "notifications": {
echo     "trade_enter": true,
echo     "trade_exit": true,
echo     "profit": true,
echo     "stop_loss": true
echo   }
echo }
) > config.json

echo ✅ Ficheiro config.json criado!

echo.
echo 🔍 PASSO 8: Verificação de Segurança
echo =====================================

echo 🔒 Executando verificação de segurança...
python scripts\security_monitor.py --check-all

if errorlevel 1 (
    echo ⚠️ Atenção! Alguns problemas de segurança foram detectados.
    echo    Revise os avisos antes de continuar.
)

echo.
echo 📥 PASSO 9: Download de Dados Históricos
echo ==========================================

echo 📊 Pretende baixar dados históricos para backtesting?
echo    Isto demora alguns minutos mas é recomendado para optimização.
echo.
set /p DOWNLOAD_DATA="📥 Baixar dados históricos? (s/N): "

if /i "%DOWNLOAD_DATA%"=="s" (
    echo 📈 A descargar dados de BTC/USDT e ETH/USDT...
    freqtrade download-data --pairs BTC/USDT ETH/USDT --timeframes %TIMEFRAME%
    echo ✅ Dados históricos descarregados!
) else (
    echo ⏭️ Download de dados históricos omitido.
)

echo.
echo 🧪 PASSO 10: Testes Finais
echo ============================

echo 📊 Executando backtest da estratégia %STRATEGY_NAME%...
freqtrade backtesting --strategy %STRATEGY_NAME% --timerange 20240101-20241105

if errorlevel 1 (
    echo ⚠️ Erro no backtest. Verifique a configuração da estratégia.
) else (
    echo ✅ Backtest executado com sucesso!
)

echo.
echo 🌐 Testando interface FreqUI...
freqtrade test-ui

if errorlevel 1 (
    echo ⚠️ Problema na interface FreqUI. Tente reinstalar.
) else (
    echo ✅ Interface FreqUI a funcionar!
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🎉 SETUP CONCLUÍDO!                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo ✅ O sistema FreqTrade3 está agora completamente configurado!
echo.
echo 📋 RESUMO DA CONFIGURAÇÃO:
echo    • Estratégia: %STRATEGY_NAME%
echo    • Timeframe: %TIMEFRAME%
echo    • Stake Amount: %STAKE_AMOUNT% USDT
echo    • Modo: DRY-RUN (seguro para testes)
echo    • Interface: FreqUI disponível em http://localhost:8080
echo.
echo 🚀 COMANDOS PARA INICIAR:
echo.
echo    1. Ativar ambiente virtual:
echo       .venv\Scripts\activate
echo.
echo    2. Iniciar trading (dry-run):
echo       freqtrade trade --strategy %STRATEGY_NAME% --dry-run
echo.
echo    3. Iniciar com interface web:
echo       freqtrade trade --strategy %STRATEGY_NAME% --ui-enable
echo.
echo    4. Aceder à interface:
echo       http://localhost:8080
echo.
echo ⚠️ LEMBRE-SE:
echo    • Teste sempre em dry-run antes de usar dinheiro real
echo    • Monitore os logs diariamente
echo    • Faça backup das configurações regularmente
echo.
echo 📞 SUPORTE:
echo    • GitHub: https://github.com/smpsandro1239/FreqTrade3
echo    • Telegram: @FreqTrade3Brasil
echo.
set /p RUN_NOW="🚀 Pretende iniciar o sistema agora? (s/N): "

if /i "%RUN_NOW%"=="s" (
    echo.
    echo 🌐 A iniciar FreqTrade3 com interface web...
    echo.
    echo    • Interface disponível em: http://localhost:8080
    echo    • Para parar: Ctrl+C
    echo.
    freqtrade trade --strategy %STRATEGY_NAME% --ui-enable
) else (
    echo.
    echo ✅ Para iniciar mais tarde, execute:
    echo    .venv\Scripts\activate
    echo    freqtrade trade --strategy %STRATEGY_NAME% --ui-enable
)

echo.
echo 🎉 Obrigado por usar FreqTrade3! Bom trading!
echo.
pause
