from flask import Blueprint, jsonify, request, send_file, render_template
from .services.trading_service import trading_system
from .services.backtesting_service import advanced_backtest
import os

api = Blueprint('api', __name__)

@api.route('/')
def dashboard():
    """Dashboard principal completo"""
    return render_template('index.html')

@api.route('/api/status')
def get_status():
    """Status completo do sistema"""
    return jsonify(trading_system.get_status())

@api.route('/api/trades')
def get_trades():
    """Obter lista de trades"""
    return jsonify({
        'trades': trading_system.get_trades(),
        'total': len(trading_system.get_trades())
    })

@api.route('/api/market_data/<path:pair>')
def get_market_data(pair):
    """Obter dados de mercado para gráficos"""
    try:
        pair = pair.replace('-', '/').replace('_', '/')
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 200))
        data = trading_system.get_market_data(pair, timeframe, limit)
        return jsonify({
            'pair': pair,
            'timeframe': timeframe,
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api.route('/api/indicators/<path:pair>')
def get_indicators(pair):
    """Obter indicadores técnicos para gráficos"""
    try:
        pair = pair.replace('-', '/').replace('_', '/')
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 200))
        indicators = trading_system.get_indicators(pair, timeframe, limit)
        return jsonify({
            'pair': pair,
            'timeframe': timeframe,
            'indicators': indicators
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api.route('/api/advanced-backtest', methods=['POST'])
def run_advanced_backtest():
    """Executar backtest avançado"""
    try:
        if not advanced_backtest:
            return jsonify({
                'success': False,
                'error': 'Motor de backtesting avançado não disponível'
            })

        data = request.get_json() or {}
        strategy_name = data.get('strategy', 'AdvancedEMA')
        pair = data.get('pair', 'BTC/USDT')
        timeframe = data.get('timeframe', '15m')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # Mapear estratégia para função
        strategy_map = {
            'AdvancedEMA': 'ema_crossover_strategy',
            'RSI_MeanReversion': 'rsi_mean_reversion_strategy',
            'MACD_Strategy': 'ema_crossover_strategy'
        }

        strategy_func_name = strategy_map.get(strategy_name, 'ema_crossover_strategy')

        # Executar backtest
        result = advanced_backtest.backtest_strategy(
            strategy_func_name, pair, start_date, end_date, timeframe, 10000.0
        )

        if result.get('success'):
            # Gerar gráfico se disponível
            chart_path = None
            if result.get('backtest_id'):
                chart_path = advanced_backtest.generate_tradingview_chart(
                    result['backtest_id']
                )

            return jsonify({
                'success': True,
                'results': result['metrics'],
                'chart_url': f'/backtest_chart/{result["backtest_id"]}' if chart_path else None
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro no backtest')
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api.route('/api/optimize', methods=['POST'])
def optimize_strategy():
    """Otimizar estratégia"""
    try:
        if not advanced_backtest:
            return jsonify({
                'success': False,
                'error': 'Motor de backtesting avançado não disponível'
            })

        data = request.get_json() or {}
        strategy_name = data.get('strategy', 'AdvancedEMA')
        pair = data.get('pair', 'BTC/USDT')
        timeframe = data.get('timeframe', '15m')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # Mapear estratégia para função
        strategy_map = {
            'AdvancedEMA': 'ema_crossover_strategy',
            'RSI_MeanReversion': 'rsi_mean_reversion_strategy'
        }

        strategy_func_name = strategy_map.get(strategy_name, 'ema_crossover_strategy')

        # Executar otimização
        results = advanced_backtest.optimize_strategy(
            strategy_func_name, pair, start_date, end_date, timeframe
        )

        if results:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhum resultado de otimização'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api.route('/api/manual-order', methods=['POST'])
def create_manual_order():
    """Criar ordem manual"""
    try:
        data = request.get_json() or {}
        pair = data.get('pair')
        side = data.get('side')
        amount = float(data.get('amount', 0))
        order_type = data.get('order_type', 'market')
        price = data.get('price')

        if not pair or not side or amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Parâmetros inválidos'
            })

        result = trading_system.create_manual_order(
            pair, side, amount, order_type, price
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api.route('/backtest_chart/<int:backtest_id>')
def get_backtest_chart(backtest_id):
    """Servir gráfico de backtest"""
    try:
        if advanced_backtest:
            chart_path = advanced_backtest.generate_tradingview_chart(backtest_id)
            if chart_path and os.path.exists(chart_path):
                return send_file(chart_path)
        return "Gráfico não encontrado", 404
    except Exception as e:
        return str(e), 500