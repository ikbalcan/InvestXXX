"""
Dashboard Grafik Fonksiyonları
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def plot_price_chart(data, title="Fiyat Grafiği"):
    """Fiyat grafiği çizer"""
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name="OHLC"
    ))
    
    # Moving averages ekle
    if 'sma_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['sma_20'],
            name="SMA 20",
            line=dict(color='orange', width=2)
        ))
    
    if 'sma_50' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['sma_50'],
            name="SMA 50",
            line=dict(color='red', width=2)
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Tarih",
        yaxis_title="Fiyat (TL)",
        height=500,
        showlegend=True
    )
    
    return fig

def plot_volume_chart(data):
    """Hacim grafiği çizer"""
    fig = go.Figure()
    
    colors = ['green' if close >= open else 'red' 
              for close, open in zip(data['close'], data['open'])]
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['volume'],
        marker_color=colors,
        name="Hacim"
    ))
    
    fig.update_layout(
        title="İşlem Hacmi",
        xaxis_title="Tarih",
        yaxis_title="Hacim",
        height=300
    )
    
    return fig

def plot_technical_indicators(data):
    """Teknik göstergeler grafiği"""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("RSI", "MACD", "Bollinger Bands"),
        vertical_spacing=0.1,
        row_heights=[0.3, 0.3, 0.4]
    )
    
    # RSI
    if 'rsi' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['rsi'],
            name="RSI",
            line=dict(color='purple')
        ), row=1, col=1)
        
        # RSI seviyeleri
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=1, col=1)
    
    # MACD
    if 'macd' in data.columns and 'macd_signal' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['macd'],
            name="MACD",
            line=dict(color='blue')
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['macd_signal'],
            name="MACD Signal",
            line=dict(color='red')
        ), row=2, col=1)
    
    # Bollinger Bands
    if 'sma_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['close'],
            name="Fiyat",
            line=dict(color='black')
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['sma_20'],
            name="SMA 20",
            line=dict(color='orange')
        ), row=3, col=1)
    
    fig.update_layout(height=800, showlegend=True)
    return fig
