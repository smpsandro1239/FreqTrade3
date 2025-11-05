# 🔒 DOCUMENTAÇÃO DE SEGURANÇA - FREQTRADE3

## ⚠️ AVISO IMPORTANTE DE SEGURANÇA

Este projeto implementa **trading algorítmico em tempo real** que pode resultar em **PERDAS FINANCEIRAS SIGNIFICATIVAS**.

### 🛡️ MEDIDAS DE SEGURANÇA OBRIGATÓRIAS

#### 1. CONFIGURAÇÃO INICIAL SEGURA
- [ ] **NUNCA** usar dados reais sem testes extensivos
- [ ] Configurar sempre `--dry-run` inicialmente
- [ ] Usar apenas APIs com permissões de **trading** (sem withdraw)
- [ ] Configurar limites de perda máxima
- [ ] Implementar stop-loss em todas as estratégias

#### 2. PROTEÇÃO DE CREDENCIAIS
```bash
# ❌ NUNCA fazer commit disso:
{
  "api_key": "sua_chave_real_aqui",
  "secret": "seu_segredo_real_aqui"
}

# ✅ SEMPRE usar variáveis de ambiente:
{
  "api_key": "${EXCHANGE_API_KEY}",
  "secret": "${EXCHANGE_SECRET}"
}
```

#### 3. CONFIGURAÇÕES DE RISCO CONSERVADORAS
```json
{
  "max_open_trades": 3,
  "stake_amount": 10,
  "tradable_balance_ratio": 0.99,
  "unfilledtimeout": {
    "buy": 10,
    "sell": 30
  },
  "dry_run": true
}
```

### 🔐 AUTENTICAÇÃO E CHAVES API

#### Exchange Binance (Exemplo)
```bash
# 1. Criar API Key na Binance
# 2. Configurar permissões:
#    ✓ Enable Reading
#    ✓ Enable Spot & Margin Trading
#    ✗ Enable Withdrawals (DESABILITADO)
# 3. Configurar IP whitelist (opcional mas recomendado)
```

#### Variáveis de Ambiente
```bash
# .env (NUNCA commitar)
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_SECRET=your_secret_here
EXCHANGE_PASSPHRASE=your_passphrase_here
```

### 🛠️ INSTALAÇÃO SEGURA

#### 1. Verificação do Sistema
```bash
# Verificar Python (mínimo 3.8)
python --version

# Verificar pip
pip --version

# Atualizar pip
python -m pip install --upgrade pip
```

#### 2. Instalação Isenta (Ambiente Virtual)
```bash
# Criar ambiente virtual isolado
python -m venv freqtrade_env

# Ativar ambiente virtual
# Windows:
freqtrade_env\Scripts\activate
# Linux/Mac:
source freqtrade_env/bin/activate

# Instalar FreqTrade
pip install freqtrade
```

#### 3. Configuração Inicial Segura
```bash
# Criar configuração de exemplo
freqtrade new-config

# ⚠️ ALTERAR IMEDIATAMENTE:
# 1. "dry_run": true (SEMPRE começar assim)
# 2. "max_open_trades": 1 (número baixo inicial)
# 3. "stake_amount": amount_conservativo
# 4. Configurar exchange e API keys
```

### 📊 MONITORAMENTO DE SEGURANÇA

#### 1. Logs de Segurança
```bash
# Monitorar logs em tempo real
tail -f logs/freqtrade.log

# Verificar logs de erros
grep -i error logs/freqtrade.log
grep -i "unauthorized\|failed\|timeout" logs/freqtrade.log
```

#### 2. Métricas de Risco
- [ ] **Drawdown máximo**: Não deve ultrapassar 5-10%
- [ ] **Número de trades simultâneos**: Máximo 3-5 inicialmente
- [ ] **Valor por trade**: Nunca mais de 1-2% do capital total
- [ ] **Win rate**: Monitorar se está sendo positivo

#### 3. Alertas Automáticos
```python
# Implementar alertas para:
# - Drawdown > 5%
# - 3 perdas consecutivas
# - Erro de API/conexão
# - Volume de trading anormal
```

### ⚠️ SINAIS DE ALERTA

#### 🚨 PARAR TRADING IMEDIATAMENTE SE:
1. **3+ perdas consecutivas** em estratégias testadas
2. **Drawdown > 10%** em um dia
3. **Erros de API constantes** ou timeouts
4. **Volume de trading 50%+** acima do normal
5. **Estratégia performando 50% worse** que no backtest

### 🔧 MANUTENÇÃO PREVENTIVA

#### Diária
- [ ] Verificar logs por erros
- [ ] Confirmar conexão com exchange
- [ ] Monitorar métricas de performance
- [ ] Verificar saldo e posições

#### Semanal
- [ ] Review de performance vs backtest
- [ ] Atualizar se necessário (SEMPRE testar primeiro)
- [ ] Backup de configurações e dados
- [ ] Limpeza de logs antigos

#### Mensal
- [ ] Análise completa de estratégia
- [ ] Otimização de parâmetros (se necessário)
- [ ] Review de segurança de APIs
- [ ] Atualização completa do sistema

### 🆘 PLANO DE EMERGÊNCIA

#### Se Algo der Errado:
1. **PARAR** o bot imediatamente: `freqtrade show-trades --stop`
2. **DESCONECTAR** APIs se necessário
3. **VERIFICAR** posições na exchange
4. **DOCUMENTAR** o que aconteceu
5. **ANALISAR** logs para entender o problema

#### Contatos de Emergência:
- Documentar API support da exchange
- Ter números de suporte técnico
- Backup de dispositivos de acesso

### 📋 CHECKLIST DE SEGURANÇA PRE-TRADING

**ANTES DE QUALQUER TRADING REAL:**
- [ ] Estratégia testada em dry-run por pelo menos 1 semana
- [ ] Backtest mostrando profit consistente
- [ ] Configuração de stop-loss funcionando
- [ ] Monitoramento ativo configurado
- [ ] Backup de dados e configurações feito
- [ ] APIs com permissões corretas (sem withdraw)
- [ ] Limites de perda máxima configurados
- [ ] Plano de emergência definido
- [ ] Amostra pequena testada (1-2% do capital máximo)

### 🔄 ATUALIZAÇÕES E MANUTENÇÃO

#### Antes de Atualizar:
1. **Backup completo** de user_data/ e configurações
2. **Testar** nova versão em ambiente isolado
3. **Verificar** mudanças na documentação
4. **Confirmar** compatibilidade de estratégias
5. **Testar dry-run** por alguns dias

#### Processo de Rollback:
```bash
# Se algo der errado, voltar à versão anterior:
pip install freqtrade==versão_anterior_conhecida
# Restaurar backup de configurações
# Testar novamente em dry-run
```

---

## ⚖️ RESPONSABILIDADE LEGAL

**IMPORTANTE**: Este software é fornecido "como está" sem garantias. O usuário é inteiramente responsável por:
- Todas as operações de trading realizadas
- Configurações de risco implementadas
- Monitoramento constante das operações
- Conformidade com regulamentações locais

**NUNCA invista mais do que pode perder completamente.**

---

*Última atualização: 05/11/2025*
*Versão da documentação: 1.0*
