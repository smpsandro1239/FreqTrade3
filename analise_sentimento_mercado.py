#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Análise de Sentimento de Mercado
Versão: 4.0 - Análise de Sentimento Multi-Fonte
Características: Análise de notícias, redes sociais, fear/greed index, indicadores sentimentais
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests
import schedule
import yaml

# Bibliotecas de análise de texto
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
    print("✅ NLTK disponível para análise de texto")
except ImportError:
    NLTK_AVAILABLE = False
    print("⚠️  NLTK não disponível. Análise limitada.")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
    print("✅ TextBlob disponível para análise de sentimento")
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("⚠️  TextBlob não disponível.")

@dataclass
class SentimentData:
    """Dados de sentimento estruturados"""
    symbol: str
    timestamp: str
    overall_sentiment: float  # -1.0 a 1.0
    fear_greed_index: Optional[float] = None
    news_sentiment: float = 0.0
    social_sentiment: float = 0.0
    technical_sentiment: float = 0.0
    volume_sentiment: float = 0.0
    market_cap_sentiment: float = 0.0
    confidence: float = 0.0
    source_count: int = 0
    metadata: Dict[str, Any] = None

class SentimentAnalyzer:
    """Analisador de sentimento multi-fonte para mercado crypto"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.sentiment_data_dir = 'sentiment_data'
        self.config_file = 'configs/sentiment_config.yaml'

        # Criar diretórios
        os.makedirs(self.sentiment_data_dir, exist_ok=True)
        os.makedirs('configs', exist_ok=True)

        # Inicializar analisador
        self._init_analyzer()

        # Cache de sentimentos
        self.sentiment_cache = {}
        self.cache_ttl = 300  # 5 minutos

        # Configurações
        self.config = self._load_config()

    def _init_analyzer(self):
        """Inicializar analisador de sentimento"""
        if NLTK_AVAILABLE:
            try:
                # Baixar recursos NLTK se necessário
                nltk.download('vader_lexicon', quiet=True)
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                nltk.download('wordnet', quiet=True)

                self.nltk_analyzer = SentimentIntensityAnalyzer()
                self.lemmatizer = WordNetLemmatizer()
                self.stop_words = set(stopwords.words('english'))
            except Exception as e:
                print(f"❌ Erro ao inicializar NLTK: {e}")
                self.nltk_analyzer = None
        else:
            self.nltk_analyzer = None

        if TEXTBLOB_AVAILABLE:
            self.textblob_analyzer = TextBlob
        else:
            self.textblob_analyzer = None

        print("🧠 Analisador de Sentimento inicializado")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações do analisador"""
        default_config = {
            'fear_greed': {
                'enabled': True,
                'api_key': None,
                'update_interval': 3600  # 1 hora
            },
            'news_sentiment': {
                'enabled': True,
                'sources': ['cryptonews', 'coindesk', 'cointelegraph'],
                'keywords': ['bitcoin', 'ethereum', 'crypto', 'blockchain'],
                'update_interval': 1800  # 30 minutos
            },
            'social_sentiment': {
                'enabled': True,
                'platforms': ['twitter', 'reddit', 'telegram'],
                'keywords': ['btc', 'eth', 'crypto', 'moon', 'hodl'],
                'update_interval': 900   # 15 minutos
            },
            'technical_sentiment': {
                'enabled': True,
                'indicators': ['rsi', 'macd', 'sma', 'bollinger'],
                'timeframes': ['1h', '4h', '1d'],
                'update_interval': 300   # 5 minutos
            },
            'weightings': {
                'fear_greed': 0.2,
                'news': 0.25,
                'social': 0.15,
                'technical': 0.3,
                'volume': 0.1
            },
            'thresholds': {
                'very_positive': 0.7,
                'positive': 0.3,
                'neutral': 0.1,
                'negative': -0.3,
                'very_negative': -0.7
            }
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    # Merge com default
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                return config
            else:
                # Salvar configuração default
                with open(self.config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                return default_config
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração: {e}")
            return default_config

    def get_fear_greed_index(self) -> Optional[float]:
        """Obter Fear & Greed Index"""
        try:
            if not self.config.get('fear_greed', {}).get('enabled', True):
                return None

            # API do Alternative.me (gratuita)
            response = requests.get('https://api.alternative.me/fng/', timeout=10)
            data = response.json()

            if 'data' in data and data['data']:
                fng_value = float(data['data'][0]['value'])
                return (fng_value - 50) / 50  # Normalizar para -1 a 1

        except Exception as e:
            print(f"⚠️  Erro ao obter Fear & Greed Index: {e}")

        return None

    def analyze_news_sentiment(self, symbol: str = "BTC") -> float:
        """Análise de sentimento de notícias"""
        try:
            if not self.config.get('news_sentiment', {}).get('enabled', True):
                return 0.0

            # Simulação de análise de notícias (em produção, usar APIs reais)
            news_headlines = self._fetch_news_headlines(symbol)

            if not news_headlines:
                return 0.0

            sentiments = []
            for headline in news_headlines:
                sentiment = self._analyze_text_sentiment(headline)
                if sentiment is not None:
                    sentiments.append(sentiment)

            return np.mean(sentiments) if sentiments else 0.0

        except Exception as e:
            print(f"❌ Erro na análise de notícias: {e}")
            return 0.0

    def analyze_social_sentiment(self, symbol: str = "BTC") -> float:
        """Análise de sentimento em redes sociais"""
        try:
            if not self.config.get('social_sentiment', {}).get('enabled', True):
                return 0.0

            # Simulação de análise de redes sociais
            social_posts = self._fetch_social_posts(symbol)

            if not social_posts:
                return 0.0

            sentiments = []
            for post in social_posts:
                sentiment = self._analyze_text_sentiment(post)
                if sentiment is not None:
                    sentiments.append(sentiment)

            return np.mean(sentiments) if sentiments else 0.0

        except Exception as e:
            print(f"❌ Erro na análise de redes sociais: {e}")
            return 0.0

    def analyze_technical_sentiment(self, symbol: str, timeframe: str = '1h') -> float:
        """Análise de sentimento baseada em indicadores técnicos"""
        try:
            if not self.config.get('technical_sentiment', {}).get('enabled', True):
                return 0.0

            # Conectar ao banco para obter dados técnicos
            conn = sqlite3.connect(self.db_path)

            # Query para dados de mercado
            query = """
                SELECT open, high, low, close, volume
                FROM market_data
                WHERE pair = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT 100
            """

            df = pd.read_sql_query(query, conn, params=(symbol, timeframe))
            conn.close()

            if len(df) < 20:
                return 0.0

            # Calcular indicadores técnicos
            technical_score = 0.0

            # RSI
            rsi = self._calculate_rsi(df['close'].values)
            if rsi is not None:
                if rsi > 70:
                    technical_score -= 0.3  # Sobrecomprado = negativo
                elif rsi < 30:
                    technical_score += 0.3  # Sobrevendido = positivo

            # MACD
            macd_line, macd_signal = self._calculate_macd(df['close'].values)
            if macd_line is not None and macd_signal is not None:
                if macd_line > macd_signal:
                    technical_score += 0.2
                else:
                    technical_score -= 0.2

            # Médias móveis
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            sma_50 = df['close'].rolling(50).mean().iloc[-1]
            current_price = df['close'].iloc[-1]

            if current_price > sma_20:
                technical_score += 0.2
            if sma_20 > sma_50:
                technical_score += 0.1

            # Volume
            recent_volume = df['volume'].tail(10).mean()
            historical_volume = df['volume'].head(50).mean()

            if recent_volume > historical_volume * 1.5:
                technical_score += 0.1  # Volume alto pode ser positivo

            # Normalizar para -1 a 1
            return np.clip(technical_score, -1.0, 1.0)

        except Exception as e:
            print(f"❌ Erro na análise técnica: {e}")
            return 0.0

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> Optional[float]:
        """Calcular RSI"""
        if len(prices) < period + 1:
            return None

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float]]:
        """Calcular MACD"""
        if len(prices) < slow:
            return None, None

        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        if ema_fast is None or ema_slow is None:
            return None, None

        macd_line = ema_fast[-1] - ema_slow[-1]

        # Para o sinal, precisaríamos calcular EMA do MACD
        # Simplificado para demonstração
        macd_signal = macd_line * 0.9  # Aproximação

        return macd_line, macd_signal

    def _calculate_ema(self, prices: np.ndarray, period: int) -> Optional[np.ndarray]:
        """Calcular EMA"""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = np.zeros(len(prices))
        ema[period-1] = np.mean(prices[:period])

        for i in range(period, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i-1] * (1 - multiplier))

        return ema

    def _analyze_text_sentiment(self, text: str) -> Optional[float]:
        """Análise de sentimento de texto"""
        try:
            if not text:
                return None

            # Usar NLTK se disponível
            if self.nltk_analyzer:
                scores = self.nltk_analyzer.polarity_scores(text)
                return scores['compound']  # Normalizado entre -1 e 1

            # Usar TextBlob como fallback
            elif self.textblob_analyzer:
                blob = self.textblob_analyzer(text)
                return blob.sentiment.polarity

            # Fallback simples baseado em palavras-chave
            else:
                return self._simple_keyword_sentiment(text)

        except Exception as e:
            print(f"❌ Erro na análise de texto: {e}")
            return 0.0

    def _simple_keyword_sentiment(self, text: str) -> float:
        """Análise de sentimento simples por palavras-chave"""
        positive_words = [
            'bull', 'bullish', 'moon', 'pump', 'up', 'rise', 'gain', 'profit', 'positive',
            'breakout', 'rally', 'surge', 'rocket', 'diamond', 'hands', 'hodl'
        ]

        negative_words = [
            'bear', 'bearish', 'dump', 'crash', 'down', 'fall', 'loss', 'negative',
            'correction', 'decline', 'drop', 'blood', 'panic', 'sell', 'exit'
        ]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count + negative_count == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return np.clip(sentiment, -1.0, 1.0)

    def _fetch_news_headlines(self, symbol: str) -> List[str]:
        """Obter manchetes de notícias (simulado)"""
        # Em produção, usar APIs como NewsAPI, CryptoNews API, etc.
        sample_headlines = [
            f"{symbol} shows strong momentum amid institutional adoption",
            f"Technical analysis suggests {symbol} breakout potential",
            f"{symbol} price targets updated by major analysts",
            f"Regulatory clarity boosts {symbol} confidence",
            f"Market volatility affects {symbol} trading"
        ]
        return sample_headlines[:3]  # Retornar amostra

    def _fetch_social_posts(self, symbol: str) -> List[str]:
        """Obter posts de redes sociais (simulado)"""
        # Em produção, usar APIs do Twitter, Reddit, etc.
        sample_posts = [
            f"{symbol} to the moon! 🚀",
            f"Strong hands Hodling {symbol}",
            f"Technical indicators looking bullish for {symbol}",
            f"Time to buy the dip on {symbol}",
            f"{symbol} showing strength in this market"
        ]
        return sample_posts[:3]  # Retornar amostra

    def get_comprehensive_sentiment(self, symbol: str, timeframe: str = '1h') -> SentimentData:
        """Obter análise de sentimento abrangente"""
        try:
            cache_key = f"{symbol}_{timeframe}"

            # Verificar cache
            if cache_key in self.sentiment_cache:
                cached_data, cache_time = self.sentiment_cache[cache_key]
                if time.time() - cache_time < self.cache_ttl:
                    return cached_data

            # Coletar todos os tipos de sentimento
            sentiment_components = {
                'fear_greed': self.get_fear_greed_index(),
                'news': self.analyze_news_sentiment(symbol),
                'social': self.analyze_social_sentiment(symbol),
                'technical': self.analyze_technical_sentiment(symbol, timeframe)
            }

            # Remover valores None
            valid_sentiments = {k: v for k, v in sentiment_components.items() if v is not None}

            if not valid_sentiments:
                # Retornar sentimento neutro se não conseguir obter dados
                result = SentimentData(
                    symbol=symbol,
                    timestamp=datetime.now().isoformat(),
                    overall_sentiment=0.0,
                    confidence=0.0,
                    source_count=0
                )
            else:
                # Calcular sentimento ponderado
                weights = self.config.get('weightings', {})
                weighted_sum = 0.0
                total_weight = 0.0

                for source, sentiment in valid_sentiments.items():
                    weight = weights.get(source, 0.2)
                    weighted_sum += sentiment * weight
                    total_weight += weight

                overall_sentiment = weighted_sum / total_weight if total_weight > 0 else 0.0

                # Calcular confiança baseada na quantidade de fontes
                confidence = len(valid_sentiments) / len(sentiment_components)

                result = SentimentData(
                    symbol=symbol,
                    timestamp=datetime.now().isoformat(),
                    overall_sentiment=overall_sentiment,
                    fear_greed_index=sentiment_components.get('fear_greed'),
                    news_sentiment=sentiment_components.get('news', 0.0),
                    social_sentiment=sentiment_components.get('social', 0.0),
                    technical_sentiment=sentiment_components.get('technical', 0.0),
                    confidence=confidence,
                    source_count=len(valid_sentiments),
                    metadata={'components': sentiment_components}
                )

            # Cache do resultado
            self.sentiment_cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            print(f"❌ Erro na análise de sentimento abrangente: {e}")
            return SentimentData(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                overall_sentiment=0.0,
                confidence=0.0,
                source_count=0
            )

    def get_sentiment_trend(self, symbol: str, periods: int = 24) -> Dict[str, Any]:
        """Obter tendência de sentimento ao longo do tempo"""
        try:
            # Conectar ao banco
            conn = sqlite3.connect(self.db_path)

            query = """
                SELECT timestamp, overall_sentiment, confidence, source_count
                FROM sentiment_data
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """

            df = pd.read_sql_query(query, conn, params=(symbol, periods))
            conn.close()

            if df.empty:
                return {'trend': 'neutral', 'change': 0.0, 'confidence': 0.0}

            # Calcular tendência
            recent_sentiment = df['overall_sentiment'].head(6).mean()  # Últimas 6 leituras
            historical_sentiment = df['overall_sentiment'].tail(6).mean()  # 6 leituras anteriores

            change = recent_sentiment - historical_sentiment

            # Classificar tendência
            if change > 0.1:
                trend = 'bullish'
            elif change < -0.1:
                trend = 'bearish'
            else:
                trend = 'neutral'

            return {
                'trend': trend,
                'change': change,
                'recent_sentiment': recent_sentiment,
                'historical_sentiment': historical_sentiment,
                'confidence': df['confidence'].mean(),
                'data_points': len(df)
            }

        except Exception as e:
            print(f"❌ Erro ao obter tendência: {e}")
            return {'trend': 'unknown', 'change': 0.0, 'confidence': 0.0}

    def save_sentiment_data(self, sentiment_data: SentimentData):
        """Salvar dados de sentimento no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Criar tabela se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sentiment_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timestamp TEXT,
                    overall_sentiment REAL,
                    fear_greed_index REAL,
                    news_sentiment REAL,
                    social_sentiment REAL,
                    technical_sentiment REAL,
                    volume_sentiment REAL,
                    market_cap_sentiment REAL,
                    confidence REAL,
                    source_count INTEGER,
                    metadata TEXT
                )
            ''')

            # Inserir dados
            cursor.execute('''
                INSERT INTO sentiment_data
                (symbol, timestamp, overall_sentiment, fear_greed_index, news_sentiment,
                 social_sentiment, technical_sentiment, volume_sentiment, market_cap_sentiment,
                 confidence, source_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sentiment_data.symbol,
                sentiment_data.timestamp,
                sentiment_data.overall_sentiment,
                sentiment_data.fear_greed_index,
                sentiment_data.news_sentiment,
                sentiment_data.social_sentiment,
                sentiment_data.technical_sentiment,
                sentiment_data.volume_sentiment,
                sentiment_data.market_cap_sentiment,
                sentiment_data.confidence,
                sentiment_data.source_count,
                json.dumps(sentiment_data.metadata or {})
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao salvar dados de sentimento: {e}")

    def get_market_mood(self) -> Dict[str, Any]:
        """Obter humor geral do mercado"""
        try:
            # Analisar principais cryptocurrencies
            symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL']
            sentiments = []

            for symbol in symbols:
                sentiment = self.get_comprehensive_sentiment(symbol)
                sentiments.append(sentiment.overall_sentiment)

            if not sentiments:
                return {'mood': 'unknown', 'score': 0.0, 'description': 'Dados insuficientes'}

            avg_sentiment = np.mean(sentiments)

            # Classificar humor
            if avg_sentiment > 0.5:
                mood = 'euphoric'
                description = 'Mercado em euforia, alta demanda'
            elif avg_sentiment > 0.2:
                mood = 'bullish'
                description = 'Mercado otimista, tendência de alta'
            elif avg_sentiment > -0.2:
                mood = 'neutral'
                description = 'Mercado equilibrado, lateral'
            elif avg_sentiment > -0.5:
                mood = 'bearish'
                description = 'Mercado pessimista, pressão de venda'
            else:
                mood = 'panicked'
                description = 'Mercado em pânico, alta volatilidade'

            return {
                'mood': mood,
                'score': avg_sentiment,
                'description': description,
                'symbols_analyzed': len(symbols),
                'confidence': np.std(sentiments)  # Menor desvio = mais consenso
            }

        except Exception as e:
            print(f"❌ Erro ao obter humor do mercado: {e}")
            return {'mood': 'unknown', 'score': 0.0, 'description': 'Erro na análise'}

    def start_monitoring(self, symbols: List[str] = None, interval: int = 300):
        """Iniciar monitoramento contínuo de sentimento"""
        if symbols is None:
            symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL']

        def monitor_sentiment():
            while True:
                try:
                    for symbol in symbols:
                        sentiment_data = self.get_comprehensive_sentiment(symbol)
                        self.save_sentiment_data(sentiment_data)
                        print(f"📊 Sentimento {symbol}: {sentiment_data.overall_sentiment:.3f}")

                    # Verificar alertas
                    self._check_sentiment_alerts(symbols)

                except Exception as e:
                    print(f"❌ Erro no monitoramento: {e}")

                time.sleep(interval)

        # Iniciar thread de monitoramento
        monitor_thread = threading.Thread(target=monitor_sentiment, daemon=True)
        monitor_thread.start()
        print(f"🟢 Monitoramento de sentimento iniciado para: {', '.join(symbols)}")

    def _check_sentiment_alerts(self, symbols: List[str]):
        """Verificar alertas de sentimento"""
        try:
            market_mood = self.get_market_mood()

            # Alertas baseados no humor do mercado
            if market_mood['mood'] in ['euphoric', 'panicked']:
                print(f"⚠️  ALERTA: Mercado em {market_mood['mood']} - {market_mood['description']}")

            # Verificar mudanças abruptas de sentimento
            for symbol in symbols:
                trend = self.get_sentiment_trend(symbol, 12)  # últimas 12 horas
                if abs(trend['change']) > 0.3:
                    print(f"⚠️  ALERTA: Mudança abrupta de sentimento {symbol}: {trend['change']:.3f}")

        except Exception as e:
            print(f"❌ Erro na verificação de alertas: {e}")

# API para integração com o painel principal
def create_sentiment_analyzer():
    """Criar instância do analisador de sentimento"""
    return SentimentAnalyzer()

if __name__ == "__main__":
    # Teste do analisador
    analyzer = create_sentiment_analyzer()

    # Teste de análise
    sentiment = analyzer.get_comprehensive_sentiment("BTC")
    print(f"Sentimento BTC: {sentiment}")

    # Teste de humor do mercado
    market_mood = analyzer.get_market_mood()
    print(f"Humor do mercado: {market_mood}")

    # Iniciar monitoramento
    analyzer.start_monitoring(['BTC', 'ETH'], interval=60)
