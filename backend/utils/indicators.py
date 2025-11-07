import ta

def add_technical_indicators(df):
    """Adicionar indicadores técnicos avançados"""
    try:
        df['ema_12'] = ta.trend.ema_indicator(df['Close'], window=12)
        df['ema_26'] = ta.trend.ema_indicator(df['Close'], window=26)
        df['ema_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['ema_200'] = ta.trend.ema_indicator(df['Close'], window=200)
        df['sma_20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['macd'] = ta.trend.macd(df['Close'])
        df['macd_signal'] = ta.trend.macd_signal(df['Close'])
        df['macd_histogram'] = ta.trend.macd_diff(df['Close'])
        df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
        bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        return df
    except Exception as e:
        print(f"Error adding indicators: {e}")
        return df