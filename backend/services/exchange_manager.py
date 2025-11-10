import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

class ExchangeManager:
    """
    Gerencia a comunicação com as exchanges de criptomoedas usando ccxt.
    """
    def __init__(self, exchange_id='binance'):
        self.exchange_id = exchange_id
        self.exchange = self._init_exchange()

    def _init_exchange(self):
        """
        Inicializa a instância da exchange com as chaves de API.
        """
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            exchange = exchange_class({
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_API_SECRET'),
                'options': {
                    'defaultType': 'spot',
                },
            })
            # Habilitar o modo de teste (sandbox) se as chaves forem para o ambiente de teste
            if os.getenv('EXCHANGE_SANDBOX_MODE') == 'true':
                exchange.set_sandbox_mode(True)
            return exchange
        except (AttributeError, KeyError) as e:
            print(f"Erro ao inicializar a exchange {self.exchange_id}: {e}")
            return None

    def fetch_ohlcv(self, symbol, timeframe='15m', since=None, limit=100):
        """
        Busca dados de velas (OHLCV) para um determinado símbolo.
        """
        if not self.exchange:
            return []
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        except ccxt.Error as e:
            print(f"Erro ao buscar dados OHLCV para {symbol}: {e}")
            return []

    def create_order(self, symbol, order_type, side, amount, price=None):
        """
        Cria uma ordem de compra ou venda.
        """
        if not self.exchange:
            return None
        try:
            if order_type == 'limit' and price is None:
                raise ValueError("O preço é necessário para ordens do tipo 'limit'")
            return self.exchange.create_order(symbol, order_type, side, amount, price)
        except ccxt.Error as e:
            print(f"Erro ao criar ordem para {symbol}: {e}")
            return None

    def get_balance(self):
        """
        Busca o saldo da conta na exchange.
        """
        if not self.exchange:
            return {}
        try:
            return self.exchange.fetch_balance()
        except ccxt.Error as e:
            print(f"Erro ao buscar saldo: {e}")
            return {}

# Instância global do gerenciador da exchange
exchange_manager = ExchangeManager()