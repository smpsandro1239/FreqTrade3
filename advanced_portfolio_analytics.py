#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 SISTEMA DE PORTFOLIO ANALYTICS AVANÇADO - FREQTRADE3
Análise completa de performance e otimização de portfólio
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA


@dataclass
class PortfolioMetrics:
    """Métricas completas do portfólio"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    var_95: float
    cvar_95: float
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float
    treynor_ratio: float
    jensen_alpha: float
    skewness: float
    kurtosis: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    recovery_factor: float

@dataclass
class AssetAllocation:
    """Alocação de ativos"""
    symbol: str
    weight: float
    expected_return: float
    volatility: float
    beta: float
    risk_contribution: float
    marginal_risk_contribution: float

class AdvancedPortfolioAnalyzer:
    """Analisador avançado de portfólio para FreqTrade3"""

    def __init__(self, benchmark_symbol='BTC'):
        self.benchmark_symbol = benchmark_symbol
        self.benchmark_data = self.load_benchmark_data()

    def load_benchmark_data(self):
        """Carregar dados do benchmark (Bitcoin)"""
        # Simular dados do BTC como benchmark
        dates = pd.date_range('2024-01-01', '2024-11-07', freq='1D')
        np.random.seed(42)

        # Simular preço do BTC
        initial_price = 40000
        returns = np.random.normal(0.001, 0.04, len(dates))  # 0.1% daily return, 4% vol
        prices = [initial_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        return pd.Series(prices, index=dates)

    def calculate_portfolio_metrics(self, returns: pd.Series, benchmark_returns: pd.Series,
                                  risk_free_rate: float = 0.02) -> PortfolioMetrics:
        """Calcular métricas completas do portfólio"""

        # Métricas básicas
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + returns.mean()) ** 252 - 1
        volatility = returns.std() * np.sqrt(252)

        # Métricas de risco-retorno
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)

        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino_ratio = excess_returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else float('inf')

        # Drawdown
        cumulative = (1 + returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak
        max_drawdown = drawdown.min()

        # Calmar Ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else float('inf')

        # VaR e CVaR
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()

        # Beta e Alpha
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        if len(aligned_returns) > 0:
            beta = np.cov(aligned_returns, aligned_benchmark)[0, 1] / np.var(aligned_benchmark)
            alpha = aligned_returns.mean() - beta * aligned_benchmark.mean()
            information_ratio = (aligned_returns.mean() - aligned_benchmark.mean()) / (aligned_returns - aligned_benchmark).std()
            tracking_error = (aligned_returns - aligned_benchmark).std() * np.sqrt(252)
        else:
            beta = 1.0
            alpha = 0.0
            information_ratio = 0.0
            tracking_error = 0.0

        # Treynor Ratio
        treynor_ratio = excess_returns.mean() * 252 / beta if beta != 0 else 0

        # Jensen Alpha
        jensen_alpha = alpha * 252  # Annualized

        # Moments
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns)

        # Trade statistics
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0
        profit_factor = wins.sum() / abs(losses.sum()) if len(losses) > 0 and losses.sum() != 0 else float('inf')
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0

        # Recovery Factor
        recovery_factor = annualized_return / abs(max_drawdown) if max_drawdown != 0 else float('inf')

        return PortfolioMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            beta=beta,
            alpha=alpha,
            information_ratio=information_ratio,
            tracking_error=tracking_error,
            treynor_ratio=treynor_ratio,
            jensen_alpha=jensen_alpha,
            skewness=skewness,
            kurtosis=kurtosis,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            recovery_factor=recovery_factor
        )

    def optimize_portfolio_weights(self, returns_data: pd.DataFrame,
                                 target_return: Optional[float] = None,
                                 risk_aversion: float = 1.0) -> Dict:
        """Otimizar pesos do portfólio usando Markowitz"""
        from scipy.optimize import minimize

        n_assets = len(returns_data.columns)

        # Calcular média e covariância
        mean_returns = returns_data.mean()
        cov_matrix = returns_data.cov()

        # Função objetivo: maximizar Sharpe Ratio
        def objective(weights):
            portfolio_return = np.sum(weights * mean_returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
            return -sharpe  # Minimizar negativo = maximizar positivo

        # Restrições
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Soma dos pesos = 1
        ]

        if target_return:
            constraints.append({
                'type': 'eq',
                'fun': lambda x: np.sum(x * mean_returns) - target_return
            })

        # Bounds: pesos entre 0 e 1
        bounds = tuple((0, 1) for _ in range(n_assets))

        # Chute inicial: pesos iguais
        x0 = np.array([1/n_assets] * n_assets)

        # Otimizar
        result = minimize(
            objective, x0, method='SLSQP', bounds=bounds, constraints=constraints
        )

        if result.success:
            optimized_weights = result.x
            portfolio_return = np.sum(optimized_weights * mean_returns)
            portfolio_vol = np.sqrt(np.dot(optimized_weights.T, np.dot(cov_matrix, optimized_weights)))
            sharpe_ratio = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0

            return {
                'success': True,
                'weights': dict(zip(returns_data.columns, optimized_weights)),
                'expected_return': portfolio_return,
                'volatility': portfolio_vol,
                'sharpe_ratio': sharpe_ratio,
                'optimized_at': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': result.message
            }

    def perform_black_litterman(self, market_data: pd.DataFrame,
                              views: Dict[str, float]) -> Dict:
        """Implementar modelo Black-Litterman"""
        n_assets = len(market_data.columns)

        # Matriz de covariância
        cov_matrix = market_data.cov()

        # Cálculo do tau (parâmetro de incerteza)
        tau = 0.05

        # Matriz Sigma (covariância)
        sigma = cov_matrix * (1 + tau)

        # Vector de retornos de mercado (equal weight)
        market_weights = np.array([1/n_assets] * n_assets)

        # Retornos implícitos de mercado
        risk_aversion = 3.0  # Typical value
        pi = risk_aversion * np.dot(sigma, market_weights)

        # Matriz de views (Q)
        P = np.zeros((len(views), n_assets))
        q = np.zeros(len(views))

        for i, (symbol, view_return) in enumerate(views.items()):
            if symbol in market_data.columns:
                asset_idx = list(market_data.columns).index(symbol)
                P[i, asset_idx] = 1
                q[i] = view_return

        # Matriz de incerteza das views
        omega = np.diag([0.025] * len(views))  # 2.5% uncertainty per view

        # Cálculo do modelo Black-Litterman
        # Σ_bl = (τΣ)^(-1) + P'Ω^(-1)P
        left_side = np.linalg.inv(tau * sigma)
        right_side = np.dot(P.T, np.dot(np.linalg.inv(omega), P))
        middle = np.linalg.inv(left_side + right_side)

        # Retornos ajustados
        right_term = np.dot(P.T, np.dot(np.linalg.inv(omega), q))
        pi_bl = np.dot(middle, np.dot(left_side, pi) + right_term)

        # Pesos Black-Litterman
        risk_aversion_bl = 3.0
        sigma_bl = sigma
        weights_bl = np.dot(np.linalg.inv(risk_aversion_bl * sigma_bl), pi_bl)

        return {
            'success': True,
            'weights': dict(zip(market_data.columns, weights_bl)),
            'expected_returns': dict(zip(market_data.columns, pi_bl)),
            'method': 'Black-Litterman',
            'optimized_at': datetime.now().isoformat()
        }

    def perform_factors_analysis(self, returns_data: pd.DataFrame) -> Dict:
        """Análise de fatores (Fama-French)"""
        factors = {
            'market': returns_data.mean(axis=1),  # Market factor (proxy)
            'volatility': returns_data.std(axis=1),  # Volatility factor
            'momentum': returns_data.rolling(5).mean().mean(axis=1),  # Momentum factor
            'reversal': returns_data.rolling(20).mean().mean(axis=1)   # Reversal factor
        }

        factor_returns = pd.DataFrame(factors)
        factor_loadings = {}

        # Regressão de cada asset contra os fatores
        for symbol in returns_data.columns:
            asset_returns = returns_data[symbol]
            aligned_data = asset_returns.align(factor_returns, join='inner')

            if len(aligned_data[0]) > 30:  # Enough data
                from sklearn.linear_model import LinearRegression
                X = aligned_data[1].dropna()
                y = aligned_data[0].reindex(X.index).dropna()

                if len(X) > 10 and len(y) > 10:
                    X_aligned = X.reindex(y.index)
                    model = LinearRegression().fit(X_aligned, y)

                    factor_loadings[symbol] = {
                        'market_beta': model.coef_[0] if len(model.coef_) > 0 else 0,
                        'volatility_beta': model.coef_[1] if len(model.coef_) > 1 else 0,
                        'momentum_beta': model.coef_[2] if len(model.coef_) > 2 else 0,
                        'reversal_beta': model.coef_[3] if len(model.coef_) > 3 else 0,
                        'alpha': model.intercept_,
                        'r_squared': model.score(X_aligned, y)
                    }

        # Análise de fatores globais
        global_factor_performance = {}
        for factor_name, factor_data in factors.items():
            if len(factor_data.dropna()) > 0:
                factor_mean = factor_data.mean()
                factor_vol = factor_data.std()
                global_factor_performance[factor_name] = {
                    'mean_return': factor_mean,
                    'volatility': factor_vol,
                    'sharpe_ratio': factor_mean / factor_vol if factor_vol > 0 else 0
                }

        return {
            'success': True,
            'factor_loadings': factor_loadings,
            'global_factor_performance': global_factor_performance,
            'analysis_date': datetime.now().isoformat()
        }

    def generate_portfolio_report(self, returns_data: pd.DataFrame,
                                current_allocations: Dict[str, float]) -> Dict:
        """Gerar relatório completo do portfólio"""

        # Calcular métricas do portfólio
        portfolio_returns = (returns_data * list(current_allocations.values())).sum(axis=1)
        benchmark_returns = self.benchmark_data.pct_change().dropna()

        aligned_returns, aligned_benchmark = portfolio_returns.align(benchmark_returns, join='inner')
        metrics = self.calculate_portfolio_metrics(aligned_returns, aligned_benchmark)

        # Alocação atual
        allocations = []
        for symbol, weight in current_allocations.items():
            if symbol in returns_data.columns:
                asset_returns = returns_data[symbol]
                asset_vol = asset_returns.std() * np.sqrt(252)
                asset_return = asset_returns.mean() * 252

                allocations.append({
                    'symbol': symbol,
                    'weight': weight,
                    'expected_return': asset_return,
                    'volatility': asset_vol
                })

        # Otimização de portfólio
        optimization_result = self.optimize_portfolio_weights(returns_data)

        # Análise de fatores
        factors_result = self.perform_factors_analysis(returns_data)

        # Recomendações
        recommendations = []

        if metrics.sharpe_ratio < 1.0:
            recommendations.append("📈 Sharpe Ratio baixo: Considere reequilibrar portfólio")

        if metrics.max_drawdown < -0.15:
            recommendations.append("⚠️ Drawdown alto: Reduza exposição a ativos voláteis")

        if metrics.beta > 1.5:
            recommendations.append("📊 Beta alto: Adicione ativos com menor correlação ao mercado")

        # Relatório final
        report = {
            'report_date': datetime.now().isoformat(),
            'portfolio_metrics': {
                'total_return': f"{metrics.total_return:.2%}",
                'annualized_return': f"{metrics.annualized_return:.2%}",
                'volatility': f"{metrics.volatility:.2%}",
                'sharpe_ratio': f"{metrics.sharpe_ratio:.2f}",
                'max_drawdown': f"{metrics.max_drawdown:.2%}",
                'win_rate': f"{metrics.win_rate:.2%}",
                'profit_factor': f"{metrics.profit_factor:.2f}"
            },
            'current_allocation': allocations,
            'optimization_result': optimization_result,
            'factors_analysis': factors_result,
            'recommendations': recommendations,
            'summary_score': self.calculate_portfolio_score(metrics)
        }

        return report

    def calculate_portfolio_score(self, metrics: PortfolioMetrics) -> float:
        """Calcular score geral do portfólio (0-100)"""
        score = 0

        # Sharpe Ratio (25 points max)
        if metrics.sharpe_ratio > 2.0:
            score += 25
        elif metrics.sharpe_ratio > 1.0:
            score += 20
        elif metrics.sharpe_ratio > 0.5:
            score += 15
        else:
            score += 5

        # Max Drawdown (20 points max)
        if abs(metrics.max_drawdown) < 0.05:
            score += 20
        elif abs(metrics.max_drawdown) < 0.10:
            score += 15
        elif abs(metrics.max_drawdown) < 0.15:
            score += 10
        else:
            score += 5

        # Win Rate (15 points max)
        if metrics.win_rate > 0.7:
            score += 15
        elif metrics.win_rate > 0.6:
            score += 12
        elif metrics.win_rate > 0.5:
            score += 8
        else:
            score += 3

        # Profit Factor (15 points max)
        if metrics.profit_factor > 2.0:
            score += 15
        elif metrics.profit_factor > 1.5:
            score += 12
        elif metrics.profit_factor > 1.2:
            score += 8
        else:
            score += 3

        # Alpha/Outperformance (25 points max)
        if abs(metrics.alpha) > 0.05:
            score += 25
        elif abs(metrics.alpha) > 0.02:
            score += 20
        elif abs(metrics.alpha) > 0.01:
            score += 15
        else:
            score += 10

        return min(100, score)

    def create_visualization_report(self, returns_data: pd.DataFrame,
                                  current_allocations: Dict[str, float],
                                  save_path: str = 'reports/portfolio_analysis.png'):
        """Criar visualizações do relatório"""
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Configurar estilo
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('FreqTrade3 - Portfolio Analytics Report', fontsize=16, fontweight='bold')

        # 1. Performance cumulativa
        cumulative_returns = (1 + returns_data).cumprod()
        portfolio_cumulative = (cumulative_returns * list(current_allocations.values())).sum(axis=1)
        benchmark_cumulative = (1 + self.benchmark_data.pct_change()).cumprod()

        axes[0, 0].plot(portfolio_cumulative.index, portfolio_cumulative.values, label='Portfolio', linewidth=2)
        axes[0, 0].plot(benchmark_cumulative.index, benchmark_cumulative.values, label='BTC Benchmark', linewidth=2)
        axes[0, 0].set_title('Cumulative Performance')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Alocação atual
        symbols = list(current_allocations.keys())
        weights = list(current_allocations.values())
        colors = plt.cm.Set3(np.linspace(0, 1, len(symbols)))

        axes[0, 1].pie(weights, labels=symbols, autopct='%1.1f%%', colors=colors)
        axes[0, 1].set_title('Current Allocation')

        # 3. Rolling Sharpe Ratio
        portfolio_returns = (returns_data * weights).sum(axis=1)
        rolling_sharpe = portfolio_returns.rolling(30).mean() / portfolio_returns.rolling(30).std() * np.sqrt(252)
        axes[0, 2].plot(rolling_sharpe.index, rolling_sharpe.values, color='purple', linewidth=2)
        axes[0, 2].set_title('Rolling Sharpe Ratio (30-day)')
        axes[0, 2].grid(True, alpha=0.3)

        # 4. Drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (cumulative - peak) / peak

        axes[1, 0].fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
        axes[1, 0].plot(drawdown.index, drawdown.values, color='red', linewidth=1)
        axes[1, 0].set_title('Drawdown')
        axes[1, 0].grid(True, alpha=0.3)

        # 5. Correlation Matrix
        corr_matrix = returns_data.corr()
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                   ax=axes[1, 1], square=True)
        axes[1, 1].set_title('Asset Correlation Matrix')

        # 6. Risk-Return Scatter
        annual_returns = returns_data.mean() * 252
        annual_vols = returns_data.std() * np.sqrt(252)

        axes[1, 2].scatter(annual_vols, annual_returns, s=100, alpha=0.7)
        for i, symbol in enumerate(returns_data.columns):
            axes[1, 2].annotate(symbol, (annual_vols.iloc[i], annual_returns.iloc[i]))
        axes[1, 2].set_xlabel('Annual Volatility')
        axes[1, 2].set_ylabel('Annual Return')
        axes[1, 2].set_title('Risk-Return Profile')
        axes[1, 2].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

def demo_portfolio_analytics():
    """Demonstração do sistema de analytics"""
    print("📊 DEMO - Sistema de Portfolio Analytics Avançado")
    print("=" * 50)

    # Inicializar analisador
    analyzer = AdvancedPortfolioAnalyzer()

    # Simular dados de retornos
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', '2024-11-07', freq='1D')
    assets = ['BTC', 'ETH', 'BNB', 'ADA', 'XRP']

    # Criar matriz de retornos
    returns_data = {}
    for asset in assets:
        returns = np.random.normal(0.001, 0.04, len(dates))  # Realistic crypto returns
        returns_data[asset] = returns

    returns_df = pd.DataFrame(returns_data, index=dates)

    # Alocação atual
    current_allocations = {'BTC': 0.4, 'ETH': 0.25, 'BNB': 0.15, 'ADA': 0.1, 'XRP': 0.1}

    print("📈 Analisando portfólio...")

    # Gerar relatório completo
    report = analyzer.generate_portfolio_report(returns_df, current_allocations)

    print("\n📊 MÉTRICAS PRINCIPAIS:")
    for metric, value in report['portfolio_metrics'].items():
        print(f"  {metric.replace('_', ' ').title()}: {value}")

    print(f"\n🎯 Portfolio Score: {report['summary_score']}/100")

    print("\n💡 RECOMENDAÇÕES:")
    for rec in report['recommendations']:
        print(f"  {rec}")

    # Otimização
    print("\n🔧 OTIMIZAÇÃO:")
    optimization = report['optimization_result']
    if optimization['success']:
        print("  Alocação Otimizada:")
        for symbol, weight in optimization['weights'].items():
            print(f"    {symbol}: {weight:.1%}")
        print(f"  Expected Sharpe Ratio: {optimization['sharpe_ratio']:.2f}")

    # Análise de fatores
    print("\n📊 FATORES:")
    factors = report['factors_analysis']
    if factors['success']:
        print("  Performance dos Fatores:")
        for factor, perf in factors['global_factor_performance'].items():
            print(f"    {factor.title()}: Sharpe {perf['sharpe_ratio']:.2f}")

    # Criar visualização
    print("\n📈 Gerando visualizações...")
    viz_path = analyzer.create_visualization_report(returns_df, current_allocations)
    print(f"  Gráfico salvo em: {viz_path}")

    print("\n🎉 Demo concluído!")

if __name__ == "__main__":
    demo_portfolio_analytics()
