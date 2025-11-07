from flask_socketio import emit
from .app import socketio
from .services.trading_service import trading_system
from .services.trading_bot import trading_bot
from datetime import datetime
import time
import threading

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado ao FreqTrade3 Complete')
    emit('status', {'data': 'Conectado ao FreqTrade3 Complete - Sistema Superior'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Cliente desconectado')

@socketio.on('start_bot')
def handle_start_bot(data):
    trading_system.current_strategy = data.get('strategy', 'AdvancedEMA')
    trading_system.current_pair = data.get('pair', 'BTC/USDT')
    trading_system.timeframe = data.get('timeframe', '15m')
    trading_bot.start()
    emit('status', trading_system.get_status(), broadcast=True)

@socketio.on('stop_bot')
def handle_stop_bot():
    trading_bot.stop()
    emit('status', trading_system.get_status(), broadcast=True)

def update_data():
    """Atualizar dados a cada 5 segundos"""
    while True:
        try:
            socketio.emit('data_update', {
                'status': trading_system.get_status(),
                'timestamp': datetime.now().isoformat()
            })
            time.sleep(5)
        except Exception as e:
            print(f"Erro na atualização: {e}")
            time.sleep(5)

def start_update_thread():
    update_thread = threading.Thread(target=update_data)
    update_thread.daemon = True
    update_thread.start()