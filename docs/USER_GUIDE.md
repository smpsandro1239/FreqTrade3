# 📘 GUIA DO USUÁRIO - FREQTRADE3

## 🎯 ÍNDICE

1. [Introdução](#-introdução)
2. [Instalação Rápida](#-instalação-rápida)
3. [Primeira Configuração](#-primeira-configuração)
4. [Estratégias Básicas](#-estratégias-básicas)
5. [FreqUI - Interface Web](#-frequi---interface-web)
6. [Backtesting](#-backtesting)
7. [Trading Real](#-trading-real)
8. [Monitoramento](#-monitoramento)
9. [Solução de Problemas](#-solução-de-problemas)
10. [Recursos Avançados](#-recursos-avançados)

---

## 🎯 INTRODUÇÃO

O FreqTrade3 é um sistema completo de trading algorítmico que permite:

- **Trading automatizado** com estratégias personalizáveis
- **Interface web** similar ao TradingView (FreqUI)
- **Backtesting avançado** com dados históricos
- **Máxima segurança** com templates seguros
- **Estratégias prontas** para uso imediato

### ⚠️ AVISO IMPORTANTE

**NUNCA** invista dinheiro que você não pode perder completamente.
**SEMPRE** teste estratégias em dry-run antes de usar dinheiro real.

---

## 🚀 INSTALAÇÃO RÁPIDA

### Método 1: Instalação Automática (Recomendado)

```bash
# 1. Clonar repositório
git clone https://github.com/smpsandro1239/FreqTrade3.git
cd FreqTrade3

# 2. Executar instalador
chmod +x install.sh
./install.sh

# 3. Ativar ambiente virtual
source .venv/bin/activate

# 4. Verificar instalação
freqtrade --version
freqtrade install-ui
```

### Método 2: Instalação Manual

```bash
# 1. Criar ambiente virtual
python3 -m venv freqtrade_env
source freqtrade_env/bin/activate

# 2. Instalar FreqTrade
pip install freqtrade
pip install "freqtrade[all]"

# 3. Configurar FreqUI
freqtrade install-ui

# 4. Criar configuração
freqtrade new-config
```

---

## 🔧 PRIMEIRA CONFIGURAÇÃO

### 1. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp configs/.env.example .env

# Editar com suas chaves API
nano .env
```

**Configurações essenciais no `.env`:**
```bash
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_SECRET=seu_secret_aqui
TELEGRAM_BOT_TOKEN=token_opcional
TELEGRAM_CHAT_ID=chat_id_opcional
```

### 2. Configurar Exchange (Binance)

1. **Criar API Key na Binance:**
   - Acesse [Binance API Management](https://www.binance.com/en/my/settings/api-management)
   - Crie nova API key
   - **Habilite:** Read, Spot & Margin Trading
   - **DESABILITE:** Withdrawals (NUNCA habilitar)

2. **Configurar no config.json:**
```json
{
  "exchange": {
    "name": "binance",
    "key": "${BINANCE_API_KEY}",
    "secret": "${BINANCE_SECRET}"
  },
  "dry_run": true
}
```

### 3. Testar Configuração

```bash
# Testar conexão com exchange
freqtrade test-pairlist --exchange binance

# Verificar configurações
python3 scripts/security_monitor.py --check-all
```

---

## 🧠 ESTRATÉGIAS BÁSICAS

### Estratégia 1: EMA200RSI (Conservadora)

**Características:**
- Baixo risco, alta confiabilidade
- Win rate: 65-75%
- Ideal para iniciantes
- Timeframe: 1h, 4h

```bash
# Testar estratégia
freqtrade backtesting --strategy EMA200RSI --timerange 20240101-20241101

# Trading em modo seguro
freqtrade trade --strategy EMA200RSI --dry-run
```

### Estratégia 2: Template Personalizada

```bash
# Copiar template
cp strategies/template_strategy.py user_data/strategies/MinhaEstrategia.py

# Editar estratégia
nano user_data/strategies/MinhaEstrategia.py

# Testar
freqtrade backtesting --strategy MinhaEstrategia
```

### Criar Estratégia Personalizada

```python
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import pandas as pd

class MinhaEstrategia(IStrategy):
    timeframe = '15m'

    def populate_indicators(self, df, metadata):
        # Adicionar indicadores
        df['rsi'] = ta.RSI(df, timeperiod=14)
        return df

    def populate_entry_trend(self, df, metadata):
        # Condições de entrada
        df.loc[df['rsi'] < 30, 'enter_long'] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        # Condições de saída
        df.loc[df['rsi'] > 70, 'exit_long'] = 1
        return df
```

---

## 🌐 FREQUI - INTERFACE WEB

### Ativação

```bash
# Iniciar com interface web
freqtrade trade --strategy EMA200RSI --ui-enable

# Acessar no navegador
# http://localhost:8080
```

### Funcionalidades

- **Dashboard:** Visão geral das métricas
- **Charts:** Gráficos em tempo real
- **Trades:** Histórico de operações
- **Strategies:** Gerenciamento de estratégias
- **Settings:** Configurações globais

### Configuração Avançada

```bash
# Personalizar porta e host
freqtrade trade --ui-enable --ui-host 0.0.0.0 --ui-port 8080

# Ativar SSL (produção)
freqtrade trade --ui-enable --ui-ssl
```

---

## 📈 BACKTESTING

### Backtesting Básico

```bash
# Backtesting simples
freqtrade backtesting --strategy EMA200RSI

# Com timerange específico
freqtrade backtesting --strategy EMA200RSI --timerange 20240101-20241101

# Com pares específicos
freqtrade backtesting --strategy EMA200RSI -p BTC/USDT ETH/USDT
```

### Otimização

```bash
# Otimização automática
freqtrade optimize --strategy EMA200RSI

# Com parâmetros customizados
freqtrade optimize --strategy EMA200RSI --epochs 1000

# Otimização múltipla
freqtrade optimize --strategy-list EMA200RSI MACDStrategy --epochs 500
```

### Análise de Resultados

```bash
# Gerar gráficos de resultados
freqtrade plot-dataframe --strategy EMA200RSI -p BTC/USDT

# Gerar relatório detalhado
freqtrade edge-position-size --strategy EMA200RSI
```

### Interpretação dos Resultados

**Métricas importantes:**
- **Win Rate:** % de trades vencedores
- **Profit Factor:** Razão lucro/prejuízo
- **Max Drawdown:** Maior perda consecutiva
- **Sharpe Ratio:** Retorno ajustado ao risco
- **Total Return:** Retorno total do período

---

## 💰 TRADING REAL

### ⚠️ ANTES DE COMEÇAR

1. **Teste em dry-run por pelo menos 1 semana**
2. **Configure stop-loss em todas as estratégias**
3. **Comece com valores pequenos**
4. **Monitore logs diariamente**

### Configuração para Trading Real

```bash
# 1. Editar config.json
nano config.json

# 2. Alterar configurações críticas:
{
  "dry_run": false,          # ⚠️ MUDAR PARA FALSE
  "max_open_trades": 3,      # Número conservador
  "stake_amount": 50,        # Valor por trade
  "stoploss": -0.02          # Stop loss de 2%
}

# 3. Verificar segurança
python3 scripts/security_monitor.py --check-configs

# 4. Fazer backup
./scripts/backup.sh
```

### Comandos de Trading

```bash
# Iniciar trading
freqtrade trade --strategy EMA200RSI

# Parar trading
freqtrade stop

# Ver status
freqtrade status

# Listar trades
freqtrade show-trades

# Ver profits
freqtrade profit
```

### Gestão de Risco

```python
# No config.json
{
  "max_open_trades": 3,           # Máximo 3 trades simultâneos
  "tradable_balance_ratio": 0.9,  # Usar 90% do saldo
  "stoploss": -0.02,             # Stop loss de 2%
  "trailing_stop": true,          # Trailing stop ativado
  "minimal_roi": {
    "0": 0.02,                   # 2% em 0 min
    "30": 0.01                   # 1% em 30 min
  }
}
```

---

## 📊 MONITORAMENTO

### Logs em Tempo Real

```bash
# Ver logs
tail -f logs/freqtrade.log

# Buscar erros
grep -i error logs/freqtrade.log

# Monitor de sistema
python3 scripts/security_monitor.py --check-all
```

### Alertas Automáticos

```json
// No config.json
{
  "telegram": {
    "enabled": true,
    "token": "${TELEGRAM_BOT_TOKEN}",
    "chat_id": "${TELEGRAM_CHAT_ID}"
  },
  "notifications": {
    "trade_enter": true,
    "trade_exit": true,
    "profit": true,
    "stop_loss": true
  }
}
```

### Métricas Importantes

- **Drawdown atual**
- **Número de trades abertos**
- **P&L (Profit & Loss)**
- **Win rate**
- **Tempo médio em posições**

---

## 🔧 SOLUÇÃO DE PROBLEMAS

### Problemas Comuns

#### Erro: "API key inválida"

```bash
# Verificar credenciais
freqtrade test-pairlist --exchange binance

# Soluções:
# 1. Verificar se API key está correta
# 2. Confirmar permissões na exchange
# 3. Verificar IP whitelist (se configurado)
```

#### Erro: "Dry run mode is disabled"

```bash
# Verificar config.json
grep "dry_run" config.json
# Deve estar: "dry_run": true

# Para voltar ao safe mode
freqtrade stop
nano config.json  # Alterar para dry_run: true
```

#### FreqUI não carrega

```bash
# Verificar instalação
freqtrade test-ui

# Reinstalar se necessário
pip install -U "freqtrade[all]"

# Verificar porta
netstat -tlnp | grep 8080
```

#### Estratégia não executa

```bash
# Verificar se estratégia existe
freqtrade list-strategies

# Testar estratégia
freqtrade backtesting --strategy NomeEstrategia

# Verificar erros na estratégia
freqtrade trade --strategy NomeEstrategia --loglevel DEBUG
```

### Backup e Restore

```bash
# Fazer backup
./scripts/backup.sh

# Restaurar backup
cd backups/freqtrade3_backup_YYYYMMDD_HHMMSS/
./restore.sh
```

### Logs e Debug

```bash
# Log detalhado
freqtrade trade --strategy NomeEstrategia --loglevel DEBUG

# Verificar status detalhado
freqtrade status --verbose

# Informações do sistema
python3 scripts/security_monitor.py --report
```

---

## ⚡ RECURSOS AVANÇADOS

### Estratégias Multi-Timeframe

```python
def informative_pairs(self):
    return [
        ('BTC/USDT', '1h'),  # Timeframe para análise
        ('ETH/USDT', '4h'),  # Timeframe para tendência
    ]
```

### Integração com Exchanges Múltiplas

```json
{
  "exchange": {
    "name": "binance",
    "key": "${BINANCE_API_KEY}",
    "secret": "${BINANCE_SECRET}"
  },
  "pair_whitelist": [
    "BTC/USDT", "ETH/USDT", "ADA/USDT"
  ]
}
```

### Webhooks e Notificações

```json
{
  "webhook": {
    "enabled": true,
    "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  },
  "discord": {
    "enabled": true,
    "webhook_url": "${DISCORD_WEBHOOK}"
  }
}
```

### Otimização Automática

```bash
# Otimizar parâmetros de estratégia
freqtrade optimize --strategy NomeEstrategia --epochs 1000

# Otimização com diferentes pares
freqtrade optimize --strategy NomeEstrategia --pairs BTC/USDT ETH/USDT
```

### Análise Avançada

```bash
# Plotar dados com indicadores
freqtrade plot-dataframe --strategy NomeEstrategia -p BTC/USDT

# Análise deedge (gestão de risco)
freqtrade edge-position-size --strategy NomeEstrategia
```

---

## 📞 SUPORTE E COMUNIDADE

### Recursos de Ajuda

- **GitHub Issues:** [Issues](https://github.com/smpsandro1239/FreqTrade3/issues)
- **Documentação:** [Wiki](https://github.com/smpsandro1239/FreqTrade3/wiki)
- **Telegram:** @FreqTrade3Brasil
- **Discord:** [Servidor da Comunidade](https://discord.gg/freqtrade3)

### Antes de Pedir Ajuda

1. ✅ Leia este guia completamente
2. ✅ Verifique os logs de erro
3. ✅ Execute `python3 scripts/security_monitor.py --check-all`
4. ✅ Teste em dry-run primeiro
5. ✅ Procure issues similares no GitHub

### Reportar Problemas

Ao reportar problemas, inclua:
- Sistema operacional
- Versão do Python
- Versão do FreqTrade
- Logs de erro completos
- Configuração usada
- Passos para reproduzir

---

## 📚 RECURSOS ADICIONAIS

### Links Úteis

- [Documentação Oficial FreqTrade](https://www.freqtrade.io/)
- [Lista de Estratégias](https://www.freqtrade.io/en/stable/strategy-customization/)
- [API Reference](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Backtesting Guide](https://www.freqtrade.io/en/stable/backtesting-analysis/)

### Livros Recomendados

- "Algorithmic Trading" - Ernest Chan
- "Quantitative Trading" - Ernest Chan
- "Technical Analysis of the Financial Markets" - John Murphy

### Cursos Online

- Python for Finance
- Machine Learning for Trading
- Quantitative Finance

---

## 🎓 CONCLUSÃO

Parabéns! Você agora tem um sistema completo de trading algorítmico configurado com máxima segurança.

### Próximos Passos

1. **Continue aprendendo:** Estude mais sobre estratégias e análise técnica
2. **Pratique regularmente:** Use sempre dry-run antes de dinheiro real
3. **Monitore continuamente:** Acompanhe performance e ajuste estratégias
4. **Mantenha backups:** Faça backups regulares das suas configurações
5. **Participe da comunidade:** Compartilhe experiências e aprenda com outros

### Lembre-se

- **Segurança em primeiro lugar**
- **Teste tudo antes de usar com dinheiro real**
- **Monitore suas estratégias continuamente**
- **Nunca pare de aprender**

**BONS TRADINGS E BOA SORTE! 🍀**

---

*Última atualização: 05/11/2025*
*Versão do guia: 1.0*
