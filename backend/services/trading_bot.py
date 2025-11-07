from .trading_service import trading_system
import time
from datetime import datetime
import numpy as np

class TradingBot:
    def __init__(self):
        self.bot_running = False

    def start(self):
        self.bot_running = True
        while self.bot_running:
            try:
                # Simular atividade de trading
                if np.random.random() < 0.1:  # 10% chance a cada 5s
                    pair = trading_system.current_pair
                    base_price = 98500 if 'BTC' in pair else 3250 if 'ETH' in pair else 200
                    price = base_price * np.random.uniform(0.98, 1.02)

                    # Simular trade
                    new_trade = {
                        'pair': pair,
                        'side': 'buy' if np.random.random() > 0.5 else 'sell',
                        'amount': round(np.random.uniform(0.01, 1.0), 4),
                        'entry_price': round(price, 2),
                        'status': 'open',
                        'strategy': trading_system.current_strategy,
                        'entry_time': datetime.now().isoformat(),
                        'is_manual': False,
                        'reason': 'Auto trading signal'
                    }

                    # Adicionar à lista local
                    trading_system.trades.insert(0, {
                        'id': len(trading_system.trades) + 1,
                        **new_trade,
                        'exit_price': None,
                        'pnl': None,
                        'pnl_pct': None
                    })

                time.sleep(5)
            except Exception as e:
                print(f"Erro no bot de trading: {e}")
                time.sleep(5)

    def stop(self):
        self.bot_running = False

trading_bot = TradingBot()