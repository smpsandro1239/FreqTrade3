#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📱 SISTEMA DE NOTIFICAÇÕES INTELIGENTES - FREQTRADE3
Notificações multi-canal com IA e personalização avançada
"""

import asyncio
import json
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from typing import Callable, Dict, List, Optional

import aiohttp
import requests
from jinja2 import Template


class NotificationChannel(Enum):
    """Canais de notificação"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    SMS = "sms"
    PUSH = "pushbullet"
    WEBHOOK = "webhook"
    DISCORD_WEBHOOK = "discord_webhook"

class NotificationPriority(Enum):
    """Prioridades de notificação"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class NotificationRule:
    """Regra de notificação"""
    id: str
    name: str
    trigger_condition: str
    channels: List[NotificationChannel]
    template: str
    priority: NotificationPriority
    cooldown_minutes: int = 60
    is_active: bool = True
    metadata: Dict = None

@dataclass
class NotificationEvent:
    """Evento de notificação"""
    id: str
    rule_id: str
    title: str
    message: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    timestamp: datetime
    metadata: Dict
    is_sent: bool = False

class SmartNotificationManager:
    """Gerenciador inteligente de notificações"""

    def __init__(self, config_file='config/notifications.json'):
        self.config = self.load_notification_config(config_file)
        self.notification_history = []
        self.rate_limits = {}
        self.templates = self.load_templates()

    def load_notification_config(self, config_file):
        """Carregar configuração de notificações"""
        default_config = {
            "telegram": {
                "bot_token": "",
                "chat_id": "",
                "enabled": False
            },
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_emails": [],
                "enabled": False
            },
            "discord": {
                "webhook_url": "",
                "enabled": False
            },
            "slack": {
                "webhook_url": "",
                "enabled": False
            },
            "webhooks": {
                "trading_alerts": "",
                "risk_alerts": "",
                "system_alerts": "",
                "enabled": False
            },
            "rules": []
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return {**default_config, **config}
            else:
                return default_config
        except Exception as e:
            print(f"❌ Erro ao carregar config: {e}, usando padrão")
            return default_config

    def load_templates(self):
        """Carregar templates de notificação"""
        return {
            "trade_executed": Template("""
🎯 **TRADE EXECUTADO**
Símbolo: {{ symbol }}
Ação: {{ action }}
Quantidade: {{ quantity }}
Preço: ${{ price }}
P&L: ${{ pnl }}
Hora: {{ timestamp }}
            """),

            "profit_target": Template("""
🎉 **OBJETIVO DE LUCRO ATINGIDO!**
Símbolo: {{ symbol }}
Lucro: ${{ profit }}
Percentual: {{ percentage }}%
🎯 Meta: ${{ target }}
            """),

            "stop_loss": Template("""
🛑 **STOP LOSS ATIVADO**
Símbolo: {{ symbol }}
Perda: ${{ loss }}
Percentual: {{ percentage }}%
💰 Saldo: ${{ balance }}
            """),

            "high_risk": Template("""
⚠️ **ALERTA DE ALTO RISCO**
Nível: {{ risk_level }}
Motivo: {{ reason }}
Score: {{ risk_score }}
💡 Ação recomendada: {{ recommendation }}
            """),

            "system_error": Template("""
🚨 **ERRO DO SISTEMA**
Componente: {{ component }}
Erro: {{ error }}
Timestamp: {{ timestamp }}
📋 Status: {{ status }}
            """),

            "market_opportunity": Template("""
🚀 **OPORTUNIDADE DE MERCADO**
Símbolo: {{ symbol }}
Sinal: {{ signal }}
Confiança: {{ confidence }}%
Preço: ${{ price }}
📊 Indicadores: {{ indicators }}
            """),

            "portfolio_update": Template("""
📈 **ATUALIZAÇÃO DE PORTFÓLIO**
Valor Total: ${{ total_value }}
P&L 24h: ${{ daily_pnl }} ({{ daily_change }}%)
Melhor Ativo: {{ best_performer }} (+{{ best_gain }}%)
Pior Ativo: {{ worst_performer }} ({{ worst_loss }}%)
            """),

            "strategy_performance": Template("""
📊 **PERFORMANCE DA ESTRATÉGIA**
Nome: {{ strategy_name }}
Período: {{ period }}
Win Rate: {{ win_rate }}%
ROI: {{ roi }}%
Trades: {{ total_trades }}
Lucro: ${{ profit }}
            """)
        }

    async def send_telegram(self, message: str, priority: NotificationPriority) -> bool:
        """Enviar notificação via Telegram"""
        if not self.config['telegram']['enabled'] or not self.config['telegram']['bot_token']:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.config['telegram']['bot_token']}/sendMessage"

            # Mapear prioridade para emoji
            priority_emoji = {
                NotificationPriority.LOW: "💬",
                NotificationPriority.MEDIUM: "📢",
                NotificationPriority.HIGH: "⚠️",
                NotificationPriority.CRITICAL: "🚨",
                NotificationPriority.EMERGENCY: "🆘"
            }

            formatted_message = f"{priority_emoji.get(priority, '📧')} {message}"

            payload = {
                'chat_id': self.config['telegram']['chat_id'],
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    return response.status == 200

        except Exception as e:
            print(f"❌ Erro Telegram: {e}")
            return False

    def send_email(self, subject: str, message: str, priority: NotificationPriority) -> bool:
        """Enviar notificação via Email"""
        if not self.config['email']['enabled'] or not self.config['email']['username']:
            return False

        try:
            # Configurar email
            msg = MimeMultipart()
            msg['From'] = self.config['email']['from_email']
            msg['To'] = ', '.join(self.config['email']['to_emails'])
            msg['Subject'] = f"[FreqTrade3-{priority.value.upper()}] {subject}"

            # Corpo do email
            priority_color = {
                NotificationPriority.LOW: "#008000",      # Verde
                NotificationPriority.MEDIUM: "#FF8C00",   # Laranja
                NotificationPriority.HIGH: "#FF0000",     # Vermelho
                NotificationPriority.CRITICAL: "#8B0000", # Vermelho escuro
                NotificationPriority.EMERGENCY: "#000000" # Preto
            }

            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="background-color: {priority_color.get(priority, '#333')}; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0;">
                            <h2>FreqTrade3 Notification</h2>
                        </div>
                        <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 5px 5px;">
                            <h3>{subject}</h3>
                            <p style="white-space: pre-line;">{message}</p>
                            <hr style="margin: 20px 0;">
                            <p style="font-size: 12px; color: #666;">
                                Enviado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br>
                                Prioridade: {priority.value.upper()}
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """

            msg.attach(MimeText(html_body, 'html'))

            # Enviar email
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['username'], self.config['email']['password'])
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            print(f"❌ Erro Email: {e}")
            return False

    async def send_discord(self, message: str, priority: NotificationPriority) -> bool:
        """Enviar notificação via Discord"""
        if not self.config['discord']['enabled'] or not self.config['discord']['webhook_url']:
            return False

        try:
            # Mapear cores para Discord (decimal)
            priority_colors = {
                NotificationPriority.LOW: 0x00FF00,      # Verde
                NotificationPriority.MEDIUM: 0xFF8C00,   # Laranja
                NotificationPriority.HIGH: 0xFF0000,     # Vermelho
                NotificationPriority.CRITICAL: 0x8B0000, # Vermelho escuro
                NotificationPriority.EMERGENCY: 0x000000 # Preto
            }

            payload = {
                "embeds": [{
                    "title": "FreqTrade3 Alert",
                    "description": message,
                    "color": priority_colors.get(priority, 0x7289DA),
                    "timestamp": datetime.now().isoformat(),
                    "footer": {
                        "text": f"Priority: {priority.value.upper()}"
                    }
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.config['discord']['webhook_url'], json=payload) as response:
                    return response.status == 204

        except Exception as e:
            print(f"❌ Erro Discord: {e}")
            return False

    async def send_webhook(self, message: str, priority: NotificationPriority, webhook_type: str = "trading_alerts") -> bool:
        """Enviar notificação via Webhook genérico"""
        webhook_url = self.config['webhooks'].get(webhook_type, "")
        if not webhook_url or not self.config['webhooks']['enabled']:
            return False

        try:
            payload = {
                "timestamp": datetime.now().isoformat(),
                "priority": priority.value,
                "message": message,
                "source": "FreqTrade3",
                "type": webhook_type
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200

        except Exception as e:
            print(f"❌ Erro Webhook: {e}")
            return False

    def should_send_notification(self, rule: NotificationRule) -> bool:
        """Verificar se deve enviar notificação baseado no cooldown"""
        now = datetime.now()
        last_sent = self.rate_limits.get(rule.id)

        if last_sent is None:
            return True

        cooldown_end = last_sent + timedelta(minutes=rule.cooldown_minutes)
        return now >= cooldown_end

    async def send_notification(self, event: NotificationEvent) -> bool:
        """Enviar notificação através dos canais configurados"""
        success_count = 0
        total_channels = len(event.channels)

        # Enviar para cada canal
        for channel in event.channels:
            try:
                if channel == NotificationChannel.TELEGRAM:
                    if await self.send_telegram(event.message, event.priority):
                        success_count += 1

                elif channel == NotificationChannel.EMAIL:
                    if self.send_email(event.title, event.message, event.priority):
                        success_count += 1

                elif channel == NotificationChannel.DISCORD:
                    if await self.send_discord(event.message, event.priority):
                        success_count += 1

                elif channel == NotificationChannel.WEBHOOK:
                    if await self.send_webhook(event.message, event.priority, "trading_alerts"):
                        success_count += 1

            except Exception as e:
                print(f"❌ Erro ao enviar para {channel.value}: {e}")

        # Marcar como enviado se pelo menos um canal funcionou
        event.is_sent = success_count > 0

        # Salvar no histórico
        self.notification_history.append(event)

        # Atualizar rate limit
        self.rate_limits[event.rule_id] = datetime.now()

        return event.is_sent

    def create_notification_event(self, rule: NotificationRule, template_name: str,
                                data: Dict, priority: NotificationPriority = NotificationPriority.MEDIUM) -> NotificationEvent:
        """Criar evento de notificação usando template"""
        if template_name in self.templates:
            template = self.templates[template_name]
            message = template.render(**data)
        else:
            message = str(data)

        # Título baseado no template
        title_map = {
            "trade_executed": "Trade Executado",
            "profit_target": "Objetivo Atingido",
            "stop_loss": "Stop Loss",
            "high_risk": "Alto Risco",
            "system_error": "Erro do Sistema",
            "market_opportunity": "Oportunidade",
            "portfolio_update": "Atualização do Portfólio",
            "strategy_performance": "Performance"
        }

        title = title_map.get(template_name, "Notificação FreqTrade3")

        return NotificationEvent(
            id=f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            rule_id=rule.id,
            title=title,
            message=message,
            priority=priority,
            channels=rule.channels,
            timestamp=datetime.now(),
            metadata=data
        )

    def process_trading_event(self, event_type: str, data: Dict) -> bool:
        """Processar evento de trading e enviar notificações"""
        # Buscar regras aplicáveis
        applicable_rules = []
        for rule in self.config.get('rules', []):
            if rule.get('trigger_condition') == event_type and rule.get('is_active', True):
                applicable_rules.append(NotificationRule(**rule))

        if not applicable_rules:
            return False

        success = True
        for rule in applicable_rules:
            if not self.should_send_notification(rule):
                continue

            # Determinar template e prioridade baseado no evento
            template_map = {
                'trade_executed': ('trade_executed', NotificationPriority.MEDIUM),
                'profit_target': ('profit_target', NotificationPriority.HIGH),
                'stop_loss': ('stop_loss', NotificationPriority.HIGH),
                'high_risk': ('high_risk', NotificationPriority.CRITICAL),
                'system_error': ('system_error', NotificationPriority.EMERGENCY),
                'market_opportunity': ('market_opportunity', NotificationPriority.MEDIUM)
            }

            if event_type in template_map:
                template_name, priority = template_map[event_type]
                event = self.create_notification_event(rule, template_name, data, priority)

                # Enviar notificação
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Se já está rodando, usar create_task
                    asyncio.create_task(self.send_notification(event))
                else:
                    # Se não está rodando, executar de forma síncrona
                    success = success and loop.run_until_complete(self.send_notification(event))

        return success

    def get_notification_history(self, hours: int = 24) -> List[Dict]:
        """Obter histórico de notificações"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_notifications = [
            {
                'id': event.id,
                'title': event.title,
                'message': event.message[:100] + '...' if len(event.message) > 100 else event.message,
                'priority': event.priority.value,
                'channels': [ch.value for ch in event.channels],
                'timestamp': event.timestamp.isoformat(),
                'sent': event.is_sent
            }
            for event in self.notification_history
            if event.timestamp >= cutoff
        ]

        return recent_notifications

    def add_notification_rule(self, rule: NotificationRule):
        """Adicionar nova regra de notificação"""
        if 'rules' not in self.config:
            self.config['rules'] = []

        self.config['rules'].append({
            'id': rule.id,
            'name': rule.name,
            'trigger_condition': rule.trigger_condition,
            'channels': [ch.value for ch in rule.channels],
            'template': rule.template,
            'priority': rule.priority.value,
            'cooldown_minutes': rule.cooldown_minutes,
            'is_active': rule.is_active,
            'metadata': rule.metadata or {}
        })

    def save_config(self, config_file='config/notifications.json'):
        """Salvar configuração"""
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

def create_default_notification_rules():
    """Criar regras padrão de notificação"""
    return [
        NotificationRule(
            id="trade_notification",
            name="Notificação de Trade",
            trigger_condition="trade_executed",
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
            template="trade_executed",
            priority=NotificationPriority.MEDIUM,
            cooldown_minutes=5
        ),
        NotificationRule(
            id="profit_target",
            name="Objetivo de Lucro",
            trigger_condition="profit_target",
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.DISCORD],
            template="profit_target",
            priority=NotificationPriority.HIGH,
            cooldown_minutes=30
        ),
        NotificationRule(
            id="high_risk_alert",
            name="Alerta de Alto Risco",
            trigger_condition="high_risk",
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL, NotificationChannel.SLACK],
            template="high_risk",
            priority=NotificationPriority.CRITICAL,
            cooldown_minutes=15
        )
    ]

def demo_notifications():
    """Demonstração do sistema de notificações"""
    print("📱 DEMO - Sistema de Notificações Inteligentes")
    print("=" * 50)

    # Inicializar gerenciador
    notifier = SmartNotificationManager()

    # Adicionar regras padrão
    rules = create_default_notification_rules()
    for rule in rules:
        notifier.add_notification_rule(rule)

    print("✅ Regras de notificação configuradas")

    # Simular eventos de trading
    trading_events = [
        {
            'type': 'trade_executed',
            'data': {
                'symbol': 'BTC',
                'action': 'BUY',
                'quantity': 0.1,
                'price': 101000,
                'pnl': 500,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
        },
        {
            'type': 'profit_target',
            'data': {
                'symbol': 'ETH',
                'profit': 1500,
                'percentage': 12.5,
                'target': 12000
            }
        },
        {
            'type': 'high_risk',
            'data': {
                'risk_level': 'CRITICAL',
                'reason': 'Alta volatilidade detectada',
                'risk_score': 0.85,
                'recommendation': 'Reduzir posições em 50%'
            }
        }
    ]

    print("🔄 Processando eventos de trading...")

    for event in trading_events:
        print(f"\n📡 Evento: {event['type']}")
        success = notifier.process_trading_event(event['type'], event['data'])
        print(f"  Resultado: {'✅ Sucesso' if success else '❌ Falha'}")

    # Mostrar histórico
    print("\n📋 HISTÓRICO DE NOTIFICAÇÕES:")
    history = notifier.get_notification_history()

    for item in history:
        print(f"  🕐 {item['timestamp'][:19]} | {item['priority'].upper()} | {item['title']}")
        print(f"     {item['message'][:80]}...")

    print("\n🎉 Demo concluído!")

if __name__ == "__main__":
    demo_notifications()
