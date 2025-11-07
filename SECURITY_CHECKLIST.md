# 🛡️ CHECKLIST DE SEGURANÇA - FREQTRADE3

## ✅ CONFIGURAÇÕES DE SEGURANÇA IMPLEMENTADAS

### 🔐 1. Chaves API e Credenciais
```bash
# Arquivo .env (NUNCA commit no git)
# Copiar de configs/.env.example
API_KEY_BINANCE=your_key_here
API_SECRET_BINANCE=your_secret_here
API_KEY_TELEGRAM=your_bot_token
WEBHOOK_SECRET=super_secret_webhook_key
ENCRYPTION_KEY=32_characters_minimum_key
```

### 🔒 2. Configurações de Segurança
- ✅ **Rate Limiting**: Máximo 120 requests/minuto
- ✅ **HTTPS Force**: Redirecionamento automático para HTTPS
- ✅ **Headers Security**: CSP, HSTS, X-Frame-Options configurados
- ✅ **Input Validation**: Sanitização de todos os parâmetros
- ✅ **SQL Injection Protection**: Prepared statements
- ✅ **XSS Protection**: Escape de outputs HTML

### 🚨 3. Sistema de Alertas de Segurança
```python
# Alertas automáticos para:
- Login attempts > 5 em 10 minutos
- API calls > 100 em 5 minutos
- Mudanças não autorizadas no config
- Conexões suspeitas de IPs
- Tentativas de acesso a endpoints restritos
```

### 🔍 4. Monitoramento e Logs
```bash
# Logs importantes monitorados:
/logs/security.log      # Tentativas de invasão
/logs/trading.log       # Atividades de trading
/logs/api_access.log    # Acessos à API
/logs/database.log      # Operações do banco
```

### 💰 5. Proteção de Fundos
```python
# Configurações de proteção:
MAX_TRADE_AMOUNT = 0.1  # 10% máximo do saldo
STOP_LOSS_GLOBAL = -0.05  # 5% stop loss geral
DAILY_LOSS_LIMIT = 0.02   # 2% perda diária máxima
EMERGENCY_STOP = True     # Parada automática
```

## 🛠️ INSTALAÇÃO SEGURA

### 1. Clonar Repositório
```bash
git clone https://github.com/smpsandro1239/FreqTrade3.git
cd FreqTrade3
```

### 2. Setup Ambiente Seguro
```bash
# 1. Criar ambiente virtual
python -m venv freqtrade_env
source freqtrade_env/bin/activate  # Linux/Mac
# freqtrade_env\Scripts\activate  # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp configs/.env.example .env
nano .env  # Adicionar suas chaves API
```

### 3. Configurar APIs
```bash
# Binance API (OBRIGATÓRIO para trading real)
export BINANCE_API_KEY="sua_chave_aqui"
export BINANCE_API_SECRET="seu_secret_aqui"

# Telegram (opcional, para alertas)
export TELEGRAM_BOT_TOKEN="token_do_bot"
export TELEGRAM_CHAT_ID="seu_chat_id"
```

## 🚀 INÍCIO RÁPIDO (MODO SEGURO)

### 1. Teste Dry-Run (OBRIGATÓRIO)
```bash
# Sempre testar por pelo menos 7 dias antes do real
python painel_profissional_freqtrade3_clean.py --dry-run
```

### 2. Modo Produção
```bash
# Só ativar após testes bem-sucedidos
export PRODUCTION_MODE=True
python painel_profissional_freqtrade3_clean.py
```

## ⚠️ AVISOS IMPORTANTES

### 🚨 NUNCA Fazer:
- ❌ Commitar arquivos .env no git
- ❌ Usar chaves de produção em desenvolvimento
- ❌ Rodar sem dry-run primeiro
- ❌ Deixar expuesto sem HTTPS
- ❌ Ignorar alertas de segurança

### ✅ SEMPRE Fazer:
- ✅ Backup regular dos dados
- ✅ Atualizar dependências
- ✅ Monitorar logs de segurança
- ✅ Usar API keys com permissões limitadas
- ✅ Configurar stop loss adequado

## 🔧 COMANDOS ÚTEIS

```bash
# Verificar status de segurança
python tests/security_tests.py

# Backup do banco de dados
python scripts/backup.sh

# Ver logs de segurança
tail -f logs/security.log

# Parar bot em emergência
curl -X POST http://localhost:8081/api/emergency-stop
```

## 📞 SUPORTE

Em caso de dúvidas sobre segurança:
1. Verificar este documento primeiro
2. Consultar logs em `/logs/`
3. Executar `tests/security_tests.py`
4. Contatar mantenedor do projeto

---
**Última atualização**: 07/11/2025 06:00 UTC
**Versão**: 1.0.0
**Mantenha este arquivo sempre atualizado!**
