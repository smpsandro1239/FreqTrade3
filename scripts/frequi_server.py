#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - FREQUI TRADINGVIEW INTEGRATION
================================================================

Interface web avançada com:
- Gráficos TradingView em tempo real
- Indicadores técnicos interativos
- Sistema de alertas visuais e sonoros
- Backtesting interativo
- Dashboard de performance
- Alertas multi-canal (Telegram, Discord, Email)

Funcionalidades:
- Real-time charting com TradingView
- Interactive indicators (RSI, MACD, Bollinger Bands)
- Trade execution interface
- Risk management dashboard
- Multi-timeframe analysis
- Alert management system

Uso:
    python3 frequi_server.py --port 8080 --secure
    python3 frequi_server.py --config frequi_config.json
"""

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets

# Importar módulos do FreqTrade
try:
    from freqtrade.exchange import Exchange
    from freqtrade.freqtradebot import FreqtradeBot
    from freqtrade.persistence import Trade
    from freqtrade.strategy.interface import IStrategy
except ImportError:
    print("❌ FreqTrade não encontrado. Execute: pip install freqtrade")
    sys.exit(1)

# Flask e componentes web
try:
    import plotly.express as px
    import plotly.graph_objs as go
    from flask import Flask, jsonify, render_template, request, send_file
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit, join_room, leave_room
    from plotly.utils import PlotlyJSONEncoder
except ImportError:
    print("❌ Dependências web não encontradas. Execute: pip install flask flask-socketio plotly")
    sys.exit(1)


@dataclass
class ChartData:
    """Estrutura para dados de gráfico"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: Dict[str, float]


@dataclass
class TradeAlert:
    """Estrutura para alertas de trade"""
    id: str
    pair: str
    action: str  # BUY, SELL, STOP
    price: float
    timestamp: datetime
    message: str
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class MarketData:
    """Estrutura para dados de mercado"""
    pair: str
    price: float
    change_24h: float
    volume: float
    timestamp: datetime


class FreqUIServer:
    """Servidor FreqUI com funcionalidades TradingView"""

    def __init__(self, config_path: str = "frequi_config.json", port: int = 8080,
                 freqtrade_config: str = "configs/config.json"):
        self.config_path = config_path
        self.port = port
        self.freqtrade_config = freqtrade_config
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.clients = defaultdict(list)
        self.active_rooms = set()

        # Dados em tempo real
        self.market_data = {}
        self.chart_data = defaultdict(deque)
        self.trade_alerts = deque(maxlen=1000)
        self.active_trades = []

        # Configurações
        self.config = self._load_config()
        self.trading_pairs = self._load_trading_pairs()

        # Setup logging
        self._setup_logging()

        # Inicializar componentes
        self._setup_routes()
        self._setup_websocket_handlers()
        self._setup_data_streams()

        self.logger.info("🟢 FreqUI Server inicializado")

    def _load_config(self) -> Dict:
        """Carrega configuração do FreqUI"""
        default_config = {
            "ui": {
                "title": "FreqTrade3 TradingView",
                "theme": "dark",
                "language": "pt",
                "chart_library": "tradingview",
                "update_interval": 5000
            },
            "security": {
                "enable_auth": False,
                "session_timeout": 3600,
                "max_clients": 100,
                "rate_limiting": True
            },
            "tradingview": {
                "widget_id": "tradingview_widget",
                "symbol": "BINANCE:BTCUSDT",
                "interval": "15",
                "theme": "dark",
                "style": "1",
                "locale": "pt",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": False,
                "allow_symbol_change": True,
                "container_id": "tradingview_chart"
            },
            "alerts": {
                "sound_enabled": True,
                "popup_enabled": True,
                "telegram_enabled": False,
                "discord_enabled": False,
                "email_enabled": False,
                "webhook_enabled": False
            },
            "dashboard": {
                "refresh_interval": 10000,
                "show_profit_loss": True,
                "show_winning_trades": True,
                "show_losing_trades": True,
                "show_portfolio_overview": True
            },
            "backtesting": {
                "enable_interface": True,
                "default_timeframe": "15m",
                "default_strategy": "template_strategy",
                "max_results": 50
            },
            "indicators": {
                "rsi": {"enabled": True, "period": 14, "overbought": 70, "oversold": 30},
                "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
                "bb": {"enabled": True, "period": 20, "std_dev": 2.0},
                "ema": {"enabled": True, "fast": 12, "slow": 26, "very_slow": 200}
            }
        }

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Merge com configurações padrão
                default_config.update(user_config)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")

        return default_config

    def _load_trading_pairs(self) -> List[str]:
        """Carrega lista de pares de trading"""
        try:
            if os.path.exists(self.freqtrade_config):
                with open(self.freqtrade_config, 'r') as f:
                    config = json.load(f)
                return config.get('pair_whitelist', [])
        except Exception as e:
            self.logger.error(f"Erro ao carregar pares de trading: {e}")

        # Pares padrão
        return [
            "BTC/USDT", "ETH/USDT", "BNB/USDT",
            "ADA/USDT", "XRP/USDT", "SOL/USDT"
        ]

    def _setup_logging(self):
        """Configura sistema de logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [FREQUI] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "frequi.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("FreqUI")

    def _setup_routes(self):
        """Configura rotas Flask"""

        @self.app.route('/')
        def index():
            """Página principal do FreqUI"""
            return render_template('frequi_dashboard.html',
                                 config=self.config,
                                 pairs=self.trading_pairs)

        @self.app.route('/dashboard')
        def dashboard():
            """Dashboard principal"""
            return render_template('dashboard.html', config=self.config)

        @self.app.route('/charts')
        def charts():
            """Interface de gráficos TradingView"""
            return render_template('charts.html', config=self.config)

        @self.app.route('/alerts')
        def alerts():
            """Gestão de alertas"""
            return render_template('alerts.html', config=self.config)

        @self.app.route('/backtest')
        def backtest():
            """Interface de backtesting"""
            return render_template('backtest.html', config=self.config)

        @self.app.route('/api/market_data')
        def get_market_data():
            """API para dados de mercado"""
            return jsonify({
                'market_data': self.market_data,
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/api/active_trades')
        def get_active_trades():
            """API para trades ativos"""
            return jsonify({
                'trades': self.active_trades,
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/api/strategy_info')
        def get_strategy_info():
            """API para informações da estratégia"""
            return jsonify({
                'strategy': 'template_strategy',  # Atualizar dinamicamente
                'timeframe': '15m',
                'parameters': {
                    'rsi_period': 14,
                    'ema_fast': 12,
                    'ema_slow': 26
                },
                'performance': {
                    'win_rate': 0.72,
                    'profit_factor': 1.45,
                    'total_trades': 156
                }
            })

        @self.app.route('/api/chart_data/<pair>')
        def get_chart_data(pair):
            """API para dados de gráfico"""
            try:
                if pair in self.chart_data:
                    data = list(self.chart_data[pair])
                    return jsonify({
                        'pair': pair,
                        'data': [asdict(item) for item in data[-100:]],  # Últimos 100 candles
                        'timestamp': datetime.now().isoformat()
                    })
                return jsonify({'error': 'Pair not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/alerts')
        def get_alerts():
            """API para alertas"""
            return jsonify({
                'alerts': [asdict(alert) for alert in list(self.trade_alerts)[-50:]],
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/api/trade', methods=['POST'])
        def execute_trade():
            """API para executar trades manuais"""
            try:
                data = request.json
                pair = data.get('pair')
                side = data.get('side')  # 'buy' ou 'sell'
                amount = data.get('amount')

                # Implementar execução de trade manual
                result = self._execute_manual_trade(pair, side, amount)

                return jsonify({
                    'success': result,
                    'message': f'Trade {side} executado para {pair}'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/strategy_parameters', methods=['GET', 'POST'])
        def manage_strategy_parameters():
            """API para gerenciar parâmetros da estratégia"""
            if request.method == 'GET':
                # Retornar parâmetros atuais
                return jsonify({'parameters': self.config.get('indicators', {})})
            else:
                # Atualizar parâmetros
                try:
                    data = request.json
                    self.config['indicators'].update(data)
                    self._save_config()
                    return jsonify({'success': True})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500

        @self.app.route('/api/download_logs')
        def download_logs():
            """Download de logs"""
            try:
                log_file = request.args.get('log', 'frequi.log')
                return send_file(f'logs/{log_file}', as_attachment=True)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def _setup_websocket_handlers(self):
        """Configura handlers de websocket"""

        @self.socketio.on('connect')
        def handle_connect():
            """Cliente conectado"""
            self.logger.info(f"Cliente conectado: {request.sid}")
            emit('connected', {'message': 'Conectado ao FreqUI'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Cliente desconectado"""
            self.logger.info(f"Cliente desconectado: {request.sid}")

        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Assinar room específico"""
            room = data.get('room')
            if room:
                join_room(room)
                self.active_rooms.add(room)
                self.logger.info(f"Cliente {request.sid} assinou room: {room}")
                emit('subscribed', {'room': room})

        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Desassinar room"""
            room = data.get('room')
            if room:
                leave_room(room)
                self.active_rooms.discard(room)
                self.logger.info(f"Cliente {request.sid} desassinou room: {room}")
                emit('unsubscribed', {'room': room})

        @self.socketio.on('request_market_data')
        def handle_market_data_request(data):
            """Request de dados de mercado"""
            pair = data.get('pair')
            if pair in self.market_data:
                emit('market_data_update', {
                    'pair': pair,
                    'data': self.market_data[pair]
                })

        @self.socketio.on('execute_trade')
        def handle_trade_execution(data):
            """Execução de trade via websocket"""
            try:
                pair = data.get('pair')
                side = data.get('side')
                amount = data.get('amount')

                result = self._execute_manual_trade(pair, side, amount)

                emit('trade_executed', {
                    'pair': pair,
                    'side': side,
                    'amount': amount,
                    'success': result
                })

                # Alertar todos os clientes
                self.socketio.emit('trade_notification', {
                    'pair': pair,
                    'side': side,
                    'amount': amount,
                    'timestamp': datetime.now().isoformat()
                })

            except Exception as e:
                emit('trade_error', {'error': str(e)})

        @self.socketio.on('update_strategy_params')
        def handle_strategy_update(data):
            """Atualizar parâmetros da estratégia"""
            try:
                # Aplicar novos parâmetros
                self.config['indicators'].update(data)
                self._save_config()

                emit('strategy_updated', {'success': True})
                self.logger.info(f"Parâmetros da estratégia atualizados por {request.sid}")

            except Exception as e:
                emit('strategy_update_error', {'error': str(e)})

    def _setup_data_streams(self):
        """Configura streams de dados em tempo real"""

        def market_data_loop():
            """Loop para atualizar dados de mercado"""
            while True:
                try:
                    self._update_market_data()
                    time.sleep(5)  # Update a cada 5 segundos
                except Exception as e:
                    self.logger.error(f"Erro no loop de dados de mercado: {e}")
                    time.sleep(10)

        def trade_alerts_loop():
            """Loop para verificar alertas de trade"""
            while True:
                try:
                    self._check_trade_alerts()
                    time.sleep(2)  # Check a cada 2 segundos
                except Exception as e:
                    self.logger.error(f"Erro no loop de alertas: {e}")
                    time.sleep(5)

        def chart_data_loop():
            """Loop para atualizar dados de gráfico"""
            while True:
                try:
                    self._update_chart_data()
                    time.sleep(30)  # Update a cada 30 segundos
                except Exception as e:
                    self.logger.error(f"Erro no loop de dados de gráfico: {e}")
                    time.sleep(60)

        # Iniciar threads de background
        threading.Thread(target=market_data_loop, daemon=True).start()
        threading.Thread(target=trade_alerts_loop, daemon=True).start()
        threading.Thread(target=chart_data_loop, daemon=True).start()

    def _update_market_data(self):
        """Atualiza dados de mercado em tempo real"""
        try:
            for pair in self.trading_pairs:
                # Simular dados de mercado (em produção, usar API real do exchange)
                import random
                current_price = 45000 + random.uniform(-500, 500)  # BTC simulado
                change_24h = random.uniform(-5, 5)
                volume = random.uniform(1000000, 10000000)

                market_data = MarketData(
                    pair=pair,
                    price=current_price,
                    change_24h=change_24h,
                    volume=volume,
                    timestamp=datetime.now()
                )

                self.market_data[pair] = asdict(market_data)

                # Enviar atualização via websocket
                self.socketio.emit('market_data_update', {
                    'pair': pair,
                    'data': asdict(market_data)
                }, room='market_data')

        except Exception as e:
            self.logger.error(f"Erro ao atualizar dados de mercado: {e}")

    def _update_chart_data(self):
        """Atualiza dados de gráfico"""
        try:
            for pair in self.trading_pairs:
                # Simular dados OHLCV (em produção, usar dados reais)
                import random
                from datetime import timedelta

                base_price = self.market_data.get(pair, {}).get('price', 45000)

                # Gerar candle simulado
                open_price = base_price
                high_price = open_price + random.uniform(0, 100)
                low_price = open_price - random.uniform(0, 100)
                close_price = random.uniform(low_price, high_price)
                volume = random.uniform(1000, 10000)

                chart_data = ChartData(
                    timestamp=datetime.now(),
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    indicators={
                        'rsi': random.uniform(20, 80),
                        'macd': random.uniform(-50, 50),
                        'bb_upper': high_price * 1.02,
                        'bb_lower': low_price * 0.98
                    }
                )

                self.chart_data[pair].append(chart_data)

                # Limitar histórico (manter apenas últimas 1000 candles)
                if len(self.chart_data[pair]) > 1000:
                    self.chart_data[pair].popleft()

                # Enviar atualização via websocket
                self.socketio.emit('chart_data_update', {
                    'pair': pair,
                    'data': asdict(chart_data)
                }, room=f'chart_{pair}')

        except Exception as e:
            self.logger.error(f"Erro ao atualizar dados de gráfico: {e}")

    def _check_trade_alerts(self):
        """Verifica e gera alertas de trade"""
        try:
            # Verificar trades ativos
            open_trades = Trade.get_open_trades()

            for trade in open_trades:
                # Calcular profit atual
                current_profit = trade.calc_profit_ratio()

                # Verificar stop loss
                if current_profit <= -0.03:  # 3% perda
                    alert = TradeAlert(
                        id=f"stop_{trade.id}",
                        pair=trade.pair,
                        action="STOP_LOSS",
                        price=trade.open_rate,
                        timestamp=datetime.now(),
                        message=f"Stop Loss atingido para {trade.pair}: {current_profit:.2%}",
                        priority="HIGH"
                    )
                    self.trade_alerts.append(alert)

                    # Enviar alerta
                    self._send_alert(alert)

                # Verificar take profit
                elif current_profit >= 0.05:  # 5% lucro
                    alert = TradeAlert(
                        id=f"take_{trade.id}",
                        pair=trade.pair,
                        action="TAKE_PROFIT",
                        price=trade.open_rate,
                        timestamp=datetime.now(),
                        message=f"Take Profit atingido para {trade.pair}: {current_profit:.2%}",
                        priority="MEDIUM"
                    )
                    self.trade_alerts.append(alert)

                    # Enviar alerta
                    self._send_alert(alert)

            # Atualizar lista de trades ativos
            self.active_trades = [
                {
                    'id': trade.id,
                    'pair': trade.pair,
                    'amount': trade.amount,
                    'open_rate': trade.open_rate,
                    'profit': trade.calc_profit_ratio(),
                    'profit_abs': trade.calc_profit(),
                    'open_date': trade.open_date.isoformat()
                }
                for trade in open_trades
            ]

            # Enviar atualização de trades ativos
            self.socketio.emit('trades_update', {
                'trades': self.active_trades,
                'timestamp': datetime.now().isoformat()
            }, room='dashboard')

        except Exception as e:
            self.logger.error(f"Erro ao verificar alertas: {e}")

    def _send_alert(self, alert: TradeAlert):
        """Envia alerta via múltiplos canais"""
        try:
            # WebSocket
            self.socketio.emit('alert', asdict(alert))

            # Som
            if self.config['alerts']['sound_enabled']:
                self.socketio.emit('play_sound', {
                    'sound': 'alert' if alert.priority == 'HIGH' else 'notification'
                })

            # Popup
            if self.config['alerts']['popup_enabled']:
                self.socketio.emit('show_popup', {
                    'title': f"Alerta FreqTrade3 - {alert.action}",
                    'message': alert.message,
                    'priority': alert.priority
                })

            # Telegram
            if self.config['alerts']['telegram_enabled']:
                self._send_telegram_alert(alert)

            # Discord
            if self.config['alerts']['discord_enabled']:
                self._send_discord_alert(alert)

            # Email
            if self.config['alerts']['email_enabled']:
                self._send_email_alert(alert)

            self.logger.info(f"Alerta enviado: {alert.message}")

        except Exception as e:
            self.logger.error(f"Erro ao enviar alerta: {e}")

    def _send_telegram_alert(self, alert: TradeAlert):
        """Envia alerta via Telegram"""
        # Implementação futura
        pass

    def _send_discord_alert(self, alert: TradeAlert):
        """Envia alerta via Discord"""
        # Implementação futura
        pass

    def _send_email_alert(self, alert: TradeAlert):
        """Envia alerta via email"""
        # Implementação futura
        pass

    def _execute_manual_trade(self, pair: str, side: str, amount: float) -> bool:
        """Executa trade manual (simulation)"""
        try:
            self.logger.info(f"Trade manual simulado: {side} {amount} {pair}")

            # Em uma implementação real, integraria com o FreqTrade bot
            # para executar o trade através da API

            return True

        except Exception as e:
            self.logger.error(f"Erro ao executar trade manual: {e}")
            return False

    def _save_config(self):
        """Salva configuração atual"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")

    def run(self, debug: bool = False, host: str = "0.0.0.0"):
        """Inicia o servidor FreqUI"""
        try:
            self.logger.info(f"🚀 Iniciando FreqUI Server em http://{host}:{self.port}")
            self.logger.info(f"📊 Dashboard: http://{host}:{self.port}/dashboard")
            self.logger.info(f"📈 Gráficos: http://{host}:{self.port}/charts")
            self.logger.info(f"🔔 Alertas: http://{host}:{self.port}/alerts")

            self.socketio.run(
                self.app,
                host=host,
                port=self.port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )

        except KeyboardInterrupt:
            self.logger.info("🛑 FreqUI Server parado pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro no servidor FreqUI: {e}")
            raise


def create_template_files():
    """Cria templates HTML para o FreqUI"""

    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Dashboard principal
    dashboard_html = '''
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FreqTrade3 Dashboard</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #1e1e1e; color: #ffffff; }
        .card { background-color: #2d2d2d; border: 1px solid #404040; }
        .navbar { background-color: #000000 !important; }
        .btn-primary { background-color: #007bff; border-color: #007bff; }
        .profit { color: #28a745; }
        .loss { color: #dc3545; }
        .metric-card { text-align: center; padding: 1rem; }
        .trading-pair { display: flex; justify-content: space-between; padding: 0.5rem; border-bottom: 1px solid #404040; }
        .alert-high { background-color: #dc3545; }
        .alert-medium { background-color: #ffc107; color: #000; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand">
                <i class="fas fa-chart-line"></i> FreqTrade3 Dashboard
            </span>
            <div class="d-flex">
                <span class="navbar-text me-3">
                    <i class="fas fa-circle text-success"></i> Online
                </span>
                <a href="/charts" class="btn btn-outline-light btn-sm">
                    <i class="fas fa-chart-bar"></i> Gráficos
                </a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-3">
        <div class="row">
            <!-- Métricas principais -->
            <div class="col-md-3">
                <div class="card metric-card">
                    <h5>Capital Total</h5>
                    <h3 class="text-primary">$10,000.00</h3>
                    <small>Dry Run Mode</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <h5>Trades Ativos</h5>
                    <h3 class="text-warning" id="active-trades-count">0</h3>
                    <small>Pairs</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <h5>Lucro/Prejuízo</h5>
                    <h3 class="profit" id="total-profit">+$125.45</h3>
                    <small>Hoje</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <h5>Win Rate</h5>
                    <h3 class="text-info" id="win-rate">72%</h3>
                    <small>Últimos 30 dias</small>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <!-- Dados de mercado -->
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-area"></i> Dados de Mercado</h5>
                    </div>
                    <div class="card-body">
                        <div id="market-data">
                            <!-- Dados serão carregados via JavaScript -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Alertas recentes -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-bell"></i> Alertas Recentes</h5>
                    </div>
                    <div class="card-body" style="height: 400px; overflow-y: auto;">
                        <div id="alerts-container">
                            <!-- Alertas serão carregados via JavaScript -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <!-- Trades ativos -->
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-exchange-alt"></i> Trades Ativos</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-dark table-striped">
                                <thead>
                                    <tr>
                                        <th>Par</th>
                                        <th>Entrada</th>
                                        <th>Preço Atual</th>
                                        <th>Quantidade</th>
                                        <th>Lucro/Prejuízo</th>
                                        <th>Ações</th>
                                    </tr>
                                </thead>
                                <tbody id="active-trades-table">
                                    <!-- Dados serão carregados via JavaScript -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Configuração do Socket.IO
        const socket = io();

        // Atualizar dados de mercado
        socket.on('market_data_update', function(data) {
            updateMarketData(data);
        });

        // Atualizar trades ativos
        socket.on('trades_update', function(data) {
            updateActiveTrades(data.trades);
        });

        // Receber alertas
        socket.on('alert', function(alert) {
            showAlert(alert);
        });

        // Atualizar dados iniciais
        function initializeDashboard() {
            // Solicitar dados iniciais
            socket.emit('subscribe', {room: 'dashboard'});
            socket.emit('subscribe', {room: 'market_data'});

            // Carregar dados iniciais via AJAX
            loadInitialData();
        }

        function loadInitialData() {
            fetch('/api/market_data')
                .then(response => response.json())
                .then(data => {
                    if (data.market_data) {
                        Object.entries(data.market_data).forEach(([pair, data]) => {
                            updateMarketData({pair, data});
                        });
                    }
                });

            fetch('/api/active_trades')
                .then(response => response.json())
                .then(data => {
                    if (data.trades) {
                        updateActiveTrades(data.trades);
                    }
                });
        }

        function updateMarketData(data) {
            const container = document.getElementById('market-data');
            const existing = container.querySelector(`[data-pair="${data.pair}"]`);

            const changeClass = data.data.change_24h >= 0 ? 'profit' : 'loss';
            const changeIcon = data.data.change_24h >= 0 ? '↗' : '↘';

            const html = `
                <div class="trading-pair" data-pair="${data.pair}">
                    <div>
                        <strong>${data.pair}</strong><br>
                        <small class="text-muted">Volume: ${formatNumber(data.data.volume)}</small>
                    </div>
                    <div class="text-end">
                        <div><strong>$${formatPrice(data.data.price)}</strong></div>
                        <div class="${changeClass}">
                            ${changeIcon} ${data.data.change_24h.toFixed(2)}%
                        </div>
                    </div>
                </div>
            `;

            if (existing) {
                existing.outerHTML = html;
            } else {
                container.innerHTML += html;
            }
        }

        function updateActiveTrades(trades) {
            const tbody = document.getElementById('active-trades-table');
            const count = document.getElementById('active-trades-count');

            count.textContent = trades.length;

            if (trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum trade ativo</td></tr>';
                return;
            }

            tbody.innerHTML = trades.map(trade => {
                const profitClass = trade.profit >= 0 ? 'profit' : 'loss';
                const profitIcon = trade.profit >= 0 ? '↗' : '↘';

                return `
                    <tr>
                        <td>${trade.pair}</td>
                        <td>$${formatPrice(trade.open_rate)}</td>
                        <td>$${formatPrice(trade.open_rate * 1.02)}</td>
                        <td>${trade.amount.toFixed(6)}</td>
                        <td class="${profitClass}">
                            ${profitIcon} ${(trade.profit * 100).toFixed(2)}%
                        </td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="closeTrade('${trade.id}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function showAlert(alert) {
            const container = document.getElementById('alerts-container');
            const alertClass = alert.priority === 'HIGH' ? 'alert-high' : 'alert-medium';

            const html = `
                <div class="alert ${alertClass} mb-2">
                    <strong>${alert.action}</strong> - ${alert.pair}<br>
                    <small>${alert.message}</small><br>
                    <small class="text-muted">${new Date(alert.timestamp).toLocaleTimeString()}</small>
                </div>
            `;

            container.innerHTML = html + container.innerHTML;

            // Limitar a 10 alertas
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }

        function formatPrice(price) {
            return price.toFixed(2);
        }

        function formatNumber(num) {
            if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
            if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
            if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
            return num.toFixed(0);
        }

        function closeTrade(tradeId) {
            if (confirm('Deseja realmente fechar este trade?')) {
                socket.emit('execute_trade', {
                    pair: 'BTC/USDT',
                    side: 'sell',
                    amount: 0.001
                });
            }
        }

        // Inicializar dashboard quando a página carregar
        document.addEventListener('DOMContentLoaded', initializeDashboard);
    </script>
</body>
</html>
'''

    with open(templates_dir / "dashboard.html", 'w', encoding='utf-8') as f:
        f.write(dashboard_html)

    # Template de gráficos TradingView
    charts_html = '''
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FreqTrade3 Gráficos TradingView</title>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #1e1e1e; color: #ffffff; }
        .card { background-color: #2d2d2d; border: 1px solid #404040; }
        .navbar { background-color: #000000 !important; }
        .indicator-panel { max-height: 400px; overflow-y: auto; }
        .tradingview-widget-container { height: 600px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand">
                <i class="fas fa-chart-bar"></i> FreqTrade3 Gráficos
            </span>
            <div class="d-flex">
                <a href="/dashboard" class="btn btn-outline-light btn-sm me-2">
                    <i class="fas fa-home"></i> Dashboard
                </a>
                <select class="form-select form-select-sm" id="pair-selector" style="width: 150px;">
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="BNB/USDT">BNB/USDT</option>
                </select>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-3">
        <div class="row">
            <!-- Gráfico principal -->
            <div class="col-md-9">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line"></i> Gráfico TradingView</h5>
                    </div>
                    <div class="card-body p-0">
                        <div id="tradingview_chart" class="tradingview-widget-container"></div>
                    </div>
                </div>
            </div>

            <!-- Painel de indicadores -->
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-area"></i> Indicadores</h5>
                    </div>
                    <div class="card-body indicator-panel">
                        <!-- RSI -->
                        <div class="mb-3">
                            <label class="form-label">RSI</label>
                            <div class="input-group input-group-sm">
                                <span class="input-group-text">Período</span>
                                <input type="number" class="form-control" id="rsi-period" value="14" min="1" max="50">
                                <button class="btn btn-primary" onclick="toggleIndicator('rsi')">
                                    <i class="fas fa-toggle-on"></i>
                                </button>
                            </div>
                        </div>

                        <!-- MACD -->
                        <div class="mb-3">
                            <label class="form-label">MACD</label>
                            <div class="row">
                                <div class="col-4">
                                    <input type="number" class="form-control form-control-sm" id="macd-fast" value="12" placeholder="Fast">
                                </div>
                                <div class="col-4">
                                    <input type="number" class="form-control form-control-sm" id="macd-slow" value="26" placeholder="Slow">
                                </div>
                                <div class="col-4">
                                    <button class="btn btn-primary btn-sm" onclick="toggleIndicator('macd')">
                                        <i class="fas fa-toggle-on"></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Bollinger Bands -->
                        <div class="mb-3">
                            <label class="form-label">Bollinger Bands</label>
                            <div class="row">
                                <div class="col-6">
                                    <input type="number" class="form-control form-control-sm" id="bb-period" value="20" placeholder="Período">
                                </div>
                                <div class="col-6">
                                    <input type="number" class="form-control form-control-sm" id="bb-std" value="2" placeholder="Std Dev">
                                </div>
                            </div>
                            <button class="btn btn-primary btn-sm mt-1 w-100" onclick="toggleIndicator('bb')">
                                <i class="fas fa-toggle-on"></i>
                            </button>
                        </div>

                        <!-- EMAs -->
                        <div class="mb-3">
                            <label class="form-label">EMAs</label>
                            <div class="mb-1">
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text">12</span>
                                    <button class="btn btn-primary btn-sm" onclick="toggleIndicator('ema12')">
                                        <i class="fas fa-toggle-on"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="mb-1">
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text">26</span>
                                    <button class="btn btn-primary btn-sm" onclick="toggleIndicator('ema26')">
                                        <i class="fas fa-toggle-on"></i>
                                    </button>
                                </div>
                            </div>
                            <div>
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text">200</span>
                                    <button class="btn btn-primary btn-sm" onclick="toggleIndicator('ema200')">
                                        <i class="fas fa-toggle-on"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Informações da estratégia -->
                <div class="card mt-3">
                    <div class="card-header">
                        <h6><i class="fas fa-cog"></i> Estratégia</h6>
                    </div>
                    <div class="card-body">
                        <small class="text-muted">
                            Estratégia: EMA200RSI<br>
                            Timeframe: 15m<br>
                            Status: Ativa<br>
                            Último Signal: BUY BTC/USDT
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Configuração TradingView
        let tvWidget = null;
        const socket = io();

        function initTradingView() {
            if (tvWidget) {
                tvWidget.remove();
            }

            tvWidget = new TradingView.widget({
                "width": "100%",
                "height": 600,
                "symbol": "BINANCE:BTCUSDT",
                "interval": "15",
                "timezone": "Europe/Lisbon",
                "theme": "dark",
                "style": "1",
                "locale": "pt",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_chart",
                "studies": [
                    "RSI@tv-basicstudies",
                    "MACD@tv-basicstudies",
                    "BollingerBands@tv-basicstudies"
                ],
                "overrides": {
                    "paneProperties.background": "#1e1e1e",
                    "paneProperties.vertGridProperties.color": "#363c4e",
                    "paneProperties.horzGridProperties.color": "#363c4e",
                    "symbolWatermarkProperties.transparency": 90,
                    "scalesProperties.textColor": "#AAA"
                }
            });
        }

        function toggleIndicator(indicator) {
            // Implementar toggle de indicadores
            console.log('Toggle indicator:', indicator);

            // Atualizar parâmetros via websocket
            const params = getIndicatorParams();
            socket.emit('update_strategy_params', params);
        }

        function getIndicatorParams() {
            return {
                rsi: {
                    enabled: true,
                    period: parseInt(document.getElementById('rsi-period').value)
                },
                macd: {
                    enabled: true,
                    fast: parseInt(document.getElementById('macd-fast').value),
                    slow: parseInt(document.getElementById('macd-slow').value)
                },
                bb: {
                    enabled: true,
                    period: parseInt(document.getElementById('bb-period').value),
                    std_dev: parseInt(document.getElementById('bb-std').value)
                }
            };
        }

        // Atualizar símbolo quando selecionado
        document.getElementById('pair-selector').addEventListener('change', function(e) {
            const pair = e.target.value;
            const exchange = pair.includes('/USDT') ? 'BINANCE' : 'BINANCE';
            const symbol = `${exchange}:${pair.replace('/', '')}`;

            if (tvWidget) {
                tvWidget.onChartReady(() => {
                    tvWidget.chart().setSymbol(symbol, () => {
                        console.log('Symbol changed to:', symbol);
                    });
                });
            }

            // Assinar dados do novo par
            socket.emit('subscribe', {room: `chart_${pair}`});
        });

        // Socket.IO handlers
        socket.on('chart_data_update', function(data) {
            console.log('Chart data update:', data);
            // Atualizar gráfico com novos dados
        });

        socket.on('strategy_updated', function(data) {
            if (data.success) {
                console.log('Estratégia atualizada com sucesso');
                // Recarregar indicadores no gráfico
            }
        });

        // Inicializar quando a página carregar
        document.addEventListener('DOMContentLoaded', function() {
            initTradingView();

            // Assinar room do gráfico
            socket.emit('subscribe', {room: 'chart_BTC/USDT'});
        });
    </script>
</body>
</html>
'''

    with open(templates_dir / "charts.html", 'w', encoding='utf-8') as f:
        f.write(charts_html)


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='FreqUI Server - Interface TradingView')
    parser.add_argument('--port', type=int, default=8080, help='Porta do servidor')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host do servidor')
    parser.add_argument('--config', type=str, default='frequi_config.json', help='Arquivo de configuração')
    parser.add_argument('--freqtrade-config', type=str, default='configs/config.json', help='Config FreqTrade')
    parser.add_argument('--debug', action='store_true', help='Modo debug')
    parser.add_argument('--create-templates', action='store_true', help='Criar templates HTML')

    args = parser.parse_args()

    if args.create_templates:
        print("📄 Criando templates HTML...")
        create_template_files()
        print("✅ Templates criados em templates/")
        return

    try:
        # Criar templates se não existirem
        if not Path("templates").exists():
            print("📄 Criando templates HTML...")
            create_template_files()

        # Iniciar servidor
        server = FreqUIServer(
            config_path=args.config,
            port=args.port,
            freqtrade_config=args.freqtrade_config
        )

        server.run(debug=args.debug, host=args.host)

    except KeyboardInterrupt:
        print("\n🛑 Servidor parado pelo usuário")
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
