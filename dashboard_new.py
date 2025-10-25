"""
Hisse Senedi Yön Tahmini Sistemi - Streamlit Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import json
from datetime import datetime

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from backtest import Backtester
from live_trade import PaperTrader
from price_target_predictor import PriceTargetPredictor

# Yardımcı modülleri import et
from dashboard_utils import load_config, load_stock_data, analyze_stock_characteristics, get_auto_params
from dashboard_charts import plot_price_chart, plot_volume_chart, plot_technical_indicators

@st.cache_data
def create_features(data):
    """Özellikler oluşturur"""
    try:
        engineer = FeatureEngineer(load_config())
        return engineer.create_all_features(data)
    except:
        return pd.DataFrame()

def main():
    """Ana dashboard"""
    
    # Streamlit sayfa konfigürasyonu - Tam genişlik
    st.set_page_config(
        page_title="Hisse Senedi Yön Tahmini",
        page_icon="📈",
        layout="wide",  # Tam genişlik
        initial_sidebar_state="expanded"
    )
    
    # Başlık
    st.markdown('<h1 class="main-header">📈 Hisse Senedi Yön Tahmini Sistemi</h1>', 
                unsafe_allow_html=True)
    
    # CSS stilleri - Tam genişlik
    st.markdown("""
    <style>
        /* Ana container'ı tam genişlik yap */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        
        /* Sidebar'ı daralt */
        .css-1d391kg {
            width: 200px;
        }
        
        /* Ana içeriği genişlet */
        .css-1v0mbdj {
            width: calc(100% - 200px);
        }
        
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .signal-buy {
            background-color: #d4edda;
            color: #155724;
            padding: 0.5rem;
            border-radius: 0.25rem;
            font-weight: bold;
        }
        .signal-sell {
            background-color: #f8d7da;
            color: #721c24;
            padding: 0.5rem;
            border-radius: 0.25rem;
            font-weight: bold;
        }
        
        /* Tüm elementleri tam genişlik yap */
        .stDataFrame, .stPlotlyChart, .stMetric {
            width: 100% !important;
        }
        
        /* Tab içeriklerini genişlet */
        .stTabs [data-baseweb="tab-list"] {
            width: 100%;
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("⚙️ Kontrol Paneli")
    
    # Konfigürasyon yükle
    config = load_config()
    symbols = config.get('TARGET_STOCKS', ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS'])
    
    # Popüler BIST hisseleri listesi
    popular_stocks = [
        "THYAO.IS", "AKBNK.IS", "BIMAS.IS", "EREGL.IS", "FONET.IS", 
        "GARAN.IS", "ISCTR.IS", "KRDMD.IS", "PETKM.IS", "SAHOL.IS", 
        "TUPRS.IS", "ASELS.IS", "KOZAL.IS", "SASA.IS", "TCELL.IS"
    ]
    
    # Hisse seçimi - hem config'den hem popüler hisselerden
    all_symbols = list(set(symbols + popular_stocks))
    all_symbols.sort()
    
    # Manuel hisse girişi için text input
    st.sidebar.subheader("🔍 Hisse Arama")
    custom_symbol = st.sidebar.text_input(
        "Manuel Hisse Kodu:", 
        placeholder="örn: GARAN.IS",
        help="BIST hisse kodunu .IS uzantısı ile girin"
    )
    
    # Hisse seçimi
    if custom_symbol and custom_symbol.upper() not in all_symbols:
        all_symbols.insert(0, custom_symbol.upper())
    
    selected_symbol = st.sidebar.selectbox(
        "Hisse Senedi Seçin:",
        all_symbols,
        index=0
    )
    
    # Veri periyodu
    period = st.sidebar.selectbox(
        "Veri Periyodu:",
        ["1y", "2y", "5y"],
        index=1
    )
    
    # Cache yönetimi
    st.sidebar.subheader("🗂️ Cache Yönetimi")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🔄 Yenile", help="Cache'i temizle ve yeniden yükle"):
            # Cache dosyasını sil
            cache_file = f"data/raw/{selected_symbol.replace('.IS', '')}_cache.csv"
            if os.path.exists(cache_file):
                os.remove(cache_file)
            st.rerun()
    
    with col2:
        if st.button("🗑️ Tüm Cache", help="Tüm cache dosyalarını temizle"):
            import glob
            cache_files = glob.glob("data/raw/*_cache.csv")
            for file in cache_files:
                try:
                    os.remove(file)
                except:
                    pass
            st.success("Tüm cache temizlendi!")
            st.rerun()
    
    # Ana içerik - Güzel tab görünümü
    st.markdown("""
    <style>
        /* Tab görünümünü iyileştir */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding-left: 20px;
            padding-right: 20px;
            background-color: #f0f2f6;
            border-radius: 10px 10px 0 0;
            border: 1px solid #e0e0e0;
            margin-right: 5px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #1f77b4;
            color: white;
            border-color: #1f77b4;
        }
        
        .stTabs [aria-selected="false"] {
            background-color: #f8f9fa;
            color: #495057;
        }
        
        .stTabs [aria-selected="false"]:hover {
            background-color: #e9ecef;
            border-color: #1f77b4;
        }
        
        /* Tab içeriklerini güzel kutular haline getir */
        .stTabs [data-baseweb="tab-panel"] {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 0 0 10px 10px;
            padding: 20px;
            margin-top: -1px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Tab sırasını kontrol et ve düzelt
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Veri Analizi", 
        "🔮 Gelecek Tahmin", 
        "🤖 Model Tahminleri", 
        "📈 Backtest", 
        "💼 Paper Trading", 
        "🎯 Model Eğitimi"
    ])
    
    with tab1:
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
                f"{data['close'].pct_change().iloc[-1]:.2%}"
            )
        
        with col2:
            st.metric(
                "Günlük Hacim",
                f"{data['volume'].iloc[-1]:,.0f}",
                f"{data['volume'].pct_change().iloc[-1]:.2%}"
            )
        
        with col3:
            volatility = data['close'].pct_change().std() * np.sqrt(252)
            st.metric(
                "Yıllık Volatilite",
                f"{volatility:.2%}"
            )
        
        with col4:
            total_return = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1
            st.metric(
                "Toplam Getiri",
                f"{total_return:.2%}"
            )
        
        # Grafikler
        st.subheader("Fiyat Grafiği")
        price_chart = plot_price_chart(data, f"{selected_symbol} Fiyat Grafiği")
        st.plotly_chart(price_chart, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("İşlem Hacmi")
            volume_chart = plot_volume_chart(data)
            st.plotly_chart(volume_chart, use_container_width=True)
        
        with col2:
            st.subheader("Getiri Dağılımı")
            returns = data['close'].pct_change().dropna()
            
            fig = px.histogram(
                returns,
                nbins=50,
                title="Günlük Getiri Dağılımı",
                labels={'x': 'Getiri', 'y': 'Frekans'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Teknik göstergeler
        st.subheader("Teknik Göstergeler")
        
        with st.spinner("Özellikler oluşturuluyor..."):
            features_df = create_features(data)
        
        if not features_df.empty:
            indicators_chart = plot_technical_indicators(features_df)
            st.plotly_chart(indicators_chart, use_container_width=True)
            
            # Özellik özeti
            st.subheader("Özellik Özeti")
            
            feature_cols = [col for col in features_df.columns 
                           if col not in ['open', 'high', 'low', 'close', 'volume', 'adj_close']]
            
            feature_summary = features_df[feature_cols].describe()
            st.dataframe(feature_summary, use_container_width=True)
    
    with tab2:
        st.header("🔮 Gelecek Tahmin")
        st.info("🎯 Bu sekme hissenin **bir sonraki hamlesini** tahmin eder ve size net sinyal verir!")
        
        # Model seçimi
        model_files = []
        if os.path.exists('src/models'):
            model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
        
        if not model_files:
            st.warning("⚠️ Eğitilmiş model bulunamadı! Önce model eğitimi yapın.")
        else:
            # En son modeli otomatik seç
            model_files.sort(reverse=True)
            selected_model = st.selectbox("🔮 Tahmin Modeli:", model_files, index=0, key="prediction_model_selection")
            
            # Tahmin butonu
            if st.button("🔮 Gelecek Hamleyi Tahmin Et", type="primary"):
                with st.spinner("🔮 Gelecek hamle tahmin ediliyor..."):
                    try:
                        # Modeli yükle
                        predictor = StockDirectionPredictor(config)
                        model_path = f'src/models/{selected_model}'
                        
                        if not predictor.load_model(model_path):
                            st.error("❌ Model yüklenemedi!")
                        else:
                            # Güncel veri yükle
                            data = load_stock_data(selected_symbol, "1y")
                            features_df = create_features(data)
                            
                            if features_df.empty:
                                st.error("❌ Özellikler oluşturulamadı!")
                            else:
                                # Son günün tahminini yap
                                X, y = predictor.prepare_data(features_df)
                                predictions, probabilities = predictor.predict(X)
                                
                                # Son tahmin
                                last_prediction = predictions[-1]
                                last_confidence = np.max(probabilities[-1])
                                last_prob_up = probabilities[-1][1]
                                last_prob_down = probabilities[-1][0]
                                
                                # Son fiyat
                                last_price = data['close'].iloc[-1]
                                
                                # Volatilite hesapla
                                volatility = data['close'].pct_change().std() * np.sqrt(252)
                                
                                # Hedef fiyat tahmini - Model verileri ile
                                price_predictor = PriceTargetPredictor(config)
                                
                                # Model metriklerini al (varsa)
                                model_metrics = {}
                                try:
                                    # Model dosyasından metrikleri yükle
                                    metrics_file = f'src/models/{selected_model}/metrics.json'
                                    if os.path.exists(metrics_file):
                                        with open(metrics_file, 'r') as f:
                                            model_metrics = json.load(f)
                                    else:
                                        # Alternatif: Model sınıfından metrikleri al
                                        if hasattr(predictor, 'test_metrics'):
                                            model_metrics = predictor.test_metrics
                                        else:
                                            # Varsayılan metrikler
                                            model_metrics = {
                                                'accuracy': 0.6,
                                                'precision': 0.6,
                                                'recall': 0.6,
                                                'f1_score': 0.6
                                            }
                                except Exception as e:
                                    # Hata durumunda varsayılan metrikler
                                    model_metrics = {
                                        'accuracy': 0.6,
                                        'precision': 0.6,
                                        'recall': 0.6,
                                        'f1_score': 0.6
                                    }
                                
                                # Model verilerini hazırla
                                model_data = {
                                    'test_metrics': {
                                        'accuracy': model_metrics.get('accuracy', 0.5),
                                        'precision': model_metrics.get('precision', 0.5),
                                        'recall': model_metrics.get('recall', 0.5),
                                        'f1_score': model_metrics.get('f1_score', 0.5)
                                    }
                                }
                                
                                price_targets = price_predictor.calculate_price_targets(
                                    last_price, last_prediction, last_confidence, volatility, data, model_data
                                )
                                
                                # Ana Karar - Basit ve Net
                                st.markdown("---")
                                st.subheader("🎯 Yatırım Kararı")
                                
                                if last_prediction == 1:  # AL sinyali
                                    st.markdown(f"""
                                    <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 30px; border-radius: 20px; text-align: center; border: 3px solid #28a745; margin: 20px 0; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);">
                                        <h1 style="color: #155724; margin: 0; font-size: 3em;">🟢 AL</h1>
                                        <h3 style="color: #155724; margin: 15px 0;">Hisse yükselişe geçecek!</h3>
                                        <p style="color: #155724; margin: 0; font-size: 1.3em; font-weight: bold;">Güven: %{last_confidence*100:.1f}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Basit öneriler
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.info(f"""
                                        **📈 Pozisyonunuz Yoksa:**
                                        ✅ **AL** - Yükseliş bekleniyor
                                        🎯 Hedef: {price_targets['targets']['moderate']:.2f} TL
                                        ⏰ Tahmini süre: {price_targets['time_targets']['moderate']['estimated_days']} gün
                                        """)
                                    with col2:
                                        st.info(f"""
                                        **📊 Pozisyonunuz Varsa:**
                                        ✅ **KORU** - Yükseliş devam edecek
                                        🎯 Hedef: {price_targets['targets']['aggressive']:.2f} TL
                                        ⏰ Tahmini süre: {price_targets['time_targets']['aggressive']['estimated_days']} gün
                                        """)
                                    
                                else:  # SAT sinyali
                                    st.markdown(f"""
                                    <div style="background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); padding: 30px; border-radius: 20px; text-align: center; border: 3px solid #dc3545; margin: 20px 0; box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);">
                                        <h1 style="color: #721c24; margin: 0; font-size: 3em;">🔴 SAT</h1>
                                        <h3 style="color: #721c24; margin: 15px 0;">Hisse düşüşe geçecek!</h3>
                                        <p style="color: #721c24; margin: 0; font-size: 1.3em; font-weight: bold;">Güven: %{last_confidence*100:.1f}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Basit öneriler
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.warning(f"""
                                        **📉 Pozisyonunuz Yoksa:**
                                        ⏳ **BEKLE** - Düşüş bekleniyor
                                        🎯 Hedef: {price_targets['targets']['moderate']:.2f} TL
                                        ⏰ Tahmini süre: {price_targets['time_targets']['moderate']['estimated_days']} gün
                                        """)
                                    with col2:
                                        st.error(f"""
                                        **📊 Pozisyonunuz Varsa:**
                                        ❌ **SAT** - Düşüş başlayacak
                                        🛡️ Stop Loss: {price_targets['stop_loss']:.2f} TL
                                        ⏰ Tahmini süre: {price_targets['time_targets']['conservative']['estimated_days']} gün
                                        """)
                                
                                # Temel Bilgiler
                                st.subheader("📊 Temel Bilgiler")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("💰 Mevcut Fiyat", f"{last_price:.2f} TL")
                                
                                with col2:
                                    # Güven skoru düzeltmesi
                                    if last_confidence > 0.75:
                                        st.success(f"🎯 Güven: %{last_confidence*100:.1f}")
                                    elif last_confidence > 0.55:
                                        st.warning(f"⚠️ Güven: %{last_confidence*100:.1f}")
                                    else:
                                        st.error(f"❌ Güven: %{last_confidence*100:.1f}")
                                
                                with col3:
                                    volatility_category = "Çok Yüksek" if volatility > 0.6 else "Yüksek" if volatility > 0.4 else "Orta" if volatility > 0.25 else "Düşük"
                                    st.metric("📊 Volatilite", volatility_category)
                                
                                with col4:
                                    st.metric("📈 Risk/Getiri", f"{price_targets['risk_reward_ratio']:.2f}")
                                
                                # Destek/Direnç Seviyeleri - Önemli!
                                st.subheader("🎯 Destek/Direnç Seviyeleri")
                                
                                chart_analysis = price_targets['time_targets']['conservative']['chart_analysis']
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.markdown(f"""
                                    <div style="background-color: #e8f5e8; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #28a745;">
                                        <h3 style="color: #155724; margin: 0;">🛡️ Destek</h3>
                                        <h2 style="color: #155724; margin: 10px 0;">{chart_analysis['support_level']:.2f} TL</h2>
                                        <p style="color: #666; margin: 0;">Mevcut fiyattan %{((chart_analysis['support_level'] - last_price) / last_price * 100):+.1f}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col2:
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #6c757d;">
                                        <h3 style="color: #495057; margin: 0;">💰 Mevcut</h3>
                                        <h2 style="color: #495057; margin: 10px 0;">{last_price:.2f} TL</h2>
                                        <p style="color: #666; margin: 0;">Son fiyat</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col3:
                                    st.markdown(f"""
                                    <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #dc3545;">
                                        <h3 style="color: #721c24; margin: 0;">🚀 Direnç</h3>
                                        <h2 style="color: #721c24; margin: 10px 0;">{chart_analysis['resistance_level']:.2f} TL</h2>
                                        <p style="color: #666; margin: 0;">Mevcut fiyattan %{((chart_analysis['resistance_level'] - last_price) / last_price * 100):+.1f}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Basit Hedef Fiyatlar
                                st.subheader("🎯 Hedef Fiyatlar")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric(
                                        "Konservatif Hedef", 
                                        f"{price_targets['targets']['conservative']:.2f} TL",
                                        f"{((price_targets['targets']['conservative'] - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                with col2:
                                    st.metric(
                                        "Orta Hedef", 
                                        f"{price_targets['targets']['moderate']:.2f} TL",
                                        f"{((price_targets['targets']['moderate'] - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                with col3:
                                    st.metric(
                                        "Agresif Hedef", 
                                        f"{price_targets['targets']['aggressive']:.2f} TL",
                                        f"{((price_targets['targets']['aggressive'] - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                with col4:
                                    st.metric(
                                        "Stop Loss", 
                                        f"{price_targets['stop_loss']:.2f} TL",
                                        f"{((price_targets['stop_loss'] - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                # Basit Tahmini Süreler
                                st.subheader("📅 Tahmini Süreler")
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    conservative_info = price_targets['time_targets']['conservative']
                                    st.info(f"""
                                    **🛡️ Konservatif**
                                    {conservative_info['estimated_days']} gün
                                    ({conservative_info['min_days']}-{conservative_info['max_days']} gün arası)
                                    """)
                                
                                with col2:
                                    moderate_info = price_targets['time_targets']['moderate']
                                    st.info(f"""
                                    **⚖️ Orta**
                                    {moderate_info['estimated_days']} gün
                                    ({moderate_info['min_days']}-{moderate_info['max_days']} gün arası)
                                    """)
                                
                                with col3:
                                    aggressive_info = price_targets['time_targets']['aggressive']
                                    st.info(f"""
                                    **🚀 Agresif**
                                    {aggressive_info['estimated_days']} gün
                                    ({aggressive_info['min_days']}-{aggressive_info['max_days']} gün arası)
                                    """)
                                
                                # Detaylı Analiz (Daraltılabilir)
                    except Exception as e:
                        st.error(f"❌ Tahmin hatası: {str(e)}")
    
    with tab3:
        st.header("🤖 Model Tahminleri")
        
        # Model yükleme
        model_files = []
        if os.path.exists('src/models'):
            model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
        
        if not model_files:
            st.warning("Eğitilmiş model bulunamadı! Önce model eğitimi yapın.")
            return
        
        # En son modeli otomatik seç
        model_files.sort(reverse=True)  # En yeni modeli başa al
        selected_model = st.selectbox("Model Seçin:", model_files, index=0, key="model_selection")
        
        if st.button("Tahmin Yap"):
            with st.spinner("Tahmin yapılıyor..."):
                try:
                    # Modeli yükle
                    predictor = StockDirectionPredictor(config)
                    model_path = f'src/models/{selected_model}'
                    
                    if not predictor.load_model(model_path):
                        st.error("Model yüklenemedi!")
                        return
                    
                    # Veri hazırla
                    data = load_stock_data(selected_symbol, period)
                    features_df = create_features(data)
                    
                    if features_df.empty:
                        st.error("Özellikler oluşturulamadı!")
                        return
                    
                    # Tahmin yap
                    X, y = predictor.prepare_data(features_df)
                    predictions, probabilities = predictor.predict(X)
                    
                    # Son tahmin
                    last_prediction = predictions[-1]
                    last_confidence = np.max(probabilities[-1])
                    last_prob_up = probabilities[-1][1]
                    last_prob_down = probabilities[-1][0]
                    
                    # Sonuçları göster
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if last_prediction == 1:
                            st.markdown('<div class="signal-buy">🟢 AL SİNYALİ</div>', 
                                      unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="signal-sell">🔴 SAT SİNYALİ</div>', 
                                      unsafe_allow_html=True)
                    
                    with col2:
                        st.metric("Güven Skoru", f"{last_confidence:.2f}")
                    
                    with col3:
                        st.metric("Yükseliş Olasılığı", f"{last_prob_up:.2f}")
                    
                    # Tahmin geçmişi
                    st.subheader("Tahmin Geçmişi")
                    
                    prediction_df = pd.DataFrame({
                        'Tarih': features_df.index,
                        'Tahmin': ['AL' if p == 1 else 'SAT' for p in predictions],
                        'Güven': np.max(probabilities, axis=1),
                        'Yükseliş Olasılığı': probabilities[:, 1],
                        'Gerçek Yön': ['Yukarı' if r > 0 else 'Aşağı' for r in features_df['future_return']]
                    })
                    
                    st.dataframe(prediction_df.tail(10), use_container_width=True)
                    
                    # Performans metrikleri
                    if 'future_return' in features_df.columns:
                        actual_direction = (features_df['future_return'] > 0).astype(int)
                        accuracy = np.mean(predictions == actual_direction)
                        
                        st.subheader("Model Performansı")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Doğruluk", f"{accuracy:.2%}")
                        
                        with col2:
                            # Yüksek güven skorlu tahminlerin doğruluğu
                            high_conf_mask = np.max(probabilities, axis=1) > 0.7
                            if np.sum(high_conf_mask) > 0:
                                high_conf_accuracy = np.mean(
                                    predictions[high_conf_mask] == actual_direction[high_conf_mask]
                                )
                                st.metric("Yüksek Güven Doğruluğu", f"{high_conf_accuracy:.2%}")
                            else:
                                st.metric("Yüksek Güven Doğruluğu", "N/A")
                        
                        with col3:
                            st.metric("Toplam Tahmin", len(predictions))
                
                except Exception as e:
                    st.error(f"Tahmin hatası: {str(e)}")
    
    with tab4:
        st.header("📈 Backtest Sonuçları")
        
        if not model_files:
            st.warning("Backtest için model gerekli!")
            return
        
        # En son modeli otomatik seç
        model_files.sort(reverse=True)  # En yeni modeli başa al
        selected_model = st.selectbox("Backtest Modeli:", model_files, key="backtest_model_selection", index=0)
        
        if st.button("Backtest Çalıştır"):
            with st.spinner("Backtest çalıştırılıyor..."):
                try:
                    # Modeli yükle
                    predictor = StockDirectionPredictor(config)
                    model_path = f'src/models/{selected_model}'
                    
                    if not predictor.load_model(model_path):
                        st.error("Model yüklenemedi!")
                        return
                    
                    # Veri hazırla
                    data = load_stock_data(selected_symbol, period)
                    features_df = create_features(data)
                    
                    if features_df.empty:
                        st.error("Özellikler oluşturulamadı!")
                        return
                    
                    # Tahminler
                    X, y = predictor.prepare_data(features_df)
                    predictions, probabilities = predictor.predict(X)
                    
                    # Backtest
                    backtester = Backtester(config)
                    results = backtester.run_backtest(features_df, predictions, probabilities, selected_symbol)
                    
                    if results:
                        # Performans metrikleri
                        metrics = results['performance_metrics']
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Toplam Getiri",
                                f"{metrics['total_return']:.2%}",
                                f"{metrics['annualized_return']:.2%}"
                            )
                        
                        with col2:
                            st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.3f}")
                        
                        with col3:
                            st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")
                        
                        with col4:
                            st.metric("Kazanma Oranı", f"{metrics['win_rate']:.2%}")
                        
                        # Equity curve
                        st.subheader("Sermaye Eğrisi")
                        equity_df = results['equity_curve']
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=equity_df.index,
                            y=equity_df['equity'],
                            name="Sermaye",
                            line=dict(color='blue', width=2)
                        ))
                        
                        fig.update_layout(
                            title="Sermaye Eğrisi",
                            xaxis_title="Tarih",
                            yaxis_title="Sermaye (TL)",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # İşlem detayları
                        st.subheader("İşlem Detayları")
                        
                        trades_df = pd.DataFrame(results['trades'])
                        if not trades_df.empty:
                            trades_df['date'] = pd.to_datetime(trades_df['date'])
                            st.dataframe(trades_df, use_container_width=True)
                        
                        # Rapor
                        st.subheader("Detaylı Rapor")
                        report = backtester.generate_report()
                        st.text(report)
                
                except Exception as e:
                    st.error(f"Backtest hatası: {str(e)}")
    
    with tab5:
        st.header("💼 Paper Trading")
        
        # Paper trader durumu
        paper_trader = PaperTrader(config)
        summary = paper_trader.get_portfolio_summary()
        
        # Portföy özeti
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Mevcut Sermaye",
                f"{summary['current_capital']:,.0f} TL"
            )
        
        with col2:
            st.metric(
                "Toplam Değer",
                f"{summary['total_value']:,.0f} TL"
            )
        
        with col3:
            st.metric(
                "Toplam Getiri",
                f"{summary['total_return']:.2%}"
            )
        
        with col4:
            st.metric(
                "Aktif Pozisyonlar",
                summary['positions']
            )
        
        # Pozisyonlar
        if summary['position_values']:
            st.subheader("Aktif Pozisyonlar")
            
            for symbol, value in summary['position_values'].items():
                position = paper_trader.positions[symbol]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write(f"**{symbol}**")
                
                with col2:
                    st.write(f"Değer: {value:,.0f} TL")
                
                with col3:
                    st.write(f"Giriş: {position['entry_price']:.2f} TL")
                
                with col4:
                    st.write(f"Miktar: {position['quantity']:.0f}")
        
        # Son işlemler
        if summary['recent_trades']:
            st.subheader("Son İşlemler")
            
            trades_df = pd.DataFrame(summary['recent_trades'])
            st.dataframe(trades_df, use_container_width=True)
        
        # Manuel işlem
        st.subheader("Manuel İşlem")
        
        col1, col2 = st.columns(2)
        
        with col1:
            action = st.selectbox("İşlem Türü:", ["BUY", "SELL"], key="paper_trading_action_1")
        
        with col2:
            price = st.number_input("Fiyat (TL):", min_value=0.01, value=100.0)
        
        confidence = st.slider("Güven Skoru:", 0.0, 1.0, 0.7)
        
        if st.button("İşlem Yap"):
            prediction = 1 if action == "BUY" else 0
            
            result = paper_trader.process_signal(
                selected_symbol, price, prediction, confidence
            )
            
            if result['success']:
                st.success(f"✅ İşlem başarılı: {result['action_taken']} - {result['reason']}")
                st.rerun()  # Sayfayı yenile
            else:
                # Detaylı hata mesajı
                if result['action_taken'] is None:
                    if prediction == 1:
                        st.warning("⚠️ BUY sinyali işlenemedi. Güven skoru yeterli değil veya zaten pozisyon var.")
                    else:
                        st.warning("⚠️ SELL sinyali işlenemedi. Pozisyon yok veya güven skoru yeterli değil.")
                else:
                    st.error(f"❌ İşlem başarısız: {result.get('reason', 'Bilinmeyen hata')}")
        
        # Günlük rapor
        if st.button("Günlük Rapor Oluştur"):
            report = paper_trader.generate_daily_report()
            st.text(report)
    
    with tab6:
        st.header("🎯 Akıllı Model Eğitimi")
        
        # Hisse seçimi ve analiz
        stock_options = all_symbols  # Ana dropdown'daki tüm hisseleri kullan
        selected_stock = st.selectbox("📊 Eğitim için Hisse Seçin:", stock_options, key="training_stock_selection")
        
        # Hisse analizi
        if selected_stock:
            with st.spinner("Hisse analiz ediliyor..."):
                analysis = analyze_stock_characteristics(selected_stock)
                
                # Dinamik güven eşiği hesapla
                if analysis:
                    volatility = analysis['volatility']
                    if volatility > 0.6:
                        dynamic_threshold = 0.45
                        threshold_color = "error"
                    elif volatility > 0.4:
                        dynamic_threshold = 0.50
                        threshold_color = "warning"
                    elif volatility > 0.25:
                        dynamic_threshold = 0.55
                        threshold_color = "info"
                    else:
                        dynamic_threshold = 0.60
                        threshold_color = "success"
                    
                    st.info(f"🎯 Dinamik Güven Eşiği: **{dynamic_threshold:.2f}** (Volatilite: %{volatility*100:.1f})")
                
            if analysis:
                st.success("✅ Hisse analizi tamamlandı!")
                
                # Hisse karakteristikleri
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    volatility_pct = analysis['volatility'] * 100
                    if volatility_pct > 40:
                        st.error(f"🔥 Volatilite: %{volatility_pct:.1f} (Yüksek)")
                    elif volatility_pct > 25:
                        st.warning(f"⚠️ Volatilite: %{volatility_pct:.1f} (Orta)")
                    else:
                        st.success(f"✅ Volatilite: %{volatility_pct:.1f} (Düşük)")
                
                with col2:
                    volume_millions = analysis['avg_volume'] / 1_000_000
                    st.info(f"📊 Ortalama Hacim: {volume_millions:.1f}M")
                
                with col3:
                    range_pct = analysis['price_range'] * 100
                    st.info(f"📈 Fiyat Aralığı: %{range_pct:.1f}")
                
                with col4:
                    trend_pct = analysis['trend_strength'] * 100
                    st.info(f"📊 Trend Gücü: %{trend_pct:.1f}")
                
                # Akıllı parametre önerileri
                st.subheader("🧠 Akıllı Parametre Önerileri")
                
                recommendations = analysis['recommendations']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**🎯 Model Önerileri:**")
                    st.success(f"Model Karmaşıklığı: {recommendations['model_complexity']}")
                    st.success(f"Risk Seviyesi: {recommendations['risk_level']}")
                    
                    # Önerilen parametreler
                    st.write("**📋 Önerilen Değerler:**")
                    st.code(f"""
Max Depth: {recommendations['max_depth']}
Learning Rate: {recommendations['learning_rate']}
Stop Loss: %{recommendations['stop_loss']*100:.0f}
Take Profit: %{recommendations['take_profit']*100:.0f}
Günlük İşlem: {recommendations['max_daily_trades']}
Güven Eşiği: {recommendations['confidence_threshold']:.2f}
                    """)
                
                with col2:
                    st.write("**💡 Neden Bu Parametreler?**")
                    if analysis['volatility'] > 0.4:
                        st.info("🔥 Yüksek volatilite → Konservatif yaklaşım")
                        st.info("📉 Düşük risk toleransı")
                        st.info("🛡️ Güçlü stop-loss")
                    elif analysis['volatility'] > 0.25:
                        st.info("⚖️ Orta volatilite → Dengeli yaklaşım")
                        st.info("📊 Orta risk seviyesi")
                        st.info("🎯 Optimal parametreler")
                    else:
                        st.info("📈 Düşük volatilite → Agresif yaklaşım")
                        st.info("🚀 Yüksek risk toleransı")
                        st.info("💪 Büyük hedefler")
        
        # Akıllı parametre önerisi
        if analysis:
            volatility = analysis['volatility']
            
            # Volatiliteye göre otomatik parametre önerisi
            if volatility > 0.6:  # Yüksek volatilite
                st.warning(f"🔥 Yüksek Volatilite (%{volatility*100:.1f}) - Konservatif parametreler öneriliyor")
                auto_params = get_auto_params(volatility)
            elif volatility > 0.4:  # Orta-yüksek volatilite
                st.info(f"⚠️ Orta-Yüksek Volatilite (%{volatility*100:.1f}) - Dengeli parametreler")
                auto_params = get_auto_params(volatility)
            else:  # Düşük volatilite
                st.success(f"✅ Düşük Volatilite (%{volatility*100:.1f}) - Agresif parametreler")
                auto_params = get_auto_params(volatility)
            
            # Otomatik parametreleri göster
            st.subheader("🎯 Otomatik Parametre Önerisi")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Güven Eşiği", f"{auto_params['confidence']:.2f}")
                st.metric("Stop Loss", f"%{auto_params['stop_loss']*100:.0f}")
            
            with col2:
                st.metric("Take Profit", f"%{auto_params['take_profit']*100:.0f}")
                st.metric("Pozisyon Büyüklüğü", f"%{auto_params['position_size']*100:.0f}")
            
            with col3:
                st.metric("Max Depth", auto_params['max_depth'])
                st.metric("Günlük İşlem", auto_params['max_trades'])
        
        # Eğitim başlat
        if st.button("🚀 Model Eğitimini Başlat", type="primary"):
            with st.spinner("Model eğitiliyor..."):
                try:
                    # Otomatik parametreleri kullan
                    if analysis and 'auto_params' in locals():
                        # Volatilite analizi yapıldıysa otomatik parametreleri kullan
                        dynamic_confidence = auto_params['confidence']
                        dynamic_stop_loss = auto_params['stop_loss']
                        dynamic_take_profit = auto_params['take_profit']
                        dynamic_position_size = auto_params['position_size']
                        dynamic_max_trades = auto_params['max_trades']
                        dynamic_max_depth = auto_params['max_depth']
                        dynamic_learning_rate = auto_params['learning_rate']
                    else:
                        # Varsayılan parametreler
                        dynamic_confidence = 0.60
                        dynamic_stop_loss = 0.20
                        dynamic_take_profit = 0.30
                        dynamic_position_size = 0.20
                        dynamic_max_trades = 3
                        dynamic_max_depth = 4
                        dynamic_learning_rate = 0.05
                    
                    # Tam konfigürasyonu oluştur (gelecek tahmin odaklı)
                    full_config = {
                        'MODEL_CONFIG': {
                            'max_depth': auto_params['max_depth'],  # Dinamik
                            'learning_rate': auto_params['learning_rate'],  # Dinamik
                            'n_estimators': auto_params['n_estimators'],  # Dinamik
                            'subsample': auto_params['subsample'],  # Dinamik
                            'colsample_bytree': auto_params['colsample_bytree'],  # Dinamik
                            'min_child_weight': auto_params['min_child_weight'],  # Dinamik
                            'reg_alpha': auto_params['reg_alpha'],  # Dinamik
                            'reg_lambda': auto_params['reg_lambda'],  # Dinamik
                            'early_stopping_rounds': auto_params.get('early_stopping_rounds', 20),  # Overfitting önleme
                            'validation_fraction': auto_params.get('validation_fraction', 0.2),  # Daha fazla validation
                            'random_state': 42,
                            'n_jobs': -1
                        },
                        'RISK_MANAGEMENT': {
                            'max_position_size': auto_params['position_size'],  # Dinamik
                            'stop_loss_pct': auto_params['stop_loss'],  # Dinamik
                            'take_profit_pct': auto_params['take_profit'],  # Dinamik
                            'max_daily_trades': auto_params['max_trades'],  # Dinamik
                            'confidence_threshold': auto_params['confidence']  # Dinamik güven eşiği
                        },
                        'DATA_CONFIG': {
                            'train_test_split': 0.8,
                            'min_volume_threshold': 1000000
                        },
                        'BACKTEST_CONFIG': {
                            'start_date': "2020-01-01",
                            'end_date': "2024-01-01",
                            'initial_capital': 100000,
                            'commission_rate': 0.0000,
                            'slippage_rate': 0.0000
                        },
                        'TARGET_STOCKS': [selected_stock]
                    }
                    
                    # Model eğitimi
                    predictor = StockDirectionPredictor(full_config)
                    
                    # Veri yükle
                    data_loader = DataLoader(full_config)
                    data = data_loader.fetch_stock_data(selected_stock, "2y")
                    
                    if data.empty:
                        st.error("Veri yüklenemedi!")
                        return
                    
                    # Özellikler oluştur
                    feature_engineer = FeatureEngineer(full_config)
                    features_df = feature_engineer.create_all_features(data)
                    
                    if features_df.empty:
                        st.error("Özellikler oluşturulamadı!")
                        return
                    
                    # Veriyi hazırla
                    X, y = predictor.prepare_data(features_df)
                    
                    # Model eğitimi
                    results = predictor.train_model(X, y)
                    
                    # Modeli kaydet
                    model_path = predictor.save_model(f"{selected_stock.replace('.IS', '')}_Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib")
                    
                    st.success("✅ Model eğitimi tamamlandı!")
                    
                    # Sonuçları göster - Anlaşılır format
                    st.subheader("📊 Model Performansı")
                    
                    # Model güvenilirliği
                    test_accuracy = results['test_metrics']['accuracy']
                    test_f1 = results['test_metrics']['f1']
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if test_accuracy > 0.7:
                            st.success(f"🎯 Model Güvenilirliği: Yüksek (%{test_accuracy*100:.1f})")
                        elif test_accuracy > 0.6:
                            st.warning(f"⚠️ Model Güvenilirliği: Orta (%{test_accuracy*100:.1f})")
                        else:
                            st.error(f"❌ Model Güvenilirliği: Düşük (%{test_accuracy*100:.1f})")
                    
                    with col2:
                        if test_f1 > 0.7:
                            st.success(f"🎯 Kazanma Şansı: Yüksek (%{test_f1*100:.1f})")
                        elif test_f1 > 0.6:
                            st.warning(f"⚠️ Kazanma Şansı: Orta (%{test_f1*100:.1f})")
                        else:
                            st.error(f"❌ Kazanma Şansı: Düşük (%{test_f1*100:.1f})")
                    
                    with col3:
                        train_accuracy = results['train_metrics']['accuracy']
                        if train_accuracy - test_accuracy > 0.1:
                            st.warning("⚠️ Overfitting Riski")
                        else:
                            st.success("✅ Model Dengeli")
                    
                    with col4:
                        st.success("✅ Model Kaydedildi")
                    
                    # Model durumu özeti
                    if test_accuracy > 0.7 and test_f1 > 0.6:
                        st.success("🚀 Model durumu: Mükemmel! Hemen kullanabilirsin.")
                    elif test_accuracy > 0.6 and test_f1 > 0.5:
                        st.warning("⚠️ Model durumu: İyi ama daha iyi olabilir.")
                    else:
                        st.error("❌ Model durumu: Zayıf. Parametreleri ayarla.")
                    
                    # Feature importance - Debug ve düzeltme
                    st.subheader("🔍 En Önemli Özellikler")
                    
                    # Debug: results içeriğini kontrol et
                    st.write("Debug - Results keys:", list(results.keys()) if isinstance(results, dict) else "Results is not dict")
                    
                    if isinstance(results, dict) and 'feature_importance' in results:
                        importance_data = results['feature_importance']
                        st.write("Debug - Feature importance type:", type(importance_data))
                        st.write("Debug - Feature importance content:", importance_data)
                        
                        if importance_data is not None and not importance_data.empty:
                            importance_df = importance_data.head(10)
                            
                            fig = px.bar(
                                importance_df, 
                                x='importance', 
                                y='feature',
                                orientation='h',
                                title="Top 10 Feature Importance"
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("⚠️ Feature importance verisi boş!")
                    else:
                        st.warning("⚠️ Feature importance bulunamadı!")
                        
                        # Alternatif: Model'den direkt feature importance al
                        if hasattr(predictor.model, 'feature_importances_'):
                            st.info("🔄 Model'den direkt feature importance alınıyor...")
                            
                            # Feature isimlerini al
                            feature_names = X.columns.tolist()
                            importances = predictor.model.feature_importances_
                            
                            # DataFrame oluştur
                            importance_df = pd.DataFrame({
                                'feature': feature_names,
                                'importance': importances
                            }).sort_values('importance', ascending=False).head(10)
                            
                            st.write("Debug - Direct importance:", importance_df)
                            
                            fig = px.bar(
                                importance_df, 
                                x='importance', 
                                y='feature',
                                orientation='h',
                                title="Top 10 Feature Importance (Direct)"
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error("❌ Model'de feature importance bulunamadı!")
                    
                    # Model dosya yolu
                    st.info(f"📁 Model kaydedildi: `{model_path}`")
                    
                    # Dinamik parametreler bilgisi
                    st.subheader("🎯 Kullanılan Dinamik Parametreler")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Güven Eşiği", f"{dynamic_confidence:.2f}")
                        st.metric("Stop Loss", f"%{dynamic_stop_loss*100:.0f}")
                    
                    with col2:
                        st.metric("Take Profit", f"%{dynamic_take_profit*100:.0f}")
                        st.metric("Pozisyon Büyüklüğü", f"%{dynamic_position_size*100:.0f}")
                    
                    with col3:
                        st.metric("Max Depth", dynamic_max_depth)
                        st.metric("Günlük İşlem", dynamic_max_trades)
                    
                    # Otomatik backtest çalıştır
                    st.subheader("📈 Otomatik Backtest")
                    st.info("Model eğitimi tamamlandı! Dinamik parametrelerle backtest çalıştırılıyor...")
                    
                    with st.spinner("Backtest çalıştırılıyor..."):
                        try:
                            backtester = Backtester(full_config)
                            backtest_results = backtester.run_backtest(features_df, 
                                                                     results['predictions'], 
                                                                     results['probabilities'], 
                                                                     selected_stock)
                            
                            st.success("✅ Backtest tamamlandı!")
                            
                            # Sonuçları göster
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Toplam Getiri", f"%{backtest_results['total_return']:.1f}")
                            with col2:
                                st.metric("Kazanma Oranı", f"%{backtest_results['win_rate']:.1f}")
                            with col3:
                                st.metric("Sharpe Ratio", f"{backtest_results['sharpe_ratio']:.2f}")
                            
                            # İşlem sayısı
                            trades_count = len(backtest_results.get('trades', []))
                            st.info(f"📊 Toplam İşlem Sayısı: {trades_count}")
                            
                            if trades_count > 0:
                                st.success("🎉 Model çalışıyor! İşlemler yapıldı.")
                            else:
                                st.warning("⚠️ Henüz işlem yapılmadı. Parametreler ayarlanabilir.")
                        
                        except Exception as e:
                            st.error(f"Backtest hatası: {str(e)}")
                
                except Exception as e:
                    st.error(f"Model eğitimi hatası: {str(e)}")

if __name__ == "__main__":
    main()
