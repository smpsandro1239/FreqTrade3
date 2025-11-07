#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Notifications Push
Versão: 4.0 - Notificações Push Avançadas
Características: Firebase FCM, Web Push, Service Worker, templates, gestão de dispositivos
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import ssl
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pywebpush
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Tipos de notificação"""
    TRADE_EXECUTION = "trade_execution"
    PRICE_ALERT = "price_alert"
    RISK_WARNING = "risk_warning"
    SYSTEM_STATUS = "system_status"
    BACKUP_COMPLETE = "backup_complete"
    OPPORTUNITY = "opportunity"
    NEWS = "news"
    PORTFOLIO_UPDATE = "portfolio_update"
    MAINTENANCE = "maintenance"

class PushProvider(Enum):
    """Provedores de push"""
    FIREBASE = "firebase"
    WEB_PUSH = "web_push"
    APNS = "apns"  # Apple Push Notification Service
    FCM = "fcm"    # Firebase Cloud Messaging

@dataclass
class PushSubscription:
    """Subscrição de push notification"""
    id: str
    endpoint: str
    keys: Dict[str, str]
    device_info: Dict[str, Any]
    user_id: str
    created_at: str
    last_used: str
    active: bool

@dataclass
class PushMessage:
    """Mensagem de push notification"""
    id: str
    title: str
    body: str
    icon: str
    badge: str
    image: str
    click_action: str
    data: Dict[str, Any]
    notification_type: NotificationType
    priority: str = "high"
    ttl: int = 86400  # 24 horas
    sound: str = "default"
    actions: List[Dict[str, str]] = None

class PushNotificationSystem:
    """Sistema de notifications push"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.push_data_dir = 'push_data'
        self.certs_dir = 'certs'

        # Criar diretórios
        os.makedirs(self.push_data_dir, exist_ok=True)
        os.makedirs(self.certs_dir, exist_ok=True)

        # Estado interno
        self.subscriptions = {}
        self.notification_history = deque(maxlen=10000)
        self.devices = {}

        # Configurações
        self.config = self._load_config()

        # Provedores
        self.providers = self._init_providers()

        # Service Worker
        self._create_service_worker()

        # VAPID keys para Web Push
        self._init_vapid_keys()

        # Inicializar sistema
        self._init_push_system()

    def _init_push_system(self):
        """Inicializar sistema de push"""
        # Inicializar base de dados
        self._init_database()

        # Carregar subscrições
        self._load_subscriptions()

        print("🔔 Sistema de Push Notifications inicializado")

    def _init_database(self):
        """Inicializar base de dados de push"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de subscrições
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS push_subscriptions (
                    id TEXT PRIMARY KEY,
                    endpoint TEXT UNIQUE,
                    p256dh TEXT,
                    auth TEXT,
                    device_type TEXT,
                    user_agent TEXT,
                    device_id TEXT,
                    user_id TEXT,
                    created_at TEXT,
                    last_used TEXT,
                    active BOOLEAN,
                    metadata TEXT
                )
            ''')

            # Tabela de mensagens enviadas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS push_messages (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    body TEXT,
                    icon TEXT,
                    badge TEXT,
                    image TEXT,
                    click_action TEXT,
                    data TEXT,
                    type TEXT,
                    priority TEXT,
                    ttl INTEGER,
                    sent_at TEXT,
                    success_count INTEGER,
                    failure_count INTEGER,
                    provider_responses TEXT
                )
            ''')

            # Tabela de tokens de dispositivos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_tokens (
                    id TEXT PRIMARY KEY,
                    token TEXT,
                    platform TEXT,
                    app_version TEXT,
                    user_id TEXT,
                    active BOOLEAN,
                    last_seen TEXT,
                    metadata TEXT
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database de push: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações de push"""
        default_config = {
            'firebase': {
                'enabled': False,
                'server_key': '',
                'sender_id': '',
                'project_id': '',
                'api_key': ''
            },
            'web_push': {
                'enabled': True,
                'vapid_public_key': '',
                'vapid_private_key': '',
                'vapid_subject': 'mailto:admin@freqtrade3.com'
            },
            'settings': {
                'default_priority': 'high',
                'default_ttl': 86400,  # 24 horas
                'max_retries': 3,
                'retry_delay': 5,  # segundos
                'batch_size': 100,
                'rate_limit': 1000  # mensagens por hora
            },
            'templates': {
                NotificationType.TRADE_EXECUTION: {
                    'title': 'Trade Executado',
                    'body': '{side} {quantity} {symbol} a ${price}',
                    'icon': '/icons/trade.png'
                },
                NotificationType.PRICE_ALERT: {
                    'title': 'Alerta de Preço',
                    'body': '{symbol} alcanzó ${price}',
                    'icon': '/icons/price.png'
                },
                NotificationType.RISK_WARNING: {
                    'title': 'Aviso de Risco',
                    'body': '{message}',
                    'icon': '/icons/warning.png'
                },
                NotificationType.SYSTEM_STATUS: {
                    'title': 'Status do Sistema',
                    'body': '{message}',
                    'icon': '/icons/system.png'
                }
            },
            'filters': {
                'enabled': True,
                'min_importance': 'medium',
                'user_preferences': True
            }
        }

        try:
            config_file = 'configs/push_config.json'
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return {**default_config, **config}
            else:
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração de push: {e}")
            return default_config

    def _init_providers(self) -> Dict[PushProvider, Callable]:
        """Inicializar provedores de push"""
        return {
            PushProvider.FIREBASE: self._send_firebase_push,
            PushProvider.WEB_PUSH: self._send_web_push,
            PushProvider.FCM: self._send_fcm_push
        }

    def _create_service_worker(self):
        """Criar Service Worker para Web Push"""
        service_worker_content = '''
const CACHE_NAME = 'freqtrade3-push-v1';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/icons/icon-192x192.png'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Push notification handler
self.addEventListener('push', function(event) {
  const options = {
    body: event.data ? event.data.text() : 'Nova notificação do FreqTrade3',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Ver Detalhes',
        icon: '/icons/checkmark.png'
      },
      {
        action: 'close',
        title: 'Fechar',
        icon: '/icons/xmark.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('FreqTrade3', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/dashboard')
    );
  } else if (event.action === 'close') {
    // Just close the notification
  } else {
    // Default action - open dashboard
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Background sync for offline notifications
self.addEventListener('sync', function(event) {
  if (event.tag === 'background-sync') {
    event.waitUntil(
      // Sync pending notifications
      syncPendingNotifications()
    );
  }
});

function syncPendingNotifications() {
  return fetch('/api/push/sync', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });
}
'''

        service_worker_file = os.path.join(self.push_data_dir, 'service-worker.js')
        with open(service_worker_file, 'w', encoding='utf-8') as f:
            f.write(service_worker_content)

        print("📄 Service Worker criado")

    def _init_vapid_keys(self):
        """Inicializar chaves VAPID para Web Push"""
        vapid_file = os.path.join(self.certs_dir, 'vapid_keys.json')

        if not os.path.exists(vapid_file):
            # Gerar novas chaves VAPID
            try:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )

                public_key = private_key.public_key()

                # Serializar chaves
                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )

                public_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )

                # Converter para base64url
                def b64url_encode(data):
                    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

                vapid_keys = {
                    'publicKey': b64url_encode(public_pem),
                    'privateKey': b64url_encode(private_pem),
                    'subject': self.config['web_push']['vapid_subject']
                }

                # Salvar chaves
                with open(vapid_file, 'w') as f:
                    json.dump(vapid_keys, f, indent=2)

                # Atualizar configuração
                self.config['web_push']['vapid_public_key'] = vapid_keys['publicKey']
                self.config['web_push']['vapid_private_key'] = vapid_keys['privateKey']

                print("🔑 Chaves VAPID geradas")

            except Exception as e:
                print(f"❌ Erro ao gerar chaves VAPID: {e}")
        else:
            # Carregar chaves existentes
            try:
                with open(vapid_file, 'r') as f:
                    vapid_keys = json.load(f)

                self.config['web_push']['vapid_public_key'] = vapid_keys['publicKey']
                self.config['web_push']['vapid_private_key'] = vapid_keys['privateKey']

                print("🔑 Chaves VAPID carregadas")

            except Exception as e:
                print(f"❌ Erro ao carregar chaves VAPID: {e}")

    def _load_subscriptions(self):
        """Carregar subscrições do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, endpoint, p256dh, auth, device_type, user_agent,
                       device_id, user_id, created_at, last_used, active, metadata
                FROM push_subscriptions
                WHERE active = 1
            ''')

            for row in cursor.fetchall():
                subscription = PushSubscription(
                    id=row[0],
                    endpoint=row[1],
                    keys={'p256dh': row[2], 'auth': row[3]},
                    device_info={
                        'device_type': row[4],
                        'user_agent': row[5],
                        'device_id': row[6]
                    },
                    user_id=row[7],
                    created_at=row[8],
                    last_used=row[9],
                    active=bool(row[10])
                )

                self.subscriptions[subscription.id] = subscription

            conn.close()
            print(f"📱 {len(self.subscriptions)} subscrições carregadas")

        except Exception as e:
            print(f"⚠️  Erro ao carregar subscrições: {e}")

    def subscribe_device(self, subscription_data: Dict[str, Any], user_id: str = "default") -> str:
        """Registrar nova subscrição de dispositivo"""
        try:
            # Validar dados de subscrição
            if 'endpoint' not in subscription_data or 'keys' not in subscription_data:
                raise ValueError("Dados de subscrição inválidos")

            # Verificar se já existe
            endpoint = subscription_data['endpoint']
            existing_sub = self._get_subscription_by_endpoint(endpoint)

            if existing_sub:
                # Atualizar subscrição existente
                existing_sub.last_used = datetime.now().isoformat()
                existing_sub.active = True
                self._save_subscription(existing_sub)
                return existing_sub.id

            # Criar nova subscrição
            subscription_id = str(uuid.uuid4())

            subscription = PushSubscription(
                id=subscription_id,
                endpoint=endpoint,
                keys=subscription_data['keys'],
                device_info=subscription_data.get('device_info', {}),
                user_id=user_id,
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat(),
                active=True
            )

            # Salvar
            self.subscriptions[subscription_id] = subscription
            self._save_subscription(subscription)

            logger.info(f"Nova subscrição registrada: {subscription_id}")
            return subscription_id

        except Exception as e:
            logger.error(f"Erro ao registrar subscrição: {e}")
            raise

    def _get_subscription_by_endpoint(self, endpoint: str) -> Optional[PushSubscription]:
        """Obter subscrição por endpoint"""
        for sub in self.subscriptions.values():
            if sub.endpoint == endpoint:
                return sub
        return None

    def _save_subscription(self, subscription: PushSubscription):
        """Salvar subscrição no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO push_subscriptions
                (id, endpoint, p256dh, auth, device_type, user_agent,
                 device_id, user_id, created_at, last_used, active, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                subscription.id, subscription.endpoint,
                subscription.keys.get('p256dh', ''),
                subscription.keys.get('auth', ''),
                subscription.device_info.get('device_type', ''),
                subscription.device_info.get('user_agent', ''),
                subscription.device_info.get('device_id', ''),
                subscription.user_id, subscription.created_at,
                subscription.last_used, subscription.active,
                json.dumps(subscription.device_info)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar subscrição: {e}")

    def unsubscribe_device(self, subscription_id: str) -> bool:
        """Cancelar subscrição de dispositivo"""
        try:
            if subscription_id in self.subscriptions:
                subscription = self.subscriptions[subscription_id]
                subscription.active = False
                self._save_subscription(subscription)
                logger.info(f"Subscrição cancelada: {subscription_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Erro ao cancelar subscrição: {e}")
            return False

    def send_notification(self, message: PushMessage, target_users: List[str] = None,
                         target_types: List[NotificationType] = None) -> Dict[str, Any]:
        """Enviar notificação push"""
        try:
            logger.info(f"Enviando notificação: {message.title}")

            # Filtrar subscrições
            target_subscriptions = self._filter_subscriptions(target_users, target_types)

            if not target_subscriptions:
                logger.warning("Nenhuma subscrição válida encontrada")
                return {
                    'success': False,
                    'error': 'No valid subscriptions found',
                    'sent_count': 0
                }

            # Preparar payload
            payload = {
                'title': message.title,
                'body': message.body,
                'icon': message.icon,
                'badge': message.badge,
                'image': message.image,
                'click_action': message.click_action,
                'data': message.data,
                'tag': message.notification_type.value,
                'requireInteraction': message.priority == 'high',
                'timestamp': int(time.time())
            }

            # Enviar em lotes
            results = self._send_in_batches(target_subscriptions, payload, message)

            # Salvar histórico
            self._save_message_history(message, results)

            return {
                'success': True,
                'message_id': message.id,
                'total_targeted': len(target_subscriptions),
                'sent_count': results['sent_count'],
                'failed_count': results['failed_count'],
                'results': results['details']
            }

        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {e}")
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0
            }

    def _filter_subscriptions(self, target_users: List[str] = None,
                             target_types: List[NotificationType] = None) -> List[PushSubscription]:
        """Filtrar subscrições por critérios"""
        subscriptions = list(self.subscriptions.values())

        # Filtrar por usuários
        if target_users:
            subscriptions = [sub for sub in subscriptions if sub.user_id in target_users]

        # Filtrar por tipos (implementar lógica de preferências)
        if target_types:
            # Aqui seria implementada a lógica de preferências do usuário
            # Por simplicidade, incluir todas as subscrições ativas
            pass

        # Apenas subscrições ativas
        subscriptions = [sub for sub in subscriptions if sub.active]

        return subscriptions

    def _send_in_batches(self, subscriptions: List[PushSubscription],
                        payload: Dict[str, Any], message: PushMessage) -> Dict[str, Any]:
        """Enviar notificações em lotes"""
        batch_size = self.config['settings']['batch_size']
        results = {
            'sent_count': 0,
            'failed_count': 0,
            'details': []
        }

        for i in range(0, len(subscriptions), batch_size):
            batch = subscriptions[i:i + batch_size]
            batch_results = self._send_batch(batch, payload, message)

            results['sent_count'] += batch_results['sent_count']
            results['failed_count'] += batch_results['failed_count']
            results['details'].extend(batch_results['details'])

            # Pequena pausa entre lotes
            if i + batch_size < len(subscriptions):
                time.sleep(1)

        return results

    def _send_batch(self, subscriptions: List[PushSubscription],
                   payload: Dict[str, Any], message: PushMessage) -> Dict[str, Any]:
        """Enviar lote de notificações"""
        results = {
            'sent_count': 0,
            'failed_count': 0,
            'details': []
        }

        for subscription in subscriptions:
            try:
                # Determinar provedor
                provider = self._detect_provider(subscription)

                # Enviar via provedor
                success = self.providers[provider](subscription, payload, message)

                if success:
                    results['sent_count'] += 1
                    results['details'].append({
                        'subscription_id': subscription.id,
                        'status': 'sent',
                        'provider': provider.value
                    })
                else:
                    results['failed_count'] += 1
                    results['details'].append({
                        'subscription_id': subscription.id,
                        'status': 'failed',
                        'provider': provider.value,
                        'error': 'Unknown error'
                    })

            except Exception as e:
                results['failed_count'] += 1
                results['details'].append({
                    'subscription_id': subscription.id,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Erro ao enviar para {subscription.id}: {e}")

        return results

    def _detect_provider(self, subscription: PushSubscription) -> PushProvider:
        """Detectar provedor baseado na subscrição"""
        endpoint = subscription.endpoint.lower()

        if 'fcm' in endpoint or 'firebase' in endpoint:
            return PushProvider.FCM
        elif 'webpush' in endpoint or 'mozilla' in endpoint or 'chrome' in endpoint:
            return PushProvider.WEB_PUSH
        else:
            # Por padrão, usar Web Push
            return PushProvider.WEB_PUSH

    def _send_web_push(self, subscription: PushSubscription, payload: Dict[str, Any],
                      message: PushMessage) -> bool:
        """Enviar via Web Push"""
        try:
            if not self.config['web_push']['enabled']:
                return False

            # Preparar dados
            data = {
                'title': message.title,
                'body': message.body,
                'icon': message.icon,
                'badge': message.badge,
                'image': message.image,
                'click_action': message.click_action,
                'data': message.data,
                'tag': message.notification_type.value,
                'timestamp': int(time.time())
            }

            # Enviar usando pywebpush
            pywebpush(
                webpush_subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': subscription.keys
                },
                data=json.dumps(data),
                vapid_private_key=self.config['web_push']['vapid_private_key'],
                vapid_claims={
                    'aud': subscription.endpoint,
                    'exp': int(time.time()) + message.ttl,
                    'sub': self.config['web_push']['vapid_subject']
                }
            )

            return True

        except Exception as e:
            logger.error(f"Erro no Web Push para {subscription.id}: {e}")
            return False

    def _send_fcm_push(self, subscription: PushSubscription, payload: Dict[str, Any],
                      message: PushMessage) -> bool:
        """Enviar via Firebase Cloud Messaging"""
        try:
            if not self.config['firebase']['enabled']:
                return False

            # Extrair token FCM do endpoint ou keys
            fcm_token = self._extract_fcm_token(subscription)

            if not fcm_token:
                logger.warning(f"Token FCM não encontrado para {subscription.id}")
                return False

            # Preparar payload FCM
            fcm_payload = {
                'to': fcm_token,
                'notification': {
                    'title': message.title,
                    'body': message.body,
                    'icon': message.icon,
                    'badge': message.badge,
                    'image': message.image,
                    'click_action': message.click_action,
                    'sound': message.sound,
                    'tag': message.notification_type.value
                },
                'data': {
                    'type': message.notification_type.value,
                    'timestamp': str(int(time.time())),
                    **message.data
                },
                'priority': message.priority,
                'time_to_live': message.ttl
            }

            # Headers
            headers = {
                'Authorization': f'key={self.config["firebase"]["server_key"]}',
                'Content-Type': 'application/json'
            }

            # Enviar
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                json=fcm_payload,
                headers=headers,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Erro no FCM para {subscription.id}: {e}")
            return False

    def _extract_fcm_token(self, subscription: PushSubscription) -> Optional[str]:
        """Extrair token FCM da subscrição"""
        # Tentar extrair do endpoint
        if 'fcm' in subscription.endpoint.lower():
            # O token pode estar na URL
            parts = subscription.endpoint.split('/')
            if len(parts) > 4:
                return parts[-1]

        # Tentar extrair dos keys
        if 'p256dh' in subscription.keys:
            # Tentar extrair de metadados
            device_info = subscription.device_info
            return device_info.get('fcm_token')

        return None

    def _send_firebase_push(self, subscription: PushSubscription, payload: Dict[str, Any],
                           message: PushMessage) -> bool:
        """Enviar via Firebase (legacy)"""
        # Implementação similar ao FCM mas usando API legacy
        return self._send_fcm_push(subscription, payload, message)

    def create_notification_template(self, notification_type: NotificationType,
                                   data: Dict[str, Any]) -> PushMessage:
        """Criar notificação usando template"""
        template = self.config['templates'].get(notification_type, {
            'title': 'FreqTrade3',
            'body': 'Nova notificação',
            'icon': '/icons/default.png'
        })

        # Formatar templates
        title = template['title'].format(**data)
        body = template['body'].format(**data)

        return PushMessage(
            id=str(uuid.uuid4()),
            title=title,
            body=body,
            icon=template.get('icon', '/icons/default.png'),
            badge=template.get('badge', '/icons/badge.png'),
            image=template.get('image', ''),
            click_action=template.get('click_action', '/dashboard'),
            data=data,
            notification_type=notification_type,
            sound=template.get('sound', 'default'),
            actions=template.get('actions', [])
        )

    def send_trade_notification(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enviar notificação de trade"""
        message = self.create_notification_template(
            NotificationType.TRADE_EXECUTION,
            trade_data
        )

        return self.send_notification(message)

    def send_price_alert(self, symbol: str, price: float, target_price: float,
                        alert_type: str) -> Dict[str, Any]:
        """Enviar alerta de preço"""
        data = {
            'symbol': symbol,
            'price': f"{price:.2f}",
            'target_price': f"{target_price:.2f}",
            'alert_type': alert_type
        }

        message = self.create_notification_template(
            NotificationType.PRICE_ALERT,
            data
        )

        return self.send_notification(message)

    def send_risk_warning(self, warning_type: str, message_text: str,
                         severity: str = 'medium') -> Dict[str, Any]:
        """Enviar aviso de risco"""
        data = {
            'warning_type': warning_type,
            'message': message_text,
            'severity': severity
        }

        message = self.create_notification_template(
            NotificationType.RISK_WARNING,
            data
        )

        # Prioridade baseada na severidade
        if severity == 'critical':
            message.priority = 'high'
            message.sound = 'critical'

        return self.send_notification(message)

    def send_system_notification(self, status: str, message_text: str) -> Dict[str, Any]:
        """Enviar notificação de sistema"""
        data = {
            'status': status,
            'message': message_text
        }

        message = self.create_notification_template(
            NotificationType.SYSTEM_STATUS,
            data
        )

        return self.send_notification(message)

    def _save_message_history(self, message: PushMessage, results: Dict[str, Any]):
        """Salvar histórico de mensagem"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO push_messages
                (id, title, body, icon, badge, image, click_action, data,
                 type, priority, ttl, sent_at, success_count, failure_count, provider_responses)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.id, message.title, message.body, message.icon,
                message.badge, message.image, message.click_action, json.dumps(message.data),
                message.notification_type.value, message.priority, message.ttl,
                datetime.now().isoformat(), results['sent_count'], results['failed_count'],
                json.dumps(results['details'])
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas de push notifications"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total de subscrições ativas
            cursor.execute('''
                SELECT COUNT(*) FROM push_subscriptions WHERE active = 1
            ''')
            active_subscriptions = cursor.fetchone()[0]

            # Mensagens enviadas hoje
            today = datetime.now().date()
            cursor.execute('''
                SELECT COUNT(*) FROM push_messages
                WHERE DATE(sent_at) = ?
            ''', (today.isoformat(),))
            messages_today = cursor.fetchone()[0]

            # Taxa de sucesso
            cursor.execute('''
                SELECT
                    SUM(success_count) as total_success,
                    SUM(failure_count) as total_failure
                FROM push_messages
                WHERE DATE(sent_at) = ?
            ''', (today.isoformat(),))

            stats_row = cursor.fetchone()
            total_success = stats_row[0] or 0
            total_failure = stats_row[1] or 0

            success_rate = (total_success / (total_success + total_failure) * 100) if (total_success + total_failure) > 0 else 0

            # Por tipo de notificação
            cursor.execute('''
                SELECT type, COUNT(*)
                FROM push_messages
                WHERE DATE(sent_at) = ?
                GROUP BY type
            ''', (today.isoformat(),))

            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()

            return {
                'active_subscriptions': active_subscriptions,
                'messages_today': messages_today,
                'success_rate': round(success_rate, 2),
                'by_type': by_type,
                'total_sent': total_success,
                'total_failed': total_failure
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}

    def get_vapid_public_key(self) -> str:
        """Obter chave pública VAPID"""
        return self.config['web_push']['vapid_public_key']

    def register_service_worker(self) -> str:
        """Obter URL do Service Worker"""
        service_worker_path = os.path.join(self.push_data_dir, 'service-worker.js')
        return f'/{service_worker_path.replace(os.sep, "/").replace("push_data/", "push_data/")}'

# API para integração
def create_push_notification_system():
    """Criar instância do sistema de push notifications"""
    return PushNotificationSystem()

if __name__ == "__main__":
    # Teste do sistema de push
    push_system = create_push_notification_system()

    # Obter chave pública VAPID
    vapid_key = push_system.get_vapid_public_key()
    print(f"Chave VAPID: {vapid_key[:20]}...")

    # Teste de notificação
    trade_data = {
        'side': 'BUY',
        'quantity': '0.001',
        'symbol': 'BTC/USDT',
        'price': '45000.00'
    }

    result = push_system.send_trade_notification(trade_data)
    print(f"Resultado: {result}")

    # Estatísticas
    stats = push_system.get_statistics()
    print(f"Estatísticas: {stats}")
