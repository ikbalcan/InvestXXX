"""
Veri Analizi Tab - Dashboard Modülü
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from dashboard_utils import load_config, load_stock_data, analyze_stock_characteristics
from dashboard_charts import plot_price_chart, plot_volume_chart, plot_technical_indicators

@st.cache_data
def create_features(data):
    """Özellikler oluşturur"""
    try:
        from feature_engineering import FeatureEngineer
        engineer = FeatureEngineer(load_config())
        return engineer.create_all_features(data)
    except:
        return pd.DataFrame()

def show_data_analysis_tab(selected_symbol, period="2y"):
    """Veri Analizi Tab"""
    
    st.header("📊 Veri Analizi")
    
    # Veri yükle
    with st.spinner("Veri yükleniyor..."):
        data = load_stock_data(selected_symbol, period)
    
    if data.empty:
        st.error("Veri yüklenemedi!")
        return
    
    # Temel bilgiler
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Son Fiyat",
            f"{data['close'].iloc[-1]:.2f} TL",
            f"{data['close'].pct_change().iloc[-1]*100:+.2f}%"
        )
    
    with col2:
        st.metric(
            "Günlük Değişim",
            f"{data['close'].iloc[-1] - data['close'].iloc[-2]:.2f} TL",
            f"{((data['close'].iloc[-1] / data['close'].iloc[-2]) - 1)*100:+.2f}%"
        )
    
    with col3:
        st.metric(
            "Hacim",
            f"{data['volume'].iloc[-1]:,}",
            f"{data['volume'].pct_change().iloc[-1]*100:+.1f}%"
        )
    
    with col4:
        volatility = data['close'].pct_change().std() * np.sqrt(252) * 100
        st.metric(
            "Volatilite",
            f"{volatility:.1f}%",
            "Yıllık"
        )
    
    # Grafikler
    st.subheader("📈 Fiyat Grafiği")
    fig_price = plot_price_chart(data, f"{selected_symbol} Fiyat Grafiği")
    st.plotly_chart(fig_price, use_container_width=True)
    
    # Hacim grafiği
    st.subheader("📊 Hacim Analizi")
    fig_volume = plot_volume_chart(data)
    st.plotly_chart(fig_volume, use_container_width=True)
    
    # Teknik indikatörler
    st.subheader("🔧 Teknik İndikatörler")
    fig_technical = plot_technical_indicators(data)
    st.plotly_chart(fig_technical, use_container_width=True)
    
    # Hisse karakteristikleri
    st.subheader("📋 Hisse Karakteristikleri")
    characteristics = analyze_stock_characteristics(selected_symbol, period)
    
    if characteristics is None:
        st.warning("⚠️ Hisse karakteristikleri analiz edilemedi. Veri yüklenemedi.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📊 Temel Bilgiler")
        st.write(f"**Sembol:** {selected_symbol}")
        st.write(f"**Veri Sayısı:** {len(data)} gün")
        st.write(f"**Başlangıç:** {data.index[0].strftime('%d.%m.%Y')}")
        st.write(f"**Bitiş:** {data.index[-1].strftime('%d.%m.%Y')}")
    
    with col2:
        st.markdown("### 📈 Performans")
        st.write(f"**Volatilite:** %{characteristics['volatility']*100:.1f}")
        st.write(f"**Volatilite Kategorisi:** {characteristics['volatility_category']}")
        st.write(f"**Ortalama Hacim:** {characteristics['avg_volume']:,.0f}")
        st.write(f"**Fiyat Aralığı:** %{characteristics['price_range']*100:.1f}")
    
    with col3:
        st.markdown("### 🎯 Öneriler")
        recommendations = characteristics['recommendations']
        st.write(f"**Model Karmaşıklığı:** {recommendations['model_complexity']}")
        st.write(f"**Risk Seviyesi:** {recommendations['risk_level']}")
        st.write(f"**Max Depth:** {recommendations['max_depth']}")
        st.write(f"**Learning Rate:** {recommendations['learning_rate']}")
    
    # Veri tablosu
    st.subheader("📋 Ham Veri")
    st.dataframe(data.tail(20), use_container_width=True)
    
    # İstatistikler
    st.subheader("📊 İstatistikler")
    st.dataframe(data.describe(), use_container_width=True)
