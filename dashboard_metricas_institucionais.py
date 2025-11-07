#!/usr/bin/env python3
"""
FreqTrade3 - Dashboard de Métricas Institucionais
Versão: 4.0 - Análise Profissional Avançada
Características: Métricas avançadas, visualizações, relatórios, benchmarks, KPIs
"""

import json
import logging
import math
import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo
from flask import Flask, jsonify, render_template_string, request
from plotly.subplots import make_subplots

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricCategory(Enum):
    """Categorias de métricas"""
    PERFORMANCE = "performance"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    OPERATIONAL = "operational"
    BENCHMARK = "benchmark"
    ALERTS = "alerts"

class TimeFrame(Enum):
    """Períodos de análise"""
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"
    LAST_1Y = "1y"
    ALL_TIME = "all"

@dataclass
class InstitutionalMetrics:
    """Métricas institucionais completas"""
    timestamp: str
    period: TimeFrame

    # Performance Metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float

    # Risk Metrics
    portfolio_beta: float
    portfolio_alpha: float
    information_ratio: float
    tracking_error: float
    correlation_btc: float
    concentration_risk: float
    liquidity_score: float

    # Portfolio Metrics
    total_value: float
    number_of_positions: int
    largest_position: float
    sector_allocation: Dict[str, float]
    asset_allocation: Dict[str, float]

    # Operational Metrics
    win_rate: float
    profit_factor: float
    average_trade: float
    largest_win: float
    largest_loss: float
    total_trades: int
    avg_holding_period: float

    # Benchmark Comparison
    vs_btc_return: float
    vs_btc_sharpe: float
    vs_btc_drawdown: float

    # Health Scores
    overall_health_score: float
    risk_adjusted_score: float
    operational_score: float

class InstitutionalDashboard:
    """Dashboard de métricas institucionais"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.dashboard_data_dir = 'dashboard_data'
        self.reports_dir = 'reports'
        self.templates_dir = 'templates'

        # Criar diretórios
        os.makedirs(self.dashboard_data_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)

        # Estado interno
        self.current_metrics = {}
        self.metrics_history = deque(maxlen=1000)
        self.benchmarks = {}
        self.thresholds = {}

        # Configuração
        self._load_configuration()

        # Cache
        self.cache_ttl = 300  # 5 minutos
        self.last_cache_update = {}

        # Inicializar dashboard
        self._init_dashboard()

    def _init_dashboard(self):
        """Inicializar dashboard"""
        # Carregar benchmarks
        self._load_benchmarks()

        # Definir thresholds
        self._define_thresholds()

        print("📊 Dashboard de Métricas Institucionais inicializado")

    def _load_configuration(self):
        """Carregar configurações do dashboard"""
        self.config = {
            'refresh_interval': 60,  # segundos
            'default_period': TimeFrame.LAST_30D,
            'cache_enabled': True,
            'export_formats': ['html', 'pdf', 'json'],
            'alert_thresholds': {
                'sharpe_ratio': 0.5,
                'max_drawdown': 0.15,
                'win_rate': 0.40,
                'concentration_risk': 0.30
            },
            'visualization': {
                'chart_height': 400,
                'color_scheme': 'plotly_dark',
                'default_theme': 'dark'
            }
        }

    def _load_benchmarks(self):
        """Carregar dados de benchmark"""
        # BTC como benchmark principal
        self.benchmarks = {
            'BTC': {
                'name': 'Bitcoin (BTC)',
                'return_24h': 0.02,
                'return_7d': 0.05,
                'return_30d': 0.15,
                'return_90d': 0.45,
                'return_1y': 1.20,
                'volatility': 0.65,
                'sharpe_ratio': 1.85,
                'max_drawdown': 0.85,
                'color': '#F7931A'
            },
            'SPY': {
                'name': 'S&P 500 ETF',
                'return_24h': 0.001,
                'return_7d': 0.008,
                'return_30d': 0.025,
                'return_90d': 0.075,
                'return_1y': 0.18,
                'volatility': 0.15,
                'sharpe_ratio': 1.20,
                'max_drawdown': 0.35,
                'color': '#1f77b4'
            }
        }

    def _define_thresholds(self):
        """Definir thresholds para análise"""
        self.thresholds = {
            MetricCategory.PERFORMANCE: {
                'sharpe_ratio': {'poor': 0.5, 'good': 1.0, 'excellent': 2.0},
                'sortino_ratio': {'poor': 0.7, 'good': 1.4, 'excellent': 2.1},
                'calmar_ratio': {'poor': 0.3, 'good': 0.8, 'excellent': 1.5},
                'max_drawdown': {'acceptable': 0.10, 'warning': 0.20, 'critical': 0.30}
            },
            MetricCategory.RISK: {
                'var_95': {'low': 0.02, 'medium': 0.05, 'high': 0.10},
                'cvar_95': {'low': 0.03, 'medium': 0.08, 'high': 0.15},
                'concentration_risk': {'diversified': 0.15, 'concentrated': 0.30, 'highly_concentrated': 0.50}
            },
            MetricCategory.OPERATIONAL: {
                'win_rate': {'poor': 0.40, 'acceptable': 0.50, 'good': 0.60},
                'profit_factor': {'poor': 1.0, 'acceptable': 1.2, 'good': 1.5}
            }
        }

    def calculate_institutional_metrics(self, period: TimeFrame = TimeFrame.LAST_30D) -> InstitutionalMetrics:
        """Calcular todas as métricas institucionais"""
        try:
            # Carregar dados
            trades_data = self._get_trades_data(period)
            portfolio_data = self._get_portfolio_data(period)
            market_data = self._get_market_data(period)

            # Calcular métricas
            performance_metrics = self._calculate_performance_metrics(trades_data, period)
            risk_metrics = self._calculate_risk_metrics(trades_data, market_data, period)
            portfolio_metrics = self._calculate_portfolio_metrics(portfolio_data, period)
            operational_metrics = self._calculate_operational_metrics(trades_data, period)
            benchmark_metrics = self._calculate_benchmark_metrics(trades_data, market_data, period)

            # Calcular scores
            health_scores = self._calculate_health_scores(
                performance_metrics, risk_metrics, operational_metrics
            )

            # Compilar métricas
            metrics = InstitutionalMetrics(
                timestamp=datetime.now().isoformat(),
                period=period,
                **performance_metrics,
                **risk_metrics,
                **portfolio_metrics,
                **operational_metrics,
                **benchmark_metrics,
                **health_scores
            )

            # Cache
            self.current_metrics[period.value] = metrics
            self.metrics_history.append(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Erro ao calcular métricas: {e}")
            return self._get_default_metrics(period)

    def _get_trades_data(self, period: TimeFrame) -> pd.DataFrame:
        """Obter dados de trades para o período"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Query para trades
            date_filter = self._get_date_filter(period)
            query = f"""
                SELECT
                    t.*,
                    m.open as market_open,
                    m.high as market_high,
                    m.low as market_low,
                    m.close as market_close,
                    m.volume as market_volume
                FROM trades t
                LEFT JOIN market_data m ON t.pair = m.pair
                    AND datetime(t.open_time) BETWEEN datetime('now', '{date_filter}') AND datetime('now')
                WHERE datetime(t.open_time) >= datetime('now', '{date_filter}')
                ORDER BY t.open_time ASC
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            # Processar dados
            if not df.empty:
                df['open_time'] = pd.to_datetime(df['open_time'])
                df['close_time'] = pd.to_datetime(df['close_time'], errors='coerce')
                df['profit'] = pd.to_numeric(df['profit'], errors='coerce')
                df['return'] = df['profit'] / (df['amount'] * df['open_price'])
                df['holding_period'] = (df['close_time'] - df['open_time']).dt.total_seconds() / 3600  # horas

            return df

        except Exception as e:
            logger.error(f"Erro ao obter dados de trades: {e}")
            return pd.DataFrame()

    def _get_portfolio_data(self, period: TimeFrame) -> Dict[str, Any]:
        """Obter dados de portfólio"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Posições atuais
            cursor.execute('''
                SELECT symbol, size, entry_price, mark_price, unrealized_pnl,
                       percentage, leverage, margin
                FROM manual_positions
                WHERE size != 0
            ''')

            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'symbol': row[0],
                    'size': float(row[1]),
                    'entry_price': float(row[2]),
                    'mark_price': float(row[3]),
                    'unrealized_pnl': float(row[4]),
                    'percentage': float(row[5]),
                    'leverage': float(row[6]),
                    'margin': float(row[7])
                })

            # Saldo atual
            cursor.execute('''
                SELECT asset, free, locked, total
                FROM manual_balances
            ''')

            balances = {}
            for row in cursor.fetchall():
                balances[row[0]] = {
                    'free': float(row[1]),
                    'locked': float(row[2]),
                    'total': float(row[3])
                }

            conn.close()

            return {
                'positions': positions,
                'balances': balances,
                'total_positions': len(positions),
                'total_value': sum(b['total'] for b in balances.values())
            }

        except Exception as e:
            logger.error(f"Erro ao obter dados de portfólio: {e}")
            return {'positions': [], 'balances': {}, 'total_value': 0}

    def _get_market_data(self, period: TimeFrame) -> pd.DataFrame:
        """Obter dados de mercado"""
        try:
            # Implementação simplificada - em produção seria uma API real
            dates = pd.date_range(
                start=datetime.now() - self._get_period_duration(period),
                end=datetime.now(),
                freq='1H'
            )

            # Simular dados do BTC
            np.random.seed(42)  # Para resultados consistentes
            returns = np.random.normal(0.001, 0.02, len(dates))
            prices = 45000 * np.cumprod(1 + returns)

            df = pd.DataFrame({
                'timestamp': dates,
                'close': prices,
                'return': returns
            })

            return df

        except Exception as e:
            logger.error(f"Erro ao obter dados de mercado: {e}")
            return pd.DataFrame()

    def _get_date_filter(self, period: TimeFrame) -> str:
        """Obter filtro de data para query"""
        period_map = {
            TimeFrame.LAST_24H: '-1 day',
            TimeFrame.LAST_7D: '-7 days',
            TimeFrame.LAST_30D: '-30 days',
            TimeFrame.LAST_90D: '-90 days',
            TimeFrame.LAST_1Y: '-1 year',
            TimeFrame.ALL_TIME: '-10 years'
        }
        return period_map.get(period, '-30 days')

    def _get_period_duration(self, period: TimeFrame) -> timedelta:
        """Obter duração do período"""
        duration_map = {
            TimeFrame.LAST_24H: timedelta(days=1),
            TimeFrame.LAST_7D: timedelta(days=7),
            TimeFrame.LAST_30D: timedelta(days=30),
            TimeFrame.LAST_90D: timedelta(days=90),
            TimeFrame.LAST_1Y: timedelta(days=365),
            TimeFrame.ALL_TIME: timedelta(days=3650)
        }
        return duration_map.get(period, timedelta(days=30))

    def _calculate_performance_metrics(self, trades_data: pd.DataFrame, period: TimeFrame) -> Dict[str, float]:
        """Calcular métricas de performance"""
        try:
            if trades_data.empty:
                return self._get_default_performance_metrics()

            # Retorno total
            total_profit = trades_data['profit'].sum()
            initial_capital = 10000  # Assumir capital inicial
            total_return = total_profit / initial_capital

            # Anualizar retorno
            period_days = self._get_period_duration(period).days
            annualized_return = (1 + total_return) ** (365 / period_days) - 1

            # Volatilidade
            returns = trades_data['return'].dropna()
            volatility = returns.std() * np.sqrt(252)  # Anualizada

            # Métricas de risco-retorno
            risk_free_rate = 0.02  # Taxa livre de risco

            if volatility > 0:
                sharpe_ratio = (annualized_return - risk_free_rate) / volatility
            else:
                sharpe_ratio = 0

            # Sortino ratio
            downside_returns = returns[returns < 0]
            downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_std if downside_std > 0 else 0

            # Calmar ratio
            max_drawdown = self._calculate_max_drawdown(trades_data)
            calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0

            # VaR e CVaR
            var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
            cvar_95 = np.mean(returns[returns <= var_95]) if len(returns) > 0 else var_95

            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'max_drawdown': max_drawdown,
                'var_95': var_95,
                'cvar_95': cvar_95
            }

        except Exception as e:
            logger.error(f"Erro ao calcular métricas de performance: {e}")
            return self._get_default_performance_metrics()

    def _calculate_risk_metrics(self, trades_data: pd.DataFrame, market_data: pd.DataFrame, period: TimeFrame) -> Dict[str, float]:
        """Calcular métricas de risco"""
        try:
            # Beta e Alpha (vs BTC)
            portfolio_returns = trades_data['return'].dropna()
            btc_returns = market_data['return'].dropna()

            if len(portfolio_returns) > 10 and len(btc_returns) > 10:
                # Alinhar séries
                min_len = min(len(portfolio_returns), len(btc_returns))
                p_returns = portfolio_returns.tail(min_len)
                b_returns = btc_returns.tail(min_len)

                # Calcular beta
                covariance = np.cov(p_returns, b_returns)[0, 1]
                btc_variance = np.var(b_returns)
                portfolio_beta = covariance / btc_variance if btc_variance > 0 else 1.0

                # Calcular alpha
                p_mean = np.mean(p_returns)
                b_mean = np.mean(btc_returns)
                risk_free_rate = 0.02 / 252  # Diária
                portfolio_alpha = p_mean - (risk_free_rate + portfolio_beta * (b_mean - risk_free_rate))
                portfolio_alpha = portfolio_alpha * 252  # Anualizado
            else:
                portfolio_beta = 1.0
                portfolio_alpha = 0.0

            # Information ratio
            excess_returns = portfolio_returns - btc_returns
            tracking_error = excess_returns.std() * np.sqrt(252)
            information_ratio = np.mean(excess_returns) * 252 / tracking_error if tracking_error > 0 else 0

            # Correlação com BTC
            if len(portfolio_returns) > 0 and len(btc_returns) > 0:
                min_len = min(len(portfolio_returns), len(btc_returns))
                correlation_btc = np.corrcoef(
                    portfolio_returns.tail(min_len),
                    btc_returns.tail(min_len)
                )[0, 1] if min_len > 1 else 0
            else:
                correlation_btc = 0

            # Concentração de risco
            concentration_risk = self._calculate_concentration_risk(trades_data)

            # Score de liquidez (simplificado)
            liquidity_score = 0.8  # Assumir boa liquidez para crypto

            return {
                'portfolio_beta': portfolio_beta,
                'portfolio_alpha': portfolio_alpha,
                'information_ratio': information_ratio,
                'tracking_error': tracking_error,
                'correlation_btc': correlation_btc,
                'concentration_risk': concentration_risk,
                'liquidity_score': liquidity_score
            }

        except Exception as e:
            logger.error(f"Erro ao calcular métricas de risco: {e}")
            return self._get_default_risk_metrics()

    def _calculate_portfolio_metrics(self, portfolio_data: Dict[str, Any], period: TimeFrame) -> Dict[str, float]:
        """Calcular métricas de portfólio"""
        try:
            positions = portfolio_data.get('positions', [])
            total_value = portfolio_data.get('total_value', 0)

            # Métricas básicas
            total_value = total_value
            number_of_positions = len(positions)

            # Maior posição
            largest_position = 0
            if positions:
                largest_position = max(pos['percentage'] for pos in positions)

            # Alocação por setor (simplificado)
            sector_allocation = self._calculate_sector_allocation(positions)

            # Alocação por ativo
            asset_allocation = {}
            if positions:
                for pos in positions:
                    symbol = pos['symbol']
                    asset_allocation[symbol] = pos['percentage']

            return {
                'total_value': total_value,
                'number_of_positions': number_of_positions,
                'largest_position': largest_position,
                'sector_allocation': sector_allocation,
                'asset_allocation': asset_allocation
            }

        except Exception as e:
            logger.error(f"Erro ao calcular métricas de portfólio: {e}")
            return self._get_default_portfolio_metrics()

    def _calculate_operational_metrics(self, trades_data: pd.DataFrame, period: TimeFrame) -> Dict[str, float]:
        """Calcular métricas operacionais"""
        try:
            if trades_data.empty:
                return self._get_default_operational_metrics()

            # Métricas básicas
            total_trades = len(trades_data)
            winning_trades = len(trades_data[trades_data['profit'] > 0])
            losing_trades = len(trades_data[trades_data['profit'] < 0])

            # Win rate
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            # Profit factor
            gross_profit = trades_data[trades_data['profit'] > 0]['profit'].sum()
            gross_loss = abs(trades_data[trades_data['profit'] < 0]['profit'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

            # Médias
            average_trade = trades_data['profit'].mean()
            largest_win = trades_data['profit'].max() if not trades_data.empty else 0
            largest_loss = trades_data['profit'].min() if not trades_data.empty else 0

            # Período médio de manutenção
            holding_periods = trades_data['holding_period'].dropna()
            avg_holding_period = holding_periods.mean() if len(holding_periods) > 0 else 0

            return {
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'average_trade': average_trade,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'total_trades': total_trades,
                'avg_holding_period': avg_holding_period
            }

        except Exception as e:
            logger.error(f"Erro ao calcular métricas operacionais: {e}")
            return self._get_default_operational_metrics()

    def _calculate_benchmark_metrics(self, trades_data: pd.DataFrame, market_data: pd.DataFrame, period: TimeFrame) -> Dict[str, float]:
        """Calcular métricas de benchmark"""
        try:
            btc_benchmark = self.benchmarks.get('BTC', {})

            # Comparações
            vs_btc_return = self._get_period_return(trades_data, period) - btc_benchmark.get('return_30d', 0)
            vs_btc_sharpe = 0 - btc_benchmark.get('sharpe_ratio', 1.85)  # Nossa sharpe - BTC sharpe
            vs_btc_drawdown = 0 - btc_benchmark.get('max_drawdown', 0.85)  # Nosso DD - BTC DD

            return {
                'vs_btc_return': vs_btc_return,
                'vs_btc_sharpe': vs_btc_sharpe,
                'vs_btc_drawdown': vs_btc_drawdown
            }

        except Exception as e:
            logger.error(f"Erro ao calcular métricas de benchmark: {e}")
            return self._get_default_benchmark_metrics()

    def _calculate_health_scores(self, performance: Dict, risk: Dict, operational: Dict) -> Dict[str, float]:
        """Calcular scores de saúde"""
        try:
            # Score geral (0-100)
            performance_score = min(100, max(0, performance.get('sharpe_ratio', 0) * 20))
            risk_score = max(0, 100 - risk.get('max_drawdown', 0) * 200)
            operational_score = operational.get('win_rate', 0) * 100

            overall_health = (performance_score + risk_score + operational_score) / 3

            return {
                'overall_health_score': overall_health,
                'risk_adjusted_score': risk_score,
                'operational_score': operational_score
            }

        except Exception as e:
            logger.error(f"Erro ao calcular health scores: {e}")
            return self._get_default_health_scores()

    def _calculate_max_drawdown(self, trades_data: pd.DataFrame) -> float:
        """Calcular máximo drawdown"""
        try:
            if trades_data.empty:
                return 0

            # Calcular equity curve
            trades_data = trades_data.sort_values('open_time')
            cumulative_pnl = trades_data['profit'].cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdown = (cumulative_pnl - running_max) / (running_max + 1)  # Evitar divisão por zero

            return abs(drawdown.min())

        except Exception as e:
            logger.error(f"Erro ao calcular max drawdown: {e}")
            return 0

    def _calculate_concentration_risk(self, trades_data: pd.DataFrame) -> float:
        """Calcular risco de concentração"""
        try:
            if trades_data.empty:
                return 0

            # Herfindahl Index
            position_sizes = trades_data.groupby('pair')['amount'].sum()
            total_size = position_sizes.sum()

            if total_size == 0:
                return 0

            # Normalizar e calcular HHI
            weights = position_sizes / total_size
            hhi = (weights ** 2).sum()

            return hhi

        except Exception as e:
            logger.error(f"Erro ao calcular concentração: {e}")
            return 0

    def _calculate_sector_allocation(self, positions: List[Dict]) -> Dict[str, float]:
        """Calcular alocação por setor"""
        sectors = {
            'store_of_value': ['BTC'],
            'smart_contracts': ['ETH'],
            'exchange': ['BNB'],
            'layer1': ['ADA', 'SOL', 'DOT'],
            'payments': ['XRP'],
            'oracle': ['LINK']
        }

        sector_allocation = {}

        for sector, symbols in sectors.items():
            sector_weight = 0
            for pos in positions:
                if pos['symbol'] in symbols:
                    sector_weight += pos['percentage']
            sector_allocation[sector] = sector_weight

        return sector_allocation

    def _get_period_return(self, trades_data: pd.DataFrame, period: TimeFrame) -> float:
        """Obter retorno do período"""
        try:
            if trades_data.empty:
                return 0

            total_profit = trades_data['profit'].sum()
            initial_capital = 10000
            return total_profit / initial_capital

        except Exception as e:
            logger.error(f"Erro ao obter retorno do período: {e}")
            return 0

    # Métodos para métricas padrão (fallback)
    def _get_default_metrics(self, period: TimeFrame) -> InstitutionalMetrics:
        """Retornar métricas padrão"""
        return InstitutionalMetrics(
            timestamp=datetime.now().isoformat(),
            period=period,
            **self._get_default_performance_metrics(),
            **self._get_default_risk_metrics(),
            **self._get_default_portfolio_metrics(),
            **self._get_default_operational_metrics(),
            **self._get_default_benchmark_metrics(),
            **self._get_default_health_scores()
        )

    def _get_default_performance_metrics(self) -> Dict[str, float]:
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.20,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown': 0.0,
            'var_95': 0.05,
            'cvar_95': 0.07
        }

    def _get_default_risk_metrics(self) -> Dict[str, float]:
        return {
            'portfolio_beta': 1.0,
            'portfolio_alpha': 0.0,
            'information_ratio': 0.0,
            'tracking_error': 0.0,
            'correlation_btc': 0.7,
            'concentration_risk': 0.2,
            'liquidity_score': 0.8
        }

    def _get_default_portfolio_metrics(self) -> Dict[str, float]:
        return {
            'total_value': 10000.0,
            'number_of_positions': 0,
            'largest_position': 0.0,
            'sector_allocation': {},
            'asset_allocation': {}
        }

    def _get_default_operational_metrics(self) -> Dict[str, float]:
        return {
            'win_rate': 0.5,
            'profit_factor': 1.2,
            'average_trade': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'total_trades': 0,
            'avg_holding_period': 0.0
        }

    def _get_default_benchmark_metrics(self) -> Dict[str, float]:
        return {
            'vs_btc_return': 0.0,
            'vs_btc_sharpe': 0.0,
            'vs_btc_drawdown': 0.0
        }

    def _get_default_health_scores(self) -> Dict[str, float]:
        return {
            'overall_health_score': 50.0,
            'risk_adjusted_score': 50.0,
            'operational_score': 50.0
        }

    def generate_performance_chart(self, period: TimeFrame = TimeFrame.LAST_30D) -> str:
        """Gerar gráfico de performance"""
        try:
            # Obter dados
            trades_data = self._get_trades_data(period)
            metrics = self.calculate_institutional_metrics(period)

            # Criar subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    'Equity Curve', 'Drawdown',
                    'Monthly Returns', 'Return Distribution',
                    'Rolling Sharpe (30d)', 'Rolling Max Drawdown (30d)'
                ],
                specs=[[{"colspan": 2}, None],
                       [{"type": "bar"}, {"type": "histogram"}],
                       [{"type": "scatter"}, {"type": "scatter"}]]
            )

            # Equity Curve
            if not trades_data.empty:
                trades_data = trades_data.sort_values('open_time')
                trades_data['cumulative_pnl'] = trades_data['profit'].cumsum()

                fig.add_trace(
                    go.Scatter(
                        x=trades_data['open_time'],
                        y=trades_data['cumulative_pnl'],
                        mode='lines',
                        name='Equity Curve',
                        line=dict(color='#4CAF50', width=2)
                    ),
                    row=1, col=1
                )

            # Drawdown
            if not trades_data.empty:
                running_max = trades_data['cumulative_pnl'].expanding().max()
                drawdown = (trades_data['cumulative_pnl'] - running_max) / (running_max + 1)

                fig.add_trace(
                    go.Scatter(
                        x=trades_data['open_time'],
                        y=drawdown,
                        mode='lines',
                        name='Drawdown',
                        line=dict(color='#f44336', width=2),
                        fill='tonexty'
                    ),
                    row=1, col=1
                )

            # Monthly Returns
            if not trades_data.empty:
                monthly_returns = trades_data.groupby(trades_data['open_time'].dt.to_period('M'))['profit'].sum()

                fig.add_trace(
                    go.Bar(
                        x=[str(p) for p in monthly_returns.index],
                        y=monthly_returns.values,
                        name='Monthly Returns',
                        marker_color=['#4CAF50' if x > 0 else '#f44336' for x in monthly_returns.values]
                    ),
                    row=2, col=1
                )

            # Return Distribution
            if not trades_data.empty:
                fig.add_trace(
                    go.Histogram(
                        x=trades_data['return'],
                        nbinsx=30,
                        name='Return Distribution',
                        marker_color='#2196F3'
                    ),
                    row=2, col=2
                )

            # Rolling Sharpe
            if not trades_data.empty and len(trades_data) > 30:
                rolling_sharpe = trades_data['return'].rolling(30).mean() / trades_data['return'].rolling(30).std() * np.sqrt(252)

                fig.add_trace(
                    go.Scatter(
                        x=trades_data['open_time'],
                        y=rolling_sharpe,
                        mode='lines',
                        name='Rolling Sharpe',
                        line=dict(color='#FF9800', width=2)
                    ),
                    row=3, col=1
                )

            # Rolling Max Drawdown
            if not trades_data.empty and len(trades_data) > 30:
                window = 30
                rolling_max = trades_data['cumulative_pnl'].rolling(window).max()
                rolling_drawdown = (trades_data['cumulative_pnl'] - rolling_max) / (rolling_max + 1)

                fig.add_trace(
                    go.Scatter(
                        x=trades_data['open_time'],
                        y=rolling_drawdown,
                        mode='lines',
                        name='Rolling Max DD',
                        line=dict(color='#9C27B0', width=2)
                    ),
                    row=3, col=2
                )

            # Layout
            fig.update_layout(
                title=f'Performance Analysis - {period.value}',
                showlegend=True,
                height=900,
                template='plotly_dark'
            )

            # Salvar
            chart_file = os.path.join(self.dashboard_data_dir, f'performance_chart_{period.value}.html')
            fig.write_html(chart_file)

            return chart_file

        except Exception as e:
            logger.error(f"Erro ao gerar gráfico de performance: {e}")
            return ""

    def generate_risk_chart(self, period: TimeFrame = TimeFrame.LAST_30D) -> str:
        """Gerar gráfico de risco"""
        try:
            metrics = self.calculate_institutional_metrics(period)

            # Criar subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    'Value at Risk (VaR)', 'Risk Metrics',
                    'Correlation Matrix', 'Sector Allocation'
                ]
            )

            # VaR
            var_95 = metrics.var_95
            var_99 = var_95 * 1.5  # Estimativa

            fig.add_trace(
                go.Bar(
                    x=['VaR 95%', 'VaR 99%'],
                    y=[var_95, var_99],
                    name='Value at Risk',
                    marker_color=['#FF9800', '#f44336']
                ),
                row=1, col=1
            )

            # Risk Metrics
            fig.add_trace(
                go.Scatter(
                    x=[metrics.sharpe_ratio],
                    y=[metrics.max_drawdown],
                    mode='markers',
                    name='Risk-Return Profile',
                    marker=dict(
                        size=100,
                        color=['#4CAF50' if metrics.sharpe_ratio > 1 else '#FF9800'],
                        opacity=0.7
                    )
                ),
                row=1, col=2
            )

            # Correlation Matrix (simplificado)
            symbols = list(metrics.asset_allocation.keys())[:5]  # Top 5
            corr_data = np.random.rand(len(symbols), len(symbols))  # Simulado

            fig.add_trace(
                go.Heatmap(
                    z=corr_data,
                    x=symbols,
                    y=symbols,
                    colorscale='RdYlBu',
                    name='Correlation'
                ),
                row=2, col=1
            )

            # Sector Allocation
            if metrics.sector_allocation:
                fig.add_trace(
                    go.Pie(
                        labels=list(metrics.sector_allocation.keys()),
                        values=list(metrics.sector_allocation.values()),
                        name='Sector Allocation'
                    ),
                    row=2, col=2
                )

            # Layout
            fig.update_layout(
                title=f'Risk Analysis - {period.value}',
                showlegend=True,
                height=600,
                template='plotly_dark'
            )

            # Salvar
            chart_file = os.path.join(self.dashboard_data_dir, f'risk_chart_{period.value}.html')
            fig.write_html(chart_file)

            return chart_file

        except Exception as e:
            logger.error(f"Erro ao gerar gráfico de risco: {e}")
            return ""

    def generate_dashboard_html(self, period: TimeFrame = TimeFrame.LAST_30D) -> str:
        """Gerar HTML completo do dashboard"""
        try:
            # Calcular métricas
            metrics = self.calculate_institutional_metrics(period)

            # Gerar gráficos
            performance_chart = self.generate_performance_chart(period)
            risk_chart = self.generate_risk_chart(period)

            # Template HTML
            html_template = '''
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>FreqTrade3 - Dashboard Institucional</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #fff; }
                    .header { background: linear-gradient(135deg, #1a1f2e 0%, #0f1419 100%); padding: 20px; border-bottom: 1px solid #333; }
                    .header h1 { font-size: 2.5em; font-weight: 300; background: linear-gradient(45deg, #4CAF50, #2196F3); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                    .container { display: grid; grid-template-columns: 300px 1fr; gap: 20px; padding: 20px; }
                    .sidebar { background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; height: fit-content; }
                    .main-content { display: grid; grid-template-rows: auto auto 1fr; gap: 20px; }
                    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
                    .metric-card { background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); }
                    .metric-value { font-size: 1.8em; font-weight: 600; margin-bottom: 5px; }
                    .metric-label { font-size: 0.9em; color: #888; text-transform: uppercase; letter-spacing: 1px; }
                    .metric-change { font-size: 0.8em; margin-top: 5px; }
                    .positive { color: #4CAF50; }
                    .negative { color: #f44336; }
                    .chart-container { background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); }
                    .tabs { display: flex; background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 5px; margin-bottom: 20px; }
                    .tab { padding: 10px 20px; background: transparent; border: none; color: #fff; cursor: pointer; border-radius: 5px; transition: all 0.3s; }
                    .tab.active { background: #4CAF50; }
                    .tab-content { display: none; }
                    .tab-content.active { display: block; }
                    iframe { width: 100%; height: 500px; border: none; border-radius: 10px; }
                    .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
                    .status-good { background: #4CAF50; }
                    .status-warning { background: #FF9800; }
                    .status-critical { background: #f44336; }
                    @media (max-width: 1200px) { .container { grid-template-columns: 1fr; } }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>FreqTrade3 - Dashboard Institucional</h1>
                    <p>Última atualização: {timestamp}</p>
                </div>

                <div class="container">
                    <div class="sidebar">
                        <h3>Controles</h3>
                        <div class="tabs">
                            <button class="tab active" onclick="switchTab('performance')">Performance</button>
                            <button class="tab" onclick="switchTab('risk')">Risco</button>
                        </div>

                        <h3>Período</h3>
                        <select id="period-select" onchange="changePeriod()">
                            <option value="24h">Últimas 24h</option>
                            <option value="7d">Últimos 7 dias</option>
                            <option value="30d" selected>Últimos 30 dias</option>
                            <option value="90d">Últimos 90 dias</option>
                            <option value="1y">Último ano</option>
                        </select>

                        <h3>Health Score</h3>
                        <div style="text-align: center; margin: 20px 0;">
                            <div style="font-size: 3em; font-weight: bold; color: {health_color};">
                                {overall_score:.0f}
                            </div>
                            <div>Score Geral</div>
                        </div>

                        <h3>Status</h3>
                        <div class="metric-card">
                            <div><span class="status-indicator {status_class}"></span>Risco</div>
                            <div><span class="status-indicator {status_class}"></span>Performance</div>
                            <div><span class="status-indicator {status_class}"></span>Operacional</div>
                        </div>
                    </div>

                    <div class="main-content">
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-value {return_class}">{total_return:.1%}</div>
                                <div class="metric-label">Retorno Total</div>
                                <div class="metric-change {return_class}">{annualized_return:.1%} anualizado</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value {sharpe_class}">{sharpe_ratio:.2f}</div>
                                <div class="metric-label">Sharpe Ratio</div>
                                <div class="metric-change {sortino_class}>Sortino: {sortino_ratio:.2f}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value {dd_class}">{max_drawdown:.1%}</div>
                                <div class="metric-label">Max Drawdown</div>
                                <div class="metric-change">VaR 95%: {var_95:.1%}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value {winrate_class}">{win_rate:.1%}</div>
                                <div class="metric-label">Win Rate</div>
                                <div class="metric-change">Trades: {total_trades}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">{total_value:,.0f}</div>
                                <div class="metric-label">Valor Total</div>
                                <div class="metric-change">Posições: {number_of_positions}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value {beta_class}">{portfolio_beta:.2f}</div>
                                <div class="metric-label">Portfolio Beta</div>
                                <div class="metric-change">vs BTC: {vs_btc_return:.1%}</div>
                            </div>
                        </div>

                        <div class="chart-container">
                            <div id="performance-tab" class="tab-content active">
                                <h3>Análise de Performance</h3>
                                {performance_chart_html}
                            </div>

                            <div id="risk-tab" class="tab-content">
                                <h3>Análise de Risco</h3>
                                {risk_chart_html}
                            </div>
                        </div>
                    </div>
                </div>

                <script>
                    function switchTab(tabName) {
                        // Hide all tab contents
                        const contents = document.querySelectorAll('.tab-content');
                        contents.forEach(content => content.classList.remove('active'));

                        // Remove active class from all tabs
                        const tabs = document.querySelectorAll('.tab');
                        tabs.forEach(tab => tab.classList.remove('active'));

                        // Show selected tab content
                        document.getElementById(tabName + '-tab').classList.add('active');
                        event.target.classList.add('active');
                    }

                    function changePeriod() {
                        const period = document.getElementById('period-select').value;
                        window.location.href = '?period=' + period;
                    }
                </script>
            </body>
            </html>
            '''

            # Preparar dados para template
            template_data = {
                'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'overall_score': metrics.overall_health_score,
                'health_color': '#4CAF50' if metrics.overall_health_score > 70 else '#FF9800' if metrics.overall_health_score > 50 else '#f44336',
                'status_class': 'status-good' if metrics.overall_health_score > 70 else 'status-warning',
                'total_return': metrics.total_return,
                'return_class': 'positive' if metrics.total_return > 0 else 'negative',
                'annualized_return': metrics.annualized_return,
                'sharpe_ratio': metrics.sharpe_ratio,
                'sharpe_class': 'positive' if metrics.sharpe_ratio > 1 else 'negative',
                'sortino_ratio': metrics.sortino_ratio,
                'sortino_class': 'positive' if metrics.sortino_ratio > 1 else 'negative',
                'max_drawdown': metrics.max_drawdown,
                'dd_class': 'positive' if metrics.max_drawdown < 0.1 else 'negative',
                'var_95': abs(metrics.var_95),
                'win_rate': metrics.win_rate,
                'winrate_class': 'positive' if metrics.win_rate > 0.5 else 'negative',
                'total_trades': metrics.total_trades,
                'total_value': metrics.total_value,
                'number_of_positions': metrics.number_of_positions,
                'portfolio_beta': metrics.portfolio_beta,
                'beta_class': 'positive' if metrics.portfolio_beta < 1.2 else 'negative',
                'vs_btc_return': metrics.vs_btc_return,
                'performance_chart_html': f'<iframe src="{performance_chart}"></iframe>' if performance_chart else '<p>Gráfico não disponível</p>',
                'risk_chart_html': f'<iframe src="{risk_chart}"></iframe>' if risk_chart else '<p>Gráfico não disponível</p>'
            }

            # Renderizar HTML
            html_content = html_template.format(**template_data)

            # Salvar arquivo
            dashboard_file = os.path.join(self.dashboard_data_dir, f'institutional_dashboard_{period.value}.html')
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            return dashboard_file

        except Exception as e:
            logger.error(f"Erro ao gerar dashboard HTML: {e}")
            return ""

    def export_report(self, format: str = 'html', period: TimeFrame = TimeFrame.LAST_30D) -> str:
        """Exportar relatório"""
        try:
            metrics = self.calculate_institutional_metrics(period)

            if format == 'json':
                # Export JSON
                report_data = asdict(metrics)
                report_file = os.path.join(self.reports_dir, f'report_{period.value}.json')
                with open(report_file, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
                return report_file

            elif format == 'html':
                # Export HTML (dashboard completo)
                return self.generate_dashboard_html(period)

            else:
                raise ValueError(f"Formato não suportado: {format}")

        except Exception as e:
            logger.error(f"Erro ao exportar relatório: {e}")
            return ""

    def get_dashboard_data(self, period: TimeFrame = TimeFrame.LAST_30D) -> Dict[str, Any]:
        """Obter dados para API"""
        try:
            metrics = self.calculate_institutional_metrics(period)

            return {
                'success': True,
                'period': period.value,
                'timestamp': metrics.timestamp,
                'metrics': asdict(metrics),
                'benchmarks': self.benchmarks,
                'thresholds': self.thresholds
            }

        except Exception as e:
            logger.error(f"Erro ao obter dados do dashboard: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# API para integração
def create_institutional_dashboard():
    """Criar instância do dashboard institucional"""
    return InstitutionalDashboard()

if __name__ == "__main__":
    # Teste do dashboard
    dashboard = create_institutional_dashboard()

    # Calcular métricas
    metrics = dashboard.calculate_institutional_metrics(TimeFrame.LAST_30D)
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {metrics.max_drawdown:.1%}")
    print(f"Win Rate: {metrics.win_rate:.1%}")

    # Gerar dashboard HTML
    html_file = dashboard.generate_dashboard_html(TimeFrame.LAST_30D)
    print(f"Dashboard gerado: {html_file}")

    # Exportar relatório
    json_report = dashboard.export_report('json', TimeFrame.LAST_30D)
    print(f"Relatório JSON: {json_report}")
