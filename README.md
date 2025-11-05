# 🚀 FreqTrade3 - Sistema de Trading Algorítmico Avançado

<div align="center">

![FreqTrade3](https://img.shields.io/badge/FreqTrade3-v3.0-blue.svg)

![Python](https://img.shields.io/badge/Python-3.8+-green.svg)

![License](https://img.shields.io/badge/License-MIT-yellow.svg)

![Security](https://img.shields.io/badge/Security-Maximum-red.svg)

**Sistema completo de trading algorítmico com interface TradingView, backtesting avançado e máximo nível de segurança.**

[Documentação de Segurança](#-documentação-de-segurança) • [Instalação](#-instalação-rápida) • [Configuração](#-configuração-segura) • [Estratégias](#-estratégias-prontas) • [FreqUI](#-frequi-tradingview-integrado)

</div>

## 🎯 CARACTERÍSTICAS PRINCIPAIS

### 🔒 Segurança Máxima

- ✅ Templates de configuração seguros por padrão
- ✅ Proteção automática de credenciais
- ✅ Sistema de dry-run obrigatório
- ✅ Monitoramento de segurança em tempo real
- ✅ Backup automático de dados sensíveis

### 📊 Interface TradingView Integrada (FreqUI)

- 🎨 Gráficos idênticos ao TradingView
- 📈 Velas, indicadores e trades em tempo real
- 🔍 Zoom, pan e cross-hair interativo
- 📱 Interface web responsiva
- 🎯 Alertas visuais e sonoros

### 🧠 Estratégias Avançadas

- 📚 Centenas de estratégias pré-otimizadas
- 🔄 Conversor automático Pine Script → Python
- ⚡ Otimização automática de parâmetros
- 📊 Backtesting com métricas detalhadas
- 🎯 Backtesting multi-timeframe

### 🚨 Sistema de Alertas

- 🔔 Notificações em tempo real
- 📱 Telegram/Discord/Email
- 📊 Métricas de performance
- ⚠️ Alertas de risco automáticos

## 📋 PRÉ-REQUISITOS

- **Python 3.8+**
- **Sistema Operacional**: Windows 10/11, macOS 10.15+, ou Linux
- **RAM**: Mínimo 4GB (recomendado 8GB+)
- **Espaço**: 2GB livres
- **Internet**: Conexão estável (trading em tempo real)

## 🚀 INSTALAÇÃO RÁPIDA

### Opção 1: Instalação Automática (Recomendada)
```bash
# 1. Clonar repositório
git clone https://github.com/smpsandro1239/FreqTrade3.git
cd FreqTrade3

# 2. Executar instalador automático
./install.sh

# 3. Ativar ambiente virtual
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# 4. Configurar FreqUI
freqtrade install-ui

# 5. Criar configuração segura
freqtrade new-config --config config_template_dryrun.json
```

### Opção 2: Instalação Manual
```bash
# 1. Criar ambiente virtual
python -m venv freqtrade_env
source freqtrade_env/bin/activate  # Linux/Mac
# freqtrade_env\Scripts\activate   # Windows

# 2. Instalar FreqTrade
pip install -U freqtrade

# 3. Instalar FreqUI
pip install -U "freqtrade[all]"

# 4. Verificar instalação
freqtrade --version

freqtrade install-ui
```

## 🔧 CONFIGURAÇÃO SEGURA

### 1. Configuração de Segurança Básica
```bash
# Copiar template seguro
cp config_template_dryrun.json config.json

# ⚠️ IMPORTANTE: ALTERAR ANTES DE USAR!
nano config.json
```

### 2. Configuração de API (Exchange)
```json
{
  "exchange": {
    "name": "binance",
    "key": "${BINANCE_API_KEY}",
    "secret": "${BINANCE_SECRET}",
    "ccxt_config": {},
    "ccxt_async_config": {}
  },
  "dry_run": true,
  "max_open_trades": 3,
  "stake_amount": 10,
  "tradable_balance_ratio": 0.99
}
```

### 3. Variáveis de Ambiente
```bash
# Criar arquivo .env (NUNCA commit!)
cat > .env << EOF
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_SECRET=seu_secret_aqui
# Adicionar outras exchange keys conforme necessário
EOF
```

## 📊 FREQUI - TRADINGVIEW INTEGRADO

### Ativação do FreqUI
```bash
# Iniciar trading com interface web
freqtrade trade --strategy SuaEstrategia --ui-enable

# Acessar interface
# 🌐 http://localhost:8080
```

### Recursos do FreqUI

- **Charts**: Gráficos em tempo real com indicadores
- **Trades**: Histórico de trades executados
- **Dashboard**: Métricas e performance em tempo real
- **Strategies**: Gerenciamento de estratégias
- **Settings**: Configurações globais

### Configuração Avançada do FreqUI
```bash
# Personalizar porta e host
freqtrade trade --ui-enable --ui-host 0.0.0.0 --ui-port 8080

# Ativar SSL/HTTPS (produção)
freqtrade trade --ui-enable --ui-ssl
```

## 🧠 ESTRATÉGIAS PRONTAS

### Estratégias Incluídas

#### 1. EMA-200 + RSI (Conservative)

```bash
# Backtest
freqtrade backtesting --strategy EMA200RSI --timerange 20240101-20241101

# Trading com FreqUI
freqtrade trade --strategy EMA200RSI --ui-enable
```

#### 2. MACD Crossover (Medium Risk)

```bash
freqtrade backtesting --strategy MACDStrategy --timerange 20240101-20241101
```

#### 3. Bollinger Bands + Stochastic (Aggressive)

```bash
freqtrade backtesting --strategy BollingerRSI --timerange 20240101-20241101
```

### Criando Estratégias Personalizadas

#### Template Base para Nova Estratégia
```python
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import pandas as pd

class MinhaEstrategia(IStrategy):
    timeframe = '15m'

    def populate_indicators(self, df, metadata):
        # Adicionar indicadores aqui
        df['rsi'] = ta.RSI(df, timeperiod=14)
        return df

    def populate_entry_trend(self, df, metadata):
        # Lógica de entrada
        df.loc[df['rsi'] < 30, 'enter_long'] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        # Lógica de saída
        df.loc[df['rsi'] > 70, 'exit_long'] = 1
        return df
```

## 📈 BACKTESTING AVANÇADO

### Backteste Básico
```bash
# Backteste simples
freqtrade backtesting --strategy EMA200RSI

# Backteste com timerange específico
freqtrade backtesting --strategy EMA200RSI --timerange 20240101-20241101

# Backteste com dados de mercado específicos
freqtrade backtesting --strategy EMA200RSI -p BTC/USDT
```

### Otimização de Parâmetros
```bash
# Otimização automática
freqtrade optimize --strategy EMA200RSI

# Otimização com parâmetros personalizados
freqtrade optimize --strategy BollingerRSI --epochs 1000
```

### Geração de Gráficos
```bash
# Gerar gráficos de backtest
freqtrade plot-dataframe --strategy EMA200RSI -p BTC/USDT

# Gráficos com trades marcados
freqtrade plot-dataframe --strategy EMA200RSI --indicators1 ema_fast,ema_slow
```

## 🔔 SISTEMA DE ALERTAS

### Configuração de Alertas
```json
{
  "webhook": {
    "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  },
  "notifications": {
    "trade_enter": true,
    "trade_exit": true,
    "profit": true,
    "stop_loss": true
  }
}
```

### Integração com Telegram
```json
{
  "telegram": {
    "enabled": true,
    "token": "${TELEGRAM_BOT_TOKEN}",
    "chat_id": "${TELEGRAM_CHAT_ID}"
  }
}
```

## 🛠️ COMANDOS ESSENCIAIS

### Trading

```bash
# Trading em modo seguro (dry-run)
freqtrade trade --strategy EMA200RSI

# Trading com FreqUI
freqtrade trade --strategy EMA200RSI --ui-enable

# Parar trading
freqtrade stop

# Status do bot
freqtrade status
```

### Gestão de Dados

```bash
# Baixar dados históricos
freqtrade download-data --pairs BTC/USDT ETH/USDT --timeframes 1h 4h

# Limpar dados antigos
freqtrade clean-data

# Listar dados disponíveis
freqtrade list-timeframes

freqtrade list-pairs --exchange binance
```

### Backtesting e Otimização

```bash
# Backtesting completo
freqtrade backtesting --strategy-list EMA200RSI MACDStrategy

# Otimização múltipla
freqtrade optimize --strategy-list BollingerRSI --epochs 500

# Gerar relatório detalhado
freqtrade edge-position-size --strategy EMA200RSI
```

## 📚 ESTRUTURA DO PROJETO

```
FreqTrade3/
├── 📄 README.md                    # Este arquivo
├── 🔒 SECURITY.md                  # Documentação de segurança
├── 📁 configs/                     # Configurações seguras
│   ├── config_template_dryrun.json
│   ├── config_template_live.json
│   └── config_production.json
├── 📁 strategies/                  # Estratégias pré-definidas
│   ├── template_strategy.py
│   ├── EMA200RSI.py
│   ├── MACDStrategy.py
│   └── BollingerRSI.py
├── 📁 scripts/                     # Scripts de automação
│   ├── install.sh                  # Instalação automática
│   ├── backup.sh                   # Backup seguro
│   └── security_check.sh           # Verificação de segurança
├── 📁 docs/                        # Documentação completa
│   ├── USER_GUIDE.md
│   ├── API_INTEGRATION.md
│   └── TROUBLESHOOTING.md
├── 📁 user_data/                   # Dados do usuário (NUNCA commit!)
│   ├── strategies/
│   ├── data/
│   ├── notebooks/
│   └── config.json
└── 📄 .gitignore                   # Proteção de dados sensíveis
```

## ⚡ FEATURES AVANÇADAS

### 🤖 Trading Automático Multi-Exchange

- Suporte a 20+ exchanges
- Arbitragem automática
- Rebalanceamento de portfólio
- Gestão automática de risco

### 📊 Análise Técnica Avançada

- 100+ indicadores técnicos
- Análise multi-timeframe
- Detecção de padrões automatizada
- Machine Learning integrado

### 🔐 Segurança Institucional

- Criptografia de dados sensíveis
- Autenticação 2FA obrigatória
- Logs de auditoria completos
- Backup automático seguro

## 🆘 SUPORTE E TROUBLESHOOTING

### Problemas Comuns

#### Erro: "API key inválida"

```bash
# Verificar credenciais
freqtrade test-pairlist --exchange binance

# Verificar permissões da API
# Certificar-se de que Spot Trading está habilitado
```

#### Erro: "Dry run mode is disabled"

```bash
# Verificar configuração
grep "dry_run" config.json
# Deve estar: "dry_run": true
```

#### FreqUI não carrega

```bash
# Verificar instalação
freqtrade test-ui

# Reinstalar se necessário
pip install -U "freqtrade[all]"
```

### Logs e Debugging

```bash
# Ver logs em tempo real
tail -f logs/freqtrade.log

# Debug mode
freqtrade trade --strategy EMA200RSI --loglevel DEBUG

# Verificar status detalhado
freqtrade status --verbose
```

## 📞 SUPORTE

- **GitHub Issues**: [Issues](https://github.com/smpsandro1239/FreqTrade3/issues)
- **Documentação**: [Wiki](https://github.com/smpsandro1239/FreqTrade3/wiki)
- **Telegram**: @FreqTrade3Brasil
- **Discord**: [Servidor da Comunidade](https://discord.gg/freqtrade3)

## 📜 LICENÇA

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ⚖️ DISCLAIMER

**AVISO IMPORTANTE**: Este software é fornecido "como está" sem garantias. Trading algorítmico envolve riscos substanciais de perda financeira.

- **SEMPRE** use dry-run antes de trading real
- **NUNCA** invista mais do que pode perder
- **SEMPRE** configure stop-loss
- **NUNCA** pare de monitorar suas estratégias

---

<div align="center">

**⭐ Se este projeto foi útil, considere dar uma estrela! ⭐**

Desenvolvido com ❤️ pela comunidade FreqTrade3

[🔒 Segurança](#-documentação-de-segurança) | [📊 TradingView](#-frequi---tradingview-integrado) | [🧠 IA](#-features-avançadas) | [🔔 Alertas](#-sistema-de-alertas)

</div>
