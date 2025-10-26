"""
Dashboard Grafik Fonksiyonları
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def plot_price_chart(data, title="Fiyat Grafiği"):
    """Fiyat grafiği çizer - İyileştirilmiş etkileşim"""
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name="OHLC",
        hoverinfo='x+y',
        hovertext=[f"Açılış: {open:.2f} TL<br>Yüksek: {high:.2f} TL<br>Düşük: {low:.2f} TL<br>Kapanış: {close:.2f} TL" 
                  for open, high, low, close in zip(data['open'], data['high'], data['low'], data['close'])]
    ))
    
    # Moving averages ekle - Renk paleti standardizasyonu
    if 'sma_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['sma_20'],
            name="SMA 20",
            line=dict(color='#28a745', width=2),  # Yeşil
            hovertemplate="<b>%{x}</b><br>SMA 20: %{y:.2f} TL<extra></extra>"
        ))
    
    if 'sma_50' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['sma_50'],
            name="SMA 50",
            line=dict(color='#dc3545', width=2),  # Kırmızı
            hovertemplate="<b>%{x}</b><br>SMA 50: %{y:.2f} TL<extra></extra>"
        ))
    
    # Trend çizgisi ekle
    if len(data) > 20:
        # Son 20 günün trend çizgisi
        recent_data = data.tail(20)
        z = np.polyfit(range(len(recent_data)), recent_data['close'], 1)
        trend_line = np.poly1d(z)
        trend_values = trend_line(range(len(recent_data)))
        
        fig.add_trace(go.Scatter(
            x=recent_data.index,
            y=trend_values,
            name="Trend Çizgisi",
            line=dict(color='#17a2b8', width=3, dash='dash'),  # Mavi
            hovertemplate="<b>%{x}</b><br>Trend: %{y:.2f} TL<extra></extra>"
        ))
    
    # Destek/Direnç seviyeleri
    if len(data) > 50:
        recent_high = data['high'].tail(50).max()
        recent_low = data['low'].tail(50).min()
        
        # Direnç seviyesi
        fig.add_hline(
            y=recent_high, 
            line_dash="dot", 
            line_color="#dc3545", 
            annotation_text=f"Direnç: {recent_high:.2f} TL",
            annotation_position="top right"
        )
        
        # Destek seviyesi
        fig.add_hline(
            y=recent_low, 
            line_dash="dot", 
            line_color="#28a745", 
            annotation_text=f"Destek: {recent_low:.2f} TL",
            annotation_position="bottom right"
        )
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#495057'}
        },
        xaxis_title="Tarih",
        yaxis_title="Fiyat (TL)",
        height=500,
        showlegend=True,
        hovermode='x unified',
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=12)
    )
    
    # X ekseni formatı
    fig.update_xaxes(
        tickformat="%d %b %Y",
        tickangle=45
    )
    
    return fig

def plot_volume_chart(data):
    """Hacim grafiği çizer - İyileştirilmiş etkileşim"""
    fig = go.Figure()
    
    # Renk paleti standardizasyonu
    colors = ['#28a745' if close >= open else '#dc3545' 
              for close, open in zip(data['close'], data['open'])]
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['volume'],
        marker_color=colors,
        name="Hacim",
        hovertemplate="<b>%{x}</b><br>Hacim: %{y:,.0f}<extra></extra>"
    ))
    
    fig.update_layout(
        title={
            'text': "İşlem Hacmi",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#495057'}
        },
        xaxis_title="Tarih",
        yaxis_title="Hacim",
        height=300,
        hovermode='x unified',
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=12)
    )
    
    # X ekseni formatı
    fig.update_xaxes(
        tickformat="%d %b %Y",
        tickangle=45
    )
    
    return fig

def plot_technical_indicators(data):
    """Teknik göstergeler grafiği - İyileştirilmiş etkileşim"""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("📈 RSI (Relative Strength Index)", "📊 MACD (Moving Average Convergence Divergence)", "🎯 Bollinger Bands"),
        vertical_spacing=0.15,  # Daha fazla boşluk
        row_heights=[0.3, 0.3, 0.4]
    )
    
    # RSI - Renk paleti standardizasyonu
    if 'rsi' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['rsi'],
            name="RSI",
            line=dict(color='#17a2b8', width=2),  # Mavi
            hovertemplate="<b>%{x}</b><br>RSI: %{y:.1f}<extra></extra>"
        ), row=1, col=1)
        
        # RSI seviyeleri
        fig.add_hline(y=70, line_dash="dash", line_color="#dc3545", row=1, col=1, 
                     annotation_text="Aşırı Alım (70)", annotation_position="top right")
        fig.add_hline(y=30, line_dash="dash", line_color="#28a745", row=1, col=1,
                     annotation_text="Aşırı Satım (30)", annotation_position="bottom right")
        fig.add_hline(y=50, line_dash="dot", line_color="#6c757d", row=1, col=1,
                     annotation_text="Nötr (50)", annotation_position="right")
        
        # RSI bölgelerini renklendir
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(220, 53, 69, 0.1)", layer="below", row=1, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="rgba(40, 167, 69, 0.1)", layer="below", row=1, col=1)
    
    # MACD - Renk paleti standardizasyonu
    if 'macd' in data.columns and 'macd_signal' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['macd'],
            name="MACD",
            line=dict(color='#28a745', width=2),  # Yeşil
            hovertemplate="<b>%{x}</b><br>MACD: %{y:.3f}<extra></extra>"
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['macd_signal'],
            name="MACD Signal",
            line=dict(color='#dc3545', width=2),  # Kırmızı
            hovertemplate="<b>%{x}</b><br>MACD Signal: %{y:.3f}<extra></extra>"
        ), row=2, col=1)
        
        # MACD histogram
        if 'macd_histogram' in data.columns:
            colors = ['#28a745' if val >= 0 else '#dc3545' for val in data['macd_histogram']]
            fig.add_trace(go.Bar(
                x=data.index,
                y=data['macd_histogram'],
                name="MACD Histogram",
                marker_color=colors,
                opacity=0.6,
                hovertemplate="<b>%{x}</b><br>MACD Histogram: %{y:.3f}<extra></extra>"
            ), row=2, col=1)
        
        # MACD sıfır çizgisi
        fig.add_hline(y=0, line_dash="dot", line_color="#6c757d", row=2, col=1,
                     annotation_text="Sıfır Çizgisi", annotation_position="right")
    
    # Bollinger Bands - Renk paleti standardizasyonu
    if 'sma_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['close'],
            name="Fiyat",
            line=dict(color='#495057', width=2),  # Gri
            hovertemplate="<b>%{x}</b><br>Fiyat: %{y:.2f} TL<extra></extra>"
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['sma_20'],
            name="SMA 20",
            line=dict(color='#17a2b8', width=2),  # Mavi
            hovertemplate="<b>%{x}</b><br>SMA 20: %{y:.2f} TL<extra></extra>"
        ), row=3, col=1)
        
        # Bollinger Bands
        if 'bb_upper' in data.columns and 'bb_lower' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['bb_upper'],
                name="BB Üst",
                line=dict(color='#dc3545', width=1, dash='dot'),
                hovertemplate="<b>%{x}</b><br>BB Üst: %{y:.2f} TL<extra></extra>"
            ), row=3, col=1)
            
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['bb_lower'],
                name="BB Alt",
                line=dict(color='#28a745', width=1, dash='dot'),
                hovertemplate="<b>%{x}</b><br>BB Alt: %{y:.2f} TL<extra></extra>"
            ), row=3, col=1)
            
            # Bollinger Bands orta bandı (SMA 20)
            if 'bb_middle' in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data['bb_middle'],
                    name="BB Orta",
                    line=dict(color='#6c757d', width=1, dash='dash'),
                    hovertemplate="<b>%{x}</b><br>BB Orta: %{y:.2f} TL<extra></extra>"
                ), row=3, col=1)
            
            # Bollinger Bands bölgelerini renklendir
            fig.add_hrect(y0=data['bb_upper'].min(), y1=data['bb_upper'].max(), 
                         fillcolor="rgba(220, 53, 69, 0.05)", layer="below", row=3, col=1)
            fig.add_hrect(y0=data['bb_lower'].min(), y1=data['bb_lower'].max(), 
                         fillcolor="rgba(40, 167, 69, 0.05)", layer="below", row=3, col=1)
    
    fig.update_layout(
        height=900,  # Daha yüksek
        showlegend=True,
        hovermode='x unified',
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=12),
        margin=dict(l=50, r=50, t=80, b=50),  # Kenar boşlukları
        title={
            'text': "Teknik İndikatörler Analizi",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#495057'}
        }
    )
    
    # X ekseni formatı
    fig.update_xaxes(
        tickformat="%d %b %Y",
        tickangle=45
    )
    
    return fig
