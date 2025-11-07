#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 SISTEMA DE INTEGRAÇÃO CENTRAL - FREQTRADE3
Orquestrador principal que coordena todos os módulos avançados
"""

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import schedule

from advanced_portfolio_analytics import AdvancedPortfolioAnalyzer
from advanced_risk_manager import AdvancedRiskManager, RiskLevel
# Importar módulos avançados
from machine_learning_predictor import MLTradingAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from smart_notifications import NotificationPriority, SmartNotificationManager


class SystemStatus(Enum):
    """Status do sistema"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class SystemMetrics:
    """Métricas do sistema"""
    uptime: float
    cpu_usage: float
    memory_usage: float
    active_strategies: int
    active_positions: int
    total_pnl: float
    daily_pnl: float
    portfolio_value: float
    risk_score: float
    system_health: str
    last_updated: datetime

class FreqTrade3CentralOrchestrator:
    """Orquestrador central do FreqTrade3"""

    def __init__(self, config_file='config/central_config.json'):
        self.config = self.load_config(config_file)
        self.status = SystemStatus.INITIALIZING
        self.start_time = datetime.now()

        # Inicializar módulos avançados
        self.ml_analyzer = None
        self.sentiment_analyzer = None
        self.risk_manager = None
        self.portfolio_analyzer = None
        self.notification_manager = None

        # Dados de sistema
        self.system_metrics = SystemMetrics(
            uptime=0, cpu_usage=0, memory_usage=0, active_strategies=0,
            active_positions=0, total_pnl=0, daily_pnl=0, portfolio_value=0,
            risk_score=0, system_health="unknown", last_updated=datetime.now()
        )

        # Estado das estratégias
        self.active_strategies = {}
        self.positions = {}
        self.market_data_cache = {}

        # Threading
        self.running = False
        self.threads = {}

        # Logging
        self.setup_logging()

    def load_config(self, config_file):
        """Carregar configuração central"""
        default_config = {
            "system": {
                "update_interval_seconds": 30,
                "max_concurrent_strategies": 5,
                "enable_ml_predictions": True,
                "enable_sentiment_analysis": True,
                "enable_risk_monitoring": True,
                "enable_portfolio_analytics": True,
                "enable_smart_notifications": True
            },
            "ml": {
                "model_retrain_hours": 24,
                "prediction_confidence_threshold": 0.7,
                "features_window_days": 30
            },
            "sentiment": {
                "update_interval_hours": 1,
                "confidence_threshold": 0.6,
                "sources": ["news", "social_media"]
            },
            "risk": {
                "max_portfolio_risk": 0.02,
                "var_confidence": 0.95,
                "alert_thresholds": {
                    "volatility": 0.4,
                    "drawdown": 0.15,
                    "correlation": 0.8
                }
            },
            "portfolio": {
                "rebalance_frequency": "weekly",
                "optimization_interval": "daily",
                "benchmark": "BTC"
            },
            "notifications": {
                "global_cooldown_minutes": 5,
                "emergency_contacts": [],
                "channels": {
                    "telegram": False,
                    "email": False,
                    "discord": False
                }
            }
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Merge com padrão
                self.merge_config(default_config, config)
                return default_config
            else:
                return default_config
        except Exception as e:
            self.logger.error(f"Erro ao carregar config: {e}, usando padrão")
            return default_config

    def merge_config(self, default, custom):
        """Mergear configurações"""
        for key, value in custom.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self.merge_config(default[key], value)
            else:
                default[key] = value

    def setup_logging(self):
        """Configurar sistema de logging"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/orchestrator.log'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger('FreqTrade3-Orchestrator')

    async def initialize_modules(self):
        """Inicializar todos os módulos"""
        self.logger.info("🚀 Inicializando módulos do FreqTrade3...")

        try:
            # Machine Learning
            if self.config['system']['enable_ml_predictions']:
                self.ml_analyzer = MLTradingAnalyzer()
                self.logger.info("✅ ML Analyzer inicializado")

            # Sentiment Analysis
            if self.config['system']['enable_sentiment_analysis']:
                self.sentiment_analyzer = SentimentAnalyzer()
                self.logger.info("✅ Sentiment Analyzer inicializado")

            # Risk Management
            if self.config['system']['enable_risk_monitoring']:
                self.risk_manager = AdvancedRiskManager()
                self.logger.info("✅ Risk Manager inicializado")

            # Portfolio Analytics
            if self.config['system']['enable_portfolio_analytics']:
                self.portfolio_analyzer = AdvancedPortfolioAnalyzer()
                self.logger.info("✅ Portfolio Analyzer inicializado")

            # Smart Notifications
            if self.config['system']['enable_smart_notifications']:
                self.notification_manager = SmartNotificationManager()
                self.logger.info("✅ Notification Manager inicializado")

            self.status = SystemStatus.RUNNING
            self.logger.info("🎉 Todos os módulos inicializados com sucesso!")

        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização: {e}")
            self.status = SystemStatus.ERROR

    async def market_data_processor(self):
        """Processador de dados de mercado em tempo real"""
        while self.running:
            try:
                # Simular dados de mercado (em produção, conectar com exchange)
                for symbol in ['BTC', 'ETH', 'BNB', 'ADA', 'XRP']:
                    if symbol not in self.market_data_cache:
                        self.market_data_cache[symbol] = []

                    # Adicionar novo dado simulado
                    new_data = {
                        'timestamp': datetime.now(),
                        'price': 50000 + (hash(symbol) % 10000),  # Preço simulado
                        'volume': 1000000 + (hash(symbol) % 500000),
                        'volatility': 0.02 + (hash(symbol) % 100) / 1000
                    }

                    self.market_data_cache[symbol].append(new_data)

                    # Manter apenas últimos 1000 pontos
                    if len(self.market_data_cache[symbol]) > 1000:
                        self.market_data_cache[symbol] = self.market_data_cache[symbol][-1000:]

                await asyncio.sleep(self.config['system']['update_interval_seconds'])

            except Exception as e:
                self.logger.error(f"Erro no processador de mercado: {e}")
                await asyncio.sleep(5)

    async def ml_prediction_processor(self):
        """Processador de predições ML"""
        if not self.ml_analyzer:
            return

        while self.running:
            try:
                for symbol in self.market_data_cache:
                    if len(self.market_data_cache[symbol]) > 100:
                        # Preparar dados para ML
                        data_df = self.prepare_market_data_for_ml(symbol)

                        if data_df is not None:
                            # Fazer predição
                            model_name = f"{symbol}_prediction_model"
                            prediction = self.ml_analyzer.predict(data_df, model_name)

                            if prediction:
                                self.logger.info(f"🤖 ML Prediction {symbol}: {prediction['prediction']:.2f}%")

                                # Gerar sinal se confiança alta
                                if prediction.get('confidence', 0) > self.config['ml']['prediction_confidence_threshold']:
                                    signal = self.ml_analyzer.generate_trading_signals(
                                        data_df, model_name, threshold=0.5
                                    )

                                    if signal and signal['signal'] in ['buy', 'sell']:
                                        await self.handle_trading_signal(signal, symbol)

                await asyncio.sleep(300)  # A cada 5 minutos

            except Exception as e:
                self.logger.error(f"Erro no processador ML: {e}")
                await asyncio.sleep(30)

    async def sentiment_processor(self):
        """Processador de análise de sentimento"""
        if not self.sentiment_analyzer:
            return

        while self.running:
            try:
                # Analisar sentimento para principais cryptos
                for symbol in ['BTC', 'ETH', 'BNB']:
                    sentiment_data = self.sentiment_analyzer.get_sentiment_for_trading(symbol)

                    if sentiment_data:
                        self.logger.info(f"🎭 Sentiment {symbol}: {sentiment_data['sentiment_score']:.2f}")

                        # Se sentimento muito positivo/negativo, gerar alerta
                        if abs(sentiment_data['sentiment_score']) > 0.7:
                            await self.handle_sentiment_alert(sentiment_data)

                await asyncio.sleep(3600)  # A cada hora

            except Exception as e:
                self.logger.error(f"Erro no processador de sentimento: {e}")
                await asyncio.sleep(300)

    async def risk_monitor_processor(self):
        """Monitor de risco em tempo real"""
        if not self.risk_manager:
            return

        while self.running:
            try:
                # Preparar posições para análise de risco
                positions = []
                for pos_id, position in self.positions.items():
                    current_price = self.get_current_price(position['symbol'])
                    if current_price:
                        positions.append({
                            'symbol': position['symbol'],
                            'size': position['size'],
                            'entry_price': position['entry_price'],
                            'side': position['side'],
                            'leverage': position.get('leverage', 1.0)
                        })

                if positions:
                    # Análise de risco do portfólio
                    market_data = {symbol: self.market_data_cache.get(symbol, [])
                                 for symbol in set(pos['symbol'] for pos in positions)}

                    risk_metrics = self.risk_manager.assess_portfolio_risk(positions, market_data)

                    # Atualizar métricas do sistema
                    self.system_metrics.risk_score = min(1.0, abs(risk_metrics.max_drawdown))

                    # Verificar alertas de risco
                    if risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                        await self.handle_risk_alert(risk_metrics)

                    self.logger.info(f"🛡️ Risk Level: {risk_metrics.risk_level.value.upper()}")

                await asyncio.sleep(120)  # A cada 2 minutos

            except Exception as e:
                self.logger.error(f"Erro no monitor de risco: {e}")
                await asyncio.sleep(60)

    async def portfolio_analytics_processor(self):
        """Processador de analytics de portfólio"""
        if not self.portfolio_analyzer:
            return

        while self.running:
            try:
                # Simular retornos de portfólio
                portfolio_returns = self.calculate_portfolio_returns()

                if len(portfolio_returns) > 30:
                    # Análise de performance
                    metrics = self.portfolio_analyzer.calculate_portfolio_metrics(
                        portfolio_returns, self.portfolio_analyzer.benchmark_data.pct_history()
                    )

                    # Gerar relatório
                    report = self.portfolio_analyzer.generate_portfolio_report(
                        portfolio_returns, self.get_current_allocation()
                    )

                    # Salvar relatório
                    await self.save_portfolio_report(report)

                    self.logger.info(f"📊 Portfolio Score: {report['summary_score']}/100")

                await asyncio.sleep(3600)  # A cada hora

            except Exception as e:
                self.logger.error(f"Erro no processador de analytics: {e}")
                await asyncio.sleep(300)

    def prepare_market_data_for_ml(self, symbol: str):
        """Preparar dados de mercado para ML"""
        data = self.market_data_cache.get(symbol, [])
        if len(data) < 50:
            return None

        try:
            import pandas as pd
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)

            # Adicionar indicadores técnicos
            df['rsi'] = self.calculate_rsi(df['price'])
            df['ema_12'] = df['price'].ewm(span=12).mean()
            df['ema_26'] = df['price'].ewm(span=26).mean()

            return df
        except Exception as e:
            self.logger.error(f"Erro ao preparar dados para ML {symbol}: {e}")
            return None

    def calculate_rsi(self, prices, period=14):
        """Calcular RSI simplificado"""
        deltas = prices.diff()
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)

        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()

        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Obter preço atual de um símbolo"""
        data = self.market_data_cache.get(symbol, [])
        if data:
            return data[-1]['price']
        return None

    def calculate_portfolio_returns(self):
        """Calcular retornos do portfólio"""
        # Implementação simplificada
        import numpy as np
        import pandas as pd

        dates = pd.date_range('2024-01-01', datetime.now(), freq='1D')
        returns = np.random.normal(0.001, 0.02, len(dates))  # Simulated returns

        return pd.Series(returns, index=dates)

    def get_current_allocation(self) -> Dict[str, float]:
        """Obter alocação atual do portfólio"""
        if not self.positions:
            return {'BTC': 0.4, 'ETH': 0.3, 'BNB': 0.2, 'ADA': 0.1}

        # Calcular baseado em posições ativas
        total_value = sum(pos['size'] * pos['entry_price'] for pos in self.positions.values())
        allocation = {}

        for pos in self.positions.values():
            value = pos['size'] * pos['entry_price']
            allocation[pos['symbol']] = value / total_value if total_value > 0 else 0

        return allocation

    async def handle_trading_signal(self, signal: Dict, symbol: str):
        """Manipular sinal de trading"""
        self.logger.info(f"🎯 Trading Signal: {symbol} - {signal['signal']} (confidence: {signal['confidence']:.2f})")

        # Aqui seria integrado com o sistema de trading principal
        # Por enquanto, apenas log
        if self.notification_manager:
            event_data = {
                'symbol': symbol,
                'action': signal['signal'].upper(),
                'quantity': 0.1,  # Default
                'price': self.get_current_price(symbol),
                'pnl': 0,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }

            self.notification_manager.process_trading_event('trade_executed', event_data)

    async def handle_sentiment_alert(self, sentiment_data: Dict):
        """Manipular alerta de sentimento"""
        self.logger.info(f"🎭 Sentiment Alert: {sentiment_data['symbol']} - {sentiment_data['sentiment_label']}")

        if self.notification_manager:
            await self.notification_manager.send_notification(
                type('Event', (), {
                    'title': f'Sentiment Alert - {sentiment_data["symbol"]}',
                    'message': f'Sentiment: {sentiment_data["sentiment_score"]:.2f} ({sentiment_data["sentiment_label"]})',
                    'priority': NotificationPriority.HIGH if abs(sentiment_data['sentiment_score']) > 0.8 else NotificationPriority.MEDIUM
                })()
            )

    async def handle_risk_alert(self, risk_metrics):
        """Manipular alerta de risco"""
        self.logger.warning(f"🛡️ Risk Alert: {risk_metrics.risk_level.value.upper()}")

        if self.notification_manager:
            event_data = {
                'risk_level': risk_metrics.risk_level.value.upper(),
                'reason': f'Max Drawdown: {risk_metrics.max_drawdown:.2%}, VaR: {risk_metrics.var_95:.2%}',
                'risk_score': abs(risk_metrics.max_drawdown),
                'recommendation': 'Considere reduzir posições'
            }

            self.notification_manager.process_trading_event('high_risk', event_data)

    async def save_portfolio_report(self, report: Dict):
        """Salvar relatório de portfólio"""
        try:
            reports_dir = "reports"
            os.makedirs(reports_dir, exist_ok=True)

            filename = f"{reports_dir}/portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"📊 Relatório salvo: {filename}")

        except Exception as e:
            self.logger.error(f"Erro ao salvar relatório: {e}")

    def update_system_metrics(self):
        """Atualizar métricas do sistema"""
        import psutil

        # Calcular uptime
        self.system_metrics.uptime = (datetime.now() - self.start_time).total_seconds()

        # Recursos do sistema
        self.system_metrics.cpu_usage = psutil.cpu_percent()
        self.system_metrics.memory_usage = psutil.virtual_memory().percent

        # Métricas de trading
        self.system_metrics.active_strategies = len(self.active_strategies)
        self.system_metrics.active_positions = len(self.positions)

        # P&L (simulado)
        self.system_metrics.total_pnl = sum(
            pos.get('unrealized_pnl', 0) for pos in self.positions.values()
        )

        # Portfolio value (simulado)
        self.system_metrics.portfolio_value = 100000 + self.system_metrics.total_pnl

        # Health status
        if self.system_metrics.cpu_usage < 80 and self.system_metrics.memory_usage < 80:
            self.system_metrics.system_health = "healthy"
        elif self.system_metrics.cpu_usage < 95 and self.system_metrics.memory_usage < 95:
            self.system_metrics.system_health = "warning"
        else:
            self.system_metrics.system_health = "critical"

        self.system_metrics.last_updated = datetime.now()

    async def system_health_monitor(self):
        """Monitor de saúde do sistema"""
        while self.running:
            try:
                self.update_system_metrics()

                # Verificar se está tudo OK
                if (self.system_metrics.cpu_usage > 95 or
                    self.system_metrics.memory_usage > 95):
                    self.logger.warning("⚠️ High resource usage detected")
                    if self.notification_manager:
                        # Enviar alerta de sistema
                        pass

                await asyncio.sleep(60)  # A cada minuto

            except Exception as e:
                self.logger.error(f"Erro no monitor de saúde: {e}")
                await asyncio.sleep(30)

    def get_system_status(self) -> Dict:
        """Obter status completo do sistema"""
        return {
            'status': self.status.value,
            'uptime_seconds': self.system_metrics.uptime,
            'health': self.system_metrics.system_health,
            'active_strategies': self.system_metrics.active_strategies,
            'active_positions': self.system_metrics.active_positions,
            'portfolio_value': self.system_metrics.portfolio_value,
            'total_pnl': self.system_metrics.total_pnl,
            'risk_score': self.system_metrics.risk_score,
            'modules': {
                'ml_analyzer': self.ml_analyzer is not None,
                'sentiment_analyzer': self.sentiment_analyzer is not None,
                'risk_manager': self.risk_manager is not None,
                'portfolio_analyzer': self.portfolio_analyzer is not None,
                'notification_manager': self.notification_manager is not None
            },
            'last_updated': self.system_metrics.last_updated.isoformat()
        }

    async def start(self):
        """Iniciar orquestrador"""
        if self.running:
            self.logger.warning("Sistema já está rodando")
            return

        self.logger.info("🚀 Iniciando FreqTrade3 Central Orchestrator...")

        # Inicializar módulos
        await self.initialize_modules()

        if self.status == SystemStatus.ERROR:
            self.logger.error("❌ Falha na inicialização, abortando")
            return

        self.running = True

        # Criar tasks
        tasks = [
            self.market_data_processor(),
            self.ml_prediction_processor(),
            self.sentiment_processor(),
            self.risk_monitor_processor(),
            self.portfolio_analytics_processor(),
            self.system_health_monitor()
        ]

        # Executar todos os tasks
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Parar orquestrador"""
        self.logger.info("🛑 Parando FreqTrade3 Central Orchestrator...")
        self.running = False
        self.status = SystemStatus.PAUSED
        self.logger.info("✅ Orquestrador parado")

    def run(self):
        """Executar orquestrador (síncrono)"""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            self.logger.info("🛑 Interrompido pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro fatal: {e}")
            self.status = SystemStatus.ERROR

async def main():
    """Função principal"""
    print("🚀 FREQTRADE3 - CENTRAL ORCHESTRATOR")
    print("=" * 50)

    # Criar e iniciar orquestrador
    orchestrator = FreqTrade3CentralOrchestrator()

    # Configurar graceful shutdown
    import signal
    def signal_handler(signum, frame):
        print("\n🛑 Recebido sinal de parada...")
        await orchestrator.stop()
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await orchestrator.start()
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        print("👋 FreqTrade3 Orchestrator finalizado")

if __name__ == "__main__":
    asyncio.run(main())
