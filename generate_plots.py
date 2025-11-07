#!/usr/bin/env python3
"""
============================================================
FREQTRADE3 - GERADOR DE GRÁFICOS MANUAL
============================================================

Script para gerar gráficos de trading usando matplotlib
com dados do FreqTrade e indicadores das estratégias.

Autor: FreqTrade3 Project
Data: 2025-11-05
============================================================
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import talib.abstract as ta

# Adicionar o diretório do FreqTrade ao path
sys.path.append('C:/Users/AESAS/AppData/Local/Programs/Python/Python311/Lib/site-packages')

class TradingPlotter:
    """Classe para gerar gráficos de trading"""

    def __init__(self, data_dir='user_data/data/binance'):
        self.data_dir = Path(data_dir)
        self.fig_size = (16, 12)

    def load_data(self, pair, timeframe='15m'):
        """Carrega dados do par"""
        try:
            # Tentar diferentes extensões
            for ext in ['.feather', '.json']:
                file_path = self.data_dir / f"{pair}_{timeframe}{ext}"
                if file_path.exists():
                    if ext == '.feather':
                        df = pd.read_feather(file_path)
                    else:
                        df = pd.read_json(file_path, lines=True)

                    # Padronizar colunas
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date').sort_index()

                    # Verificar se temos dados
                    if len(df) > 0:
                        print(f"✅ Dados carregados: {pair} {timeframe}")
                        print(f"📊 {len(df)} candles de {df.index[0]} até {df.index[-1]}")
                        return df

            print(f"❌ Não foi possível carregar dados para {pair}")
            return None

        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            return None

    def add_indicators(self, df):
        """Adiciona indicadores técnicos"""
        try:
            # MACD
            macd, macd_signal, macd_hist = ta.MACD(df['close'])
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist

            # EMAs
            df['ema_fast'] = ta.EMA(df, timeperiod=12)
            df['ema_slow'] = ta.EMA(df, timeperiod=26)
            df['ema_200'] = ta.EMA(df, timeperiod=200)

            # RSI
            df['rsi'] = ta.RSI(df, timeperiod=14)

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = ta.BBANDS(df['close'])
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower

            # Volume
            df['volume_ma'] = ta.SMA(df['volume'], timeperiod=20)

            print("✅ Indicadores adicionados")
            return df

        except Exception as e:
            print(f"❌ Erro ao adicionar indicadores: {e}")
            return df

    def generate_signals(self, df):
        """Gera sinais de compra e venda"""
        try:
            # Sinais de compra (MACD)
            df['buy_signal'] = (
                (df['macd'] > df['macd_signal']) &
                (df['macd'] > 0) &
                (df['rsi'] > 25) &
                (df['rsi'] < 75) &
                (df['close'] > df['ema_fast']) &
                (df['volume'] > df['volume_ma'] * 1.2)
            )

            # Sinais de venda (MACD)
            df['sell_signal'] = (
                (df['macd'] < df['macd_signal']) |
                (df['rsi'] > 75) |
                (df['close'] < df['ema_fast'])
            )

            buy_count = df['buy_signal'].sum()
            sell_count = df['sell_signal'].sum()

            print(f"✅ Sinais gerados:")
            print(f"   📈 Sinais de compra: {buy_count}")
            print(f"   📉 Sinais de venda: {sell_count}")

            return df

        except Exception as e:
            print(f"❌ Erro ao gerar sinais: {e}")
            return df

    def plot_trading_chart(self, df, pair, timeframe, save_path=None):
        """Gera gráfico completo de trading"""
        try:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=self.fig_size,
                                               gridspec_kw={'height_ratios': [3, 1, 1]})

            # Gráfico 1: Preços e EMAs
            ax1.plot(df.index, df['close'], label='Preço', color='black', linewidth=1)
            ax1.plot(df.index, df['ema_fast'], label='EMA 12', color='blue', alpha=0.7)
            ax1.plot(df.index, df['ema_slow'], label='EMA 26', color='orange', alpha=0.7)
            ax1.plot(df.index, df['ema_200'], label='EMA 200', color='red', alpha=0.7)

            # Bollinger Bands
            ax1.fill_between(df.index, df['bb_upper'], df['bb_lower'],
                           alpha=0.2, color='gray', label='Bollinger Bands')

            # Sinais de compra e venda
            buy_signals = df[df['buy_signal']]
            sell_signals = df[df['sell_signal']]

            ax1.scatter(buy_signals.index, buy_signals['close'],
                       color='green', marker='^', s=100, label='Compra', zorder=5)
            ax1.scatter(sell_signals.index, sell_signals['close'],
                       color='red', marker='v', s=100, label='Venda', zorder=5)

            ax1.set_title(f'{pair} - {timeframe} - Sinais de Trading', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Preço (USDT)', fontsize=12)
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)

            # Gráfico 2: MACD
            ax2.plot(df.index, df['macd'], label='MACD', color='blue')
            ax2.plot(df.index, df['macd_signal'], label='Signal', color='red')
            ax2.bar(df.index, df['macd_hist'], label='Histograma',
                   color='green', alpha=0.3)
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax2.set_ylabel('MACD', fontsize=12)
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.3)

            # Gráfico 3: RSI e Volume
            ax3_twin = ax3.twinx()

            # RSI
            ax3.plot(df.index, df['rsi'], label='RSI', color='purple', linewidth=2)
            ax3.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Sobrecomprado')
            ax3.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Sobrevendido')
            ax3.set_ylabel('RSI', fontsize=12, color='purple')
            ax3.set_ylim(0, 100)

            # Volume
            ax3_twin.bar(df.index, df['volume'], alpha=0.3, color='lightblue', label='Volume')
            ax3_twin.plot(df.index, df['volume_ma'], color='darkblue', label='Volume MA')
            ax3_twin.set_ylabel('Volume', fontsize=12)

            ax3.set_xlabel('Data', fontsize=12)
            ax3.legend(loc='upper left')
            ax3_twin.legend(loc='upper right')
            ax3.grid(True, alpha=0.3)

            # Formatação de datas
            for ax in [ax1, ax2, ax3]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # Salvar se path fornecido
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"✅ Gráfico salvo: {save_path}")

            plt.show()

        except Exception as e:
            print(f"❌ Erro ao gerar gráfico: {e}")

    def print_statistics(self, df, pair):
        """Imprime estatísticas dos sinais"""
        try:
            buy_signals = df[df['buy_signal']]
            sell_signals = df[df['sell_signal']]

            total_candles = len(df)
            price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100

            print(f"\n📊 ESTATÍSTICAS - {pair}")
            print(f"=" * 50)
            print(f"Período: {df.index[0].strftime('%Y-%m-%d %H:%M')} até {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
            print(f"Total de candles: {total_candles}")
            print(f"Preço inicial: ${df['close'].iloc[0]:.2f}")
            print(f"Preço final: ${df['close'].iloc[-1]:.2f}")
            print(f"Variação total: {price_change:.2f}%")
            print(f"")
            print(f"Sinais de compra: {len(buy_signals)} ({len(buy_signals)/total_candles*100:.1f}%)")
            print(f"Sinais de venda: {len(sell_signals)} ({len(sell_signals)/total_candles*100:.1f}%)")
            print(f"")
            print(f"RSI médio: {df['rsi'].mean():.2f}")
            print(f"Volume médio: {df['volume'].mean():.0f}")
            print(f"Volatilidade: {df['close'].pct_change().std()*100:.2f}%")

        except Exception as e:
            print(f"❌ Erro ao imprimir estatísticas: {e}")


def main():
    """Função principal"""
    print("FREQTRADE3 - Gerador de Graficos")
    print("=" * 50)

    # Inicializar plotter
    plotter = TradingPlotter()

    # Carregar dados ETH/USDT
    df = plotter.load_data('ETH/USDT', '15m')
    if df is None:
        print("X Nao foi possivel carregar os dados")
        return

    # Adicionar indicadores
    df = plotter.add_indicators(df)
    if df.empty:
        print("X Falha ao adicionar indicadores")
        return

    # Gerar sinais
    df = plotter.generate_signals(df)

    # Filtrar período específico (últimos 5 dias)
    end_date = df.index[-1]
    start_date = end_date - timedelta(days=5)
    df_recent = df[start_date:end_date]

    # Gerar gráfico
    plotter.plot_trading_chart(
        df_recent,
        'ETH/USDT',
        '15m',
        save_path='user_data/plot_html/eth_usdt_trading_chart.png'
    )

    # Imprimir estatísticas
    plotter.print_statistics(df_recent, 'ETH/USDT')

    print(f"\n+ Grafico gerado com sucesso!")
    print(f"Pasta: user_data/plot_html/eth_usdt_trading_chart.png")
    print(f"Para visualizar, acesse: http://localhost:8090/plot_html/eth_usdt_trading_chart.png")


if __name__ == "__main__":
    main()
