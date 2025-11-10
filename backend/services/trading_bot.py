from .trading_service import trading_system
from .exchange_manager import exchange_manager
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
                # Lógica de decisão do bot
                if np.random.random() < 0.1:  # 10% de chance a cada 5s de criar uma ordem
                    pair = trading_system.current_pair
                    side = 'buy' if np.random.random() > 0.5 else 'sell'
                    amount = round(np.random.uniform(0.01, 0.1), 4)

                    # Criar ordem na exchange
                    order = exchange_manager.create_order(pair, 'market', side, amount)

                    if order:
                        print(f"Ordem criada: {order}")
                    else:
                        print("Falha ao criar ordem.")

                time.sleep(5)
            except Exception as e:
                print(f"Erro no bot de trading: {e}")
                time.sleep(5)

    def stop(self):
        self.bot_running = False

trading_bot = TradingBot()