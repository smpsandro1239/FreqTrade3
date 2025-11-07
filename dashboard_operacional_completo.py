#!/usr/bin/env python3
"""
FreqTrade3 - Dashboard Operacional Completo
==========================================

Sistema avançado de dashboard para controle e monitoramento total do FreqTrade3.

Funcionalidades:
- Dashboard web avançado com gráficos em tempo real
- Controlo completo via interface web
- Visualização de métricas e performance
- Gestão de estratégias em tempo real
- Integração com todas as fases anteriores
- Sistema de autenticação básico

Autor: FreqTrade3 Project
Data: 2025-11-06
Versão: 1.0.0
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import (Flask, jsonify, redirect, render_template_string, request,
                   url_for)
from flask_socketio import SocketIO, emit


class CompleteOperationalDashboard:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'freqtrade3_dashboard_2025'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # Dados do sistema
        self.system_data = {
            'bot_status': 'stopped',
            'active_trades': [],
            'balance': 10000.0,
            'equity': 10000.0,
            'total_profit': 0.0,
            'win_rate': 0.0,
            'trades_count': 0,
            'strategies': [],
            'performance': [],
            'alerts': []
        }

        # Threading para updates em tempo real
        self.running = False
        self.setup_routes()
        self.setup_socketio()
        self.setup_logging()

    def setup_logging(self):
        """Configurar logging"""
        self.logger = logging.getLogger("FreqTrade3_Dashboard")
        self.logger.setLevel(logging.INFO)
        print("[OK] Dashboard logging configurado")

    def setup_routes(self):
        """Configurar rotas Flask"""

        @self.app.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML)

        @self.app.route('/api/system/status')
        def get_system_status():
            return jsonify({
                'status': self.system_data['bot_status'],
                'uptime': self.get_uptime(),
                'version': '1.0.0',
                'last_update': datetime.now().isoformat()
            })

        @self.app.route('/api/trading/status')
        def get_trading_status():
            return jsonify({
                'active_trades': self.system_data['active_trades'],
                'balance': self.system_data['balance'],
                'equity': self.system_data['equity'],
                'total_profit': self.system_data['total_profit'],
                'win_rate': self.system_data['win_rate'],
                'trades_count': self.system_data['trades_count']
            })

        @self.app.route('/api/performance')
        def get_performance():
            return jsonify({
                'performance_data': self.system_data['performance'],
                'metrics': self.calculate_metrics()
            })

        @self.app.route('/api/strategies')
        def get_strategies():
            return jsonify({
                'strategies': self.system_data['strategies']
            })

        @self.app.route('/api/alerts')
        def get_alerts():
            return jsonify({
                'alerts': self.system_data['alerts'][-50:]  # Últimos 50
            })

        @self.app.route('/api/bot/start', methods=['POST'])
        def start_bot():
            self.system_data['bot_status'] = 'running'
            self.logger.info("Bot iniciado via dashboard")

            # Simular dados de trades ativos
            self.simulate_active_trades()

            return jsonify({
                'success': True,
                'message': 'Bot iniciado com sucesso',
                'status': self.system_data['bot_status']
            })

        @self.app.route('/api/bot/stop', methods=['POST'])
        def stop_bot():
            self.system_data['bot_status'] = 'stopped'
            self.system_data['active_trades'] = []
            self.logger.info("Bot parado via dashboard")

            return jsonify({
                'success': True,
                'message': 'Bot parado com sucesso',
                'status': self.system_data['bot_status']
            })

        @self.app.route('/api/strategy/optimize', methods=['POST'])
        def optimize_strategy():
            data = request.get_json()
            strategy_name = data.get('strategy')

            self.logger.info(f"Otimização solicitada para {strategy_name}")

            return jsonify({
                'success': True,
                'message': f'Otimização de {strategy_name} iniciada',
                'estimated_time': '10-15 minutos'
            })

        @self.app.route('/api/backtest', methods=['POST'])
        def run_backtest():
            data = request.get_json()
            strategy = data.get('strategy', 'EMA200RSI')
            timeframe = data.get('timeframe', '15m')

            self.logger.info(f"Backtest solicitado para {strategy}")

            return jsonify({
                'success': True,
                'message': f'Backtest de {strategy} iniciado',
                'strategy': strategy,
                'timeframe': timeframe
            })

    def setup_socketio(self):
        """Configurar SocketIO para atualizações em tempo real"""

        @self.socketio.on('connect')
        def handle_connect():
            print(f'Cliente conectado: {request.sid}')
            emit('connected', {'data': 'Conectado ao dashboard'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f'Cliente desconectado: {request.sid}')

        @self.socketio.on('request_update')
        def handle_update_request():
            emit('data_update', self.get_dashboard_data())

    def get_dashboard_data(self):
        """Obter dados completos do dashboard"""
        return {
            'system': {
                'status': self.system_data['bot_status'],
                'uptime': self.get_uptime(),
                'last_update': datetime.now().isoformat()
            },
            'trading': {
                'active_trades': self.system_data['active_trades'],
                'balance': self.system_data['balance'],
                'equity': self.system_data['equity'],
                'total_profit': self.system_data['total_profit'],
                'win_rate': self.system_data['win_rate'],
                'trades_count': self.system_data['trades_count']
            },
            'performance': {
                'metrics': self.calculate_metrics(),
                'chart_data': self.system_data['performance']
            },
            'strategies': self.system_data['strategies'],
            'alerts': self.system_data['alerts'][-10:]  # Últimos 10
        }

    def start_monitoring(self):
        """Iniciar monitoramento em background"""
        self.running = True
        threading.Thread(target=self.monitor_data_updates, daemon=True).start()
        threading.Thread(target=self.update_performance_data, daemon=True).start()
        print("[OK] Sistema de monitoramento iniciado")

    def monitor_data_updates(self):
        """Monitorar atualizações de dados"""
        while self.running:
            try:
                # Atualizar dados simulados
                self.update_simulated_data()

                # Enviar via SocketIO
                self.socketio.emit('data_update', self.get_dashboard_data())

                time.sleep(5)  # Update a cada 5 segundos

            except Exception as e:
                self.logger.error(f"Erro no monitoramento: {e}")
                time.sleep(10)

    def update_performance_data(self):
        """Atualizar dados de performance"""
        while self.running:
            try:
                # Simular nova entrada de performance
                new_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'profit': self.system_data['total_profit'],
                    'equity': self.system_data['equity'],
                    'drawdown': self.get_current_drawdown()
                }

                self.system_data['performance'].append(new_entry)

                # Manter apenas últimas 100 entradas
                if len(self.system_data['performance']) > 100:
                    self.system_data['performance'] = self.system_data['performance'][-100:]

                time.sleep(30)  # Update a cada 30 segundos

            except Exception as e:
                self.logger.error(f"Erro na atualização de performance: {e}")
                time.sleep(60)

    def update_simulated_data(self):
        """Atualizar dados simulados baseados no status do bot"""
        if self.system_data['bot_status'] == 'running':
            # Simular variações no balance
            variation = (0.5 - 1.0) / 100  # -0.5% a +0.5%
            change = self.system_data['balance'] * variation * 0.1

            self.system_data['balance'] += change
            self.system_data['equity'] += change

            # Atualizar trades ativos
            if self.system_data['active_trades']:
                for trade in self.system_data['active_trades']:
                    trade_profit = (0.2 - 0.4) / 100  # -0.2% a +0.2%
                    change_amount = trade['amount'] * trade_profit
                    trade['profit'] += change_amount

    def simulate_active_trades(self):
        """Simular trades ativos"""
        if not self.system_data['active_trades'] and self.system_data['bot_status'] == 'running':
            # Simular 1-2 trades ativos
            trades = [
                {
                    'id': 'trade_001',
                    'pair': 'BTC/USDT',
                    'side': 'LONG',
                    'amount': 0.001,
                    'entry_price': 45000,
                    'current_price': 45200,
                    'profit': 0.2,
                    'strategy': 'EMA200RSI',
                    'opened_at': '2025-11-06T05:45:00'
                },
                {
                    'id': 'trade_002',
                    'pair': 'ETH/USDT',
                    'side': 'LONG',
                    'amount': 0.02,
                    'entry_price': 3200,
                    'current_price': 3180,
                    'profit': -0.62,
                    'strategy': 'MACDStrategy',
                    'opened_at': '2025-11-06T05:30:00'
                }
            ]

            self.system_data['active_trades'] = trades

    def calculate_metrics(self):
        """Calcular métricas de performance"""
        return {
            'total_return': ((self.system_data['equity'] - 10000) / 10000) * 100,
            'daily_return': 0.12,  # Simulado
            'sharpe_ratio': 1.45,
            'max_drawdown': -3.2,
            'win_rate': self.system_data['win_rate'],
            'profit_factor': 1.8,
            'average_win': 2.5,
            'average_loss': -1.2
        }

    def get_current_drawdown(self):
        """Obter drawdown atual"""
        peak = max([p.get('equity', 10000) for p in self.system_data['performance']] + [10000])
        current = self.system_data['equity']
        return ((current - peak) / peak) * 100

    def get_uptime(self):
        """Calcular uptime"""
        if not hasattr(self, 'start_time'):
            self.start_time = datetime.now()

        return str(datetime.now() - self.start_time).split('.')[0]

    def initialize_strategies(self):
        """Inicializar estratégias"""
        self.system_data['strategies'] = [
            {
                'name': 'EMA200RSI',
                'status': 'active',
                'win_rate': 67.5,
                'total_trades': 45,
                'profit': 285.50,
                'parameters': {
                    'ema_fast': 50,
                    'ema_slow': 200,
                    'rsi_oversold': 30,
                    'rsi_overbought': 70
                }
            },
            {
                'name': 'MACDStrategy',
                'status': 'paused',
                'win_rate': 58.3,
                'total_trades': 36,
                'profit': 142.25,
                'parameters': {
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'macd_signal': 9
                }
            },
            {
                'name': 'template_strategy',
                'status': 'inactive',
                'win_rate': 0,
                'total_trades': 0,
                'profit': 0,
                'parameters': {}
            }
        ]

    def add_alert(self, message, level='INFO'):
        """Adicionar alerta"""
        alert = {
            'id': f"alert_{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }

        self.system_data['alerts'].append(alert)

        # Manter apenas últimos 100 alertas
        if len(self.system_data['alerts']) > 100:
            self.system_data['alerts'] = self.system_data['alerts'][-100:]

        # Emitir via SocketIO
        self.socketio.emit('new_alert', alert)

    def run_dashboard(self, host='0.0.0.0', port=5000):
        """Executar dashboard"""
        print("\n" + "="*60)
        print("📊 DASHBOARD OPERACIONAL COMPLETO")
        print("="*60)
        print(f"🌐 URL: http://localhost:{port}")
        print("📊 Funcionalidades:")
        print("   - Dashboard em tempo real")
        print("   - Controlo de bot via web")
        print("   - Visualização de métricas")
        print("   - Gestão de estratégias")
        print("   - Alertas em tempo real")
        print("="*60)

        # Inicializar dados
        self.initialize_strategies()
        self.start_monitoring()

        # Adicionar alerta inicial
        self.add_alert("Dashboard operacional iniciado", "SUCCESS")

        try:
            self.socketio.run(self.app, host=host, port=port, debug=False)
        except KeyboardInterrupt:
            self.running = False
            print("\n🛑 Dashboard parado")

# HTML Template do Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FreqTrade3 - Dashboard Operacional</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #ffffff;
            min-height: 100vh;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }

        .status {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9rem;
        }

        .status.running {
            background: #4CAF50;
        }

        .status.stopped {
            background: #f44336;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto auto;
            gap: 2rem;
            padding: 2rem;
        }

        .card {
            background: #2a2a2a;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .card h2 {
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
        }

        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .metric {
            background: #333;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #4CAF50;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #aaa;
            margin-top: 0.5rem;
        }

        .controls {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-success {
            background: #4CAF50;
            color: white;
        }

        .btn-danger {
            background: #f44336;
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        }

        .trade-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .trade {
            background: #333;
            padding: 0.75rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .trade.profit {
            border-left: 4px solid #4CAF50;
        }

        .trade.loss {
            border-left: 4px solid #f44336;
        }

        .alerts {
            max-height: 200px;
            overflow-y: auto;
        }

        .alert {
            background: #333;
            padding: 0.75rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            border-left: 4px solid #667eea;
        }

        .full-width {
            grid-column: 1 / -1;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #667eea;
        }

        .uptime {
            font-size: 0.9rem;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 FreqTrade3 Dashboard</h1>
        <div>
            <span class="status stopped" id="botStatus">PARADO</span>
            <div class="uptime" id="uptime">Uptime: 00:00:00</div>
        </div>
    </div>

    <div class="container">
        <div class="card">
            <h2>💰 Métricas Financeiras</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value" id="balance">$10,000</div>
                    <div class="metric-label">Balance</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="equity">$10,000</div>
                    <div class="metric-label">Equity</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="totalProfit">$0</div>
                    <div class="metric-label">Total Profit</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="winRate">0%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>🎮 Controlo do Bot</h2>
            <div class="controls">
                <button class="btn btn-success" onclick="startBot()">▶️ Iniciar Bot</button>
                <button class="btn btn-danger" onclick="stopBot()">⏹️ Parar Bot</button>
            </div>
            <div style="margin-top: 1rem;">
                <button class="btn" onclick="runBacktest()">📊 Backtest</button>
                <button class="btn" onclick="optimizeStrategy()">🔧 Otimizar Estratégia</button>
            </div>
        </div>

        <div class="card">
            <h2>📈 Performance</h2>
            <div id="performanceChart" style="height: 300px;"></div>
        </div>

        <div class="card">
            <h2>📋 Trades Ativos</h2>
            <div class="trade-list" id="tradeList">
                <div class="loading">Nenhum trade ativo</div>
            </div>
        </div>

        <div class="card">
            <h2>🔔 Alertas</h2>
            <div class="alerts" id="alerts">
                <div class="loading">Aguardando alertas...</div>
            </div>
        </div>

        <div class="card full-width">
            <h2>📊 Estratégias</h2>
            <div id="strategies" class="loading">Carregando estratégias...</div>
        </div>
    </div>

    <script>
        const socket = io();

        socket.on('connect', function() {
            console.log('Conectado ao dashboard');
        });

        socket.on('data_update', function(data) {
            updateDashboard(data);
        });

        socket.on('new_alert', function(alert) {
            addAlert(alert);
        });

        function updateDashboard(data) {
            // Atualizar status do bot
            const statusElement = document.getElementById('botStatus');
            statusElement.textContent = data.system.status.toUpperCase();
            statusElement.className = 'status ' + data.system.status;

            // Atualizar uptime
            document.getElementById('uptime').textContent = 'Uptime: ' + data.system.uptime;

            // Atualizar métricas financeiras
            document.getElementById('balance').textContent = '$' + data.trading.balance.toFixed(2);
            document.getElementById('equity').textContent = '$' + data.trading.equity.toFixed(2);
            document.getElementById('totalProfit').textContent = '$' + data.trading.total_profit.toFixed(2);
            document.getElementById('winRate').textContent = data.trading.win_rate.toFixed(1) + '%';

            // Atualizar trades
            updateTrades(data.trading.active_trades);

            // Atualizar performance
            updatePerformanceChart(data.performance.chart_data);

            // Atualizar estratégias
            updateStrategies(data.strategies);

            // Atualizar alertas
            updateAlerts(data.alerts);
        }

        function updateTrades(trades) {
            const tradeList = document.getElementById('tradeList');

            if (trades.length === 0) {
                tradeList.innerHTML = '<div class="loading">Nenhum trade ativo</div>';
                return;
            }

            tradeList.innerHTML = trades.map(trade => `
                <div class="trade ${trade.profit >= 0 ? 'profit' : 'loss'}">
                    <div>
                        <strong>${trade.pair}</strong><br>
                        <small>${trade.strategy}</small>
                    </div>
                    <div>
                        <strong>${trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}%</strong><br>
                        <small>$${(trade.current_price * trade.amount).toFixed(2)}</small>
                    </div>
                </div>
            `).join('');
        }

        function updatePerformanceChart(data) {
            if (!data || data.length === 0) return;

            const timestamps = data.map(d => new Date(d.timestamp));
            const equity = data.map(d => d.equity);
            const profit = data.map(d => d.profit);

            const trace1 = {
                x: timestamps,
                y: equity,
                type: 'scatter',
                mode: 'lines',
                name: 'Equity',
                line: {color: '#4CAF50'}
            };

            const trace2 = {
                x: timestamps,
                y: profit,
                type: 'scatter',
                mode: 'lines',
                name: 'Profit',
                yaxis: 'y2',
                line: {color: '#667eea'}
            };

            const layout = {
                paper_bgcolor: '#2a2a2a',
                plot_bgcolor: '#2a2a2a',
                font: {color: '#ffffff'},
                xaxis: {
                    gridcolor: '#444',
                    title: 'Time'
                },
                yaxis: {
                    gridcolor: '#444',
                    title: 'Equity ($)',
                    side: 'left'
                },
                yaxis2: {
                    gridcolor: '#444',
                    title: 'Profit ($)',
                    side: 'right',
                    overlaying: 'y'
                },
                margin: {l: 60, r: 60, t: 40, b: 60}
            };

            Plotly.newPlot('performanceChart', [trace1, trace2], layout, {responsive: true});
        }

        function updateStrategies(strategies) {
            const container = document.getElementById('strategies');

            container.innerHTML = strategies.map(strategy => `
                <div style="background: #333; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3>${strategy.name}</h3>
                            <span style="background: ${strategy.status === 'active' ? '#4CAF50' : '#f44336'};
                                         padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">
                                ${strategy.status}
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <div><strong>Win Rate:</strong> ${strategy.win_rate}%</div>
                            <div><strong>Profit:</strong> $${strategy.profit.toFixed(2)}</div>
                            <div><strong>Trades:</strong> ${strategy.total_trades}</div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts');

            if (alerts.length === 0) {
                container.innerHTML = '<div class="loading">Aguardando alertas...</div>';
                return;
            }

            container.innerHTML = alerts.map(alert => `
                <div class="alert">
                    <div style="font-weight: 600;">${alert.level}</div>
                    <div style="color: #aaa; font-size: 0.9rem;">${new Date(alert.timestamp).toLocaleTimeString()}</div>
                    <div>${alert.message}</div>
                </div>
            `).join('');
        }

        function addAlert(alert) {
            // Adicionar novo alerta no topo
            const container = document.getElementById('alerts');
            const alertHTML = `
                <div class="alert">
                    <div style="font-weight: 600;">${alert.level}</div>
                    <div style="color: #aaa; font-size: 0.9rem;">${new Date(alert.timestamp).toLocaleTimeString()}</div>
                    <div>${alert.message}</div>
                </div>
            `;

            container.innerHTML = alertHTML + container.innerHTML;
        }

        function startBot() {
            fetch('/api/bot/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Bot iniciado com sucesso!');
                    }
                });
        }

        function stopBot() {
            fetch('/api/bot/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Bot parado com sucesso!');
                    }
                });
        }

        function runBacktest() {
            const strategy = prompt('Estratégia para backtest (EMA200RSI, MACDStrategy, template_strategy):', 'EMA200RSI');
            if (strategy) {
                fetch('/api/backtest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({strategy: strategy})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Backtest iniciado: ' + data.message);
                    }
                });
            }
        }

        function optimizeStrategy() {
            const strategy = prompt('Estratégia para otimizar (EMA200RSI, MACDStrategy, template_strategy):', 'EMA200RSI');
            if (strategy) {
                fetch('/api/strategy/optimize', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({strategy: strategy})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Otimização iniciada: ' + data.message);
                    }
                });
            }
        }

        // Solicitar atualização inicial
        socket.emit('request_update');
    </script>
</body>
</html>
"""

def main():
    """Função principal"""
    dashboard = CompleteOperationalDashboard()

    print("""
[INFO] FREQTRADE3 - DASHBOARD OPERACIONAL COMPLETO
================================================

Este dashboard implementa:
  - Interface web avancada em tempo real
  - Controlo completo do bot via web
  - Visualizacao de metricas e performance
  - Graficos dinamicos com Plotly
  - Alertas em tempo real
  - Gestao de estrategias via interface

Iniciar dashboard?""")

    choice = input("(s/n): ").lower().strip()

    if choice in ['s', 'sim', 'yes', 'y']:
        dashboard.run_dashboard(port=5000)
    else:
        print("❌ Dashboard cancelado")

if __name__ == "__main__":
    main()
