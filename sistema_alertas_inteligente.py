#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Alertas Inteligente Multi-Canal
Versão: 4.0 - Alertas Avançados e Inteligentes
Características: Multi-canal, regras inteligentes, alertas contextuais, escalação automática
"""

import json
import logging
import os
import smtplib
import sqlite3
import ssl
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests
import schedule
import yaml

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Severidades de alerta"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertCategory(Enum):
    """Categorias de alerta"""
    TRADING = "trading"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    SYSTEM = "system"
    MARKET = "market"
    PERFORMANCE = "performance"
    SENTIMENT = "sentiment"
    NEWS = "news"

class AlertChannel(Enum):
    """Canais de notificação"""
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"
    LOG = "log"
    DASHBOARD = "dashboard"

@dataclass
class AlertRule:
    """Regra de alerta configurável"""
    id: str
    name: str
    category: AlertCategory
    severity: AlertSeverity
    condition: Dict[str, Any]
    message_template: str
    channels: List[AlertChannel]
    cooldown_minutes: int = 60
    enabled: bool = True
    escalation_rules: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

@dataclass
class Alert:
    """Alerta estruturado"""
    id: str
    timestamp: str
    rule_id: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    channels: List[AlertChannel]
    data: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    escalation_level: int = 0
    delivered_channels: List[AlertChannel] = None

class IntelligentAlertSystem:
    """Sistema de alertas inteligente multi-canal"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.alerts_data_dir = 'alerts_data'
        self.config_file = 'configs/alert_config.yaml'

        # Criar diretórios
        os.makedirs(self.alerts_data_dir, exist_ok=True)
        os.makedirs('configs', exist_ok=True)

        # Estado interno
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=10000)  # Últimos 10k alertas
        self.cooldown_tracker = defaultdict(datetime)  # Track cooldown por rule_id
        self.escalation_tracker = defaultdict(list)  # Track escalações

        # Configurações
        self.config = self._load_config()

        # Conectores de canal
        self.channels = self._init_channels()

        # Inicializar sistema
        self._init_alert_system()

        # Thread de monitoramento
        self.monitoring_active = False
        self.monitor_thread = None

    def _init_alert_system(self):
        """Inicializar sistema de alertas"""
        # Inicializar base de dados
        self._init_database()

        # Carregar regras padrão
        self._load_default_rules()

        # Carregar regras salvas
        self._load_saved_rules()

        print("🚨 Sistema de Alertas Inteligente inicializado")

    def _init_database(self):
        """Inicializar base de dados de alertas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de regras de alerta
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    category TEXT,
                    severity TEXT,
                    condition TEXT,
                    message_template TEXT,
                    channels TEXT,
                    cooldown_minutes INTEGER,
                    enabled BOOLEAN,
                    escalation_rules TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # Tabela de alertas enviados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    rule_id TEXT,
                    category TEXT,
                    severity TEXT,
                    title TEXT,
                    message TEXT,
                    channels TEXT,
                    data TEXT,
                    acknowledged BOOLEAN,
                    resolved BOOLEAN,
                    escalation_level INTEGER,
                    delivered_channels TEXT
                )
            ''')

            # Tabela de configurações de canal
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channel_configs (
                    channel TEXT PRIMARY KEY,
                    config TEXT,
                    enabled BOOLEAN,
                    last_tested TEXT
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database de alertas: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações do sistema"""
        default_config = {
            'email': {
                'enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_email': '',
                'to_emails': [],
                'use_tls': True
            },
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_id': '',
                'api_url': 'https://api.telegram.org'
            },
            'discord': {
                'enabled': False,
                'webhook_url': ''
            },
            'slack': {
                'enabled': False,
                'webhook_url': '',
                'channel': '#alerts'
            },
            'webhook': {
                'enabled': False,
                'urls': [],
                'headers': {'Content-Type': 'application/json'},
                'timeout': 30
            },
            'sms': {
                'enabled': False,
                'provider': 'twilio',
                'account_sid': '',
                'auth_token': '',
                'from_number': '',
                'to_numbers': []
            },
            'general': {
                'max_alerts_per_hour': 100,
                'max_alerts_per_day': 1000,
                'enable_digest': True,
                'digest_schedule': 'daily',
                'enable_escalation': True,
                'escalation_timeout_hours': 4
            }
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                return {**default_config, **config}
            else:
                # Salvar configuração default
                with open(self.config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                return default_config
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração: {e}")
            return default_config

    def _init_channels(self) -> Dict[AlertChannel, Callable]:
        """Inicializar conectores de canal"""
        channels = {
            AlertChannel.LOG: self._send_log_alert,
            AlertChannel.DASHBOARD: self._send_dashboard_alert,
            AlertChannel.EMAIL: self._send_email_alert,
            AlertChannel.TELEGRAM: self._send_telegram_alert,
            AlertChannel.DISCORD: self._send_discord_alert,
            AlertChannel.SLACK: self._send_slack_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
            AlertChannel.SMS: self._send_sms_alert,
            AlertChannel.PUSH: self._send_push_alert
        }

        print("📱 Canais de notificação inicializados")
        return channels

    def _load_default_rules(self):
        """Carregar regras de alerta padrão"""
        default_rules = [
            AlertRule(
                id="trading_profit_target",
                name="Meta de Lucro Atingida",
                category=AlertCategory.TRADING,
                severity=AlertSeverity.MEDIUM,
                condition={
                    "type": "profit_threshold",
                    "threshold": 0.10,  # 10% lucro
                    "timeframe": "daily"
                },
                message_template="🎯 Meta de lucro atingida: {profit_pct:.1%} - Valor: ${profit_value:.2f}",
                channels=[AlertChannel.DASHBOARD, AlertChannel.TELEGRAM]
            ),
            AlertRule(
                id="risk_stop_loss",
                name="Stop Loss Acionado",
                category=AlertCategory.RISK,
                severity=AlertSeverity.HIGH,
                condition={
                    "type": "stop_loss_triggered",
                    "threshold": 0.05  # 5% stop loss
                },
                message_template="🛑 Stop Loss acionado! Perda: ${loss_value:.2f} ({loss_pct:.1%})",
                channels=[AlertChannel.EMAIL, AlertChannel.TELEGRAM, AlertChannel.DASHBOARD]
            ),
            AlertRule(
                id="risk_max_drawdown",
                name="Drawdown Máximo",
                category=AlertCategory.RISK,
                severity=AlertSeverity.CRITICAL,
                condition={
                    "type": "max_drawdown",
                    "threshold": 0.15  # 15% drawdown
                },
                message_template="⚠️ DRAWDOWN CRÍTICO! Máxima perda: {drawdown_pct:.1%}",
                channels=[AlertChannel.EMAIL, AlertChannel.TELEGRAM, AlertChannel.SMS]
            ),
            AlertRule(
                id="portfolio_concentration",
                name="Alta Concentração de Ativo",
                category=AlertCategory.PORTFOLIO,
                severity=AlertSeverity.MEDIUM,
                condition={
                    "type": "position_concentration",
                    "threshold": 0.30  # 30% por ativo
                },
                message_template="📊 Alta concentração detectada: {symbol} ({weight:.1%})",
                channels=[AlertChannel.DASHBOARD, AlertChannel.DISCORD]
            ),
            AlertRule(
                id="market_volatility_spike",
                name="Pico de Volatilidade",
                category=AlertCategory.MARKET,
                severity=AlertSeverity.MEDIUM,
                condition={
                    "type": "volatility_spike",
                    "threshold": 2.0,  # 2x volatilidade normal
                    "timeframe": "1h"
                },
                message_template="📈 Pico de volatilidade: {volatility_ratio:.1f}x normal",
                channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK]
            ),
            AlertRule(
                id="system_performance",
                name="Performance do Sistema",
                category=AlertCategory.SYSTEM,
                severity=AlertSeverity.LOW,
                condition={
                    "type": "system_metrics",
                    "metrics": ["cpu", "memory", "response_time"],
                    "thresholds": {"cpu": 80, "memory": 85, "response_time": 5000}
                },
                message_template="🔧 Métricas do sistema: CPU {cpu}%, RAM {memory}ms, Resposta {response_time}ms",
                channels=[AlertChannel.DASHBOARD]
            ),
            AlertRule(
                id="sentiment_extreme",
                name="Sentimento Extremo",
                category=AlertCategory.SENTIMENT,
                severity=AlertSeverity.MEDIUM,
                condition={
                    "type": "sentiment_extreme",
                    "threshold": 0.8,  # 80% confiança
                    "sentiment_type": "extreme"
                },
                message_template="🧠 Sentimento extremo detectado: {sentiment_type} ({confidence:.1%})",
                channels=[AlertChannel.DASHBOARD, AlertChannel.TELEGRAM]
            ),
            AlertRule(
                id="news_sentiment_negative",
                name="Notícias Negativas",
                category=AlertCategory.NEWS,
                severity=AlertSeverity.HIGH,
                condition={
                    "type": "news_sentiment",
                    "sentiment_threshold": -0.5,
                    "source_count": 3
                },
                message_template="📰 Notícias negativas detectadas: Sentimento {sentiment:.1%} em {source_count} fontes",
                channels=[AlertChannel.EMAIL, AlertChannel.DISCORD]
            )
        ]

        for rule in default_rules:
            self.alert_rules[rule.id] = rule

        print("📋 Regras padrão carregadas")

    def _load_saved_rules(self):
        """Carregar regras salvas do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, category, severity, condition, message_template,
                       channels, cooldown_minutes, enabled, escalation_rules, metadata
                FROM alert_rules
            ''')

            for row in cursor.fetchall():
                rule_data = {
                    'id': row[0],
                    'name': row[1],
                    'category': AlertCategory(row[2]),
                    'severity': AlertSeverity(row[3]),
                    'condition': json.loads(row[4]),
                    'message_template': row[5],
                    'channels': [AlertChannel(c) for c in json.loads(row[6])],
                    'cooldown_minutes': row[7],
                    'enabled': bool(row[8]),
                    'escalation_rules': json.loads(row[9]) if row[9] else None,
                    'metadata': json.loads(row[10]) if row[10] else {}
                }

                rule = AlertRule(**rule_data)
                self.alert_rules[rule.id] = rule

            conn.close()
            print(f"📋 {len(self.alert_rules)} regras carregadas do banco")

        except Exception as e:
            print(f"⚠️  Erro ao carregar regras salvas: {e}")

    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Adicionar nova regra de alerta"""
        try:
            self.alert_rules[rule.id] = rule

            # Salvar no banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO alert_rules
                (id, name, category, severity, condition, message_template, channels,
                 cooldown_minutes, enabled, escalation_rules, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule.id, rule.name, rule.category.value, rule.severity.value,
                json.dumps(rule.condition), rule.message_template,
                json.dumps([c.value for c in rule.channels]), rule.cooldown_minutes,
                rule.enabled, json.dumps(rule.escalation_rules or []),
                json.dumps(rule.metadata or {}),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            print(f"✅ Regra '{rule.name}' adicionada")
            return True

        except Exception as e:
            print(f"❌ Erro ao adicionar regra: {e}")
            return False

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remover regra de alerta"""
        try:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]

                # Remover do banco
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
                conn.commit()
                conn.close()

                print(f"✅ Regra '{rule_id}' removida")
                return True
            else:
                print(f"⚠️  Regra '{rule_id}' não encontrada")
                return False

        except Exception as e:
            print(f"❌ Erro ao remover regra: {e}")
            return False

    def evaluate_alert_conditions(self, data: Dict[str, Any]) -> List[Alert]:
        """Avaliar condições de todas as regras ativas"""
        triggered_alerts = []

        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue

            # Verificar cooldown
            if self._is_in_cooldown(rule):
                continue

            # Avaliar condição
            if self._evaluate_condition(rule, data):
                alert = self._create_alert(rule, data)
                if alert:
                    triggered_alerts.append(alert)

        return triggered_alerts

    def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """Verificar se regra está em cooldown"""
        rule_id = rule.id
        if rule_id in self.cooldown_tracker:
            last_alert = self.cooldown_tracker[rule_id]
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            return datetime.now() - last_alert < cooldown_delta
        return False

    def _evaluate_condition(self, rule: AlertRule, data: Dict[str, Any]) -> bool:
        """Avaliar condição de uma regra"""
        try:
            condition = rule.condition
            condition_type = condition.get('type')

            if condition_type == "profit_threshold":
                return self._check_profit_threshold(condition, data)
            elif condition_type == "stop_loss_triggered":
                return self._check_stop_loss(condition, data)
            elif condition_type == "max_drawdown":
                return self._check_max_drawdown(condition, data)
            elif condition_type == "position_concentration":
                return self._check_position_concentration(condition, data)
            elif condition_type == "volatility_spike":
                return self._check_volatility_spike(condition, data)
            elif condition_type == "system_metrics":
                return self._check_system_metrics(condition, data)
            elif condition_type == "sentiment_extreme":
                return self._check_sentiment_extreme(condition, data)
            elif condition_type == "news_sentiment":
                return self._check_news_sentiment(condition, data)
            else:
                print(f"⚠️  Tipo de condição desconhecido: {condition_type}")
                return False

        except Exception as e:
            print(f"❌ Erro ao avaliar condição: {e}")
            return False

    def _check_profit_threshold(self, condition: Dict, data: Dict) -> bool:
        """Verificar threshold de lucro"""
        threshold = condition.get('threshold', 0.1)
        timeframe = condition.get('timeframe', 'daily')

        # Extrair dados de lucro do data
        profit_pct = data.get('profit_percentage', 0)
        return profit_pct >= threshold

    def _check_stop_loss(self, condition: Dict, data: Dict) -> bool:
        """Verificar stop loss acionado"""
        stop_loss_triggered = data.get('stop_loss_triggered', False)
        return stop_loss_triggered

    def _check_max_drawdown(self, condition: Dict, data: Dict) -> bool:
        """Verificar drawdown máximo"""
        threshold = condition.get('threshold', 0.15)
        current_drawdown = data.get('max_drawdown', 0)
        return current_drawdown >= threshold

    def _check_position_concentration(self, condition: Dict, data: Dict) -> bool:
        """Verificar concentração de posição"""
        threshold = condition.get('threshold', 0.30)
        position_data = data.get('positions', {})

        for symbol, position in position_data.items():
            weight = position.get('weight', 0)
            if weight >= threshold:
                return True
        return False

    def _check_volatility_spike(self, condition: Dict, data: Dict) -> bool:
        """Verificar pico de volatilidade"""
        threshold = condition.get('threshold', 2.0)
        current_vol = data.get('volatility', 0)
        normal_vol = data.get('normal_volatility', 0.02)

        if normal_vol > 0:
            vol_ratio = current_vol / normal_vol
            return vol_ratio >= threshold
        return False

    def _check_system_metrics(self, condition: Dict, data: Dict) -> bool:
        """Verificar métricas do sistema"""
        metrics = condition.get('metrics', [])
        thresholds = condition.get('thresholds', {})

        for metric in metrics:
            threshold = thresholds.get(metric)
            current_value = data.get(metric, 0)

            if current_value >= threshold:
                return True
        return False

    def _check_sentiment_extreme(self, condition: Dict, data: Dict) -> bool:
        """Verificar sentimento extremo"""
        threshold = condition.get('threshold', 0.8)
        sentiment_data = data.get('sentiment', {})

        overall_sentiment = sentiment_data.get('overall_sentiment', 0)
        confidence = sentiment_data.get('confidence', 0)

        # Verificar se é extremo e tem alta confiança
        is_extreme = abs(overall_sentiment) >= threshold * 0.7  # 70% do threshold
        return is_extreme and confidence >= threshold

    def _check_news_sentiment(self, condition: Dict, data: Dict) -> bool:
        """Verificar sentimento de notícias"""
        sentiment_threshold = condition.get('sentiment_threshold', -0.5)
        source_count = condition.get('source_count', 3)

        news_data = data.get('news_sentiment', {})
        avg_sentiment = news_data.get('average_sentiment', 0)
        sources = news_data.get('source_count', 0)

        return avg_sentiment <= sentiment_threshold and sources >= source_count

    def _create_alert(self, rule: AlertRule, data: Dict[str, Any]) -> Optional[Alert]:
        """Criar alerta a partir de uma regra"""
        try:
            # Gerar ID único
            alert_id = f"{rule.id}_{int(time.time())}"

            # Formatar mensagem
            title = rule.name
            message = rule.message_template.format(**data)

            # Criar dados contextuais
            alert_data = {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'timestamp': datetime.now().isoformat(),
                'severity': rule.severity.value,
                'category': rule.category.value,
                **data
            }

            alert = Alert(
                id=alert_id,
                timestamp=datetime.now().isoformat(),
                rule_id=rule.id,
                category=rule.category,
                severity=rule.severity,
                title=title,
                message=message,
                channels=rule.channels,
                data=alert_data,
                delivered_channels=[]
            )

            return alert

        except Exception as e:
            print(f"❌ Erro ao criar alerta: {e}")
            return None

    def send_alert(self, alert: Alert) -> bool:
        """Enviar alerta via todos os canais configurados"""
        success_count = 0

        for channel in alert.channels:
            if self._send_alert_via_channel(alert, channel):
                success_count += 1
                alert.delivered_channels.append(channel)

        # Salvar alerta no histórico
        self._save_alert(alert)
        self.alert_history.append(alert)

        # Atualizar cooldown
        self.cooldown_tracker[alert.rule_id] = datetime.now()

        if success_count > 0:
            print(f"🚨 Alerta enviado: {alert.title} via {success_count} canais")

            # Verificar escalação
            if self.config.get('general', {}).get('enable_escalation', True):
                self._check_escalation(alert)

            return True
        else:
            print(f"❌ Falha ao enviar alerta: {alert.title}")
            return False

    def _send_alert_via_channel(self, alert: Alert, channel: AlertChannel) -> bool:
        """Enviar alerta via canal específico"""
        try:
            if channel in self.channels:
                return self.channels[channel](alert)
            else:
                print(f"⚠️  Canal não implementado: {channel}")
                return False
        except Exception as e:
            print(f"❌ Erro ao enviar via {channel}: {e}")
            return False

    def _send_log_alert(self, alert: Alert) -> bool:
        """Enviar alerta para log"""
        logger.warning(f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        return True

    def _send_dashboard_alert(self, alert: Alert) -> bool:
        """Enviar alerta para dashboard (salvar em arquivo)"""
        try:
            alerts_file = os.path.join(self.alerts_data_dir, 'dashboard_alerts.json')

            # Carregar alertas existentes
            if os.path.exists(alerts_file):
                with open(alerts_file, 'r') as f:
                    dashboard_alerts = json.load(f)
            else:
                dashboard_alerts = []

            # Adicionar novo alerta
            dashboard_alerts.append(asdict(alert))

            # Manter apenas os últimos 100 alertas
            dashboard_alerts = dashboard_alerts[-100:]

            # Salvar
            with open(alerts_file, 'w') as f:
                json.dump(dashboard_alerts, f, indent=2)

            return True

        except Exception as e:
            print(f"❌ Erro ao salvar no dashboard: {e}")
            return False

    def _send_email_alert(self, alert: Alert) -> bool:
        """Enviar alerta por email"""
        try:
            email_config = self.config.get('email', {})
            if not email_config.get('enabled', False):
                return False

            # Configurar email
            msg = MimeMultipart()
            msg['From'] = email_config.get('from_email')
            msg['To'] = ', '.join(email_config.get('to_emails', []))
            msg['Subject'] = f"[{alert.severity.value.upper()}] FreqTrade3 - {alert.title}"

            # Corpo do email
            body = f"""
            <h2>FreqTrade3 - Alerta de {alert.category.value.title()}</h2>
            <p><strong>Severidade:</strong> {alert.severity.value.upper()}</p>
            <p><strong>Título:</strong> {alert.title}</p>
            <p><strong>Mensagem:</strong> {alert.message}</p>
            <p><strong>Timestamp:</strong> {alert.timestamp}</p>
            <hr>
            <p><em>Dados adicionais:</em></p>
            <pre>{json.dumps(alert.data, indent=2)}</pre>
            """

            msg.attach(MimeText(body, 'html'))

            # Enviar email
            if email_config.get('username') and email_config.get('password'):
                server = smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port', 587))
                server.starttls()
                server.login(email_config.get('username'), email_config.get('password'))
                text = msg.as_string()
                server.sendmail(email_config.get('from_email'), email_config.get('to_emails'), text)
                server.quit()

                return True

        except Exception as e:
            print(f"❌ Erro ao enviar email: {e}")

        return False

    def _send_telegram_alert(self, alert: Alert) -> bool:
        """Enviar alerta via Telegram"""
        try:
            telegram_config = self.config.get('telegram', {})
            if not telegram_config.get('enabled', False):
                return False

            bot_token = telegram_config.get('bot_token')
            chat_id = telegram_config.get('chat_id')

            if not bot_token or not chat_id:
                return False

            # Formatar mensagem
            emoji_map = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🚨",
                AlertSeverity.CRITICAL: "🆘",
                AlertSeverity.EMERGENCY: "💀"
            }

            emoji = emoji_map.get(alert.severity, "📢")
            message = f"{emoji} <b>{alert.title}</b>\n\n{alert.message}\n\n<i>{alert.timestamp}</i>"

            # Enviar
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"❌ Erro ao enviar Telegram: {e}")
            return False

    def _send_discord_alert(self, alert: Alert) -> bool:
        """Enviar alerta via Discord"""
        try:
            discord_config = self.config.get('discord', {})
            if not discord_config.get('enabled', False):
                return False

            webhook_url = discord_config.get('webhook_url')
            if not webhook_url:
                return False

            # Cores por severidade
            color_map = {
                AlertSeverity.LOW: 0x00ff00,      # Verde
                AlertSeverity.MEDIUM: 0xffff00,   # Amarelo
                AlertSeverity.HIGH: 0xff8000,     # Laranja
                AlertSeverity.CRITICAL: 0xff0000, # Vermelho
                AlertSeverity.EMERGENCY: 0x800000 # Vermelho escuro
            }

            embed = {
                "title": f"{alert.title}",
                "description": alert.message,
                "color": color_map.get(alert.severity, 0x808080),
                "timestamp": alert.timestamp,
                "fields": [
                    {"name": "Severidade", "value": alert.severity.value.upper(), "inline": True},
                    {"name": "Categoria", "value": alert.category.value.title(), "inline": True},
                    {"name": "ID", "value": alert.id, "inline": True}
                ]
            }

            payload = {
                "embeds": [embed]
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code == 204  # Discord retorna 204 no sucesso

        except Exception as e:
            print(f"❌ Erro ao enviar Discord: {e}")
            return False

    def _send_slack_alert(self, alert: Alert) -> bool:
        """Enviar alerta via Slack"""
        try:
            slack_config = self.config.get('slack', {})
            if not slack_config.get('enabled', False):
                return False

            webhook_url = slack_config.get('webhook_url')
            if not webhook_url:
                return False

            # Cores por severidade
            color_map = {
                AlertSeverity.LOW: "good",
                AlertSeverity.MEDIUM: "warning",
                AlertSeverity.HIGH: "danger",
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.EMERGENCY: "danger"
            }

            payload = {
                "channel": slack_config.get('channel', '#alerts'),
                "username": "FreqTrade3 Bot",
                "icon_emoji": ":robot_face:",
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "warning"),
                        "title": alert.title,
                        "text": alert.message,
                        "fields": [
                            {"title": "Severidade", "value": alert.severity.value.upper(), "short": True},
                            {"title": "Categoria", "value": alert.category.value.title(), "short": True},
                            {"title": "ID", "value": alert.id, "short": True}
                        ],
                        "ts": int(time.time())
                    }
                ]
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"❌ Erro ao enviar Slack: {e}")
            return False

    def _send_webhook_alert(self, alert: Alert) -> bool:
        """Enviar alerta via webhook genérico"""
        try:
            webhook_config = self.config.get('webhook', {})
            if not webhook_config.get('enabled', False):
                return False

            urls = webhook_config.get('urls', [])
            headers = webhook_config.get('headers', {'Content-Type': 'application/json'})
            timeout = webhook_config.get('timeout', 30)

            success_count = 0

            for url in urls:
                payload = {
                    "alert": asdict(alert),
                    "source": "FreqTrade3",
                    "timestamp": datetime.now().isoformat()
                }

                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                    if response.status_code < 400:
                        success_count += 1
                except Exception as e:
                    print(f"⚠️  Erro ao enviar webhook para {url}: {e}")

            return success_count > 0

        except Exception as e:
            print(f"❌ Erro ao enviar webhooks: {e}")
            return False

    def _send_sms_alert(self, alert: Alert) -> bool:
        """Enviar alerta via SMS"""
        # Implementação simplificada - requer integração com provedor de SMS
        try:
            sms_config = self.config.get('sms', {})
            if not sms_config.get('enabled', False):
                return False

            # Aqui seria implementada a lógica do Twilio ou outro provedor
            print(f"📱 SMS enviado para: {alert.title}")
            return True

        except Exception as e:
            print(f"❌ Erro ao enviar SMS: {e}")
            return False

    def _send_push_alert(self, alert: Alert) -> bool:
        """Enviar alerta via push notification"""
        # Implementação simplificada - requer Firebase ou similar
        try:
            print(f"🔔 Push notification enviado: {alert.title}")
            return True
        except Exception as e:
            print(f"❌ Erro ao enviar push: {e}")
            return False

    def _check_escalation(self, alert: Alert):
        """Verificar se alerta precisa ser escalado"""
        try:
            rule = self.alert_rules.get(alert.rule_id)
            if not rule or not rule.escalation_rules:
                return

            escalation_timeout = self.config.get('general', {}).get('escalation_timeout_hours', 4)

            # Verificar se alerta está pendente há tempo suficiente
            alert_time = datetime.fromisoformat(alert.timestamp)
            time_diff = datetime.now() - alert_time
            timeout_delta = timedelta(hours=escalation_timeout)

            if time_diff < timeout_delta:
                return

            # Verificar se já foi escalado
            rule_id = alert.rule_id
            if rule_id in self.escalation_tracker:
                escalation_times = self.escalation_tracker[rule_id]
                if any((datetime.now() - esc_time) < timeout_delta for esc_time in escalation_times):
                    return

            # Executar escalação
            self._execute_escalation(alert, rule)

            # Registrar escalação
            if rule_id not in self.escalation_tracker:
                self.escalation_tracker[rule_id] = []
            self.escalation_tracker[rule_id].append(datetime.now())

        except Exception as e:
            print(f"❌ Erro na verificação de escalação: {e}")

    def _execute_escalation(self, alert: Alert, rule: AlertRule):
        """Executar escalação do alerta"""
        try:
            escalation_msg = f"🔺 ESCALAÇÃO: {alert.title} - {alert.message}"

            # Canais de escalação (mais abrangentes)
            escalation_channels = [
                AlertChannel.EMAIL,
                AlertChannel.TELEGRAM,
                AlertChannel.SMS
            ]

            # Criar alerta de escalação
            escalation_alert = Alert(
                id=f"escalation_{alert.id}",
                timestamp=datetime.now().isoformat(),
                rule_id=alert.rule_id,
                category=AlertCategory.SYSTEM,
                severity=AlertSeverity.HIGH,  # Escalação é sempre alta
                title=f"Escalação: {alert.title}",
                message=escalation_msg,
                channels=escalation_channels,
                data={
                    **alert.data,
                    'escalation': True,
                    'original_alert_id': alert.id,
                    'original_severity': alert.severity.value
                },
                escalation_level=alert.escalation_level + 1
            )

            # Enviar alerta de escalação
            self.send_alert(escalation_alert)

            print(f"🔺 Alerta escalado: {alert.title}")

        except Exception as e:
            print(f"❌ Erro na escalação: {e}")

    def _save_alert(self, alert: Alert):
        """Salvar alerta no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO alerts
                (id, timestamp, rule_id, category, severity, title, message,
                 channels, data, acknowledged, resolved, escalation_level, delivered_channels)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id, alert.timestamp, alert.rule_id, alert.category.value,
                alert.severity.value, alert.title, alert.message,
                json.dumps([c.value for c in alert.channels]), json.dumps(alert.data),
                alert.acknowledged, alert.resolved, alert.escalation_level,
                json.dumps([c.value for c in alert.delivered_channels] or [])
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar alerta: {e}")

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Confirmar recebimento de alerta"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE alerts SET acknowledged = TRUE WHERE id = ?
            ''', (alert_id,))

            conn.commit()
            conn.close()

            # Atualizar no histórico local
            for alert in self.alert_history:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    break

            return True

        except Exception as e:
            print(f"❌ Erro ao confirmar alerta: {e}")
            return False

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Obter resumo de alertas das últimas horas"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Filtrar alertas recentes
            recent_alerts = [
                alert for alert in self.alert_history
                if datetime.fromisoformat(alert.timestamp) > cutoff_time
            ]

            # Estatísticas
            total_alerts = len(recent_alerts)
            by_severity = defaultdict(int)
            by_category = defaultdict(int)
            by_channel = defaultdict(int)
            acknowledged_count = 0

            for alert in recent_alerts:
                by_severity[alert.severity.value] += 1
                by_category[alert.category.value] += 1
                for channel in alert.channels:
                    by_channel[channel.value] += 1
                if alert.acknowledged:
                    acknowledged_count += 1

            return {
                'period_hours': hours,
                'total_alerts': total_alerts,
                'acknowledged': acknowledged_count,
                'pending': total_alerts - acknowledged_count,
                'by_severity': dict(by_severity),
                'by_category': dict(by_category),
                'by_channel': dict(by_channel),
                'most_common_severity': max(by_severity.items(), key=lambda x: x[1])[0] if by_severity else 'none',
                'most_common_category': max(by_category.items(), key=lambda x: x[1])[0] if by_category else 'none'
            }

        except Exception as e:
            print(f"❌ Erro ao gerar resumo: {e}")
            return {}

    def test_channels(self) -> Dict[str, bool]:
        """Testar todos os canais configurados"""
        test_results = {}

        # Criar alerta de teste
        test_alert = Alert(
            id=f"test_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            rule_id="channel_test",
            category=AlertCategory.SYSTEM,
            severity=AlertSeverity.LOW,
            title="Teste de Canal",
            message="Este é um teste do sistema de alertas",
            channels=[channel for channel in AlertChannel],
            data={'test': True}
        )

        for channel in AlertChannel:
            try:
                result = self._send_alert_via_channel(test_alert, channel)
                test_results[channel.value] = result
            except Exception as e:
                print(f"❌ Erro ao testar {channel}: {e}")
                test_results[channel.value] = False

        return test_results

    def start_monitoring(self, data_provider: Callable[[], Dict], interval: int = 60):
        """Iniciar monitoramento contínuo"""
        if self.monitoring_active:
            return

        self.monitoring_active = True

        def monitor_alerts():
            while self.monitoring_active:
                try:
                    # Obter dados atuais
                    current_data = data_provider()

                    # Avaliar regras
                    alerts = self.evaluate_alert_conditions(current_data)

                    # Enviar alertas
                    for alert in alerts:
                        self.send_alert(alert)

                    # Limitar taxa de alertas
                    if len(alerts) > 0:
                        time.sleep(5)  # Pausa entre grupos de alertas

                except Exception as e:
                    print(f"❌ Erro no monitoramento: {e}")

                time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor_alerts, daemon=True)
        self.monitor_thread.start()
        print("🟢 Monitoramento de alertas iniciado")

    def stop_monitoring(self):
        """Parar monitoramento"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("🔴 Monitoramento de alertas parado")

# API para integração com o painel principal
def create_alert_system():
    """Criar instância do sistema de alertas"""
    return IntelligentAlertSystem()

if __name__ == "__main__":
    # Teste do sistema de alertas
    alert_system = create_alert_system()

    # Teste de avaliação
    test_data = {
        'profit_percentage': 0.12,
        'stop_loss_triggered': False,
        'max_drawdown': 0.05,
        'positions': {'BTC/USDT': {'weight': 0.35}},
        'volatility': 0.04,
        'normal_volatility': 0.02
    }

    alerts = alert_system.evaluate_alert_conditions(test_data)
    print(f"Alertas disparados: {len(alerts)}")

    # Testar canais
    test_results = alert_system.test_channels()
    print(f"Teste de canais: {test_results}")

    # Iniciar monitoramento
    alert_system.start_monitoring(lambda: test_data, interval=30)
