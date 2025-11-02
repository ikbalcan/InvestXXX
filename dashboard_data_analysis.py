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

@st.cache_data(ttl=1800)  # 30 dakika cache - Optimizasyon: Feature engineering cache'leniyor
def create_features(data, config_hash=None):
    """Özellikler oluşturur (endeks verisi ile)"""
    try:
        from data_loader import DataLoader
        from feature_engineering import FeatureEngineer
        config = load_config()
        
        # DataLoader ve FeatureEngineer oluştur
        loader = DataLoader(config)
        engineer = FeatureEngineer(config, data_loader=loader)
        
        # BIST 100 endeks verisini yükle
        index_data = loader.get_index_data(period="2y")
        
        # Özellikleri oluştur
        return engineer.create_all_features(data, index_data=index_data)
    except Exception as e:
        import logging
        logging.error(f"Feature oluşturma hatası: {str(e)}")
        return pd.DataFrame()

def show_data_analysis_tab(selected_symbol, period="2y", interval="1d"):
    """Veri Analizi Tab"""
    
    st.header("📊 Veri Analizi")
    
    # Zaman dilimi bilgisi
    st.info(f"📅 **Zaman Dilimi:** {interval} | **Periyot:** {period}")
    
    # Zaman dilimi açıklaması
    interval_descriptions = {
        "1d": "📊 **Günlük:** Uzun vadeli trend analizi için ideal",
        "1h": "⏰ **Saatlik:** Kısa vadeli günlük işlemler için",
        "4h": "🕐 **4 Saatlik:** Swing trading için optimal",
        "1wk": "📈 **Haftalık:** Uzun vadeli yatırım analizi"
    }
    
    if interval in interval_descriptions:
        st.info(interval_descriptions[interval])
    
    # Veri yükle
    with st.spinner("Veri yükleniyor..."):
        data = load_stock_data(selected_symbol, period, interval)
    
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
    st.plotly_chart(fig_price, use_container_width=True, config={'displayModeBar': True})
    
    # Hacim grafiği
    st.subheader("📊 Hacim Analizi")
    fig_volume = plot_volume_chart(data)
    st.plotly_chart(fig_volume, use_container_width=True, config={'displayModeBar': True})
    
    # Teknik indikatörler
    st.subheader("🔧 Teknik İndikatörler")
    
    with st.spinner("Teknik indikatörler hesaplanıyor..."):
        features_df = create_features(data)
    
    if not features_df.empty:
        fig_technical = plot_technical_indicators(features_df)
        st.plotly_chart(fig_technical, use_container_width=True, config={'displayModeBar': True})
        
        # Teknik indikatör açıklamaları - Collapsible
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; margin: 20px 0;">
            <h3 style="color: #495057; font-size: 1.5rem; margin: 0;">📚 İndikatör Açıklamaları</h3>
            <p style="color: #6c757d; font-size: 1rem; margin: 5px 0 0 0;">Her indikatörün altında detaylı açıklama</p>
        </div>
        """, unsafe_allow_html=True)
        
        # RSI Collapsible
        with st.expander("📈 RSI (Relative Strength Index) - Nasıl İncelenir?", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%); border-radius: 10px; padding: 20px; border-left: 4px solid #2196f3;">
                <div style="margin-bottom: 15px;">
                    <h4 style="color: #1976d2; margin: 0 0 10px 0; font-size: 1.2rem;">🔍 Nasıl Okunur:</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li><strong style="color: #d32f2f;">70+</strong>: Aşırı alım bölgesi → <span style="color: #d32f2f;">Satış sinyali</span></li>
                        <li><strong style="color: #388e3c;">30-</strong>: Aşırı satım bölgesi → <span style="color: #388e3c;">Alış sinyali</span></li>
                        <li><strong style="color: #f57c00;">50</strong>: Nötr seviye</li>
                        <li><strong style="color: #7b1fa2;">Divergence</strong>: Fiyat ile RSI ters yönde hareket ederse trend değişimi habercisi</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #1976d2; margin: 0 0 10px 0; font-size: 1.2rem;">💡 Kullanım Alanları:</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li>Kısa vadeli alım/satım sinyalleri</li>
                        <li>Momentum analizi</li>
                        <li>Aşırı alım/satım tespiti</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # MACD Collapsible
        with st.expander("📊 MACD (Moving Average Convergence Divergence) - Nasıl İncelenir?", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%); border-radius: 10px; padding: 20px; border-left: 4px solid #4caf50;">
                <div style="margin-bottom: 15px;">
                    <h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 1.2rem;">🔍 Nasıl Okunur:</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li><strong style="color: #388e3c;">MACD > Signal</strong>: <span style="color: #388e3c;">Yükseliş momentumu</span></li>
                        <li><strong style="color: #d32f2f;">MACD < Signal</strong>: <span style="color: #d32f2f;">Düşüş momentumu</span></li>
                        <li><strong style="color: #f57c00;">Histogram</strong>: Momentum değişimini gösterir</li>
                        <li><strong style="color: #7b1fa2;">Sıfır çizgisi</strong>: Trend değişim noktası</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 1.2rem;">💡 Kullanım Alanları:</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li>Trend değişim sinyalleri</li>
                        <li>Momentum analizi</li>
                        <li>Uzun vadeli trend takibi</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Bollinger Bands Collapsible
        with st.expander("🎯 Bollinger Bands - Nasıl İncelenir?", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%); border-radius: 10px; padding: 20px; border-left: 4px solid #ff9800;">
                <div style="margin-bottom: 15px;">
                    <h4 style="color: #f57c00; margin: 0 0 10px 0; font-size: 1.2rem;">🔍 Nasıl Okunur:</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li><strong style="color: #d32f2f;">Fiyat > Üst Band</strong>: Aşırı alım → <span style="color: #d32f2f;">Satış sinyali</span></li>
                        <li><strong style="color: #388e3c;">Fiyat < Alt Band</strong>: Aşırı satım → <span style="color: #388e3c;">Alış sinyali</span></li>
                        <li><strong style="color: #7b1fa2;">Band Daralması</strong>: Büyük hareket habercisi</li>
                        <li><strong style="color: #f57c00;">Band Genişlemesi</strong>: Volatilite artışı</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #f57c00; margin: 0 0 10px 0; font-size: 1.2rem;">💡 Kullanım Alanları:</h4>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li>Volatilite analizi</li>
                        <li>Destek/direnç seviyeleri</li>
                        <li>Breakout sinyalleri</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Teknik indikatör özeti
        st.subheader("📊 Teknik İndikatör Özeti")
        st.info("💡 **İpucu:** Bu değerler son günün teknik analizini gösterir. Birden fazla indikatörün aynı yönde sinyal vermesi daha güvenilir sonuçlar verir.")
        
        # Son değerler
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'rsi' in features_df.columns:
                rsi_value = features_df['rsi'].iloc[-1]
                if rsi_value > 70:
                    st.error(f"RSI: {rsi_value:.1f} (Aşırı Alım)")
                elif rsi_value < 30:
                    st.success(f"RSI: {rsi_value:.1f} (Aşırı Satım)")
                else:
                    st.info(f"RSI: {rsi_value:.1f} (Nötr)")
        
        with col2:
            if 'macd' in features_df.columns and 'macd_signal' in features_df.columns:
                macd_value = features_df['macd'].iloc[-1]
                signal_value = features_df['macd_signal'].iloc[-1]
                if macd_value > signal_value:
                    st.success(f"MACD: {macd_value:.3f} (Yükseliş)")
                else:
                    st.error(f"MACD: {macd_value:.3f} (Düşüş)")
        
        with col3:
            if 'bb_upper' in features_df.columns and 'bb_lower' in features_df.columns:
                current_price = features_df['close'].iloc[-1]
                bb_upper = features_df['bb_upper'].iloc[-1]
                bb_lower = features_df['bb_lower'].iloc[-1]
                
                if current_price > bb_upper:
                    st.error(f"BB: Aşırı Alım")
                elif current_price < bb_lower:
                    st.success(f"BB: Aşırı Satım")
                else:
                    st.info(f"BB: Normal Seviye")
        
        with col4:
            if 'sma_20' in features_df.columns and 'sma_50' in features_df.columns:
                sma_20 = features_df['sma_20'].iloc[-1]
                sma_50 = features_df['sma_50'].iloc[-1]
                current_price = features_df['close'].iloc[-1]
                
                if current_price > sma_20 > sma_50:
                    st.success(f"SMA: Güçlü Yükseliş")
                elif current_price < sma_20 < sma_50:
                    st.error(f"SMA: Güçlü Düşüş")
                else:
                    st.warning(f"SMA: Karışık Sinyal")
        
        # Genel analiz önerisi
        st.markdown("---")
        st.subheader("🎯 Genel Analiz Önerisi")
        
        # Sinyal sayısını hesapla
        buy_signals = 0
        sell_signals = 0
        
        if 'rsi' in features_df.columns:
            rsi_value = features_df['rsi'].iloc[-1]
            if rsi_value < 30:
                buy_signals += 1
            elif rsi_value > 70:
                sell_signals += 1
        
        if 'macd' in features_df.columns and 'macd_signal' in features_df.columns:
            macd_value = features_df['macd'].iloc[-1]
            signal_value = features_df['macd_signal'].iloc[-1]
            if macd_value > signal_value:
                buy_signals += 1
            else:
                sell_signals += 1
        
        if 'bb_upper' in features_df.columns and 'bb_lower' in features_df.columns:
            current_price = features_df['close'].iloc[-1]
            bb_upper = features_df['bb_upper'].iloc[-1]
            bb_lower = features_df['bb_lower'].iloc[-1]
            if current_price < bb_lower:
                buy_signals += 1
            elif current_price > bb_upper:
                sell_signals += 1
        
        if 'sma_20' in features_df.columns and 'sma_50' in features_df.columns:
            sma_20 = features_df['sma_20'].iloc[-1]
            sma_50 = features_df['sma_50'].iloc[-1]
            current_price = features_df['close'].iloc[-1]
            if current_price > sma_20 > sma_50:
                buy_signals += 1
            elif current_price < sma_20 < sma_50:
                sell_signals += 1
        
        # Genel öneri
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🟢 Alış Sinyalleri", buy_signals)
        
        with col2:
            st.metric("🔴 Satış Sinyalleri", sell_signals)
        
        with col3:
            if buy_signals > sell_signals:
                st.success("📈 Genel Trend: Yükseliş")
            elif sell_signals > buy_signals:
                st.error("📉 Genel Trend: Düşüş")
            else:
                st.warning("⚖️ Genel Trend: Nötr")
        
        # Detaylı öneri
        if buy_signals >= 3:
            st.success("🚀 **Güçlü Alış Sinyali:** Çoğu indikatör alış yönünde sinyal veriyor!")
        elif sell_signals >= 3:
            st.error("⚠️ **Güçlü Satış Sinyali:** Çoğu indikatör satış yönünde sinyal veriyor!")
        elif buy_signals > sell_signals:
            st.info("📈 **Hafif Yükseliş Eğilimi:** Alış sinyalleri daha fazla")
        elif sell_signals > buy_signals:
            st.info("📉 **Hafif Düşüş Eğilimi:** Satış sinyalleri daha fazla")
        else:
            st.warning("⚖️ **Karışık Sinyaller:** İndikatörler farklı yönlerde sinyal veriyor")
    else:
        st.warning("⚠️ Teknik indikatörler hesaplanamadı!")
    
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
    st.dataframe(data.tail(20), width='stretch')
    
    # İstatistikler
    st.subheader("📊 İstatistikler")
    st.dataframe(data.describe(), width='stretch')
