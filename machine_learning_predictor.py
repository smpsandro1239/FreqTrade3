#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 SISTEMA DE MACHINE LEARNING - FREQTRADE3
Análise preditiva com algoritmos de ML para otimização de estratégias
"""

import json
import os
import warnings
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

class MLTradingAnalyzer:
    """Sistema de análise preditiva para trading"""

    def __init__(self, model_dir='models/'):
        self.model_dir = model_dir
        self.models = {}
        self.scalers = {}
        self.feature_names = []

        # Criar diretório para modelos
        os.makedirs(model_dir, exist_ok=True)

        # Carregar modelos existentes
        self.load_models()

    def create_features(self, df):
        """Criar features para ML baseadas em dados históricos"""
        features = df.copy()

        # Features de preço
        features['price_change'] = df['close'].pct_change()
        features['high_low_ratio'] = df['high'] / df['low']
        features['open_close_ratio'] = df['open'] / df['close']

        # Features de volume
        features['volume_ma'] = df['volume'].rolling(window=10).mean()
        features['volume_ratio'] = df['volume'] / features['volume_ma']

        # Features técnicas
        if 'rsi' in df.columns:
            features['rsi_overbought'] = (df['rsi'] > 70).astype(int)
            features['rsi_oversold'] = (df['rsi'] < 30).astype(int)

        if 'ema_12' in df.columns:
            features['ema_spread'] = df['ema_12'] - df.get('ema_26', df['ema_12'])
            features['price_ema_ratio'] = df['close'] / df['ema_12']

        # Features de volatilidade
        features['volatility'] = df['close'].rolling(window=10).std()
        features['volatility_ratio'] = features['volatility'] / features['volatility'].rolling(window=50).mean()

        # Features de tempo
        features['hour'] = pd.to_datetime(features.index).hour
        features['day_of_week'] = pd.to_datetime(features.index).dayofweek
        features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)

        # Features de momentum
        features['momentum_3'] = df['close'] / df['close'].shift(3) - 1
        features['momentum_7'] = df['close'] / df['close'].shift(7) - 1
        features['momentum_14'] = df['close'] / df['close'].shift(14) - 1

        return features

    def train_prediction_model(self, df, target='future_return_24h', model_type='random_forest'):
        """Treinar modelo de predição"""
        print(f"🤖 Treinando modelo {model_type} para predição de {target}")

        # Preparar dados
        features = self.create_features(df)

        # Criar target (retorno futuro 24h)
        features[target] = (df['close'].shift(-24) / df['close'] - 1) * 100

        # Remover valores nulos
        features = features.dropna()

        if len(features) < 100:
            print("❌ Dados insuficientes para treinamento")
            return None

        # Selecionar features numéricas
        feature_columns = features.select_dtypes(include=[np.number]).columns
        feature_columns = [col for col in feature_columns if col != target]

        X = features[feature_columns].fillna(0)
        y = features[target]

        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Escalonamento
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Treinar modelo
        if model_type == 'random_forest':
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif model_type == 'linear_regression':
            model = LinearRegression()
        else:
            raise ValueError(f"Tipo de modelo não suportado: {model_type}")

        model.fit(X_train_scaled, y_train)

        # Avaliar modelo
        y_pred = model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"📊 Modelo treinado - MSE: {mse:.4f}, R²: {r2:.4f}")

        # Salvar modelo
        model_name = f"{target}_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        joblib.dump(model, f"{self.model_dir}{model_name}.pkl")
        joblib.dump(scaler, f"{self.model_dir}{model_name}_scaler.pkl")

        # Salvar metadados
        metadata = {
            'model_name': model_name,
            'model_type': model_type,
            'target': target,
            'features': feature_columns,
            'mse': mse,
            'r2': r2,
            'training_date': datetime.now().isoformat(),
            'data_points': len(features)
        }

        with open(f"{self.model_dir}{model_name}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        # Manter referência ao modelo
        self.models[model_name] = model
        self.scalers[model_name] = scaler
        self.feature_names = feature_columns

        return model_name

    def predict(self, df, model_name):
        """Fazer predição com modelo treinado"""
        if model_name not in self.models:
            print(f"❌ Modelo {model_name} não encontrado")
            return None

        model = self.models[model_name]
        scaler = self.scalers[model_name]

        # Preparar dados
        features = self.create_features(df)

        # Selecionar features
        X = features[self.feature_names].fillna(0).iloc[-1:]  # Último período

        # Fazer predição
        X_scaled = scaler.transform(X)
        prediction = model.predict(X_scaled)[0]

        return {
            'prediction': prediction,
            'confidence': 'medium',  # Pode ser melhorado com ensemble
            'timestamp': datetime.now().isoformat()
        }

    def load_models(self):
        """Carregar modelos salvos"""
        if not os.path.exists(self.model_dir):
            return

        for file in os.listdir(self.model_dir):
            if file.endswith('_metadata.json'):
                try:
                    with open(f"{self.model_dir}{file}", 'r') as f:
                        metadata = json.load(f)

                    model_name = metadata['model_name']

                    # Carregar modelo e scaler
                    model = joblib.load(f"{self.model_dir}{model_name}.pkl")
                    scaler = joblib.load(f"{self.model_dir}{model_name}_scaler.pkl")

                    self.models[model_name] = model
                    self.scalers[model_name] = scaler

                    print(f"✅ Modelo {model_name} carregado")

                except Exception as e:
                    print(f"❌ Erro ao carregar modelo {file}: {e}")

    def get_feature_importance(self, model_name):
        """Obter importância das features"""
        if model_name not in self.models:
            return None

        model = self.models[model_name]

        if hasattr(model, 'feature_importances_'):
            importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)

            return importance
        else:
            return None

    def generate_trading_signals(self, df, model_name, threshold=0.5):
        """Gerar sinais de trading baseados em ML"""
        prediction = self.predict(df, model_name)

        if prediction is None:
            return None

        signal = 'hold'
        confidence = abs(prediction['prediction'])

        if prediction['prediction'] > threshold:
            signal = 'buy'
        elif prediction['prediction'] < -threshold:
            signal = 'sell'

        return {
            'signal': signal,
            'confidence': confidence,
            'predicted_return': prediction['prediction'],
            'model': model_name,
            'timestamp': prediction['timestamp']
        }

def demo_ml_analysis():
    """Demonstração do sistema ML"""
    print("🤖 DEMO - Sistema de Machine Learning")
    print("=" * 50)

    # Criar dados de exemplo
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', '2024-11-07', freq='1H')

    # Simular dados de mercado
    n = len(dates)
    base_price = 50000
    price_changes = np.random.normal(0, 0.001, n)
    prices = [base_price]

    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)

    df = pd.DataFrame({
        'timestamp': dates,
        'open': [p * (1 + np.random.normal(0, 0.0005)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': prices,
        'volume': np.random.lognormal(10, 1, n)
    })

    df.set_index('timestamp', inplace=True)

    # Adicionar indicadores técnicos
    df['rsi'] = 50 + np.random.normal(0, 15, n)
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()

    # Inicializar sistema ML
    ml_analyzer = MLTradingAnalyzer()

    # Treinar modelo
    print("🔄 Treinando modelo de predição...")
    model_name = ml_analyzer.train_prediction_model(df, model_type='random_forest')

    if model_name:
        print(f"✅ Modelo {model_name} treinado com sucesso!")

        # Fazer predição
        prediction = ml_analyzer.predict(df, model_name)
        if prediction:
            print(f"📈 Predição: {prediction['prediction']:.2f}% (próximas 24h)")

        # Gerar sinal de trading
        signal = ml_analyzer.generate_trading_signals(df, model_name)
        if signal:
            print(f"🎯 Sinal: {signal['signal']} (confiança: {signal['confidence']:.2f})")

        # Importância das features
        importance = ml_analyzer.get_feature_importance(model_name)
        if importance is not None:
            print("\n📊 Top 5 Features Mais Importantes:")
            for _, row in importance.head().iterrows():
                print(f"  {row['feature']}: {row['importance']:.4f}")

    print("\n🎉 Demo concluído!")

if __name__ == "__main__":
    demo_ml_analysis()
