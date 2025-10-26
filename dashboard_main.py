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
from datetime import datetime

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

# Tab modüllerini import et
from dashboard_data_analysis import show_data_analysis_tab
from dashboard_future_prediction import show_future_prediction_tab
from dashboard_model_training import show_model_training_tab
from dashboard_stock_hunter import show_stock_hunter_tab

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
    
    # CSS stilleri - UI/UX İyileştirmeleri
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
        
        /* Tab stillerini güzelleştir - Renk paleti standardizasyonu */
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
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #28a745; /* Yeşil - Pozitif */
            color: white;
            border-color: #28a745;
            box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
        }
        
        .stTabs [aria-selected="false"] {
            background-color: #f8f9fa;
            color: #495057;
        }
        
        .stTabs [aria-selected="false"]:hover {
            background-color: #e9ecef;
            border-color: #28a745;
            transform: translateY(-2px);
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
        
        /* Bilgi katmanlama için kartlar */
        .info-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 20px;
            margin: 10px 0;
            border-left: 5px solid #28a745;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        /* HTML içerik desteği */
        .info-card p {
            margin: 10px 0;
            line-height: 1.6;
        }
        
        .info-card strong {
            font-weight: 700;
            color: #495057;
        }
        
        .info-card h3 {
            margin: 0 0 15px 0;
            color: #495057;
        }
        
        .info-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .summary-card {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border-left-color: #28a745;
        }
        
        .warning-card {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border-left-color: #ffc107;
        }
        
        .danger-card {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left-color: #dc3545;
        }
        
        .info-card {
            background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
            border-left-color: #17a2b8;
        }
        
        /* Typography hiyerarşisi */
        .main-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #28a745;
            text-align: center;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 1.8rem;
            font-weight: 600;
            color: #495057;
            margin: 1.5rem 0 1rem 0;
            border-bottom: 3px solid #28a745;
            padding-bottom: 0.5rem;
        }
        
        .subsection-title {
            font-size: 1.3rem;
            font-weight: 500;
            color: #6c757d;
            margin: 1rem 0 0.5rem 0;
        }
        
        .metric-large {
            font-size: 2rem;
            font-weight: 700;
            color: #28a745;
        }
        
        .metric-medium {
            font-size: 1.5rem;
            font-weight: 600;
            color: #495057;
        }
        
        .metric-small {
            font-size: 1rem;
            font-weight: 500;
            color: #6c757d;
        }
        
        /* Güven skoru gauge */
        .confidence-gauge {
            background: conic-gradient(from 0deg, #dc3545 0deg, #ffc107 120deg, #28a745 240deg, #28a745 360deg);
            border-radius: 50%;
            width: 120px;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            position: relative;
        }
        
        .confidence-gauge::before {
            content: '';
            width: 80px;
            height: 80px;
            background: white;
            border-radius: 50%;
            position: absolute;
        }
        
        .confidence-text {
            font-size: 1.2rem;
            font-weight: 700;
            color: #495057;
            z-index: 1;
        }
        
        /* Responsive tasarım - Mobil uyumluluk */
        @media (max-width: 768px) {
            .main-title {
                font-size: 2rem;
            }
            
            .section-title {
                font-size: 1.5rem;
            }
            
            .metric-large {
                font-size: 1.5rem;
            }
            
            .confidence-gauge {
                width: 100px;
                height: 100px;
            }
            
            .confidence-gauge::before {
                width: 70px;
                height: 70px;
            }
            
            /* Mobilde kartları tek sütun yap */
            .info-card {
                margin: 5px 0;
                padding: 15px;
            }
            
            /* Mobilde tab'ları küçült */
            .stTabs [data-baseweb="tab"] {
                height: 40px;
                padding-left: 10px;
                padding-right: 10px;
                font-size: 12px;
            }
            
            /* Mobilde sidebar'ı daralt */
            .css-1d391kg {
                width: 200px;
            }
            
            /* Mobilde ana içeriği genişlet */
            .css-1v0mbdj {
                width: calc(100% - 200px);
            }
        }
        
        /* Tablet uyumluluk */
        @media (max-width: 1024px) and (min-width: 769px) {
            .main-title {
                font-size: 2.2rem;
            }
            
            .section-title {
                font-size: 1.6rem;
            }
            
            .metric-large {
                font-size: 1.8rem;
            }
            
            .confidence-gauge {
                width: 110px;
                height: 110px;
            }
            
            .confidence-gauge::before {
                width: 75px;
                height: 75px;
            }
        }
        
        /* Büyük ekranlar için optimizasyon */
        @media (min-width: 1200px) {
            .main .block-container {
                padding-left: 2rem;
                padding-right: 2rem;
            }
            
            .info-card {
                padding: 25px;
            }
            
            .main-title {
                font-size: 3rem;
            }
        }
        
        /* Animasyonlar */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .fade-in-up {
            animation: fadeInUp 0.6s ease-out;
        }
        
        /* Buton iyileştirmeleri */
        .stButton > button {
            border-radius: 25px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        /* Scroll davranışı - Tahmin sonuçlarına yumuşak scroll */
        html {
            scroll-behavior: smooth;
        }
        
        /* Tahmin sonuçları anchor'ı için scroll offset */
        #tahmin-sonuclari {
            scroll-margin-top: 20px;
        }
    </style>
    
    <script>
        // Tahmin butonu tıklandığında scroll davranışını kontrol et
        window.addEventListener('load', function() {
            // Streamlit'in otomatik scroll'unu engelle
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        // Tahmin sonuçları eklendiğinde scroll'u kontrol et
                        const tahminSonuclari = document.getElementById('tahmin-sonuclari');
                        if (tahminSonuclari) {
                            // Akıllı Analiz kısmına scroll yap
                            setTimeout(function() {
                                tahminSonuclari.scrollIntoView({ 
                                    behavior: 'smooth', 
                                    block: 'start' 
                                });
                            }, 500);
                        }
                    }
                });
            });
            
            // Ana container'ı gözlemle
            const mainContainer = document.querySelector('.main .block-container');
            if (mainContainer) {
                observer.observe(mainContainer, { childList: true, subtree: true });
            }
        });
    </script>
    """, unsafe_allow_html=True)
    
    # Sidebar - Mobil uyumlu
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 10px;">
        <h2 style="color: #28a745; margin: 0;">⚙️ Kontrol Paneli</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Konfigürasyon yükle
    config = load_config()
    symbols = config.get('TARGET_STOCKS', ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS'])
    
    # Genişletilmiş BIST hisseleri listesi - Kategorilere ayrılmış
    bist_stocks = {
        '🏦 Bankacılık': [
            'AKBNK.IS', 'GARAN.IS', 'ISCTR.IS', 'HALKB.IS', 'VAKBN.IS', 'YKBNK.IS',
            'ALBRK.IS', 'DENIZ.IS', 'QNBFB.IS', 'TSKB.IS', 'VAKFN.IS'
        ],
        '🏭 Sanayi': [
            'THYAO.IS', 'TUPRS.IS', 'EREGL.IS', 'KRDMD.IS', 'PETKM.IS', 'SAHOL.IS',
            'BIMAS.IS', 'ASELS.IS', 'FROTO.IS', 'KCHOL.IS', 'OTKAR.IS', 'TKFEN.IS',
            'TOASO.IS', 'ULKER.IS', 'VESTL.IS', 'ZOREN.IS', 'ARCLK.IS', 'BRSAN.IS',
            'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KOZAL.IS', 'MGROS.IS', 'PGSUS.IS',
            'SISE.IS', 'TCELL.IS', 'TTKOM.IS', 'AZTEK.IS', 'FONET.IS', 'ERSU.IS',
            'KONYA.IS', 'MARTI.IS', 'NETAS.IS', 'PAMEL.IS', 'SELEC.IS', 'SMRTG.IS',
            'SNPAM.IS', 'TATGD.IS', 'TURSG.IS', 'UNYEC.IS'
        ],
        '🏢 Gayrimenkul': [
            'EKGYO.IS', 'YAPRK.IS', 'ALGYO.IS', 'AVGYO.IS', 'BAGFS.IS', 'BRKO.IS',
            'BRKV.IS', 'DAGI.IS', 'DZGYO.IS', 'EGEPO.IS', 'EMKEL.IS', 'EMNIS.IS',
            'ERSU.IS', 'FMIZP.IS', 'GSDHO.IS', 'GUBRF.IS', 'HLGYO.IS', 'ISGYO.IS',
            'KGYO.IS', 'KLKIM.IS', 'KORDS.IS', 'KRSTL.IS', 'LOGO.IS', 'MEGAP.IS',
            'MRSHL.IS', 'MRDIN.IS', 'NUGYO.IS', 'OZGYO.IS', 'PAMEL.IS', 'PGSUS.IS',
            'RYGYO.IS', 'SELEC.IS', 'SNPAM.IS', 'SOKM.IS', 'TATGD.IS', 'TURSG.IS',
            'UNYEC.IS', 'VKGYO.IS', 'YAPRK.IS'
        ],
        '⚡ Enerji': [
            'PETKM.IS', 'TUPRS.IS', 'AKSEN.IS', 'BUCIM.IS', 'CLEBI.IS', 'DOKM.IS',
            'ECILC.IS', 'EGECM.IS', 'EGEPO.IS', 'EMKEL.IS', 'EMNIS.IS', 'ERSU.IS',
            'FMIZP.IS', 'GUBRF.IS', 'HLGYO.IS', 'ISGYO.IS', 'KGYO.IS', 'KLKIM.IS',
            'KORDS.IS', 'KRSTL.IS', 'LOGO.IS', 'MEGAP.IS', 'MRSHL.IS', 'MRDIN.IS',
            'NUGYO.IS', 'OZGYO.IS', 'PAMEL.IS', 'PGSUS.IS', 'RYGYO.IS', 'SELEC.IS',
            'SNPAM.IS', 'SOKM.IS', 'TATGD.IS', 'TURSG.IS', 'UNYEC.IS', 'VKGYO.IS'
        ],
        '🛒 Perakende': [
            'MGROS.IS', 'BIMAS.IS', 'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KCHOL.IS',
            'KOZAL.IS', 'OTKAR.IS', 'PGSUS.IS', 'SISE.IS', 'TCELL.IS', 'TOASO.IS',
            'ULKER.IS', 'VESTL.IS', 'ZOREN.IS', 'ARCLK.IS', 'BRSAN.IS', 'FROTO.IS',
            'MARTI.IS', 'NETAS.IS', 'SELEC.IS', 'SMRTG.IS', 'SNPAM.IS', 'TATGD.IS',
            'TURSG.IS', 'UNYEC.IS'
        ],
        '🚗 Otomotiv': [
            'FROTO.IS', 'OTKAR.IS', 'TKFEN.IS', 'TOASO.IS', 'VESTL.IS', 'ZOREN.IS',
            'ARCLK.IS', 'BRSAN.IS', 'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KCHOL.IS',
            'KOZAL.IS', 'MARTI.IS', 'NETAS.IS', 'SELEC.IS', 'SMRTG.IS', 'SNPAM.IS',
            'TATGD.IS', 'TURSG.IS', 'UNYEC.IS'
        ],
        '💊 Sağlık': [
            'SELEC.IS', 'SMRTG.IS', 'SNPAM.IS', 'TATGD.IS', 'TURSG.IS', 'UNYEC.IS',
            'ARCLK.IS', 'BRSAN.IS', 'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KCHOL.IS',
            'KOZAL.IS', 'MARTI.IS', 'NETAS.IS', 'PAMEL.IS', 'PGSUS.IS', 'SISE.IS',
            'TCELL.IS', 'TOASO.IS', 'ULKER.IS', 'VESTL.IS', 'ZOREN.IS'
        ],
        '📱 Teknoloji': [
            'ASELS.IS', 'FONET.IS', 'NETAS.IS', 'SELEC.IS', 'SMRTG.IS', 'SNPAM.IS',
            'TATGD.IS', 'TCELL.IS', 'TURSG.IS', 'TTKOM.IS', 'UNYEC.IS', 'AZTEK.IS',
            'ERSU.IS', 'KONYA.IS', 'MARTI.IS', 'PAMEL.IS', 'PGSUS.IS', 'SISE.IS',
            'TOASO.IS', 'ULKER.IS', 'VESTL.IS', 'ZOREN.IS'
        ],
        '🏗️ İnşaat': [
            'YAPRK.IS', 'EKGYO.IS', 'ALGYO.IS', 'AVGYO.IS', 'BAGFS.IS', 'BRKO.IS',
            'BRKV.IS', 'DAGI.IS', 'DZGYO.IS', 'EGEPO.IS', 'EMKEL.IS', 'EMNIS.IS',
            'ERSU.IS', 'FMIZP.IS', 'GSDHO.IS', 'GUBRF.IS', 'HLGYO.IS', 'ISGYO.IS',
            'KGYO.IS', 'KLKIM.IS', 'KORDS.IS', 'KRSTL.IS', 'LOGO.IS', 'MEGAP.IS',
            'MRSHL.IS', 'MRDIN.IS', 'NUGYO.IS', 'OZGYO.IS', 'PAMEL.IS', 'PGSUS.IS',
            'RYGYO.IS', 'SELEC.IS', 'SNPAM.IS', 'SOKM.IS', 'TATGD.IS', 'TURSG.IS',
            'UNYEC.IS', 'VKGYO.IS'
        ],
        '🍽️ Gıda': [
            'ULKER.IS', 'BIMAS.IS', 'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KCHOL.IS',
            'KOZAL.IS', 'MGROS.IS', 'OTKAR.IS', 'PGSUS.IS', 'SISE.IS', 'TCELL.IS',
            'TOASO.IS', 'VESTL.IS', 'ZOREN.IS', 'ARCLK.IS', 'BRSAN.IS', 'FROTO.IS',
            'MARTI.IS', 'NETAS.IS', 'SELEC.IS', 'SMRTG.IS', 'SNPAM.IS', 'TATGD.IS',
            'TURSG.IS', 'UNYEC.IS'
        ]
    }
    
    # Tüm hisseleri tek listede topla
    all_symbols = []
    for category, stocks in bist_stocks.items():
        all_symbols.extend(stocks)
    
    # Tekrarları kaldır ve sırala
    all_symbols = sorted(list(set(all_symbols)))
    
    # Session state'te seçili hisseyi sakla ve başlat
    if 'current_selected_symbol' not in st.session_state:
        st.session_state.current_selected_symbol = all_symbols[0] if all_symbols else None
    
    # Hisse seçimi - İyileştirilmiş arama
    st.sidebar.markdown("### 📊 Hisse Seçimi")
    
    # Arama terimi için metin girişi
    search_term = st.sidebar.text_input(
        "🔍 Hisse Ara:",
        value="",
        placeholder="örn: THYAO, MEGMT, AKBNK...",
        help="Hisse kodunu yazın (örn: MEGMT) veya aşağıdan seçin"
    )
    
    # Arama sonuçlarını filtrele
    if search_term:
        # Arama terimini temizle ve büyük harfe çevir
        search_clean = search_term.upper().strip()
        
        # Sonuçları filtrele
        filtered_symbols = [s for s in all_symbols if search_clean in s]
        
        # Eğer hiçbir sonuç bulunamazsa, kullanıcının girdiği değeri direkt kullan
        if not filtered_symbols:
            # Girdiğiniz değeri otomatik olarak .IS ile tamamla
            if not search_clean.endswith('.IS'):
                search_clean = search_clean + '.IS'
            
            # Yeni hisseyi listeye ekle
            if search_clean not in all_symbols:
                filtered_symbols = [search_clean]
                all_symbols.insert(0, search_clean)
                st.sidebar.success(f"✅ {search_clean} eklendi!")
        
        # Bulunan sonuçları kullan
        if filtered_symbols:
            # Seçili hisseyi listede bul
            current_index = 0
            if st.session_state.current_selected_symbol in filtered_symbols:
                current_index = filtered_symbols.index(st.session_state.current_selected_symbol)
            
            selected_symbol = st.sidebar.selectbox(
                "📋 Bulunan Hisseler:",
                filtered_symbols,
                index=current_index,
                help="Aradığınız hisseyi seçin"
            )
        else:
            # Eğer hiç sonuç yoksa varsayılan hisse
            selected_symbol = all_symbols[0]
    else:
        # Arama yapılmadıysa normal dropdown göster
        # Seçili hisseyi listede bul
        current_index = 0
        if st.session_state.current_selected_symbol in all_symbols:
            current_index = all_symbols.index(st.session_state.current_selected_symbol)
        
        selected_symbol = st.sidebar.selectbox(
            "📋 Tüm BIST Hisseleri:",
            all_symbols,
            index=current_index,
            help="Bir hisse seçin veya yukarıdaki arama kutusuna yazarak arayın"
        )
    
    # Session state'i güncelle
    st.session_state.current_selected_symbol = selected_symbol
    
    # Seçilen hisseyi session state'e kaydet
    if 'recent_searches' not in st.session_state:
        st.session_state.recent_searches = []
    
    if 'last_selected_symbol' not in st.session_state:
        st.session_state.last_selected_symbol = selected_symbol
    
    # Eğer yeni bir hisse seçildiyse, son aramalara ekle
    if selected_symbol != st.session_state.last_selected_symbol:
        if selected_symbol and selected_symbol not in st.session_state.recent_searches:
            st.session_state.recent_searches.insert(0, selected_symbol)
            # En fazla 6 hisse tut
            if len(st.session_state.recent_searches) > 6:
                st.session_state.recent_searches = st.session_state.recent_searches[:6]
        st.session_state.last_selected_symbol = selected_symbol
    
    # Seçilen hisse bilgisi - Daha temiz görünüm
    st.sidebar.markdown(f"""
    <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                padding: 10px; 
                border-radius: 8px; 
                color: white; 
                text-align: center; 
                margin: 10px 0;">
        <strong>🎯 Seçilen Hisse:</strong><br>
        <span style="font-size: 1.2em;">{selected_symbol}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Son aramalar veya Popüler hisseler
    st.sidebar.markdown("### 🚀 Hızlı Erişim")
    
    # Eğer son aramalar varsa onları göster, yoksa popüler hisseleri göster
    if st.session_state.recent_searches:
        display_stocks = st.session_state.recent_searches[:6]
        section_title = "🔄 Son Aramalar"
    else:
        display_stocks = ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS', 'GARAN.IS', 'ASELS.IS']
        section_title = "⚡ Popüler Hisseler"
    
    # Butonları göster
    cols = st.sidebar.columns(2)
    for i, stock in enumerate(display_stocks):
        with cols[i % 2]:
            if st.button(f"{stock.replace('.IS', '')}", key=f"quick_{stock}_{i}", use_container_width=True):
                # Son aramalar sırasını güncelle
                if stock in st.session_state.recent_searches:
                    st.session_state.recent_searches.remove(stock)
                st.session_state.recent_searches.insert(0, stock)
                if len(st.session_state.recent_searches) > 6:
                    st.session_state.recent_searches = st.session_state.recent_searches[:6]
                
                # Session state'i güncelle
                st.session_state.current_selected_symbol = stock
                st.session_state.last_selected_symbol = stock
                st.rerun()
    
    # Veri periyodu seçimi - Mobil uyumlu
    st.sidebar.markdown("### 📅 Veri Periyodu")
    period = st.sidebar.selectbox(
        "Periyot:", 
        ["1y", "2y", "5y"], 
        index=1,
        help="Analiz için veri periyodunu seçin"
    )
    
    # Zaman dilimi seçimi - Mobil uyumlu
    st.sidebar.markdown("### ⏰ Zaman Dilimi")
    interval = st.sidebar.selectbox(
        "Zaman Dilimi:", 
        ["1d", "1h", "4h", "1wk"], 
        index=0,
        help="Teknik analiz için zaman dilimini seçin"
    )
    
    # Tab sırasını kontrol et ve düzelt - 5 Ana Kategori
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Veri Analizi", 
        "🔮 Tahmin Karar", 
        "🎯 Hisse Avcısı",
        "💼 Paper Trading",
        "🤖 Model Eğitimi"
    ])
    
    with tab1:
        # 📊 Veri Analizi - Sadece hisse analizi ve veri
        show_data_analysis_tab(selected_symbol, period, interval)
    
    with tab2:
        # 🔮 Tahmin Karar - Doğrudan gelecek tahmin içeriği
        show_future_prediction_tab(selected_symbol, config, interval=interval)
    
    with tab3:
        # 🎯 Hisse Avcısı - Toplu analiz ve karşılaştırma
        show_stock_hunter_tab(bist_stocks, all_symbols, config)
    
    with tab4:
        # 💼 Paper Trading & Portföy Yönetimi
        st.markdown('<h2 class="section-title">💼 Portföy Yönetimi & Paper Trading</h2>', unsafe_allow_html=True)
        
        # Paper Trading açıklaması
        st.info("📚 **Paper Trading Nedir?**")
        st.write("**Paper Trading**, gerçek para kullanmadan sanal bir portföy ile hisse senedi işlemleri yapmanızı sağlayan bir simülasyon sistemidir.")
        
        st.subheader("🎯 Nasıl Çalışır?")
        st.write("""
        - **📝 Manuel Ekleme:** Mevcut hisselerinizi sisteme ekleyerek portföyünüzü oluşturun
        - **🤖 AI Destekli İşlem:** Makine öğrenmesi modeli ile gelecek tahminleri yapın
        - **📊 Performans Takibi:** Kar/zarar analizi ve risk metrikleri ile performansınızı izleyin
        - **💰 Sanal Sermaye:** Gerçek para riski olmadan stratejilerinizi test edin
        """)
        
        st.subheader("✅ Faydaları:")
        st.write("""
        - Gerçek para kaybetme riski olmadan deneyim kazanın
        - AI tahminlerinin doğruluğunu test edin
        - Farklı stratejileri deneyin
        - Risk yönetimi becerilerinizi geliştirin
        """)
        
        # Paper trader durumu
        try:
            from live_trade import PaperTrader
            
            # Session state ile paper trader'ı sakla
            if 'paper_trader' not in st.session_state:
                st.session_state.paper_trader = PaperTrader(config)
            
            paper_trader = st.session_state.paper_trader
            
            # Her seferinde localStorage'dan güncel veriyi yükle
            paper_trader.initial_capital = paper_trader.load_initial_capital()
            paper_trader.current_capital = paper_trader.load_current_capital()
            paper_trader.positions = paper_trader.load_positions()
            paper_trader.trade_history = paper_trader.load_trade_history()
            
            summary = paper_trader.get_portfolio_summary()
            
            # Portföy özeti - Streamlit metrikleri
            st.subheader("📊 Portföy Özeti")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Mevcut Sermaye", f"{summary['current_capital']:,.0f} TL")
            
            with col2:
                st.metric("Toplam Değer", f"{summary['total_value']:,.0f} TL")
            
            with col3:
                delta_color = "normal" if summary['total_return'] > 0 else "inverse"
                st.metric("Toplam Getiri", f"{summary['total_return']:+.2%}", delta=f"{summary['total_return']:+.2%}")
            
            with col4:
                st.metric("Aktif Pozisyonlar", f"{summary['positions']}")
            
            # İstatistikler
            st.subheader("📈 İstatistikler")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_trades = summary.get('total_trades', 0)
                st.metric("Toplam İşlem", str(total_trades))
            
            with col2:
                today_trades = summary.get('today_trades', 0)
                st.metric("Bugünkü İşlem", str(today_trades))
            
            with col3:
                win_rate = summary.get('win_rate', 0.0)
                st.metric("Kazanma Oranı", f"{win_rate:.1%}")
            
            with col4:
                profitable = summary.get('profitable_trades', 0)
                losing = summary.get('losing_trades', 0)
                st.metric("Kazanç/Kayıp", f"{profitable}/{losing}")
            
            # Portföy yönetimi bölümleri
            st.markdown('<h3 class="subsection-title">🎛️ Portföy Yönetimi</h3>', unsafe_allow_html=True)
            
            # Alt sekmeler
            portfolio_tab1, portfolio_tab2, portfolio_tab3 = st.tabs([
                "📝 Hisse Ekleme", 
                "📊 Mevcut Pozisyonlar", 
                "⚙️ Ayarlar"
            ])
            
            with portfolio_tab1:
                st.markdown('<h4 class="subsection-title">📝 Yeni Hisse Ekleme</h4>', unsafe_allow_html=True)
                
                # Hisse ekleme formu
                with st.form("add_stock_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        stock_symbol = st.selectbox(
                            "Hisse Senedi:", 
                            all_symbols,
                            help="Eklemek istediğiniz hisse senedini seçin"
                        )
                        
                        entry_price = st.number_input(
                            "Giriş Fiyatı (TL):", 
                            min_value=0.01, 
                            value=100.0,
                            help="Hisseyi hangi fiyattan aldığınızı girin"
                        )
                    
                    with col2:
                        quantity = st.number_input(
                            "Miktar (Lot):", 
                            min_value=1, 
                            value=100,
                            help="Kaç lot aldığınızı girin"
                        )
                        
                        entry_date = st.date_input(
                            "Alım Tarihi:",
                            value=datetime.now().date(),
                            help="Hisseyi hangi tarihte aldığınızı seçin"
                        )
                    
                    # Form gönderimi
                    submitted = st.form_submit_button("💼 Hisse Ekle", type="primary")
                    
                    if submitted:
                        # Manuel pozisyon ekleme
                        total_value = quantity * entry_price
                        
                        if total_value <= summary['current_capital']:
                            # Pozisyonu ekle
                            paper_trader.positions[stock_symbol] = {
                                'quantity': quantity,
                                'entry_price': entry_price,
                                'entry_date': datetime.combine(entry_date, datetime.min.time()),
                                'confidence': 0.8  # Manuel ekleme için varsayılan güven
                            }
                            
                            # Sermayeyi güncelle
                            paper_trader.current_capital -= total_value
                            
                            # İşlemi kaydet
                            trade = {
                                'date': datetime.now(),
                                'symbol': stock_symbol,
                                'action': 'BUY',
                                'price': entry_price,
                                'quantity': quantity,
                                'position_size': total_value,
                                'confidence': 0.8,
                                'capital_after': paper_trader.current_capital,
                                'manual_entry': True
                            }
                            
                            paper_trader.trade_history.append(trade)
                            paper_trader.save_to_localStorage()
                            
                            # Session state'i güncelle
                            st.session_state.paper_trader = paper_trader
                            
                            st.success(f"✅ {stock_symbol} hissesi başarıyla eklendi!")
                            st.success(f"💰 Toplam değer: {total_value:,.0f} TL")
                            st.success("🔄 Sayfa yenileniyor...")
                            
                            # Sayfa yenileme yerine veriyi güncelle
                            st.rerun()
                        else:
                            st.error(f"❌ Yetersiz sermaye! Mevcut: {summary['current_capital']:,.0f} TL, Gerekli: {total_value:,.0f} TL")
            
            with portfolio_tab2:
                st.markdown('<h4 class="subsection-title">📊 Mevcut Pozisyonlar</h4>', unsafe_allow_html=True)
                
                if summary['positions'] > 0:
                    for symbol, details in summary['position_details'].items():
                        # Pozisyon bilgilerini Streamlit ile göster
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.subheader(f"📊 {symbol}")
                            st.write(f"**Miktar:** {details['quantity']:.0f} lot")
                            st.write(f"**Giriş Fiyatı:** {details['entry_price']:.2f} TL")
                            st.write(f"**Güncel Fiyat:** {details['current_price']:.2f} TL")
                        
                        with col2:
                            st.metric("Güncel Değer", f"{details['current_value']:,.0f} TL")
                            st.metric("Tutma Süresi", f"{details['days_held']} gün")
                        
                        with col3:
                            # Getiri gösterimi
                            if details['unrealized_return'] > 0:
                                st.metric("Getiri", f"{details['unrealized_return']:+.2%}", delta="📈")
                            else:
                                st.metric("Getiri", f"{details['unrealized_return']:+.2%}", delta="📉")
                        
                        st.divider()
                        
                        # Pozisyon işlemleri
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button(f"📈 {symbol} Sat", key=f"sell_{symbol}"):
                                st.session_state[f"show_sell_{symbol}"] = True
                        
                        with col2:
                            if st.button(f"📊 {symbol} Detay", key=f"detail_{symbol}"):
                                st.session_state[f"show_detail_{symbol}"] = True
                        
                        with col3:
                            if st.button(f"❌ {symbol} Sil", key=f"delete_{symbol}"):
                                st.session_state[f"show_delete_{symbol}"] = True
                        
                        # Satış formu
                        if st.session_state.get(f"show_sell_{symbol}", False):
                            st.write("---")
                            st.subheader(f"📈 {symbol} Satış İşlemi")
                            sell_price = st.number_input(
                                f"{symbol} Satış Fiyatı:", 
                                min_value=0.01, 
                                value=details['current_price'],
                                key=f"sell_price_{symbol}"
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"✅ Satışı Onayla", key=f"confirm_sell_{symbol}"):
                                    success = paper_trader.close_position(symbol, sell_price, "Manuel Satış")
                                    if success:
                                        st.success(f"✅ {symbol} satışı tamamlandı!")
                                        st.session_state[f"show_sell_{symbol}"] = False
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Satış işlemi başarısız!")
                            
                            with col2:
                                if st.button("❌ İptal", key=f"cancel_sell_{symbol}"):
                                    st.session_state[f"show_sell_{symbol}"] = False
                                    st.rerun()
                        
                        # Detay gösterimi
                        if st.session_state.get(f"show_detail_{symbol}", False):
                            st.write("---")
                            st.subheader(f"📊 {symbol} Pozisyon Detayları")
                            st.write(f"**Miktar:** {details['quantity']:.0f} lot")
                            st.write(f"**Giriş Fiyatı:** {details['entry_price']:.2f} TL")
                            st.write(f"**Güncel Fiyat:** {details['current_price']:.2f} TL")
                            st.write(f"**Güncel Değer:** {details['current_value']:,.0f} TL")
                            st.write(f"**Gerçekleşmemiş Getiri:** {details['unrealized_return']:+.2%}")
                            st.write(f"**Tutma Süresi:** {details['days_held']} gün")
                            st.write(f"**Güven Skoru:** {details['confidence']:.2f}")
                            
                            if st.button("❌ Kapat", key=f"close_detail_{symbol}"):
                                st.session_state[f"show_detail_{symbol}"] = False
                                st.rerun()
                        
                        # Silme onayı
                        if st.session_state.get(f"show_delete_{symbol}", False):
                            st.write("---")
                            st.warning(f"⚠️ {symbol} pozisyonunu silmek istediğinizden emin misiniz?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"✅ Evet, Sil", key=f"confirm_delete_{symbol}"):
                                    del paper_trader.positions[symbol]
                                    paper_trader.save_to_localStorage()
                                    st.session_state.paper_trader = paper_trader
                                    st.success(f"✅ {symbol} pozisyonu silindi!")
                                    st.session_state[f"show_delete_{symbol}"] = False
                                    st.rerun()
                            with col2:
                                if st.button("❌ İptal", key=f"cancel_delete_{symbol}"):
                                    st.session_state[f"show_delete_{symbol}"] = False
                                    st.rerun()
                        
                        st.write("---")
                    
                    # Performans analizi
                    st.subheader("📈 Portföy Performans Analizi")
                    
                    performance = summary['portfolio_performance']
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Toplam Kar/Zarar", f"{performance['total_profit_loss']:+.2%}")
                    
                    with col2:
                        st.metric("Ortalama Getiri", f"{performance['avg_return_per_trade']:+.2%}")
                    
                    with col3:
                        st.metric("En İyi İşlem", f"{performance['best_trade']:+.2%}")
                    
                    with col4:
                        st.metric("En Kötü İşlem", f"{performance['worst_trade']:+.2%}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Maksimum Düşüş", f"{performance['max_drawdown']:+.2%}")
                    
                    with col2:
                        st.metric("Sharpe Oranı", f"{performance['sharpe_ratio']:.2f}")
                    
                else:
                    st.info("📝 Henüz pozisyonunuz bulunmuyor. 'Hisse Ekleme' sekmesinden yeni pozisyonlar ekleyebilirsiniz.")
            
            with portfolio_tab3:
                st.markdown('<h4 class="subsection-title">⚙️ Portföy Ayarları</h4>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🔄 Portföy Sıfırlama**")
                    if st.button("🔄 Portföyü Sıfırla", type="secondary"):
                        new_capital = st.number_input("Yeni Sermaye (TL):", min_value=1000, value=100000)
                        if st.button("✅ Onayla", type="primary"):
                            paper_trader.reset_portfolio(new_capital)
                            st.success(f"✅ Portföy sıfırlandı! Yeni sermaye: {new_capital:,.0f} TL")
                            st.rerun()
                
                with col2:
                    st.markdown("**💾 Veri Yönetimi**")
                    if st.button("💾 Durumu Kaydet", type="secondary"):
                        paper_trader.save_to_localStorage()
                        st.success("✅ Durum kaydedildi!")
                    
                    if st.button("📥 Durumu Yükle", type="secondary"):
                        st.info("💡 Durum otomatik olarak yükleniyor...")
            
            # Risk yönetimi bilgileri
            st.subheader("⚠️ Risk Yönetimi")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Maksimum Pozisyon", f"{paper_trader.max_position_size:.1%}")
            
            with col2:
                st.metric("Stop Loss", f"{paper_trader.stop_loss_pct:.1%}")
            
            with col3:
                st.metric("Take Profit", f"{paper_trader.take_profit_pct:.1%}")
            
            # Son işlemler
            if summary['recent_trades']:
                st.subheader("📋 Son İşlemler")
                
                for trade in summary['recent_trades']:
                    emoji = "🟢" if trade['action'] == 'BUY' else "🔴"
                    manual_indicator = "👤" if trade.get('manual_entry', False) else "🤖"
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.write(f"{emoji} {manual_indicator}")
                    
                    with col2:
                        st.write(f"{trade['date'].strftime('%H:%M')}")
                    
                    with col3:
                        st.write(f"{trade['symbol']} - {trade['action']}")
                    
                    with col4:
                        if 'return_pct' in trade:
                            st.write(f"{trade['price']:.2f} TL ({trade['return_pct']:+.2%})")
                        else:
                            st.write(f"{trade['price']:.2f} TL")
                    
                    st.divider()
                    
        except Exception as e:
            st.warning("⚠️ Paper Trading modülü henüz aktif değil.")
            st.info("💡 Bu özellik yakında aktif olacak!")
            st.error(f"Hata detayı: {str(e)}")
    
    with tab5:
        # 🤖 Model Eğitimi - Sadece model eğitimi
        show_model_training_tab(all_symbols)

if __name__ == "__main__":
    main()
