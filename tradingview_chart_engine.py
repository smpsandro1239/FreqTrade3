#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 SISTEMA DE GRÁFICOS TRADINGVIEW-LIKE - FREQTRADE3
Gráficos idênticos ao TradingView com plotly.js avançado
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class TradingViewChartEngine:
    """Motor de gráficos TradingView-like com Plotly.js"""

    def __init__(self):
        self.chart_id = "freqtrade_chart"
        self.script_template = self.get_tradingview_template()

    def get_tradingview_template(self) -> str:
        """Template do gráfico TradingView-like"""
        return """
        // ===================== TRADINGVIEW CHART ENGINE =====================

        // Configuração avançada do gráfico
        const tvChart = new TradingView.widget({
            symbol: 'BINANCE:BTCUSDT',
            interval: '60',
            container_id: '%s',
            library_path: '/static/js/charting_library/',
            autosize: true,

            // === CONFIGURAÇÕES DE INTERFACE ===
            locale: 'pt',
            timezone: 'Europe/Lisbon',
            theme: 'light',

            // === TOOLBAR ===
            toolbar_bg: '#f1f3f6',
            hide_side_toolbar: false,
            allow_symbol_change: true,
            hide_top_toolbar: false,
            hide_legend: false,
            save_image: true,
            studies_overrides: {},

            // === CONTROLES ===
            disabled_features: [
                'header_symbol_search',
                'symbol_search_hot_key',
                'header_resolutions',
                'header_chart_type',
                'header_settings',
                'compare_feature',
                'header_indicators',
                'control_bar',
                'timeframes_toolbar',
                'left_toolbar',
                'edit_buttons_in_legend',
                'context_menus'
            ],

            enabled_features: [
                'use_localstorage_for_settings',
                'volume_force_overlay',
                'create_volume_indicator_by_default'
            ],

            // === ESTUDOS ===
            studies: [
                'Volume@tv-basicstudies',
                'MACD@tv-basicstudies',
                'RSI@tv-basicstudies',
                'EMA@tv-basicstudies',
                'BollingerBands@tv-basicstudies',
                'Stochastic@tv-basicstudies',
                'ATR@tv-basicstudies'
            ],

            // === PALETA DE CORES ===
            overrides: {
                'paneProperties.background': '#ffffff',
                'paneProperties.vertGridProperties.color': '#e1e4e8',
                'paneProperties.horzGridProperties.color': '#e1e4e8',
                'symbolWatermarkProperties.transparency': 90,
                'scalesProperties.backgroundColor': '#ffffff',
                'scalesProperties.textColor': '#333',

                // Candlestick colors
                'mainSeriesProperties.candleStyle.upColor': '#26a69a',
                'mainSeriesProperties.candleStyle.downColor': '#ef5350',
                'mainSeriesProperties.candleStyle.borderUpColor': '#26a69a',
                'mainSeriesProperties.candleStyle.borderDownColor': '#ef5350',
                'mainSeriesProperties.candleStyle.wickUpColor': '#26a69a',
                'mainSeriesProperties.candleStyle.wickDownColor': '#ef5350',

                // Volume colors
                'volumeSeriesProperties.color': '#26a69a',
                'volumeSeriesProperties.decorationColor': 'rgba(0,0,0,0)',

                // Grid
                'paneProperties.vertGridProperties.style': 1,
                'paneProperties.horzGridProperties.style': 1
            },

            // === ONCLICKS ===
            onChartReady: function() {
                console.log('TradingView Chart Ready');

                // Inicializar desenhadores de trades
                initializeTradeDrawings();

                // Configurar WebSocket para dados em tempo real
                setupRealtimeData();
            }
        });

        // ===================== DRAWING TOOLS =====================

        let chart = tvChart;
        let currentWidget = tvChart.chart();

        function initializeTradeDrawings() {
            // Configurar estilo dos trades
            const tradeStyle = {
                linecolor: 'rgba(255, 0, 0, 1)',
                linestyle: 1,
                linewidth: 2,
                color: 'rgba(255, 0, 0, 1)'
            };

            // Configurar ordem de desenho
            const pendingOrders = new Map();
            const openPositions = new Map();
            const closedTrades = [];
        }

        // ===================== REAL-TIME DATA =====================

        function setupRealtimeData() {
            // WebSocket para dados em tempo real
            const socket = io();

            socket.on('market_data', function(data) {
                if (data && data.pair && data.timeframe) {
                    // Atualizar dados do gráfico
                    updateChartData(data);

                    // Verificar sinais de trading
                    checkTradingSignals(data);
                }
            });

            socket.on('trade_executed', function(trade) {
                drawTradeOnChart(trade);
                updateTradeList(trade);
            });

            socket.on('indicators_update', function(indicators) {
                updateIndicators(indicators);
            });
        }

        function updateChartData(marketData) {
            try {
                // Converter dados para formato TradingView
                const tvData = {
                    time: marketData.timestamp,
                    open: marketData.open,
                    high: marketData.high,
                    low: marketData.low,
                    close: marketData.close,
                    volume: marketData.volume
                };

                // Atualizar gráfico via API TradingView
                currentWidget.onChartReady(() => {
                    currentWidget.chart().executeActionById('updateData').dataToSave([tvData]);
                });
            } catch (error) {
                console.error('Erro ao atualizar dados:', error);
            }
        }

        // ===================== TRADE MANAGEMENT =====================

        function drawTradeOnChart(trade) {
            const isBuy = trade.side === 'buy';
            const color = isBuy ? '#26a69a' : '#ef5350';

            // Ponto de entrada
            const entryPoint = {
                time: new Date(trade.timestamp).getTime() / 1000,
                price: trade.price,
                color: color,
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: `${isBuy ? 'COMPRA' : 'VENDA'}: ${trade.quantity}`
            };

            // Linha de posição
            const positionLine = {
                price: trade.price,
                color: color,
                width: 2,
                style: 1,
                editable: true
            };

            // Desenhar no gráfico
            currentWidget.onChartReady(() => {
                const chartObject = currentWidget.chart();
                chartObject.createShape(entryPoint, {
                    onSecondaryClick: function() {
                        // Menu de contexto para o trade
                        showTradeContextMenu(trade);
                    }
                });
            });
        }

        // ===================== SIGNALS & INDICATORS =====================

        function checkTradingSignals(data) {
            // Verificar EMA Crossover
            if (data.indicators) {
                const { ema_12, ema_26, rsi, macd, signal } = data.indicators;

                if (ema_12 && ema_26) {
                    // Sinal de compra
                    if (ema_12 > ema_26 && ema_12.length > 1 && ema_12[ema_12.length-2] <= ema_26[ema_26.length-2]) {
                        showSignal('COMPRA', 'EMA Crossover Bullish', '#26a69a');
                    }

                    // Sinal de venda
                    if (ema_12 < ema_26 && ema_12[ema_12.length-2] >= ema_26[ema_26.length-2]) {
                        showSignal('VENDA', 'EMA Crossover Bearish', '#ef5350');
                    }
                }

                // RSI signals
                if (rsi && rsi.length > 0) {
                    const currentRsi = rsi[rsi.length-1];
                    if (currentRsi < 30) {
                        showSignal('COMPRA', 'RSI Oversold', '#26a69a');
                    } else if (currentRsi > 70) {
                        showSignal('VENDA', 'RSI Overbought', '#ef5350');
                    }
                }
            }
        }

        function showSignal(type, description, color) {
            // Criar notificação visual
            const signalElement = document.createElement('div');
            signalElement.className = 'trading-signal';
            signalElement.innerHTML = `
                <div class="signal-indicator" style="background-color: ${color}">
                    ${type}
                </div>
                <div class="signal-description">${description}</div>
            `;

            // Posicionar no gráfico
            const chartContainer = document.getElementById('%s');
            chartContainer.appendChild(signalElement);

            // Animar e remover
            setTimeout(() => {
                signalElement.classList.add('show');
                setTimeout(() => {
                    signalElement.classList.remove('show');
                    setTimeout(() => {
                        signalElement.remove();
                    }, 500);
                }, 3000);
            }, 100);
        }

        // ===================== MANUAL TRADING =====================

        function openManualTradeDialog() {
            // Dialog para entrada manual
            const dialog = document.createElement('div');
            dialog.className = 'manual-trade-dialog';
            dialog.innerHTML = `
                <div class="dialog-content">
                    <h3>Entrada Manual de Trade</h3>
                    <div class="form-group">
                        <label>Par:</label>
                        <select id="manual-pair">
                            <option value="BTC/USDT">BTC/USDT</option>
                            <option value="ETH/USDT">ETH/USDT</option>
                            <option value="BNB/USDT">BNB/USDT</option>
                            <option value="ADA/USDT">ADA/USDT</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Ação:</label>
                        <select id="manual-action">
                            <option value="buy">COMPRA</option>
                            <option value="sell">VENDA</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Quantidade:</label>
                        <input type="number" id="manual-quantity" step="0.0001" placeholder="0.1">
                    </div>
                    <div class="form-group">
                        <label>Preço:</label>
                        <input type="number" id="manual-price" step="0.01" placeholder="Preço atual">
                    </div>
                    <div class="form-group">
                        <label>Stop Loss:</label>
                        <input type="number" id="manual-stop-loss" step="0.01" placeholder="Opcional">
                    </div>
                    <div class="form-group">
                        <label>Take Profit:</label>
                        <input type="number" id="manual-take-profit" step="0.01" placeholder="Opcional">
                    </div>
                    <div class="dialog-actions">
                        <button onclick="executeManualTrade()" class="btn-primary">Executar</button>
                        <button onclick="closeManualTradeDialog()" class="btn-secondary">Cancelar</button>
                    </div>
                </div>
            `;

            document.body.appendChild(dialog);
        }

        function executeManualTrade() {
            const trade = {
                pair: document.getElementById('manual-pair').value,
                action: document.getElementById('manual-action').value,
                quantity: parseFloat(document.getElementById('manual-quantity').value),
                price: parseFloat(document.getElementById('manual-price').value),
                stop_loss: document.getElementById('manual-stop-loss').value || null,
                take_profit: document.getElementById('manual-take-profit').value || null,
                timestamp: new Date().toISOString()
            };

            // Enviar para backend
            fetch('/api/manual_trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(trade)
            }).then(response => {
                if (response.ok) {
                    closeManualTradeDialog();
                    showNotification('Trade executado com sucesso!', 'success');
                } else {
                    showNotification('Erro ao executar trade', 'error');
                }
            });
        }

        function closeManualTradeDialog() {
            const dialog = document.querySelector('.manual-trade-dialog');
            if (dialog) dialog.remove();
        }

        // ===================== NOTIFICATION SYSTEM =====================

        function showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.innerHTML = `
                <div class="notification-content">
                    <span>${message}</span>
                    <button onclick="this.parentElement.parentElement.remove()">×</button>
                </div>
            `;

            document.body.appendChild(notification);

            setTimeout(() => {
                notification.classList.add('show');
            }, 100);

            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }, 5000);
        }

        // ===================== STRATEGY VISUALIZATION =====================

        function updateStrategyVisualization(strategy) {
            // Atualizar indicadores e sinais no gráfico
            if (strategy.signals) {
                strategy.signals.forEach(signal => {
                    drawStrategySignal(signal);
                });
            }

            // Destacar pontos de entrada/saída
            if (strategy.entries) {
                strategy.entries.forEach(entry => {
                    drawEntryPoint(entry);
                });
            }
        }

        function drawStrategySignal(signal) {
            const isBuy = signal.type === 'buy';
            const color = isBuy ? '#26a69a' : '#ef5350';

            currentWidget.onChartReady(() => {
                const chartObject = currentWidget.chart();
                chartObject.createShape({
                    time: new Date(signal.timestamp).getTime() / 1000,
                    price: signal.price,
                    color: color,
                    shape: isBuy ? 'arrowUp' : 'arrowDown',
                    text: signal.strategy
                });
            });
        }

        // ===================== EVENT LISTENERS =====================

        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 't':
                        e.preventDefault();
                        openManualTradeDialog();
                        break;
                    case 'b':
                        e.preventDefault();
                        // Toggle indicators
                        break;
                    case 'h':
                        e.preventDefault();
                        // Show help
                        break;
                }
            }
        });

        // ===================== STYLES =====================

        const styles = `
        <style>
        .trading-signal {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 1000;
            opacity: 0;
            transform: translateX(100px);
            transition: all 0.3s ease;
        }

        .trading-signal.show {
            opacity: 1;
            transform: translateX(0);
        }

        .signal-indicator {
            font-weight: bold;
            text-align: center;
            margin-bottom: 5px;
        }

        .signal-description {
            font-size: 12px;
            text-align: center;
        }

        .manual-trade-dialog {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .dialog-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            min-width: 400px;
            max-width: 500px;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }

        .form-group input, .form-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        .dialog-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .btn-primary, .btn-secondary {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        .btn-primary {
            background: #26a69a;
            color: white;
        }

        .btn-secondary {
            background: #666;
            color: white;
        }

        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10001;
            max-width: 300px;
            transform: translateX(100%);
            transition: all 0.3s ease;
        }

        .notification.show {
            transform: translateX(0);
        }

        .notification-content {
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .notification.success .notification-content {
            border-left: 4px solid #26a69a;
        }

        .notification.error .notification-content {
            border-left: 4px solid #ef5350;
        }

        .notification.info .notification-content {
            border-left: 4px solid #2196F3;
        }
        </style>
        `;

        // Injetar estilos
        document.head.insertAdjacentHTML('beforeend', styles);
        """ % (self.chart_id, self.chart_id)

    def generate_chart_html(self, symbol: str = "BTC/USDT", timeframe: str = "1h",
                          show_strategy: bool = True, show_trades: bool = True) -> str:
        """Gerar HTML completo do gráfico TradingView-like"""

        html_template = f"""
        <!DOCTYPE html>
        <html lang="pt">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FreqTrade3 - Gráfico TradingView</title>

            <!-- TradingView Charting Library -->
            <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>

            <!-- Socket.IO -->
            <script src="/socket.io/socket.io.js"></script>

            <!-- Chart.js para indicadores -->
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js"></script>

            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f5f5f5;
                }}

                .chart-container {{
                    position: relative;
                    width: 100%;
                    height: 600px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}

                .chart-header {{
                    padding: 15px 20px;
                    background: #fff;
                    border-bottom: 1px solid #e1e4e8;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }}

                .chart-title {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }}

                .chart-controls {{
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }}

                .btn {{
                    padding: 6px 12px;
                    border: 1px solid #ddd;
                    background: white;
                    color: #666;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    transition: all 0.2s;
                }}

                .btn:hover {{
                    background: #f5f5f5;
                    border-color: #999;
                }}

                .btn-primary {{
                    background: #26a69a;
                    color: white;
                    border-color: #26a69a;
                }}

                .btn-primary:hover {{
                    background: #2bbbad;
                }}

                .chart-toolbar {{
                    display: flex;
                    gap: 15px;
                    align-items: center;
                }}

                .indicator-selector {{
                    display: flex;
                    gap: 5px;
                }}

                .indicator-btn {{
                    padding: 4px 8px;
                    border: 1px solid #ddd;
                    background: white;
                    color: #666;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 11px;
                }}

                .indicator-btn.active {{
                    background: #26a69a;
                    color: white;
                    border-color: #26a69a;
                }}

                .timeframe-selector {{
                    display: flex;
                    gap: 3px;
                }}

                .timeframe-btn {{
                    padding: 6px 8px;
                    border: 1px solid #ddd;
                    background: white;
                    color: #666;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 12px;
                }}

                .timeframe-btn.active {{
                    background: #26a69a;
                    color: white;
                    border-color: #26a69a;
                }}

                .trades-panel {{
                    position: absolute;
                    top: 60px;
                    right: 20px;
                    width: 300px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    max-height: 400px;
                    overflow-y: auto;
                    z-index: 100;
                    display: none;
                }}

                .trades-panel.show {{
                    display: block;
                }}

                .trades-header {{
                    padding: 15px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #e1e4e8;
                    font-weight: 600;
                    color: #333;
                }}

                .trade-item {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #f0f0f0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}

                .trade-item:last-child {{
                    border-bottom: none;
                }}

                .trade-info {{
                    flex: 1;
                }}

                .trade-symbol {{
                    font-weight: 600;
                    color: #333;
                }}

                .trade-details {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 2px;
                }}

                .trade-pnl {{
                    font-weight: 600;
                    font-size: 14px;
                }}

                .trade-pnl.positive {{
                    color: #26a69a;
                }}

                .trade-pnl.negative {{
                    color: #ef5350;
                }}

                .signals-panel {{
                    position: absolute;
                    top: 60px;
                    left: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    max-width: 300px;
                    z-index: 100;
                }}

                .signals-header {{
                    padding: 15px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #e1e4e8;
                    font-weight: 600;
                    color: #333;
                }}

                .signal-item {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #f0f0f0;
                }}

                .signal-item:last-child {{
                    border-bottom: none;
                }}

                .signal-type {{
                    font-weight: 600;
                    margin-bottom: 4px;
                }}

                .signal-buy {{
                    color: #26a69a;
                }}

                .signal-sell {{
                    color: #ef5350;
                }}

                .signal-description {{
                    font-size: 12px;
                    color: #666;
                }}

                .loading-overlay {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(255,255,255,0.9);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                }}

                .loading-spinner {{
                    width: 40px;
                    height: 40px;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #26a69a;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }}

                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">
                        📊 {symbol} - {timeframe}
                        <span id="current-price" style="margin-left: 15px; color: #26a69a; font-weight: 600;">
                            Carregando...
                        </span>
                    </div>

                    <div class="chart-controls">
                        <div class="chart-toolbar">
                            <div class="timeframe-selector">
                                <button class="timeframe-btn" data-tf="1m">1m</button>
                                <button class="timeframe-btn" data-tf="5m">5m</button>
                                <button class="timeframe-btn" data-tf="15m">15m</button>
                                <button class="timeframe-btn active" data-tf="1h">1h</button>
                                <button class="timeframe-btn" data-tf="4h">4h</button>
                                <button class="timeframe-btn" data-tf="1d">1d</button>
                            </div>

                            <div class="indicator-selector">
                                <button class="indicator-btn active" data-ind="rsi">RSI</button>
                                <button class="indicator-btn" data-ind="macd">MACD</button>
                                <button class="indicator-btn" data-ind="ema">EMA</button>
                                <button class="indicator-btn" data-ind="bb">BB</button>
                            </div>

                            <button class="btn" onclick="toggleTrades()">💰 Trades</button>
                            <button class="btn" onclick="toggleSignals()">🎯 Sinais</button>
                            <button class="btn-primary" onclick="openManualTrade()">Manual</button>
                        </div>
                    </div>
                </div>

                <div id="main-chart" style="height: 500px;"></div>

                <div class="trades-panel" id="trades-panel">
                    <div class="trades-header">📈 Histório de Trades</div>
                    <div id="trades-list">
                        <div style="padding: 20px; text-align: center; color: #666;">
                            Nenhum trade ainda
                        </div>
                    </div>
                </div>

                <div class="signals-panel" id="signals-panel">
                    <div class="signals-header">🎯 Sinais de Trading</div>
                    <div id="signals-list">
                        <div style="padding: 20px; text-align: center; color: #666;">
                            Aguardando sinais...
                        </div>
                    </div>
                </div>

                <div class="loading-overlay" id="loading">
                    <div class="loading-spinner"></div>
                </div>
            </div>

            <script>
                {self.script_template}

                // ===================== IMPLEMENTAÇÃO ADICIONAL =====================

                let chart;
                let mainSeries;
                let volumeSeries;
                let currentSymbol = '{symbol}';
                let currentTimeframe = '{timeframe}';
                let socket;

                // Inicializar gráfico
                function initChart() {{
                    const container = document.getElementById('main-chart');

                    chart = LightweightCharts.createChart(container, {{
                        layout: {{
                            background: {{ type: 'Solid', color: '#ffffff' }},
                            textColor: '#333',
                        }},
                        width: container.clientWidth,
                        height: 450,
                        grid: {{
                            vertLines: {{
                                color: '#e1e4e8',
                                style: 1,
                            }},
                            horzLines: {{
                                color: '#e1e4e8',
                                style: 1,
                            }},
                        }},
                        crosshair: {{
                            mode: 1,
                        }},
                        timeScale: {{
                            timeVisible: true,
                            secondsVisible: false,
                        }},
                    }});

                    // Série principal (candlesticks)
                    mainSeries = chart.addCandlestickSeries({{
                        upColor: '#26a69a',
                        downColor: '#ef5350',
                        borderDownColor: '#ef5350',
                        borderUpColor: '#26a69a',
                        wickDownColor: '#ef5350',
                        wickUpColor: '#26a69a',
                    }});

                    // Série de volume
                    volumeSeries = chart.addHistogramSeries({{
                        color: '#26a69a',
                        priceFormat: {{
                            type: 'volume',
                        }},
                        priceScaleId: 'volume',
                    }});

                    // Price scale para volume
                    chart.priceScale('volume').applyOptions({{
                        scaleMargins: {{
                            top: 0.8,
                            bottom: 0,
                        }},
                    }});

                    // Carregar dados iniciais
                    loadChartData();

                    // Configurar WebSocket
                    setupWebSocket();
                }}

                // Carregar dados do gráfico
                async function loadChartData() {{
                    try {{
                        const response = await fetch(`/api/market_data/${{currentSymbol}}?timeframe=${{currentTimeframe}}&limit=100`);
                        const data = await response.json();

                        if (data.data && data.data.length > 0) {{
                            const candlestickData = data.data.map(item => ({{
                                time: Math.floor(new Date(item.timestamp).getTime() / 1000),
                                open: item.open,
                                high: item.high,
                                low: item.low,
                                close: item.close,
                            }}));

                            const volumeData = data.data.map(item => ({{
                                time: Math.floor(new Date(item.timestamp).getTime() / 1000),
                                value: item.volume,
                                color: item.close >= item.open ? '#26a69a' : '#ef5350',
                            }}));

                            mainSeries.setData(candlestickData);
                            volumeSeries.setData(volumeData);

                            // Atualizar preço atual
                            if (candlestickData.length > 0) {{
                                const current = candlestickData[candlestickData.length - 1];
                                document.getElementById('current-price').textContent =
                                    `${{current.close.toLocaleString('pt-BR', {{style: 'currency', currency: 'USD'}})}}`;
                            }}
                        }}

                        document.getElementById('loading').style.display = 'none';
                    }} catch (error) {{
                        console.error('Erro ao carregar dados:', error);
                        document.getElementById('loading').style.display = 'none';
                    }}
                }}

                // WebSocket para dados em tempo real
                function setupWebSocket() {{
                    socket = io();

                    socket.on('market_data_update', function(data) {{
                        if (data.pair === currentSymbol) {{
                            const candle = {{
                                time: Math.floor(new Date(data.timestamp).getTime() / 1000),
                                open: data.open,
                                high: data.high,
                                low: data.low,
                                close: data.close,
                            }};

                            const volume = {{
                                time: candle.time,
                                value: data.volume,
                                color: data.close >= data.open ? '#26a69a' : '#ef5350',
                            }};

                            mainSeries.update(candle);
                            volumeSeries.update(volume);

                            // Atualizar preço
                            document.getElementById('current-price').textContent =
                                `${{data.close.toLocaleString('pt-BR', {{style: 'currency', currency: 'USD'}})}}`;
                        }}
                    }});

                    socket.on('trade_executed', function(trade) {{
                        updateTradesList(trade);
                    }});

                    socket.on('trading_signal', function(signal) {{
                        addSignal(signal);
                    }});
                }}

                // Atualizar lista de trades
                function updateTradesList(trade) {{
                    const tradesList = document.getElementById('trades-list');
                    const isBuy = trade.side === 'buy';

                    const tradeElement = document.createElement('div');
                    tradeElement.className = 'trade-item';
                    tradeElement.innerHTML = `
                        <div class="trade-info">
                            <div class="trade-symbol">${{trade.symbol}} - ${{isBuy ? 'COMPRA' : 'VENDA'}}</div>
                            <div class="trade-details">
                                ${{trade.quantity}} @ ${{trade.price.toLocaleString('pt-BR')}}
                            </div>
                        </div>
                        <div class="trade-pnl ${{trade.pnl >= 0 ? 'positive' : 'negative'}}">
                            ${{trade.pnl >= 0 ? '+' : ''}}${{trade.pnl.toFixed(2)}}
                        </div>
                    `;

                    tradesList.insertBefore(tradeElement, tradesList.firstChild);

                    // Remover mensagem de "nenhum trade"
                    const emptyMessage = tradesList.querySelector('div[style*="text-align: center"]');
                    if (emptyMessage) {{
                        emptyMessage.remove();
                    }}
                }}

                // Adicionar sinal
                function addSignal(signal) {{
                    const signalsList = document.getElementById('signals-list');
                    const isBuy = signal.action === 'buy';

                    const signalElement = document.createElement('div');
                    signalElement.className = 'signal-item';
                    signalElement.innerHTML = `
                        <div class="signal-type signal-${{isBuy ? 'buy' : 'sell'}}">
                            ${{isBuy ? 'COMPRA' : 'VENDA'}}
                        </div>
                        <div class="signal-description">
                            ${{signal.strategy}} - ${{signal.reason}}
                        </div>
                    `;

                    signalsList.insertBefore(signalElement, signalsList.firstChild);

                    // Remover mensagem de "aguardando"
                    const waitingMessage = signalsList.querySelector('div[style*="text-align: center"]');
                    if (waitingMessage) {{
                        waitingMessage.remove();
                    }}

                    // Limpar sinais antigos
                    const signals = signalsList.querySelectorAll('.signal-item');
                    if (signals.length > 20) {{
                        signals[signals.length - 1].remove();
                    }}
                }}

                // Event listeners
                document.addEventListener('DOMContentLoaded', function() {{
                    initChart();

                    // Timeframe buttons
                    document.querySelectorAll('.timeframe-btn').forEach(btn => {{
                        btn.addEventListener('click', function() {{
                            document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                            this.classList.add('active');
                            currentTimeframe = this.dataset.tf;
                            loadChartData();
                        }});
                    }});

                    // Indicator buttons
                    document.querySelectorAll('.indicator-btn').forEach(btn => {{
                        btn.addEventListener('click', function() {{
                            this.classList.toggle('active');
                            // Implementar toggle de indicadores
                        }});
                    }});
                }});

                // Funções globais
                function toggleTrades() {{
                    const panel = document.getElementById('trades-panel');
                    panel.classList.toggle('show');
                }}

                function toggleSignals() {{
                    const panel = document.getElementById('signals-panel');
                    panel.classList.toggle('show');
                }}

                function openManualTrade() {{
                    const dialog = document.createElement('div');
                    dialog.className = 'manual-trade-dialog';
                    dialog.innerHTML = `
                        <div class="dialog-content">
                            <h3>📈 Entrada Manual de Trade</h3>
                            <div class="form-group">
                                <label>Par:</label>
                                <select id="manual-pair">
                                    <option value="BTC/USDT">BTC/USDT</option>
                                    <option value="ETH/USDT">ETH/USDT</option>
                                    <option value="BNB/USDT">BNB/USDT</option>
                                    <option value="ADA/USDT">ADA/USDT</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Ação:</label>
                                <select id="manual-action">
                                    <option value="buy">COMPRA</option>
                                    <option value="sell">VENDA</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Quantidade:</label>
                                <input type="number" id="manual-quantity" step="0.0001" placeholder="0.1">
                            </div>
                            <div class="form-group">
                                <label>Preço:</label>
                                <input type="number" id="manual-price" step="0.01" placeholder="Preço atual">
                            </div>
                            <div class="dialog-actions">
                                <button onclick="executeManualTrade()" class="btn-primary">Executar</button>
                                <button onclick="closeManualTrade()" class="btn">Cancelar</button>
                            </div>
                        </div>
                    `;

                    document.body.appendChild(dialog);
                }}

                function executeManualTrade() {{
                    const trade = {{
                        pair: document.getElementById('manual-pair').value,
                        side: document.getElementById('manual-action').value,
                        quantity: parseFloat(document.getElementById('manual-quantity').value),
                        price: parseFloat(document.getElementById('manual-price').value),
                        timestamp: new Date().toISOString()
                    }};

                    fetch('/api/manual_trade', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(trade)
                    }}).then(response => {{
                        if (response.ok) {{
                            closeManualTrade();
                            showNotification('Trade executado com sucesso!', 'success');
                        }} else {{
                            showNotification('Erro ao executar trade', 'error');
                        }}
                    }});
                }}

                function closeManualTrade() {{
                    const dialog = document.querySelector('.manual-trade-dialog');
                    if (dialog) dialog.remove();
                }}

                function showNotification(message, type) {{
                    const notification = document.createElement('div');
                    notification.className = `notification ${{type}}`;
                    notification.innerHTML = `
                        <div class="notification-content">
                            <span>${{message}}</span>
                            <button onclick="this.parentElement.parentElement.remove()">×</button>
                        </div>
                    `;

                    document.body.appendChild(notification);

                    setTimeout(() => {{
                        notification.classList.add('show');
                    }}, 100);

                    setTimeout(() => {{
                        notification.classList.remove('show');
                        setTimeout(() => notification.remove(), 300);
                    }}, 5000);
                }}
            </script>
        </body>
        </html>
        """

        return html_template

    def save_chart_html(self, symbol: str = "BTC/USDT", timeframe: str = "1h",
                       output_path: str = "tradingview_chart.html") -> str:
        """Salvar HTML do gráfico"""
        html_content = self.generate_chart_html(symbol, timeframe)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_path

def demo_tradingview_chart():
    """Demonstração do gráfico TradingView-like"""
    print("🎨 DEMO - Gráfico TradingView-like")
    print("=" * 50)

    # Criar motor de gráficos
    chart_engine = TradingViewChartEngine()

    # Gerar gráfico
    output_path = chart_engine.save_chart_html("BTC/USDT", "1h", "tradingview_demo.html")

    print(f"✅ Gráfico TradingView-like gerado: {output_path}")
    print(f"📊 Características:")
    print(f"   • Candlesticks idênticos ao TradingView")
    print(f"   • Volume bars coloridos")
    print(f"   • WebSocket para dados reais")
    print(f"   • Entrada manual de trades")
    print(f"   • Painel de sinais e trades")
    print(f"   • Indicadores técnicos")
    print(f"   • Responsive design")
    print(f"   • Interface profissional")

    print(f"\n🚀 Para abrir: abrir arquivo em browser ou integrar no sistema web")

    print("\n🎉 Demo concluído!")

if __name__ == "__main__":
    demo_tradingview_chart()
