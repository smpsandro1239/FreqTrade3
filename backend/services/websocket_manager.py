import asyncio
import json
import websockets
from ..app import socketio

class WebSocketManager:
    """
    Gerencia a conexão WebSocket com a exchange para receber dados em tempo real.
    """
    def __init__(self, symbol='btcusdt'):
        self.symbol = symbol
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_1m"

    async def listen(self):
        """
        Conecta-se ao WebSocket e começa a escutar por mensagens.
        """
        try:
            async with websockets.connect(self.ws_url) as websocket:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    kline = data['k']

                    # Formata a vela para a Lightweight Charts
                    formatted_kline = {
                        "time": int(kline['t'] / 1000),
                        "open": float(kline['o']),
                        "high": float(kline['h']),
                        "low": float(kline['l']),
                        "close": float(kline['c']),
                        "volume": float(kline['v'])
                    }

                    # Emite a vela para o frontend
                    socketio.emit('kline_update', formatted_kline)

        except Exception as e:
            print(f"Erro na conexão WebSocket: {e}")

def start_websocket_listener():
    """
    Inicia o listener do WebSocket em uma thread separada.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ws_manager = WebSocketManager()
    loop.run_until_complete(ws_manager.listen())

# Iniciar o listener do WebSocket em uma thread separada
import threading
ws_thread = threading.Thread(target=start_websocket_listener, daemon=True)
ws_thread.start()