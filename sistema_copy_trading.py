#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Copy Trading
Versão: 4.0 - Social Trading Avançado
Características: Leader traders, followers, performance tracking, alocação dinâmica, comissionamento
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import secrets
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
import pandas as pd

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CopyTradingStatus(Enum):
    """Status do copy trading"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SUSPENDED = "suspended"

class TraderLevel(Enum):
    """Níveis de trader"""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"

class PerformanceMetric(Enum):
    """Métricas de performance"""
    TOTAL_RETURN = "total_return"
    SHARPE_RATIO = "sharpe_ratio"
    WIN_RATE = "win_rate"
    MAX_DRAWDOWN = "max_drawdown"
    PROFIT_FACTOR = "profit_factor"
    CONSISTENCY = "consistency"
    TRADES_COUNT = "trades_count"

@dataclass
class LeaderTrader:
    """Trader leader (quem pode ser copiado)"""
    id: str
    username: str
    display_name: str
    bio: str
    avatar_url: str
    level: TraderLevel
    total_followers: int
    total_aum: float  # Assets Under Management
    performance_score: float
    verified: bool
    created_at: str
    last_active: str
    settings: Dict[str, Any]
    stats: Dict[str, Any]

@dataclass
class Follower:
    """Follower (quem copia trades)"""
    id: str
    leader_id: str
    user_id: str
    allocation_amount: float
    allocation_percentage: float
    risk_level: str  # low, medium, high
    auto_invest: bool
    stop_loss_percentage: float
    max_drawdown_limit: float
    created_at: str
    status: CopyTradingStatus
    last_sync: str
    performance: Dict[str, Any]

@dataclass
class CopyTrade:
    """Trade copiado"""
    id: str
    leader_id: str
    follower_id: str
    original_trade_id: str
    symbol: str
    side: str  # buy, sell
    amount: float
    price: float
    executed_price: float
    copy_percentage: float
    status: str  # pending, executed, failed, cancelled
    created_at: str
    executed_at: str
    error_message: Optional[str] = None

class CopyTradingSystem:
    """Sistema de copy trading completo"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.copy_data_dir = 'copy_data'
        self.avatars_dir = 'avatars'

        # Criar diretórios
        os.makedirs(self.copy_data_dir, exist_ok=True)
        os.makedirs(self.avatars_dir, exist_ok=True)

        # Estado interno
        self.leaders = {}
        self.followers = {}
        self.copy_trades = {}
        self.performance_cache = {}
        self.sync_active = False
        self.sync_thread = None

        # Configurações
        self.config = self._load_config()

        # Inicializar sistema
        self._init_copy_trading_system()

    def _init_copy_trading_system(self):
        """Inicializar sistema de copy trading"""
        # Inicializar base de dados
        self._init_database()

        # Carregar dados existentes
        self._load_leaders()
        self._load_followers()

        # Inicializar sincronização
        self._init_sync_system()

        print("👥 Sistema de Copy Trading inicializado")

    def _init_database(self):
        """Inicializar base de dados de copy trading"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de leaders
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS copy_leaders (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    display_name TEXT,
                    bio TEXT,
                    avatar_url TEXT,
                    level TEXT,
                    total_followers INTEGER,
                    total_aum REAL,
                    performance_score REAL,
                    verified BOOLEAN,
                    created_at TEXT,
                    last_active TEXT,
                    settings TEXT,
                    stats TEXT
                )
            ''')

            # Tabela de followers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS copy_followers (
                    id TEXT PRIMARY KEY,
                    leader_id TEXT,
                    user_id TEXT,
                    allocation_amount REAL,
                    allocation_percentage REAL,
                    risk_level TEXT,
                    auto_invest BOOLEAN,
                    stop_loss_percentage REAL,
                    max_drawdown_limit REAL,
                    created_at TEXT,
                    status TEXT,
                    last_sync TEXT,
                    performance TEXT,
                    FOREIGN KEY (leader_id) REFERENCES copy_leaders (id)
                )
            ''')

            # Tabela de copy trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS copy_trades (
                    id TEXT PRIMARY KEY,
                    leader_id TEXT,
                    follower_id TEXT,
                    original_trade_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    amount REAL,
                    price REAL,
                    executed_price REAL,
                    copy_percentage REAL,
                    status TEXT,
                    created_at TEXT,
                    executed_at TEXT,
                    error_message TEXT,
                    FOREIGN KEY (leader_id) REFERENCES copy_leaders (id),
                    FOREIGN KEY (follower_id) REFERENCES copy_followers (id)
                )
            ''')

            # Tabela de performance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS copy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trader_id TEXT,
                    trader_type TEXT,  -- leader ou follower
                    date TEXT,
                    total_value REAL,
                    pnl REAL,
                    return_percentage REAL,
                    positions_count INTEGER,
                    trades_count INTEGER,
                    aum REAL,
                    metrics TEXT,
                    created_at TEXT
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database de copy trading: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações"""
        default_config = {
            'copy_trading': {
                'min_allocation': 100.0,  # $100 mínimo
                'max_leader_followers': 1000,
                'max_follower_leaders': 50,
                'default_risk_level': 'medium',
                'max_risk_allocation': 0.20,  # 20% do portfólio
                'performance_calculation_period': 30,  # dias
                'leader_verification_required': False
            },
            'commission': {
                'leader_fee_percentage': 0.01,  # 1% dos profits
                'platform_fee_percentage': 0.005,  # 0.5%
                'payment_schedule': 'monthly'
            },
            'sync': {
                'enabled': True,
                'interval_seconds': 30,
                'max_concurrent_syncs': 10,
                'retry_attempts': 3
            },
            'filters': {
                'min_trades_count': 10,
                'min_performance_score': 5.0,
                'max_drawdown_threshold': 0.25,  # 25%
                'min_trading_days': 30
            },
            'risk_management': {
                'default_stop_loss': 0.05,  # 5%
                'max_daily_loss': 0.02,  # 2%
                'position_size_limit': 0.10,  # 10% por posição
                'correlation_limit': 0.70
            }
        }

        try:
            config_file = 'configs/copy_trading_config.json'
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return {**default_config, **config}
            else:
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração de copy trading: {e}")
            return default_config

    def register_leader_trader(self, username: str, display_name: str, bio: str = "",
                             avatar_url: str = "", level: TraderLevel = TraderLevel.NOVICE) -> str:
        """Registrar novo leader trader"""
        try:
            # Verificar se já existe
            if self._get_leader_by_username(username):
                raise ValueError("Username já existe")

            leader_id = str(uuid.uuid4())

            leader = LeaderTrader(
                id=leader_id,
                username=username,
                display_name=display_name,
                bio=bio,
                avatar_url=avatar_url,
                level=level,
                total_followers=0,
                total_aum=0.0,
                performance_score=0.0,
                verified=False,
                created_at=datetime.now().isoformat(),
                last_active=datetime.now().isoformat(),
                settings={
                    'min_allocation': self.config['copy_trading']['min_allocation'],
                    'max_followers': self.config['copy_trading']['max_leader_followers'],
                    'auto_accept': True
                },
                stats={
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'total_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0
                }
            )

            # Salvar
            self.leaders[leader_id] = leader
            self._save_leader(leader)

            logger.info(f"Leader trader registrado: {username} ({leader_id})")
            return leader_id

        except Exception as e:
            logger.error(f"Erro ao registrar leader: {e}")
            raise

    def start_copying_leader(self, leader_id: str, user_id: str, allocation_amount: float,
                           risk_level: str = "medium", auto_invest: bool = True) -> str:
        """Iniciar cópia de um leader"""
        try:
            # Verificar se leader existe
            leader = self._get_leader(leader_id)
            if not leader:
                raise ValueError("Leader não encontrado")

            # Validar alocação
            if allocation_amount < self.config['copy_trading']['min_allocation']:
                raise ValueError(f"Alocação mínima: ${self.config['copy_trading']['min_allocation']}")

            # Verificar limites
            follower_count = len([f for f in self.followers.values() if f.leader_id == leader_id])
            if follower_count >= leader.settings.get('max_followers', self.config['copy_trading']['max_leader_followers']):
                raise ValueError("Leader atingiu limite de followers")

            follower_id = str(uuid.uuid4())

            follower = Follower(
                id=follower_id,
                leader_id=leader_id,
                user_id=user_id,
                allocation_amount=allocation_amount,
                allocation_percentage=0.0,  # Será calculado
                risk_level=risk_level,
                auto_invest=auto_invest,
                stop_loss_percentage=self.config['risk_management']['default_stop_loss'],
                max_drawdown_limit=self.config['copy_trading']['max_risk_allocation'],
                created_at=datetime.now().isoformat(),
                status=CopyTradingStatus.ACTIVE,
                last_sync=datetime.now().isoformat(),
                performance={
                    'total_pnl': 0.0,
                    'total_return': 0.0,
                    'win_rate': 0.0,
                    'trades_count': 0,
                    'started_at': datetime.now().isoformat()
                }
            )

            # Calcular alocação percentual
            follower.allocation_percentage = self._calculate_allocation_percentage(follower)

            # Salvar
            self.followers[follower_id] = follower
            self._save_follower(follower)

            # Atualizar stats do leader
            leader.total_followers += 1
            leader.total_aum += allocation_amount
            self._save_leader(leader)

            logger.info(f"Follower iniciado: {follower_id} copiando {leader_id}")
            return follower_id

        except Exception as e:
            logger.error(f"Erro ao iniciar copy: {e}")
            raise

    def _calculate_allocation_percentage(self, follower: Follower) -> float:
        """Calcular percentual de alocação baseado no risco"""
        risk_multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5
        }

        base_percentage = follower.allocation_amount / 10000  # Assumir portfólio base de $10k
        risk_multiplier = risk_multipliers.get(follower.risk_level, 1.0)

        return min(base_percentage * risk_multiplier, follower.max_drawdown_limit)

    def _get_leader(self, leader_id: str) -> Optional[LeaderTrader]:
        """Obter leader por ID"""
        return self.leaders.get(leader_id)

    def _get_leader_by_username(self, username: str) -> Optional[LeaderTrader]:
        """Obter leader por username"""
        for leader in self.leaders.values():
            if leader.username == username:
                return leader
        return None

    def _save_leader(self, leader: LeaderTrader):
        """Salvar leader no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO copy_leaders
                (id, username, display_name, bio, avatar_url, level,
                 total_followers, total_aum, performance_score, verified,
                 created_at, last_active, settings, stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                leader.id, leader.username, leader.display_name, leader.bio,
                leader.avatar_url, leader.level.value, leader.total_followers,
                leader.total_aum, leader.performance_score, leader.verified,
                leader.created_at, leader.last_active, json.dumps(leader.settings),
                json.dumps(leader.stats)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar leader: {e}")

    def _save_follower(self, follower: Follower):
        """Salvar follower no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO copy_followers
                (id, leader_id, user_id, allocation_amount, allocation_percentage,
                 risk_level, auto_invest, stop_loss_percentage, max_drawdown_limit,
                 created_at, status, last_sync, performance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                follower.id, follower.leader_id, follower.user_id,
                follower.allocation_amount, follower.allocation_percentage,
                follower.risk_level, follower.auto_invest, follower.stop_loss_percentage,
                follower.max_drawdown_limit, follower.created_at, follower.status.value,
                follower.last_sync, json.dumps(follower.performance)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar follower: {e}")

    def _load_leaders(self):
        """Carregar leaders do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM copy_leaders
            ''')

            for row in cursor.fetchall():
                leader = LeaderTrader(
                    id=row[0],
                    username=row[1],
                    display_name=row[2],
                    bio=row[3],
                    avatar_url=row[4],
                    level=TraderLevel(row[5]),
                    total_followers=row[6],
                    total_aum=row[7],
                    performance_score=row[8],
                    verified=row[9],
                    created_at=row[10],
                    last_active=row[11],
                    settings=json.loads(row[12]) if row[12] else {},
                    stats=json.loads(row[13]) if row[13] else {}
                )

                self.leaders[leader.id] = leader

            conn.close()
            print(f"📊 {len(self.leaders)} leaders carregados")

        except Exception as e:
            logger.error(f"Erro ao carregar leaders: {e}")

    def _load_followers(self):
        """Carregar followers do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM copy_followers
            ''')

            for row in cursor.fetchall():
                follower = Follower(
                    id=row[0],
                    leader_id=row[1],
                    user_id=row[2],
                    allocation_amount=row[3],
                    allocation_percentage=row[4],
                    risk_level=row[5],
                    auto_invest=row[6],
                    stop_loss_percentage=row[7],
                    max_drawdown_limit=row[8],
                    created_at=row[9],
                    status=CopyTradingStatus(row[10]),
                    last_sync=row[11],
                    performance=json.loads(row[12]) if row[12] else {}
                )

                self.followers[follower.id] = follower

            conn.close()
            print(f"👥 {len(self.followers)} followers carregados")

        except Exception as e:
            logger.error(f"Erro ao carregar followers: {e}")

    def sync_trade_execution(self, leader_id: str, trade_data: Dict[str, Any]) -> List[CopyTrade]:
        """Sincronizar execução de trade para followers"""
        try:
            if not self.sync_active:
                return []

            # Obter followers ativos do leader
            active_followers = [
                f for f in self.followers.values()
                if f.leader_id == leader_id and f.status == CopyTradingStatus.ACTIVE
            ]

            if not active_followers:
                return []

            copied_trades = []

            for follower in active_followers:
                try:
                    # Calcular amount copiado
                    copy_amount = self._calculate_copy_amount(follower, trade_data)

                    if copy_amount <= 0:
                        continue

                    # Criar copy trade
                    copy_trade = CopyTrade(
                        id=str(uuid.uuid4()),
                        leader_id=leader_id,
                        follower_id=follower.id,
                        original_trade_id=trade_data.get('id', ''),
                        symbol=trade_data['symbol'],
                        side=trade_data['side'],
                        amount=copy_amount,
                        price=trade_data.get('price', 0.0),
                        executed_price=0.0,
                        copy_percentage=copy_amount / trade_data.get('amount', 1.0),
                        status='pending',
                        created_at=datetime.now().isoformat(),
                        executed_at=''
                    )

                    # Executar trade simulado
                    success = self._execute_copy_trade(copy_trade, follower)

                    if success:
                        copy_trade.status = 'executed'
                        copy_trade.executed_at = datetime.now().isoformat()
                        copy_trade.executed_price = trade_data.get('price', 0.0) * np.random.uniform(0.999, 1.001)

                        # Atualizar performance do follower
                        self._update_follower_performance(follower, copy_trade, trade_data)
                    else:
                        copy_trade.status = 'failed'
                        copy_trade.error_message = "Falha na execução simulada"

                    # Salvar trade
                    self.copy_trades[copy_trade.id] = copy_trade
                    self._save_copy_trade(copy_trade)

                    copied_trades.append(copy_trade)

                except Exception as e:
                    logger.error(f"Erro ao copiar trade para follower {follower.id}: {e}")
                    continue

            logger.info(f"Trade sincronizado: {len(copied_trades)} cópias executadas")
            return copied_trades

        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            return []

    def _calculate_copy_amount(self, follower: Follower, trade_data: Dict[str, Any]) -> float:
        """Calcular amount a ser copiado"""
        try:
            # Amount base da alocação do follower
            base_amount = follower.allocation_amount

            # Verificar limites de risco
            trade_value = trade_data.get('amount', 0) * trade_data.get('price', 0)
            max_position_size = follower.allocation_amount * self.config['risk_management']['position_size_limit']

            if trade_value > max_position_size:
                # Reduzir amount proporcionalmente
                ratio = max_position_size / trade_value
                base_amount *= ratio

            # Aplicar percentual de alocação
            copy_amount = base_amount * follower.allocation_percentage

            # Aplicar multiplicadores de risco
            risk_multipliers = {'low': 0.7, 'medium': 1.0, 'high': 1.3}
            risk_multiplier = risk_multipliers.get(follower.risk_level, 1.0)
            copy_amount *= risk_multiplier

            return min(copy_amount, follower.allocation_amount * 0.5)  # Máximo 50% da alocação por trade

        except Exception as e:
            logger.error(f"Erro ao calcular copy amount: {e}")
            return 0.0

    def _execute_copy_trade(self, copy_trade: CopyTrade, follower: Follower) -> bool:
        """Executar trade copiado (simulado)"""
        try:
            # Verificar saldo disponível
            # Na implementação real, seria integrado com o sistema de trading
            current_balance = 10000.0  # Simulado

            trade_cost = copy_trade.amount * copy_trade.price

            if trade_cost > current_balance:
                logger.warning(f"Saldo insuficiente para follower {follower.id}")
                return False

            # Verificar stop loss
            if follower.stop_loss_percentage > 0:
                # Implementar lógica de stop loss
                pass

            return True

        except Exception as e:
            logger.error(f"Erro na execução do copy trade: {e}")
            return False

    def _update_follower_performance(self, follower: Follower, copy_trade: CopyTrade, original_trade: Dict[str, Any]):
        """Atualizar performance do follower"""
        try:
            # Simular PnL (na implementação real seria calculado baseado em preço atual)
            if copy_trade.status == 'executed':
                # Profit simulado baseado no side
                if copy_trade.side == 'buy':
                    current_price = copy_trade.price * np.random.uniform(0.98, 1.02)
                else:
                    current_price = copy_trade.price * np.random.uniform(0.98, 1.02)

                pnl = (current_price - copy_trade.price) * copy_trade.amount if copy_trade.side == 'buy' else (copy_trade.price - current_price) * copy_trade.amount
                pnl *= np.random.uniform(0.8, 1.2)  # Adicionar variação

                # Atualizar performance
                follower.performance['total_pnl'] = follower.performance.get('total_pnl', 0) + pnl
                follower.performance['trades_count'] = follower.performance.get('trades_count', 0) + 1

                # Calcular return
                current_total = follower.allocation_amount + follower.performance['total_pnl']
                follower.performance['total_return'] = (current_total - follower.allocation_amount) / follower.allocation_amount

                # Atualizar win rate
                if pnl > 0:
                    wins = follower.performance.get('wins', 0) + 1
                    total_trades = follower.performance['trades_count']
                    follower.performance['win_rate'] = wins / total_trades
                    follower.performance['wins'] = wins
                else:
                    follower.performance['wins'] = follower.performance.get('wins', 0)

                follower.last_sync = datetime.now().isoformat()

                # Salvar
                self._save_follower(follower)

                # Salvar performance no histórico
                self._save_performance_snapshot(follower.id, 'follower', follower.performance)

        except Exception as e:
            logger.error(f"Erro ao atualizar performance do follower: {e}")

    def _save_copy_trade(self, copy_trade: CopyTrade):
        """Salvar copy trade no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO copy_trades
                (id, leader_id, follower_id, original_trade_id, symbol, side,
                 amount, price, executed_price, copy_percentage, status,
                 created_at, executed_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                copy_trade.id, copy_trade.leader_id, copy_trade.follower_id,
                copy_trade.original_trade_id, copy_trade.symbol, copy_trade.side,
                copy_trade.amount, copy_trade.price, copy_trade.executed_price,
                copy_trade.copy_percentage, copy_trade.status, copy_trade.created_at,
                copy_trade.executed_at, copy_trade.error_message
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar copy trade: {e}")

    def _save_performance_snapshot(self, trader_id: str, trader_type: str, performance: Dict[str, Any]):
        """Salvar snapshot de performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO copy_performance
                (trader_id, trader_type, date, total_value, pnl, return_percentage,
                 positions_count, trades_count, aum, metrics, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trader_id, trader_type, datetime.now().date().isoformat(),
                performance.get('total_value', 10000.0), performance.get('total_pnl', 0.0),
                performance.get('total_return', 0.0), performance.get('positions_count', 0),
                performance.get('trades_count', 0), performance.get('allocation_amount', 0.0),
                json.dumps(performance), datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar performance snapshot: {e}")

    def _init_sync_system(self):
        """Inicializar sistema de sincronização"""
        if self.config['sync']['enabled']:
            self.sync_active = True
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            print("🔄 Sistema de sincronização iniciado")

    def _sync_loop(self):
        """Loop de sincronização"""
        while self.sync_active:
            try:
                # Sincronizar performance dos leaders
                self._sync_leader_performance()

                # Verificar stop losses e limites
                self._check_risk_limits()

                # Limpar trades antigos
                self._cleanup_old_trades()

                time.sleep(self.config['sync']['interval_seconds'])

            except Exception as e:
                logger.error(f"Erro no loop de sincronização: {e}")
                time.sleep(5)

    def _sync_leader_performance(self):
        """Sincronizar performance dos leaders"""
        for leader in self.leaders.values():
            try:
                # Calcular métricas de performance
                metrics = self._calculate_leader_performance(leader)

                # Atualizar leader
                leader.performance_score = metrics.get('overall_score', 0.0)
                leader.stats.update(metrics)
                leader.last_active = datetime.now().isoformat()

                # Salvar
                self._save_leader(leader)

                # Salvar snapshot
                self._save_performance_snapshot(leader.id, 'leader', metrics)

            except Exception as e:
                logger.error(f"Erro ao sincronizar leader {leader.id}: {e}")

    def _calculate_leader_performance(self, leader: LeaderTrader) -> Dict[str, Any]:
        """Calcular performance do leader"""
        try:
            # Obter trades do leader (simulado)
            leader_trades = self._get_leader_trades(leader.id)

            if not leader_trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'total_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'profit_factor': 1.0,
                    'consistency': 0.0,
                    'overall_score': 0.0
                }

            # Calcular métricas
            total_trades = len(leader_trades)
            winning_trades = len([t for t in leader_trades if t.get('pnl', 0) > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            total_pnl = sum(t.get('pnl', 0) for t in leader_trades)
            total_return = total_pnl / 10000  # Assumir capital inicial

            # Calcular Sharpe ratio (simplificado)
            returns = [t.get('return', 0) for t in leader_trades]
            if returns and len(returns) > 1:
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0
            else:
                sharpe_ratio = 0

            # Max drawdown (simplificado)
            cumulative_pnl = np.cumsum([t.get('pnl', 0) for t in leader_trades])
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = (cumulative_pnl - running_max) / (running_max + 1)
            max_drawdown = abs(np.min(drawdown))

            # Profit factor
            gross_profit = sum(t.get('pnl', 0) for t in leader_trades if t.get('pnl', 0) > 0)
            gross_loss = abs(sum(t.get('pnl', 0) for t in leader_trades if t.get('pnl', 0) < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

            # Consistência (baseada na variância dos retornos)
            consistency = 1.0 / (1.0 + np.std(returns)) if returns else 0

            # Score geral
            score_components = [
                win_rate * 25,
                min(total_return * 10, 25),
                min(sharpe_ratio * 10, 25),
                max(0, (0.20 - max_drawdown) * 50),  # Penalizar drawdown alto
                min(profit_factor * 10, 20),
                consistency * 10
            ]
            overall_score = sum(score_components)

            return {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'consistency': consistency,
                'overall_score': min(overall_score, 100)  # Limitar a 100
            }

        except Exception as e:
            logger.error(f"Erro ao calcular performance do leader: {e}")
            return {}

    def _get_leader_trades(self, leader_id: str) -> List[Dict[str, Any]]:
        """Obter trades do leader (simulado)"""
        # Na implementação real, seria obtido do sistema de trading
        # Por enquanto, gerar trades simulados para teste

        trades = []
        for i in range(np.random.randint(10, 100)):
            trade = {
                'id': f"trade_{i}",
                'pnl': np.random.normal(0, 100),
                'return': np.random.normal(0, 0.01),
                'timestamp': datetime.now() - timedelta(days=np.random.randint(1, 365))
            }
            trades.append(trade)

        return trades

    def _check_risk_limits(self):
        """Verificar limites de risco dos followers"""
        for follower in self.followers.values():
            if follower.status != CopyTradingStatus.ACTIVE:
                continue

            try:
                # Verificar drawdown
                current_return = follower.performance.get('total_return', 0)
                if current_return < -follower.max_drawdown_limit:
                    # Pausar follower
                    follower.status = CopyTradingStatus.PAUSED
                    self._save_follower(follower)
                    logger.warning(f"Follower {follower.id} pausado por drawdown excessivo")

                # Verificar stop loss
                if follower.stop_loss_percentage > 0:
                    # Implementar verificação de stop loss
                    pass

            except Exception as e:
                logger.error(f"Erro ao verificar risco do follower {follower.id}: {e}")

    def _cleanup_old_trades(self):
        """Limpar trades antigos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=90)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM copy_trades
                WHERE datetime(created_at) < datetime(?)
            ''', (cutoff_date.isoformat(),))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted_count > 0:
                logger.info(f"Trades antigos removidos: {deleted_count}")

        except Exception as e:
            logger.error(f"Erro ao limpar trades antigos: {e}")

    def get_leaderboard(self, metric: PerformanceMetric = PerformanceMetric.TOTAL_RETURN,
                       limit: int = 50) -> List[Dict[str, Any]]:
        """Obter leaderboard de traders"""
        try:
            # Calcular scores para todos os leaders
            leaderboard = []

            for leader in self.leaders.values():
                if not self._leader_meets_criteria(leader):
                    continue

                # Obter performance
                performance = self._calculate_leader_performance(leader)

                # Calcular score baseado na métrica solicitada
                score = self._calculate_metric_score(performance, metric)

                leaderboard.append({
                    'id': leader.id,
                    'username': leader.username,
                    'display_name': leader.display_name,
                    'avatar_url': leader.avatar_url,
                    'level': leader.level.value,
                    'total_followers': leader.total_followers,
                    'total_aum': leader.total_aum,
                    'verified': leader.verified,
                    'performance': performance,
                    'score': score
                })

            # Ordenar por score
            leaderboard.sort(key=lambda x: x['score'], reverse=True)

            return leaderboard[:limit]

        except Exception as e:
            logger.error(f"Erro ao obter leaderboard: {e}")
            return []

    def _leader_meets_criteria(self, leader: LeaderTrader) -> bool:
        """Verificar se leader atende aos critérios mínimos"""
        filters = self.config['filters']

        # Verificar número mínimo de trades
        if leader.stats.get('total_trades', 0) < filters['min_trades_count']:
            return False

        # Verificar score mínimo de performance
        if leader.performance_score < filters['min_performance_score']:
            return False

        # Verificar limite de drawdown
        if leader.stats.get('max_drawdown', 0) > filters['max_drawdown_threshold']:
            return False

        # Verificar dias mínimos de trading
        if leader.verified:
            trading_days = (datetime.now() - datetime.fromisoformat(leader.created_at)).days
            if trading_days < filters['min_trading_days']:
                return False

        return True

    def _calculate_metric_score(self, performance: Dict[str, Any], metric: PerformanceMetric) -> float:
        """Calcular score baseado na métrica"""
        metric_weights = {
            PerformanceMetric.TOTAL_RETURN: 1.0,
            PerformanceMetric.SHARPE_RATIO: 0.8,
            PerformanceMetric.WIN_RATE: 0.6,
            PerformanceMetric.MAX_DRAWDOWN: 0.9,  # Menor é melhor
            PerformanceMetric.PROFIT_FACTOR: 0.7,
            PerformanceMetric.CONSISTENCY: 0.5,
            PerformanceMetric.TRADES_COUNT: 0.3
        }

        weight = metric_weights.get(metric, 1.0)

        if metric == PerformanceMetric.MAX_DRAWDOWN:
            # Para drawdown, menor é melhor
            return weight * (1.0 - min(performance.get('max_drawdown', 0), 1.0))
        else:
            return weight * performance.get(metric.value, 0.0)

    def get_follower_performance(self, follower_id: str) -> Dict[str, Any]:
        """Obter performance de um follower"""
        try:
            follower = self.followers.get(follower_id)
            if not follower:
                return {}

            # Calcular performance detalhada
            performance = follower.performance.copy()

            # Adicionar métricas calculadas
            if follower.performance.get('trades_count', 0) > 0:
                performance['avg_trade'] = (follower.performance.get('total_pnl', 0) /
                                          follower.performance['trades_count'])
            else:
                performance['avg_trade'] = 0.0

            # Calcular período ativo
            started_at = datetime.fromisoformat(follower.performance.get('started_at', follower.created_at))
            days_active = (datetime.now() - started_at).days
            performance['days_active'] = days_active

            if days_active > 0:
                performance['daily_return'] = (performance.get('total_return', 0) / days_active)
                performance['trades_per_day'] = (performance.get('trades_count', 0) / days_active)
            else:
                performance['daily_return'] = 0.0
                performance['trades_per_day'] = 0.0

            return performance

        except Exception as e:
            logger.error(f"Erro ao obter performance do follower {follower_id}: {e}")
            return {}

    def stop_copying_leader(self, follower_id: str) -> bool:
        """Parar de copiar um leader"""
        try:
            follower = self.followers.get(follower_id)
            if not follower:
                return False

            # Alterar status
            follower.status = CopyTradingStatus.INACTIVE
            self._save_follower(follower)

            # Atualizar stats do leader
            leader = self.leaders.get(follower.leader_id)
            if leader:
                leader.total_followers = max(0, leader.total_followers - 1)
                leader.total_aum = max(0, leader.total_aum - follower.allocation_amount)
                self._save_leader(leader)

            logger.info(f"Copy trading parado para follower {follower_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao parar copy trading: {e}")
            return False

    def get_copy_trading_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas gerais do copy trading"""
        try:
            # Contadores
            total_leaders = len(self.leaders)
            total_followers = len(self.followers)
            active_copy_trades = len([t for t in self.copy_trades.values() if t.status == 'pending'])

            # AUM total
            total_aum = sum(leader.total_aum for leader in self.leaders.values())

            # Performance média
            if self.leaders:
                avg_performance = np.mean([leader.performance_score for leader in self.leaders.values()])
                avg_followers = np.mean([leader.total_followers for leader in self.leaders.values()])
            else:
                avg_performance = 0
                avg_followers = 0

            # Top performers
            top_leaders = self.get_leaderboard(PerformanceMetric.TOTAL_RETURN, 5)

            return {
                'total_leaders': total_leaders,
                'total_followers': total_followers,
                'active_copy_trades': active_copy_trades,
                'total_aum': total_aum,
                'average_performance_score': round(avg_performance, 2),
                'average_followers_per_leader': round(avg_followers, 1),
                'top_leaders': top_leaders,
                'sync_active': self.sync_active
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}

# API para integração
def create_copy_trading_system():
    """Criar instância do sistema de copy trading"""
    return CopyTradingSystem()

if __name__ == "__main__":
    # Teste do sistema de copy trading
    copy_system = create_copy_trading_system()

    # Registrar leader
    leader_id = copy_system.register_leader_trader(
        username="crypto_master",
        display_name="Crypto Master",
        bio="Especialista em crypto trading com 5+ anos de experiência"
    )
    print(f"Leader registrado: {leader_id}")

    # Iniciar copy
    follower_id = copy_system.start_copying_leader(
        leader_id=leader_id,
        user_id="user123",
        allocation_amount=1000.0,
        risk_level="medium"
    )
    print(f"Follower iniciado: {follower_id}")

    # Simular trade do leader
    trade_data = {
        'id': 'trade_001',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'amount': 0.1,
        'price': 45000.0
    }

    copied_trades = copy_system.sync_trade_execution(leader_id, trade_data)
    print(f"Trades copiados: {len(copied_trades)}")

    # Leaderboard
    leaderboard = copy_system.get_leaderboard()
    print(f"Leaderboard: {len(leaderboard)} traders")

    # Estatísticas
    stats = copy_system.get_copy_trading_statistics()
    print(f"Estatísticas: {stats}")
