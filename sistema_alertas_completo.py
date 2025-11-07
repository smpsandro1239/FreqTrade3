#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Alertas Completo
========================================

Sistema avançado de alertas para trading automático em tempo real.

Funcionalidades:
- Alertas em tempo real via múltiplos canais
- Integração Telegram/Discord/Email
- Notificações de trading automático
- Alertas de otimização de estratégias
- Sistema de monitoramento inteligente
- Gestão de preferências de alerta

Autor: FreqTrade3 Project
Data: 2025-11-06
Versão: 1.0.0
"""

import json
import logging
import os
import smtplib
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from typing import Dict, List, Optional

import requests


@dataclass
class AlertConfig:
    """Configuração de alerta"""
    name: str
    description: str
    enabled: bool = True
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    channels: List[str] = None  # telegram, discord, email, webhook

    def __post_init__(self):
        if self.channels is None:
            self.channels = ["console"]

@dataclass
class Alert:
    """Classe de alerta"""
    id: str
    timestamp: datetime
    level: str
    title: str
    message: str
    channels: List[str]
    data: Dict = None
    sent: bool = False

    def __post_init__(self):
        if self.data is None:
            self.data = {}

class ComprehensiveAlertSystem:
    def __init__(self):
        self.alerts = []
        self.alert_configs = {}
        self.subscribers = {}  # Usuários e suas preferências
        self.webhook_urls = {}
        self.active_alerts = {}  # Alertas ativos para evitar spam
        self.rate_limits = {}  # Rate limiting por canal
        self.alert_statistics = {
            'total_sent': 0,
            'by_channel': {},
            'by_priority': {},
            'by_type': {}
        }

        self.setup_logging()
        self.load_configuration()
        self.initialize_default_configs()

    def setup_logging(self):
        """Configurar sistema de logging"""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("alerts", exist_ok=True)

        self.logger = logging.getLogger("FreqTrade3_Alerts")
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler("logs/sistema_alertas.log")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        print("[OK] Sistema de logging de alertas configurado")

    def load_configuration(self):
        """Carregar configuração de alertas"""
        config_file = "alerts/alert_config.json"

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    self.webhook_urls = data.get('webhook_urls', {})
                    self.subscribers = data.get('subscribers', {})
                    print("[OK] Configuração de alertas carregada")
            except Exception as e:
                self.logger.error(f"Erro ao carregar configuração: {e}")
                print(f"[WARNING] Erro ao carregar configuração: {e}")
        else:
            print("[INFO] Arquivo de configuração não encontrado, criando configuração padrão")
            self.save_configuration()

    def save_configuration(self):
        """Salvar configuração de alertas"""
        config_file = "alerts/alert_config.json"

        data = {
            'webhook_urls': self.webhook_urls,
            'subscribers': self.subscribers,
            'saved_at': datetime.now().isoformat()
        }

        try:
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[OK] Configuração salva: {config_file}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")

    def initialize_default_configs(self):
        """Inicializar configurações padrão de alertas"""
        default_configs = [
            AlertConfig(
                name="TRADE_ENTRY",
                description="Alerta de entrada em trade",
                priority="HIGH",
                channels=["telegram", "discord", "console"]
            ),
            AlertConfig(
                name="TRADE_EXIT",
                description="Alerta de saída de trade",
                priority="HIGH",
                channels=["telegram", "discord", "console"]
            ),
            AlertConfig(
                name="TRADE_PROFIT",
                description="Alerta de lucro significativo",
                priority="MEDIUM",
                channels=["telegram", "console"]
            ),
            AlertConfig(
                name="TRADE_LOSS",
                description="Alerta de perda significativa",
                priority="HIGH",
                channels=["telegram", "discord", "console"]
            ),
            AlertConfig(
                name="STRATEGY_ERROR",
                description="Erro em estratégia",
                priority="CRITICAL",
                channels=["telegram", "discord", "email", "console"]
            ),
            AlertConfig(
                name="OPTIMIZATION_COMPLETE",
                description="Otimização de estratégia concluída",
                priority="MEDIUM",
                channels=["telegram", "console"]
            ),
            AlertConfig(
                name="RISK_WARNING",
                description="Alerta de risco elevado",
                priority="CRITICAL",
                channels=["telegram", "discord", "email", "console"]
            ),
            AlertConfig(
                name="SYSTEM_STATUS",
                description="Status do sistema",
                priority="LOW",
                channels=["console"]
            ),
            AlertConfig(
                name="BACKTEST_COMPLETE",
                description="Backtesting concluído",
                priority="MEDIUM",
                channels=["telegram", "console"]
            ),
            AlertConfig(
                name="BOT_START",
                description="Bot iniciado",
                priority="MEDIUM",
                channels=["telegram", "console"]
            ),
            AlertConfig(
                name="BOT_STOP",
                description="Bot parado",
                priority="HIGH",
                channels=["telegram", "discord", "console"]
            )
        ]

        for config in default_configs:
            self.alert_configs[config.name] = config

        print(f"[OK] {len(default_configs)} configurações de alerta inicializadas")

    def start_alert_system(self):
        """Iniciar sistema de alertas"""
        print("\n" + "="*60)
        print("🚨 SISTEMA DE ALERTAS COMPLETO")
        print("="*60)
        print("🎯 Funcionalidades:")
        print("   - Alertas em tempo real")
        print("   - Múltiplos canais de notificação")
        print("   - Integração Telegram/Discord/Email")
        print("   - Rate limiting inteligente")
        print("   - Sistema de preferências")
        print("="*60)

        # Iniciar threads de monitoramento
        threading.Thread(target=self.monitor_trading_alerts, daemon=True).start()
        threading.Thread(target=self.monitor_system_alerts, daemon=True).start()
        threading.Thread(target=self.monitor_optimization_alerts, daemon=True).start()

        self.logger.info("Sistema de alertas iniciado")
        print("[OK] Sistema de alertas ativo")

        # Teste de sistema
        self.send_test_alert()

        # Menu principal
        self.show_alert_menu()

    def show_alert_menu(self):
        """Exibir menu de alertas"""
        while True:
            print("\n" + "-"*60)
            print("🚨 SISTEMA DE ALERTAS - OPÇÕES")
            print("-"*60)
            print("1. 📊 Ver estatísticas de alertas")
            print("2. ⚙️ Configurar canais de notificação")
            print("3. 👥 Gerenciar assinantes")
            print("4. 🧪 Enviar alerta de teste")
            print("5. 📋 Ver alertas recentes")
            print("6. 🔔 Simular evento de trading")
            print("7. 🛑 Parar sistema de alertas")
            print("-"*60)

            choice = input("Escolha uma opção (1-7): ").strip()

            if choice == '1':
                self.show_statistics()
            elif choice == '2':
                self.configure_channels()
            elif choice == '3':
                self.manage_subscribers()
            elif choice == '4':
                self.send_test_alert()
            elif choice == '5':
                self.show_recent_alerts()
            elif choice == '6':
                self.simulate_trading_event()
            elif choice == '7':
                self.stop_alert_system()
                break
            else:
                print("❌ Opção inválida")

    def send_alert(self, alert_type: str, title: str, message: str,
                   data: Dict = None, priority: str = None):
        """Enviar alerta"""
        try:
            # Verificar configuração
            config = self.alert_configs.get(alert_type)
            if not config or not config.enabled:
                return

            # Usar prioridade da configuração se não especificada
            level = priority or config.priority

            # Criar alerta
            alert = Alert(
                id=f"{alert_type}_{int(time.time())}",
                timestamp=datetime.now(),
                level=level,
                title=title,
                message=message,
                channels=config.channels,
                data=data or {}
            )

            # Adicionar à lista
            self.alerts.append(alert)

            # Enviar via cada canal
            for channel in alert.channels:
                self.send_via_channel(alert, channel)

            # Atualizar estatísticas
            self.update_statistics(alert)

            # Salvar log
            self.logger.info(f"Alerta enviado: {alert_type} - {title}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar alerta {alert_type}: {e}")

    def send_via_channel(self, alert: Alert, channel: str):
        """Enviar alerta via canal específico"""
        try:
            if channel == "console":
                self.send_to_console(alert)
            elif channel == "telegram":
                self.send_to_telegram(alert)
            elif channel == "discord":
                self.send_to_discord(alert)
            elif channel == "email":
                self.send_to_email(alert)
            elif channel == "webhook":
                self.send_to_webhook(alert)
            else:
                self.logger.warning(f"Canal desconhecido: {channel}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar alerta via {channel}: {e}")

    def send_to_console(self, alert: Alert):
        """Enviar alerta para console"""
        icon = self.get_level_icon(alert.level)
        timestamp = alert.timestamp.strftime("%H:%M:%S")

        message = f"""
{icon} ALERTA [{alert.level}] - {timestamp}
📋 Tipo: {alert.id}
📝 Título: {alert.title}
💬 Mensagem: {alert.message}
📊 Dados: {alert.data}
{'='*60}
"""

        print(message)

    def send_to_telegram(self, alert: Alert):
        """Enviar alerta via Telegram"""
        bot_token = self.webhook_urls.get('telegram_bot_token')
        chat_id = self.webhook_urls.get('telegram_chat_id')

        if not bot_token or not chat_id:
            self.logger.warning("Configuração do Telegram não encontrada")
            return

        # Rate limiting
        if not self.check_rate_limit('telegram'):
            return

        message = f"🚨 *FreqTrade3 Alert*\n\n"
        message += f"*{alert.title}*\n\n"
        message += f"{alert.message}\n\n"

        if alert.data:
            message += f"📊 *Dados:*\n"
            for key, value in alert.data.items():
                message += f"• {key}: {value}\n"

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                alert.sent = True
                self.logger.info(f"Alerta enviado para Telegram: {alert.id}")
            else:
                self.logger.error(f"Erro Telegram API: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar Telegram: {e}")

    def send_to_discord(self, alert: Alert):
        """Enviar alerta via Discord webhook"""
        webhook_url = self.webhook_urls.get('discord_webhook_url')

        if not webhook_url:
            self.logger.warning("URL do Discord webhook não encontrada")
            return

        # Rate limiting
        if not self.check_rate_limit('discord'):
            return

        # Cores baseadas na prioridade
        color_map = {
            'LOW': 0x808080,      # Cinza
            'MEDIUM': 0xFFA500,   # Laranja
            'HIGH': 0xFF0000,     # Vermelho
            'CRITICAL': 0x800080  # Roxo
        }

        embed = {
            'title': f"{self.get_level_icon(alert.level)} {alert.title}",
            'description': alert.message,
            'color': color_map.get(alert.level, 0x808080),
            'timestamp': alert.timestamp.isoformat(),
            'fields': []
        }

        if alert.data:
            for key, value in alert.data.items():
                embed['fields'].append({
                    'name': key,
                    'value': str(value),
                    'inline': True
                })

        payload = {
            'embeds': [embed]
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                alert.sent = True
                self.logger.info(f"Alerta enviado para Discord: {alert.id}")
            else:
                self.logger.error(f"Erro Discord API: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar Discord: {e}")

    def send_to_email(self, alert: Alert):
        """Enviar alerta via email"""
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASSWORD')
        recipient = os.getenv('ALERT_EMAIL_RECIPIENT', email_user)

        if not all([email_user, email_password, recipient]):
            self.logger.warning("Configuração de email não encontrada")
            return

        # Rate limiting
        if not self.check_rate_limit('email'):
            return

        try:
            msg = MimeMultipart()
            msg['From'] = email_user
            msg['To'] = recipient
            msg['Subject'] = f"[FreqTrade3] {alert.title}"

            body = f"""
FreqTrade3 Alert System

Alert Type: {alert.id}
Priority: {alert.level}
Timestamp: {alert.timestamp}

Title: {alert.title}
Message: {alert.message}

"""

            if alert.data:
                body += "Additional Data:\n"
                for key, value in alert.data.items():
                    body += f"  {key}: {value}\n"

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
            server.quit()

            alert.sent = True
            self.logger.info(f"Alerta enviado para email: {alert.id}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar email: {e}")

    def send_to_webhook(self, alert: Alert):
        """Enviar alerta via webhook genérico"""
        webhook_url = self.webhook_urls.get('generic_webhook_url')

        if not webhook_url:
            self.logger.warning("URL do webhook genérico não encontrada")
            return

        # Rate limiting
        if not self.check_rate_limit('webhook'):
            return

        payload = {
            'alert_id': alert.id,
            'timestamp': alert.timestamp.isoformat(),
            'level': alert.level,
            'title': alert.title,
            'message': alert.message,
            'data': alert.data,
            'source': 'FreqTrade3'
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code in [200, 201, 204]:
                alert.sent = True
                self.logger.info(f"Alerta enviado via webhook: {alert.id}")
            else:
                self.logger.error(f"Erro webhook API: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar webhook: {e}")

    def check_rate_limit(self, channel: str) -> bool:
        """Verificar rate limiting por canal"""
        now = time.time()

        if channel not in self.rate_limits:
            self.rate_limits[channel] = {'count': 0, 'reset': now + 60}

        limit = self.rate_limits[channel]

        if now > limit['reset']:
            # Resetar limite
            limit['count'] = 0
            limit['reset'] = now + 60

        # Limites por canal
        limits = {
            'telegram': 30,    # 30 mensagens/minuto
            'discord': 30,
            'email': 10,       # 10 emails/minuto
            'webhook': 60
        }

        max_requests = limits.get(channel, 30)

        if limit['count'] >= max_requests:
            return False

        limit['count'] += 1
        return True

    def get_level_icon(self, level: str) -> str:
        """Obter ícone para nível de alerta"""
        icons = {
            'LOW': '🔵',
            'MEDIUM': '🟡',
            'HIGH': '🟠',
            'CRITICAL': '🔴'
        }
        return icons.get(level, '⚪')

    def monitor_trading_alerts(self):
        """Monitorar alertas de trading"""
        while True:
            try:
                # Simular monitoramento de trades
                # Aqui integraria com o sistema de monitoramento da FASE 2

                time.sleep(30)  # Check a cada 30 segundos
            except Exception as e:
                self.logger.error(f"Erro no monitoramento de trading: {e}")
                time.sleep(60)

    def monitor_system_alerts(self):
        """Monitorar alertas de sistema"""
        while True:
            try:
                # Simular monitoramento de sistema
                # Aqui verificaria status do bot, conexão, etc.

                time.sleep(60)  # Check a cada minuto
            except Exception as e:
                self.logger.error(f"Erro no monitoramento de sistema: {e}")
                time.sleep(120)

    def monitor_optimization_alerts(self):
        """Monitorar alertas de otimização"""
        while True:
            try:
                # Simular monitoramento de otimização
                # Aqui verificaria status de otimizações da FASE 3

                time.sleep(300)  # Check a cada 5 minutos
            except Exception as e:
                self.logger.error(f"Erro no monitoramento de otimização: {e}")
                time.sleep(600)

    def send_test_alert(self):
        """Enviar alerta de teste"""
        test_alert = Alert(
            id="TEST_ALERT",
            timestamp=datetime.now(),
            level="MEDIUM",
            title="Teste de Alerta",
            message="Este é um alerta de teste do sistema FreqTrade3",
            channels=["console"],
            data={
                "system": "FreqTrade3",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        )

        self.alerts.append(test_alert)
        self.send_to_console(test_alert)
        self.update_statistics(test_alert)

        print("✅ Alerta de teste enviado!")

    def simulate_trading_event(self):
        """Simular evento de trading para teste"""
        print("\n🎯 SIMULAÇÃO DE EVENTOS DE TRADING")
        print("-" * 40)
        print("1. Simular entrada em trade")
        print("2. Simular saída com lucro")
        print("3. Simular stop loss")
        print("4. Simular erro de estratégia")
        print("5. Simular otimização concluída")

        choice = input("Escolha um evento (1-5): ").strip()

        if choice == '1':
            self.send_alert("TRADE_ENTRY", "Entrada em Trade",
                          "ETH/USDT - BUY - $3,250 - EMA200RSI",
                          {"pair": "ETH/USDT", "side": "BUY", "price": 3250, "strategy": "EMA200RSI"})
        elif choice == '2':
            self.send_alert("TRADE_PROFIT", "Lucro Significativo",
                          "BTC/USDT +5.2% - TAKE PROFIT ativado",
                          {"pair": "BTC/USDT", "profit": 5.2, "reason": "TAKE_PROFIT"})
        elif choice == '3':
            self.send_alert("TRADE_LOSS", "Stop Loss Ativado",
                          "ADA/USDT -2.8% - STOP LOSS executado",
                          {"pair": "ADA/USDT", "loss": -2.8, "reason": "STOP_LOSS"})
        elif choice == '4':
            self.send_alert("STRATEGY_ERROR", "Erro de Estratégia",
                          "MACDStrategy falhou - Erro de cálculo de indicadores",
                          {"strategy": "MACDStrategy", "error": "MACD calculation failed"})
        elif choice == '5':
            self.send_alert("OPTIMIZATION_COMPLETE", "Otimização Concluída",
                          "EMA200RSI otimizada com sucesso - Score: 0.847",
                          {"strategy": "EMA200RSI", "score": 0.847, "params": "Updated"})

    def show_statistics(self):
        """Exibir estatísticas de alertas"""
        print("\n📊 ESTATÍSTICAS DE ALERTAS")
        print("="*50)

        total = len(self.alerts)
        print(f"Total de alertas: {total}")

        if total == 0:
            print("Nenhum alerta enviado ainda.")
            return

        # Por canal
        print("\n📡 Por Canal:")
        for channel, count in self.alert_statistics['by_channel'].items():
            print(f"  {channel}: {count}")

        # Por prioridade
        print("\n🎯 Por Prioridade:")
        for priority, count in self.alert_statistics['by_priority'].items():
            print(f"  {priority}: {count}")

        # Por tipo
        print("\n📋 Por Tipo:")
        for alert_type, count in self.alert_statistics['by_type'].items():
            print(f"  {alert_type}: {count}")

    def update_statistics(self, alert: Alert):
        """Atualizar estatísticas"""
        self.alert_statistics['total_sent'] += 1

        # Por canal
        for channel in alert.channels:
            if channel not in self.alert_statistics['by_channel']:
                self.alert_statistics['by_channel'][channel] = 0
            self.alert_statistics['by_channel'][channel] += 1

        # Por prioridade
        priority = alert.level
        if priority not in self.alert_statistics['by_priority']:
            self.alert_statistics['by_priority'][priority] = 0
        self.alert_statistics['by_priority'][priority] += 1

        # Por tipo
        alert_type = alert.id.split('_')[0]
        if alert_type not in self.alert_statistics['by_type']:
            self.alert_statistics['by_type'][alert_type] = 0
        self.alert_statistics['by_type'][alert_type] += 1

    def configure_channels(self):
        """Configurar canais de notificação"""
        print("\n⚙️ CONFIGURAÇÃO DE CANAIS")
        print("-" * 40)
        print("1. Telegram Bot Token")
        print("2. Telegram Chat ID")
        print("3. Discord Webhook URL")
        print("4. Email SMTP Config")
        print("5. Webhook URL Genérico")
        print("6. Ver configuração atual")

        choice = input("Escolha uma opção (1-6): ").strip()

        if choice == '1':
            token = input("Telegram Bot Token: ").strip()
            self.webhook_urls['telegram_bot_token'] = token
        elif choice == '2':
            chat_id = input("Telegram Chat ID: ").strip()
            self.webhook_urls['telegram_chat_id'] = chat_id
        elif choice == '3':
            webhook = input("Discord Webhook URL: ").strip()
            self.webhook_urls['discord_webhook_url'] = webhook
        elif choice == '4':
            print("Configure as variáveis de ambiente:")
            print("EMAIL_USER, EMAIL_PASSWORD, ALERT_EMAIL_RECIPIENT")
        elif choice == '5':
            webhook = input("Webhook URL Genérico: ").strip()
            self.webhook_urls['generic_webhook_url'] = webhook
        elif choice == '6':
            print("\nConfiguração Atual:")
            for key, value in self.webhook_urls.items():
                if 'token' in key or 'password' in key:
                    print(f"  {key}: {'*' * (len(str(value)) - 4) + str(value)[-4:]}")
                else:
                    print(f"  {key}: {value}")

        if choice in ['1', '2', '3', '5']:
            self.save_configuration()
            print("✅ Configuração salva!")

    def manage_subscribers(self):
        """Gerenciar assinantes"""
        print("\n👥 GERENCIAMENTO DE ASSINANTES")
        print("-" * 40)
        print("1. Adicionar assinante")
        print("2. Ver assinantes")
        print("3. Remover assinante")

        choice = input("Escolha uma opção (1-3): ").strip()

        if choice == '1':
            name = input("Nome do assinante: ").strip()
            email = input("Email: ").strip()
            telegram_id = input("Telegram ID (opcional): ").strip()
            discord_id = input("Discord ID (opcional): ").strip()

            self.subscribers[name] = {
                'email': email,
                'telegram_id': telegram_id,
                'discord_id': discord_id,
                'preferences': {},
                'created_at': datetime.now().isoformat()
            }

            print("✅ Assinante adicionado!")

        elif choice == '2':
            if not self.subscribers:
                print("Nenhum assinante encontrado.")
            else:
                for name, data in self.subscribers.items():
                    print(f"\n👤 {name}")
                    print(f"   Email: {data['email']}")
                    print(f"   Telegram: {data['telegram_id']}")
                    print(f"   Discord: {data['discord_id']}")

        elif choice == '3':
            name = input("Nome do assinante a remover: ").strip()
            if name in self.subscribers:
                del self.subscribers[name]
                print("✅ Assinante removido!")
            else:
                print("❌ Assinante não encontrado.")

        if choice in ['1', '3']:
            self.save_configuration()

    def show_recent_alerts(self):
        """Exibir alertas recentes"""
        print("\n📋 ALERTAS RECENTES")
        print("="*50)

        if not self.alerts:
            print("Nenhum alerta encontrado.")
            return

        # Mostrar últimos 10 alertas
        recent = self.alerts[-10:]

        for alert in reversed(recent):
            icon = self.get_level_icon(alert.level)
            timestamp = alert.timestamp.strftime("%H:%M:%S")
            status = "✅" if alert.sent else "❌"

            print(f"{status} {icon} [{timestamp}] {alert.title}")
            print(f"   {alert.message}")
            print(f"   Canais: {', '.join(alert.channels)}")
            print("-" * 50)

    def stop_alert_system(self):
        """Parar sistema de alertas"""
        print("\n🛑 Parando sistema de alertas...")

        # Salvar logs
        log_file = f"alerts/alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump([asdict(alert) for alert in self.alerts], f, indent=2, default=str)

        self.logger.info(f"Sistema de alertas parado. Log salvo: {log_file}")
        print(f"✅ Log de alertas salvo: {log_file}")

def main():
    """Função principal"""
    alert_system = ComprehensiveAlertSystem()

    print("""
🚨 FREQTRADE3 - SISTEMA DE ALERTAS COMPLETO
==========================================

Este sistema implementa:
  📡 Alertas em tempo real via múltiplos canais
  🤖 Integração com Telegram/Discord/Email
  🎯 Sistema inteligente de priorização
  ⚡ Rate limiting para evitar spam
  👥 Gestão de assinantes e preferências

Iniciar sistema de alertas?""")

    choice = input("(s/n): ").lower().strip()

    if choice in ['s', 'sim', 'yes', 'y']:
        alert_system.start_alert_system()
    else:
        print("❌ Sistema de alertas cancelado")

if __name__ == "__main__":
    main()
