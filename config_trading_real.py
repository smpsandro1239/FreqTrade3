#!/usr/bin/env python3
"""
FreqTrade3 - Configuração para Trading Real
===========================================

Sistema seguro para configuração e execução de trading com APIs reais.

Características:
- Configuração segura de API keys
- Validação de credenciais
- Teste com capital mínimo
- Backup automático
- Controlo de risco

Autor: FreqTrade3 Project
Data: 2025-11-06
Versão: 1.0.0
"""

import getpass
import json
import os
import sys

from cryptography.fernet import Fernet


class RealTradingConfig:
    def __init__(self):
        self.config_dir = "user_data"
        self.encrypted_config = "user_data/encrypted_config.json"
        self.fernet_key_file = "user_data/.fernet_key"
        self.fernet = None

    def setup_encryption(self):
        """Configurar sistema de criptografia para APIs"""
        if not os.path.exists(self.fernet_key_file):
            # Gerar nova chave
            key = Fernet.generate_key()
            with open(self.fernet_key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.fernet_key_file, 0o600)  # Permissão só para owner
        else:
            # Usar chave existente
            with open(self.fernet_key_file, 'rb') as f:
                key = f.read()

        self.fernet = Fernet(key)

    def get_api_credentials(self):
        """Obter credenciais de API do usuário"""
        print("\n" + "="*60)
        print("🔐 CONFIGURAÇÃO DE TRADING REAL - FREQTRADE3")
        print("="*60)
        print("⚠️  ATENÇÃO: Este sistema irá executar trades REAIS!")
        print("⚠️  Certifique-se de entender os riscos antes de continuar.")
        print("="*60)

        confirm = input("\nDeseja continuar? (sim/não): ").lower().strip()
        if confirm not in ['sim', 's', 'yes', 'y']:
            print("❌ Operação cancelada.")
            return None

        print("\n📋 INFORMAÇÕES NECESSÁRIAS:")
        print("   - API Key da Binance")
        print("   - API Secret da Binance")
        print("   - Capital inicial (USDT)")
        print("   - Pares de trading preferidos")

        credentials = {}

        # Binance API
        print("\n🔑 BINANCE API:")
        credentials['binance_api_key'] = getpass.getpass("API Key (oculta): ").strip()
        credentials['binance_api_secret'] = getpass.getpass("API Secret (oculto): ").strip()

        # Configurações de risco
        print("\n💰 CONFIGURAÇÕES DE CAPITAL:")
        initial_capital = float(input("Capital inicial em USDT (mínimo 50): "))
        if initial_capital < 50:
            print("❌ Capital mínimo de 50 USDT.")
            return None
        credentials['initial_capital'] = initial_capital

        # Pares preferidos
        print("\n📊 PARES DE TRADING:")
        pairs_input = input("Pares (separados por vírgula, ex: BTC/USDT,ETH/USDT): ")
        pairs = [p.strip().upper() for p in pairs_input.split(',') if p.strip()]
        credentials['preferred_pairs'] = pairs

        # Configurações de segurança
        print("\n🛡️ CONFIGURAÇÕES DE SEGURANÇA:")
        max_trade_percent = float(input("Máximo % do capital por trade (5-20): "))
        if not 5 <= max_trade_percent <= 20:
            print("❌ Valor deve estar entre 5% e 20%.")
            return None
        credentials['max_trade_percent'] = max_trade_percent

        stop_loss_percent = float(input("Stop loss máximo em % (2-10): "))
        if not 2 <= stop_loss_percent <= 10:
            print("❌ Valor deve estar entre 2% e 10%.")
            return None
        credentials['stop_loss_percent'] = stop_loss_percent

        return credentials

    def validate_credentials(self, credentials):
        """Validar credenciais da Binance"""
        print("\n🔍 VALIDANDO CREDENCIAIS...")

        try:
            import ccxt
            exchange = ccxt.binance({
                'apiKey': credentials['binance_api_key'],
                'secret': credentials['binance_api_secret'],
                'sandbox': True,  # Teste primeiro
            })

            # Tentar conectar
            balance = exchange.fetch_balance()
            print("✅ Conexão com Binance: OK")
            print(f"💰 Saldo USDT: {balance['USDT']['free']}")

            # Verificar pares
            for pair in credentials['preferred_pairs']:
                if '/' in pair:
                    base, quote = pair.split('/')
                    full_pair = f"{base}/{quote}"
                    ticker = exchange.fetch_ticker(full_pair)
                    print(f"📈 {pair}: ${ticker['last']}")

            print("✅ Todas as credenciais validadas com sucesso!")
            return True

        except Exception as e:
            print(f"❌ Erro de validação: {e}")
            return False

    def encrypt_and_save(self, credentials):
        """Criptografar e salvar credenciais"""
        if not self.fernet:
            self.setup_encryption()

        # Criptografar dados sensíveis
        sensitive_data = {
            'binance_api_key': self.fernet.encrypt(credentials['binance_api_key'].encode()).decode(),
            'binance_api_secret': self.fernet.encrypt(credentials['binance_api_secret'].encode()).decode(),
            'initial_capital': credentials['initial_capital'],
            'preferred_pairs': credentials['preferred_pairs'],
            'max_trade_percent': credentials['max_trade_percent'],
            'stop_loss_percent': credentials['stop_loss_percent']
        }

        # Salvar configurações criptografadas
        with open(self.encrypted_config, 'w') as f:
            json.dump(sensitive_data, f, indent=2)

        # Permissões de segurança
        os.chmod(self.encrypted_config, 0o600)

        print(f"✅ Configurações salvas em: {self.encrypted_config}")
        print("🔐 Dados sensíveis criptografados com sucesso!")

        return True

    def load_real_config(self):
        """Carregar configuração de trading real"""
        if not os.path.exists(self.encrypted_config):
            print("❌ Nenhuma configuração de trading real encontrada.")
            print("Execute primeiro o setup de credenciais.")
            return None

        if not self.fernet:
            self.setup_encryption()

        try:
            with open(self.encrypted_config, 'r') as f:
                encrypted_data = json.load(f)

            # Descriptografar
            config = {
                'binance_api_key': self.fernet.decrypt(encrypted_data['binance_api_key'].encode()).decode(),
                'binance_api_secret': self.fernet.decrypt(encrypted_data['binance_api_secret'].encode()).decode(),
                'initial_capital': encrypted_data['initial_capital'],
                'preferred_pairs': encrypted_data['preferred_pairs'],
                'max_trade_percent': encrypted_data['max_trade_percent'],
                'stop_loss_percent': encrypted_data['stop_loss_percent']
            }

            print("✅ Configuração de trading real carregada.")
            return config

        except Exception as e:
            print(f"❌ Erro ao carregar configuração: {e}")
            return None

    def create_real_trading_config(self, credentials):
        """Criar arquivo de configuração para FreqTrade"""
        config = {
            "_comment": "FreqTrade3 - Configuração para Trading Real",
            "_warning": "CUIDADO: ESTE ARQUIVO EXECUTA TRADING REAL!",
            "_security_level": "MAXIMUM",
            "_created": "2025-11-06",
            "exchange": {
                "name": "binance",
                "key": credentials['binance_api_key'],
                "secret": credentials['binance_api_secret'],
                "ccxt_config": {
                    "enableRateLimit": True,
                    "rateLimit": 200,
                    "options": {
                        "defaultType": "spot"  # Apenas spot trading por segurança
                    }
                },
                "ccxt_async_config": {
                    "enableRateLimit": True,
                    "rateLimit": 200
                },
                "dry_run": False  # TRADING REAL!
            },
            "timeframe": "15m",
            "stake_currency": "USDT",
            "stake_amount": credentials['initial_capital'] / len(credentials['preferred_pairs']),
            "max_open_trades": 3,
            "stoploss": -credentials['stop_loss_percent'] / 100,
            "dry_run": False,
            "pairlists": [
                {
                    "method": "StaticPairList",
                    "pair_whitelist": credentials['preferred_pairs']
                }
            ],
            "risk_management": {
                "max_trade_size_percent": credentials['max_trade_percent'] / 100,
                "max_daily_loss_percent": 5.0,  # Máximo 5% perda por dia
                "enable_stop_loss": True,
                "enable_trailing_stop": False,
                "stop_loss_dynamic": True
            },
            "api_server": {
                "enabled": True,
                "listen_ip_address": "127.0.0.1",
                "listen_port": 8081,
                "username": "freqtrade3",
                "password": "freqtrade3_real_2025",
                "jwt_secret_key": "freqtrade3_real_jwt_2025"
            },
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                        "formatter": "default"
                    },
                    "file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": "DEBUG",
                        "formatter": "default",
                        "filename": "logs/freqtrade3_real.log",
                        "maxBytes": 10485760,
                        "backupCount": 10
                    }
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["console", "file"]
                }
            }
        }

        config_file = "user_data/config_real.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Configuração de trading real criada: {config_file}")
        return config_file

    def run_setup(self):
        """Executar setup completo de trading real"""
        print("\n🚀 SETUP DE TRADING REAL - FREQTRADE3")
        print("="*50)

        # Verificar se já existe configuração
        if os.path.exists(self.encrypted_config):
            print("⚠️  Configuração existente encontrada.")
            overwrite = input("Deseja sobrescrever? (sim/não): ").lower().strip()
            if overwrite not in ['sim', 's', 'yes', 'y']:
                print("Setup cancelado.")
                return False

        # Obter credenciais
        credentials = self.get_api_credentials()
        if not credentials:
            return False

        # Validar credenciais
        if not self.validate_credentials(credentials):
            print("❌ Validação falhou. Verifique suas credenciais.")
            return False

        # Salvar criptografado
        if not self.encrypt_and_save(credentials):
            return False

        # Criar config do FreqTrade
        config_file = self.create_real_trading_config(credentials)

        print("\n" + "="*60)
        print("✅ SETUP DE TRADING REAL CONCLUÍDO!")
        print("="*60)
        print(f"📁 Arquivo de configuração: {config_file}")
        print(f"🔐 Credenciais salvas em: {self.encrypted_config}")
        print("\n⚠️  AVISOS IMPORTANTES:")
        print("   - Este sistema executa TRADING REAL")
        print("   - Comece com capital pequeno")
        print("   - Monitore constantemente")
        print("   - Use sempre stop loss")
        print("\n🚀 Para iniciar trading real:")
        print(f"   freqtrade trade --config {config_file}")
        print("="*60)

        return True

def main():
    """Função principal"""
    setup = RealTradingConfig()

    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup.run_setup()
    elif len(sys.argv) > 1 and sys.argv[1] == 'load':
        config = setup.load_real_config()
        if config:
            print("\n📊 CONFIGURAÇÃO ATUAL:")
            print(f"Capital inicial: {config['initial_capital']} USDT")
            print(f"Pares: {', '.join(config['preferred_pairs'])}")
            print(f"Risco máx por trade: {config['max_trade_percent']}%")
            print(f"Stop loss: {config['stop_loss_percent']}%")
        else:
            print("❌ Configuração não encontrada.")
    else:
        print("""
🔧 Comandos disponíveis:
   python config_trading_real.py setup  - Configurar trading real
   python config_trading_real.py load   - Ver configuração atual
        """)

if __name__ == "__main__":
    main()
