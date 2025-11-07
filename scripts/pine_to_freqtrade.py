#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - CONVERSOR PINE SCRIPT PARA FREQTRADE
================================================================

Conversor automático de scripts Pine Script do TradingView para
estratégias Python do FreqTrade

Funcionalidades:
- Conversão automática de indicadores Pine Script
- Mapeamento de funções comuns
- Geração de estratégias FreqTrade compatíveis
- Interface de linha de comando interativa

Uso:
    python3 pine_to_freqtrade.py --input script.pine --output estrategia.py
    python3 pine_to_freqtrade.py --interactive

"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PineToFreqTradeConverter:
    """Conversor de Pine Script para FreqTrade"""

    def __init__(self):
        # Mapeamento de funções Pine Script para Python/Talib
        self.function_mappings = {
            # Moving Averages
            'sma': 'ta.SMA',
            'ema': 'ta.EMA',
            'wma': 'ta.WMA',
            'vwma': 'ta.VWMA',
            'rma': 'ta.RMA',
            'swma': 'ta.SWMA',

            # Osciladores
            'rsi': 'ta.RSI',
            'macd': 'ta.MACD',
            'stoch': 'ta.STOCH',
            'adx': 'ta.ADX',
            'cci': 'ta.CCI',
            'roc': 'ta.ROC',

            # Bollinger Bands
            'bb': 'ta.BBANDS',
            'bbbasis': 'ta.BBANDS middle',
            'bbupper': 'ta.BBANDS upper',
            'bblower': 'ta.BBANDS lower',

            # Volume
            'volume': 'volume',
            'vwap': 'ta.VWAP',

            # Math
            'abs': 'abs',
            'sqrt': 'np.sqrt',
            'max': 'max',
            'min': 'min',
            'log': 'np.log',
            'exp': 'np.exp',

            # Statistical
            'stdev': 'ta.STDDEV',
            'variance': 'ta.VAR',
            'correlation': 'ta.CORR',
            'covariance': 'ta.COV',
        }

        # Padrões de entrada/saída comuns
        self.entry_patterns = [
            r'long\s*=\s*(.+)',
            r'enter_long\s*=\s*(.+)',
            r'buy\s*=\s*(.+)',
            r'signal\s*=\s*(.+)'
        ]

        self.exit_patterns = [
            r'short\s*=\s*(.+)',
            r'exit_long\s*=\s*(.+)',
            r'sell\s*=\s*(.+)',
            r'exit\s*=\s*(.+)'
        ]

        # Parâmetros comuns
        self.common_params = {
            'length': 14,
            'length1': 12,
            'length2': 26,
            'length3': 9,
            'mult': 2.0,
            'tf': '15m'
        }

    def convert_pine_script(self, pine_code: str, strategy_name: str = "ConvertedStrategy") -> str:
        """
        Converte código Pine Script para estratégia FreqTrade

        Args:
            pine_code: Código Pine Script original
            strategy_name: Nome da estratégia resultante

        Returns:
            Código Python da estratégia FreqTrade
        """

        # Limpar e estruturar o código Pine
        pine_code = self._clean_pine_code(pine_code)

        # Extrair parâmetros
        parameters = self._extract_parameters(pine_code)

        # Extrair indicadores
        indicators = self._extract_indicators(pine_code)

        # Extrair lógica de entrada
        entry_logic = self._extract_entry_logic(pine_code)

        # Extrair lógica de saída
        exit_logic = self._extract_exit_logic(pine_code)

        # Gerar código Python
        python_code = self._generate_strategy_code(
            strategy_name, parameters, indicators, entry_logic, exit_logic
        )

        return python_code

    def _clean_pine_code(self, code: str) -> str:
        """Limpa e estrutura código Pine Script"""
        # Remover comentários de linha
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)

        # Remover comentários de bloco
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        # Normalizar espaços, mas preservar quebras de linha
        lines = code.split('\n')
        lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
        code = '\n'.join(lines)
        code = re.sub(r';\s*', '\n', code)

        return code.strip()

    def _extract_parameters(self, code: str) -> Dict:
        """Extrai parâmetros do código Pine"""
        parameters = {}

        # Procurar por parâmetros input
        param_patterns = [
            r'input\.(\w+)\s*=\s*(.+)',
            r'input\s+(\w+)\s*=\s*(.+)',
            r'(\w+)\s*=\s*input\((.+)\)'
        ]

        for pattern in param_patterns:
            matches = re.findall(pattern, code)
            for match in matches:
                param_name = match[0].strip()
                param_value = match[1].strip()

                # Tentar converter para tipo apropriado
                try:
                    if param_value.isdigit():
                        parameters[param_name] = int(param_value)
                    elif '.' in param_value and param_value.replace('.', '').isdigit():
                        parameters[param_name] = float(param_value)
                    elif param_value.lower() in ['true', 'false']:
                        parameters[param_name] = param_value.lower() == 'true'
                    else:
                        parameters[param_name] = param_value.strip('"\'')
                except:
                    parameters[param_name] = param_value.strip('"\'')

        return parameters

    def _extract_indicators(self, code: str) -> List[Dict]:
        """Extrai indicadores do código Pine"""
        indicators = []

        # Padrões para diferentes tipos de indicadores
        indicator_patterns = {
            'sma': r'sma\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            'ema': r'ema\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            'rsi': r'rsi\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            'macd': r'macd\s*\(\s*([^)]+)\s*\)',
            'bb': r'bb\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)'
        }

        for indicator_type, pattern in indicator_patterns.items():
            matches = re.findall(pattern, code, re.IGNORECASE)
            for match in matches:
                indicator = {
                    'type': indicator_type,
                    'source': match[0].strip() if len(match) > 0 else 'close',
                    'parameters': []
                }

                # Extrair parâmetros adicionais
                if len(match) > 1:
                    indicator['parameters'].append(match[1].strip())
                if len(match) > 2:
                    indicator['parameters'].append(match[2].strip())

                indicators.append(indicator)

        return indicators

    def _extract_entry_logic(self, code: str) -> str:
        """Extrai lógica de entrada do código Pine"""
        entry_logic = "False"

        for pattern in self.entry_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                logic = match.group(1).strip()
                # Converter operadores Pine para Python
                logic = self._convert_operators(logic)
                entry_logic = logic
                break

        return entry_logic

    def _extract_exit_logic(self, code: str) -> str:
        """Extrai lógica de saída do código Pine"""
        exit_logic = "False"

        for pattern in self.exit_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                logic = match.group(1).strip()
                # Converter operadores Pine para Python
                logic = self._convert_operators(logic)
                exit_logic = logic
                break

        return exit_logic

    def _convert_operators(self, logic: str) -> str:
        """Converte operadores Pine Script para Python usando regex"""
        # Mapeamento de operadores Pine para Python
        operator_mappings = [
            (r'\bnot\b', '~'),
            (r'\band\b', '&'),
            (r'\bor\b', '|'),
            (r'==', '=='),
            (r'!=', '!='),
            (r'>=', '>='),
            (r'<=', '<='),
            (r'>', '>'),
            (r'<', '<'),
        ]

        # Aplicar substituições de forma segura
        for pine_op, python_op in operator_mappings:
            try:
                logic = re.sub(pine_op, python_op, logic, flags=re.IGNORECASE)
            except re.error as e:
                # Em caso de erro de regex, manter a lógica original
                print(f"Erro ao converter operador '{pine_op}': {e}")
                pass

        return logic

    def _generate_strategy_code(self, strategy_name: str, parameters: Dict,
                               indicators: List[Dict], entry_logic: str, exit_logic: str) -> str:
        """Gera código Python da estratégia"""

        # Cabeçalho da estratégia
        code = f'''"""
================================================================
FREQTRADE3 - ESTRATÉGIA CONVERTIDA DO TRADINGVIEW
================================================================

Esta estratégia foi convertida automaticamente de Pine Script
Origem: TradingView (convertida por FreqTrade3)

Conversão automática realizada em: {Path().cwd()}

AVISO: Teste extensivamente antes de usar com dinheiro real!
"""

import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta
import pandas as pd


class {strategy_name}(IStrategy):
    """
    Estratégia convertida automaticamente do Pine Script

    ⚠️ AVISO IMPORTANTE:
    Esta estratégia foi convertida automaticamente e pode precisar
    de ajustes manuais para funcionar corretamente.

    Recomendações:
    1. Teste extensivamente em backtesting
    2. Verifique os parâmetros manualmente
    3. Ajuste lógica se necessário
    4. Teste em dry-run antes de trading real
    """

    # ========================================
    # CONFIGURAÇÕES BÁSICAS
    # ========================================
    INTERFACE_VERSION = 3
    timeframe = '15m'
    startup_candles = 30

    # ROI conservador (ajustar conforme necessário)
    minimal_roi = {{
        "0": 0.02,
        "60": 0.01,
        "120": 0
    }}

    stoploss = -0.02
    trailing_stop = True

    # ========================================
    # PARÂMETROS EXTRAÍDOS DO PINE
    # ========================================
'''

        # Adicionar parâmetros extraídos
        if parameters:
            for param_name, param_value in parameters.items():
                param_safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', param_name)

                if isinstance(param_value, int):
                    code += f'    {param_safe_name} = IntParameter(1, 100, default={param_value}, space="buy")\n'
                elif isinstance(param_value, float):
                    code += f'    {param_safe_name} = DecimalParameter(0.1, 5.0, default={param_value}, space="buy")\n'
                elif isinstance(param_value, bool):
                    code += f'    {param_safe_name} = BooleanParameter(default={param_value})\n'
                else:
                    code += f'    {param_safe_name} = "{param_value}"  # String parameter\n'

        # Adicionar indicadores
        code += '\n    # ========================================\n'
        code += '    # INDICADORES TÉCNICOS\n'
        code += '    # ========================================\n'
        code += '    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:\n'
        code += '        """\n        Indicadores extraídos do Pine Script convertido\n        """"\n\n'

        for i, indicator in enumerate(indicators):
            var_name = f'{indicator["type"]}_{i+1}'

            if indicator["type"] == "sma":
                code += f'        # Simple Moving Average\n'
                code += f'        dataframe["{var_name}"] = ta.SMA(dataframe["close"], timeperiod={indicator["parameters"][0] if indicator["parameters"] else 14})\n'

            elif indicator["type"] == "ema":
                code += f'        # Exponential Moving Average\n'
                code += f'        dataframe["{var_name}"] = ta.EMA(dataframe["close"], timeperiod={indicator["parameters"][0] if indicator["parameters"] else 14})\n'

            elif indicator["type"] == "rsi":
                code += f'        # RSI\n'
                code += f'        dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod={indicator["parameters"][0] if indicator["parameters"] else 14})\n'

            elif indicator["type"] == "macd":
                code += f'        # MACD\n'
                code += f'        dataframe["macd"], dataframe["macdsignal"], dataframe["macdhist"] = ta.MACD(dataframe["close"])\n'

            elif indicator["type"] == "bb":
                code += f'        # Bollinger Bands\n'
                code += f'        dataframe["bb_upper"], dataframe["bb_middle"], dataframe["bb_lower"] = ta.BBANDS(dataframe["close"])\n'

        code += '\n        return dataframe\n'

        # Adicionar lógica de entrada
        code += '\n    # ========================================\n'
        code += '    # LÓGICA DE ENTRADA\n'
        code += '    # ========================================\n'
        code += '    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:\n'
        code += '        """\n        Lógica de entrada convertida do Pine Script\n        """"\n\n'

        code += f'        dataframe.loc[\n            (\n                # Lógica de entrada convertida\n                ({entry_logic}) &\n                (dataframe["volume"] > 0)\n            ),\n            "enter_long"\n        ] = 1\n\n'
        code += '        return dataframe\n'

        # Adicionar lógica de saída
        code += '\n    # ========================================\n'
        code += '    # LÓGICA DE SAÍDA\n'
        code += '    # ========================================\n'
        code += '    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:\n'
        code += '        """\n        Lógica de saída convertida do Pine Script\n        """"\n\n'

        code += f'        dataframe.loc[\n            (\n                # Lógica de saída convertida\n                ({exit_logic}) &\n                (dataframe["volume"] > 0)\n            ),\n            "exit_long"\n        ] = 1\n\n'
        code += '        return dataframe\n'

        # Adicionar comentários finais
        code += '''
    # ========================================
    # INSTRUÇÕES PARA AJUSTES MANUAIS
    # ========================================
    def manual_adjustments_needed(self):
        """
        Lista de ajustes manuais recomendados:

        1. Verificar e ajustar parâmetros IntParameter/DecimalParameter
        2. Ajustar timeframe conforme estratégia original
        3. Validar lógica de entrada/saída
        4. Adicionar filtros de volume se necessário
        5. Ajustar stop loss e ROI conforme estratégia
        6. Testar extensivamente em backtesting
        """
        pass
'''

        return code

    def interactive_mode(self):
        """Modo interativo para conversão"""
        print("🔄 Conversor Pine Script para FreqTrade")
        print("=" * 50)
        print()

        # Obter arquivo de entrada
        while True:
            input_file = input("📁 Caminho para o arquivo Pine Script (.pine): ").strip()
            if os.path.exists(input_file):
                break
            print("❌ Arquivo não encontrado. Tente novamente.")

        # Ler conteúdo do arquivo
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                pine_code = f.read()
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            return

        # Obter nome da estratégia
        strategy_name = input("📝 Nome da estratégia (padrão: ConvertedStrategy): ").strip()
        if not strategy_name:
            strategy_name = "ConvertedStrategy"

        # Obter arquivo de saída
        output_file = input("📄 Arquivo de saída (padrão: converted_strategy.py): ").strip()
        if not output_file:
            output_file = "converted_strategy.py"

        print("\n🔄 Convertendo Pine Script para FreqTrade...")

        try:
            # Converter código
            python_code = self.convert_pine_script(pine_code, strategy_name)

            # Salvar arquivo
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(python_code)

            print(f"✅ Conversão concluída!")
            print(f"📄 Arquivo salvo em: {output_file}")
            print()
            print("⚠️ IMPORTANTE:")
            print("1. Revise o código gerado")
            print("2. Ajuste parâmetros se necessário")
            print("3. Teste em backtesting")
            print("4. Teste em dry-run antes de usar dinheiro real")

        except Exception as e:
            print(f"❌ Erro durante conversão: {e}")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Conversor Pine Script para FreqTrade')
    parser.add_argument('--input', type=str, help='Arquivo Pine Script de entrada')
    parser.add_argument('--output', type=str, help='Arquivo Python de saída')
    parser.add_argument('--interactive', action='store_true', help='Modo interativo')
    parser.add_argument('--strategy-name', type=str, default='ConvertedStrategy',
                       help='Nome da estratégia')

    args = parser.parse_args()

    converter = PineToFreqTradeConverter()

    if args.interactive:
        converter.interactive_mode()
    elif args.input:
        if not args.output:
            args.output = "converted_strategy.py"

        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                pine_code = f.read()

            python_code = converter.convert_pine_script(pine_code, args.strategy_name)

            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(python_code)

            print(f"✅ Conversão concluída! Arquivo salvo em: {args.output}")

        except Exception as e:
            print(f"❌ Erro: {e}")
    else:
        print("Use --interactive para modo interativo ou --input para especificar arquivo")
        parser.print_help()


if __name__ == "__main__":
    main()
