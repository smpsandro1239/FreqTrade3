#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭 SISTEMA DE ANÁLISE DE SENTIMENTO - FREQTRADE3
Análise de sentimentos de redes sociais e notícias para trading
"""

import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from textblob import TextBlob


class SentimentAnalyzer:
    """Analisador de sentimentos para mercado de crypto"""

    def __init__(self, cache_dir='data/sentiment/'):
        self.cache_dir = cache_dir
        self.sentiment_scores = {}
        self.news_sources = [
            'coindesk',
            'cointelegraph',
            'decrypt',
            'theblock',
            'messaricrypto'
        ]

        # Criar diretório de cache
        os.makedirs(cache_dir, exist_ok=True)

        # Palavras-chave relacionadas a crypto
        self.crypto_keywords = {
            'bullish': ['bull', 'moon', 'pump', 'buy', 'up', 'gain', 'profit', 'rise', 'surge'],
            'bearish': ['bear', 'dump', 'sell', 'down', 'loss', 'fall', 'crash', 'decline'],
            'news_positive': ['adoption', 'partnership', 'listing', 'upgrade', 'launch', 'milestone'],
            'news_negative': ['hack', 'ban', 'regulation', 'scam', 'fraud', 'investigation']
        }

    def fetch_crypto_news(self, query='bitcoin', limit=50):
        """Buscar notícias sobre crypto (simulado para demo)"""
        # Para demo, vamos simular notícias
        simulated_news = [
            {
                'title': 'Bitcoin reaches new all-time high as institutional adoption grows',
                'description': 'Major financial institutions continue to invest in Bitcoin, driving price up',
                'sentiment': 'positive',
                'source': 'coindesk',
                'timestamp': datetime.now() - timedelta(hours=1)
            },
            {
                'title': 'Crypto market shows strong bullish momentum',
                'description': 'Technical analysis suggests continued upward movement',
                'sentiment': 'positive',
                'source': 'cointelegraph',
                'timestamp': datetime.now() - timedelta(hours=2)
            },
            {
                'title': 'Regulatory uncertainty weighs on crypto markets',
                'description': 'New regulations create uncertainty among investors',
                'sentiment': 'negative',
                'source': 'decrypt',
                'timestamp': datetime.now() - timedelta(hours=3)
            }
        ]

        return simulated_news[:limit]

    def analyze_text_sentiment(self, text):
        """Analisar sentimento de um texto usando TextBlob"""
        if not text:
            return 0.0

        # Análise com TextBlob
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 (negativo) a 1 (positivo)

        # Análise customizada com palavras-chave
        text_lower = text.lower()
        bullish_score = sum(1 for word in self.crypto_keywords['bullish'] if word in text_lower)
        bearish_score = sum(1 for word in self.crypto_keywords['bearish'] if word in text_lower)

        # Ajustar polaridade com palavras-chave
        keyword_adjustment = (bullish_score - bearish_score) * 0.1
        final_score = polarity + keyword_adjustment

        # Normalizar para -1 a 1
        return max(-1, min(1, final_score))

    def analyze_social_sentiment(self, symbol='BTC'):
        """Analisar sentimento de redes sociais (simulado)"""
        # Simular dados do Twitter/Reddit
        simulated_tweets = [
            "Bitcoin is looking very bullish! Time to buy the dip! 📈",
            "Just accumulated more BTC. HODLing for the moon! 🚀",
            "Market seems uncertain about crypto regulations..."
        ]

        sentiment_scores = []
        for tweet in simulated_tweets:
            score = self.analyze_text_sentiment(tweet)
            sentiment_scores.append(score)

        # Calcular média ponderada
        avg_sentiment = np.mean(sentiment_scores)
        confidence = 1 - np.std(sentiment_scores)  # Baixa variância = alta confiança

        return {
            'sentiment': avg_sentiment,
            'confidence': max(0, confidence),
            'sample_size': len(sentiment_scores),
            'source': 'social_media',
            'timestamp': datetime.now().isoformat()
        }

    def analyze_news_sentiment(self, symbol='BTC'):
        """Analisar sentimento de notícias"""
        try:
            news = self.fetch_crypto_news(symbol)

            sentiment_scores = []
            headlines = []

            for article in news:
                title_sentiment = self.analyze_text_sentiment(article['title'])
                desc_sentiment = self.analyze_text_sentiment(article.get('description', ''))

                # Ponderar título mais que descrição
                article_sentiment = (title_sentiment * 0.7) + (desc_sentiment * 0.3)
                sentiment_scores.append(article_sentiment)
                headlines.append(article['title'])

            if not sentiment_scores:
                return {
                    'sentiment': 0.0,
                    'confidence': 0.0,
                    'sample_size': 0,
                    'source': 'news',
                    'timestamp': datetime.now().isoformat()
                }

            avg_sentiment = np.mean(sentiment_scores)
            confidence = min(1, len(sentiment_scores) / 10)  # Mais artigos = mais confiança

            return {
                'sentiment': avg_sentiment,
                'confidence': confidence,
                'sample_size': len(sentiment_scores),
                'headlines': headlines[:5],  # Top 5 headlines
                'source': 'news',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ Erro ao analisar notícias: {e}")
            return {
                'sentiment': 0.0,
                'confidence': 0.0,
                'sample_size': 0,
                'source': 'news',
                'timestamp': datetime.now().isoformat()
            }

    def get_combined_sentiment(self, symbol='BTC'):
        """Combinar análise de sentimentos de múltiplas fontes"""
        try:
            # Análise de notícias
            news_sentiment = self.analyze_news_sentiment(symbol)

            # Análise de redes sociais
            social_sentiment = self.analyze_social_sentiment(symbol)

            # Combinar com pesos
            if news_sentiment['sample_size'] > 0 and social_sentiment['sample_size'] > 0:
                # Peso 60% notícias, 40% redes sociais
                combined_sentiment = (
                    news_sentiment['sentiment'] * 0.6 * news_sentiment['confidence'] +
                    social_sentiment['sentiment'] * 0.4 * social_sentiment['confidence']
                )

                # Calcular confiança combinada
                combined_confidence = (
                    news_sentiment['confidence'] * 0.6 +
                    social_sentiment['confidence'] * 0.4
                )
            else:
                combined_sentiment = 0.0
                combined_confidence = 0.0

            # Classificar sentimento
            if combined_sentiment > 0.2:
                sentiment_label = 'very_positive'
            elif combined_sentiment > 0.05:
                sentiment_label = 'positive'
            elif combined_sentiment > -0.05:
                sentiment_label = 'neutral'
            elif combined_sentiment > -0.2:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'very_negative'

            result = {
                'symbol': symbol,
                'sentiment_score': combined_sentiment,
                'sentiment_label': sentiment_label,
                'confidence': combined_confidence,
                'news_sentiment': news_sentiment,
                'social_sentiment': social_sentiment,
                'timestamp': datetime.now().isoformat()
            }

            # Salvar no cache
            self.save_sentiment_cache(symbol, result)

            return result

        except Exception as e:
            print(f"❌ Erro ao obter sentimento combinado: {e}")
            return None

    def save_sentiment_cache(self, symbol, data):
        """Salvar dados de sentimento no cache"""
        try:
            cache_file = f"{self.cache_dir}{symbol.lower()}_sentiment.json"
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Erro ao salvar cache: {e}")

    def load_sentiment_cache(self, symbol):
        """Carregar dados de sentimento do cache"""
        try:
            cache_file = f"{self.cache_dir}{symbol.lower()}_sentiment.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    data = json.load(f)

                # Verificar se o cache não é muito antigo (1 hora)
                cache_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cache_time < timedelta(hours=1):
                    return data

            return None
        except Exception as e:
            print(f"❌ Erro ao carregar cache: {e}")
            return None

    def get_sentiment_for_trading(self, symbol='BTC'):
        """Obter sentimento formatado para decisões de trading"""
        sentiment_data = self.get_combined_sentiment(symbol)

        if not sentiment_data:
            return None

        # Converter sentimento em sinal de trading
        score = sentiment_data['sentiment_score']
        confidence = sentiment_data['confidence']

        if score > 0.3 and confidence > 0.7:
            signal = 'strong_buy'
        elif score > 0.1 and confidence > 0.5:
            signal = 'buy'
        elif score < -0.3 and confidence > 0.7:
            signal = 'strong_sell'
        elif score < -0.1 and confidence > 0.5:
            signal = 'sell'
        else:
            signal = 'hold'

        return {
            'symbol': symbol,
            'trading_signal': signal,
            'sentiment_score': score,
            'confidence': confidence,
            'sentiment_label': sentiment_data['sentiment_label'],
            'recommendation': self.get_trading_recommendation(signal, score, confidence),
            'timestamp': sentiment_data['timestamp']
        }

    def get_trading_recommendation(self, signal, score, confidence):
        """Gerar recomendação de trading baseada em sentimento"""
        recommendations = {
            'strong_buy': f"🔥 SENTIMENTO MUITO POSITIVO! Score: {score:.2f}, Confiança: {confidence:.2f} - Considere posição long",
            'buy': f"📈 Sentimento positivo. Score: {score:.2f}, Confiança: {confidence:.2f} - Oportunidade de compra",
            'hold': f"⏸️ Sentimento neutro. Score: {score:.2f}, Confiança: {confidence:.2f} - Aguardar melhor momento",
            'sell': f"📉 Sentimento negativo. Score: {score:.2f}, Confiança: {confidence:.2f} - Considere reduzir posições",
            'strong_sell': f"❌ SENTIMENTO MUITO NEGATIVO! Score: {score:.2f}, Confiança: {confidence:.2f} - Considere posição short"
        }

        return recommendations.get(signal, "Sentimento indefinido")

def demo_sentiment_analysis():
    """Demonstração do sistema de análise de sentimento"""
    print("🎭 DEMO - Sistema de Análise de Sentimento")
    print("=" * 50)

    # Inicializar analisador
    sentiment_analyzer = SentimentAnalyzer()

    # Analisar sentimento para Bitcoin
    print("🔍 Analisando sentimento do Bitcoin...")
    result = sentiment_analyzer.get_sentiment_for_trading('BTC')

    if result:
        print(f"📊 Símbolo: {result['symbol']}")
        print(f"🎯 Sinal: {result['trading_signal']}")
        print(f"📈 Score: {result['sentiment_score']:.3f}")
        print(f"💪 Confiança: {result['confidence']:.3f}")
        print(f"🏷️ Rótulo: {result['sentiment_label']}")
        print(f"💡 Recomendação: {result['recommendation']}")
        print(f"⏰ Timestamp: {result['timestamp']}")

    # Análise de notícias vs redes sociais
    print("\n📰 Análise Detalhada:")
    news_result = sentiment_analyzer.get_combined_sentiment('BTC')
    if news_result:
        print(f"📰 Notícias - Score: {news_result['news_sentiment']['sentiment']:.3f}")
        print(f"📱 Social - Score: {news_result['social_sentiment']['sentiment']:.3f}")

        if news_result['news_sentiment']['headlines']:
            print("\n🔥 Top Headlines:")
            for headline in news_result['news_sentiment']['headlines']:
                print(f"  • {headline}")

    print("\n🎉 Demo concluído!")

if __name__ == "__main__":
    demo_sentiment_analysis()
