#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛡️ SISTEMA DE RISK MANAGEMENT AVANÇADO - FREQTRADE3
Gerenciamento inteligente de risco com algoritmos avançados
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class RiskLevel(Enum):
    """Níveis de risco"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PositionType(Enum):
    """Tipos de posição"""
    LONG = "long"
    SHORT = "short"

@dataclass
class RiskMetrics:
    """Métricas de risco calculadas"""
    volatility: float
    var_95: float  # Value at Risk 95%
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float
    correlation: float
    risk_level: RiskLevel

@dataclass
class PositionRisk:
    """Risco de uma posição específica"""
    symbol: str
    position_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    risk_score: float
    max_loss_potential: float
    stop_loss_price: float
    take_profit_price: float
    risk_reward_ratio: float

class AdvancedRiskManager:
    """Gerenciador avançado de risco para trading"""

    def __init__(self, config_file='config/risk_config.json'):
        self.config = self.load_risk_config(config_file)
        self.risk_metrics = {}
        self.position_risks = {}
        self.max_portfolio_risk = self.config.get('max_portfolio_risk', 0.02)  # 2%
        self.max_single_position_risk = self.config.get('max_single_position_risk', 0.01)  # 1%

    def load_risk_config(self, config_file):
        """Carregar configuração de risco"""
        default_config = {
            "max_portfolio_risk": 0.02,
            "max_single_position_risk": 0.01,
            "max_positions": 10,
            "max_leverage": 3.0,
            "var_confidence": 0.95,
            "stop_loss_default": 0.02,
            "take_profit_default": 0.06,
            "risk_free_rate": 0.02,
            "correlation_threshold": 0.7,
            "volatility_threshold": 0.5
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return {**default_config, **config}
            else:
                return default_config
        except Exception as e:
            print(f"❌ Erro ao carregar config: {e}, usando padrão")
            return default_config

    def calculate_volatility(self, returns: pd.Series) -> float:
        """Calcular volatilidade annualized"""
        if len(returns) < 2:
            return 0.0

        volatility = returns.std() * np.sqrt(252)  # Annualized
        return float(volatility)

    def calculate_var(self, returns: pd.Series, confidence=0.95) -> float:
        """Calcular Value at Risk (VaR)"""
        if len(returns) < 10:
            return 0.0

        var = np.percentile(returns, (1 - confidence) * 100)
        return float(var)

    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calcular Maximum Drawdown"""
        if len(prices) < 2:
            return 0.0

        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        max_dd = drawdown.min()
        return float(max_dd)

    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate=0.02) -> float:
        """Calcular Sharpe Ratio"""
        if len(returns) < 2 or returns.std() == 0:
            return 0.0

        excess_returns = returns.mean() - risk_free_rate / 252  # Daily risk-free rate
        sharpe = excess_returns / returns.std() * np.sqrt(252)
        return float(sharpe)

    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate=0.02) -> float:
        """Calcular Sortino Ratio"""
        if len(returns) < 2:
            return 0.0

        excess_returns = returns.mean() - risk_free_rate / 252
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return float('inf')

        downside_std = downside_returns.std() * np.sqrt(252)
        sortino = excess_returns / downside_std * np.sqrt(252)
        return float(sortino)

    def calculate_beta(self, asset_returns: pd.Series, market_returns: pd.Series) -> float:
        """Calcular Beta (correlação com mercado)"""
        if len(asset_returns) < 2 or len(market_returns) < 2:
            return 1.0

        # Alinhar as séries
        min_length = min(len(asset_returns), len(market_returns))
        asset_aligned = asset_returns.tail(min_length)
        market_aligned = market_returns.tail(min_length)

        covariance = np.cov(asset_aligned, market_aligned)[0, 1]
        market_variance = np.var(market_aligned)

        if market_variance == 0:
            return 1.0

        beta = covariance / market_variance
        return float(beta)

    def calculate_correlation_matrix(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Calcular matriz de correlação"""
        return returns_df.corr()

    def assess_portfolio_risk(self, positions: List[Dict], market_data: Dict) -> RiskMetrics:
        """Avaliar risco do portfólio completo"""
        if not positions:
            return RiskMetrics(0, 0, 0, 0, 0, 1, 0, RiskLevel.LOW)

        # Calcular retornos do portfólio
        portfolio_values = []
        dates = []

        # Simular histórico do portfólio (em produção, usar dados reais)
        base_value = 100000  # $100k portfolio
        for i in range(30):  # 30 dias
            daily_return = np.random.normal(0, 0.01)  # 1% daily volatility
            base_value *= (1 + daily_return)
            portfolio_values.append(base_value)
            dates.append(datetime.now() - timedelta(days=30-i))

        portfolio_series = pd.Series(portfolio_values, index=dates)
        returns = portfolio_series.pct_change().dropna()

        # Calcular métricas
        volatility = self.calculate_volatility(returns)
        var_95 = self.calculate_var(returns, self.config['var_confidence'])
        max_drawdown = self.calculate_max_drawdown(portfolio_series)
        sharpe = self.calculate_sharpe_ratio(returns, self.config['risk_free_rate'])
        sortino = self.calculate_sortino_ratio(returns, self.config['risk_free_rate'])

        # Beta e correlação (simplificado)
        beta = 1.0  # Assume market correlation
        correlation = 0.7  # Assume high market correlation

        # Determinar nível de risco
        risk_score = self.calculate_portfolio_risk_score(
            volatility, abs(max_drawdown), abs(var_95)
        )
        risk_level = self.determine_risk_level(risk_score)

        return RiskMetrics(
            volatility=volatility,
            var_95=var_95,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            beta=beta,
            correlation=correlation,
            risk_level=risk_level
        )

    def calculate_position_risk(self, position: Dict, current_price: float,
                              market_volatility: float = 0.3) -> PositionRisk:
        """Calcular risco de uma posição individual"""
        symbol = position['symbol']
        size = position['size']
        entry_price = position['entry_price']
        leverage = position.get('leverage', 1.0)

        # Calcular P&L atual
        if position['side'] == 'long':
            unrealized_pnl = (current_price - entry_price) * size
        else:
            unrealized_pnl = (entry_price - current_price) * size

        # Risco potencial máximo
        max_loss_per_unit = abs(entry_price * 0.05)  # 5% max loss assumption
        max_loss_potential = max_loss_per_unit * size * leverage

        # Preços de stop loss e take profit recomendados
        stop_loss_pct = self.config['stop_loss_default']
        take_profit_pct = self.config['take_profit_default']

        if position['side'] == 'long':
            stop_loss_price = entry_price * (1 - stop_loss_pct)
            take_profit_price = entry_price * (1 + take_profit_pct)
        else:
            stop_loss_price = entry_price * (1 + stop_loss_pct)
            take_profit_price = entry_price * (1 - take_profit_pct)

        # Risk-reward ratio
        if position['side'] == 'long':
            potential_profit = (take_profit_price - entry_price) * size
            potential_loss = (entry_price - stop_loss_price) * size
        else:
            potential_profit = (entry_price - take_profit_price) * size
            potential_loss = (stop_loss_price - entry_price) * size

        risk_reward_ratio = potential_profit / max(potential_loss, 0.01)

        # Score de risco baseado em volatilidade e size
        risk_score = min(1.0, (market_volatility * leverage * size / 1000))

        return PositionRisk(
            symbol=symbol,
            position_size=size,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            risk_score=risk_score,
            max_loss_potential=max_loss_potential,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio
        )

    def calculate_portfolio_risk_score(self, volatility, max_dd, var) -> float:
        """Calcular score de risco do portfólio (0-1)"""
        # Normalizar e combinar métricas
        vol_score = min(1.0, volatility / 0.5)  # 50% volatility = max score
        dd_score = min(1.0, abs(max_dd) / 0.2)  # 20% drawdown = max score
        var_score = min(1.0, abs(var) / 0.05)   # 5% VaR = max score

        # Peso ponderado
        risk_score = (vol_score * 0.4 + dd_score * 0.4 + var_score * 0.2)
        return min(1.0, risk_score)

    def determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determinar nível de risco baseado no score"""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def check_position_limits(self, symbol: str, position_size: float,
                            portfolio_value: float) -> Tuple[bool, str]:
        """Verificar limites de posição"""
        # Limite de posição individual
        position_value = position_size * portfolio_value
        if position_value > self.max_single_position_risk * portfolio_value:
            return False, f"Posição muito grande para {symbol}: {position_value/portfolio_value:.2%} do portfólio"

        # Verificar número de posições
        if len(self.position_risks) >= self.config.get('max_positions', 10):
            return False, f"Máximo de {self.config['max_positions']} posições permitido"

        return True, "Posição dentro dos limites"

    def check_correlation_risk(self, symbol: str, positions: List[Dict]) -> Tuple[bool, str]:
        """Verificar risco de correlação entre posições"""
        if len(positions) < 2:
            return True, "Risco de correlação baixo"

        # Simular matriz de correlação (em produção, usar dados reais)
        crypto_correlations = {
            'BTC': {'ETH': 0.8, 'BNB': 0.7, 'ADA': 0.6},
            'ETH': {'BTC': 0.8, 'BNB': 0.6, 'ADA': 0.5},
            'BNB': {'BTC': 0.7, 'ETH': 0.6, 'ADA': 0.4},
            'ADA': {'BTC': 0.6, 'ETH': 0.5, 'BNB': 0.4}
        }

        # Verificar correlação com posições existentes
        for pos in positions:
            if pos['symbol'] != symbol and pos['symbol'] in crypto_correlations.get(symbol, {}):
                correlation = crypto_correlations[symbol][pos['symbol']]
                if correlation > self.config['correlation_threshold']:
                    return False, f"Alta correlação detectada: {symbol} vs {pos['symbol']} ({correlation:.2f})"

        return True, "Risco de correlação aceitável"

    def generate_risk_recommendations(self, risk_metrics: RiskMetrics,
                                    position_risks: List[PositionRisk]) -> List[str]:
        """Gerar recomendações baseadas na análise de risco"""
        recommendations = []

        # Recomendações baseadas no nível de risco geral
        if risk_metrics.risk_level == RiskLevel.CRITICAL:
            recommendations.append("🚨 RISCO CRÍTICO: Considere reduzir todas as posições")
            recommendations.append("🛑 Ativar modo de proteção: stop loss obrigatório")
        elif risk_metrics.risk_level == RiskLevel.HIGH:
            recommendations.append("⚠️ Risco alto: Reduzir exposição a ativos voláteis")
            recommendations.append("📊 Diversificar portfólio com ativos menos correlacionados")

        # Recomendações baseadas no Sharpe Ratio
        if risk_metrics.sharpe_ratio < 1.0:
            recommendations.append("📈 Sharpe Ratio baixo: Otimizar estratégias de entrada")

        # Recomendações baseadas no Max Drawdown
        if abs(risk_metrics.max_drawdown) > 0.15:
            recommendations.append("📉 Drawdown alto: Implementar stop loss mais agressivo")

        # Recomendações para posições individuais
        for pos_risk in position_risks:
            if pos_risk.risk_reward_ratio < 1.0:
                recommendations.append(f"⚖️ {pos_risk.symbol}: Risk-reward desfavorável ({pos_risk.risk_reward_ratio:.2f})")

            if pos_risk.risk_score > 0.7:
                recommendations.append(f"🔥 {pos_risk.symbol}: Posição de alto risco, considere reduzir")

        return recommendations

    def generate_emergency_stop_plan(self, risk_metrics: RiskMetrics) -> Dict:
        """Gerar plano de parada de emergência"""
        plan = {
            "trigger_conditions": [],
            "actions": [],
            "timeout": 0
        }

        # Condições de ativação
        if risk_metrics.max_drawdown < -0.1:
            plan["trigger_conditions"].append("Drawdown > 10%")

        if risk_metrics.volatility > 0.4:
            plan["trigger_conditions"].append("Volatilidade > 40%")

        if risk_metrics.var_95 < -0.05:
            plan["trigger_conditions"].append("VaR 95% > 5%")

        # Ações de emergência
        plan["actions"] = [
            "Parar todas as novas posições",
            "Fechar posições com maior risco",
            "Ativar stop loss em todas as posições",
            "Alertar administrador do sistema",
            "Salvar estado atual do portfólio"
        ]

        plan["timeout"] = 300  # 5 minutos

        return plan

def demo_risk_management():
    """Demonstração do sistema de risk management"""
    print("🛡️ DEMO - Sistema de Risk Management Avançado")
    print("=" * 50)

    # Inicializar gerenciador
    risk_manager = AdvancedRiskManager()

    # Simular posições do portfólio
    positions = [
        {'symbol': 'BTC', 'size': 2.5, 'entry_price': 101000, 'side': 'long', 'leverage': 1.0},
        {'symbol': 'ETH', 'size': 10, 'entry_price': 3500, 'side': 'long', 'leverage': 1.0},
        {'symbol': 'BNB', 'size': 50, 'entry_price': 650, 'side': 'long', 'leverage': 2.0}
    ]

    # Preços atuais (simulados)
    current_prices = {'BTC': 102000, 'ETH': 3550, 'BNB': 670}

    # Analisar risco do portfólio
    print("📊 Analisando risco do portfólio...")
    risk_metrics = risk_manager.assess_portfolio_risk(positions, current_prices)

    print(f"📈 Volatilidade: {risk_metrics.volatility:.2%}")
    print(f"💰 VaR 95%: {risk_metrics.var_95:.2%}")
    print(f"📉 Max Drawdown: {risk_metrics.max_drawdown:.2%}")
    print(f"🎯 Sharpe Ratio: {risk_metrics.sharpe_ratio:.2f}")
    print(f"⚖️ Sortino Ratio: {risk_metrics.sortino_ratio:.2f}")
    print(f"🚨 Nível de Risco: {risk_metrics.risk_level.value.upper()}")

    # Analisar risco de posições individuais
    print("\n📋 Análise de Posições:")
    position_risks = []

    for position in positions:
        pos_risk = risk_manager.calculate_position_risk(
            position, current_prices[position['symbol']]
        )
        position_risks.append(pos_risk)

        print(f"💎 {pos_risk.symbol}:")
        print(f"   P&L: ${pos_risk.unrealized_pnl:.2f}")
        print(f"   Risco Score: {pos_risk.risk_score:.2f}")
        print(f"   Risk-Reward: {pos_risk.risk_reward_ratio:.2f}")
        print(f"   Stop Loss: ${pos_risk.stop_loss_price:.2f}")

    # Gerar recomendações
    print("\n💡 Recomendações:")
    recommendations = risk_manager.generate_risk_recommendations(risk_metrics, position_risks)
    for rec in recommendations:
        print(f"   {rec}")

    # Plano de emergência
    print("\n🚨 Plano de Emergência:")
    emergency_plan = risk_manager.generate_emergency_stop_plan(risk_metrics)
    print(f"   Condições: {', '.join(emergency_plan['trigger_conditions'])}")
    print(f"   Timeout: {emergency_plan['timeout']}s")

    print("\n🎉 Demo concluído!")

if __name__ == "__main__":
    demo_risk_management()
