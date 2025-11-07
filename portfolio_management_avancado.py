#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Portfolio Management Avançado
Versão: 4.0 - Gestão de Portfólio Institucional
Características: Alocação dinâmica, rebalanceamento, otimização Markowitz, performance attribution
"""

import json
import logging
import math
import os
import sqlite3
import threading
import time
import warnings
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# Bibliotecas de otimização
try:
    from scipy.optimize import minimize
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️  scipy não disponível. Otimização limitada.")

@dataclass
class PortfolioPosition:
    """Posição individual no portfólio"""
    symbol: str
    quantity: float
    current_price: float
    market_value: float
    weight: float  # 0.0 a 1.0
    cost_basis: float
    unrealized_pnl: float
    realized_pnl: float
    return_pct: float
    volatility: float
    beta: float
    sector: str = "crypto"
    last_rebalanced: Optional[str] = None

@dataclass
class PortfolioMetrics:
    """Métricas de performance do portfólio"""
    timestamp: str
    total_value: float
    total_return: float
    annual_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    var_95: float
    cvar_95: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float
    correlation_btc: float
    performance_attribution: Dict[str, float]

class AllocationStrategy(Enum):
    """Estratégias de alocação"""
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP_WEIGHT = "market_cap_weight"
    VOLATILITY_WEIGHT = "volatility_weight"
    RISK_PARITY = "risk_parity"
    BLACK_LITTERMAN = "black_litterman"
    MEAN_VARIANCE = "mean_variance"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    CUSTOM = "custom"

class AdvancedPortfolioManager:
    """Sistema avançado de gestão de portfólio"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db',
                 initial_capital: float = 100000.0):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.portfolio_data_dir = 'portfolio_data'
        self.config_file = 'configs/portfolio_config.yaml'

        # Criar diretórios
        os.makedirs(self.portfolio_data_dir, exist_ok=True)
        os.makedirs('configs', exist_ok=True)

        # Estado do portfólio
        self.positions = {}
        self.cash = initial_capital
        self.total_value = initial_capital
        self.portfolio_history = deque(maxlen=2520)  # 2520 dias (~7 anos)
        self.target_allocation = {}
        self.current_strategy = AllocationStrategy.EQUAL_WEIGHT

        # Configurações
        self.config = self._load_config()

        # Inicializar manager
        self._init_portfolio_manager()

        # Cache de dados
        self.returns_cache = {}
        self.covariance_cache = {}
        self.cache_ttl = 3600  # 1 hora

    def _init_portfolio_manager(self):
        """Inicializar sistema de portfolio management"""
        # Inicializar base de dados
        self._init_database()

        # Carregar posições atuais
        self._load_current_positions()

        # Definir alocação alvo inicial
        if not self.target_allocation:
            self.set_target_allocation(AllocationStrategy.EQUAL_WEIGHT)

        print("📊 Portfolio Manager Avançado inicializado")

    def _init_database(self):
        """Inicializar base de dados de portfólio"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de posições do portfólio
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    quantity REAL,
                    current_price REAL,
                    market_value REAL,
                    weight REAL,
                    cost_basis REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    return_pct REAL,
                    volatility REAL,
                    beta REAL,
                    sector TEXT,
                    metadata TEXT
                )
            ''')

            # Tabela de métricas de portfólio
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    total_value REAL,
                    total_return REAL,
                    annual_return REAL,
                    volatility REAL,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    max_drawdown REAL,
                    calmar_ratio REAL,
                    var_95 REAL,
                    cvar_95 REAL,
                    beta REAL,
                    alpha REAL,
                    tracking_error REAL,
                    information_ratio REAL,
                    correlation_btc REAL,
                    performance_attribution TEXT
                )
            ''')

            # Tabela de rebalanceamentos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_rebalancing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    strategy TEXT,
                    trigger_reason TEXT,
                    old_allocation TEXT,
                    new_allocation TEXT,
                    trades_executed TEXT,
                    cost REAL
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database de portfólio: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações do portfólio"""
        default_config = {
            'rebalancing': {
                'threshold': 0.05,  # 5% desvio para rebalancear
                'frequency': 'monthly',  # daily, weekly, monthly
                'calendar_days': [1, 15],  # Rebalancear nos dias 1 e 15
                'min_trade_size': 100,  # $100 mínimo por trade
                'transaction_cost': 0.001  # 0.1% custo por trade
            },
            'target_allocation': {
                'BTC/USDT': 0.30,
                'ETH/USDT': 0.25,
                'BNB/USDT': 0.15,
                'ADA/USDT': 0.10,
                'SOL/USDT': 0.10,
                'XRP/USDT': 0.05,
                'DOT/USDT': 0.03,
                'LINK/USDT': 0.02
            },
            'risk_limits': {
                'max_single_position': 0.40,  # 40% máximo por posição
                'max_crypto_exposure': 0.95,  # 95% máximo em crypto
                'min_cash_reserve': 0.05,  # 5% mínimo em cash
                'sector_limits': {
                    'layer1': 0.60,
                    'defi': 0.30,
                    'meme': 0.10
                }
            },
            'optimization': {
                'lookback_period': 252,  # 1 ano
                'risk_free_rate': 0.02,
                'target_volatility': 0.20,
                'constraints': {
                    'min_weight': 0.01,
                    'max_weight': 0.40,
                    'sum_weights': 1.0
                }
            },
            'performance': {
                'benchmark': 'BTC/USDT',
                'rebalance_cost': 0.001,
                'tax_loss_harvesting': True
            }
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return {**default_config, **config}
            else:
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração: {e}")
            return default_config

    def _load_current_positions(self):
        """Carregar posições atuais do banco"""
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
                current_price = self._get_current_price(symbol)

                market_value = quantity * current_price
                unrealized_pnl = float(profit) if profit else (current_price - entry_price) * quantity
                cost_basis = quantity * entry_price
                return_pct = (current_price - entry_price) / entry_price

                self.positions[symbol] = PortfolioPosition(
                    symbol=symbol,
                    quantity=float(quantity),
                    current_price=current_price,
                    market_value=market_value,
                    weight=0.0,  # Será calculado
                    cost_basis=cost_basis,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=0.0,
                    return_pct=return_pct,
                    volatility=self._calculate_volatility(symbol),
                    beta=self._get_beta(symbol),
                    sector=self._get_sector(symbol)
                )

            # Calcular valor total
            self._update_portfolio_value()

            conn.close()

        except Exception as e:
            print(f"⚠️  Erro ao carregar posições: {e}")

    def _get_current_price(self, symbol: str) -> float:
        """Obter preço atual"""
        # Preços aproximados (em produção, usar API real)
        prices = {
            'BTC/USDT': 98500, 'ETH/USDT': 3250, 'BNB/USDT': 685,
            'ADA/USDT': 0.98, 'XRP/USDT': 1.85, 'SOL/USDT': 235,
            'DOT/USDT': 8.75, 'LINK/USDT': 24.50
        }
        return prices.get(symbol, 100.0)

    def _calculate_volatility(self, symbol: str, period: int = 30) -> float:
        """Calcular volatilidade histórica"""
        try:
            # Simular volatilidade baseada no símbolo
            vol_map = {
                'BTC/USDT': 0.65, 'ETH/USDT': 0.75, 'BNB/USDT': 0.80,
                'ADA/USDT': 0.90, 'XRP/USDT': 0.85, 'SOL/USDT': 0.95,
                'DOT/USDT': 0.88, 'LINK/USDT': 0.82
            }
            return vol_map.get(symbol, 0.80)
        except Exception:
            return 0.80

    def _get_beta(self, symbol: str) -> float:
        """Obter beta em relação ao BTC"""
        # Betas típicos em relação ao BTC
        beta_map = {
            'BTC/USDT': 1.0, 'ETH/USDT': 1.2, 'BNB/USDT': 1.1,
            'ADA/USDT': 1.4, 'XRP/USDT': 1.3, 'SOL/USDT': 1.5,
            'DOT/USDT': 1.35, 'LINK/USDT': 1.25
        }
        return beta_map.get(symbol, 1.0)

    def _get_sector(self, symbol: str) -> str:
        """Obter setor do ativo"""
        sectors = {
            'BTC/USDT': 'store_of_value',
            'ETH/USDT': 'smart_contracts',
            'BNB/USDT': 'exchange',
            'ADA/USDT': 'layer1',
            'XRP/USDT': 'payments',
            'SOL/USDT': 'layer1',
            'DOT/USDT': 'layer1',
            'LINK/USDT': 'oracle'
        }
        return sectors.get(symbol, 'crypto')

    def _update_portfolio_value(self):
        """Atualizar valor total do portfólio"""
        total_value = self.cash
        for position in self.positions.values():
            total_value += position.market_value

        # Atualizar weights
        for position in self.positions.values():
            position.weight = position.market_value / total_value if total_value > 0 else 0

        self.total_value = total_value

        # Adicionar ao histórico
        self.portfolio_history.append({
            'timestamp': datetime.now().isoformat(),
            'total_value': total_value,
            'positions': {k: asdict(v) for k, v in self.positions.items()},
            'cash': self.cash
        })

    def set_target_allocation(self, strategy: AllocationStrategy,
                            custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Definir alocação alvo"""
        try:
            self.current_strategy = strategy

            if strategy == AllocationStrategy.EQUAL_WEIGHT:
                symbols = list(self.positions.keys()) if self.positions else list(self.config['target_allocation'].keys())
                weight = 1.0 / len(symbols)
                self.target_allocation = {symbol: weight for symbol in symbols}

            elif strategy == AllocationStrategy.MARKET_CAP_WEIGHT:
                # Usar pesos configurados (proxy para market cap)
                self.target_allocation = self.config['target_allocation'].copy()

            elif strategy == AllocationStrategy.VOLATILITY_WEIGHT:
                self.target_allocation = self._calculate_volatility_weights()

            elif strategy == AllocationStrategy.RISK_PARITY:
                self.target_allocation = self._calculate_risk_parity_weights()

            elif strategy == AllocationStrategy.MEAN_VARIANCE:
                self.target_allocation = self._calculate_mean_variance_weights()

            elif strategy == AllocationStrategy.MINIMUM_VARIANCE:
                self.target_allocation = self._calculate_minimum_variance_weights()

            elif strategy == AllocationStrategy.MAXIMUM_SHARPE:
                self.target_allocation = self._calculate_maximum_sharpe_weights()

            elif strategy == AllocationStrategy.CUSTOM and custom_weights:
                self.target_allocation = custom_weights.copy()

            else:
                # Default para equal weight
                symbols = list(self.positions.keys()) if self.positions else ['BTC/USDT']
                weight = 1.0 / len(symbols)
                self.target_allocation = {symbol: weight for symbol in symbols}

            # Normalizar para somar 1.0
            total_weight = sum(self.target_allocation.values())
            if total_weight > 0:
                self.target_allocation = {k: v / total_weight for k, v in self.target_allocation.items()}

            return self.target_allocation.copy()

        except Exception as e:
            print(f"❌ Erro ao definir alocação: {e}")
            return {'BTC/USDT': 1.0}

    def _calculate_volatility_weights(self) -> Dict[str, float]:
        """Calcular pesos baseados na volatilidade (inversa)"""
        try:
            weights = {}
            total_inverse_vol = 0

            for symbol in self.positions.keys():
                vol = self._calculate_volatility(symbol)
                inverse_vol = 1.0 / vol if vol > 0 else 1.0
                weights[symbol] = inverse_vol
                total_inverse_vol += inverse_vol

            # Normalizar
            if total_inverse_vol > 0:
                weights = {k: v / total_inverse_vol for k, v in weights.items()}

            return weights

        except Exception as e:
            print(f"❌ Erro no cálculo de pesos por volatilidade: {e}")
            return {'BTC/USDT': 1.0}

    def _calculate_risk_parity_weights(self) -> Dict[str, float]:
        """Calcular pesos de risk parity (equal risk contribution)"""
        try:
            # Obter volatilidades
            volatilities = {}
            for symbol in self.positions.keys():
                volatilities[symbol] = self._calculate_volatility(symbol)

            # Risk parity simples: peso inversamente proporcional à volatilidade
            total_inverse_vol = sum(1.0 / vol for vol in volatilities.values())
            weights = {}

            for symbol, vol in volatilities.items():
                weights[symbol] = (1.0 / vol) / total_inverse_vol

            return weights

        except Exception as e:
            print(f"❌ Erro no cálculo de risk parity: {e}")
            return self._calculate_volatility_weights()

    def _calculate_mean_variance_weights(self) -> Dict[str, float]:
        """Calcular pesos usando otimização mean-variance"""
        if not SCIPY_AVAILABLE:
            print("⚠️  scipy não disponível, usando equal weight")
            return self._calculate_volatility_weights()

        try:
            symbols = list(self.positions.keys())
            n_assets = len(symbols)

            if n_assets == 0:
                return {'BTC/USDT': 1.0}

            # Obter retornos históricos (simplificado)
            returns_data = self._get_historical_returns_matrix(symbols)

            # Calcular média e covariância
            mean_returns = np.mean(returns_data, axis=0)
            cov_matrix = np.cov(returns_data.T)

            # Função objetivo: maximizar retorno ajustado por risco
            def objective(weights):
                portfolio_return = np.sum(weights * mean_returns)
                portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
                return -(portfolio_return - 0.5 * portfolio_variance)  # Negativo para maximizar

            # Restrições
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Soma = 1
            ]

            # Bounds
            bounds = tuple((0.01, 0.40) for _ in range(n_assets))

            # Chute inicial
            x0 = np.array([1.0 / n_assets] * n_assets)

            # Otimizar
            result = minimize(objective, x0, method='SLSQP',
                            bounds=bounds, constraints=constraints)

            if result.success:
                weights = result.x
                return {symbols[i]: max(0, weights[i]) for i in range(n_assets)}
            else:
                print("⚠️  Otimização mean-variance falhou, usando equal weight")
                return self._calculate_volatility_weights()

        except Exception as e:
            print(f"❌ Erro na otimização mean-variance: {e}")
            return self._calculate_volatility_weights()

    def _calculate_minimum_variance_weights(self) -> Dict[str, float]:
        """Calcular pesos de mínima variância"""
        if not SCIPY_AVAILABLE:
            return self._calculate_volatility_weights()

        try:
            symbols = list(self.positions.keys())
            n_assets = len(symbols)

            # Obter matriz de covariância
            returns_data = self._get_historical_returns_matrix(symbols)
            cov_matrix = np.cov(returns_data.T)

            # Função objetivo: minimizar variância
            def objective(weights):
                return np.dot(weights.T, np.dot(cov_matrix, weights))

            # Restrições e bounds
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
            ]
            bounds = tuple((0.01, 0.40) for _ in range(n_assets))
            x0 = np.array([1.0 / n_assets] * n_assets)

            result = minimize(objective, x0, method='SLSQP',
                            bounds=bounds, constraints=constraints)

            if result.success:
                weights = result.x
                return {symbols[i]: max(0, weights[i]) for i in range(n_assets)}
            else:
                return self._calculate_volatility_weights()

        except Exception as e:
            print(f"❌ Erro na otimização mínima variância: {e}")
            return self._calculate_volatility_weights()

    def _calculate_maximum_sharpe_weights(self) -> Dict[str, float]:
        """Calcular pesos de máximo Sharpe ratio"""
        if not SCIPY_AVAILABLE:
            return self._calculate_volatility_weights()

        try:
            symbols = list(self.positions.keys())
            n_assets = len(symbols)

            # Dados
            returns_data = self._get_historical_returns_matrix(symbols)
            mean_returns = np.mean(returns_data, axis=0)
            cov_matrix = np.cov(returns_data.T)
            risk_free_rate = self.config['optimization']['risk_free_rate']

            # Função objetivo: maximizar Sharpe ratio
            def objective(weights):
                portfolio_return = np.sum(weights * mean_returns)
                portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
                portfolio_std = np.sqrt(portfolio_variance)

                if portfolio_std == 0:
                    return -1000

                sharpe = (portfolio_return - risk_free_rate) / portfolio_std
                return -sharpe  # Negativo para maximizar

            # Restrições e bounds
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
            ]
            bounds = tuple((0.01, 0.40) for _ in range(n_assets))
            x0 = np.array([1.0 / n_assets] * n_assets)

            result = minimize(objective, x0, method='SLSQP',
                            bounds=bounds, constraints=constraints)

            if result.success:
                weights = result.x
                return {symbols[i]: max(0, weights[i]) for i in range(n_assets)}
            else:
                return self._calculate_volatility_weights()

        except Exception as e:
            print(f"❌ Erro na otimização máximo Sharpe: {e}")
            return self._calculate_volatility_weights()

    def _get_historical_returns_matrix(self, symbols: List[str],
                                     period: int = 252) -> np.ndarray:
        """Obter matriz de retornos históricos"""
        try:
            returns_matrix = []

            for symbol in symbols:
                # Simular retornos baseados no símbolo
                base_return = {'BTC/USDT': 0.0008, 'ETH/USDT': 0.001, 'BNB/USDT': 0.0009,
                              'ADA/USDT': 0.0012, 'XRP/USDT': 0.0011, 'SOL/USDT': 0.0013,
                              'DOT/USDT': 0.00115, 'LINK/USDT': 0.00105}.get(symbol, 0.001)

                vol = self._calculate_volatility(symbol)

                # Gerar retornos simulados
                returns = np.random.normal(base_return, vol / np.sqrt(252), period)
                returns_matrix.append(returns)

            return np.array(returns_matrix).T

        except Exception as e:
            print(f"❌ Erro ao obter matriz de retornos: {e}")
            return np.random.normal(0, 0.02, (period, len(symbols)))

    def should_rebalance(self) -> Tuple[bool, str]:
        """Determinar se deve rebalancear"""
        try:
            # Verificar se há posições
            if not self.positions or not self.target_allocation:
                return False, "No positions to rebalance"

            # Calcular desvios
            max_deviation = 0.0
            rebalance_reason = ""

            for symbol, target_weight in self.target_allocation.items():
                current_weight = self.positions.get(symbol, PortfolioPosition(
                    symbol, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ""
                )).weight

                deviation = abs(current_weight - target_weight)
                max_deviation = max(max_deviation, deviation)

            # Verificar threshold
            threshold = self.config['rebalancing']['threshold']
            if max_deviation > threshold:
                rebalance_reason = f"Deviation {max_deviation:.2%} exceeds threshold {threshold:.2%}"
                return True, rebalance_reason

            # Verificar rebalanceamento por calendário
            today = datetime.now()
            calendar_days = self.config['rebalancing']['calendar_days']

            if today.day in calendar_days:
                # Verificar se já foi rebalanceado hoje
                last_rebalance = self._get_last_rebalance_date()
                if not last_rebalance or (today - last_rebalance).days >= 15:
                    return True, "Scheduled rebalancing"

            return False, "Within thresholds"

        except Exception as e:
            print(f"❌ Erro ao verificar rebalanceamento: {e}")
            return False, "Error in rebalance check"

    def _get_last_rebalance_date(self) -> Optional[datetime]:
        """Obter data do último rebalanceamento"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT MAX(timestamp) FROM portfolio_rebalancing
            ''')

            result = cursor.fetchone()[0]
            conn.close()

            if result:
                return datetime.fromisoformat(result)
            return None

        except Exception:
            return None

    def rebalance_portfolio(self) -> Dict[str, Any]:
        """Executar rebalanceamento do portfólio"""
        try:
            should_rebalance, reason = self.should_rebalance()

            if not should_rebalance:
                return {'success': False, 'reason': reason}

            print(f"🔄 Iniciando rebalanceamento: {reason}")

            # Calcular trades necessários
            trades = self._calculate_rebalance_trades()

            if not trades:
                return {'success': False, 'reason': 'No trades needed'}

            # Executar trades (simulado)
            executed_trades = self._execute_rebalance_trades(trades)

            # Calcular custo
            total_cost = sum(trade['cost'] for trade in executed_trades)

            # Salvar rebalanceamento
            self._save_rebalancing(reason, trades, executed_trades, total_cost)

            # Atualizar posições
            self._update_positions_from_trades(executed_trades)

            result = {
                'success': True,
                'reason': reason,
                'trades_planned': len(trades),
                'trades_executed': len(executed_trades),
                'total_cost': total_cost,
                'new_weights': {symbol: self.positions.get(symbol, PortfolioPosition(symbol, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "")).weight
                              for symbol in self.target_allocation.keys()}
            }

            print(f"✅ Rebalanceamento concluído: {len(executed_trades)} trades, custo ${total_cost:.2f}")
            return result

        except Exception as e:
            print(f"❌ Erro no rebalanceamento: {e}")
            return {'success': False, 'reason': str(e)}

    def _calculate_rebalance_trades(self) -> List[Dict[str, Any]]:
        """Calcular trades necessários para rebalanceamento"""
        try:
            trades = []

            for symbol, target_weight in self.target_allocation.items():
                current_position = self.positions.get(symbol)
                current_weight = current_position.weight if current_position else 0

                # Calcular diferença
                weight_diff = target_weight - current_weight
                value_diff = weight_diff * self.total_value

                # Verificar se é significativa
                min_trade_size = self.config['rebalancing']['min_trade_size']
                if abs(value_diff) < min_trade_size:
                    continue

                # Determinar ação
                current_price = self._get_current_price(symbol)
                quantity_diff = value_diff / current_price

                if quantity_diff > 0:
                    action = 'buy'
                else:
                    action = 'sell'
                    quantity_diff = abs(quantity_diff)

                # Calcular custo
                transaction_cost_pct = self.config['rebalancing']['transaction_cost']
                cost = abs(value_diff) * transaction_cost_pct

                trades.append({
                    'symbol': symbol,
                    'action': action,
                    'quantity': quantity_diff,
                    'price': current_price,
                    'value': abs(value_diff),
                    'cost': cost
                })

            return trades

        except Exception as e:
            print(f"❌ Erro ao calcular trades: {e}")
            return []

    def _execute_rebalance_trades(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executar trades de rebalanceamento (simulado)"""
        try:
            executed_trades = []

            for trade in trades:
                symbol = trade['symbol']
                action = trade['action']
                quantity = trade['quantity']
                price = trade['price']

                # Simular execução
                if action == 'buy':
                    if self.cash >= trade['value'] + trade['cost']:
                        self.cash -= (trade['value'] + trade['cost'])

                        if symbol in self.positions:
                            pos = self.positions[symbol]
                            old_quantity = pos.quantity
                            pos.quantity += quantity
                            pos.cost_basis = (pos.cost_basis * old_quantity + quantity * price) / pos.quantity
                        else:
                            self.positions[symbol] = PortfolioPosition(
                                symbol=symbol,
                                quantity=quantity,
                                current_price=price,
                                market_value=quantity * price,
                                weight=0.0,
                                cost_basis=quantity * price,
                                unrealized_pnl=0.0,
                                realized_pnl=0.0,
                                return_pct=0.0,
                                volatility=self._calculate_volatility(symbol),
                                beta=self._get_beta(symbol),
                                sector=self._get_sector(symbol)
                            )

                        executed_trades.append(trade.copy())

                elif action == 'sell':
                    if symbol in self.positions:
                        pos = self.positions[symbol]
                        sell_quantity = min(quantity, pos.quantity)

                        if sell_quantity > 0:
                            # Atualizar posição
                            pos.quantity -= sell_quantity
                            proceeds = sell_quantity * price
                            self.cash += (proceeds - trade['cost'])

                            # Calcular P&L realizado
                            cost_sold = sell_quantity * pos.cost_basis
                            realized_pnl = proceeds - cost_sold
                            pos.realized_pnl += realized_pnl

                            # Remover posição se quantidade = 0
                            if pos.quantity <= 0:
                                del self.positions[symbol]

                            trade['quantity'] = sell_quantity
                            executed_trades.append(trade.copy())

            # Atualizar valor do portfólio
            self._update_portfolio_value()

            return executed_trades

        except Exception as e:
            print(f"❌ Erro ao executar trades: {e}")
            return []

    def _update_positions_from_trades(self, trades: List[Dict[str, Any]]):
        """Atualizar posições após trades"""
        for trade in trades:
            symbol = trade['symbol']
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.current_price = trade['price']
                pos.market_value = pos.quantity * pos.price
                pos.unrealized_pnl = pos.market_value - pos.cost_basis
                pos.return_pct = pos.unrealized_pnl / pos.cost_basis if pos.cost_basis > 0 else 0

        self._update_portfolio_value()

    def _save_rebalancing(self, reason: str, planned_trades: List[Dict],
                         executed_trades: List[Dict], cost: float):
        """Salvar registro de rebalanceamento"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO portfolio_rebalancing
                (timestamp, strategy, trigger_reason, old_allocation,
                 new_allocation, trades_executed, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                self.current_strategy.value,
                reason,
                json.dumps({symbol: pos.weight for symbol, pos in self.positions.items()}),
                json.dumps(self.target_allocation),
                json.dumps(executed_trades),
                cost
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar rebalanceamento: {e}")

    def calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calcular métricas completas do portfólio"""
        try:
            timestamp = datetime.now().isoformat()

            # Métricas básicas
            total_value = self.total_value
            total_return = (total_value - self.initial_capital) / self.initial_capital

            # Calcular retornos históricos do portfólio
            portfolio_returns = self._get_portfolio_returns()

            if len(portfolio_returns) < 2:
                return self._get_default_metrics(timestamp, total_value)

            # Métricas de risco e retorno
            annual_return = np.mean(portfolio_returns) * 252
            volatility = np.std(portfolio_returns) * np.sqrt(252)
            risk_free_rate = self.config['optimization']['risk_free_rate']

            # Sharpe ratio
            sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Sortino ratio
            downside_returns = [r for r in portfolio_returns if r < 0]
            downside_std = np.std(downside_returns) * np.sqrt(252) if downside_returns else volatility
            sortino_ratio = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0

            # Max drawdown
            max_drawdown = self._calculate_max_drawdown()

            # Calmar ratio
            calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

            # VaR e CVaR
            var_95 = np.percentile(portfolio_returns, 5)
            cvar_95 = np.mean([r for r in portfolio_returns if r <= var_95])

            # Beta e Alpha
            btc_returns = self._get_btc_returns()
            beta, alpha = self._calculate_beta_alpha(portfolio_returns, btc_returns)

            # Tracking error e Information ratio
            tracking_error = np.std([p - b for p, b in zip(portfolio_returns, btc_returns)])
            information_ratio = (annual_return - np.mean(btc_returns) * 252) / tracking_error if tracking_error > 0 else 0

            # Correlação com BTC
            correlation_btc = np.corrcoef(portfolio_returns, btc_returns)[0, 1] if len(btc_returns) == len(portfolio_returns) else 0

            # Performance attribution
            performance_attribution = self._calculate_performance_attribution()

            metrics = PortfolioMetrics(
                timestamp=timestamp,
                total_value=total_value,
                total_return=total_return,
                annual_return=annual_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                calmar_ratio=calmar_ratio,
                var_95=var_95,
                cvar_95=cvar_95,
                beta=beta,
                alpha=alpha,
                tracking_error=tracking_error,
                information_ratio=information_ratio,
                correlation_btc=correlation_btc,
                performance_attribution=performance_attribution
            )

            # Salvar métricas
            self._save_portfolio_metrics(metrics)

            return metrics

        except Exception as e:
            print(f"❌ Erro ao calcular métricas: {e}")
            return self._get_default_metrics(datetime.now().isoformat(), self.total_value)

    def _get_portfolio_returns(self, period: int = 252) -> List[float]:
        """Obter retornos históricos do portfólio"""
        try:
            if len(self.portfolio_history) < 2:
                return []

            returns = []
            values = [entry['total_value'] for entry in list(self.portfolio_history)[-period-1:]]

            for i in range(1, len(values)):
                if values[i-1] > 0:
                    ret = (values[i] - values[i-1]) / values[i-1]
                    returns.append(ret)

            return returns

        except Exception as e:
            print(f"⚠️  Erro ao obter retornos do portfólio: {e}")
            return []

    def _get_btc_returns(self, period: int = 252) -> List[float]:
        """Obter retornos do BTC para benchmark"""
        try:
            # Simular retornos do BTC
            btc_returns = []
            for i in range(period):
                ret = np.random.normal(0.0008, 0.65 / np.sqrt(252))
                btc_returns.append(ret)
            return btc_returns
        except Exception:
            return []

    def _calculate_beta_alpha(self, portfolio_returns: List[float],
                            benchmark_returns: List[float]) -> Tuple[float, float]:
        """Calcular beta e alpha do portfólio"""
        try:
            if len(portfolio_returns) < 10 or len(benchmark_returns) < 10:
                return 1.0, 0.0

            # Alinhar tamanhos
            min_len = min(len(portfolio_returns), len(benchmark_returns))
            p_returns = portfolio_returns[-min_len:]
            b_returns = benchmark_returns[-min_len:]

            # Calcular beta
            covariance = np.cov(p_returns, b_returns)[0, 1]
            benchmark_variance = np.var(b_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0

            # Calcular alpha
            portfolio_mean = np.mean(p_returns)
            benchmark_mean = np.mean(b_returns)
            risk_free_rate = self.config['optimization']['risk_free_rate'] / 252
            alpha = portfolio_mean - (risk_free_rate + beta * (benchmark_mean - risk_free_rate))

            return beta, alpha

        except Exception as e:
            print(f"⚠️  Erro ao calcular beta/alpha: {e}")
            return 1.0, 0.0

    def _calculate_performance_attribution(self) -> Dict[str, float]:
        """Calcular atribuição de performance por ativo"""
        try:
            attribution = {}
            total_value = self.total_value

            for symbol, position in self.positions.items():
                # Contribuição para o retorno total
                weight = position.weight
                individual_return = position.return_pct
                contribution = weight * individual_return
                attribution[symbol] = contribution

            return attribution

        except Exception as e:
            print(f"⚠️  Erro na atribuição de performance: {e}")
            return {}

    def _calculate_max_drawdown(self) -> float:
        """Calcular máximo drawdown"""
        try:
            if len(self.portfolio_history) < 2:
                return 0.0

            values = [entry['total_value'] for entry in self.portfolio_history]
            peak = values[0]
            max_dd = 0.0

            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)

            return max_dd

        except Exception as e:
            print(f"⚠️  Erro ao calcular max drawdown: {e}")
            return 0.0

    def _get_default_metrics(self, timestamp: str, total_value: float) -> PortfolioMetrics:
        """Retornar métricas padrão em caso de erro"""
        return PortfolioMetrics(
            timestamp=timestamp,
            total_value=total_value,
            total_return=0.0,
            annual_return=0.0,
            volatility=0.20,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            calmar_ratio=0.0,
            var_95=0.05,
            cvar_95=0.07,
            beta=1.0,
            alpha=0.0,
            tracking_error=0.0,
            information_ratio=0.0,
            correlation_btc=0.7,
            performance_attribution={}
        )

    def _save_portfolio_metrics(self, metrics: PortfolioMetrics):
        """Salvar métricas de portfólio no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO portfolio_metrics
                (timestamp, total_value, total_return, annual_return, volatility,
                 sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, var_95,
                 cvar_95, beta, alpha, tracking_error, information_ratio,
                 correlation_btc, performance_attribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.total_value,
                metrics.total_return,
                metrics.annual_return,
                metrics.volatility,
                metrics.sharpe_ratio,
                metrics.sortino_ratio,
                metrics.max_drawdown,
                metrics.calmar_ratio,
                metrics.var_95,
                metrics.cvar_95,
                metrics.beta,
                metrics.alpha,
                metrics.tracking_error,
                metrics.information_ratio,
                metrics.correlation_btc,
                json.dumps(metrics.performance_attribution)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar métricas: {e}")

    def get_portfolio_report(self) -> Dict[str, Any]:
        """Gerar relatório completo do portfólio"""
        try:
            metrics = self.calculate_portfolio_metrics()

            # Análise de composição
            composition = {}
            for symbol, position in self.positions.items():
                composition[symbol] = {
                    'weight': position.weight,
                    'value': position.market_value,
                    'return': position.return_pct,
                    'sector': position.sector
                }

            # Alocação vs target
            allocation_analysis = {}
            for symbol, target in self.target_allocation.items():
                current = self.positions.get(symbol)
                current_weight = current.weight if current else 0
                allocation_analysis[symbol] = {
                    'target': target,
                    'current': current_weight,
                    'deviation': current_weight - target,
                    'action': 'buy' if current_weight < target else 'sell' if current_weight > target else 'hold'
                }

            # Recomendações
            recommendations = self._generate_portfolio_recommendations(metrics, composition)

            return {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_value': metrics.total_value,
                    'total_return': metrics.total_return,
                    'annual_return': metrics.annual_return,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'max_drawdown': metrics.max_drawdown,
                    'beta': metrics.beta,
                    'correlation_btc': metrics.correlation_btc
                },
                'metrics': asdict(metrics),
                'composition': composition,
                'target_allocation': self.target_allocation,
                'allocation_analysis': allocation_analysis,
                'recommendations': recommendations,
                'rebalance_status': {
                    'should_rebalance': self.should_rebalance()[0],
                    'reason': self.should_rebalance()[1]
                }
            }

        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return {'error': str(e)}

    def _generate_portfolio_recommendations(self, metrics: PortfolioMetrics,
                                          composition: Dict) -> List[str]:
        """Gerar recomendações para o portfólio"""
        recommendations = []

        # Recomendações baseadas em métricas
        if metrics.sharpe_ratio < 0.5:
            recommendations.append("Considerar otimização de risco para melhorar Sharpe ratio")

        if metrics.max_drawdown > 0.20:
            recommendations.append("Implementar estratégias de proteção contra drawdowns")

        if metrics.beta > 1.5:
            recommendations.append("Reduzir exposição a ativos de alta volatilidade")

        # Recomendações baseadas em composição
        top_weights = sorted(composition.items(), key=lambda x: x[1]['weight'], reverse=True)[:3]

        if top_weights and top_weights[0][1]['weight'] > 0.30:
            recommendations.append(f"Alta concentração em {top_weights[0][0]} ({top_weights[0][1]['weight']:.1%}). Considerar diversificação.")

        # Recomendações de rebalanceamento
        should_rebalance, reason = self.should_rebalance()
        if should_rebalance:
            recommendations.append(f"Rebalanceamento recomendado: {reason}")

        # Recomendações de otimização
        recommendations.append("Monitorar performance vs benchmark BTC")
        recommendations.append("Considerar rebalanceamento periódico para manter alocação")

        return recommendations[:5]  # Máximo 5 recomendações

# API para integração com o painel principal
def create_portfolio_manager():
    """Criar instância do portfolio manager"""
    return AdvancedPortfolioManager()

if __name__ == "__main__":
    # Teste do portfolio manager
    pm = create_portfolio_manager()

    # Teste de definição de alocação
    allocation = pm.set_target_allocation(AllocationStrategy.RISK_PARITY)
    print(f"Alocação alvo: {allocation}")

    # Teste de rebalanceamento
    rebalance_result = pm.rebalance_portfolio()
    print(f"Rebalanceamento: {rebalance_result['success']}")

    # Teste de relatório
    report = pm.get_portfolio_report()
    print(f"Retorno total: {report['summary']['total_return']:.2%}")
