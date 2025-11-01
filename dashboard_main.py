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
from dashboard_portfolio_manager import show_portfolio_manager_tab
from dashboard_fundamental_analysis import show_fundamental_analysis_tab
from dashboard_guide import show_guide_tab
from dashboard_speculative_opportunities import show_speculative_opportunities_tab

# Yardımcı modülleri import et
from dashboard_utils import load_config, load_stock_data, analyze_stock_characteristics, get_auto_params
from dashboard_charts import plot_price_chart, plot_volume_chart, plot_technical_indicators
from src.bist_symbols_loader import get_extended_bist_symbols, add_user_symbol

def main():
    """Ana dashboard"""
    
    # Streamlit sayfa konfigürasyonu - Tam genişlik
    st.set_page_config(
        page_title="Hisse Senedi Yön Tahmini",
        page_icon="📈",
        layout="wide",  # Tam genişlik
        initial_sidebar_state="expanded"
    )
    
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
    
    # Tüm hisseleri tek listede topla (önce mevcut kategori bazlı)
    all_symbols_from_categories = []
    for category, stocks in bist_stocks.items():
        all_symbols_from_categories.extend(stocks)
    all_symbols_from_categories = sorted(list(set(all_symbols_from_categories)))
    
    # BIST'teki TÜM hisseleri yükle (genişletilmiş liste)
    all_bist_symbols = get_extended_bist_symbols()
    
    # Kategori bazlı ve genişletilmiş listeyi birleştir
    all_symbols = sorted(list(set(all_symbols_from_categories + all_bist_symbols)))
    
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
            
            # Yeni hisseyi listeye ekle ve kalıcı olarak kaydet
            if search_clean not in all_symbols:
                filtered_symbols = [search_clean]
                all_symbols.insert(0, search_clean)
                # Kalıcı olarak kaydet
                add_user_symbol(search_clean)
                st.sidebar.success(f"✅ {search_clean} eklendi ve kaydedildi!")
        
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
            if st.button(f"{stock.replace('.IS', '')}", key=f"quick_{stock}_{i}"):
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
    
    # Yatırım süresi seçimi - YENİ! YENİ!
    st.sidebar.markdown("### 🎯 Yatırım Süresi")
    investment_horizon_options = {
        "⚡ Kısa Vade (1 hafta - 1 ay)": "SHORT_TERM",
        "📊 Orta Vade (1 ay - 3 ay)": "MEDIUM_TERM",
        "🏆 Uzun Vade (3 ay - 1 yıl)": "LONG_TERM"
    }
    
    investment_horizon_keys = list(investment_horizon_options.keys())
    investment_horizon_values = list(investment_horizon_options.values())
    
    # Session state'te seçili yatırım süresini sakla
    if 'selected_investment_horizon' not in st.session_state:
        st.session_state.selected_investment_horizon = "MEDIUM_TERM"
    
    # Mevcut seçimi index'e çevir
    current_index = investment_horizon_values.index(st.session_state.selected_investment_horizon) if st.session_state.selected_investment_horizon in investment_horizon_values else 1
    
    investment_horizon_display = st.sidebar.selectbox(
        "Yatırım Stratejisi:",
        investment_horizon_keys,
        index=current_index,
        help="Yatırım sürenize göre model eğitimi ve analiz yapılır"
    )
    
    selected_investment_horizon = investment_horizon_options[investment_horizon_display]
    st.session_state.selected_investment_horizon = selected_investment_horizon
    
    # Config'e yatırım süresini ekle
    config['MODEL_CONFIG']['investment_horizon'] = selected_investment_horizon
    
    # Açıklama
    horizon_descriptions = {
        "SHORT_TERM": "📈 Küçük fiyat hareketlerine odaklanır, günlük işlemler için",
        "MEDIUM_TERM": "⚖️ Dengeli yaklaşım, haftalık/aylık trendleri hedefler",
        "LONG_TERM": "🎯 Büyük fiyat hareketlerini tahmin eder, uzun vadeli stratejiler için"
    }
    
    st.sidebar.info(f"💡 {horizon_descriptions[selected_investment_horizon]}")
    
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
    
    # Sekmeler - ilişkilere göre yeniden düzenlendi
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Veri Analizi",
        "📑 Temel Analiz",
        "🔮 Tahmin Karar",
        "🎯 Hisse Avcısı",
        "🚀 Dar Tahta Fırsatlar",
        "🤖 Portföy Yöneticisi",
        "📘 Rehber",
        "🔧 Model Eğitimi"
    ])
    
    with tab1:
        # 📊 Veri Analizi - Sadece hisse analizi ve veri
        show_data_analysis_tab(selected_symbol, period, interval)
    
    with tab2:
        # 📑 Temel Analiz - Finansal tablolar ve oranlar
        show_fundamental_analysis_tab(selected_symbol)
    
    with tab3:
        # 🔮 Tahmin Karar - Doğrudan gelecek tahmin içeriği
        show_future_prediction_tab(selected_symbol, config, interval=interval, investment_horizon=selected_investment_horizon)
    
    with tab4:
        # 🎯 Hisse Avcısı - Toplu analiz ve karşılaştırma
        show_stock_hunter_tab(bist_stocks, all_symbols, config, interval=interval, investment_horizon=selected_investment_horizon)
    
    with tab5:
        # 🚀 Dar Tahta Fırsatlar - Dar tahtalı ve aşırı yükselme potansiyeli olan hisseler
        show_speculative_opportunities_tab(bist_stocks, all_symbols, config, interval=interval, investment_horizon=selected_investment_horizon)
    
    with tab6:
        # 🤖 Robot Portföy Yöneticisi - Günlük yatırım kararları
        show_portfolio_manager_tab(config, interval=interval, investment_horizon=selected_investment_horizon)
    
    with tab7:
        # 📘 Rehber - Teknik ve Temel Analiz Bilgi Merkezi
        show_guide_tab()

    with tab8:
        # 🔧 Model Eğitimi - Ayarlar niteliğinde
        show_model_training_tab(all_symbols)

if __name__ == "__main__":
    main()
