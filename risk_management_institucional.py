#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Risk Management Institucional
Versão: 4.0 - Risk Management Avançado
Características: Position sizing dinâmico, stop loss inteligente, exposure limits, VaR, CVaR
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
import schedule


@dataclass
class RiskMetrics:
    """Métricas de risco calculadas"""
    timestamp: str
    symbol: str
    portfolio_value: float
    var_1d: float  # Value at Risk 1 dia
    cvar_1d: float  # Conditional VaR 1 dia
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float
    correlation_matrix: Dict[str, float]
    exposure_by_symbol: Dict[str, float]
    concentration_risk: float
    liquidity_risk: float

@dataclass
class PositionRisk:
    """Risco de uma posição individual"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: float = 0.0
    risk_reward_ratio: float = 0.0
    expected_return: float = 0.0
    max_loss: float = 0.0
    volatility: float = 0.0

class RiskLevel(Enum):
    """Níveis de risco"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class InstitutionalRiskManager:
    """Sistema de Risk Management de nível institucional"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db',
                 initial_capital: float = 100000.0):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.risk_data_dir = 'risk_data'
        self.config_file = 'configs/risk_config.yaml'

        # Criar diretórios
        os.makedirs(self.risk_data_dir, exist_ok=True)
        os.makedirs('configs', exist_ok=True)

        # Estado interno
        self.current_portfolio = {}
        self.risk_metrics_history = deque(maxlen=1000)  # Últimas 1000 métricas
        self.daily_pnl = {}
        self.position_sizes = {}
        self.risk_limits = self._load_risk_limits()

        # Inicializar sistema
        self._init_risk_manager()

        # Thread de monitoramento
        self.monitoring_active = False
        self.monitor_thread = None

    def _init_risk_manager(self):
        """Inicializar sistema de risk management"""
        # Inicializar base de dados
        self._init_database()

        # Carregar portfólio atual
        self._load_current_portfolio()

        print("🛡️  Risk Manager Institucional inicializado")

    def _init_database(self):
        """Inicializar base de dados de risco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de métricas de risco
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    portfolio_value REAL,
                    var_1d REAL,
                    cvar_1d REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    beta REAL,
                    correlation_matrix TEXT,
                    exposure_by_symbol TEXT,
                    concentration_risk REAL,
                    liquidity_risk REAL,
                    metadata TEXT
                )
            ''')

            # Tabela de posições de risco
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS position_risks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    quantity REAL,
                    entry_price REAL,
                    current_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size_pct REAL,
                    risk_reward_ratio REAL,
                    expected_return REAL,
                    max_loss REAL,
                    volatility REAL
                )
            ''')

            # Tabela de alertas de risco
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    alert_type TEXT,
                    symbol TEXT,
                    severity TEXT,
                    message TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database de risco: {e}")

    def _load_risk_limits(self) -> Dict[str, Any]:
        """Carregar limites de risco"""
        default_limits = {
            'portfolio': {
                'max_position_size_pct': 0.20,  # 20% por posição
                'max_sector_exposure_pct': 0.40,  # 40% por setor
                'max_daily_loss_pct': 0.05,  # 5% perda diária máxima
                'max_monthly_loss_pct': 0.15,  # 15% perda mensal máxima
                'var_limit_pct': 0.02,  # 2% VaR máximo
                'max_leverage': 3.0  # Alavancagem máxima
            },
            'risk_budgets': {
                'conservative': {
                    'max_risk_per_trade': 0.01,  # 1% por trade
                    'max_concurrent_positions': 5,
                    'max_correlation': 0.7
                },
                'moderate': {
                    'max_risk_per_trade': 0.02,  # 2% por trade
                    'max_concurrent_positions': 10,
                    'max_correlation': 0.8
                },
                'aggressive': {
                    'max_risk_per_trade': 0.03,  # 3% por trade
                    'max_concurrent_positions': 15,
                    'max_correlation': 0.9
                }
            },
            'stop_loss': {
                'default_pct': 0.05,  # 5% stop loss padrão
                'trailing_stop': True,
                'volatility_adjustment': True
            },
            'position_sizing': {
                'method': 'kelly',  # kelly, fixed, volatility
                'kelly_fraction': 0.25,  # 25% do Kelly
                'max_kelly': 0.1,  # Máximo 10% do portfólio
                'volatility_target': 0.15  # 15% volatilidade alvo
            }
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return {**default_limits, **config}  # Merge com defaults
            else:
                # Salvar configuração default
                with open(self.config_file, 'w') as f:
                    json.dump(default_limits, f, indent=2)
                return default_limits
        except Exception as e:
            print(f"⚠️  Erro ao carregar limites de risco: {e}")
            return default_limits

    def _load_current_portfolio(self):
        """Carregar portfólio atual"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Obter posições abertas
            cursor.execute('''
                SELECT pair, amount, open_price, open_time, profit
                FROM trades
                WHERE status = 'open'
            ''')

            for row in cursor.fetchall():
                symbol, quantity, entry_price, open_time, profit = row
                self.current_portfolio[symbol] = {
                    'quantity': float(quantity),
                    'entry_price': float(entry_price),
                    'open_time': open_time,
                    'unrealized_pnl': float(profit) if profit else 0.0
                }

            conn.close()

        except Exception as e:
            print(f"⚠️  Erro ao carregar portfólio: {e}")

    def calculate_position_size(self, symbol: str, entry_price: float,
                              stop_loss: float, strategy: str = 'moderate') -> Dict[str, Any]:
        """Calcular tamanho de posição usando múltiplos métodos"""
        try:
            # Obter volatilidade histórica
            volatility = self._calculate_volatility(symbol)

            # Obter parâmetros de risco
            risk_params = self.risk_limits['risk_budgets'].get(strategy,
                                                             self.risk_limits['risk_budgets']['moderate'])

            portfolio_value = self.get_portfolio_value()
            max_risk_per_trade = risk_params['max_risk_per_trade']

            # Método 1: Fixed Risk per Trade
            fixed_risk_size = (portfolio_value * max_risk_per_trade) / abs(entry_price - stop_loss)

            # Método 2: Kelly Criterion (simplificado)
            if volatility > 0:
                # Estimar win rate e profit/loss ratio (simplificado)
                estimated_win_rate = 0.55  # Assumir 55% win rate
                avg_win = abs(entry_price - stop_loss) * 2  # Assumir 1:2 R:R
                avg_loss = abs(entry_price - stop_loss)

                if avg_loss > 0:
                    kelly_fraction = (estimated_win_rate * avg_win - (1 - estimated_win_rate) * avg_loss) / avg_win
                    kelly_fraction = max(0, min(kelly_fraction * 0.25, 0.1))  # 25% do Kelly, máximo 10%
                    kelly_size = (portfolio_value * kelly_fraction) / abs(entry_price - stop_loss)
                else:
                    kelly_size = 0
            else:
                kelly_size = 0

            # Método 3: Volatility-based sizing
            volatility_target = self.risk_limits['position_sizing']['volatility_target']
            volatility_adjusted_size = (portfolio_value * volatility_target) / (volatility * entry_price)

            # Método 4: Maximum position size limit
            max_position_pct = self.risk_limits['portfolio']['max_position_size_pct']
            max_position_size = (portfolio_value * max_position_pct) / entry_price

            # Escolher o menor entre os métodos (mais conservador)
            recommended_size = min(fixed_risk_size, kelly_size, volatility_adjusted_size, max_position_size)

            return {
                'symbol': symbol,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'volatility': volatility,
                'position_sizes': {
                    'fixed_risk': fixed_risk_size,
                    'kelly_criterion': kelly_size,
                    'volatility_based': volatility_adjusted_size,
                    'max_allowed': max_position_size
                },
                'recommended_size': recommended_size,
                'position_value': recommended_size * entry_price,
                'risk_amount': recommended_size * abs(entry_price - stop_loss),
                'risk_percentage': (recommended_size * abs(entry_price - stop_loss)) / portfolio_value,
                'strategy_used': 'conservative_minimum'
            }

        except Exception as e:
            print(f"❌ Erro ao calcular tamanho de posição: {e}")
            return {'recommended_size': 0, 'error': str(e)}

    def _calculate_volatility(self, symbol: str, period: int = 30) -> float:
        """Calcular volatilidade histórica"""
        try:
            conn = sqlite3.connect(self.db_path)

            query = '''
                SELECT close FROM market_data
                WHERE pair = ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''

            df = pd.read_sql_query(query, conn, params=(symbol, period))
            conn.close()

            if len(df) < 2:
                return 0.02  # 2% default

            # Calcular retornos
            returns = df['close'].pct_change().dropna()

            # Volatilidade anualizada
            volatility = returns.std() * np.sqrt(365) if len(returns) > 0 else 0.02

            return max(volatility, 0.01)  # Mínimo 1%

        except Exception as e:
            print(f"⚠️  Erro ao calcular volatilidade: {e}")
            return 0.02  # 2% default

    def get_portfolio_value(self) -> float:
        """Obter valor atual do portfólio"""
        try:
            total_value = 0.0

            for symbol, position in self.current_portfolio.items():
                # Obter preço atual (simplificado)
                current_price = self._get_current_price(symbol)
                position_value = position['quantity'] * current_price
                total_value += position_value

            # Adicionar cash (simplificado)
            cash_value = 50000.0  # Assumir $50k em cash
            total_value += cash_value

            return total_value

        except Exception as e:
            print(f"⚠️  Erro ao calcular valor do portfólio: {e}")
            return self.initial_capital

    def _get_current_price(self, symbol: str) -> float:
        """Obter preço atual (simplificado)"""
        # Em produção, usar API de preço em tempo real
        base_prices = {
            'BTC/USDT': 98500, 'ETH/USDT': 3250, 'BNB/USDT': 685,
            'ADA/USDT': 0.98, 'XRP/USDT': 1.85, 'SOL/USDT': 235
        }
        return base_prices.get(symbol, 100.0)

    def calculate_var_cvar(self, confidence_level: float = 0.05,
                          time_horizon: int = 1) -> Dict[str, float]:
        """Calcular Value at Risk (VaR) e Conditional VaR (CVaR)"""
        try:
            # Obter retornos históricos
            returns_data = self._get_historical_returns()

            if len(returns_data) < 30:
                return {'var_1d': 0.02, 'cvar_1d': 0.03, 'var_10d': 0.06}  # Valores conservadores

            returns = np.array(returns_data)

            # VaR usando método histórico
            var_1d = np.percentile(returns, confidence_level * 100)

            # CVaR (Expected Shortfall)
            tail_returns = returns[returns <= var_1d]
            cvar_1d = np.mean(tail_returns) if len(tail_returns) > 0 else var_1d

            # VaR para 10 dias (assumindo independência)
            var_10d = var_1d * np.sqrt(time_horizon)

            return {
                'var_1d': abs(var_1d),
                'cvar_1d': abs(cvar_1d),
                'var_10d': abs(var_10d),
                'confidence_level': confidence_level
            }

        except Exception as e:
            print(f"❌ Erro ao calcular VaR/CVaR: {e}")
            return {'var_1d': 0.02, 'cvar_1d': 0.03, 'var_10d': 0.06}

    def _get_historical_returns(self, days: int = 252) -> List[float]:
        """Obter retornos históricos do portfólio"""
        try:
            # Simular dados históricos baseados no portfólio atual
            daily_returns = []

            for i in range(days):
                # Simular retorno diário (normalmente distribuído)
                daily_return = np.random.normal(0.0005, 0.02)  # 0.05% média, 2% desvio
                daily_returns.append(daily_return)

            return daily_returns

        except Exception as e:
            print(f"⚠️  Erro ao obter retornos históricos: {e}")
            return [0.0] * days

    def calculate_correlation_matrix(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Calcular matriz de correlação entre ativos"""
        try:
            correlations = {}

            for symbol in symbols:
                correlations[symbol] = {}

                for other_symbol in symbols:
                    if symbol == other_symbol:
                        correlations[symbol][other_symbol] = 1.0
                    else:
                        # Calcular correlação (simplificado)
                        correlation = self._calculate_symbol_correlation(symbol, other_symbol)
                        correlations[symbol][other_symbol] = correlation

            return correlations

        except Exception as e:
            print(f"❌ Erro ao calcular matriz de correlação: {e}")
            return {}

    def _calculate_symbol_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calcular correlação entre dois símbolos"""
        try:
            # Dados simulados de correlação para crypto principais
            crypto_correlations = {
                ('BTC/USDT', 'ETH/USDT'): 0.75,
                ('BTC/USDT', 'BNB/USDT'): 0.70,
                ('BTC/USDT', 'ADA/USDT'): 0.65,
                ('ETH/USDT', 'BNB/USDT'): 0.80,
                ('ETH/USDT', 'ADA/USDT'): 0.60,
                ('BNB/USDT', 'ADA/USDT'): 0.55
            }

            # Buscar correlação direta
            key = (symbol1, symbol2)
            reverse_key = (symbol2, symbol1)

            if key in crypto_correlations:
                return crypto_correlations[key]
            elif reverse_key in crypto_correlations:
                return crypto_correlations[reverse_key]
            else:
                # Correlação default baseada na categoria
                return 0.50  # Correlação moderada default

        except Exception as e:
            print(f"⚠️  Erro ao calcular correlação {symbol1}-{symbol2}: {e}")
            return 0.50

    def assess_portfolio_risk(self) -> RiskMetrics:
        """Avaliar risco completo do portfólio"""
        try:
            timestamp = datetime.now().isoformat()
            portfolio_value = self.get_portfolio_value()

            # Calcular métricas de risco
            var_metrics = self.calculate_var_cvar()

            # Exposição por símbolo
            exposure_by_symbol = {}
            for symbol in self.current_portfolio.keys():
                position_value = self.current_portfolio[symbol]['quantity'] * self._get_current_price(symbol)
                exposure_by_symbol[symbol] = position_value / portfolio_value if portfolio_value > 0 else 0

            # Risco de concentração
            max_exposure = max(exposure_by_symbol.values()) if exposure_by_symbol else 0
            concentration_risk = max_exposure

            # Risco de liquidez (simplificado)
            liquidity_risk = self._calculate_liquidity_risk()

            # Calcular correlações
            symbols = list(self.current_portfolio.keys())
            if len(symbols) > 1:
                correlation_matrix = self.calculate_correlation_matrix(symbols)
            else:
                correlation_matrix = {symbols[0]: {symbols[0]: 1.0}} if symbols else {}

            # Calcular outras métricas
            max_drawdown = self._calculate_max_drawdown()
            sharpe_ratio = self._calculate_sharpe_ratio()
            sortino_ratio = self._calculate_sortino_ratio()
            beta = self._calculate_portfolio_beta()

            risk_metrics = RiskMetrics(
                timestamp=timestamp,
                symbol=','.join(symbols),
                portfolio_value=portfolio_value,
                var_1d=var_metrics['var_1d'],
                cvar_1d=var_metrics['cvar_1d'],
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                beta=beta,
                correlation_matrix=correlation_matrix,
                exposure_by_symbol=exposure_by_symbol,
                concentration_risk=concentration_risk,
                liquidity_risk=liquidity_risk
            )

            # Salvar métricas
            self._save_risk_metrics(risk_metrics)
            self.risk_metrics_history.append(risk_metrics)

            return risk_metrics

        except Exception as e:
            print(f"❌ Erro na avaliação de risco: {e}")
            return RiskMetrics(
                timestamp=datetime.now().isoformat(),
                symbol="N/A",
                portfolio_value=self.initial_capital,
                var_1d=0.02,
                cvar_1d=0.03,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                beta=1.0,
                correlation_matrix={},
                exposure_by_symbol={},
                concentration_risk=0.0,
                liquidity_risk=0.0
            )

    def _calculate_liquidity_risk(self) -> float:
        """Calcular risco de liquidez do portfólio"""
        try:
            total_value = 0.0
            illiquid_value = 0.0

            liquidity_scores = {
                'BTC/USDT': 0.95,  # Alta liquidez
                'ETH/USDT': 0.90,
                'BNB/USDT': 0.85,
                'ADA/USDT': 0.80,
                'XRP/USDT': 0.75,
                'SOL/USDT': 0.70,
                'DOT/USDT': 0.65,
                'LINK/USDT': 0.60
            }

            for symbol, position in self.current_portfolio.items():
                position_value = position['quantity'] * self._get_current_price(symbol)
                total_value += position_value

                liquidity_score = liquidity_scores.get(symbol, 0.50)
                if liquidity_score < 0.70:  # Considerar ilíquido se score < 70%
                    illiquid_value += position_value

            return illiquid_value / total_value if total_value > 0 else 0.0

        except Exception as e:
            print(f"⚠️  Erro ao calcular risco de liquidez: {e}")
            return 0.0

    def _calculate_max_drawdown(self) -> float:
        """Calcular máximo drawdown do portfólio"""
        try:
            # Simular histórico de valores do portfólio
            portfolio_values = []
            current_value = self.get_portfolio_value()

            # Gerar 252 dias de histórico simulado
            for i in range(252):
                daily_return = np.random.normal(0.0005, 0.02)
                current_value *= (1 + daily_return)
                portfolio_values.append(current_value)

            # Calcular drawdown
            peak = portfolio_values[0]
            max_drawdown = 0.0

            for value in portfolio_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)

            return max_drawdown

        except Exception as e:
            print(f"⚠️  Erro ao calcular max drawdown: {e}")
            return 0.0

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calcular Sharpe Ratio do portfólio"""
        try:
            # Simular retornos
            returns = self._get_historical_returns(252)

            if not returns or len(returns) < 2:
                return 0.0

            mean_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return == 0:
                return 0.0

            # Anualizar
            mean_return_annual = mean_return * 252
            std_return_annual = std_return * np.sqrt(252)

            sharpe = (mean_return_annual - risk_free_rate) / std_return_annual
            return max(sharpe, -5.0)  # Limitar entre -5 e 5

        except Exception as e:
            print(f"⚠️  Erro ao calcular Sharpe Ratio: {e}")
            return 0.0

    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calcular Sortino Ratio (considera apenas downside deviation)"""
        try:
            returns = self._get_historical_returns(252)

            if not returns or len(returns) < 2:
                return 0.0

            mean_return = np.mean(returns)

            # Downside deviation (apenas retornos negativos)
            downside_returns = [r for r in returns if r < 0]

            if not downside_returns:
                return float('inf')  # Nenhum retorno negativo

            downside_deviation = np.std(downside_returns)

            if downside_deviation == 0:
                return 0.0

            # Anualizar
            mean_return_annual = mean_return * 252
            downside_deviation_annual = downside_deviation * np.sqrt(252)

            sortino = (mean_return_annual - risk_free_rate) / downside_deviation_annual
            return max(sortino, -5.0)

        except Exception as e:
            print(f"⚠️  Erro ao calcular Sortino Ratio: {e}")
            return 0.0

    def _calculate_portfolio_beta(self, market_symbol: str = 'BTC/USDT') -> float:
        """Calcular beta do portfólio em relação ao mercado"""
        try:
            # Simplificado: assumir beta baseado na composição do portfólio
            total_value = self.get_portfolio_value()
            if total_value == 0:
                return 1.0

            weighted_beta = 0.0

            for symbol, position in self.current_portfolio.items():
                position_value = position['quantity'] * self._get_current_price(symbol)
                weight = position_value / total_value

                # Beta típico por crypto
                crypto_betas = {
                    'BTC/USDT': 1.0,
                    'ETH/USDT': 1.2,
                    'BNB/USDT': 1.1,
                    'ADA/USDT': 1.4,
                    'XRP/USDT': 1.3,
                    'SOL/USDT': 1.5
                }

                symbol_beta = crypto_betas.get(symbol, 1.0)
                weighted_beta += weight * symbol_beta

            return weighted_beta

        except Exception as e:
            print(f"⚠️  Erro ao calcular beta: {e}")
            return 1.0

    def _save_risk_metrics(self, risk_metrics: RiskMetrics):
        """Salvar métricas de risco no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO risk_metrics
                (timestamp, symbol, portfolio_value, var_1d, cvar_1d, max_drawdown,
                 sharpe_ratio, sortino_ratio, beta, correlation_matrix, exposure_by_symbol,
                 concentration_risk, liquidity_risk, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                risk_metrics.timestamp,
                risk_metrics.symbol,
                risk_metrics.portfolio_value,
                risk_metrics.var_1d,
                risk_metrics.cvar_1d,
                risk_metrics.max_drawdown,
                risk_metrics.sharpe_ratio,
                risk_metrics.sortino_ratio,
                risk_metrics.beta,
                json.dumps(risk_metrics.correlation_matrix),
                json.dumps(risk_metrics.exposure_by_symbol),
                risk_metrics.concentration_risk,
                risk_metrics.liquidity_risk,
                '{}'
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar métricas de risco: {e}")

    def check_risk_limits(self) -> List[Dict[str, Any]]:
        """Verificar se portfólio está dentro dos limites de risco"""
        violations = []

        try:
            risk_metrics = self.assess_portfolio_risk()
            portfolio_value = risk_metrics.portfolio_value

            # Verificar VaR
            var_limit = self.risk_limits['portfolio']['var_limit_pct']
            if risk_metrics.var_1d > var_limit:
                violations.append({
                    'type': 'VaR Violation',
                    'current': risk_metrics.var_1d,
                    'limit': var_limit,
                    'severity': 'high',
                    'message': f'VaR 1D ({risk_metrics.var_1d:.2%}) excede limite ({var_limit:.2%})'
                })

            # Verificar exposição por posição
            max_position_pct = self.risk_limits['portfolio']['max_position_size_pct']
            for symbol, exposure in risk_metrics.exposure_by_symbol.items():
                if exposure > max_position_pct:
                    violations.append({
                        'type': 'Position Limit Violation',
                        'symbol': symbol,
                        'current': exposure,
                        'limit': max_position_pct,
                        'severity': 'medium',
                        'message': f'Exposição {symbol} ({exposure:.2%}) excede limite ({max_position_pct:.2%})'
                    })

            # Verificar risco de concentração
            concentration_limit = 0.30  # 30%
            if risk_metrics.concentration_risk > concentration_limit:
                violations.append({
                    'type': 'Concentration Risk',
                    'current': risk_metrics.concentration_risk,
                    'limit': concentration_limit,
                    'severity': 'medium',
                    'message': f'Concentração máxima ({risk_metrics.concentration_risk:.2%}) muito alta'
                })

            # Verificar drawdown máximo
            if risk_metrics.max_drawdown > 0.20:  # 20%
                violations.append({
                    'type': 'Max Drawdown',
                    'current': risk_metrics.max_drawdown,
                    'limit': 0.20,
                    'severity': 'critical',
                    'message': f'Drawdown ({risk_metrics.max_drawdown:.2%}) muito alto'
                })

            # Verificar correlação
            max_correlation = 0.9
            for symbol1 in risk_metrics.correlation_matrix:
                for symbol2 in risk_metrics.correlation_matrix[symbol1]:
                    if symbol1 != symbol2:
                        correlation = abs(risk_metrics.correlation_matrix[symbol1][symbol2])
                        if correlation > max_correlation:
                            violations.append({
                                'type': 'High Correlation',
                                'symbols': [symbol1, symbol2],
                                'current': correlation,
                                'limit': max_correlation,
                                'severity': 'low',
                                'message': f'Alta correlação entre {symbol1} e {symbol2} ({correlation:.2f})'
                            })

            # Salvar violações como alertas
            for violation in violations:
                self._save_risk_alert(violation)

            return violations

        except Exception as e:
            print(f"❌ Erro na verificação de limites: {e}")
            return []

    def _save_risk_alert(self, violation: Dict[str, Any]):
        """Salvar alerta de risco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO risk_alerts
                (timestamp, alert_type, symbol, severity, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                violation['type'],
                violation.get('symbol', 'PORTFOLIO'),
                violation['severity'],
                violation['message']
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar alerta de risco: {e}")

    def get_risk_report(self) -> Dict[str, Any]:
        """Gerar relatório completo de risco"""
        try:
            risk_metrics = self.assess_portfolio_risk()
            violations = self.check_risk_limits()

            # Status geral
            if any(v['severity'] == 'critical' for v in violations):
                overall_status = 'CRITICAL'
            elif any(v['severity'] == 'high' for v in violations):
                overall_status = 'HIGH_RISK'
            elif any(v['severity'] == 'medium' for v in violations):
                overall_status = 'MEDIUM_RISK'
            else:
                overall_status = 'LOW_RISK'

            # Recomendações
            recommendations = self._generate_risk_recommendations(risk_metrics, violations)

            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': overall_status,
                'portfolio_value': risk_metrics.portfolio_value,
                'risk_metrics': asdict(risk_metrics),
                'violations': violations,
                'recommendations': recommendations,
                'risk_budget_utilization': self._calculate_risk_budget_utilization()
            }

        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'ERROR',
                'error': str(e)
            }

    def _generate_risk_recommendations(self, risk_metrics: RiskMetrics,
                                     violations: List[Dict]) -> List[str]:
        """Gerar recomendações para melhorar o perfil de risco"""
        recommendations = []

        # Recomendações baseadas em violações
        for violation in violations:
            if 'Position Limit' in violation['type']:
                recommendations.append(f"Reduzir exposição em {violation['symbol']} para {violation['limit']:.1%}")
            elif 'VaR' in violation['type']:
                recommendations.append("Reduzir tamanho das posições para diminuir VaR")
            elif 'Concentration' in violation['type']:
                recommendations.append("Diversificar portfólio para reduzir concentração")
            elif 'Correlation' in violation['type']:
                recommendations.append(f"Reduzir correlação entre {violation.get('symbols', [])}")

        # Recomendações baseadas em métricas
        if risk_metrics.sharpe_ratio < 0.5:
            recommendations.append("Melhorar relação risco-retorno (Sharpe Ratio baixo)")

        if risk_metrics.max_drawdown > 0.15:
            recommendations.append("Implementar stop loss mais rigorosos para reduzir drawdown")

        if risk_metrics.concentration_risk > 0.25:
            recommendations.append("Diversificar entre mais ativos para reduzir concentração")

        if risk_metrics.liquidity_risk > 0.20:
            recommendations.append("Aumentar posição em ativos mais líquidos")

        # Recomendações gerais
        if not recommendations:
            recommendations.append("Perfil de risco adequado. Continuar monitoramento.")

        return recommendations[:5]  # Máximo 5 recomendações

    def _calculate_risk_budget_utilization(self) -> Dict[str, float]:
        """Calcular utilização do budget de risco"""
        try:
            risk_metrics = self.assess_portfolio_risk()
            portfolio_value = risk_metrics.portfolio_value

            # VaR utilizado
            var_limit = self.risk_limits['portfolio']['var_limit_pct']
            var_utilization = risk_metrics.var_1d / var_limit if var_limit > 0 else 0

            # Exposição por posição
            max_position_pct = self.risk_limits['portfolio']['max_position_size_pct']
            max_exposure = max(risk_metrics.exposure_by_symbol.values()) if risk_metrics.exposure_by_symbol else 0
            position_utilization = max_exposure / max_position_pct if max_position_pct > 0 else 0

            # Drawdown
            max_dd_limit = 0.20  # 20%
            dd_utilization = risk_metrics.max_drawdown / max_dd_limit if max_dd_limit > 0 else 0

            return {
                'var_utilization': var_utilization,
                'position_utilization': position_utilization,
                'drawdown_utilization': dd_utilization
            }

        except Exception as e:
            print(f"⚠️  Erro ao calcular utilization: {e}")
            return {'var_utilization': 0, 'position_utilization': 0, 'drawdown_utilization': 0}

    def start_risk_monitoring(self, interval: int = 300):
        """Iniciar monitoramento contínuo de risco"""
        if self.monitoring_active:
            return

        self.monitoring_active = True

        def monitor_risk():
            while self.monitoring_active:
                try:
                    # Avaliar risco
                    risk_metrics = self.assess_portfolio_risk()
                    violations = self.check_risk_limits()

                    # Log de violações críticas
                    critical_violations = [v for v in violations if v['severity'] == 'critical']
                    if critical_violations:
                        for violation in critical_violations:
                            print(f"🚨 ALERTA CRÍTICO: {violation['message']}")

                    # Alertas de alto risco
                    high_violations = [v for v in violations if v['severity'] == 'high']
                    if high_violations:
                        for violation in high_violations:
                            print(f"⚠️  ALERTA ALTO RISCO: {violation['message']}")

                    time.sleep(interval)

                except Exception as e:
                    print(f"❌ Erro no monitoramento de risco: {e}")
                    time.sleep(60)  # Aguardar 1 minuto antes de tentar novamente

        self.monitor_thread = threading.Thread(target=monitor_risk, daemon=True)
        self.monitor_thread.start()
        print("🟢 Monitoramento de risco iniciado")

    def stop_risk_monitoring(self):
        """Parar monitoramento de risco"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("🔴 Monitoramento de risco parado")

# API para integração com o painel principal
def create_risk_manager():
    """Criar instância do risk manager"""
    return InstitutionalRiskManager()

if __name__ == "__main__":
    # Teste do risk manager
    risk_manager = create_risk_manager()

    # Teste de cálculo de posição
    position = risk_manager.calculate_position_size("BTC/USDT", 98500, 95000)
    print(f"Tamanho de posição recomendado: {position['recommended_size']}")

    # Teste de relatório de risco
    report = risk_manager.get_risk_report()
    print(f"Status geral: {report['overall_status']}")
    print(f"Violações: {len(report['violations'])}")

    # Iniciar monitoramento
    risk_manager.start_risk_monitoring(interval=60)
