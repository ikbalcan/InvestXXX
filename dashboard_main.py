"""
Hisse Senedi Yön Tahmini Sistemi - Ana Dashboard
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

# Tab modüllerini import et
from dashboard_data_analysis import show_data_analysis_tab
from dashboard_future_prediction import show_future_prediction_tab
from dashboard_model_training import show_model_training_tab

# Yardımcı modülleri import et
from dashboard_utils import load_config, load_stock_data, analyze_stock_characteristics, get_auto_params
from dashboard_charts import plot_price_chart, plot_volume_chart, plot_technical_indicators

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
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-bottom: 30px;">
        <h1 style="margin: 0; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">📈 Hisse Senedi Yön Tahmini Sistemi</h1>
        <p style="margin: 10px 0 0 0; font-size: 1.2em; opacity: 0.9;">AI Destekli Akıllı Yatırım Kararları</p>
    </div>
    """, unsafe_allow_html=True)
    
    # CSS stilleri - Tam genişlik
    st.markdown("""
    <style>
        /* Ana container'ı tam genişlik yap */
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        
        /* Sidebar genişliğini ayarla */
        .css-1d391kg {
            width: 250px;
        }
        
        /* Tab stillerini güzelleştir */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding-left: 20px;
            padding-right: 20px;
            background-color: #f8f9fa;
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
    
    # Sidebar
    st.sidebar.title("⚙️ Kontrol Paneli")
    
    # Konfigürasyon yükle
    config = load_config()
    symbols = config.get('TARGET_STOCKS', ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS'])
    
    # Popüler BIST hisseleri listesi
    all_symbols = [
        'THYAO.IS', 'AKBNK.IS', 'BIMAS.IS', 'GARAN.IS', 'ISCTR.IS', 'KRDMD.IS',
        'SAHOL.IS', 'TUPRS.IS', 'VAKBN.IS', 'YAPRK.IS', 'ARCLK.IS', 'ASELS.IS',
        'BRSAN.IS', 'CCOLA.IS', 'DOHOL.IS', 'EKGYO.IS', 'ENKAI.IS', 'EREGL.IS',
        'FROTO.IS', 'HALKB.IS', 'KCHOL.IS', 'KOZAL.IS', 'MGROS.IS', 'OTKAR.IS',
        'PETKM.IS', 'PGSUS.IS', 'SISE.IS', 'TCELL.IS', 'TKFEN.IS', 'TOASO.IS',
        'TTKOM.IS', 'ULKER.IS', 'VESTL.IS', 'YKBNK.IS', 'ZOREN.IS', 'AZTEK.IS',
        'FONET.IS', 'ERSU.IS', 'KONYA.IS', 'MARTI.IS', 'NETAS.IS', 'PAMEL.IS',
        'SELEC.IS', 'SMRTG.IS', 'SNPAM.IS', 'TATGD.IS', 'TURSG.IS', 'UNYEC.IS'
    ]
    
    # Hisse seçimi
    selected_symbol = st.sidebar.selectbox("📊 Hisse Seçin", all_symbols)
    
    # Veri periyodu seçimi
    period = st.sidebar.selectbox("📅 Veri Periyodu", ["1y", "2y", "5y"], index=1)
    
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
        show_data_analysis_tab(selected_symbol, period)
    
    with tab2:
        show_future_prediction_tab(selected_symbol, config)
    
    with tab3:
        st.header("🤖 Model Tahminleri")
        st.info("Bu sekme gelecekte geliştirilecek.")
    
    with tab4:
        st.header("📈 Backtest")
        st.info("Bu sekme gelecekte geliştirilecek.")
    
    with tab5:
        st.header("💼 Paper Trading")
        st.info("Bu sekme gelecekte geliştirilecek.")
    
    with tab6:
        show_model_training_tab(all_symbols)

if __name__ == "__main__":
    main()
