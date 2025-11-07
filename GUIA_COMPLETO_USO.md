# 📊 GUIA COMPLETO - Como Usar o FreqTrade3

## 🎯 FUNCIONALIDADES COMPLETAS DISPONÍVEIS

### 🔍 BACKTESTING (Testar Estratégias)

#### **Via Terminal:**
```bash
# Backtesting básico
freqtrade backtesting --strategy EMA200RSI --pairs BTC/USDT

# Backtesting com período específico
freqtrade backtesting --strategy EMA200RSI --pairs BTC/USDT --timerange 20251006-20251015

# Backtesting com múltiplos pares
freqtrade backtesting --strategy MACDStrategy --pairs BTC/USDT,ETH/USDT,BNB/USDT

# Resultados detalhados
freqtrade backtesting-show --strategy EMA200RSI
```

#### **Via FreqUI (Interface Web):**
1. Acesse: http://localhost:8080 (quando a FreqUI estiver ativa)
2. Vá em "Backtesting"
3. Selecione a estratégia
4. Escolha o período e pares
5. Clique "Start Backtest"

### 📈 GRÁFICOS E VISUALIZAÇÕES

#### **Gerar Gráficos via Terminal:**
```bash
# Gráfico com indicadores
freqtrade plot-dataframe --strategy EMA200RSI -p BTC/USDT --indicators1 ema_fast,ema_slow,rsi

# Gráfico com período específico
freqtrade plot-dataframe --strategy MACDStrategy -p BTC/USDT --timerange 20251006-20251015

# Abrir gráfico no navegador
# O arquivo será gerado em user_data/plot/
```

#### **Via FreqUI:**
1. Vá em "Charts" (Gráficos)
2. Selecione o par (BTC/USDT, ETH/USDT, etc.)
3. Escolha o timeframe (5m, 15m, 1h, etc.)
4. Adicione indicadores (EMA, RSI, MACD, etc.)
5. Visualize sinais de compra/venda

### 💰 REALIZAR OPERAÇÕES (COMPRAS/VENDAS)

#### **Modo Trading Real (APENAS COM API KEYS REAIS):**
```bash
# Iniciar trading com estratégia
freqtrade trade --strategy EMA200RSI --config user_data/config.json

# Trading com apenas uma estratégia
freqtrade trade --strategy MACDStrategy

# Parar o bot (Ctrl+C)
```

#### **Via FreqUI:**
1. Acesse: http://localhost:8080
2. Vá em "Trading"
3. Configure API keys (para trading real)
4. Inicie/parar o bot
5. Monitore posições em tempo real

### 📊 VER SINAIS DAS MOEDAS

#### **Via Terminal:**
```bash
# Lista de mercados disponíveis
freqtrade list-markets

# Ver dados históricos
freqtrade list-data --pairs BTC/USDT --timeframes 15m

# Ver estratégias disponíveis
freqtrade list-strategies

# Baixar dados mais recentes
freqtrade download-data --pairs BTC/USDT --timeframes 15m --timerange 20251001-
```

#### **Via FreqUI:**
1. Vá em "Markets"
2. Veja todos os pares disponíveis
3. Vá em "Analysis"
4. Veja sinais e indicadores em tempo real

### 🔧 CONFIGURAÇÕES AVANÇADAS

#### **Configuração de Estratégias:**
```python
# user_data/strategies/EMA200RSI.py
class EMA200RSI(IStrategy):
    ema_fast = IntParameter(10, 50, default=12, space='buy')
    ema_slow = IntParameter(100, 300, default=200, space='buy')
    rsi_oversold = IntParameter(10, 40, default=30, space='buy')
```

#### **Configuração de Pares:**
```json
{
  "pair_whitelist": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
  "pair_blacklist": ["BTC/PAX", "BTC/USDC"]
}
```

### 🚀 INICIAR INTERFACE FREQUI

Para usar a interface web completa, use:

```bash
# Iniciar FreqUI
freqtrade webserver --config user_data/config.json

# Depois acesse:
# http://localhost:8080
```

**Credenciais de Login (configuradas no config.json):**
- Usuário: `freqtrade3`
- Senha: `secure_password_123`

### 📱 SEÇÕES DA FREQUI

#### **Dashboard Principal:**
- Carteira atual
- Posições abertas
- P&L (lucro/perda)
- Estatísticas gerais

#### **Backtesting:**
- Histograma de resultados
- Métricas de performance
- Análise detalhada de trades

#### **Trading:**
- Posições abertas
- Histórico de trades
- Controles de start/stop

#### **Charts (Gráficos):**
- Gráficos em tempo real
- Indicadores técnicos
- Sinais de compra/venda

#### **Strategies:**
- Lista de estratégias
- Parâmetros configuráveis
- Otimização (hyperopt)

### ⚙️ COMANDOS ÚTEIS

```bash
# Ver versão
freqtrade --version

# Ver configuração atual
freqtrade show-config --config user_data/config.json

# Lista de exchanges suportadas
freqtrade list-exchanges

# Lista de timeframes
freqtrade list-timeframes

# Testar configuração
freqtrade test-pairlist --config user_data/config.json
```

### 🛡️ MODO SEGURO

**ATUALMENTE EM MODO DRY-RUN:**
- Usa dinheiro virtual ($10,000 USDT)
- Não realiza trades reais
- Perfeito para testar estratégias
- 100% seguro

### 🎯 PRÓXIMOS PASSOS:

1. **Testar backtesting**: Use os comandos acima
2. **Gerar gráficos**: Execute plot-dataframe
3. **Acessar FreqUI**: Inicie o webserver
4. **Experimentar estratégias**: Teste diferentes estratégias
5. **Configurar API keys**: Para trading real (quando quiser)

### 📞 EXEMPLO PRÁTICO COMPLETO:

```bash
# 1. Baixar dados recentes
freqtrade download-data --pairs BTC/USDT --timeframes 15m --timerange 20251001-

# 2. Fazer backtesting
freqtrade backtesting --strategy EMA200RSI --pairs BTC/USDT

# 3. Gerar gráfico
freqtrade plot-dataframe --strategy EMA200RSI -p BTC/USDT

# 4. Iniciar FreqUI
freqtrade webserver --config user_data/config.json

# 5. Acessar no navegador: http://localhost:8080
```

**🚀 SISTEMA TOTALMENTE FUNCIONAL - TODAS AS FUNCIONALIDADES DISPONÍVEIS!**
