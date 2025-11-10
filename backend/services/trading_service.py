from datetime import datetime
from ..database import get_trades_from_db, create_manual_order_in_db
from .exchange_manager import exchange_manager

class AdvancedTradingSystem:
    """Sistema de trading completo com todas as funcionalidades"""

    def __init__(self):
        self.pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT', 'SOL/USDT', 'DOT/USDT', 'LINK/USDT']
        self.timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        self.current_pair = 'BTC/USDT'
        self.timeframe = '15m'
        self.balance = 10000.0
        self.bot_running = False
        self.current_strategy = 'AdvancedEMA'
        self.start_time = datetime.now()
        self.market_data_cache = {}
        self.strategies = {}
        self.load_strategies()
        print("Advanced Trading System initialized")

    def load_strategies(self):
        """Carregar estratégias disponíveis"""
        self.strategies = {
            'AdvancedEMA': {
                'name': 'Advanced EMA Crossover',
                'description': 'EMA 12/26 com RSI filter',
            },
            'RSI_MeanReversion': {
                'name': 'RSI Mean Reversion',
                'description': 'Reversão à média com RSI',
            },
            'MACD_Strategy': {
                'name': 'MACD Trend Following',
                'description': 'Seguidor de tendência com MACD',
            }
        }

    def get_market_data(self, pair, timeframe, limit):
        """Obter dados de mercado da exchange"""
        cache_key = f"{pair}_{timeframe}_{limit}"
        if cache_key in self.market_data_cache:
            return self.market_data_cache[cache_key]

        ohlcv = exchange_manager.fetch_ohlcv(pair, timeframe, limit=limit)
        if not ohlcv:
            return []

        data = [
            {
                'timestamp': datetime.fromtimestamp(item[0] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'open': item[1],
                'high': item[2],
                'low': item[3],
                'close': item[4],
                'volume': item[5]
            }
            for item in ohlcv
        ]
        self.market_data_cache[cache_key] = data
        return data

    def get_indicators(self, pair, timeframe, limit):
        """Calcular indicadores técnicos avançados"""
        market_data = self.get_market_data(pair, timeframe, limit)
        if not market_data:
            return {}
        closes = [item['close'] for item in market_data]
        df = pd.DataFrame(closes, columns=['close'])
        indicators = {}
        indicators['rsi'] = df['close'].rolling(14).apply(lambda x: pd.Series(x).rsi()).iloc[-1]
        indicators['ema_12'] = df['close'].ewm(span=12, adjust=False).mean().iloc[-1]
        indicators['ema_26'] = df['close'].ewm(span=26, adjust=False).mean().iloc[-1]
        return indicators

    def get_trades(self, limit=50):
        """Obter trades da base de dados"""
        return get_trades_from_db(limit)

    def get_balance(self):
        """Obter saldo atual"""
        trades = self.get_trades()
        pnl = sum(t['pnl'] for t in trades if t['pnl'] and t['status'] == 'closed')
        return self.balance + pnl

    def get_status(self):
        """Status completo do sistema"""
        return {
            'bot_running': self.bot_running,
            'current_strategy': self.current_strategy,
            'balance': round(self.get_balance(), 2),
            'current_pair': self.current_pair,
            'timeframe': self.timeframe,
            'uptime': str(datetime.now() - self.start_time).split('.')[0],
            'trades_count': len(self.get_trades()),
            'status': 'ONLINE' if self.bot_running else 'STOPPED',
        }

    def create_manual_order(self, pair, side, amount, order_type='market', price=None):
        """Criar ordem manual"""
        order = exchange_manager.create_order(pair, order_type, side, amount, price)
        if order:
            trade_id, executed_at = create_manual_order_in_db(pair, side, amount, order_type, price, order['price'])
            if trade_id:
                return {'success': True, 'trade_id': trade_id}
        return {'success': False, 'error': 'Failed to create manual order'}

trading_system = AdvancedTradingSystem()