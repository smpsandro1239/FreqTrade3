#!/usr/bin/env python3
"""
============================================================
FREQTRADE3 - GERADOR DE GRAFICOS SIMPLIFICADO
============================================================

Script simples para demonstrar capacidades de graficos
com dados de trading e indicadores tecnicos.

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


class SimpleTradingChart:
    """Classe simplificada para gerar graficos de trading"""

    def __init__(self):
        self.data_dir = Path('user_data/data/binance')

    def load_eth_data(self):
        """Carrega dados do ETH/USDT"""
        try:
            file_path = self.data_dir / "ETH_USDT-15m.feather"
            if file_path.exists():
                df = pd.read_feather(file_path)
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
                print(f"Dados carregados: {len(df)} candles")
                return df
            else:
                print("Arquivo de dados nao encontrado")
                return None
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            return None

    def add_simple_indicators(self, df):
        """Adiciona indicadores simples"""
        try:
            # MACD basico
            macd, macd_signal, macd_hist = ta.MACD(df['close'])
            df['macd'] = macd
            df['macd_signal'] = macd_signal

            # EMAs
            df['ema_12'] = ta.EMA(df['close'], timeperiod=12)
            df['ema_26'] = ta.EMA(df['close'], timeperiod=26)

            # RSI
            df['rsi'] = ta.RSI(df['close'], timeperiod=14)

            print("Indicadores adicionados")
            return df

        except Exception as e:
            print(f"Erro ao adicionar indicadores: {e}")
            return df

    def generate_simple_chart(self, df):
        """Gera grafico simples"""
        try:
            # Filtrar ultimos 3 dias
            end_date = df.index[-1]
            start_date = end_date - timedelta(days=3)
            df_recent = df[start_date:end_date]

            if len(df_recent) == 0:
                print("Nenhum dado recente encontrado")
                return

            # Criar figura
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

            # Grafico 1: Preco e EMAs
            ax1.plot(df_recent.index, df_recent['close'], label='ETH Price', color='black', linewidth=2)
            ax1.plot(df_recent.index, df_recent['ema_12'], label='EMA 12', color='blue', alpha=0.7)
            ax1.plot(df_recent.index, df_recent['ema_26'], label='EMA 26', color='red', alpha=0.7)

            ax1.set_title('ETH/USDT - Preco e EMAs (15m)', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Preco (USDT)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Grafico 2: MACD
            ax2.plot(df_recent.index, df_recent['macd'], label='MACD', color='blue')
            ax2.plot(df_recent.index, df_recent['macd_signal'], label='Signal', color='red')
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax2.set_title('MACD', fontsize=14, fontweight='bold')
            ax2.set_ylabel('MACD', fontsize=12)
            ax2.set_xlabel('Data', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # Formatar datas
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # Salvar
            save_path = 'user_data/plot_html/eth_trading_chart.png'
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Grafico salvo: {save_path}")

            return True

        except Exception as e:
            print(f"Erro ao gerar grafico: {e}")
            return False

    def print_summary(self, df):
        """Imprime resumo dos dados"""
        try:
            print("\n=== RESUMO DOS DADOS ===")
            print(f"Periodo: {df.index[0]} ate {df.index[-1]}")
            print(f"Total candles: {len(df)}")
            print(f"Preco inicial: ${df['close'].iloc[0]:.2f}")
            print(f"Preco final: ${df['close'].iloc[-1]:.2f}")
            print(f"Variação: {((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100):.2f}%")
            print(f"RSI medio: {df['rsi'].mean():.2f}")
            print(f"Volume medio: {df['volume'].mean():.0f}")

        except Exception as e:
            print(f"Erro ao imprimir resumo: {e}")


def main():
    print("FREQTRADE3 - Gerador de Graficos")
    print("=" * 40)

    # Inicializar chart generator
    chart_gen = SimpleTradingChart()

    # Carregar dados
    df = chart_gen.load_eth_data()
    if df is None:
        return

    # Adicionar indicadores
    df = chart_gen.add_simple_indicators(df)

    # Gerar grafico
    success = chart_gen.generate_simple_chart(df)

    if success:
        chart_gen.print_summary(df)
        print("\nGrafico gerado com sucesso!")
        print("Acesse: http://localhost:8090/plot_html/eth_trading_chart.png")
    else:
        print("Falha ao gerar grafico")


if __name__ == "__main__":
    main()
