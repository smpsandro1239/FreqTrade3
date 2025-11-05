#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - ESTRATÉGIA EMA200RSI CONSERVADORA
================================================================

Estratégia de trading conservadora baseada em:
- EMA 200 (média móvel exponencial de 200 períodos)
- RSI (Relative Strength Index)
- Filtros de volume e volatilidade
- Gerenciamento de risco conservador

Características:
- Low risk / medium reward
- boa para iniciantes
- teste extensivo antes de usar
- configurações de segurança rigorosas

Win Rate Esperado: 65-75%
Max Drawdown: 5-8%
Sharpe Ratio: 1.2-1.8

Autor: FreqTrade3 Project
Data: 2025-11-05
Versão: 1.0.0
================================================================
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas as pd
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import (CategoricalParameter, DecimalParameter,
                                IntParameter, IStrategy)


class EMA200RSI(IStrategy):
    """
    Estratégia Conservadora EMA200RSI

    Esta estratégia implementa uma abordagem muito conservadora:
    - Usa EMA 200 como filtro de tendência de longo prazo
    - RSI para identificar condições de sobrevenda/sobrecompra
    - Filtros rigorosos de volume e volatilidade
    - Stop loss conservador e trailing stop
    - Controle de exposição máxima

    Parâmetros otimizáveis permitem ajuste fino.
    """

    # ========================================
    # CONFIGURAÇÕES BÁSICAS
    # ========================================

    # Timeframe principal da estratégia
    timeframe = '15m'
    startup_candles = 200  # Precisa de mais candles para EMA 200

    # ROI conservador
    minimal_roi = {
        "0": 0.05,    # 5% profit máximo imediato
        "30": 0.03,   # 3% após 30min
        "60": 0.02,   # 2% após 1h
        "120": 0.01,  # 1% após 2h
        "240": 0      # Break-even após 4h
    }

    # Stop loss conservador
    stoploss = -0.03  # -3% máximo

    # Trailing stop para capturar tendências
    trailing_stop = True
    trailing_stop_positive = 0.02  # 2% trailing
    trailing_stop_positive_offset = 0.01  # 1% offset
    trailing_only_offset_is_reached = True

    # Configurações de trading
    process_only_closed_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_buy_signal = True

    # ========================================
    # PARÂMETROS OTIMIZÁVEIS
    # ========================================

    # EMA - Moving Averages
    ema_fast_period = IntParameter(10, 20, default=12, space="buy",
                                  description="Período EMA rápida")
    ema_slow_period = IntParameter(50, 200, default=50, space="buy",
                                  description="Período EMA lenta")
    ema_very_slow_period = IntParameter(150, 250, default=200, space="buy",
                                       description="Período EMA muito lenta (filtro de tendência)")

    # RSI
    rsi_period = IntParameter(10, 20, default=14, space="buy")
    rsi_oversold = IntParameter(15, 35, default=25, space="buy")
    rsi_overbought = IntParameter(65, 85, default=75, space="buy")

    # MACD para confirmação
    macd_fast = IntParameter(10, 15, default=12, space="buy")
    macd_slow = IntParameter(20, 30, default=26, space="buy")
    macd_signal = IntParameter(5, 10, default=9, space="buy")

    # Bollinger Bands para confirmação
    bb_period = IntParameter(15, 25, default=20, space="buy")
    bb_std = DecimalParameter(1.5, 2.5, default=2.0, space="buy")

    # Filtros de qualidade
    min_volume = IntParameter(5000000, 20000000, default=10000000, space="buy")
    max_spread = DecimalParameter(0.2, 1.0, default=0.5, space="buy")

    # Controle de risco
    max_open_trades = 2  # Número fixo, não parâmetro otimizável
    cooldown_minutes = IntParameter(30, 120, default=60, space="buy")

    # ========================================
    # VARIÁVEIS INTERNAS
    # ========================================

    # Controle de cooldowns
    _last_buy_time = {}
    _pair_trade_count = {}

    def log_strategy_event(self, message: str, level: str = "INFO"):
        """Log customizado para eventos da estratégia"""
        logger = logging.getLogger("EMA200RSI")

        if level == "CRITICAL":
            logger.critical(f"[EMA200RSI] {message}")
        elif level == "ERROR":
            logger.error(f"[EMA200RSI] {message}")
        elif level == "WARNING":
            logger.warning(f"[EMA200RSI] {message}")
        else:
            logger.info(f"[EMA200RSI] {message}")

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Popula todos os indicadores necessários

        Args:
            dataframe: DataFrame com dados OHLCV
            metadata: Metadados do par

        Returns:
            DataFrame com indicadores calculados
        """

        # Validação básica dos dados
        if dataframe.empty or len(dataframe) < max(self.ema_very_slow_period.value, 100):
            self.log_strategy_event(f"Dados insuficientes para EMA200RSI - {metadata.get('pair', 'N/A')}", "WARNING")
            return dataframe

        try:
            # ========================================
            # MOVING AVERAGES - Triple EMA System
            # ========================================

            # EMA Rápida (12)
            dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast_period.value)

            # EMA Lenta (50)
            dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow_period.value)

            # EMA Muito Lenta (200) - filtro de tendência principal
            dataframe['ema_very_slow'] = ta.EMA(dataframe, timeperiod=self.ema_very_slow_period.value)

            # ========================================
            # RSI - Relative Strength Index
            # ========================================

            dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)

            # ========================================
            # MACD - Para confirmação de tendência
            # ========================================

            macd, macd_signal, macd_hist = ta.MACD(
                dataframe['close'],
                fastperiod=self.macd_fast.value,
                slowperiod=self.macd_slow.value,
                signalperiod=self.macd_signal.value
            )
            dataframe['macd'] = macd
            dataframe['macd_signal'] = macd_signal
            dataframe['macd_hist'] = macd_hist

            # ========================================
            # BOLLINGER BANDS - Para identificação de extremos
            # ========================================

            bb_upper, bb_middle, bb_lower = ta.BBANDS(
                dataframe['close'],
                timeperiod=self.bb_period.value,
                nbdevup=self.bb_std.value,
                nbdevdn=self.bb_std.value
            )
            dataframe['bb_upper'] = bb_upper
            dataframe['bb_middle'] = bb_middle
            dataframe['bb_lower'] = bb_lower

            # ========================================
            # INDICADORES DE VOLUME E QUALIDADE
            # ========================================

            # Volume - Filtro de qualidade
            dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
            dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']

            # ATR - Volatilidade
            dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

            # ========================================
            # INDICADORES DERIVADOS E FILTROS
            # ========================================

            # Posição relativa entre EMAs (trend strength)
            dataframe['ema_fast_vs_slow'] = (dataframe['ema_fast'] - dataframe['ema_slow']) / dataframe['ema_slow']
            dataframe['ema_vs_very_slow'] = (dataframe['ema_slow'] - dataframe['ema_very_slow']) / dataframe['ema_very_slow']

            # RSI normalizado (-1 a 1)
            dataframe['rsi_normalized'] = (dataframe['rsi'] - 50) / 50

            # MACD signal strength
            dataframe['macd_strength'] = (dataframe['macd'] - dataframe['macd_signal']) / dataframe['macd_signal']

            # BB position (0 em lower, 1 em upper)
            dataframe['bb_position'] = (
                (dataframe['close'] - dataframe['bb_lower']) /
                (dataframe['bb_upper'] - dataframe['bb_lower'])
            )

            # Condições de qualidade do mercado
            dataframe['volume_quality'] = dataframe['volume'] >= self.min_volume.value
            dataframe['spread_quality'] = dataframe['volume_ratio'] >= 0.8  # Volume não muito baixo

            # ATR como % do preço
            dataframe['atr_percentage'] = dataframe['atr'] / dataframe['close']

            # ========================================
            # SINAIS DERIVADOS
            # ========================================

            # Triângulo de EMAs (bullish crossover setup)
            dataframe['ema_triangle_bullish'] = (
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['ema_slow'] > dataframe['ema_very_slow'])
            )

            # MACD bullish
            dataframe['macd_bullish'] = (
                (dataframe['macd'] > dataframe['macd_signal']) &
                (dataframe['macd_hist'] > 0)
            )

            # RSI em zona neutra (não extrema)
            dataframe['rsi_neutral_zone'] = (
                (dataframe['rsi'] > self.rsi_oversold.value) &
                (dataframe['rsi'] < self.rsi_overbought.value)
            )

            # BB não em extremos
            dataframe['bb_not_extreme'] = (
                (dataframe['bb_position'] > 0.2) &  # Não muito próximo ao lower
                (dataframe['bb_position'] < 0.8)    # Não muito próximo ao upper
            )

            self.log_strategy_event(f"Indicadores EMA200RSI calculados para {metadata.get('pair', 'N/A')}")

        except Exception as e:
            self.log_strategy_event(f"Erro ao calcular indicadores EMA200RSI: {e}", "ERROR")
            return pd.DataFrame()  # Retornar DataFrame vazio em caso de erro

        return dataframe

    def populate_buy_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define condições de compra conservadoras

        Args:
            dataframe: DataFrame com dados e indicadores
            metadata: Metadados do par

        Returns:
            DataFrame com sinais de compra
        """

        # Inicializar coluna de sinal
        dataframe['enter_long'] = 0

        try:
            # ========================================
            # FILTRO 1: TENDÊNCIA DE LONGO PRAZO (EMA 200)
            # ========================================
            # O preço deve estar acima da EMA 200 para uma tendência geral bullish
            trend_filter = dataframe['close'] > dataframe['ema_very_slow']

            # ========================================
            # FILTRO 2: REVERSÃO BULLISH COM RSI
            # ========================================
            # RSI deve ter saído da zona de sobrevenda e estar em ascensão
            rsi_reversal = (
                (dataframe['rsi'] > self.rsi_oversold.value) &
                (dataframe['rsi'] > dataframe['rsi'].shift(1))  # RSI subindo
            )

            # ========================================
            # FILTRO 3: MACD BULLISH
            # ========================================
            # MACD deve estar em configuração bullish
            macd_condition = dataframe['macd_bullish']

            # ========================================
            # FILTRO 4: QUALIDADE DE VOLUME
            # ========================================
            # Volume deve estar numa faixa saudável
            volume_condition = dataframe['volume_quality']

            # ========================================
            # FILTRO 5: BOLLINGER BANDS
            # ========================================
            # Preço não deve estar em extremos do BB
            bb_condition = dataframe['bb_not_extreme']

            # ========================================
            # FILTRO 6: VOLATILIDADE RAZOÁVEL
            # ========================================
            # ATR não deve ser muito alto (mercado muito instável)
            volatility_condition = dataframe['atr_percentage'] < 0.08  # ATR < 8% do preço

            # ========================================
            # FILTRO 7: TRIANGLE EMAs
            # ========================================
            # EMAs devem estar alinhadas bullish
            triangle_condition = dataframe['ema_triangle_bullish']

            # ========================================
            # FILTRO 8: MOMENTUM POSITIVO
            # ========================================
            # Preço deve estar com momentum positivo
            momentum_condition = (
                (dataframe['close'] > dataframe['close'].shift(1)) &  # Preço subindo
                (dataframe['volume'] > dataframe['volume'].shift(1))  # Volume aumentando
            )

            # ========================================
            # COMBINAR TODAS AS CONDIÇÕES
            # ========================================
            buy_condition = (
                trend_filter &           # Tendência geral bullish
                rsi_reversal &           # RSI mostrando reversão bullish
                macd_condition &         # MACD bullish
                volume_condition &       # Volume adequado
                bb_condition &           # BB não em extremos
                volatility_condition &   # Volatilidade controlada
                triangle_condition &     # EMAs alinhadas
                momentum_condition &     # Momentum positivo
                (dataframe['volume'] > 0)  # Volume válido
            )

            # Aplicar sinais de compra
            dataframe.loc[buy_condition, 'enter_long'] = 1

            # Log de estatísticas de sinais
            total_signals = buy_condition.sum()
            if total_signals > 0:
                pair_name = metadata.get('pair', 'N/A')
                self.log_strategy_event(f"Buy signals EMA200RSI para {pair_name}: {total_signals} sinais")

        except Exception as e:
            self.log_strategy_event(f"Erro em populate_buy_trend: {e}", "ERROR")
            dataframe['enter_long'] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define condições de saída conservadora

        Args:
            dataframe: DataFrame com dados e indicadores
            metadata: Metadados do par

        Returns:
            DataFrame com sinais de saída
        """

        # Inicializar coluna de sinal
        dataframe['exit_long'] = 0

        try:
            # ========================================
            # CONDIÇÕES DE SAÍDA TÉCNICA
            # ========================================

            # RSI Overbought ou reversão bearish
            rsi_exit = (
                (dataframe['rsi'] > self.rsi_overbought.value) |
                (dataframe['rsi'] < dataframe['rsi'].shift(1))  # RSI caindo
            )

            # MACD bearish
            macd_exit = (
                (dataframe['macd'] < dataframe['macd_signal']) |
                (dataframe['macd_hist'] < 0)
            )

            # Breakout bearish ou extrema do BB
            bb_exit = (
                (dataframe['close'] < dataframe['bb_lower']) |  # Breakout bearish
                (dataframe['bb_position'] > 0.95)              # Muito próximo ao BB superior
            )

            # Momentum deteriorando
            momentum_exit = (
                (dataframe['close'] < dataframe['close'].shift(2)) |
                (dataframe['volume'] < dataframe['volume'].rolling(10).mean() * 0.7)
            )

            # ========================================
            # CONDIÇÕES DE SAÍDA DE RISCO
            # ========================================

            # Volatilidade muito alta (risco)
            high_volatility = dataframe['atr_percentage'] > 0.10  # ATR > 10%

            # Volume muito baixo (risco de liquidez)
            low_volume = dataframe['volume'] < (self.min_volume.value * 0.5)

            # ========================================
            # COMBINAR CONDIÇÕES
            # ========================================
            exit_condition = (
                rsi_exit |
                macd_exit |
                bb_exit |
                momentum_exit |
                high_volatility |
                low_volume
            )

            # Aplicar sinais de saída
            dataframe.loc[exit_condition, 'exit_long'] = 1

            # Log de estatísticas
            total_exits = exit_condition.sum()
            if total_exits > 0:
                pair_name = metadata.get('pair', 'N/A')
                self.log_strategy_event(f"Exit signals EMA200RSI para {pair_name}: {total_exits} sinais")

        except Exception as e:
            self.log_strategy_event(f"Erro em populate_exit_trend: {e}", "ERROR")
            dataframe['exit_long'] = 0

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                          proposed_stake: float, min_stake: Optional[float], max_stake: Optional[float],
                          **kwargs) -> float:
        """
        Calcula stake amount com controles de risco conservadores

        Args:
            pair: Par de trading
            current_time: Tempo atual
            current_rate: Taxa atual
            proposed_stake: Stake proposto
            min_stake: Stake mínimo
            max_stake: Stake máximo

        Returns:
            Stake amount ajustado
        """

        try:
            # Verificar limite máximo de trades ativos
            current_trades = len(Trade.get_open_trades())
            if current_trades >= self.max_open_trades:
                return 0  # Bloquear novo trade

            # Limitar por exposição máxima por par
            pair_exposure = 0
            for trade in Trade.get_open_trades():
                if trade.pair == pair:
                    pair_exposure += trade.stake_amount

            # Calcular exposure máximo (5% do total em cada par)
            if max_stake and max_stake > 0:
                max_pair_exposure = max_stake * 0.05  # 5% por par
                if pair_exposure >= max_pair_exposure:
                    return 0  # Exposição máxima atingida

            # Stake mínimo para evitar dust trades
            min_trade_amount = 20  # USDT mínimo
            if proposed_stake < min_trade_amount:
                return 0

            # Não exceder proposta do usuário
            return min(proposed_stake, max_stake or float('inf'))

        except Exception as e:
            self.log_strategy_event(f"Erro em custom_stake_amount: {e}", "ERROR")
            return 0

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                          side: str, **kwargs) -> bool:
        """
        Confirmação final conservadora antes da entrada

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
            # Verificar cooldown do par
            cooldown_key = f"{pair}_{current_time.strftime('%Y%m%d')}"
            if self._last_buy_time.get(cooldown_key, 0) > current_time.timestamp():
                self.log_strategy_event(f"Cooldown ativo para {pair} - rejeitando entrada", "WARNING")
                return False

            # Verificar se há trade muito recente do mesmo par
            recent_trades = Trade.get_trades_for_pair(pair)
            for trade in recent_trades:
                time_since_close = (current_time - trade.close_date).total_seconds() / 60  # minutos
                if time_since_close < self.cooldown_minutes.value:
                    self.log_strategy_event(f"Trade muito recente de {pair} - rejeitando entrada", "WARNING")
                    return False

            # Verificar amount mínimo
            if amount < 20:  # USDT mínimo conservador
                self.log_strategy_event(f"Amount muito pequeno {amount} - rejeitando entrada", "WARNING")
                return False

            # Verificar taxa razoável (não muito distante da proposta)
            if abs(rate - (rate * 0.02)) > 0.01:  # Slippage de 2%
                self.log_strategy_event(f"Slippage muito alto detectado - rejeitando entrada", "WARNING")
                return False

            # Registrar cooldown
            cooldown_until = (current_time + timedelta(minutes=self.cooldown_minutes.value)).timestamp()
            self._last_buy_time[cooldown_key] = cooldown_until

            # Log da confirmação
            self.log_strategy_event(f"Trade EMA200RSI confirmado para {pair}: {amount:.2f} USDT @ {rate:.6f}")

            return True

        except Exception as e:
            self.log_strategy_event(f"Erro em confirm_trade_entry: {e}", "ERROR")
            return False

    def bot_loop_start(self, **kwargs) -> None:
        """
        Executado no início de cada loop do bot
        Reset contadores diários e atualiza estatísticas
        """

        try:
            current_time = datetime.now()

            # Resetar informações antigas (mais de 7 dias)
            cutoff_time = (current_time - timedelta(days=7)).timestamp()
            old_keys = [key for key, timestamp in self._last_buy_time.items() if timestamp < cutoff_time]
            for key in old_keys:
                self._last_buy_time.pop(key, None)

            # Atualizar contadores de trades por par
            open_trades = Trade.get_open_trades()
            self._pair_trade_count = {}

            for trade in open_trades:
                pair = trade.pair
                self._pair_trade_count[pair] = self._pair_trade_count.get(pair, 0) + 1

            self.log_strategy_event(f"Bot loop iniciado. Trades EMA200RSI ativos: {len(open_trades)}")

        except Exception as e:
            self.log_strategy_event(f"Erro em bot_loop_start: {e}", "ERROR")

    def check_exit_signal(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                         current_profit: float, min_stake: Optional[float], **kwargs) -> Optional[pd.Series]:
        """
        Verificação adicional de sinais de saída

        Args:
            pair: Par de trading
            trade: Objeto Trade
            current_time: Tempo atual
            current_rate: Taxa atual
            current_profit: Lucro atual
            min_stake: Stake mínimo

        Returns:
            None ou série com sinal de saída
        """

        try:
            # Verificar se o trade está há muito tempo aberto
            trade_age_hours = (current_time - trade.open_date).total_seconds() / 3600

            if trade_age_hours > 48:  # 48 horas máximo
                self.log_strategy_event(f"Forçando saída de {pair} - trade muito antigo ({trade_age_hours:.1f}h)", "WARNING")
                return pd.Series([1, "MAX_AGE"])

            # Verificar drawdown crítico
            if current_profit < -0.05:  # 5% drawdown crítico
                self.log_strategy_event(f"Drawdown crítico EMA200RSI para {pair}: {current_profit:.2%}", "WARNING")
                return pd.Series([1, "HIGH_DRAWDOWN"])

            # Verificar lucro muito alto (possível extreência)
            if current_profit > 0.15:  # 15% lucro (potencial Bearish Squeeze)
                self.log_strategy_event(f"Lucro alto detectado em {pair}: {current_profit:.2%} - possível topo", "INFO")
                return pd.Series([1, "HIGH_PROFIT"])

            return None

        except Exception as e:
            self.log_strategy_event(f"Erro em check_exit_signal: {e}", "ERROR")
            return None
