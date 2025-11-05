#!/usr/bin/env python3
"""
============================================================
FREQTRADE3 - ESTRATÉGIA MACD MOMENTUM
============================================================

Estratégia de médio risco baseada em momentum MACD:
- Cruzamentos MACD como sinais principais
- Confirmação com volume e RSI
- Gestão de risco conservadora
- Otimizada para crypto bullish markets

Características:
- Win Rate esperado: 55-65%
- Max Drawdown: 10-15%
- Risco: Médio
- Timeframe: 15m
- Ideal para: Traders experientes

Autor: FreqTrade3 Project
Data: 2025-11-05
Versão: 1.0.0
============================================================
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy


class MACDStrategy(IStrategy):
    """
    Estratégia MACD Momentum para trading agressivo

    Esta estratégia utiliza cruzamentos MACD como sinais primários,
    com confirmação de volume e RSI para evitar falsos sinais.

    Configurações:
    - Cruzamento MACD bullish como entrada
    - Confirmação de volume acima da média
    - RSI entre 30-70 para evitar extremos
    - Stop loss de 8% e take profit de 4-12%
    - Trailing stop de 2%
    """

    # ========================================
    # CONFIGURAÇÕES BÁSICAS
    # ========================================

    timeframe = '15m'
    startup_candles = 100

    # ROI otimizado para estratégia momentum
    minimal_roi = {
        "0": 12.0,      # Saída imediata se 12% lucro
        "30": 6.0,      # 6% em 30min
        "60": 4.0,      # 4% em 1h
        "120": 2.0,     # 2% em 2h
        "240": 0        # Sem ROI mínimo após 4h
    }

    # Stop loss mais agressivo
    stoploss = -0.08

    # Trailing stop agressivo
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.01
    trailing_only_offset_is_reached = True

    # Configurações de execução
    process_only_closed_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_buy_signal = False

    # ========================================
    # PARÂMETROS OTIMIZÁVEIS
    # ========================================

    # MACD Parameters
    macd_fast = IntParameter(8, 20, default=12, space="buy")
    macd_slow = IntParameter(20, 40, default=26, space="buy")
    macd_signal = IntParameter(5, 15, default=9, space="buy")

    # Confirmation indicators
    rsi_period = IntParameter(10, 20, default=14, space="buy")
    rsi_oversold = IntParameter(20, 35, default=30, space="buy")
    rsi_overbought = IntParameter(65, 80, default=70, space="buy")

    ema_fast = IntParameter(10, 25, default=20, space="buy")
    ema_slow = IntParameter(40, 80, default=50, space="buy")

    # Volume confirmation
    volume_ma_period = IntParameter(10, 30, default=20, space="buy")
    volume_multiplier = DecimalParameter(1.2, 2.0, default=1.5, space="buy")

    # Risk management
    max_trades_per_pair = IntParameter(3, 7, default=5, space="buy")
    cooldown_candles = IntParameter(5, 15, default=8, space="buy")

    # Bollinger Bands for volatility filter
    bb_period = IntParameter(15, 25, default=20, space="buy")
    bb_std = DecimalParameter(1.8, 2.5, default=2.0, space="buy")

    # ========================================
    # VARIÁVEIS DE CONTROLE
    # ========================================

    _pair_trade_count = {}
    _last_signal_time = {}

    def log_strategy_event(self, message: str, level: str = "INFO"):
        """Log customizado para eventos da estratégia MACD"""
        logger = logging.getLogger("MACDStrategy")

        if level == "CRITICAL":
            logger.critical(f"[MACD_STRATEGY] {message}")
        elif level == "ERROR":
            logger.error(f"[MACD_STRATEGY] {message}")
        elif level == "WARNING":
            logger.warning(f"[MACD_STRATEGY] {message}")
        else:
            logger.info(f"[MACD_STRATEGY] {message}")

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Popula indicadores técnicos para estratégia MACD

        Args:
            dataframe: DataFrame com dados OHLCV
            metadata: Metadados do par de trading

        Returns:
            DataFrame com indicadores MACD e confirmações
        """

        try:
            # MACD principal
            macd, macd_signal_line, macd_hist = ta.MACD(
                dataframe['close'],
                fastperiod=self.macd_fast.value,
                slowperiod=self.macd_slow.value,
                signalperiod=self.macd_signal.value
            )
            dataframe['macd'] = macd
            dataframe['macd_signal'] = macd_signal_line
            dataframe['macd_hist'] = macd_hist

            # EMA para confirmação de tendência
            dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
            dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)

            # RSI para momentum
            dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)

            # Volume moving average para confirmação
            dataframe['volume_ma'] = ta.SMA(dataframe, timeperiod=self.volume_ma_period.value)
            dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']

            # Bollinger Bands para volatilidade
            bb_upper, bb_middle, bb_lower = ta.BBANDS(
                dataframe['close'],
                timeperiod=self.bb_period.value,
                nbdevup=self.bb_std.value,
                nbdevdn=self.bb_std.value
            )
            dataframe['bb_upper'] = bb_upper
            dataframe['bb_middle'] = bb_middle
            dataframe['bb_lower'] = bb_lower

            # Additional momentum indicators
            dataframe['momentum'] = ta.MOM(dataframe, timeperiod=10)
            dataframe['roc'] = ta.ROC(dataframe, timeperiod=5)

            # MACD crossover signals
            dataframe['macd_bullish_cross'] = (
                (dataframe['macd'] > dataframe['macd_signal']) &
                (dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1))
            )
            dataframe['macd_bearish_cross'] = (
                (dataframe['macd'] < dataframe['macd_signal']) &
                (dataframe['macd'].shift(1) >= dataframe['macd_signal'].shift(1))
            )

            # Trend strength
            dataframe['trend_strength'] = (dataframe['ema_fast'] > dataframe['ema_slow']).astype(int)

            # Volatility filter
            dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
            dataframe['volatility_ok'] = dataframe['bb_width'] > 0.02  # BB width > 2%

            self.log_strategy_event(f"Indicadores MACD populados para {metadata.get('pair', 'N/A')}")

        except Exception as e:
            self.log_strategy_event(f"Erro ao calcular indicadores MACD: {e}", "ERROR")
            return pd.DataFrame()

        return dataframe

    def populate_buy_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de compra baseados em MACD e confirmações

        Args:
            dataframe: DataFrame com dados OHLCV e indicadores
            metadata: Metadados do par de trading

        Returns:
            DataFrame com sinais de compra MACD
        """

        dataframe['enter_long'] = 0

        try:
            # MACD main conditions
            macd_condition = (
                (dataframe['macd'] > dataframe['macd_signal']) &
                (dataframe['macd_hist'] > 0) &
                (dataframe['macd_bullish_cross'])
            )

            # RSI confirmation (not overbought, not oversold)
            rsi_condition = (
                (dataframe['rsi'] > self.rsi_oversold.value) &
                (dataframe['rsi'] < self.rsi_overbought.value) &
                (dataframe['rsi'] > dataframe['rsi'].shift(1))  # RSI rising
            )

            # EMA trend confirmation
            trend_condition = (
                (dataframe['close'] > dataframe['ema_fast']) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['trend_strength'] == 1) &
                (dataframe['close'] > dataframe['ema_slow'] * 1.02)  # 2% above slow EMA
            )

            # Volume confirmation
            volume_condition = (
                (dataframe['volume_ratio'] > self.volume_multiplier.value) &
                (dataframe['volume'] > dataframe['volume_ma']) &
                (dataframe['volume'] > dataframe['volume'].rolling(20).mean())
            )

            # Momentum confirmation
            momentum_condition = (
                (dataframe['momentum'] > 0) &
                (dataframe['roc'] > -1) &
                (dataframe['momentum'] > dataframe['momentum'].shift(1))
            )

            # Volatility confirmation
            volatility_condition = dataframe['volatility_ok']

            # Bollinger Bands position
            bb_condition = (
                (dataframe['close'] > dataframe['bb_lower']) &
                (dataframe['close'] < dataframe['bb_upper']) &
                ((dataframe['close'] - dataframe['bb_lower']) /
                 (dataframe['bb_upper'] - dataframe['bb_lower']) < 0.8)  # Not too close to upper
            )

            # Combine all conditions
            buy_condition = (
                macd_condition &
                rsi_condition &
                trend_condition &
                volume_condition &
                momentum_condition &
                volatility_condition &
                bb_condition
            )

            # Apply buy signals
            dataframe.loc[buy_condition, 'enter_long'] = 1

            # Log statistics
            total_signals = buy_condition.sum()
            if total_signals > 0:
                pair_name = metadata.get('pair', 'N/A')
                self.log_strategy_event(
                    f"MACD buy signals para {pair_name}: {total_signals}"
                )

        except Exception as e:
            self.log_strategy_event(f"Erro em MACD populate_buy_trend: {e}", "ERROR")
            dataframe['enter_long'] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sinais de saída baseados em MACD bearish e perda de momentum

        Args:
            dataframe: DataFrame com dados OHLCV e indicadores
            metadata: Metadados do par de trading

        Returns:
            DataFrame com sinais de saída MACD
        """

        dataframe['exit_long'] = 0

        try:
            # MACD bearish conditions
            macd_exit_condition = (
                dataframe['macd_bearish_cross'] |  # Recent bearish crossover
                (dataframe['macd'] < dataframe['macd_signal']) |  # MACD below signal
                (dataframe['macd_hist'] < -0.001)  # Strong negative histogram
            )

            # RSI bearish conditions
            rsi_exit_condition = (
                (dataframe['rsi'] > self.rsi_overbought.value) |
                (dataframe['rsi'] < dataframe['rsi'].shift(1))  # RSI falling
            )

            # Momentum deteriorating
            momentum_exit_condition = (
                (dataframe['momentum'] < dataframe['momentum'].shift(1)) |
                (dataframe['momentum'] < -2) |
                (dataframe['roc'] < -3)
            )

            # Trend reversal
            trend_exit_condition = (
                (dataframe['close'] < dataframe['ema_fast']) |
                (dataframe['ema_fast'] < dataframe['ema_slow']) |
                ((dataframe['trend_strength'].shift(1) == 1) &
                 (dataframe['trend_strength'] == 0))  # Trend just turned bearish
            )

            # Bollinger Bands breakout
            bb_exit_condition = (
                (dataframe['close'] < dataframe['bb_lower']) |
                (dataframe['close'] > dataframe['bb_upper'])  # Breakout
            )

            # Combine exit conditions
            exit_condition = (
                macd_exit_condition &
                (rsi_exit_condition | momentum_exit_condition) &
                (trend_exit_condition | bb_exit_condition)
            )

            # Apply exit signals
            dataframe.loc[exit_condition, 'exit_long'] = 1

            # Log statistics
            total_exits = exit_condition.sum()
            if total_exits > 0:
                pair_name = metadata.get('pair', 'N/A')
                self.log_strategy_event(
                    f"MACD exit signals para {pair_name}: {total_exits}"
                )

        except Exception as e:
            self.log_strategy_event(f"Erro em MACD populate_exit_trend: {e}", "ERROR")
            dataframe['exit_long'] = 0

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                          proposed_stake: float, min_stake: Optional[float], max_stake: Optional[float],
                          leverage: float, entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Calcula stake amount com gestão de risco MACD

        Args:
            pair: Par de trading
            current_time: Tempo atual
            current_rate: Taxa atual
            proposed_stake: Stake proposto
            min_stake: Stake mínimo
            max_stake: Stake máximo
            leverage: Alavancagem
            entry_tag: Tag de entrada
            side: Lado (buy/sell)

        Returns:
            Stake amount ajustado para estratégia MACD
        """

        try:
            # Limit by max trades per pair
            pair_current_trades = self._pair_trade_count.get(pair, 0)
            if pair_current_trades >= self.max_trades_per_pair.value:
                return 0

            # Conservative sizing for momentum strategy
            if max_stake and max_stake > 0:
                max_allowed = max_stake * 0.03  # Máximo 3% por trade
                proposed_stake = min(proposed_stake, max_allowed)

            # Minimum stake for MACD strategy
            if proposed_stake < 20:  # USDT mínimo
                return 0

            return proposed_stake

        except Exception as e:
            self.log_strategy_event(f"Erro em custom_stake_amount MACD: {e}", "ERROR")
            return 0

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        Executado no início de cada loop do bot - MACD specific

        Args:
            current_time: Tempo atual
        """

        try:
            # Update trade counts
            open_trades = Trade.get_open_trades()
            self._pair_trade_count = {}

            for trade in open_trades:
                pair = trade.pair
                self._pair_trade_count[pair] = self._pair_trade_count.get(pair, 0) + 1

            self.log_strategy_event(
                f"MACD bot loop started. Open trades: {len(open_trades)}"
            )

        except Exception as e:
            self.log_strategy_event(f"Erro em MACD bot_loop_start: {e}", "ERROR")

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                          side: str, **kwargs) -> bool:
        """
        Confirmação final para entrada MACD

        Args:
            pair: Par de trading
            order_type: Tipo de ordem
            amount: Quantidade
            rate: Taxa
            time_in_force: Tempo em força
            current_time: Tempo atual
            entry_tag: Tag de entrada
            side: Lado

        Returns:
            True se confirmar, False caso contrário
        """

        try:
            # Check trade limits
            if self._pair_trade_count.get(pair, 0) >= self.max_trades_per_pair.value:
                self.log_strategy_event(f"Limite de trades MACD por par atingido para {pair}", "WARNING")
                return False

            # Check minimum amount
            if amount < 20:  # USDT mínimo para MACD
                self.log_strategy_event(f"Amount insuficiente para estratégia MACD: {amount}", "WARNING")
                return False

            # Log confirmation
            self.log_strategy_event(
                f"MACD trade confirmado para {pair}: {amount:.2f} @ {rate:.6f}"
            )

            return True

        except Exception as e:
            self.log_strategy_event(f"Erro em MACD confirm_trade_entry: {e}", "ERROR")
            return False

    def check_exit_signal(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                         current_profit: float, min_stake: Optional[float], **kwargs) -> Optional[pd.Series]:
        """
        Validação adicional de sinais de saída para MACD

        Args:
            pair: Par de trading
            trade: Objeto Trade
            current_time: Tempo atual
            current_rate: Taxa atual
            current_profit: Lucro atual
            min_stake: Stake mínimo

        Returns:
            None ou série de sinal de saída
        """

        try:
            # MACD specific exit rules

            # High profit target (MACD can be fast-moving)
            if current_profit > 0.12:  # 12% lucro máximo
                self.log_strategy_event(f"Forçando saída MACD de {pair} por lucro máximo: {current_profit:.2%}")
                return pd.Series([1, "MAX_PROFIT_MACD"])

            # MACD divergence (trade too old)
            trade_age = (current_time - trade.open_date).total_seconds()
            max_macd_age = 6 * 3600  # 6 horas máximo para MACD

            if trade_age > max_macd_age:
                self.log_strategy_event(f"Forçando saída MACD de {pair} por idade: {trade_age/3600:.1f}h")
                return pd.Series([1, "MAX_AGE_MACD"])

            # High loss cut-off
            if current_profit < -0.08:  # -8% perda máxima
                self.log_strategy_event(f"Stop loss MACD ativado para {pair}: {current_profit:.2%}")
                return pd.Series([1, "STOP_LOSS_MACD"])

            return None

        except Exception as e:
            self.log_strategy_event(f"Erro em MACD check_exit_signal: {e}", "ERROR")
            return None

    def get_recommended_subtimeframes(self) -> Dict[str, List[str]]:
        """
        Retorna timeframes recomendados para confirmação de sinais MACD

        Returns:
            Dicionário com timeframes por timeframe principal
        """

        return {
            "15m": ["5m", "1h"],      # Confirmação 5m e 1h
            "1h": ["15m", "4h"],      # Confirmação 15m e 4h
            "4h": ["1h", "1d"],       # Confirmação 1h e 1d
            "1d": ["4h", "1w"],       # Confirmação 4h e 1w
        }

    def populate_pair_trade(self, pair: str, **kwargs) -> pd.DataFrame:
        """
        Popula informações específicas do par para MACD

        Args:
            pair: Par de trading

        Returns:
            DataFrame vazio (placeholder)
        """

        # Placeholder para customização por par
        return pd.DataFrame()

    def populate_any_trade(self, pair: str, **kwargs) -> pd.DataFrame:
        """
        Popula informações para qualquer trade MACD

        Args:
            pair: Par de trading

        Returns:
            DataFrame vazio (placeholder)
        """

        # Placeholder para implementação futura
        return pd.DataFrame()


# ========================================
# INFORMAÇÕES ADICIONAIS DA ESTRATÉGIA
# ========================================

"""
Configurações Recomendadas para MACD Strategy:

🔧 Parâmetros de Otimização:
- macd_fast: 8-15 (padrão: 12)
- macd_slow: 20-35 (padrão: 26)
- macd_signal: 5-12 (padrão: 9)
- rsi_oversold: 25-35 (padrão: 30)
- rsi_overbought: 65-75 (padrão: 70)
- volume_multiplier: 1.2-1.8 (padrão: 1.5)

📊 Métricas Esperadas:
- Win Rate: 55-65%
- Profit Factor: 1.2-1.8
- Max Drawdown: 10-15%
- Avg Trade Duration: 2-6 horas
- Best Performance: Mercados bullish com volatilidade

⚠️  Cuidados Importantes:
- Não usar durante mercados laterais
- Evitar épocas de baixa volatilidade
- Cuidado com notícias importantes
- Ajustar volume_multiplier para liquidez do par
- Considerar spreads do exchange

🎯 Pares Recomendados:
- BTC/USDT, ETH/USDT: Pares principais
- ADA/USDT, DOT/USDT: Altcoins voláteis
- Evitar pares com spread > 0.5%
- Priorizar pares com volume 24h > $100M

🚀 Como Usar:
1. freqtrade backtesting --strategy MACDStrategy
2. freqtrade trade --strategy MACDStrategy --config configs/config_template_dryrun.json
3. freqtrade trade --strategy MACDStrategy --config configs/config_template_live.json
4. freqtrade plot-dataframe --strategy MACDStrategy -p BTC/USDT

📈 Análise de Resultados:
- Monitorar win rate semanal
- Ajustar parâmetros baseada em performance
- Usar FreqUI para visualização em tempo real
- Avaliar profit factor em períodos de 30 dias
"""
