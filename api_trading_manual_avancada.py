#!/usr/bin/env python3
"""
FreqTrade3 - API de Trading Manual Avançada
Versão: 4.0 - Trading Manual Profissional
Características: Múltiplos tipos de ordens, gestão de posições, análise técnica integrada, alavancagem
"""

import asyncio
import json
import logging
import math
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import websockets
from flask import Blueprint, Flask, jsonify, request

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Tipos de ordem"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    OCO = "oco"  # One-Cancels-Other

class OrderSide(Enum):
    """Lado da ordem"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Status da ordem"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PositionSide(Enum):
    """Lado da posição"""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"

class TradingMode(Enum):
    """Modo de trading"""
    SPOT = "spot"
    FUTURES = "futures"
    MARGIN = "margin"

@dataclass
class OrderRequest:
    """Requisição de ordem"""
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good-Til-Canceled
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reduce_only: bool = False
    close_position: bool = False
    iceberg_qty: Optional[float] = None
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class Order:
    """Ordem estruturada"""
    id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    filled_quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    time_in_force: str
    created_time: str
    updated_time: str
    filled_time: Optional[str]
    leverage: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reduce_only: bool
    close_position: bool
    iceberg_qty: Optional[float]
    commission: float
    commission_asset: str
    metadata: Dict[str, Any]
    error_message: Optional[str] = None

@dataclass
class Position:
    """Posição"""
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    realized_pnl: float
    percentage: float
    leverage: float
    margin: float
    isolated: bool
    update_time: str

class AdvancedManualTradingAPI:
    """API avançada de trading manual"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db',
                 initial_balance: float = 100000.0):
        self.db_path = db_path
        self.trading_data_dir = 'trading_data'
        self.config_file = 'configs/manual_trading_config.yaml'

        # Criar diretórios
        os.makedirs(self.trading_data_dir, exist_ok=True)
        os.makedirs('configs', exist_ok=True)

        # Estado interno
        self.orders = {}
        self.positions = {}
        self.balances = {}
        self.trade_history = deque(maxlen=10000)
        self.order_history = deque(maxlen=1000)
        self.balance_history = deque(maxlen=1000)

        # Configurações
        self.config = self._load_config()

        # Inicializar API
        self._init_trading_api()

        # Thread de monitoramento
        self.monitoring_active = False
        self.monitor_thread = None

        # WebSocket connections para dados em tempo real
        self.websocket_connections = set()

    def _init_trading_api(self):
        """Inicializar API de trading"""
        # Inicializar base de dados
        self._init_database()

        # Carregar estado atual
        self._load_current_state()

        # Inicializar saldos
        self._init_balances(initial_balance)

        print("💼 API de Trading Manual Avançada inicializada")

    def _init_database(self):
        """Inicializar base de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de ordens
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manual_orders (
                    id TEXT PRIMARY KEY,
                    client_order_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    type TEXT,
                    quantity REAL,
                    filled_quantity REAL,
                    price REAL,
                    stop_price REAL,
                    status TEXT,
                    time_in_force TEXT,
                    created_time TEXT,
                    updated_time TEXT,
                    filled_time TEXT,
                    leverage REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    reduce_only BOOLEAN,
                    close_position BOOLEAN,
                    iceberg_qty REAL,
                    commission REAL,
                    commission_asset TEXT,
                    metadata TEXT,
                    error_message TEXT
                )
            ''')

            # Tabela de posições
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manual_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    side TEXT,
                    size REAL,
                    entry_price REAL,
                    mark_price REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    percentage REAL,
                    leverage REAL,
                    margin REAL,
                    isolated BOOLEAN,
                    update_time TEXT
                )
            ''')

            # Tabela de trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manual_trades (
                    id TEXT PRIMARY KEY,
                    order_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    type TEXT,
                    quantity REAL,
                    price REAL,
                    commission REAL,
                    commission_asset TEXT,
                    time TEXT,
                    is_maker BOOLEAN,
                    metadata TEXT
                )
            ''')

            # Tabela de saldos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manual_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset TEXT,
                    free REAL,
                    locked REAL,
                    total REAL,
                    update_time TEXT
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações"""
        default_config = {
            'trading': {
                'min_order_size': 10.0,  # $10 mínimo
                'max_order_size': 1000000.0,  # $1M máximo
                'max_leverage': 125,
                'default_leverage': 1.0,
                'commission_rate': 0.001,  # 0.1%
                'commission_asset': 'USDT',
                'price_precision': 8,
                'quantity_precision': 8
            },
            'risk_management': {
                'max_daily_loss': 0.10,  # 10% perda diária máxima
                'max_position_size': 0.20,  # 20% do portfólio por posição
                'enable_stop_loss': True,
                'enable_take_profit': True,
                'default_stop_loss_pct': 0.05,  # 5%
                'default_take_profit_pct': 0.10,  # 10%
                'max_slippage': 0.005  # 0.5%
            },
            'order_types': {
                'market_orders': True,
                'limit_orders': True,
                'stop_orders': True,
                'stop_limit_orders': True,
                'trailing_stop_orders': True,
                'iceberg_orders': True,
                'oco_orders': True
            },
            'timeframes': ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'],
            'supported_symbols': [
                'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT',
                'SOL/USDT', 'DOT/USDT', 'LINK/USDT', 'LTC/USDT', 'BCH/USDT'
            ]
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

    def _load_current_state(self):
        """Carregar estado atual do trading"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Carregar ordens abertas
            cursor.execute('''
                SELECT * FROM manual_orders
                WHERE status IN ('open', 'partially_filled', 'pending')
            ''')

            for row in cursor.fetchall():
                order = self._row_to_order(row)
                self.orders[order.id] = order

            # Carregar posições
            cursor.execute('SELECT * FROM manual_positions WHERE size != 0')

            for row in cursor.fetchall():
                position = self._row_to_position(row)
                self.positions[position.symbol] = position

            conn.close()

        except Exception as e:
            print(f"⚠️  Erro ao carregar estado: {e}")

    def _init_balances(self, initial_balance: float):
        """Inicializar saldos"""
        self.balances = {
            'USDT': {
                'free': initial_balance,
                'locked': 0.0,
                'total': initial_balance
            },
            'BTC': {
                'free': 0.0,
                'locked': 0.0,
                'total': 0.0
            },
            'ETH': {
                'free': 0.0,
                'locked': 0.0,
                'total': 0.0
            }
        }

        # Salvar no banco
        self._save_balances()

    def _row_to_order(self, row) -> Order:
        """Converter row do banco para Order"""
        return Order(
            id=row[0],
            client_order_id=row[1],
            symbol=row[2],
            side=OrderSide(row[3]),
            type=OrderType(row[4]),
            quantity=float(row[5]),
            filled_quantity=float(row[6]),
            price=float(row[7]) if row[7] else None,
            stop_price=float(row[8]) if row[8] else None,
            status=OrderStatus(row[9]),
            time_in_force=row[10],
            created_time=row[11],
            updated_time=row[12],
            filled_time=row[13],
            leverage=float(row[14]),
            stop_loss=float(row[15]) if row[15] else None,
            take_profit=float(row[16]) if row[16] else None,
            reduce_only=bool(row[17]),
            close_position=bool(row[18]),
            iceberg_qty=float(row[19]) if row[19] else None,
            commission=float(row[20]),
            commission_asset=row[21],
            metadata=json.loads(row[22]) if row[22] else {},
            error_message=row[23]
        )

    def _row_to_position(self, row) -> Position:
        """Converter row do banco para Position"""
        return Position(
            symbol=row[1],
            side=PositionSide(row[2]),
            size=float(row[3]),
            entry_price=float(row[4]),
            mark_price=float(row[5]),
            unrealized_pnl=float(row[6]),
            realized_pnl=float(row[7]),
            percentage=float(row[8]),
            leverage=float(row[9]),
            margin=float(row[10]),
            isolated=bool(row[11]),
            update_time=row[12]
        )

    def create_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Criar nova ordem"""
        try:
            # Validar requisição
            validation_result = self._validate_order_request(order_request)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'code': 'INVALID_REQUEST'
                }

            # Verificar permissões
            if not self._check_order_permissions(order_request):
                return {
                    'success': False,
                    'error': 'Order type not allowed',
                    'code': 'NOT_ALLOWED'
                }

            # Calcular detalhes da ordem
            order_details = self._calculate_order_details(order_request)

            # Verificar saldo
            if not self._check_balance_sufficient(order_request, order_details):
                return {
                    'success': False,
                    'error': 'Insufficient balance',
                    'code': 'INSUFFICIENT_BALANCE'
                }

            # Criar ordem
            order = self._create_order_object(order_request, order_details)

            # Salvar ordem
            self.orders[order.id] = order
            self._save_order(order)

            # Bloquear saldo
            self._lock_balance(order_request, order_details)

            # Processar ordem imediatamente se for market order
            if order_request.type == OrderType.MARKET:
                self._execute_market_order(order)

            logger.info(f"Ordem criada: {order.id} - {order_request.symbol} {order_request.side.value} {order_request.quantity}")

            return {
                'success': True,
                'order_id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'status': order.status.value,
                'type': order.type.value,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': order.price,
                'stop_price': order.stop_price,
                'created_time': order.created_time
            }

        except Exception as e:
            logger.error(f"Erro ao criar ordem: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }

    def _validate_order_request(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Validar requisição de ordem"""
        # Verificar símbolo
        if order_request.symbol not in self.config['supported_symbols']:
            return {'valid': False, 'error': f'Symbol {order_request.symbol} not supported'}

        # Verificar quantidade
        if order_request.quantity <= 0:
            return {'valid': False, 'error': 'Quantity must be positive'}

        # Verificar limites de quantidade
        min_size = self.config['trading']['min_order_size']
        max_size = self.config['trading']['max_order_size']

        current_price = self._get_current_price(order_request.symbol)
        order_value = order_request.quantity * (order_request.price or current_price)

        if order_value < min_size:
            return {'valid': False, 'error': f'Order value too small. Minimum: ${min_size}'}

        if order_value > max_size:
            return {'valid': False, 'error': f'Order value too large. Maximum: ${max_size}'}

        # Verificar alavancagem
        max_leverage = self.config['trading']['max_leverage']
        if order_request.leverage > max_leverage:
            return {'valid': False, 'error': f'Leverage too high. Maximum: {max_leverage}x'}

        # Verificar tipos de ordem que requerem preço
        price_required_types = [OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT]
        if order_request.type in price_required_types and not order_request.price:
            return {'valid': False, 'error': f'Price required for {order_request.type.value} orders'}

        # Verificar stop price para stop orders
        stop_required_types = [OrderType.STOP, OrderType.STOP_LIMIT, OrderType.TRAILING_STOP]
        if order_request.type in stop_required_types and not order_request.stop_price:
            return {'valid': False, 'error': f'Stop price required for {order_request.type.value} orders'}

        return {'valid': True, 'error': None}

    def _check_order_permissions(self, order_request: OrderRequest) -> bool:
        """Verificar se o tipo de ordem é permitido"""
        allowed_types = self.config['order_types']

        type_map = {
            OrderType.MARKET: 'market_orders',
            OrderType.LIMIT: 'limit_orders',
            OrderType.STOP: 'stop_orders',
            OrderType.STOP_LIMIT: 'stop_limit_orders',
            OrderType.TRAILING_STOP: 'trailing_stop_orders',
            OrderType.ICEBERG: 'iceberg_orders',
            OrderType.OCO: 'oco_orders'
        }

        config_key = type_map.get(order_request.type)
        return allowed_types.get(config_key, True)

    def _calculate_order_details(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Calcular detalhes da ordem"""
        current_price = self._get_current_price(order_request.symbol)

        # Preço efetivo
        if order_request.type == OrderType.MARKET:
            effective_price = current_price
        else:
            effective_price = order_request.price

        # Valor da ordem
        order_value = order_request.quantity * effective_price

        # Comissão
        commission_rate = self.config['trading']['commission_rate']
        commission = order_value * commission_rate

        # Margem necessária (apenas para posições com alavancagem)
        margin_required = order_value / order_request.leverage if order_request.leverage > 1 else order_value

        # Slippage estimado (apenas para market orders)
        max_slippage = self.config['risk_management']['max_slippage']
        estimated_slippage = order_value * max_slippage if order_request.type == OrderType.MARKET else 0

        return {
            'current_price': current_price,
            'effective_price': effective_price,
            'order_value': order_value,
            'commission': commission,
            'margin_required': margin_required,
            'estimated_slippage': estimated_slippage,
            'total_cost': order_value + commission + estimated_slippage
        }

    def _check_balance_sufficient(self, order_request: OrderRequest, order_details: Dict[str, Any]) -> bool:
        """Verificar se o saldo é suficiente"""
        if order_request.side == OrderSide.BUY:
            # Verificar saldo em USDT
            usdt_balance = self.balances.get('USDT', {'free': 0})['free']
            return usdt_balance >= order_details['total_cost']
        else:
            # Verificar saldo do ativo
            asset = order_request.symbol.split('/')[0]
            asset_balance = self.balances.get(asset, {'free': 0})['free']
            return asset_balance >= order_request.quantity

    def _lock_balance(self, order_request: OrderRequest, order_details: Dict[str, Any]):
        """Bloquear saldo para a ordem"""
        if order_request.side == OrderSide.BUY:
            # Bloquear USDT
            self.balances['USDT']['free'] -= order_details['total_cost']
            self.balances['USDT']['locked'] += order_details['total_cost']
        else:
            # Bloquear o ativo
            asset = order_request.symbol.split('/')[0]
            self.balances[asset]['free'] -= order_request.quantity
            self.balances[asset]['locked'] += order_request.quantity

        self._save_balances()

    def _create_order_object(self, order_request: OrderRequest, order_details: Dict[str, Any]) -> Order:
        """Criar objeto Order"""
        order_id = str(uuid.uuid4())
        client_order_id = order_request.client_order_id or f"manual_{int(time.time() * 1000)}"

        return Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            type=order_request.type,
            quantity=order_request.quantity,
            filled_quantity=0.0,
            price=order_request.price,
            stop_price=order_request.stop_price,
            status=OrderStatus.PENDING,
            time_in_force=order_request.time_in_force,
            created_time=datetime.now().isoformat(),
            updated_time=datetime.now().isoformat(),
            filled_time=None,
            leverage=order_request.leverage,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit,
            reduce_only=order_request.reduce_only,
            close_position=order_request.close_position,
            iceberg_qty=order_request.iceberg_qty,
            commission=0.0,
            commission_asset=self.config['trading']['commission_asset'],
            metadata=order_request.metadata or {}
        )

    def _get_current_price(self, symbol: str) -> float:
        """Obter preço atual (simulado)"""
        # Preços aproximados atuais
        prices = {
            'BTC/USDT': 98500, 'ETH/USDT': 3250, 'BNB/USDT': 685,
            'ADA/USDT': 0.98, 'XRP/USDT': 1.85, 'SOL/USDT': 235,
            'DOT/USDT': 8.75, 'LINK/USDT': 24.50, 'LTC/USDT': 110,
            'BCH/USDT': 350
        }
        return prices.get(symbol, 100.0)

    def _execute_market_order(self, order: Order):
        """Executar ordem de mercado imediatamente"""
        try:
            current_price = self._get_current_price(order.symbol)

            # Simular execução
            fill_quantity = order.quantity
            fill_price = current_price * np.random.uniform(0.999, 1.001)  # Pequena variação
            commission = fill_quantity * fill_price * self.config['trading']['commission_rate']

            # Atualizar ordem
            order.filled_quantity = fill_quantity
            order.status = OrderStatus.FILLED
            order.filled_time = datetime.now().isoformat()
            order.updated_time = datetime.now().isoformat()
            order.commission = commission

            # Desbloquear saldo
            self._unlock_balance(order)

            # Executar trade
            self._execute_trade(order, fill_quantity, fill_price, commission)

            # Atualizar posição
            self._update_position(order, fill_quantity, fill_price)

            # Salvar ordem atualizada
            self._save_order(order)

            logger.info(f"Ordem de mercado executada: {order.id}")

        except Exception as e:
            logger.error(f"Erro ao executar ordem de mercado: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
            self._unlock_balance(order)

    def _unlock_balance(self, order: Order):
        """Desbloquear saldo da ordem"""
        if order.side == OrderSide.BUY:
            # Desbloquear USDT
            total_cost = (order.filled_quantity * (order.price or 0)) + order.commission
            self.balances['USDT']['locked'] -= total_cost
            self.balances['USDT']['free'] += total_cost
        else:
            # Desbloquear o ativo
            self.balances[order.symbol.split('/')[0]]['locked'] -= order.filled_quantity
            self.balances[order.symbol.split('/')[0]]['free'] += order.filled_quantity

    def _execute_trade(self, order: Order, quantity: float, price: float, commission: float):
        """Executar trade"""
        trade_id = str(uuid.uuid4())

        trade = {
            'id': trade_id,
            'order_id': order.id,
            'symbol': order.symbol,
            'side': order.side.value,
            'type': order.type.value,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'commission_asset': order.commission_asset,
            'time': datetime.now().isoformat(),
            'is_maker': False,  # Market order é sempre taker
            'metadata': order.metadata
        }

        # Salvar trade
        self._save_trade(trade)
        self.trade_history.append(trade)

    def _update_position(self, order: Order, quantity: float, price: float):
        """Atualizar posição"""
        symbol = order.symbol
        asset = symbol.split('/')[0]

        if symbol not in self.positions:
            # Nova posição
            self.positions[symbol] = Position(
                symbol=symbol,
                side=PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT,
                size=quantity if order.side == OrderSide.BUY else -quantity,
                entry_price=price,
                mark_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                percentage=0.0,
                leverage=order.leverage,
                margin=quantity * price / order.leverage,
                isolated=False,
                update_time=datetime.now().isoformat()
            )
        else:
            # Atualizar posição existente
            position = self.positions[symbol]

            if order.side == OrderSide.BUY:
                # Adicionar à posição
                if position.side == PositionSide.LONG:
                    total_cost = position.size * position.entry_price + quantity * price
                    new_size = position.size + quantity
                    new_entry_price = total_cost / new_size if new_size > 0 else 0
                    position.size = new_size
                    position.entry_price = new_entry_price
                else:
                    # Fechar posição short
                    if quantity >= abs(position.size):
                        # Fechar completamente
                        pnl = (position.entry_price - price) * abs(position.size)
                        position.realized_pnl += pnl
                        del self.positions[symbol]
                    else:
                        # Fechar parcialmente
                        pnl = (position.entry_price - price) * quantity
                        position.realized_pnl += pnl
                        position.size += quantity
            else:
                # Venda
                if position.side == PositionSide.LONG:
                    # Fechar posição long
                    if quantity >= position.size:
                        pnl = (price - position.entry_price) * position.size
                        position.realized_pnl += pnl
                        del self.positions[symbol]
                    else:
                        pnl = (price - position.entry_price) * quantity
                        position.realized_pnl += pnl
                        position.size -= quantity
                else:
                    # Adicionar à posição short
                    total_cost = abs(position.size) * position.entry_price + quantity * price
                    new_size = position.size - quantity
                    new_entry_price = total_cost / abs(new_size) if new_size < 0 else 0
                    position.size = new_size
                    position.entry_price = new_entry_price

        # Atualizar PnL não realizado
        self._update_unrealized_pnl()

    def _update_unrealized_pnl(self):
        """Atualizar PnL não realizado de todas as posições"""
        total_portfolio_value = self._get_total_portfolio_value()

        for symbol, position in self.positions.items():
            current_price = self._get_current_price(symbol)
            position.mark_price = current_price

            if position.size > 0:  # Long position
                position.unrealized_pnl = (current_price - position.entry_price) * position.size
            else:  # Short position
                position.unrealized_pnl = (position.entry_price - current_price) * abs(position.size)

            # Percentual da posição
            position_value = abs(position.size) * current_price
            position.percentage = position_value / total_portfolio_value if total_portfolio_value > 0 else 0

        self._save_positions()

    def _get_total_portfolio_value(self) -> float:
        """Obter valor total do portfólio"""
        total_value = 0.0

        # Valor em cash
        for asset, balance in self.balances.items():
            if asset == 'USDT':
                total_value += balance['total']
            else:
                # Converter para USDT
                price = self._get_current_price(f"{asset}/USDT")
                total_value += balance['total'] * price

        # Valor das posições
        for position in self.positions.values():
            position_value = abs(position.size) * position.mark_price
            total_value += position_value

        return total_value

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancelar ordem"""
        try:
            if order_id not in self.orders:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'code': 'ORDER_NOT_FOUND'
                }

            order = self.orders[order_id]

            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                return {
                    'success': False,
                    'error': 'Order cannot be cancelled',
                    'code': 'ORDER_STATE_ERROR'
                }

            # Atualizar status
            order.status = OrderStatus.CANCELLED
            order.updated_time = datetime.now().isoformat()

            # Desbloquear saldo
            self._unlock_balance(order)

            # Salvar
            self._save_order(order)

            logger.info(f"Ordem cancelada: {order_id}")

            return {
                'success': True,
                'order_id': order_id,
                'status': order.status.value
            }

        except Exception as e:
            logger.error(f"Erro ao cancelar ordem: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Obter status da ordem"""
        if order_id not in self.orders:
            return {
                'success': False,
                'error': 'Order not found',
                'code': 'ORDER_NOT_FOUND'
            }

        order = self.orders[order_id]
        return {
            'success': True,
            'order': asdict(order)
        }

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Obter ordens abertas"""
        open_orders = []

        for order in self.orders.values():
            if order.status in [OrderStatus.OPEN, OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                if symbol is None or order.symbol == symbol:
                    open_orders.append(asdict(order))

        return {
            'success': True,
            'orders': open_orders,
            'count': len(open_orders)
        }

    def get_positions(self) -> Dict[str, Any]:
        """Obter posições atuais"""
        positions_data = []

        for symbol, position in self.positions.items():
            if position.size != 0:
                positions_data.append(asdict(position))

        return {
            'success': True,
            'positions': positions_data,
            'count': len(positions_data)
        }

    def get_account_info(self) -> Dict[str, Any]:
        """Obter informações da conta"""
        # Atualizar PnL
        self._update_unrealized_pnl()

        # Calcular métricas da conta
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_portfolio_value = self._get_total_portfolio_value()

        # Total em trades
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        return {
            'success': True,
            'account': {
                'total_portfolio_value': total_portfolio_value,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'balances': self.balances,
                'positions_count': len(self.positions),
                'open_orders_count': len([o for o in self.orders.values() if o.status in [OrderStatus.OPEN, OrderStatus.PENDING]]),
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_commission': sum(t.get('commission', 0) for t in self.trade_history),
                'available_balance': self.balances.get('USDT', {}).get('free', 0)
            }
        }

    def get_trade_history(self, limit: int = 100) -> Dict[str, Any]:
        """Obter histórico de trades"""
        trades = list(self.trade_history)[-limit:]

        return {
            'success': True,
            'trades': trades,
            'count': len(trades)
        }

    def _save_order(self, order: Order):
        """Salvar ordem no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO manual_orders
                (id, client_order_id, symbol, side, type, quantity, filled_quantity,
                 price, stop_price, status, time_in_force, created_time, updated_time,
                 filled_time, leverage, stop_loss, take_profit, reduce_only, close_position,
                 iceberg_qty, commission, commission_asset, metadata, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.id, order.client_order_id, order.symbol, order.side.value,
                order.type.value, order.quantity, order.filled_quantity, order.price,
                order.stop_price, order.status.value, order.time_in_force, order.created_time,
                order.updated_time, order.filled_time, order.leverage, order.stop_loss,
                order.take_profit, order.reduce_only, order.close_position, order.iceberg_qty,
                order.commission, order.commission_asset, json.dumps(order.metadata),
                order.error_message
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar ordem: {e}")

    def _save_positions(self):
        """Salvar posições no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Limpar posições existentes
            cursor.execute('DELETE FROM manual_positions')

            # Inserir posições atuais
            for symbol, position in self.positions.items():
                cursor.execute('''
                    INSERT INTO manual_positions
                    (symbol, side, size, entry_price, mark_price, unrealized_pnl,
                     realized_pnl, percentage, leverage, margin, isolated, update_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.symbol, position.side.value, position.size, position.entry_price,
                    position.mark_price, position.unrealized_pnl, position.realized_pnl,
                    position.percentage, position.leverage, position.margin, position.isolated,
                    position.update_time
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar posições: {e}")

    def _save_balances(self):
        """Salvar saldos no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Limpar saldos existentes
            cursor.execute('DELETE FROM manual_balances')

            # Inserir saldos atuais
            for asset, balance in self.balances.items():
                cursor.execute('''
                    INSERT INTO manual_balances
                    (asset, free, locked, total, update_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    asset, balance['free'], balance['locked'], balance['total'],
                    datetime.now().isoformat()
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar saldos: {e}")

    def _save_trade(self, trade: Dict[str, Any]):
        """Salvar trade no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO manual_trades
                (id, order_id, symbol, side, type, quantity, price, commission,
                 commission_asset, time, is_maker, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade['id'], trade['order_id'], trade['symbol'], trade['side'],
                trade['type'], trade['quantity'], trade['price'], trade['commission'],
                trade['commission_asset'], trade['time'], trade['is_maker'],
                json.dumps(trade['metadata'])
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar trade: {e}")

    def create_flask_routes(self) -> Blueprint:
        """Criar rotas Flask para a API"""
        trading_bp = Blueprint('manual_trading', __name__)

        @trading_bp.route('/api/manual/order', methods=['POST'])
        def create_order_route():
            """Criar nova ordem"""
            data = request.get_json()

            try:
                order_request = OrderRequest(
                    symbol=data['symbol'],
                    side=OrderSide(data['side']),
                    type=OrderType(data['type']),
                    quantity=float(data['quantity']),
                    price=float(data.get('price')) if data.get('price') else None,
                    stop_price=float(data.get('stop_price')) if data.get('stop_price') else None,
                    time_in_force=data.get('time_in_force', 'GTC'),
                    leverage=float(data.get('leverage', 1.0)),
                    stop_loss=float(data.get('stop_loss')) if data.get('stop_loss') else None,
                    take_profit=float(data.get('take_profit')) if data.get('take_profit') else None,
                    reduce_only=data.get('reduce_only', False),
                    close_position=data.get('close_position', False),
                    iceberg_qty=float(data.get('iceberg_qty')) if data.get('iceberg_qty') else None,
                    client_order_id=data.get('client_order_id'),
                    metadata=data.get('metadata', {})
                )

                result = self.create_order(order_request)
                return jsonify(result)

            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_REQUEST'
                }), 400

        @trading_bp.route('/api/manual/order/<order_id>', methods=['DELETE'])
        def cancel_order_route(order_id):
            """Cancelar ordem"""
            result = self.cancel_order(order_id)
            return jsonify(result)

        @trading_bp.route('/api/manual/order/<order_id>', methods=['GET'])
        def get_order_route(order_id):
            """Obter status da ordem"""
            result = self.get_order_status(order_id)
            return jsonify(result)

        @trading_bp.route('/api/manual/orders', methods=['GET'])
        def get_orders_route():
            """Obter ordens abertas"""
            symbol = request.args.get('symbol')
            result = self.get_open_orders(symbol)
            return jsonify(result)

        @trading_bp.route('/api/manual/positions', methods=['GET'])
        def get_positions_route():
            """Obter posições"""
            result = self.get_positions()
            return jsonify(result)

        @trading_bp.route('/api/manual/account', methods=['GET'])
        def get_account_route():
            """Obter informações da conta"""
            result = self.get_account_info()
            return jsonify(result)

        @trading_bp.route('/api/manual/trades', methods=['GET'])
        def get_trades_route():
            """Obter histórico de trades"""
            limit = int(request.args.get('limit', 100))
            result = self.get_trade_history(limit)
            return jsonify(result)

        @trading_bp.route('/api/manual/price/<symbol>', methods=['GET'])
        def get_price_route(symbol):
            """Obter preço atual"""
            price = self._get_current_price(symbol)
            return jsonify({
                'success': True,
                'symbol': symbol,
                'price': price,
                'timestamp': datetime.now().isoformat()
            })

        return trading_bp

# API para integração
def create_manual_trading_api():
    """Criar instância da API de trading manual"""
    return AdvancedManualTradingAPI()

if __name__ == "__main__":
    # Teste da API
    trading_api = create_manual_trading_api()

    # Criar ordem de teste
    order_request = OrderRequest(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=0.001,
        leverage=1.0
    )

    result = trading_api.create_order(order_request)
    print(f"Resultado da ordem: {result}")

    # Obter informações da conta
    account = trading_api.get_account_info()
    print(f"Conta: {account}")

    # Inicializar Flask routes (exemplo)
    # app = Flask(__name__)
    # app.register_blueprint(trading_api.create_flask_routes())
    # app.run(debug=True)
