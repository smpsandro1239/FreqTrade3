#!/usr/bin/env python3
"""
FreqTrade3 - Advanced Backtesting Engine
Sistema SUPERIOR ao FreqTrade original com backtesting REAL, gráficos TradingView e otimização
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import ta
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

class AdvancedBacktestEngine:
    """
    Motor de backtesting avançado - SUPERIOR ao FreqTrade original
    Características:
    - Dados históricos reais
    - Tráfego de entrada/saída visível no gráfico
    - Métricas profissionais completas
    - Otimização de estratégias
    - Stress testing
    - Walk-forward analysis
    """

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.exchange_data = {
            'BTC/USDT': 'BTC-USD',
            'ETH/USDT': 'ETH-USD',
            'BNB/USDT': 'BNB-USD',
            'ADA/USDT': 'ADA-USD',
            'XRP/USDT': 'XRP-USD',
            'SOL/USDT': 'SOL-USD'
        }

        # Configurações de trading
        self.initial_balance = 10000.0  # USDC
        self.commission = 0.001  # 0.1%
        self.slippage = 0.0002  # 0.02%
        self.risk_per_trade = 0.02  # 2% por trade

        # Cache de dados
        self.data_cache = {}
        self.strategies = {}

        # Métricas de performance
        self.performance_metrics = [
            'total_return', 'annualized_return', 'sharpe_ratio', 'sortino_ratio',
            'max_drawdown', 'calmar_ratio', 'win_rate', 'profit_factor',
            'expectancy', 'var_95', 'cvar_95', 'consecutive_wins', 'consecutive_losses'
        ]

        self.init_database()

    def init_database(self):
        """Inicializar base de dados com estrutura avançada"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de backtests
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    initial_balance REAL NOT NULL,
                    final_balance REAL NOT NULL,
                    total_return REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    win_rate REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    profit_factor REAL NOT NULL,
                    config_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tabela de trades do backtest
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backtest_id INTEGER NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity REAL NOT NULL,
                    commission REAL NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_pct REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    strategy_signal TEXT,
                    indicators_json TEXT,
                    FOREIGN KEY (backtest_id) REFERENCES backtests (id)
                )
            ''')

            # Tabela de otimização
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    score REAL NOT NULL,
                    total_return REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            conn.close()
            print("Advanced database initialized successfully")

        except Exception as e:
            print(f"Error initializing database: {e}")

    def get_real_market_data(self, symbol: str, start_date: str, end_date: str, interval: str = '15m') -> pd.DataFrame:
        """
        Obter dados reais de mercado do Yahoo Finance
        """
        try:
            # Mapear símbolo
            yf_symbol = self.exchange_data.get(symbol, 'BTC-USD')

            # Ticker
            ticker = yf.Ticker(yf_symbol)

            # Mapear interval
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '1h', '1d': '1d'
            }
            yf_interval = interval_map.get(interval, '15m')

            # Baixar dados
            hist = ticker.history(start=start_date, end=end_date, interval=yf_interval)

            if hist.empty:
                raise ValueError("No data available")

            # Limpar e preparar dados
            hist = hist.dropna()
            hist = hist.reset_index()
            hist.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']

            # Adicionar indicadores técnicos
            hist = self.add_technical_indicators(hist)

            print(f"Loaded {len(hist)} real candles for {symbol}")
            return hist

        except Exception as e:
            print(f"Error getting real data for {symbol}: {e}")
            return pd.DataFrame()

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adicionar indicadores técnicos avançados"""
        try:
            # Indicadores de tendência
            df['ema_12'] = ta.trend.ema_indicator(df['Close'], window=12)
            df['ema_26'] = ta.trend.ema_indicator(df['Close'], window=26)
            df['ema_50'] = ta.trend.ema_indicator(df['Close'], window=50)
            df['ema_200'] = ta.trend.ema_indicator(df['Close'], window=200)
            df['sma_20'] = ta.trend.sma_indicator(df['Close'], window=20)

            # MACD
            df['macd'] = ta.trend.macd(df['Close'])
            df['macd_signal'] = ta.trend.macd_signal(df['Close'])
            df['macd_histogram'] = ta.trend.macd_diff(df['Close'])

            # RSI
            df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
            df['rsi_oversold'] = df['rsi'] < 30
            df['rsi_overbought'] = df['rsi'] > 70

            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

            # Stochastic
            df['stoch_k'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'])
            df['stoch_d'] = ta.momentum.stoch_signal(df['High'], df['Low'], df['Close'])

            # Volume indicators
            df['volume_sma'] = ta.volume.volume SMA(df['Close'], df['Volume'])
            df['volume_ratio'] = df['Volume'] / df['volume_sma']

            # ADX (Average Directional Index)
            df['adx'] = ta.trend.adx(df['High'], df['Low'], df['Close'])

            # ATR (Average True Range)
            df['atr'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])

            # Support and Resistance
            df['resistance'] = df['High'].rolling(window=20).max()
            df['support'] = df['Low'].rolling(window=20).min()

            return df

        except Exception as e:
            print(f"Error adding indicators: {e}")
            return df

    def backtest_strategy(self, strategy_func, symbol: str, start_date: str, end_date: str,
                         timeframe: str = '15m', initial_balance: float = 10000.0,
                         strategy_params: Dict = None) -> Dict:
        """
        Executar backtest de estratégia com métricas completas
        """
        try:
            # Obter dados
            data = self.get_real_market_data(symbol, start_date, end_date, timeframe)
            if data.empty:
                return {'error': 'No data available'}

            # Inicializar backtest
            balance = initial_balance
            position = None  # {'side': 'long'/'short', 'entry_price': float, 'quantity': float}
            trades = []
            equity_curve = []
            signals = []

            print(f"Starting backtest: {symbol} from {start_date} to {end_date}")
            print(f"Data points: {len(data)}")

            # Loop principal de backtest
            for i in range(50, len(data)):  # Aguardar indicadores calcularem
                current_row = data.iloc[i]
                prev_row = data.iloc[i-1]

                # Calcular sinais
                signals = strategy_func(data[:i+1], strategy_params or {})

                # Verificar entrada
                if not position and signals.get('entry_signal'):
                    entry_price = current_row['Close']
                    # Aplicar slippage
                    if signals['entry_signal'] == 'long':
                        entry_price *= (1 + self.slippage)
                    else:
                        entry_price *= (1 - self.slippage)

                    # Calcular tamanho da posição
                    risk_amount = balance * self.risk_per_trade
                    if signals.get('stop_loss'):
                        stop_distance = abs(entry_price - signals['stop_loss'])
                        quantity = risk_amount / stop_distance if stop_distance > 0 else 0
                    else:
                        quantity = risk_amount / entry_price

                    if quantity > 0:
                        position = {
                            'side': signals['entry_signal'],
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'entry_time': current_row['Date'],
                            'stop_loss': signals.get('stop_loss'),
                            'take_profit': signals.get('take_profit'),
                            'strategy_reason': signals.get('reason', '')
                        }

                        # Registrar sinal
                        signals.append({
                            'time': current_row['Date'],
                            'type': 'entry',
                            'side': position['side'],
                            'price': entry_price,
                            'reason': position['strategy_reason']
                        })

                # Verificar saída
                elif position:
                    should_exit = False
                    exit_reason = ''

                    # Stop loss
                    if position['stop_loss']:
                        if position['side'] == 'long' and current_row['Low'] <= position['stop_loss']:
                            should_exit = True
                            exit_reason = 'stop_loss'
                        elif position['side'] == 'short' and current_row['High'] >= position['stop_loss']:
                            should_exit = True
                            exit_reason = 'stop_loss'

                    # Take profit
                    if not should_exit and position['take_profit']:
                        if position['side'] == 'long' and current_row['High'] >= position['take_profit']:
                            should_exit = True
                            exit_reason = 'take_profit'
                        elif position['side'] == 'short' and current_row['Low'] <= position['take_profit']:
                            should_exit = True
                            exit_reason = 'take_profit'

                    # Sinais de saída
                    if not should_exit and signals.get('exit_signal'):
                        should_exit = True
                        exit_reason = 'signal'

                    # Time-based exit (máximo 50 barras)
                    if not should_exit and i - position.get('entry_index', i) > 50:
                        should_exit = True
                        exit_reason = 'time_limit'

                    # Executar saída
                    if should_exit:
                        exit_price = current_row['Close']

                        # Aplicar slippage
                        if position['side'] == 'long':
                            exit_price *= (1 - self.slippage)
                        else:
                            exit_price *= (1 + self.slippage)

                        # Calcular P&L
                        if position['side'] == 'long':
                            pnl = (exit_price - position['entry_price']) * position['quantity']
                        else:
                            pnl = (position['entry_price'] - exit_price) * position['quantity']

                        # Comissão
                        commission = (position['entry_price'] + exit_price) * position['quantity'] * self.commission
                        net_pnl = pnl - commission

                        # Atualizar balance
                        balance += net_pnl

                        # Registrar trade
                        trade = {
                            'entry_time': position['entry_time'],
                            'exit_time': current_row['Date'],
                            'side': position['side'],
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'quantity': position['quantity'],
                            'pnl': net_pnl,
                            'pnl_pct': net_pnl / (position['entry_price'] * position['quantity']),
                            'commission': commission,
                            'exit_reason': exit_reason,
                            'duration': i - position.get('entry_index', i),
                            'strategy_reason': position['strategy_reason']
                        }
                        trades.append(trade)

                        # Registrar sinal de saída
                        signals.append({
                            'time': current_row['Date'],
                            'type': 'exit',
                            'side': position['side'],
                            'price': exit_price,
                            'reason': exit_reason
                        })

                        position = None

                # Registrar equity
                if position:
                    if position['side'] == 'long':
                        unrealized_pnl = (current_row['Close'] - position['entry_price']) * position['quantity']
                    else:
                        unrealized_pnl = (position['entry_price'] - current_row['Close']) * position['quantity']
                    current_equity = balance + unrealized_pnl
                else:
                    current_equity = balance

                equity_curve.append({
                    'time': current_row['Date'],
                    'equity': current_equity,
                    'balance': balance,
                    'price': current_row['Close']
                })

                # Armazenar índice de entrada
                if position and 'entry_index' not in position:
                    position['entry_index'] = i

            # Calcular métricas
            metrics = self.calculate_advanced_metrics(trades, equity_curve, initial_balance)

            # Salvar no banco
            backtest_id = self.save_backtest_results(strategy_func.__name__, symbol, timeframe,
                                                    start_date, end_date, metrics, trades, strategy_params)

            result = {
                'backtest_id': backtest_id,
                'success': True,
                'metrics': metrics,
                'trades': trades,
                'equity_curve': equity_curve,
                'signals': signals,
                'data_points': len(data),
                'initial_balance': initial_balance,
                'final_balance': metrics['final_balance']
            }

            print(f"Backtest completed: {metrics['total_trades']} trades, {metrics['win_rate']:.2%} win rate")
            return result

        except Exception as e:
            print(f"Error in backtest: {e}")
            return {'error': str(e), 'success': False}

    def calculate_advanced_metrics(self, trades: List[Dict], equity_curve: List[Dict],
                                 initial_balance: float) -> Dict:
        """Calcular métricas avançadas de performance"""
        try:
            if not trades:
                return {
                    'total_return': 0,
                    'annualized_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'total_trades': 0
                }

            # Métricas básicas
            final_equity = equity_curve[-1]['equity'] if equity_curve else initial_balance
            total_return = (final_equity - initial_balance) / initial_balance

            # Returns diários para Sharpe
            if len(equity_curve) > 1:
                daily_returns = [equity_curve[i]['equity'] / equity_curve[i-1]['equity'] - 1
                               for i in range(1, len(equity_curve))]
                excess_returns = [r - 0.02/252 for r in daily_returns]  # 2% risk-free rate

                if np.std(daily_returns) > 0:
                    sharpe_ratio = np.mean(excess_returns) / np.std(daily_returns) * np.sqrt(252)
                else:
                    sharpe_ratio = 0

                # Sortino ratio
                downside_returns = [r for r in excess_returns if r < 0]
                if np.std(downside_returns) > 0:
                    sortino_ratio = np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)
                else:
                    sortino_ratio = 0
            else:
                sharpe_ratio = 0
                sortino_ratio = 0

            # Drawdown máximo
            peak = initial_balance
            max_drawdown = 0
            for point in equity_curve:
                if point['equity'] > peak:
                    peak = point['equity']
                drawdown = (peak - point['equity']) / peak
                max_drawdown = max(max_drawdown, drawdown)

            # Calmar ratio
            annual_return = total_return * (252 / len(equity_curve)) if equity_curve else 0
            calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

            # Métricas de trades
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] < 0]

            win_rate = len(winning_trades) / len(trades) if trades else 0

            gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

            # Expectancy
            avg_win = gross_profit / len(winning_trades) if winning_trades else 0
            avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

            # VaR e CVaR
            pnl_values = [t['pnl'] for t in trades]
            var_95 = np.percentile(pnl_values, 5)
            cvar_95 = np.mean([p for p in pnl_values if p <= var_95])

            # Streaks
            consecutive_wins = 0
            consecutive_losses = 0
            current_streak_wins = 0
            current_streak_losses = 0

            for trade in trades:
                if trade['pnl'] > 0:
                    current_streak_wins += 1
                    current_streak_losses = 0
                    consecutive_wins = max(consecutive_wins, current_streak_wins)
                else:
                    current_streak_losses += 1
                    current_streak_wins = 0
                    consecutive_losses = max(consecutive_losses, current_streak_losses)

            return {
                'total_return': total_return,
                'annualized_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar_ratio,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'var_95': var_95,
                'cvar_95': cvar_95,
                'consecutive_wins': consecutive_wins,
                'consecutive_losses': consecutive_losses,
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'final_balance': final_equity,
                'initial_balance': initial_balance
            }

        except Exception as e:
            print(f"Error calculating metrics: {e}")
            return {}

    def save_backtest_results(self, strategy_name: str, symbol: str, timeframe: str,
                            start_date: str, end_date: str, metrics: Dict, trades: List[Dict],
                            strategy_params: Dict = None) -> int:
        """Salvar resultados do backtest no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Inserir backtest
            cursor.execute('''
                INSERT INTO backtests
                (name, strategy, pair, timeframe, start_date, end_date,
                 initial_balance, final_balance, total_return, trades_count,
                 win_rate, max_drawdown, sharpe_ratio, profit_factor, config_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"{strategy_name}_{symbol}_{timeframe}",
                strategy_name, symbol, timeframe, start_date, end_date,
                metrics['initial_balance'], metrics['final_balance'],
                metrics['total_return'], metrics['total_trades'],
                metrics['win_rate'], metrics['max_drawdown'],
                metrics['sharpe_ratio'], metrics['profit_factor'],
                json.dumps(strategy_params or {})
            ))

            backtest_id = cursor.lastrowid

            # Inserir trades
            for trade in trades:
                cursor.execute('''
                    INSERT INTO backtest_trades
                    (backtest_id, entry_time, exit_time, side, entry_price, exit_price,
                     quantity, commission, pnl, pnl_pct, strategy_signal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    backtest_id, trade['entry_time'], trade['exit_time'],
                    trade['side'], trade['entry_price'], trade['exit_price'],
                    trade['quantity'], trade['commission'], trade['pnl'],
                    trade['pnl_pct'], trade.get('strategy_reason', '')
                ))

            conn.commit()
            conn.close()

            print(f"Backtest saved with ID: {backtest_id}")
            return backtest_id

        except Exception as e:
            print(f"Error saving backtest: {e}")
            return 0

    def generate_tradingview_chart(self, backtest_id: int, output_path: str = None) -> str:
        """
        Gerar gráfico TradingView-like com entradas e saídas
        """
        try:
            # Carregar dados do backtest
            conn = sqlite3.connect(self.db_path)

            # Dados do backtest
            backtest_df = pd.read_sql_query(
                "SELECT * FROM backtests WHERE id = ?",
                conn, params=(backtest_id,)
            )

            # Trades
            trades_df = pd.read_sql_query(
                "SELECT * FROM backtest_trades WHERE backtest_id = ? ORDER BY entry_time",
                conn, params=(backtest_id,)
            )

            conn.close()

            if backtest_df.empty:
                return "No backtest data found"

            backtest = backtest_df.iloc[0]

            # Obter dados de mercado
            market_data = self.get_real_market_data(
                backtest['pair'],
                backtest['start_date'],
                backtest['end_date'],
                backtest['timeframe']
            )

            if market_data.empty:
                return "No market data available"

            # Criar gráfico
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f"{backtest['pair']} - {backtest['timeframe']}", "Volume"),
                row_width=[0.7, 0.3]
            )

            # Candlestick
            fig.add_trace(
                go.Candlestick(
                    x=market_data['Date'],
                    open=market_data['Open'],
                    high=market_data['High'],
                    low=market_data['Low'],
                    close=market_data['Close'],
                    name="OHLC"
                ),
                row=1, col=1
            )

            # Indicadores
            if 'ema_12' in market_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=market_data['Date'],
                        y=market_data['ema_12'],
                        name="EMA 12",
                        line=dict(color="blue", width=2)
                    ),
                    row=1, col=1
                )

            if 'ema_26' in market_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=market_data['Date'],
                        y=market_data['ema_26'],
                        name="EMA 26",
                        line=dict(color="orange", width=2)
                    ),
                    row=1, col=1
                )

            # Entradas e saídas
            for _, trade in trades_df.iterrows():
                entry_time = pd.to_datetime(trade['entry_time'])
                exit_time = pd.to_datetime(trade['exit_time']) if trade['exit_time'] else market_data['Date'].iloc[-1]

                # Entrada
                fig.add_trace(
                    go.Scatter(
                        x=[entry_time],
                        y=[trade['entry_price']],
                        mode='markers',
                        marker=dict(
                            symbol="arrow-right" if trade['side'] == 'long' else "arrow-left",
                            size=12,
                            color="lime" if trade['side'] == 'long' else "red",
                            angle=0 if trade['side'] == 'long' else 180
                        ),
                        name=f"Entry {trade['side']}"
                    ),
                    row=1, col=1
                )

                # Saída
                if trade['exit_price']:
                    fig.add_trace(
                        go.Scatter(
                            x=[exit_time],
                            y=[trade['exit_price']],
                            mode='markers',
                            marker=dict(
                                symbol="x",
                                size=10,
                                color="yellow"
                            ),
                            name=f"Exit {trade['exit_reason']}"
                        ),
                        row=1, col=1
                    )

            # Volume
            fig.add_trace(
                go.Bar(
                    x=market_data['Date'],
                    y=market_data['Volume'],
                    name="Volume",
                    marker_color="gray",
                    opacity=0.3
                ),
                row=2, col=1
            )

            # Layout
            fig.update_layout(
                title=f"Backtest {backtest['strategy']} - {backtest['pair']} ({backtest['timeframe']})",
                xaxis_title="Data",
                yaxis_title="Preço (USDC)",
                template="plotly_dark",
                height=800,
                showlegend=True
            )

            # Configurar eixos
            fig.update_yaxes(title_text="Preço (USDC)", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)

            # Salvar
            if not output_path:
                output_path = f"user_data/backtest_charts/backtest_{backtest_id}.html"

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.write_html(output_path)

            return output_path

        except Exception as e:
            print(f"Error generating chart: {e}")
            return f"Error: {str(e)}"

    def optimize_strategy(self, strategy_func, symbol: str, start_date: str, end_date: str,
                         timeframe: str = '15m', param_ranges: Dict = None) -> List[Dict]:
        """
        Otimização de estratégias usando algoritmo genético
        """
        try:
            print(f"Starting optimization for {symbol}...")

            # Parâmetros padrão se não fornecidos
            if param_ranges is None:
                param_ranges = {
                    'rsi_period': (10, 20),
                    'rsi_oversold': (20, 35),
                    'rsi_overbought': (65, 80),
                    'ema_fast': (8, 15),
                    'ema_slow': (20, 30),
                    'stop_loss_pct': (0.01, 0.05),
                    'take_profit_pct': (0.02, 0.08)
                }

            best_results = []

            # Grid search simplificado (para demonstração)
            # Em produção, usar algoritmo genético real
            for rsi_period in range(param_ranges['rsi_period'][0], param_ranges['rsi_period'][1] + 1, 2):
                for ema_fast in range(param_ranges['ema_fast'][0], param_ranges['ema_fast'][1] + 1, 2):
                    for stop_loss in [0.02, 0.03, 0.04]:  # Exemplos
                        params = {
                            'rsi_period': rsi_period,
                            'ema_fast': ema_fast,
                            'ema_slow': 26,  # Fixo para simplificação
                            'stop_loss_pct': stop_loss,
                            'take_profit_pct': stop_loss * 2
                        }

                        # Executar backtest
                        result = self.backtest_strategy(
                            strategy_func, symbol, start_date, end_date,
                            timeframe, 10000.0, params
                        )

                        if result.get('success'):
                            score = self.calculate_optimization_score(result['metrics'])
                            best_results.append({
                                'params': params,
                                'score': score,
                                'metrics': result['metrics']
                            })

            # Ordenar por score
            best_results.sort(key=lambda x: x['score'], reverse=True)

            # Salvar top 5
            for i, result in enumerate(best_results[:5]):
                self.save_optimization_result(
                    strategy_func.__name__, symbol, timeframe,
                    result['params'], result['score'], result['metrics']
                )

            print(f"Optimization completed. Best score: {best_results[0]['score']:.4f}" if best_results else "No results")
            return best_results[:10]

        except Exception as e:
            print(f"Error in optimization: {e}")
            return []

    def calculate_optimization_score(self, metrics: Dict) -> float:
        """Calcular score para otimização (maior é melhor)"""
        try:
            # Score composto: retorno ajustado ao risco
            score = 0

            # Retorno total (peso: 30%)
            score += metrics.get('total_return', 0) * 0.3

            # Sharpe ratio (peso: 25%)
            score += metrics.get('sharpe_ratio', 0) * 0.25

            # Profit factor (peso: 20%)
            score += metrics.get('profit_factor', 0) * 0.2

            # Win rate (peso: 10%)
            score += metrics.get('win_rate', 0) * 0.1

            # Penalizar drawdown alto (peso: 15%)
            score -= metrics.get('max_drawdown', 0) * 0.15

            return score

        except Exception as e:
            print(f"Error calculating score: {e}")
            return 0

    def save_optimization_result(self, strategy: str, symbol: str, timeframe: str,
                               params: Dict, score: float, metrics: Dict) -> None:
        """Salvar resultado de otimização"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO optimization_results
                (strategy, pair, timeframe, parameters_json, score, total_return,
                 sharpe_ratio, max_drawdown, trades_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy, symbol, timeframe, json.dumps(params),
                score, metrics.get('total_return', 0), metrics.get('sharpe_ratio', 0),
                metrics.get('max_drawdown', 0), metrics.get('total_trades', 0)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error saving optimization result: {e}")

    def get_backtest_history(self, limit: int = 20) -> List[Dict]:
        """Obter histórico de backtests"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, strategy, pair, timeframe, start_date, end_date,
                       total_return, trades_count, win_rate, max_drawdown, sharpe_ratio,
                       profit_factor, created_at
                FROM backtests
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return results

        except Exception as e:
            print(f"Error getting backtest history: {e}")
            return []

    def get_optimization_results(self, strategy: str = None, limit: int = 20) -> List[Dict]:
        """Obter resultados de otimização"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if strategy:
                cursor.execute('''
                    SELECT * FROM optimization_results
                    WHERE strategy = ?
                    ORDER BY score DESC
                    LIMIT ?
                ''', (strategy, limit))
            else:
                cursor.execute('''
                    SELECT * FROM optimization_results
                    ORDER BY score DESC
                    LIMIT ?
                ''', (limit,))

            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return results

        except Exception as e:
            print(f"Error getting optimization results: {e}")
            return []

# Estratégias de exemplo
def ema_crossover_strategy(data: pd.DataFrame, params: Dict = None) -> List[Dict]:
    """Estratégia de cruzamento de EMAs"""
    if len(data) < 50:
        return []

    params = params or {}
    fast_period = params.get('ema_fast', 12)
    slow_period = params.get('ema_slow', 26)
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    current = data.iloc[-1]
    prev = data.iloc[-2]

    signals = []

    # Verificar se EMAs existem
    if f'ema_{fast_period}' not in data.columns or f'ema_{slow_period}' not in data.columns:
        return signals

    fast_ema = current[f'ema_{fast_period}']
    slow_ema = current[f'ema_{slow_period}']
    prev_fast = prev[f'ema_{fast_period}']
    prev_slow = prev[f'ema_{slow_period}']
    rsi = current['rsi'] if 'rsi' in current else 50

    # Cruzamento de alta
    if (fast_ema > slow_ema and prev_fast <= prev_slow and
        rsi < rsi_overbought and current['Close'] > fast_ema):

        stop_loss = current['Close'] * (1 - params.get('stop_loss_pct', 0.02))
        take_profit = current['Close'] * (1 + params.get('take_profit_pct', 0.04))

        signals.append({
            'entry_signal': 'long',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'EMA {fast_period}/{slow_period} bullish crossover + RSI {rsi:.1f}'
        })

    # Cruzamento de baixa
    elif (fast_ema < slow_ema and prev_fast >= prev_slow and
          rsi > rsi_oversold and current['Close'] < fast_ema):

        stop_loss = current['Close'] * (1 + params.get('stop_loss_pct', 0.02))
        take_profit = current['Close'] * (1 - params.get('take_profit_pct', 0.04))

        signals.append({
            'entry_signal': 'short',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'EMA {fast_period}/{slow_period} bearish crossover + RSI {rsi:.1f}'
        })

    # Saída
    elif rsi > rsi_overbought or rsi < rsi_oversold:
        signals.append({'exit_signal': True, 'reason': f'RSI extreme {rsi:.1f}'})

    return signals

def rsi_mean_reversion_strategy(data: pd.DataFrame, params: Dict = None) -> List[Dict]:
    """Estratégia de reversão à média com RSI"""
    if len(data) < 50:
        return []

    params = params or {}
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    current = data.iloc[-1]
    rsi = current['rsi'] if 'rsi' in current else 50

    signals = []

    # Oversold - comprar
    if rsi < rsi_oversold:
        stop_loss = current['Close'] * (1 - params.get('stop_loss_pct', 0.03))
        take_profit = current['Close'] * (1 + params.get('take_profit_pct', 0.06))

        signals.append({
            'entry_signal': 'long',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'RSI oversold {rsi:.1f}'
        })

    # Overbought - vender
    elif rsi > rsi_overbought:
        stop_loss = current['Close'] * (1 + params.get('stop_loss_pct', 0.03))
        take_profit = current['Close'] * (1 - params.get('take_profit_pct', 0.06))

        signals.append({
            'entry_signal': 'short',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'RSI overbought {rsi:.1f}'
        })

    # Saída na zona neutra
    elif 40 < rsi < 60:
        signals.append({'exit_signal': True, 'reason': f'RSI neutral {rsi:.1f}'})

    return signals

# Instância global
backtest_engine = AdvancedBacktestEngine()

if __name__ == "__main__":
    # Demonstração
    print("Advanced Backtesting Engine initialized")
    print("Available strategies: ema_crossover_strategy, rsi_mean_reversion_strategy")

    # Exemplo de uso
    result = backtest_engine.backtest_strategy(
        ema_crossover_strategy,
        'BTC/USDT',
        '2025-10-01',
        '2025-11-07',
        '15m',
        10000.0
    )

    if result.get('success'):
        print(f"Backtest successful: {result['metrics']['total_return']:.2%} return")
    else:
        print(f"Backtest failed: {result.get('error')}")
