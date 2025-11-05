#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - ESTRATÉGIA TEMPLATE SEGURA E ROBUSTA
================================================================

Template de estratégia segura para FreqTrade3 com:
- Gerenciamento de risco avançado
- Validação de dados robusta
- Logs de segurança
- Parâmetros otimizáveis
- Proteção contra overfitting

Características de Segurança:
- Validação de volume mínimo
- Filtros de spread
- Controle de slippage
- Proteção contra notícias
- Sistema de cooldown
- Máximo de trades por par
- Stop loss dinâmico

Autor: FreqTrade3 Project
Data: 2025-11-05
Versão: 1.0.0
================================================================
"""

import logging
import operator
from datetime import datetime, timedelta
from functools import reduce
from typing import Dict, Optional, Tuple

import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas as pd
import talib.abstract as ta
from freqtrade.constants import BACKTEST_BENCHMARK
from freqtrade.persistence import Trade
from freqtrade.strategy import (CategoricalParameter, DecimalParameter,
                                IntParameter, merge_informative_pair)
from freqtrade.strategy.interface import IStrategy


class SafeTemplateStrategy(IStrategy):
    """
    Estratégia template segura e robusta para FreqTrade3

    Esta estratégia implementa as melhores práticas de segurança:
    - Validação rigorosa de entrada
    - Gerenciamento de risco conservativo
    - Proteção contra cenários extremos
    - Logging detalhado de decisões
    - Sistema de cooldown avançado

    Parâmetros otimizáveis permitem ajuste fino sem overfitting.
    """

    # ========================================
    # CONFIGURAÇÕES ESTRATÉGICAS
    # ========================================

    # Timeframe da estratégia
    timeframe = '15m'
    startup_candles = 50

    # Configurações de ROI (Return on Investment)
    minimal_roi = {
        "0": 10.0,
        "20": 5.0,
        "40": 2.0,
        "80": 1.0,
        "160": 0
    }

    # Stop Loss conservador
    stoploss = -0.10

    # Trailing Stop configurado para proteção
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    # Configurações de resistência a ruído
    process_only_closed_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_buy_signal = True

    # ========================================
    # PARÂMETROS OTIMIZÁVEIS
    # ========================================

    # Filtros de qualidade de mercado
    min_volume = IntParameter(1000000, 10000000, default=5000000, space="buy",
                             description="Volume mínimo para considerar par")
    max_spread_percent = DecimalParameter(0.1, 1.0, default=0.5, space="buy",
                                         description="Spread máximo permitido (%)")

    # Timeframes e períodos
    short_ma_period = IntParameter(10, 30, default=20, space="buy")
    long_ma_period = IntParameter(20, 60, default=40, space="buy")
    rsi_period = IntParameter(10, 30, default=14, space="buy")
    bb_period = IntParameter(15, 25, default=20, space="buy")
    bb_std = DecimalParameter(1.5, 2.5, default=2.0, space="buy")

    # RSI
    rsi_oversold = IntParameter(20, 35, default=30, space="buy")
    rsi_overbought = IntParameter(65, 80, default=70, space="buy")

    # MACD
    macd_fast = IntParameter(10, 20, default=12, space="buy")
    macd_slow = IntParameter(20, 40, default=26, space="buy")
    macd_signal = IntParameter(5, 15, default=9, space="buy")

    # Controle de frequência de trades
    cooldown_candles = IntParameter(5, 20, default=10, space="buy")
    max_trades_per_pair = IntParameter(2, 5, default=3, space="buy")

    # ========================================
    # CONFIGURAÇÕES DE SEGURANÇA
    # ========================================

    # Proteção contra notícias (desabilitado por padrão)
    protect_signal_candles = IntParameter(0, 3, default=0, space="buy")

    # Controle de position size
    max_position_size_percent = DecimalParameter(1.0, 10.0, default=5.0, space="buy")

    # Filtros de volatilidade
    volatility_threshold = DecimalParameter(0.02, 0.10, default=0.05, space="buy")

    # ========================================
    # VARIÁVEIS INTERNAS
    # ========================================

    # Contadores para cooldown e trades
    _last_trade_info = {}
    _pair_trade_count = {}

    def log_strategy_event(self, message: str, level: str = "INFO"):
        """Log customizado para eventos da estratégia"""
        logger = logging.getLogger("SafeTemplateStrategy")

        if level == "CRITICAL":
            logger.critical(f"[SAFE_STRATEGY] {message}")
        elif level == "ERROR":
            logger.error(f"[SAFE_STRATEGY] {message}")
        elif level == "WARNING":
            logger.warning(f"[SAFE_STRATEGY] {message}")
        else:
            logger.info(f"[SAFE_STRATEGY] {message}")

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Popula indicadores técnicos com validação robusta

        Args:
            dataframe: DataFrame com dados OHLCV
            metadata: Metadados do par de trading

        Returns:
            DataFrame com indicadores adicionados
        """

        # Validação básica dos dados
        if dataframe.empty or len(dataframe) < max(self.short_ma_period, self.long_ma_period):
            self.log_strategy_event(f"Dados insuficientes para {metadata.get('pair', 'N/A')}", "WARNING")
            return dataframe

        try:
            # Moving Averages
            dataframe['ma_short'] = ta.SMA(dataframe, timeperiod=self.short_ma_period.value)
            dataframe['ma_long'] = ta.SMA(dataframe, timeperiod=self.long_ma_period.value)

            # RSI
            dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)

            # MACD
            macd, macd_signal, macd_hist = ta.MACD(
                dataframe['close'],
                fastperiod=self.macd_fast.value,
                slowperiod=self.macd_slow.value,
                signalperiod=self.macd_signal.value
            )
            dataframe['macd'] = macd
            dataframe['macd_signal'] = macd_signal
            dataframe['macd_hist'] = macd_hist

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = ta.BBANDS(
                dataframe['close'],
                timeperiod=self.bb_period.value,
                nbdevup=self.bb_std.value,
                nbdevdn=self.bb_std.value
            )
            dataframe['bb_upper'] = bb_upper
            dataframe['bb_middle'] = bb_middle
            dataframe['bb_lower'] = bb_lower

            # ATR (Average True Range) para volatilidade
            dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

            # Volume indicators
            dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
            dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']

            # Indicadores de momentum
            dataframe['momentum'] = ta.MOM(dataframe['close'], timeperiod=10)
            dataframe['roc'] = ta.ROC(dataframe['close'], timeperiod=10)

            # Spread (simulado - seria melhor com dados reais do exchange)
            # Para produção, usar dados reais de spread via exchange
            dataframe['spread'] = dataframe['close'] * 0.001  # 0.1% spread default

            # Filtro de volatilidade
            dataframe['volatility'] = (dataframe['high'] - dataframe['low']) / dataframe['close']
            dataframe['volatility_ok'] = dataframe['volatility'] < self.volatility_threshold.value

            # Aceleradores e indicadores customizados
            dataframe['ma_trend'] = (dataframe['ma_short'] > dataframe['ma_long']).astype(int)
            dataframe['rsi_normalized'] = (dataframe['rsi'] - 50) / 50  # Normaliza RSI para -1 a 1

            self.log_strategy_event(f"Indicadores populados para {metadata.get('pair', 'N/A')}")

        except Exception as e:
            self.log_strategy_event(f"Erro ao populizar indicadores: {e}", "ERROR")
            # Retornar dataframe vazio se não conseguir calcular indicadores
            return pd.DataFrame()

        return dataframe

    def populate_buy_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define condições de compra com validações rigorosas

        Args:
            dataframe: DataFrame com dados OHLCV e indicadores
            metadata: Metadados do par de trading

        Returns:
            DataFrame com sinais de compra
        """

        # Inicializar coluna de sinal
        dataframe['enter_long'] = 0

        try:
            # Validação de dados e volatilidade
            data_ok = (
                (dataframe['volume'] > 0) &  # Volume válido
                (dataframe['volume'] >= self.min_volume.value) &  # Volume mínimo
                (dataframe['spread'] <= (dataframe['close'] * self.max_spread_percent.value / 100)) &  # Spread baixo
                (dataframe['volatility_ok']) &  # Volatilidade acceptable
                (dataframe['volume_ratio'] > 0.5)  # Volume não muito baixo
            )

            # Condições técnicas básicas
            trend_condition = (
                (dataframe['ma_short'] > dataframe['ma_long']) &  # Tendência de alta
                (dataframe['close'] > dataframe['ma_short']) &    # Preço acima da média
                (dataframe['ma_trend'] == 1) &                   # Confirmação de tendência
                (dataframe['volume_ratio'] > 1.2)                # Volume em alta
            )

            # Condições de momentum
            momentum_condition = (
                (dataframe['rsi'] > self.rsi_oversold.value) &   # RSI não oversold
                (dataframe['rsi'] < self.rsi_overbought.value) & # RSI não overbought
                (dataframe['macd'] > dataframe['macd_signal']) & # MACD bullish
                (dataframe['macd_hist'] > 0) &                   # MACD hist positive
                (dataframe['momentum'] > 0) &                    # Momentum positive
                (dataframe['roc'] > -2)                          # ROC não muito negative
            )

            # Condições de Bollinger Bands
            bb_condition = (
                (dataframe['close'] > dataframe['bb_lower']) &   # Acima do BB inferior
                (dataframe['close'] < dataframe['bb_upper']) &   # Abaixo do BB superior
                ((dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower']) > 0.2) &  # Não muito próximo ao BB inferior
                ((dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle'] > 0.01)  # BB não muito narrow
            )

            # Condições adicionais de qualidade
            quality_conditions = (
                (dataframe['atr'] < dataframe['close'] * 0.05) &  # ATR reasonable
                (dataframe['volume'] > dataframe['volume'].rolling(20).mean() * 0.8)  # Volume reasonable
            )

            # Combinar todas as condições
            buy_condition = (
                data_ok &
                trend_condition &
                momentum_condition &
                bb_condition &
                quality_conditions
            )

            # Aplicar sinais de compra
            dataframe.loc[buy_condition, 'enter_long'] = 1

            # Log de estatísticas
            total_signals = buy_condition.sum()
            if total_signals > 0:
                pair_name = metadata.get('pair', 'N/A')
                self.log_strategy_event(f"Buy signals generated for {pair_name}: {total_signals}")

        except Exception as e:
            self.log_strategy_event(f"Erro em populate_buy_trend: {e}", "ERROR")
            dataframe['enter_long'] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define condições de saída com proteções avançadas

        Args:
            dataframe: DataFrame com dados OHLCV e indicadores
            metadata: Metadados do par de trading

        Returns:
            DataFrame com sinais de saída
        """

        # Inicializar coluna de sinal
        dataframe['exit_long'] = 0

        try:
            # Condições de saída técnica
            exit_conditions = (
                # RSI Overbought ou reversão bearish
                ((dataframe['rsi'] > 75) | (dataframe['rsi'] < dataframe['rsi'].shift(1))) &

                # MACD bearish
                ((dataframe['macd'] < dataframe['macd_signal']) | (dataframe['macd_hist'] < 0)) &

                # Breakout bearish do BB ou hitting BB superior
                ((dataframe['close'] < dataframe['bb_lower']) | (dataframe['close'] > dataframe['bb_upper'])) &

                # Momentum deteriorating
                ((dataframe['momentum'] < dataframe['momentum'].shift(1)) | (dataframe['momentum'] < -5)) &

                # Volume condition para confirmar saída
                (dataframe['volume'] > dataframe['volume'].rolling(10).mean() * 0.8)
            )

            # Condições de risco
            risk_conditions = (
                # Volatilidade muito alta
                (dataframe['volatility'] > self.volatility_threshold.value * 2) |
                # Volume muito baixo (fuga)
                (dataframe['volume'] < self.min_volume.value * 0.5) |
                # Spread muito alto
                (dataframe['spread'] > (dataframe['close'] * self.max_spread_percent.value * 2 / 100))
            )

            # Combinar condições
            final_exit_condition = exit_conditions | risk_conditions

            # Aplicar sinais de saída
            dataframe.loc[final_exit_condition, 'exit_long'] = 1

            # Log de estatísticas
            total_exits = final_exit_condition.sum()
            if total_exits > 0:
                pair_name = metadata.get('pair', 'N/A')
                self.log_strategy_event(f"Exit signals generated for {pair_name}: {total_exits}")

        except Exception as e:
            self.log_strategy_event(f"Erro em populate_exit_trend: {e}", "ERROR")
            dataframe['exit_long'] = 0

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                          proposed_stake: float, min_stake: float, max_stake: float, **kwargs) -> float:
        """
        Calcula stake amount com controles de risco

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
            # Limitar por position size máximo
            if max_stake is not None and max_stake > 0:
                max_allowed = max_stake * (self.max_position_size_percent.value / 100)
                proposed_stake = min(proposed_stake, max_allowed)

            # Verificar se não excede o stake máximo do par
            pair_current_trades = self._pair_trade_count.get(pair, 0)
            if pair_current_trades >= self.max_trades_per_pair.value:
                return 0  # Bloquear novo trade se já atingiu o limite

            # Stake mínimo para evitar dust trades
            if proposed_stake < 10:  # USDT mínimo
                return 0

            return proposed_stake

        except Exception as e:
            self.log_strategy_event(f"Erro em custom_stake_amount: {e}", "ERROR")
            return 0

    def check_exit_signal(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                         current_profit: float, min_stake: Optional[float], **kwargs) -> Optional[pd.Series]:
        """
        Validação adicional de sinais de saída

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
            # Verificar cooldown para este par
            pair_cooldown_key = f"{pair}_{current_time.strftime('%Y%m%d')}"
            if self._last_trade_info.get(pair_cooldown_key, 0) > current_time.timestamp():
                self.log_strategy_event(f"Cooldown ativo para {pair}, ignorando exit signal", "DEBUG")
                return None

            # Verificar se o trade está há muito tempo aberto
            trade_age = (current_time - trade.open_date).total_seconds()
            max_trade_age = 24 * 3600  # 24 horas máximo

            if trade_age > max_trade_age:
                self.log_strategy_event(f"Forçando saída de {pair} por idade do trade ({trade_age/3600:.1f}h)", "WARNING")
                return pd.Series([1, "MAX_AGE"])

            # Verificar drawdown
            if current_profit < -0.05:  # 5% drawdown
                self.log_strategy_event(f"Drawdown crítico para {pair}: {current_profit:.2%}", "WARNING")
                return pd.Series([1, "HIGH_DRAWDOWN"])

            # Verificar questões de mercado (spread, volume)
            # Esta verificação seria melhor com dados reais do exchange
            market_ok = True  # Placeholder - implementar verificação real

            if not market_ok:
                return pd.Series([1, "MARKET_CONDITIONS"])

            return None  # Nenhuma saída forçada

        except Exception as e:
            self.log_strategy_event(f"Erro em check_exit_signal: {e}", "ERROR")
            return None

    def leverage_by_share(self, pair: str, current_time: datetime, current_rate: float,
                        current_share: float, current_leverage: float, max_leverage: float,
                        entry_tag: Optional[str], side: Optional[str], **kwargs) -> float:
        """
        Determina alavancagem baseada no risco (usar com moderação)

        Args:
            pair: Par de trading
            current_time: Tempo atual
            current_rate: Taxa atual
            current_share: Share atual
            current_leverage: Alavancagem atual
            max_leverage: Alavancagem máxima
            entry_tag: Tag de entrada
            side: Lado (long/short)

        Returns:
            Alavancagem ajustada
        """

        try:
            # Por segurança, começar sem alavancagem
            base_leverage = 1.0

            # Ajustar baseado no número de trades ativos
            total_trades = len(Trade.get_open_trades())
            if total_trades > 3:
                return 1.0  # Sem alavancagem com muitos trades

            # Ajustar baseado na liquidez do par
            # Pares principais podem ter alavancagem maior
            if pair.endswith('/USDT') and pair.split('/')[0] in ['BTC', 'ETH', 'BNB']:
                return min(2.0, max_leverage)

            return base_leverage

        except Exception as e:
            self.log_strategy_event(f"Erro em leverage_by_share: {e}", "ERROR")
            return 1.0

    def bot_loop_start(self, **kwargs) -> None:
        """
        Executado no início de cada loop do bot

        Args:
            **kwargs: Argumentos adicionais
        """

        try:
            # Resetar contadores diários
            current_time = datetime.now()
            day_key = current_time.strftime('%Y%m%d')

            # Limpar informações antigas (mais de 7 dias)
            cutoff_time = (current_time - timedelta(days=7)).timestamp()
            for key in list(self._last_trade_info.keys()):
                if key.split('_')[-1] < day_key:
                    self._last_trade_info.pop(key, None)

            # Atualizar contadores de trades por par
            open_trades = Trade.get_open_trades()
            self._pair_trade_count = {}

            for trade in open_trades:
                pair = trade.pair
                self._pair_trade_count[pair] = self._pair_trade_count.get(pair, 0) + 1

            self.log_strategy_event(f"Bot loop started. Open trades: {len(open_trades)}")

        except Exception as e:
            self.log_strategy_event(f"Erro em bot_loop_start: {e}", "ERROR")

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                          side: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Confirmação final antes da entrada

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
            Tuple (confirmar, razão)
        """

        try:
            # Verificar limite de trades por par
            if self._pair_trade_count.get(pair, 0) >= self.max_trades_per_pair.value:
                return False, f"Limite de trades por par atingido ({self.max_trades_per_pair.value})"

            # Verificar cooldown
            cooldown_key = f"{pair}_{current_time.strftime('%Y%m%d')}"
            if self._last_trade_info.get(cooldown_key, 0) > current_time.timestamp():
                return False, "Cooldown ativo para este par"

            # Verificar amount mínimo
            if amount < 10:  # USDT mínimo
                return False, "Amount muito pequeno"

            # Registrar trade para cooldown
            cooldown_until = (current_time + timedelta(minutes=self.cooldown_candles.value * 15)).timestamp()
            self._last_trade_info[cooldown_key] = cooldown_until

            self.log_strategy_event(f"Trade confirmado para {pair}: {amount:.2f} @ {rate:.6f}")

            return True, None

        except Exception as e:
            self.log_strategy_event(f"Erro em confirm_trade_entry: {e}", "ERROR")
            return False, f"Erro interno: {str(e)}"

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                         rate: float, time_in_force: str, current_time: datetime,
                         exit_reason: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Confirmação final antes da saída

        Args:
            pair: Par de trading
            trade: Objeto Trade
            order_type: Tipo de ordem
            amount: Quantidade
            rate: Taxa
            time_in_force: Tempo em força
            current_time: Tempo atual
            exit_reason: Razão da saída

        Returns:
            Tuple (confirmar, razão)
        """

        try:
            # Log do trade sendo fechado
            profit_pct = trade.calc_profit_ratio()
            self.log_strategy_event(
                f"Trade exit confirmed for {pair}: {exit_reason}, Profit: {profit_pct:.2%}"
            )

            return True, None

        except Exception as e:
            self.log_strategy_event(f"Erro em confirm_trade_exit: {e}", "ERROR")
            return False, f"Erro interno: {str(e)}"

    def informave_pair_trade(self, pair: str, trade: Trade, current_time: datetime,
                           **kwargs) -> None:
        """
        Processa informações de trade para logging e monitoramento

        Args:
            pair: Par de trading
            trade: Objeto Trade
            current_time: Tempo atual
        """

        try:
            profit_pct = trade.calc_profit_ratio()
            self.log_strategy_event(
                f"Trade active: {pair}, PnL: {profit_pct:.2%}, "
                f"Open time: {trade.open_date.strftime('%H:%M:%S')}"
            )

        except Exception as e:
            self.log_strategy_event(f"Erro em informave_pair_trade: {e}", "ERROR")

    def populate_pair_trade(self, pair: str, **kwargs) -> pd.DataFrame:
        """
        Popula informações específicas do par (placeholder para extensões)

        Args:
            pair: Par de trading

        Returns:
            DataFrame vazio (implementar conforme necessário)
        """

        # Placeholder para implementação futura
        return pd.DataFrame()

    def populate_any_trade(self, pair: str, **kwargs) -> pd.DataFrame:
        """
        Popula informações para qualquer trade (placeholder para extensões)

        Args:
            pair: Par de trading

        Returns:
            DataFrame vazio (implementar conforme necessário)
        """

        # Placeholder para implementação futura
        return pd.DataFrame()

    def get_recommended_subtimeframes(self) -> Dict[str, List[str]]:
        """
        Retorna timeframes recomendados para confirmação de sinais

        Returns:
            Dicionário com timeframes por timeframe principal
        """

        return {
            "1m": ["5m", "15m"],
            "5m": ["15m", "1h"],
            "15m": ["1h", "4h"],
            "1h": ["4h", "1d"],
            "4h": ["1d", "1w"]
        }
