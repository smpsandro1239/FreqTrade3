def ema_crossover_strategy(data, params=None):
    """Estratégia de cruzamento de EMAs"""
    if len(data) < 50:
        return {}

    params = params or {}
    fast_period = params.get('ema_fast', 12)
    slow_period = params.get('ema_slow', 26)
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    current = data.iloc[-1]
    prev = data.iloc[-2]

    signals = {}

    # Verificar se EMAs existem
    if f'ema_{fast_period}' not in data.columns or f'ema_{slow_period}' not in data.columns:
        return signals

    fast_ema = current[f'ema_{fast_period}']
    slow_ema = current[f'ema_{slow_period}']
    prev_fast = prev[f'ema_{fast_period}']
    prev_slow = prev[f'ema_{slow_period}']
    rsi = current['rsi'] if 'rsi' in current else 50

    # Cruzamento de alta
    if (fast_ema > slow_ema and prev_fast <= prev_slow and
        rsi < rsi_overbought and current['Close'] > fast_ema):

        stop_loss = current['Close'] * (1 - params.get('stop_loss_pct', 0.02))
        take_profit = current['Close'] * (1 + params.get('take_profit_pct', 0.04))

        signals = {
            'entry_signal': 'long',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'EMA {fast_period}/{slow_period} bullish crossover + RSI {rsi:.1f}'
        }

    # Cruzamento de baixa
    elif (fast_ema < slow_ema and prev_fast >= prev_slow and
          rsi > rsi_oversold and current['Close'] < fast_ema):

        stop_loss = current['Close'] * (1 + params.get('stop_loss_pct', 0.02))
        take_profit = current['Close'] * (1 - params.get('take_profit_pct', 0.04))

        signals = {
            'entry_signal': 'short',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'EMA {fast_period}/{slow_period} bearish crossover + RSI {rsi:.1f}'
        }

    # Saída
    elif rsi > rsi_overbought or rsi < rsi_oversold:
        signals = {'exit_signal': True, 'reason': f'RSI extreme {rsi:.1f}'}

    return signals

def rsi_mean_reversion_strategy(data, params=None):
    """Estratégia de reversão à média com RSI"""
    if len(data) < 50:
        return {}

    params = params or {}
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    current = data.iloc[-1]
    rsi = current['rsi'] if 'rsi' in current else 50

    signals = {}

    # Oversold - comprar
    if rsi < rsi_oversold:
        stop_loss = current['Close'] * (1 - params.get('stop_loss_pct', 0.03))
        take_profit = current['Close'] * (1 + params.get('take_profit_pct', 0.06))

        signals = {
            'entry_signal': 'long',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'RSI oversold {rsi:.1f}'
        }

    # Overbought - vender
    elif rsi > rsi_overbought:
        stop_loss = current['Close'] * (1 + params.get('stop_loss_pct', 0.03))
        take_profit = current['Close'] * (1 - params.get('take_profit_pct', 0.06))

        signals = {
            'entry_signal': 'short',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': f'RSI overbought {rsi:.1f}'
        }

    # Saída na zona neutra
    elif 40 < rsi < 60:
        signals = {'exit_signal': True, 'reason': f'RSI neutral {rsi:.1f}'}

    return signals