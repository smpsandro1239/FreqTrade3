#!/usr/bin/env python3
"""
FreqTrade3 - API de Controlo de Trading
=======================================

API REST simples para controlo total do sistema FreqTrade3.
Permite executar comandos, monitorar trades e gerir estratégias.

Funcionalidades:
- Execução de comandos FreqTrade
- Monitoramento de status
- Controlo de estratégias
- Dashboard em tempo real

Autor: FreqTrade3 Project
Data: 2025-11-06
Versão: 1.0.0
"""

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

class TradingAPI:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        self.active_bot = None
        self.status = {
            "bot_running": False,
            "current_strategy": "EMA200RSI",
            "last_command": "Nenhum",
            "trades": [],
            "balance": 10000.0,
            "config": "config_ui.json"
        }

    def setup_routes(self):
        """Configurar rotas da API"""

        @self.app.route('/')
        def dashboard():
            return render_template_string(DASHBOARD_TEMPLATE)

        @self.app.route('/api/status')
        def get_status():
            return jsonify(self.status)

        @self.app.route('/api/start', methods=['POST'])
        def start_bot():
            data = request.get_json() or {}
            strategy = data.get('strategy', 'EMA200RSI')
            pair = data.get('pair', 'ETH/USDT')

            cmd = f"freqtrade trade --config {self.status['config']} --strategy {strategy} --pairs {pair}"

            try:
                if not self.active_bot or self.active_bot.poll() is not None:
                    self.active_bot = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.status["bot_running"] = True
                    self.status["current_strategy"] = strategy
                    self.status["last_command"] = f"Iniciado: {strategy} em {pair}"

                    # Log do trade simulado
                    trade = {
                        "pair": pair,
                        "strategy": strategy,
                        "side": "BUY",
                        "amount": 100,
                        "price": self.get_market_price(pair),
                        "timestamp": datetime.now().isoformat(),
                        "status": "ATIVO"
                    }
                    self.status["trades"].append(trade)

                    return jsonify({"success": True, "message": f"Bot iniciado com {strategy}"})
                else:
                    return jsonify({"success": False, "message": "Bot já está rodando"})

            except Exception as e:
                return jsonify({"success": False, "message": f"Erro: {str(e)}"})

        @self.app.route('/api/stop', methods=['POST'])
        def stop_bot():
            try:
                if self.active_bot:
                    self.active_bot.terminate()
                    self.status["bot_running"] = False
                    self.status["last_command"] = "Bot parado"
                    return jsonify({"success": True, "message": "Bot parado"})
                else:
                    return jsonify({"success": False, "message": "Bot não está rodando"})
            except Exception as e:
                return jsonify({"success": False, "message": f"Erro: {str(e)}"})

        @self.app.route('/api/command', methods=['POST'])
        def execute_command():
            data = request.get_json() or {}
            command = data.get('command', '')

            if not command:
                return jsonify({"success": False, "message": "Comando vazio"})

            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

                self.status["last_command"] = command

                return jsonify({
                    "success": True,
                    "output": result.stdout,
                    "error": result.stderr,
                    "return_code": result.returncode
                })

            except subprocess.TimeoutExpired:
                return jsonify({"success": False, "message": "Comando excedeu timeout"})
            except Exception as e:
                return jsonify({"success": False, "message": f"Erro: {str(e)}"})

        @self.app.route('/api/strategies')
        def get_strategies():
            try:
                result = subprocess.run("freqtrade list-strategies", shell=True, capture_output=True, text=True)
                return jsonify({
                    "success": True,
                    "strategies": result.stdout.split('\n')
                })
            except Exception as e:
                return jsonify({"success": False, "message": f"Erro: {str(e)}"})

        @self.app.route('/api/backtest', methods=['POST'])
        def run_backtest():
            data = request.get_json() or {}
            strategy = data.get('strategy', 'EMA200RSI')
            pair = data.get('pair', 'ETH/USDT')

            cmd = f"freqtrade backtesting --strategy {strategy} --pairs {pair}"

            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

                self.status["last_command"] = f"Backtest: {strategy} em {pair}"

                return jsonify({
                    "success": True,
                    "result": result.stdout,
                    "error": result.stderr
                })

            except Exception as e:
                return jsonify({"success": False, "message": f"Erro: {str(e)}"})

        @self.app.route('/api/trades')
        def get_trades():
            return jsonify(self.status["trades"])

        @self.app.route('/api/balance')
        def get_balance():
            # Simular atualização de balance
            if self.status["bot_running"] and self.status["trades"]:
                # Calcular profit baseado no trade ativo
                active_trade = self.status["trades"][-1]
                market_price = self.get_market_price(active_trade["pair"])
                if market_price > 0:
                    # Simular profit de 1.5%
                    self.status["balance"] = 10150.0

            return jsonify({"balance": self.status["balance"]})

    def get_market_price(self, pair):
        """Obter preço simulado do mercado"""
        prices = {
            "BTC/USDT": 45000.0,
            "ETH/USDT": 3500.0,
            "BNB/USDT": 320.0
        }
        return prices.get(pair, 1000.0)

    def monitor_bot_status(self):
        """Monitorar status do bot em background"""
        while True:
            if self.active_bot:
                if self.active_bot.poll() is not None:
                    self.status["bot_running"] = False

            time.sleep(5)

    def start(self, host='0.0.0.0', port=8080):
        """Iniciar servidor da API"""
        # Iniciar thread de monitoramento
        monitor_thread = threading.Thread(target=self.monitor_bot_status, daemon=True)
        monitor_thread.start()

        print(f"[OK] API de Controle iniciada em http://localhost:{port}")
        print(f"[INFO] Dashboard: http://localhost:{port}")
        print(f"[OK] Sistema pronto para trading")

        self.app.run(host=host, port=port, debug=False, threaded=True)

# =============================================================================
# TEMPLATE DO DASHBOARD
# =============================================================================

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 FreqTrade3 - Controlo de Trading</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .card h3 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }

        .btn {
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            margin: 5px;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 212, 255, 0.4);
        }

        .btn.stop {
            background: linear-gradient(45deg, #ff6b35, #d63031);
        }

        .btn.backtest {
            background: linear-gradient(45deg, #00ff88, #00cc6a);
        }

        .form-group {
            margin: 15px 0;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #00d4ff;
            font-weight: bold;
        }

        .form-group select,
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }

        .status {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: bold;
        }

        .status.running {
            background: rgba(0, 255, 136, 0.2);
            border: 1px solid #00ff88;
        }

        .status.stopped {
            background: rgba(255, 107, 53, 0.2);
            border: 1px solid #ff6b35;
        }

        .command-output {
            background: rgba(0, 0, 0, 0.5);
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            margin-top: 15px;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }

        .balance {
            font-size: 2rem;
            color: #00ff88;
            text-align: center;
            margin: 20px 0;
        }

        .trades {
            max-height: 200px;
            overflow-y: auto;
        }

        .trade-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #00d4ff;
        }

        .update-btn {
            background: linear-gradient(45deg, #ffd700, #ff9500);
            color: #000;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        .updating {
            animation: pulse 1s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 FreqTrade3 - Controlo de Trading</h1>
            <p>Sistema de Trading Automatizado - Interface de Controlo Real</p>
        </div>

        <div class="grid">
            <!-- Status do Bot -->
            <div class="card">
                <h3>📊 Status do Bot</h3>
                <div id="bot-status" class="status stopped">🔴 Parado</div>
                <div>Estratégia Atual: <span id="current-strategy">EMA200RSI</span></div>
                <div>Último Comando: <span id="last-command">Nenhum</span></div>
                <div class="balance">💰 <span id="balance">10,000.00</span> USDT</div>
                <button class="btn update-btn" onclick="updateStatus()">🔄 Atualizar</button>
            </div>

            <!-- Controlo de Bot -->
            <div class="card">
                <h3>⚡ Controlo do Bot</h3>
                <div class="form-group">
                    <label for="strategy-select">Estratégia:</label>
                    <select id="strategy-select">
                        <option value="EMA200RSI">EMA200RSI</option>
                        <option value="MACDStrategy">MACDStrategy</option>
                        <option value="template_strategy">Template Strategy</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="pair-select">Par de Trading:</label>
                    <select id="pair-select">
                        <option value="ETH/USDT">ETH/USDT</option>
                        <option value="BTC/USDT">BTC/USDT</option>
                        <option value="BNB/USDT">BNB/USDT</option>
                    </select>
                </div>
                <button class="btn" onclick="startBot()">🚀 Iniciar Bot</button>
                <button class="btn stop" onclick="stopBot()">🛑 Parar Bot</button>
            </div>

            <!-- Backtesting -->
            <div class="card">
                <h3>🧪 Backtesting</h3>
                <p>Executar testes de estratégia em dados históricos</p>
                <button class="btn backtest" onclick="runBacktest()">📊 Executar Backtest</button>
                <div id="backtest-output" class="command-output" style="display: none;"></div>
            </div>

            <!-- Comandos Customizados -->
            <div class="card">
                <h3>💻 Comandos Customizados</h3>
                <div class="form-group">
                    <label for="command-input">Comando FreqTrade:</label>
                    <input type="text" id="command-input" placeholder="freqtrade backtesting --strategy EMA200RSI --pairs ETH/USDT">
                </div>
                <button class="btn" onclick="executeCommand()">⚡ Executar</button>
                <div id="command-output" class="command-output" style="display: none;"></div>
            </div>
        </div>

        <!-- Trades Ativos -->
        <div class="card">
            <h3>📈 Trades Ativos</h3>
            <div id="trades-list" class="trades">
                <div class="trade-item">Nenhum trade ativo</div>
            </div>
        </div>
    </div>

    <script>
        // Atualizar status do sistema
        function updateStatus() {
            document.getElementById('bot-status').classList.add('updating');

            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const statusEl = document.getElementById('bot-status');
                    const currentStrategyEl = document.getElementById('current-strategy');
                    const lastCommandEl = document.getElementById('last-command');
                    const balanceEl = document.getElementById('balance');

                    if (data.bot_running) {
                        statusEl.className = 'status running';
                        statusEl.textContent = '🟢 Rodando';
                    } else {
                        statusEl.className = 'status stopped';
                        statusEl.textContent = '🔴 Parado';
                    }

                    currentStrategyEl.textContent = data.current_strategy;
                    lastCommandEl.textContent = data.last_command;
                    statusEl.classList.remove('updating');
                })
                .catch(error => {
                    console.error('Erro:', error);
                    statusEl.classList.remove('updating');
                });
        }

        // Atualizar balance
        function updateBalance() {
            fetch('/api/balance')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('balance').textContent = data.balance.toFixed(2);
                });
        }

        // Atualizar lista de trades
        function updateTrades() {
            fetch('/api/trades')
                .then(response => response.json())
                .then(data => {
                    const tradesList = document.getElementById('trades-list');
                    if (data.length === 0) {
                        tradesList.innerHTML = '<div class="trade-item">Nenhum trade ativo</div>';
                    } else {
                        tradesList.innerHTML = data.map(trade => `
                            <div class="trade-item">
                                <strong>${trade.pair}</strong> - ${trade.strategy}<br>
                                ${trade.side}: ${trade.amount} @ $${trade.price}<br>
                                <small>${new Date(trade.timestamp).toLocaleString('pt-BR')}</small>
                            </div>
                        `).join('');
                    }
                });
        }

        // Iniciar bot
        function startBot() {
            const strategy = document.getElementById('strategy-select').value;
            const pair = document.getElementById('pair-select').value;

            fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({strategy, pair})
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                updateStatus();
                updateTrades();
            });
        }

        // Parar bot
        function stopBot() {
            fetch('/api/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    updateStatus();
                });
        }

        // Executar backtest
        function runBacktest() {
            const strategy = document.getElementById('strategy-select').value;
            const pair = document.getElementById('pair-select').value;
            const output = document.getElementById('backtest-output');

            output.style.display = 'block';
            output.textContent = 'Executando backtest...';

            fetch('/api/backtest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({strategy, pair})
            })
            .then(response => response.json())
            .then(data => {
                output.textContent = data.result || data.error;
            });
        }

        // Executar comando customizado
        function executeCommand() {
            const command = document.getElementById('command-input').value;
            const output = document.getElementById('command-output');

            if (!command.trim()) {
                alert('Digite um comando');
                return;
            }

            output.style.display = 'block';
            output.textContent = 'Executando comando...';

            fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command})
            })
            .then(response => response.json())
            .then(data => {
                let outputText = '';
                if (data.success) {
                    outputText = data.output || 'Comando executado com sucesso';
                } else {
                    outputText = 'Erro: ' + (data.message || 'Comando falhou');
                }
                if (data.error) {
                    outputText += '\\n\\nStderr: ' + data.error;
                }
                output.textContent = outputText;
            });
        }

        // Atualizar informações a cada 5 segundos
        setInterval(() => {
            updateStatus();
            updateBalance();
            updateTrades();
        }, 5000);

        // Carregar informações iniciais
        updateStatus();
        updateBalance();
        updateTrades();
    </script>
</body>
</html>
"""

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    try:
        # Verificar se Flask está instalado
        import flask
        import flask_cors
    except ImportError:
        print("📦 Instalando dependências necessárias...")
        os.system("pip install flask flask-cors")

    # Criar diretório de logs se não existir
    os.makedirs("logs", exist_ok=True)

    # Inicializar e iniciar API
    api = TradingAPI()
    api.start(port=8080)
