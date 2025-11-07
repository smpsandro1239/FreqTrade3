import sqlite3
import os
from datetime import datetime

DB_PATH = 'user_data/freqtrade3.db'

def init_database():
    """Inicializar base de dados com estrutura completa"""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                status TEXT DEFAULT 'open',
                strategy TEXT,
                signal_type TEXT,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                pnl REAL DEFAULT 0,
                pnl_pct REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                stop_loss REAL,
                take_profit REAL,
                reason TEXT,
                is_manual INTEGER DEFAULT 0
            )
        ''')
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
                chart_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manual_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL,
                order_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                executed_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("Advanced database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

def get_trades_from_db(limit=50):
    """Obter trades da base de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, pair, side, amount, entry_price, exit_price, status, strategy,
                   entry_time, exit_time, pnl, pnl_pct, is_manual, reason
            FROM trades
            ORDER BY entry_time DESC LIMIT ?
        """, (limit,))
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'id': row[0],
                'pair': row[1],
                'side': row[2].upper(),
                'amount': float(row[3]),
                'entry_price': float(row[4]) if row[4] else None,
                'exit_price': float(row[5]) if row[5] else None,
                'status': row[6],
                'strategy': row[7],
                'entry_time': row[8],
                'exit_time': row[9],
                'pnl': float(row[10]) if row[10] else None,
                'pnl_pct': float(row[11]) if row[11] else None,
                'is_manual': bool(row[12]),
                'reason': row[13]
            })
        conn.close()
        return trades
    except Exception as e:
        print(f"Erro ao obter trades: {e}")
        return []

def create_manual_order_in_db(pair, side, amount, order_type, price, exec_price):
    """Criar ordem manual na base de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        executed_at = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO manual_orders (pair, side, amount, price, order_type, status, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (pair, side, amount, exec_price, order_type, 'executed', executed_at))
        cursor.execute('''
            INSERT INTO trades (pair, side, amount, entry_price, status, strategy, signal_type,
                               entry_time, is_manual, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pair, side, amount, exec_price, 'open', 'Manual', 'manual',
              executed_at, 1, f'Manual {order_type} order'))
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id, executed_at
    except Exception as e:
        print(f"Erro ao criar ordem manual: {e}")
        return None, None