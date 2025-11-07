# 🚀 GUIA COMPLETO DE INSTALAÇÃO - FREQTRADE3

## 🎯 Visão Geral
Este guia fornece instruções passo a passo para instalar e configurar o **FreqTrade3**, sistema profissional de trading automatizado com interface web moderna e máxima segurança.

## 📋 Pré-requisitos

### Sistema Operacional
- **Windows 10/11** (nativo)
- **macOS 10.15+**
- **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 11+

### Hardware Mínimo
- **CPU**: 2 cores, 2.0 GHz+
- **RAM**: 4GB (8GB recomendado)
- **Disco**: 2GB livre
- **Internet**: Conexão estável (50 Mbps+)

### Software Necessário
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/))
- **Editor de texto** (VS Code, Sublime, etc.)

## 🔧 Instalação Passo a Passo

### 1. Verificar Python
```bash
python --version
# Deve retornar: Python 3.11.x ou superior

# Se não tiver Python instalado:
# Windows: Baixar de https://python.org
# macOS: brew install python3
# Linux: sudo apt install python3 python3-pip python3-venv
```

### 2. Clonar Repositório
```bash
# Clonar o projeto
git clone https://github.com/smpsandro1239/FreqTrade3.git
cd FreqTrade3

# Verificar estrutura
ls -la
```

### 3. Criar Ambiente Virtual (RECOMENDADO)
```bash
# Windows
python -m venv freqtrade_env
freqtrade_env\Scripts\activate

# macOS/Linux
python3 -m venv freqtrade_env
source freqtrade_env/bin/activate

# Verificar ambiente
which python
# Deve mostrar: .../freqtrade_env/bin/python
```

### 4. Instalar Dependências
```bash
# Upgrade pip primeiro
pip install --upgrade pip

# Instalar dependências principais
pip install -r requirements.txt

# Verificar instalação
pip list | grep -E "(flask|freqtrade|pandas)"
```

### 5. Configurar Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp configs/.env.example .env

# Editar configurações
nano .env  # Linux/macOS
notepad .env  # Windows

# OU usar editor preferido
```

### 6. Configurações de Segurança (OBRIGATÓRIO)
```bash
# Configurações mínimas no .env:

# === BINANCE API (OBRIGATÓRIO PARA TRADING REAL) ===
BINANCE_API_KEY=sua_chave_api_binance
BINANCE_API_SECRET=seu_secret_binance

# === CONFIGURAÇÕES DE SEGURANÇA ===
ENCRYPTION_KEY=your_32_character_encryption_key_here
WEBHOOK_SECRET=super_secret_webhook_key
SECURITY_LEVEL=high

# === CONFIGURAÇÕES DE TRADING ===
MAX_TRADE_AMOUNT=0.1
STOP_LOSS_GLOBAL=-0.05
DAILY_LOSS_LIMIT=0.02
EMERGENCY_STOP_ENABLED=true

# === TELEGRAM (OPCIONAL) ===
TELEGRAM_BOT_TOKEN=seu_token_bot_telegram
TELEGRAM_CHAT_ID=seu_chat_id
TELEGRAM_ENABLED=true
```

## 🚀 Primeira Execução

### Modo Teste (OBRIGATÓRIO)
```bash
# SEMPRE começar com dry-run
python painel_profissional_freqtrade3_clean.py

# Acessar interface
# http://localhost:8081
```

### Verificar Funcionamento
1. **Interface carregando**: ✅ http://localhost:8081
2. **APIs respondendo**: ✅ http://localhost:8081/api/status
3. **Gráfico funcionando**: ✅ Selecionar BTC/USDT, 1h
4. **Dados reais**: ✅ BTC ~$101,000 (verificado 07/11/2025)

## 📊 Demonstração Completa

### 1. Dashboard Principal
```bash
# Acessar: http://localhost:8081

# Verificar seções:
- ✅ Status do Bot (Online/Offline)
- ✅ Balance ($10,000 USDC)
- ✅ Gráfico TradingView (BTC/USDT)
- ✅ Histórico de Trades
- ✅ Controles de Estratégia
```

### 2. Teste de APIs
```bash
# Status geral
curl http://localhost:8081/api/status

# Dados de mercado
curl "http://localhost:8081/api/market_data/BTC/USDT?timeframe=1h"

# Indicadores técnicos
curl "http://localhost:8081/api/indicators/BTC/USDT?timeframe=1h"

# Histórico de trades
curl http://localhost:8081/api/trades
```

### 3. Interface Gráfica
```
✅ Gráfico Candlestick: Barras OHLC visíveis
✅ Volume: Histograma no eixo secundário
✅ EMA 12/26: Linhas azul/vermelho
✅ RSI: Oscilador 0-100
✅ MACD: Histograma + sinal
✅ Bollinger Bands: Bandas superior/inferior
```

## 🛠️ Configuração Avançada

### Troca de Estratégias
```bash
# Via interface web:
1. Selecionar nova estratégia no dropdown
2. Clicar "Aplicar Estratégia"
3. Verificar confirmação

# Via API:
curl -X POST http://localhost:8081/api/strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "EMAStrategy"}'
```

### Backtesting
```bash
# Via interface:
1. Clicar aba "Backtesting"
2. Selecionar período: 2024-01-01 a 2024-10-01
3. Escolher estratégia
4. Clicar "Executar Backtest"

# Resultados esperados:
- Total Return: 15-25%
- Win Rate: 65-75%
- Max Drawdown: <10%
- Sharpe Ratio: >1.5
```

### Configuração de Alertas
```bash
# Telegram (opcional)
1. Criar bot no @BotFather
2. Obter token
3. Adicionar no .env
4. Reiniciar sistema

# Verificar envio:
curl -X POST http://localhost:8081/api/test-alert
```

## 🐛 Solução de Problemas

### Erro: "Port 8081 in use"
```bash
# Verificar processo
netstat -an | grep 8081

# Parar processo conflitante
pkill -f freqtrade

# OU usar porta alternativa
export PORT=8082
python painel_profissional_freqtrade3_clean.py
```

### Erro: "Module not found"
```bash
# Verificar ambiente virtual
which python
pip list

# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

### Erro: "Binance API connection failed"
```bash
# Verificar chaves API
python -c "
import os
print('API Key configured:', 'BINANCE_API_KEY' in os.environ)
print('API Secret configured:', 'BINANCE_API_SECRET' in os.environ)
"

# Testar conectividade
python -c "
import binance
client = binance.Client('test', 'test')
print('Binance client imported successfully')
"
```

### Interface não carrega
```bash
# Verificar logs
tail -f logs/webserver.log

# Verificar JavaScript
curl http://localhost:8081/static/js/main.js
# Deve retornar código JavaScript

# Testar comunicação
curl -X POST http://localhost:8081/api/status
```

## 📈 Verificação de Performance

### Métricas de Sistema
```bash
# Latência da API
time curl http://localhost:8081/api/status
# Esperado: < 200ms

# Uso de memória
ps aux | grep freqtrade
# Esperado: < 500MB

# CPU
top -p $(pgrep -f freqtrade)
# Esperado: < 10% em idle
```

### Teste de Estresse
```bash
# Teste de carga
for i in {1..100}; do
  curl http://localhost:8081/api/status &
done
wait

# Verificar se sistema mantém estabilidade
# Uptime deve ser 100%
```

## 🔒 Configurações de Produção

### HTTPS (Recomendado)
```bash
# Gerar certificado auto-assinado
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Exportar caminhos
export SSL_CERT_PATH=./cert.pem
export SSL_KEY_PATH=./key.pem

# Iniciar com HTTPS
python painel_profissional_freqtrade3_clean.py
```

### Firewall
```bash
# Ubuntu/Debian
sudo ufw allow 8081
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --add-port=8081/tcp --permanent
sudo firewall-cmd --reload
```

### Process Manager (Linux/Mac)
```bash
# Instalar PM2
npm install -g pm2

# Criar arquivo ecosystem.js
cat > ecosystem.js << EOF
module.exports = {
  apps: [{
    name: 'freqtrade3',
    script: 'python',
    args: 'painel_profissional_freqtrade3_clean.py',
    cwd: '/path/to/FreqTrade3',
    env: {
      PYTHONPATH: '/path/to/FreqTrade3'
    }
  }]
}
EOF

# Iniciar processo
pm2 start ecosystem.js
pm2 save
pm2 startup
```

## 📝 Logs e Monitoramento

### Localização dos Logs
```bash
# Logs principais
tail -f logs/trading.log      # Atividades de trading
tail -f logs/security.log     # Eventos de segurança
tail -f logs/api_access.log   # Acessos à API
tail -f logs/database.log     # Operações do banco
```

### Monitoramento em Tempo Real
```bash
# Dashboard de logs
watch -n 2 "tail -n 20 logs/*.log"

# Métricas do sistema
htop
iotop
netstat -an | grep 8081
```

## ✅ Checklist de Instalação

- [ ] ✅ Python 3.11+ instalado
- [ ] ✅ Git instalado
- [ ] ✅ Repositório clonado
- [ ] ✅ Ambiente virtual criado
- [ ] ✅ Dependências instaladas
- [ ] ✅ Arquivo .env configurado
- [ ] ✅ Chaves API configuradas
- [ ] ✅ Sistema inicia sem erros
- [ ] ✅ Interface acessível (http://localhost:8081)
- [ ] ✅ APIs respondendo
- [ ] ✅ Gráfico carregando
- [ ] ✅ Dados reais confirmados
- [ ] ✅ Logs funcionando
- [ ] ✅ Estratégias carregando
- [ ] ✅ Backtesting operacional
- [ ] ✅ Alertas configurados (se aplicável)

## 🆘 Suporte e Ajuda

### Recursos Disponíveis
- **README.md**: Documentação principal
- **SECURITY_CHECKLIST.md**: Guia de segurança completo
- **GUIA_COMPLETO_USO.md**: Manual detalhado de uso
- **Demo completa**: Interface funcional

### Contato
- **GitHub Issues**: [Reportar problemas](https://github.com/smpsandro1239/FreqTrade3/issues)
- **Wiki**: [Documentação adicional](https://github.com/smpsandro1239/FreqTrade3/wiki)

---

**🎉 Parabéns! Seu FreqTrade3 está instalado e funcionando!**

**Próximo passo**: [GUIA_COMPLETO_USO.md](GUIA_COMPLETO_USO.md) para aprender a usar todas as funcionalidades.

---
**Data**: 07/11/2025 06:04 UTC
**Versão**: 1.0.0
