import json
import os
import sqlite3
from datetime import datetime
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ..database import DB_PATH
from ..strategies.strategies import ema_crossover_strategy, rsi_mean_reversion_strategy
from ..utils.indicators import add_technical_indicators
import optuna

class AdvancedBacktestEngine:
    """
    Motor de backtesting avançado com otimização via Optuna.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.exchange_data = {
            'BTC/USDT': 'BTC-USD',
            'ETH/USDT': 'ETH-USD',
            'BNB/USDT': 'BNB-USD',
            'ADA/USDT': 'ADA-USD',
            'XRP/USDT': 'XRP-USD',
            'SOL/USDT': 'SOL-USD'
        }
        self.initial_balance = 10000.0
        self.commission = 0.001
        self.slippage = 0.0002
        self.risk_per_trade = 0.02
        self.data_cache = {}
        self.strategies = {
            'ema_crossover_strategy': ema_crossover_strategy,
            'rsi_mean_reversion_strategy': rsi_mean_reversion_strategy
        }

    def get_real_market_data(self, symbol, start_date, end_date, interval='15m'):
        """
        Obter dados reais de mercado do Yahoo Finance
        """
        try:
            yf_symbol = self.exchange_data.get(symbol, 'BTC-USD')
            ticker = yf.Ticker(yf_symbol)
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '1h', '1d': '1d'
            }
            yf_interval = interval_map.get(interval, '15m')
            hist = ticker.history(start=start_date, end=end_date, interval=yf_interval)
            if hist.empty:
                raise ValueError("No data available")
            hist = hist.dropna()
            hist = hist.reset_index()
            hist.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
            hist = add_technical_indicators(hist)
            print(f"Loaded {len(hist)} real candles for {symbol}")
            return hist
        except Exception as e:
            print(f"Error getting real data for {symbol}: {e}")
            return pd.DataFrame()

    def backtest_strategy(self, strategy_func_name, symbol, start_date, end_date,
                         timeframe='15m', initial_balance=10000.0,
                         strategy_params=None):
        """
        Executar backtest de estratégia com métricas completas
        """
        try:
            strategy_func = self.strategies.get(strategy_func_name)
            if not strategy_func:
                return {'error': 'Strategy not found'}

            data = self.get_real_market_data(symbol, start_date, end_date, timeframe)
            if data.empty:
                return {'error': 'No data available'}

            balance = initial_balance
            position = None
            trades = []
            equity_curve = []
            signals = []

            for i in range(50, len(data)):
                current_row = data.iloc[i]
                signals_output = strategy_func(data[:i+1], strategy_params or {})

                if not position and signals_output.get('entry_signal'):
                    entry_price = current_row['Close']
                    if signals_output['entry_signal'] == 'long':
                        entry_price *= (1 + self.slippage)
                    else:
                        entry_price *= (1 - self.slippage)

                    risk_amount = balance * self.risk_per_trade
                    stop_distance = abs(entry_price - signals_output.get('stop_loss', 0))
                    quantity = risk_amount / stop_distance if stop_distance > 0 else 0

                    if quantity > 0:
                        position = {
                            'side': signals_output['entry_signal'],
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'entry_time': current_row['Date'],
                            'stop_loss': signals_output.get('stop_loss'),
                            'take_profit': signals_output.get('take_profit'),
                            'strategy_reason': signals_output.get('reason', ''),
                            'entry_index': i
                        }
                        signals.append({
                            'time': current_row['Date'],
                            'type': 'entry',
                            'side': position['side'],
                            'price': entry_price,
                            'reason': position['strategy_reason']
                        })

                elif position:
                    should_exit = False
                    exit_reason = ''
                    if position['stop_loss']:
                        if (position['side'] == 'long' and current_row['Low'] <= position['stop_loss']) or \
                           (position['side'] == 'short' and current_row['High'] >= position['stop_loss']):
                            should_exit = True
                            exit_reason = 'stop_loss'
                    if not should_exit and position['take_profit']:
                        if (position['side'] == 'long' and current_row['High'] >= position['take_profit']) or \
                           (position['side'] == 'short' and current_row['Low'] <= position['take_profit']):
                            should_exit = True
                            exit_reason = 'take_profit'
                    if not should_exit and signals_output.get('exit_signal'):
                        should_exit = True
                        exit_reason = 'signal'
                    if not should_exit and i - position.get('entry_index', i) > 50:
                        should_exit = True
                        exit_reason = 'time_limit'

                    if should_exit:
                        exit_price = current_row['Close']
                        if position['side'] == 'long':
                            exit_price *= (1 - self.slippage)
                        else:
                            exit_price *= (1 + self.slippage)

                        if position['side'] == 'long':
                            pnl = (exit_price - position['entry_price']) * position['quantity']
                        else:
                            pnl = (position['entry_price'] - exit_price) * position['quantity']

                        commission = (position['entry_price'] + exit_price) * position['quantity'] * self.commission
                        net_pnl = pnl - commission
                        balance += net_pnl
                        trades.append({
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
                        })
                        signals.append({
                            'time': current_row['Date'],
                            'type': 'exit',
                            'side': position['side'],
                            'price': exit_price,
                            'reason': exit_reason
                        })
                        position = None

                current_equity = balance
                if position:
                    if position['side'] == 'long':
                        unrealized_pnl = (current_row['Close'] - position['entry_price']) * position['quantity']
                    else:
                        unrealized_pnl = (position['entry_price'] - current_row['Close']) * position['quantity']
                    current_equity += unrealized_pnl
                equity_curve.append({
                    'time': current_row['Date'],
                    'equity': current_equity
                })

            metrics = self.calculate_advanced_metrics(trades, equity_curve, initial_balance)
            backtest_id = self.save_backtest_results(strategy_func.__name__, symbol, timeframe,
                                                    start_date, end_date, metrics, trades, strategy_params)
            result = {
                'backtest_id': backtest_id,
                'success': True,
                'metrics': metrics,
            }
            return result
        except Exception as e:
            print(f"Error in backtest: {e}")
            return {'error': str(e), 'success': False}

    def calculate_advanced_metrics(self, trades, equity_curve, initial_balance):
        """Calcular métricas avançadas de performance"""
        if not trades:
            return {}
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_balance
        total_return = (final_equity - initial_balance) / initial_balance
        daily_returns = [equity_curve[i]['equity'] / equity_curve[i-1]['equity'] - 1 for i in range(1, len(equity_curve))]
        sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        peak = initial_balance
        max_drawdown = 0
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            drawdown = (peak - point['equity']) / peak
            max_drawdown = max(max_drawdown, drawdown)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        pnl_values = [t['pnl'] for t in trades]
        var_95 = np.percentile(pnl_values, 5)
        cvar_95 = np.mean([p for p in pnl_values if p <= var_95])

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'total_trades': len(trades),
            'final_balance': final_equity
        }

    def save_backtest_results(self, strategy_name, symbol, timeframe, start_date, end_date, metrics, trades, strategy_params):
        """Salvar resultados do backtest no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO backtests
                (name, strategy, pair, timeframe, start_date, end_date,
                 initial_balance, final_balance, total_return, trades_count,
                 win_rate, max_drawdown, sharpe_ratio, profit_factor, config_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"{strategy_name}_{symbol}_{timeframe}",
                strategy_name, symbol, timeframe, start_date, end_date,
                metrics.get('initial_balance', self.initial_balance), metrics.get('final_balance', 0),
                metrics.get('total_return', 0), metrics.get('total_trades', 0),
                metrics.get('win_rate', 0), metrics.get('max_drawdown', 0),
                metrics.get('sharpe_ratio', 0), metrics.get('profit_factor', 0),
                json.dumps(strategy_params or {})
            ))
            backtest_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return backtest_id
        except Exception as e:
            print(f"Error saving backtest: {e}")
            return 0

    def generate_tradingview_chart(self, backtest_id, output_path=None):
        """
        Gerar gráfico TradingView-like com entradas e saídas
        """
        try:
            conn = sqlite3.connect(self.db_path)
            backtest_df = pd.read_sql_query("SELECT * FROM backtests WHERE id = ?", conn, params=(backtest_id,))
            trades_df = pd.read_sql_query("SELECT * FROM backtest_trades WHERE backtest_id = ? ORDER BY entry_time", conn, params=(backtest_id,))
            conn.close()

            if backtest_df.empty:
                return "No backtest data found"

            backtest = backtest_df.iloc[0]
            market_data = self.get_real_market_data(backtest['pair'], backtest['start_date'], backtest['end_date'], backtest['timeframe'])

            if market_data.empty:
                return "No market data available"

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=(f"{backtest['pair']} - {backtest['timeframe']}", "Volume"), row_width=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=market_data['Date'], open=market_data['Open'], high=market_data['High'], low=market_data['Low'], close=market_data['Close'], name="OHLC"), row=1, col=1)

            if 'ema_12' in market_data.columns:
                fig.add_trace(go.Scatter(x=market_data['Date'], y=market_data['ema_12'], name="EMA 12", line=dict(color="blue", width=2)), row=1, col=1)
            if 'ema_26' in market_data.columns:
                fig.add_trace(go.Scatter(x=market_data['Date'], y=market_data['ema_26'], name="EMA 26", line=dict(color="orange", width=2)), row=1, col=1)

            for _, trade in trades_df.iterrows():
                fig.add_trace(go.Scatter(x=[trade['entry_time']], y=[trade['entry_price']], mode='markers', marker=dict(symbol="arrow-up" if trade['side'] == 'long' else "arrow-down", size=10, color="green" if trade['side'] == 'long' else "red"), name=f"Entry {trade['side']}"), row=1, col=1)
                if trade['exit_price']:
                    fig.add_trace(go.Scatter(x=[trade['exit_time']], y=[trade['exit_price']], mode='markers', marker=dict(symbol="x", size=8, color="blue"), name=f"Exit {trade['exit_reason']}"), row=1, col=1)

            fig.add_trace(go.Bar(x=market_data['Date'], y=market_data['Volume'], name="Volume", marker_color="gray", opacity=0.3), row=2, col=1)
            fig.update_layout(title=f"Backtest {backtest['strategy']} - {backtest['pair']} ({backtest['timeframe']})", template="plotly_dark", height=800)

            if not output_path:
                output_path = f"user_data/backtest_charts/backtest_{backtest_id}.html"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.write_html(output_path)
            return output_path
        except Exception as e:
            print(f"Error generating chart: {e}")
            return f"Error: {str(e)}"

    def optimize_strategy(self, strategy_func_name, symbol: str, start_date: str, end_date: str,
                         timeframe: str = '15m', n_trials: int = 100) -> list:
        """
        Otimização de estratégias usando Optuna.
        """
        try:
            print(f"Iniciando otimização para {symbol} com {n_trials} tentativas...")

            def objective(trial):
                params = {
                    'rsi_period': trial.suggest_int('rsi_period', 10, 20),
                    'rsi_oversold': trial.suggest_int('rsi_oversold', 20, 35),
                    'rsi_overbought': trial.suggest_int('rsi_overbought', 65, 80),
                    'ema_fast': trial.suggest_int('ema_fast', 8, 15),
                    'ema_slow': trial.suggest_int('ema_slow', 20, 30),
                    'stop_loss_pct': trial.suggest_float('stop_loss_pct', 0.01, 0.05),
                    'take_profit_pct': trial.suggest_float('take_profit_pct', 0.02, 0.08),
                }

                result = self.backtest_strategy(
                    strategy_func_name, symbol, start_date, end_date,
                    timeframe, 10000.0, params
                )

                if result.get('success'):
                    score = self.calculate_optimization_score(result['metrics'])
                    return score
                return -1  # Retorna um score ruim em caso de falha

            study = optuna.create_study(direction='maximize')
            study.optimize(objective, n_trials=n_trials)

            best_trials = sorted(study.trials, key=lambda t: t.value, reverse=True)

            # Retorna os 10 melhores resultados
            return [
                {
                    'params': trial.params,
                    'score': trial.value,
                    'metrics': self.backtest_strategy(
                        strategy_func_name, symbol, start_date, end_date,
                        timeframe, 10000.0, trial.params
                    )['metrics']
                }
                for trial in best_trials[:10]
            ]

        except Exception as e:
            print(f"Erro na otimização: {e}")
            return []

    def calculate_optimization_score(self, metrics: dict) -> float:
        """Calcular score para otimização (maior é melhor)"""
        try:
            score = 0
            score += metrics.get('total_return', 0) * 0.3
            score += metrics.get('sharpe_ratio', 0) * 0.25
            score += metrics.get('profit_factor', 0) * 0.2
            score += metrics.get('win_rate', 0) * 0.1
            score -= metrics.get('max_drawdown', 0) * 0.15
            return score
        except Exception as e:
            print(f"Error calculating score: {e}")
            return 0

advanced_backtest = AdvancedBacktestEngine()