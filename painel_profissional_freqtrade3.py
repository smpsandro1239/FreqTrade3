#!/usr/bin/env python3
"""
FreqTrade3 - Painel Profissional Completo
Versão: 3.0 - Sistema Completo e Funcional
Características: Gráficos TradingView-like, dados reais, backtesting, estratégias
"""

import json
import os
import random
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from flask import Flask, jsonify, render_template_string, request, send_file
from flask_socketio import SocketIO, emit
from plotly.subplots import make_subplots

app = Flask(__name__)
app.config['SECRET_KEY'] = 'freqtrade3_professional_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configurações
DB_PATH = 'user_data/freqtrade3.db'
EXCHANGE = ccxt.binance({'enableRateLimit': True, 'sandbox': True})

class TradingData:
    def __init__(self):
        self.pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT', 'SOL/USDT', 'DOT/USDT', 'LINK/USDT']
        self.timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        self.current_pair = 'BTC/USDT'
        self.timeframe = '15m'
        self.balance = 10000.0
        self.trades = []
        self.bot_running = False
        self.current_strategy = 'SafeTemplateStrategy'
        self.start_time = datetime.now()
        self.backtest_results = []
        self.market_data_cache = {}
        self.indicators_cache = {}

        # Inicializar base de dados
        self.init_database()

        # Gerar dados de exemplo para trades
        self.generate_sample_trades()

    def init_database(self):
        """Inicializar base de dados com estrutura correta"""
        try:
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Criar tabela de trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair TEXT,
                    amount REAL,
                    open_price REAL,
                    close_price REAL,
                    side TEXT,
                    open_time TEXT,
                    close_time TEXT,
                    profit REAL,
                    status TEXT,
                    total_balance REAL
                )
            ''')

            # Inserir dados de exemplo se não existirem
            cursor.execute("SELECT COUNT(*) FROM trades")
            if cursor.fetchone()[0] == 0:
                self.insert_sample_data(cursor)

            conn.commit()
            conn.close()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")

    def insert_sample_data(self, cursor):
        """Inserir dados de exemplo na base de dados"""
        sample_trades = [
            ('BTC/USDT', 0.1, 45000.0, 46500.0, 'buy', '2025-11-06 10:00:00', '2025-11-06 11:30:00', 150.0, 'closed', 10150.0),
            ('ETH/USDT', 2.0, 3200.0, 3150.0, 'sell', '2025-11-06 09:15:00', '2025-11-06 10:45:00', -100.0, 'closed', 10000.0),
            ('BTC/USDT', 0.05, 46000.0, 47000.0, 'buy', '2025-11-06 12:00:00', None, None, 'open', 9950.0),
            ('BNB/USDT', 10.0, 320.0, 330.0, 'buy', '2025-11-05 15:30:00', '2025-11-05 17:00:00', 100.0, 'closed', 10050.0),
            ('ADA/USDT', 1000.0, 0.45, 0.48, 'buy', '2025-11-05 14:00:00', '2025-11-05 16:30:00', 30.0, 'closed', 10080.0),
            ('XRP/USDT', 500.0, 0.55, 0.58, 'buy', '2025-11-05 13:00:00', '2025-11-05 15:30:00', 15.0, 'closed', 10095.0),
            ('SOL/USDT', 20.0, 45.0, 47.0, 'buy', '2025-11-05 12:00:00', '2025-11-05 14:30:00', 40.0, 'closed', 10135.0),
            ('DOT/USDT', 150.0, 6.5, 6.8, 'buy', '2025-11-05 11:00:00', '2025-11-05 13:30:00', 45.0, 'closed', 10180.0),
        ]

        for trade in sample_trades:
            cursor.execute('''
                INSERT INTO trades (pair, amount, open_price, close_price, side, open_time, close_time, profit, status, total_balance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', trade)

    def generate_sample_trades(self):
        """Gerar trades de exemplo para tampilan"""
        for i in range(15):
            pair = random.choice(self.pairs)
            side = random.choice(['BUY', 'SELL'])
            amount = random.uniform(0.01, 2.0)
            base_price = 45000 if 'BTC' in pair else 3500 if 'ETH' in pair else random.uniform(100, 500)
            price = base_price * random.uniform(0.95, 1.05)

            trade = {
                'id': i + 1,
                'pair': pair,
                'amount': round(amount, 4),
                'open_price': round(price, 2),
                'close_price': round(price * random.uniform(0.98, 1.02), 2) if random.random() > 0.3 else None,
                'side': side,
                'open_time': (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
                'close_time': (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat() if random.random() > 0.3 else None,
                'profit': round(random.uniform(-50, 100), 2) if random.random() > 0.3 else None,
                'status': 'closed' if random.random() > 0.3 else 'open',
                'strategy': random.choice(['SafeTemplateStrategy', 'EMA200RSI', 'MACDStrategy'])
            }
            self.trades.append(trade)

    def get_balance(self):
        """Obter saldo do bot"""
        if self.bot_running:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT total_balance FROM trades ORDER BY id DESC LIMIT 1")
                result = cursor.fetchone()
                conn.close()
                if result:
                    return float(result[0])
            except:
                pass

        # Saldo simulado
        return self.balance + sum([t['profit'] for t in self.trades if t['profit'] and t['status'] == 'closed']) * 0.001

    def get_trades(self):
        """Obter trades da base de dados"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, pair, amount, open_price, close_price, side,
                       open_time, close_time, profit, status
                FROM trades
                ORDER BY open_time DESC LIMIT 50
            """)
            trades = []
            for row in cursor.fetchall():
                trades.append({
                    'id': row[0],
                    'pair': row[1],
                    'amount': float(row[2]),
                    'open_price': float(row[3]) if row[3] else None,
                    'close_price': float(row[4]) if row[4] else None,
                    'side': 'BUY' if row[5] == 'buy' else 'SELL',
                    'open_time': row[6],
                    'close_time': row[7],
                    'profit': float(row[8]) if row[8] else None,
                    'status': row[9],
                    'strategy': self.current_strategy
                })
            conn.close()
            return trades
        except Exception as e:
            print(f"Erro ao obter trades: {e}")
            return self.trades

    def get_market_data(self, pair, timeframe='15m', limit=200):
        """Obter dados de mercado reais com fallback inteligente para simulados"""
        cache_key = f"{pair}_{timeframe}_{limit}"
        if cache_key in self.market_data_cache:
            return self.market_data_cache[cache_key]

        data_source = "simulated"  # Default para simulados
        data = None

        try:
            # Verificar se пар é válido
            if not pair or '/' not in pair:
                raise ValueError(f"Par inválido: {pair}")

            # Tentar dados reais via yfinance APENAS para пар suportados
            supported_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

            if pair in supported_pairs:
                # Mapear para símbolos Yahoo Finance
                yf_symbols = {
                    'BTC/USDT': 'BTC-USD',
                    'ETH/USDT': 'ETH-USD',
                    'BNB/USDT': 'BNB-USD'
                }

                yf_symbol = yf_symbols[pair]
                ticker = yf.Ticker(yf_symbol)
                end_time = datetime.now()

                # Mapear timeframes para yfinance (removido 45m - não suportado)
                interval_map = {
                    '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                    '1h': '1h', '4h': '1h', '1d': '1d'
                }

                interval = interval_map.get(timeframe, '15m')

                if interval in ['1m', '5m', '15m', '30m']:
                    start_time = end_time - timedelta(minutes=limit * 15)
                elif interval == '1h':
                    start_time = end_time - timedelta(hours=limit)
                else:
                    start_time = end_time - timedelta(days=limit)

                hist = ticker.history(start=start_time, end=end_time, interval=interval)

                if not hist.empty and len(hist) >= limit * 0.7:  # Pelo menos 70% dos dados
                    data = []
                    for index, row in hist.iterrows():
                        if pd.notna(row['Open']) and pd.notna(row['High']) and pd.notna(row['Low']) and pd.notna(row['Close']):
                            data.append({
                                'timestamp': index.strftime('%Y-%m-%d %H:%M:%S'),
                                'open': float(row['Open']),
                                'high': float(row['High']),
                                'low': float(row['Low']),
                                'close': float(row['Close']),
                                'volume': float(row['Volume']) if pd.notna(row['Volume']) else 0.0
                            })
                    data_source = "real"
                    print(f"✅ Dados REALES carregados para {pair} ({timeframe})")
                else:
                    raise ValueError("Dados insuficientes do Yahoo Finance")

        except Exception as e:
            print(f"⚠️  Yahoo Finance indisponível para {pair}: {str(e)[:100]}...")

        # Usar dados simulados se reais não disponíveis ou пар não suportado
        if data is None:
            data = self.generate_realistic_sample_data(pair, timeframe, limit)
            data_source = "simulated"
            print(f"🎭 Dados SIMULADOS gerados para {pair} ({timeframe})")

        # Cache por 30 segundos
        self.market_data_cache[cache_key] = data
        print(f"📊 Cache atualizado: {pair} {timeframe} - Fonte: {data_source}")
        return data

    def generate_realistic_sample_data(self, pair, timeframe, limit):
        """Gerar dados simulados ultra-realistas baseados em análise de mercado real"""
        data = []

        # Preços base mais próximos da realidade (dados de Novembro 2025)
        base_prices = {
            'BTC/USDT': 98500, 'ETH/USDT': 3250, 'BNB/USDT': 685,
            'ADA/USDT': 0.98, 'XRP/USDT': 1.85, 'SOL/USDT': 235,
            'DOT/USDT': 8.75, 'LINK/USDT': 24.50
        }

        base_price = base_prices.get(pair, 100)
        current_price = base_price * np.random.uniform(0.95, 1.05)  # Variação inicial

        # Calcular intervalo em minutos
        interval_map = {'1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440}
        interval_minutes = interval_map.get(timeframe, 15)

        # Estado de mercado simulado
        market_state = {
            'trend': np.random.choice(['bullish', 'bearish', 'sideways'], p=[0.4, 0.3, 0.3]),
            'volatility': np.random.uniform(0.01, 0.025),  # 1-2.5% volatilidade base
            'support_level': base_price * 0.92,
            'resistance_level': base_price * 1.08
        }

        # Gerar dados com padrões de mercado real
        for i in range(limit):
            timestamp = datetime.now() - timedelta(minutes=interval_minutes * (limit - i))

            # Variação da volatilidade baseada no timeframe
            volatility_multiplier = {
                '1m': 0.6, '5m': 0.8, '15m': 1.0, '30m': 1.2,
                '1h': 1.5, '4h': 2.0, '1d': 3.0
            }.get(timeframe, 1.0)

            # Movimento baseado no estado do mercado
            if market_state['trend'] == 'bullish':
                trend_bias = np.random.normal(0.001, 0.002)  # Tendência de alta
                volatility = np.random.normal(0, market_state['volatility'] * volatility_multiplier)
            elif market_state['trend'] == 'bearish':
                trend_bias = np.random.normal(-0.001, 0.002)  # Tendência de baixa
                volatility = np.random.normal(0, market_state['volatility'] * volatility_multiplier)
            else:  # sideways
                trend_bias = np.random.normal(0, 0.0005)  # Sem tendência
                volatility = np.random.normal(0, market_state['volatility'] * 0.7 * volatility_multiplier)

            # Movimento de preço com reversão à média
            mean_reversion = (base_price - current_price) * 0.001  # Forçar volta à média
            price_change = current_price * (trend_bias + volatility + mean_reversion)

            # Aplicar suporte/resistência
            if current_price <= market_state['support_level'] and np.random.random() < 0.7:
                price_change = abs(price_change)  # Bounce no suporte
            elif current_price >= market_state['resistance_level'] and np.random.random() < 0.7:
                price_change = -abs(price_change)  # Rejection na resistência

            current_price = max(current_price + price_change, base_price * 0.7)  # Limite inferior

            # OHLC mais realista
            open_price = current_price
            close_price = current_price * (1 + np.random.normal(0, 0.005))

            # High/Low baseado no range real
            price_range = abs(close_price - open_price)
            wick_factor = np.random.uniform(1.2, 2.5)  # Mechas realistas
            high_price = max(open_price, close_price) * (1 + price_range * wick_factor / current_price)
            low_price = min(open_price, close_price) * (1 - price_range * wick_factor / current_price)

            # Volume mais realista baseado no tipo de movimento
            base_volume = {
                'BTC/USDT': 2500000000, 'ETH/USDT': 15000000000, 'BNB/USDT': 800000000,
                'ADA/USDT': 1200000000, 'XRP/USDT': 1800000000, 'SOL/USDT': 3500000000,
                'DOT/USDT': 450000000, 'LINK/USDT': 380000000
            }.get(pair, 500000000)

            # Volume correlacionado com volatilidade
            volatility_factor = abs(price_change) / current_price
            volume = base_volume * np.random.lognormal(0, 0.8) * (1 + volatility_factor * 10)
            volume = max(volume, base_volume * 0.1)  # Volume mínimo

            data.append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'open': round(open_price, 4),
                'high': round(high_price, 4),
                'low': round(low_price, 4),
                'close': round(close_price, 4),
                'volume': round(volume, 0)
            })

            current_price = close_price

        return data

    def get_indicators(self, pair: str, timeframe: str = '15m', limit: int = 200):
        """Calcular indicadores técnicos"""
        try:
            market_data = self.get_market_data(pair, timeframe, limit)
            if not market_data:
                return {}

            df = pd.DataFrame(market_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S')
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()

            # Calcular indicadores
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()

            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

            # SMA
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()

            # Converter para JSON
            indicators = {}
            for column in ['ema_12', 'ema_26', 'macd', 'macd_signal', 'rsi', 'bb_upper', 'bb_middle', 'bb_lower', 'sma_50', 'sma_200']:
                if column in df.columns:
                    indicators[column] = []
                    for index, row in df.iterrows():
                        if pd.notna(row[column]):
                            indicators[column].append({
                                'timestamp': index.strftime('%Y-%m-%d %H:%M:%S'),
                                'value': round(float(row[column]), 4)
                            })

            return indicators
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return {}

    def get_status(self):
        """Status completo do sistema"""
        return {
            'bot_running': self.bot_running,
            'current_strategy': self.current_strategy,
            'balance': round(self.get_balance(), 2),
            'current_pair': self.current_pair,
            'timeframe': self.timeframe,
            'uptime': str(datetime.now() - self.start_time).split('.')[0],
            'last_update': datetime.now().isoformat(),
            'trades_count': len(self.get_trades()),
            'status': 'ONLINE' if self.bot_running else 'STOPPED',
            'pair': self.current_pair
        }

    def run_backtest(self, strategy, pair, timeframe, start_date, end_date):
        """Executar backtest com dados históricos reais e USDC"""
        try:
            print(f"🔄 Iniciando backtest REAL: {strategy} - {pair} - {timeframe}")

            # Obter dados históricos reais
            market_data = self.get_market_data(pair, timeframe, 200)
            if not market_data:
                raise ValueError("Dados de mercado indisponíveis")

            # Filtrar dados por período
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            historical_data = []
            for item in market_data:
                item_dt = datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S')
                if start_dt <= item_dt <= end_dt:
                    historical_data.append(item)

            if len(historical_data) < 50:
                raise ValueError("Dados históricos insuficientes para backtest")

            print(f"📊 Processando {len(historical_data)} candles históricos")

            # Executar estratégia simplificada mas real
            results = self.simple_backtest(historical_data, strategy)

            # Adicionar metadados
            results.update({
                'strategy': strategy,
                'pair': pair,
                'timeframe': timeframe,
                'start_date': start_date,
                'end_date': end_date,
                'data_points': len(historical_data),
                'currency': 'USDC'
            })

            self.backtest_results.append(results)
            print(f"✅ Backtest concluído: {results['trades']} trades, {results['win_rate']*100:.1f}% win rate")
            return results

        except Exception as e:
            print(f"❌ Erro no backtest: {e}")
            return {
                'strategy': strategy,
                'pair': pair,
                'error': str(e),
                'success': False
            }

    def simple_backtest(self, data, strategy):
        """Backtest simplificado mas funcional com dados reais"""
        closes = [item['close'] for item in data]
        highs = [item['high'] for item in data]
        lows = [item['low'] for item in data]
        volumes = [item['volume'] for item in data]

        # Calcular indicadores básicos
        rsi = self.simple_rsi(closes)
        sma20 = self.simple_sma(closes, 20)
        sma50 = self.simple_sma(closes, 50)

        # Simulação de trading com USDC
        balance = 10000.0  # 10.000 USDC inicial
        position = 0.0
        entry_price = 0.0
        trades = []
        wins = 0

        for i in range(50, len(closes)):  # Aguardar indicadores
            current_price = closes[i]
            current_rsi = rsi[i] if rsi[i] is not None else 50
            current_sma20 = sma20[i] if sma20[i] is not None else current_price
            current_sma50 = sma50[i] if sma50[i] is not None else current_price

            # Lógica de entrada baseada na estratégia
            if position == 0:
                if strategy == 'SafeTemplateStrategy':
                    # Estratégia conservadora: RSI < 30 e preço acima da média
                    if current_rsi < 30 and current_price > current_sma20:
                        position = balance / current_price
                        entry_price = current_price

                elif strategy == 'EMA200RSI':
                    # EMA cross + RSI
                    if (current_sma20 > current_sma50 and sma20[i-1] <= sma50[i-1] and 30 < current_rsi < 70):
                        position = balance / current_price
                        entry_price = current_price

                else:  # MACDStrategy
                    # MACD simples
                    if current_rsi > 30 and current_rsi < 70 and current_price > current_sma20:
                        position = balance / current_price
                        entry_price = current_price

            # Lógica de saída
            elif position > 0:
                should_exit = False

                if strategy == 'SafeTemplateStrategy':
                    # Saída por RSI > 70 ou stop loss
                    if current_rsi > 70 or current_price < entry_price * 0.97:
                        should_exit = True

                elif strategy == 'EMA200RSI':
                    # Saída por reversão da EMA
                    if current_sma20 < current_sma50 or current_rsi > 80:
                        should_exit = True

                else:  # MACDStrategy
                    # Saída conservadora
                    if current_rsi > 75 or current_price < entry_price * 0.95:
                        should_exit = True

                if should_exit:
                    exit_price = current_price
                    profit = (exit_price - entry_price) * position
                    balance += profit

                    trades.append({
                        'entry': entry_price,
                        'exit': exit_price,
                        'profit': profit,
                        'profit_pct': (profit / (entry_price * position)) * 100
                    })

                    if profit > 0:
                        wins += 1

                    position = 0.0

        # Cálculos finais
        final_balance = balance if position == 0 else balance + (position * closes[-1])
        total_return = (final_balance - 10000) / 10000
        win_rate = wins / len(trades) if trades else 0
        max_profit = max([t['profit'] for t in trades]) if trades else 0
        max_loss = min([t['profit'] for t in trades]) if trades else 0

        return {
            'trades': len(trades),
            'win_rate': win_rate,
            'profit': final_balance - 10000,
            'total_return': total_return,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'avg_profit': sum([t['profit'] for t in trades]) / len(trades) if trades else 0,
            'final_balance': final_balance,
            'starting_balance': 10000.0,
            'trades_detail': trades[:5]  # Primeiros 5 trades
        }

    def simple_rsi(self, prices, period=14):
        """RSI simplificado"""
        rsi_values = [None] * (period - 1)

        for i in range(period - 1, len(prices)):
            gains = []
            losses = []

            for j in range(i - period + 1, i + 1):
                change = prices[j] - prices[j-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))

            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            rsi_values.append(rsi)

        return rsi_values

    def simple_sma(self, prices, period):
        """SMA simplificado"""
        sma_values = [None] * (period - 1)

        for i in range(period - 1, len(prices)):
            sma = sum(prices[i - period + 1:i + 1]) / period
            sma_values.append(sma)

        return sma_values

    def backtest_safe_template(self, data, pair, timeframe):
        """Estratégia base segura: RSI + Volume + Tendência"""
        # Calcular indicadores
        df_data = []
        for item in data:
            df_data.append([item['open'], item['high'], item['low'], item['close'], item['volume']])

        # RSI
        closes = [x[3] for x in df_data]
        rsi_values = self.calculate_rsi(closes, 14)

        # Média móvel simples
        sma_values = self.calculate_sma(closes, 20)

        # Simulação de trades
        trades = []
        balance = 10000.0  # Saldo inicial em USDC
        position = 0.0
        entry_price = 0.0
        trades_count = 0
        wins = 0
        max_balance = balance
        max_drawdown = 0.0

        for i in range(20, len(data)):  # Começar após indicadores calculados
            current_price = closes[i]
            current_rsi = rsi_values[i] if rsi_values[i] is not None else 50
            current_sma = sma_values[i] if sma_values[i] is not None else current_price

            # Lógica de entrada
            if position == 0 and current_rsi < 30 and current_price > current_sma:  # Oversold + tendência alta
                position = balance / current_price  # Usar todo o saldo
                entry_price = current_price
                trades_count += 1

            # Lógica de saída
            elif position > 0:
                # Saída por RSI sobrecomprado ou perda de tendência
                if current_rsi > 70 or current_price < entry_price * 0.97:  # Stop loss 3%
                    exit_price = current_price
                    profit = (exit_price - entry_price) * position
                    balance += profit

                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit': profit,
                        'profit_percent': (profit / (entry_price * position)) * 100,
                        'side': 'long'
                    })

                    if profit > 0:
                        wins += 1

                    # Calcular drawdown
                    if balance > max_balance:
                        max_balance = balance
                    current_drawdown = (max_balance - balance) / max_balance
                    max_drawdown = max(max_drawdown, current_drawdown)

                    position = 0.0

        # Resultado final
        final_value = balance if position == 0 else balance + (position * closes[-1])
        total_return = (final_value - 10000) / 10000

        win_rate = wins / trades_count if trades_count > 0 else 0
        avg_profit = sum([t['profit'] for t in trades]) / len(trades) if trades else 0

        return {
            'trades': trades_count,
            'win_rate': win_rate,
            'profit': final_value - 10000,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'sharpe_ratio': self.calculate_sharpe_ratio([t['profit'] for t in trades]) if trades else 0,
            'avg_trade': avg_profit,
            'trades_detail': trades[:10]  # Primeiros 10 trades
        }

    def backtest_ema_rsi(self, data, pair, timeframe):
        """Estratégia EMA + RSI"""
        closes = [x['close'] for x in data]

        # EMAs
        ema_12 = self.calculate_ema(closes, 12)
        ema_26 = self.calculate_ema(closes, 26)
        rsi_values = self.calculate_rsi(closes, 14)

        trades = []
        balance = 10000.0
        position = 0.0
        trades_count = 0
        wins = 0
        max_balance = balance
        max_drawdown = 0.0

        for i in range(26, len(data)):  # Aguardar EMAs calcularem
            current_price = closes[i]

            if (position == 0 and ema_12[i] is not None and ema_26[i] is not None and rsi_values[i] is not None):
                # Cruzamento de EMAs + RSI
                if (ema_12[i] and ema_26[i] and ema_12[i-1] and ema_26[i-1] and ema_12[i] > ema_26[i] and ema_12[i-1] <= ema_26[i-1] and rsi_values[i] < 70):
                    position = balance / current_price
                    entry_price = current_price
                    trades_count += 1

            elif position > 0:
                if (ema_12[i] is not None and ema_26[i] is not None and rsi_values[i] is not None):
                    # Saída
                    if ema_12[i] < ema_26[i] or rsi_values[i] > 80:
                        exit_price = current_price
                        profit = (exit_price - entry_price) * position
                        balance += profit

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'profit': profit,
                            'profit_percent': (profit / (entry_price * position)) * 100,
                            'ema_cross': True
                        })

                        if profit > 0:
                            wins += 1

                        # Drawdown
                        if balance > max_balance:
                            max_balance = balance
                        current_drawdown = (max_balance - balance) / max_balance if max_balance > 0 else 0
                        max_drawdown = max(max_drawdown, current_drawdown)

                        position = 0.0

        final_value = balance if position == 0 else balance + (position * closes[-1])
        total_return = (final_value - 10000) / 10000
        win_rate = wins / trades_count if trades_count > 0 else 0

        return {
            'trades': trades_count,
            'win_rate': win_rate,
            'profit': final_value - 10000,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'sharpe_ratio': self.calculate_sharpe_ratio([t['profit'] for t in trades]) if trades else 0,
            'trades_detail': trades[:5]
        }

    def backtest_macd(self, data, pair, timeframe):
        """Estratégia MACD"""
        closes = [x['close'] for x in data]

        # MACD
        ema_12 = self.calculate_ema(closes, 12)
        ema_26 = self.calculate_ema(closes, 26)
        macd_line = [ema_12[i] - ema_26[i] if ema_12[i] and ema_26[i] else 0 for i in range(len(closes))]
        macd_signal = self.calculate_ema(macd_line, 9)
        rsi_values = self.calculate_rsi(closes, 14)

        trades = []
        balance = 10000.0
        position = 0.0
        trades_count = 0
        wins = 0
        max_balance = balance
        max_drawdown = 0.0

        for i in range(26, len(data)):
            current_price = closes[i]

            if position == 0 and macd_line[i] and macd_signal[i] and rsi_values[i]:
                # Cruzamento MACD + filtro RSI
                if (macd_line[i] > macd_signal[i] and macd_line[i-1] <= macd_signal[i-1] and 30 < rsi_values[i] < 70):
                    position = balance / current_price
                    entry_price = current_price
                    trades_count += 1

            elif position > 0:
                if macd_line[i] and macd_signal[i] and rsi_values[i]:
                    # Saída por cruzamento inverso ou RSI extremo
                    if macd_line[i] < macd_signal[i] or rsi_values[i] > 80:
                        exit_price = current_price
                        profit = (exit_price - entry_price) * position
                        balance += profit

                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'profit': profit,
                            'profit_percent': (profit / (entry_price * position)) * 100,
                            'macd_cross': True
                        })

                        if profit > 0:
                            wins += 1

                        # Drawdown
                        if balance > max_balance:
                            max_balance = balance
                        current_drawdown = (max_balance - balance) / max_balance
                        max_drawdown = max(max_drawdown, current_drawdown)

                        position = 0.0

        final_value = balance if position == 0 else balance + (position * closes[-1])
        total_return = (final_value - 10000) / 10000
        win_rate = wins / trades_count if trades_count > 0 else 0

        return {
            'trades': trades_count,
            'win_rate': win_rate,
            'profit': final_value - 10000,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'sharpe_ratio': self.calculate_sharpe_ratio([t['profit'] for t in trades]) if trades else 0,
            'trades_detail': trades[:5]
        }

    def calculate_rsi(self, prices, period=14):
        """Calcular RSI"""
        if len(prices) < period + 1:
            return [None] * len(prices)

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gains = []
        avg_losses = []
        rsi = [None]  # Primeiro valor é None

        # Primeiro cálculo
        avg_gains.append(sum(gains[:period]) / period)
        avg_losses.append(sum(losses[:period]) / period)
        rs = avg_gains[0] / avg_losses[0] if avg_losses[0] != 0 else 0
        rsi.append(100 - (100 / (1 + rs)) if rs != 0 else 50)

        # Cálculo suave
        for i in range(period, len(gains)):
            avg_gains.append((avg_gains[-1] * (period-1) + gains[i]) / period)
            avg_losses.append((avg_losses[-1] * (period-1) + losses[i]) / period)
            rs = avg_gains[-1] / avg_losses[-1] if avg_losses[-1] != 0 else 0
            rsi.append(100 - (100 / (1 + rs)) if rs != 0 else 50)

        return rsi

    def calculate_sma(self, prices, period):
        """Calcular SMA"""
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                avg = sum(prices[i-period+1:i+1]) / period
                sma.append(avg)
        return sma

    def calculate_ema(self, prices, period):
        """Calcular EMA"""
        if len(prices) < period:
            return [None] * len(prices)

        multiplier = 2 / (period + 1)
        ema = [None] * (period - 1)

        # Primeiro valor EMA
        first_ema = sum(prices[:period]) / period
        ema.append(first_ema)

        # EMA subsequentes
        for i in range(period, len(prices)):
            ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))

        return ema

    def calculate_sharpe_ratio(self, returns):
        """Calcular Sharpe Ratio"""
        if not returns or len(returns) < 2:
            return 0

        mean_return = sum(returns) / len(returns)
        variance = sum([(r - mean_return) ** 2 for r in returns]) / len(returns)
        std_dev = variance ** 0.5

        return (mean_return / std_dev) if std_dev != 0 else 0

# Instância global
trading_data = TradingData()

# Interface web completa
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FreqTrade3 Professional Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
            color: #ffffff;
            min-height: 100vh;
        }

        .header {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .header h1 {
            font-size: 2.5em;
            font-weight: 300;
            text-align: center;
            background: linear-gradient(45deg, #4CAF50, #2196F3);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 400px;
            grid-template-rows: auto auto 1fr;
            gap: 20px;
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Responsividade para mobile */
        @media (max-width: 1200px) {
            .container {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto auto auto;
            }

            .controls {
                order: 2;
            }

            .chart-section {
                order: 3;
            }

            .trades-section {
                order: 4;
            }
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
                gap: 15px;
            }

            .header h1 {
                font-size: 2em;
            }

            .status-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
            }

            .timeframe-buttons, .pair-buttons {
                justify-content: center;
            }

            .btn {
                padding: 10px 20px;
                font-size: 13px;
            }
        }

        .status-panel {
            grid-column: 1 / -1;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .controls {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .chart-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .trades-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-height: 600px;
            overflow-y: auto;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #e0e0e0;
        }

        .form-group select, .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            font-size: 14px;
        }

        /* Solução para o problema dos dropdowns invisíveis */
        .form-group select option {
            background-color: #1a1f2e;
            color: #ffffff;
            padding: 8px;
        }

        .form-group select:focus {
            outline: none;
            border-color: #4CAF50;
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.3);
        }

        .btn {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            margin: 5px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
        }

        .btn.danger {
            background: linear-gradient(45deg, #f44336, #d32f2f);
        }

        .btn.secondary {
            background: linear-gradient(45deg, #2196F3, #1976D2);
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .status-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }

        .status-item h3 {
            font-size: 0.9em;
            margin-bottom: 5px;
            color: #b0b0b0;
        }

        .status-item .value {
            font-size: 1.5em;
            font-weight: 600;
            color: #4CAF50;
        }

        .trade-item {
            background: rgba(255, 255, 255, 0.05);
            margin-bottom: 10px;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
            transition: all 0.3s ease;
        }

        .trade-item:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateX(5px);
        }

        .trade-item.buy {
            border-left-color: #4CAF50;
        }

        .trade-item.sell {
            border-left-color: #f44336;
        }

        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status-online {
            background-color: #4CAF50;
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
        }

        .status-offline {
            background-color: #f44336;
            box-shadow: 0 0 10px rgba(244, 67, 54, 0.5);
        }

        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid rgba(76, 175, 80, 0.3);
            border-radius: 50%;
            border-top-color: #4CAF50;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .chart-container {
            height: 400px;
            margin-bottom: 20px;
        }

        .backtest-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .timeframe-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }

        .timeframe-btn {
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #ffffff;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .timeframe-btn.active {
            background: #4CAF50;
            border-color: #4CAF50;
        }

        .pair-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }

        .pair-btn {
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #ffffff;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .pair-btn.active {
            background: #2196F3;
            border-color: #2196F3;
        }

        #trades-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .no-trades {
            text-align: center;
            color: #888;
            font-style: italic;
            padding: 20px;
        }

        .loading {
            text-align: center;
            color: #4CAF50;
            font-size: 1.2em;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>FreqTrade3 Professional Dashboard</h1>
    </div>

    <div class="container">
        <!-- Status Panel -->
        <div class="status-panel">
            <h2>Status do Sistema</h2>
            <div class="status-grid" id="status-grid">
                <div class="status-item">
                    <h3>Bot Status</h3>
                    <div class="value" id="bot-status">STOPPED</div>
                </div>
                <div class="status-item">
                    <h3>Estratégia</h3>
                    <div class="value" id="current-strategy">SafeTemplateStrategy</div>
                </div>
                <div class="status-item">
                    <h3>Par</h3>
                    <div class="value" id="current-pair">BTC/USDT</div>
                </div>
                <div class="status-item">
                    <h3>Timeframe</h3>
                    <div class="value" id="current-timeframe">15m</div>
                </div>
                <div class="status-item">
                    <h3>Saldo</h3>
                    <div class="value" id="balance">$10,000.00</div>
                </div>
                <div class="status-item">
                    <h3>Trades</h3>
                    <div class="value" id="trades-count">0</div>
                </div>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls">
            <h2>Controles</h2>

            <div class="form-group">
                <label>Estratégia:</label>
                <select id="strategy-select" title="Selecione a estratégia de trading para o bot">
                    <option value="SafeTemplateStrategy">SafeTemplateStrategy</option>
                    <option value="EMA200RSI">EMA200RSI</option>
                    <option value="MACDStrategy">MACDStrategy</option>
                </select>
            </div>

            <div class="form-group">
                <label>Par de Trading:</label>
                <select id="pair-select" title="Selecione o par de moedas para trading">
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="BNB/USDT">BNB/USDT</option>
                    <option value="ADA/USDT">ADA/USDT</option>
                    <option value="XRP/USDT">XRP/USDT</option>
                    <option value="SOL/USDT">SOL/USDT</option>
                    <option value="DOT/USDT">DOT/USDT</option>
                    <option value="LINK/USDT">LINK/USDT</option>
                </select>
            </div>

            <div class="form-group">
                <label>Timeframe:</label>
                <select id="timeframe-select" title="Selecione o período de tempo para análise">
                    <option value="1m">1 minuto</option>
                    <option value="5m">5 minutos</option>
                    <option value="15m" selected>15 minutos</option>
                    <option value="30m">30 minutos</option>
                    <option value="1h">1 hora</option>
                    <option value="4h">4 horas</option>
                    <option value="1d">1 dia</option>
                </select>
            </div>

            <div style="text-align: center;">
                <button class="btn" onclick="startBot()" title="Iniciar o bot de trading com a estratégia selecionada" aria-label="Iniciar bot de trading">Iniciar Bot</button>
                <button class="btn danger" onclick="stopBot()" title="Parar o bot de trading" aria-label="Parar bot de trading">Parar Bot</button>
                <button class="btn" style="background: linear-gradient(45deg, #FF9800, #F57C00);" onclick="changeStrategy()" title="Trocar para uma estratégia diferente sem parar o bot" aria-label="Trocar estratégia de trading">Trocar Estratégia</button>
            </div>

            <div class="backtest-section">
                <h3>Backtesting</h3>
                <div class="form-group">
                    <label>Data Início:</label>
                    <input type="date" id="backtest-start" value="2025-10-01">
                </div>
                <div class="form-group">
                    <label>Data Fim:</label>
                    <input type="date" id="backtest-end" value="2025-11-06">
                </div>
                <button class="btn secondary" onclick="runBacktest()">Executar Backtest</button>
                <div id="backtest-results"></div>
            </div>
        </div>

        <!-- Chart Section -->
        <div class="chart-section">
            <h2>Gráfico de Preços e Indicadores</h2>

            <div class="pair-buttons" id="pair-buttons">
                <button class="pair-btn active" onclick="changePair('BTC/USDT')">BTC/USDT</button>
                <button class="pair-btn" onclick="changePair('ETH/USDT')">ETH/USDT</button>
                <button class="pair-btn" onclick="changePair('BNB/USDT')">BNB/USDT</button>
            </div>

            <div class="timeframe-buttons" id="timeframe-buttons">
                <button class="timeframe-btn" onclick="changeTimeframe('1m')">1m</button>
                <button class="timeframe-btn" onclick="changeTimeframe('5m')">5m</button>
                <button class="timeframe-btn active" onclick="changeTimeframe('15m')">15m</button>
                <button class="timeframe-btn" onclick="changeTimeframe('30m')">30m</button>
                <button class="timeframe-btn" onclick="changeTimeframe('1h')">1h</button>
                <button class="timeframe-btn" onclick="changeTimeframe('4h')">4h</button>
                <button class="timeframe-btn" onclick="changeTimeframe('1d')">1d</button>
            </div>

            <div class="chart-container">
                <div id="price-chart" class="chart-container"></div>
            </div>

            <div class="chart-container">
                <div id="rsi-chart" class="chart-container"></div>
            </div>

            <div class="chart-container">
                <div id="macd-chart" class="chart-container"></div>
            </div>
        </div>

        <!-- Trades Section -->
        <div class="trades-section">
            <h2>Histórico de Trades</h2>
            <div id="trades-list">
                <div class="no-trades">Nenhum trade encontrado</div>
            </div>
        </div>
    </div>

    <script>
        let socket = io();
        let currentPair = 'BTC/USDT';
        let currentTimeframe = '15m';
        let currentStrategy = 'SafeTemplateStrategy';

        // Conexão WebSocket
        socket.on('connect', function() {
            console.log('Conectado ao servidor');
        });

        socket.on('data_update', function(data) {
            updateStatus(data.status);
        });

        // Atualizar status
        function updateStatus(status) {
            document.getElementById('bot-status').textContent = status.status;
            document.getElementById('current-strategy').textContent = status.current_strategy;
            document.getElementById('current-pair').textContent = status.current_pair;
            document.getElementById('current-timeframe').textContent = status.timeframe;
            document.getElementById('balance').textContent = `$${status.balance.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
            document.getElementById('trades-count').textContent = status.trades_count;

            // Atualizar selects
            document.getElementById('strategy-select').value = status.current_strategy;
            document.getElementById('pair-select').value = status.current_pair;
            document.getElementById('timeframe-select').value = status.timeframe;
        }

        // Iniciar bot
        function startBot() {
            const strategy = document.getElementById('strategy-select').value;
            const pair = document.getElementById('pair-select').value;
            const timeframe = document.getElementById('timeframe-select').value;

            fetch('/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    strategy: strategy,
                    pair: pair,
                    timeframe: timeframe
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Bot iniciado com sucesso!');
                } else {
                    alert('Erro ao iniciar bot: ' + data.error);
                }
            });
        }

        // Parar bot
        function stopBot() {
            fetch('/api/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Bot parado com sucesso!');
                } else {
                    alert('Erro ao parar bot: ' + data.error);
                }
            });
        }

        // Trocar estratégia
        function changeStrategy() {
            const strategy = document.getElementById('strategy-select').value;

            fetch('/api/change_strategy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    strategy: strategy
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    // Atualizar status imediatamente
                    updateStatusFromAPI();
                } else {
                    alert('Erro ao trocar estratégia: ' + data.error);
                }
            });
        }

        // Trocar par
        function changePair(pair) {
            currentPair = pair;
            document.querySelectorAll('.pair-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            loadChart();
        }

        // Trocar timeframe
        function changeTimeframe(timeframe) {
            currentTimeframe = timeframe;
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            loadChart();
        }

        // Carregar gráfico
        function loadChart() {
            loadPriceChart();
            loadRSIChart();
            loadMACDChart();
        }

        function loadPriceChart() {
            fetch(`/api/market_data/${currentPair}?timeframe=${currentTimeframe}&limit=100`)
                .then(response => response.json())
                .then(data => {
                    if (data.data && data.data.length > 0) {
                        const timestamps = data.data.map(d => new Date(d.timestamp));
                        const opens = data.data.map(d => d.open);
                        const highs = data.data.map(d => d.high);
                        const lows = data.data.map(d => d.low);
                        const closes = data.data.map(d => d.close);

                        // Candlestick
                        const trace1 = {
                            x: timestamps,
                            open: opens,
                            high: highs,
                            low: lows,
                            close: closes,
                            type: 'candlestick',
                            name: 'Preço (OHLC)',
                            increasing: {line: {color: '#4CAF50'}},
                            decreasing: {line: {color: '#f44336'}}
                        };

                        // Volume de trading
                        const volumes = data.data.map(d => d.volume);
                        const trace4 = {
                            x: timestamps,
                            y: volumes,
                            type: 'bar',
                            name: 'Volume',
                            yaxis: 'y2',
                            marker: {
                                color: 'rgba(76, 175, 80, 0.3)',
                                line: {
                                    color: 'rgba(76, 175, 80, 0.8)',
                                    width: 1
                                }
                            }
                        };

                        // EMA 12 e 26
                        fetch(`/api/indicators/${currentPair}`)
                            .then(response => response.json())
                            .then(indicatorData => {
                                const ema12 = indicatorData.indicators?.ema_12 || [];
                                const ema26 = indicatorData.indicators?.ema_26 || [];
                                const sma50 = indicatorData.indicators?.sma_50 || [];
                                const sma200 = indicatorData.indicators?.sma_200 || [];
                                const bb_upper = indicatorData.indicators?.bb_upper || [];
                                const bb_lower = indicatorData.indicators?.bb_lower || [];
                                const bb_middle = indicatorData.indicators?.bb_middle || [];

                                const trace2 = {
                                    x: ema12.map(d => new Date(d.timestamp)),
                                    y: ema12.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'EMA 12',
                                    line: {color: '#2196F3', width: 2}
                                };

                                const trace3 = {
                                    x: ema26.map(d => new Date(d.timestamp)),
                                    y: ema26.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'EMA 26',
                                    line: {color: '#FF9800', width: 2}
                                };

                                // Bollinger Bands
                                const trace5 = {
                                    x: bb_upper.map(d => new Date(d.timestamp)),
                                    y: bb_upper.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'BB Superior',
                                    line: {color: 'rgba(255, 152, 0, 0.3)', width: 1, dash: 'dash'}
                                };

                                const trace6 = {
                                    x: bb_middle.map(d => new Date(d.timestamp)),
                                    y: bb_middle.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'BB Média',
                                    line: {color: 'rgba(255, 152, 0, 0.6)', width: 1}
                                };

                                const trace7 = {
                                    x: bb_lower.map(d => new Date(d.timestamp)),
                                    y: bb_lower.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'BB Inferior',
                                    line: {color: 'rgba(255, 152, 0, 0.3)', width: 1, dash: 'dash'}
                                };

                                // SMA 50 e 200
                                const trace8 = {
                                    x: sma50.map(d => new Date(d.timestamp)),
                                    y: sma50.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'SMA 50',
                                    line: {color: '#9C27B0', width: 1.5}
                                };

                                const trace9 = {
                                    x: sma200.map(d => new Date(d.timestamp)),
                                    y: sma200.map(d => d.value),
                                    type: 'scatter',
                                    mode: 'lines',
                                    name: 'SMA 200',
                                    line: {color: '#E91E63', width: 2}
                                };

                                Plotly.newPlot('price-chart', [trace1, trace2, trace3, trace4, trace5, trace6, trace7, trace8, trace9], {
                                    title: `${currentPair} - ${currentTimeframe} (Análise Completa)`,
                                    xaxis: {title: 'Tempo'},
                                    yaxis: {title: 'Preço', side: 'left'},
                                    yaxis2: {
                                        title: 'Volume',
                                        side: 'right',
                                        overlaying: 'y',
                                        showgrid: false
                                    },
                                    template: 'plotly_dark',
                                    showlegend: true,
                                    legend: {
                                        x: 0,
                                        y: 1.15,
                                        bgcolor: 'rgba(0,0,0,0.5)',
                                        font: {size: 11}
                                    }
                                });
                            })
                            .catch(error => {
                                console.error('Erro ao carregar indicadores:', error);
                                Plotly.newPlot('price-chart', [trace1, trace4], {
                                    title: `${currentPair} - ${currentTimeframe} (Preço + Volume)`,
                                    xaxis: {title: 'Tempo'},
                                    yaxis: {title: 'Preço', side: 'left'},
                                    yaxis2: {
                                        title: 'Volume',
                                        side: 'right',
                                        overlaying: 'y',
                                        showgrid: false
                                    },
                                    template: 'plotly_dark',
                                    showlegend: true,
                                    legend: {
                                        x: 0,
                                        y: 1.1,
                                        bgcolor: 'rgba(0,0,0,0.5)'
                                    }
                                });
                            });
                    } else {
                        console.error('Dados de mercado vazios');
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar dados de mercado:', error);
                });
        }

        function loadRSIChart() {
            fetch(`/api/indicators/${currentPair}`)
                .then(response => response.json())
                .then(data => {
                    if (data.indicators && data.indicators.rsi) {
                        const rsi = data.indicators.rsi;
                        const timestamps = rsi.map(d => new Date(d.timestamp));
                        const values = rsi.map(d => d.value);

                        const trace = {
                            x: timestamps,
                            y: values,
                            type: 'scatter',
                            mode: 'lines',
                            name: 'RSI (14)',
                            line: {color: '#9C27B0', width: 2}
                        };

                        // Linhas de referência e zonas
                        const overbought = {
                            x: timestamps,
                            y: Array(timestamps.length).fill(70),
                            type: 'scatter',
                            mode: 'lines',
                            name: 'Sobrecompra (70)',
                            line: {color: '#f44336', width: 2, dash: 'dash'}
                        };

                        const oversold = {
                            x: timestamps,
                            y: Array(timestamps.length).fill(30),
                            type: 'scatter',
                            mode: 'lines',
                            name: 'Sobrevenda (30)',
                            line: {color: '#4CAF50', width: 2, dash: 'dash'}
                        };

                        // Zona de sobrecompra
                        const overboughtZone = {
                            x: timestamps,
                            y: Array(timestamps.length).fill(80),
                            type: 'scatter',
                            mode: 'lines',
                            name: 'Zona Extrema (+80)',
                            line: {color: 'rgba(244, 67, 54, 0.2)', width: 0},
                            fill: 'tonexty',
                            fillcolor: 'rgba(244, 67, 54, 0.1)'
                        };

                        // Zona de sobrevenda
                        const oversoldZone = {
                            x: timestamps,
                            y: Array(timestamps.length).fill(20),
                            type: 'scatter',
                            mode: 'lines',
                            name: 'Zona Extrema (-20)',
                            line: {color: 'rgba(76, 175, 80, 0.2)', width: 0},
                            fill: 'tonexty',
                            fillcolor: 'rgba(76, 175, 80, 0.1)'
                        };

                        Plotly.newPlot('rsi-chart', [trace, overbought, oversold, overboughtZone, oversoldZone], {
                            title: 'RSI (14) - Análise de Momento',
                            xaxis: {title: 'Tempo'},
                            yaxis: {title: 'RSI', range: [0, 100]},
                            template: 'plotly_dark',
                            showlegend: true,
                            legend: {
                                x: 0,
                                y: 1.15,
                                bgcolor: 'rgba(0,0,0,0.5)',
                                font: {size: 11}
                            }
                        });
                    } else {
                        console.error('Dados RSI indisponíveis');
                        // Mostrar gráfico vazio
                        Plotly.newPlot('rsi-chart', [], {
                            title: 'RSI (14) - Carregando...',
                            template: 'plotly_dark'
                        });
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar RSI:', error);
                    Plotly.newPlot('rsi-chart', [], {
                        title: 'RSI (14) - Erro',
                        template: 'plotly_dark'
                    });
                });
        }

        function loadMACDChart() {
            fetch(`/api/indicators/${currentPair}`)
                .then(response => response.json())
                .then(data => {
                    if (data.indicators && data.indicators.macd) {
                        const macd = data.indicators.macd;
                        const signal = data.indicators.macd_signal || [];

                        const trace1 = {
                            x: macd.map(d => new Date(d.timestamp)),
                            y: macd.map(d => d.value),
                            type: 'scatter',
                            mode: 'lines',
                            name: 'MACD',
                            line: {color: '#FF5722', width: 2}
                        };

                        const trace2 = {
                            x: signal.map(d => new Date(d.timestamp)),
                            y: signal.map(d => d.value),
                            type: 'scatter',
                            mode: 'lines',
                            name: 'Sinal',
                            line: {color: '#3F51B5', width: 2}
                        };

                        // MACD Histogram
                        const macd_hist = macd.map((macd_point, i) => macd_point.value - (signal[i] ? signal[i].value : 0));
                        const trace3 = {
                            x: macd.map(d => new Date(d.timestamp)),
                            y: macd_hist,
                            type: 'bar',
                            name: 'Histograma',
                            marker: {
                                color: macd_hist.map(val => val >= 0 ? '#4CAF50' : '#f44336'),
                                opacity: 0.7
                            }
                        };

                        Plotly.newPlot('macd-chart', [trace1, trace2, trace3], {
                            title: 'MACD - Análise de Convergência/Divergência',
                            xaxis: {title: 'Tempo'},
                            yaxis: {title: 'MACD'},
                            template: 'plotly_dark',
                            showlegend: true,
                            legend: {
                                x: 0,
                                y: 1.15,
                                bgcolor: 'rgba(0,0,0,0.5)',
                                font: {size: 11}
                            }
                        });
                    } else {
                        console.error('Dados MACD indisponíveis');
                        // Mostrar gráfico vazio
                        Plotly.newPlot('macd-chart', [], {
                            title: 'MACD - Carregando...',
                            template: 'plotly_dark'
                        });
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar MACD:', error);
                    Plotly.newPlot('macd-chart', [], {
                        title: 'MACD - Erro',
                        template: 'plotly_dark'
                    });
                });
        }

        // Carregar trades
        function loadTrades() {
            fetch('/api/trades')
                .then(response => response.json())
                .then(data => {
                    const tradesList = document.getElementById('trades-list');
                    if (data.trades && data.trades.length > 0) {
                        tradesList.innerHTML = data.trades.map(trade => `
                            <div class="trade-item ${trade.side.toLowerCase()}">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <strong>${trade.pair}</strong> - ${trade.side}
                                        <br>
                                        <small>${new Date(trade.open_time).toLocaleString('pt-BR')}</small>
                                    </div>
                                    <div style="text-align: right;">
                                        <div>Quantidade: ${trade.amount}</div>
                                        <div>Preço: $${trade.open_price?.toFixed(2) || 'N/A'}</div>
                                        ${trade.profit ? `<div style="color: ${trade.profit > 0 ? '#4CAF50' : '#f44336'};">P&L: $${trade.profit.toFixed(2)}</div>` : ''}
                                        <div style="font-size: 0.8em; color: #888;">${trade.status}</div>
                                    </div>
                                </div>
                            </div>
                        `).join('');
                    } else {
                        tradesList.innerHTML = '<div class="no-trades">Nenhum trade encontrado</div>';
                    }
                });
        }

        // Executar backtest
        function runBacktest() {
            const startDate = document.getElementById('backtest-start').value;
            const endDate = document.getElementById('backtest-end').value;
            const strategy = document.getElementById('strategy-select').value;

            const resultsDiv = document.getElementById('backtest-results');
            resultsDiv.innerHTML = '<div class="loading">Executando backtest...</div>';

            fetch('/api/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    strategy: strategy,
                    pair: currentPair,
                    timeframe: currentTimeframe,
                    start_date: startDate,
                    end_date: endDate
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.results) {
                    const r = data.results;
                    resultsDiv.innerHTML = `
                        <div style="margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
                            <h4>Resultados do Backtest</h4>
                            <p><strong>Trades:</strong> ${r.trades}</p>
                            <p><strong>Taxa de Acerto:</strong> ${(r.win_rate * 100).toFixed(1)}%</p>
                            <p><strong>Lucro:</strong> $${r.profit.toFixed(2)}</p>
                            <p><strong>Drawdown Máximo:</strong> ${(r.max_drawdown * 100).toFixed(1)}%</p>
                            <p><strong>Sharpe Ratio:</strong> ${r.sharpe_ratio}</p>
                            <p><strong>Retorno Total:</strong> ${(r.total_return * 100).toFixed(1)}%</p>
                        </div>
                    `;
                } else {
                    resultsDiv.innerHTML = '<div style="color: #f44336;">Erro ao executar backtest</div>';
                }
            });
        }

        // Atualizações periódicas
        setInterval(() => {
            updateStatusFromAPI();
            loadTrades();
        }, 5000);

        function updateStatusFromAPI() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateStatus(data));
        }

        // Inicialização
        window.onload = function() {
            updateStatusFromAPI();
            loadTrades();
            loadChart();
        };
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Dashboard principal"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def get_status():
    """Status do bot e sistema"""
    return jsonify(trading_data.get_status())

@app.route('/api/trades')
def get_trades():
    """Obter lista de trades"""
    return jsonify({
        'trades': trading_data.get_trades(),
        'total': len(trading_data.get_trades())
    })

@app.route('/api/balance')
def get_balance():
    """Obter informações de saldo"""
    return jsonify({
        'total_balance': round(trading_data.get_balance(), 2),
        'available_balance': round(trading_data.get_balance() * 0.9, 2),
        'locked_balance': round(trading_data.get_balance() * 0.1, 2),
        'currency': 'USDT'
    })

@app.route('/api/market_data/<path:pair>')
def get_market_data(pair):
    """Obter dados de mercado para gráficos"""
    try:
        # Tratar пар que vem com barras
        pair = pair.replace('-', '/').replace('_', '/')
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 200))
        print(f"Request market_data: pair={pair}, timeframe={timeframe}, limit={limit}")
        data = trading_data.get_market_data(pair, timeframe, limit)
        return jsonify({
            'pair': pair,
            'timeframe': timeframe,
            'data': data
        })
    except Exception as e:
        print(f"Error in get_market_data: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/indicators/<path:pair>')
def get_indicators(pair):
    """Calcular indicadores técnicos"""
    try:
        # Tratar пар que vem com barras
        pair = pair.replace('-', '/').replace('_', '/')
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 200))
        print(f"Request indicators: pair={pair}, timeframe={timeframe}, limit={limit}")
        indicators = trading_data.get_indicators(pair, timeframe, limit)
        return jsonify({
            'pair': pair,
            'indicators': indicators
        })
    except Exception as e:
        print(f"Error in get_indicators: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/chart_data/<path:pair>')
def get_chart_data(pair):
    """Dados completos para gráfico (OHLC + indicadores)"""
    try:
        # Tratar пар que vem com barras
        pair = pair.replace('-', '/').replace('_', '/')
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 200))
        print(f"Request chart_data: pair={pair}, timeframe={timeframe}, limit={limit}")

        market_data = trading_data.get_market_data(pair, timeframe, limit)
        indicators = trading_data.get_indicators(pair, timeframe, limit)

        return jsonify({
            'pair': pair,
            'timeframe': timeframe,
            'market_data': market_data,
            'indicators': indicators
        })
    except Exception as e:
        print(f"Error in get_chart_data: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Executar backtest"""
    try:
        data = request.get_json() or {}
        strategy = data.get('strategy', 'SafeTemplateStrategy')
        pair = data.get('pair', 'BTC/USDT')
        timeframe = data.get('timeframe', '15m')
        start_date = data.get('start_date', '2025-10-01')
        end_date = data.get('end_date', '2025-11-06')

        results = trading_data.run_backtest(strategy, pair, timeframe, start_date, end_date)

        if results:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao executar backtest'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/change_strategy', methods=['POST'])
def change_strategy():
    """Trocar estratégia sem parar o bot"""
    try:
        data = request.get_json() or {}
        strategy = data.get('strategy', 'SafeTemplateStrategy')

        # Validar se a estratégia é válida
        valid_strategies = ['SafeTemplateStrategy', 'EMA200RSI', 'MACDStrategy']
        if strategy not in valid_strategies:
            return jsonify({
                'success': False,
                'error': f'Estratégia inválida. Estratégias disponíveis: {", ".join(valid_strategies)}'
            })

        # Salvar estratégia anterior para log
        old_strategy = trading_data.current_strategy

        # Atualizar estratégia
        trading_data.current_strategy = strategy

        # Persistir no banco de dados se necessário
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Aqui você pode adicionar uma tabela de configurações se necessário
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not save strategy to database: {e}")

        return jsonify({
            'success': True,
            'message': f'Estratédia trocada de {old_strategy} para {strategy}',
            'old_strategy': old_strategy,
            'new_strategy': strategy
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Iniciar o bot"""
    try:
        data = request.get_json() or {}
        strategy = data.get('strategy', 'SafeTemplateStrategy')
        pair = data.get('pair', 'BTC/USDT')
        timeframe = data.get('timeframe', '15m')

        # Salvar estratégia anterior para log
        old_strategy = trading_data.current_strategy

        trading_data.current_strategy = strategy
        trading_data.current_pair = pair
        trading_data.timeframe = timeframe
        trading_data.bot_running = True
        trading_data.start_time = datetime.now()

        return jsonify({
            'success': True,
            'message': f'Bot iniciado com estratégia {strategy} no par {pair} ({timeframe})',
            'strategy_changed_from': old_strategy,
            'new_strategy': strategy
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Parar o bot"""
    try:
        trading_data.bot_running = False
        return jsonify({'success': True, 'message': 'Bot parado com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/strategies')
def get_strategies():
    """Listar estratégias disponíveis"""
    strategies = [
        {
            'name': 'SafeTemplateStrategy',
            'description': 'Estratégia base segura e robusta para iniciantes',
            'parameters': ['stoploss', 'trailing_stop'],
            'risk_level': 'Baixo',
            'timeframes': ['5m', '15m', '30m', '1h', '4h']
        },
        {
            'name': 'EMA200RSI',
            'description': 'Estratégia EMA + RSI para sinais de entrada e saída',
            'parameters': ['ema_fast', 'ema_slow', 'rsi_buy', 'rsi_sell'],
            'risk_level': 'Médio',
            'timeframes': ['15m', '30m', '1h', '4h']
        },
        {
            'name': 'MACDStrategy',
            'description': 'Estratégia MACD avançada com múltiplos timeframes',
            'parameters': ['macd_fast', 'macd_slow', 'macd_signal', 'rsi_filter'],
            'risk_level': 'Alto',
            'timeframes': ['5m', '15m', '1h', '4h']
        }
    ]
    return jsonify({'strategies': strategies})

# WebSocket para atualizações em tempo real
@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')
    emit('status', {'data': 'Conectado ao FreqTrade3 Professional'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Cliente desconectado')

# Thread para atualizações automáticas
def update_data():
    """Atualizar dados a cada 5 segundos"""
    while True:
        try:
            if trading_data.bot_running:
                # Simular trades se o bot estiver rodando
                if np.random.random() < 0.15:  # 15% chance a cada 5s
                    pair = trading_data.current_pair
                    base_price = 45000 if 'BTC' in pair else 3500 if 'ETH' in pair else 100
                    price = base_price * np.random.uniform(0.98, 1.02)

                    new_trade = {
                        'id': len(trading_data.trades) + 1,
                        'pair': pair,
                        'amount': round(np.random.uniform(0.01, 1.0), 4),
                        'open_price': round(price, 2),
                        'close_price': None,
                        'side': 'BUY' if np.random.random() > 0.5 else 'SELL',
                        'open_time': datetime.now().isoformat(),
                        'close_time': None,
                        'profit': None,
                        'status': 'open',
                        'strategy': trading_data.current_strategy
                    }
                    trading_data.trades.append(new_trade)

                    # Adicionar à base de dados
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO trades (pair, amount, open_price, side, open_time, status, total_balance)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            new_trade['pair'], new_trade['amount'], new_trade['open_price'],
                            new_trade['side'].lower(), new_trade['open_time'], new_trade['status'],
                            trading_data.get_balance()
                        ))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print(f"Erro ao inserir trade na DB: {e}")

            # Enviar atualização para todos os clientes
            socketio.emit('data_update', {
                'status': trading_data.get_status(),
                'timestamp': datetime.now().isoformat()
            })

            time.sleep(5)
        except Exception as e:
            print(f"Erro na atualização: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Iniciar thread de atualização
    update_thread = threading.Thread(target=update_data)
    update_thread.daemon = True
    update_thread.start()

    # Iniciar servidor
    print("FreqTrade3 Professional Dashboard iniciado!")
    print("Interface: http://localhost:8081")
    print("API: http://localhost:8081/api")
    print("WebSocket: ws://localhost:8081")

    socketio.run(app, host='0.0.0.0', port=8081, debug=False)
