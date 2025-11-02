"""
Dar Tahtalı ve Aşırı Yükselme Potansiyeli Olan Hisseleri Analiz Eden Modül
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from datetime import datetime, timedelta
import concurrent.futures
import time

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from price_target_predictor import PriceTargetPredictor
from dashboard_utils import load_config, load_stock_data
from src.fundamentals_loader import load_fundamentals
from src.bist_symbols_loader import get_extended_bist_symbols, add_user_symbol

@st.cache_data(ttl=300)  # 5 dakika cache
def load_stock_data_cached(symbol, period="1y", interval="1d", silent=False):
    """Hisse verilerini cache'li olarak yükle"""
    try:
        return load_stock_data(symbol, period, interval=interval, silent=silent)
    except Exception as e:
        if not silent:
            st.error(f"❌ {symbol} verisi yüklenemedi: {str(e)}")
        return pd.DataFrame()


def analyze_speculative_stock(symbol, config, period="1y", interval="1d", silent=False):
    """Dar tahtalı ve aşırı yükselme potansiyeli olan hisse analizi"""
    try:
        # Veri yükle
        data = load_stock_data_cached(symbol, period, interval=interval, silent=silent)
        if data.empty:
            return None
        
        # Temel veriler
        current_price = data['close'].iloc[-1]
        
        # Özellikler oluştur
        try:
            config_with_interval = config.copy()
            if 'MODEL_CONFIG' not in config_with_interval:
                config_with_interval['MODEL_CONFIG'] = {}
            config_with_interval['MODEL_CONFIG']['interval'] = interval
            
            # DataLoader ve FeatureEngineer oluştur
            loader = DataLoader(config_with_interval)
            engineer = FeatureEngineer(config_with_interval, data_loader=loader)
            
            # BIST 100 endeks verisini yükle
            index_data = loader.get_index_data(period="2y", interval=interval)
            
            # Özellikleri oluştur
            features_df = engineer.create_all_features(data, index_data=index_data)
        except Exception as e:
            if not silent:
                st.error(f"❌ {symbol} özellikler oluşturulamadı: {str(e)}")
            return None
        
        if features_df.empty:
            return None
        
        # OBV zaten feature engineering'de hesaplandı, yoksa hesapla
        if 'obv' not in features_df.columns:
            obv = pd.Series(index=data.index, dtype=float)
            obv.iloc[0] = data['volume'].iloc[0]
            for i in range(1, len(data)):
                if data['close'].iloc[i] > data['close'].iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] + data['volume'].iloc[i]
                elif data['close'].iloc[i] < data['close'].iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] - data['volume'].iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]
            features_df['obv'] = obv
        
        # Temel Metrikler
        # 1. Düşük Piyasa Değeri + Dar Tahta
        try:
            fundamentals = load_fundamentals(symbol)
            market_cap = fundamentals.get('key_metrics', {}).get('market_cap')
            info = fundamentals.get('info', {})
            
            # Halka açıklık oranı hesapla (floatShares / sharesOutstanding)
            shares_outstanding = info.get('sharesOutstanding')
            float_shares = info.get('floatShares')
            if shares_outstanding and shares_outstanding > 0:
                if float_shares:
                    float_ratio = float_shares / shares_outstanding
                else:
                    # floatShares yoksa yaklaşık olarak %50 varsay (placeholder)
                    float_ratio = 0.5
            else:
                float_ratio = None
        except Exception as e:
            market_cap = None
            float_ratio = None
            shares_outstanding = None
            float_shares = None
        
        # Hacim analizi
        avg_volume_20d = data['volume'].tail(20).mean()
        avg_volume_5d = data['volume'].tail(5).mean()
        current_volume = data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1
        volume_spike_3x = volume_ratio >= 3.0
        volume_spike_5x = volume_ratio >= 5.0
        
        # Son 3 ay yatay seyir kontrolü
        if len(data) >= 60:  # En az 60 gün veri
            price_3m_ago = data['close'].iloc[-60]
            price_change_3m = ((current_price / price_3m_ago) - 1) * 100
            is_horizontal = abs(price_change_3m) < 10  # %10'dan az hareket = yatay
        else:
            is_horizontal = False
            price_change_3m = 0
        
        # Teknik göstergeler
        rsi = features_df['rsi'].iloc[-1] if 'rsi' in features_df.columns else 50
        macd = features_df['macd'].iloc[-1] if 'macd' in features_df.columns else 0
        macd_signal = features_df['macd_signal'].iloc[-1] if 'macd_signal' in features_df.columns else 0
        macd_positive = macd > macd_signal
        
        # Moving averages
        sma_20 = features_df['sma_20'].iloc[-1] if 'sma_20' in features_df.columns else current_price
        price_above_sma20 = current_price > sma_20
        
        # Son 2 gün SMA20 üzerinde hacimli kapanış
        consecutive_above_sma20 = False
        if len(features_df) >= 2:
            last_2_days = features_df.tail(2)
            if all(p > s for p, s in zip(last_2_days['close'], last_2_days['sma_20'])):
                # Hacim kontrolü
                last_2_volumes = data['volume'].tail(2)
                avg_volume_check = last_2_volumes.mean() > avg_volume_20d
                consecutive_above_sma20 = avg_volume_check
        
        # Yatay sıkışma - direnç kırılımı kontrolü
        if len(data) >= 20:
            recent_high = data['high'].tail(20).max()
            recent_low = data['low'].tail(20).min()
            consolidation_range = (recent_high - recent_low) / recent_low
            is_consolidation = consolidation_range < 0.15  # %15'ten az hareket = sıkışma
            
            # Direnç kırılımı kontrolü
            if len(data) >= 21:
                resistance_level = data['high'].tail(20).head(19).max()  # Son 20 günün en yükseği (bugün hariç)
                is_breakout = current_price > resistance_level and volume_ratio > 1.5
            else:
                is_breakout = False
        else:
            is_consolidation = False
            is_breakout = False
        
        # RSI ve OBV uyumsuzluğu
        # Pozitif uyumsuzluk: Fiyat düşerken OBV artıyor (alım baskısı)
        obv_positive_divergence = False
        if len(features_df) >= 5:
            price_trend = features_df['close'].tail(5).pct_change().mean()
            obv_trend = features_df['obv'].tail(5).pct_change().mean()
            if price_trend < 0 and obv_trend > 0:
                obv_positive_divergence = True
        
        # Skorlama kriterleri
        score = 0
        criteria_met = {
            'low_market_cap': False,
            'low_float_ratio': False,
            'volume_spike': False,
            'technical_bullish': False,
            'consolidation_breakout': False,
            'rsi_optimal': False,
            'obv_divergence': False
        }
        
        # 1. Düşük Piyasa Değeri (1-5 milyar TL arası ideal)
        if market_cap:
            market_cap_billion = market_cap / 1_000_000_000 if market_cap else None
            if market_cap_billion and 1 <= market_cap_billion <= 5:
                score += 20
                criteria_met['low_market_cap'] = True
            elif market_cap_billion and market_cap_billion < 10:
                score += 10
        else:
            # Veri yoksa varsayılan skor ver (bilinmeyen)
            score += 5
        
        # 2. Düşük Halka Açıklık Oranı (<25%)
        if float_ratio:
            if float_ratio < 0.25:
                score += 25
                criteria_met['low_float_ratio'] = True
            elif float_ratio < 0.35:
                score += 15
        else:
            score += 5  # Bilinmiyor ama potansiyel var
        
        # 3. Hızla Artan Hacim (3-5x artış)
        if volume_spike_5x:
            score += 25
            criteria_met['volume_spike'] = True
        elif volume_spike_3x:
            score += 15
            criteria_met['volume_spike'] = True
        
        # 4. Teknik Görünüm
        technical_score = 0
        if macd_positive:
            technical_score += 5
        if price_above_sma20:
            technical_score += 5
        if consecutive_above_sma20:
            technical_score += 10
        if rsi >= 55 and rsi <= 65:
            technical_score += 10
            criteria_met['rsi_optimal'] = True
        elif rsi >= 60:
            technical_score += 5
        
        score += technical_score
        if technical_score >= 20:
            criteria_met['technical_bullish'] = True
        
        # 5. Yatay sıkışma - direnç kırılımı
        if is_consolidation and is_breakout:
            score += 20
            criteria_met['consolidation_breakout'] = True
        elif is_consolidation:
            score += 5
        
        # 6. OBV pozitif uyumsuzluk
        if obv_positive_divergence:
            score += 15
            criteria_met['obv_divergence'] = True
        
        # Fiyat performansı
        price_change_1d = data['close'].pct_change().iloc[-1] * 100
        price_change_1w = ((data['close'].iloc[-1] / data['close'].iloc[-5]) - 1) * 100 if len(data) >= 5 else 0
        price_change_1m = ((data['close'].iloc[-1] / data['close'].iloc[-20]) - 1) * 100 if len(data) >= 20 else 0
        
        # Volatilite
        volatility = data['close'].pct_change().std() * np.sqrt(252) * 100
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'market_cap': market_cap,
            'market_cap_billion': market_cap / 1_000_000_000 if market_cap else None,
            'float_ratio': float_ratio,
            'shares_outstanding': shares_outstanding,
            'float_shares': float_shares,
            'volume_ratio': volume_ratio,
            'volume_spike_3x': volume_spike_3x,
            'volume_spike_5x': volume_spike_5x,
            'avg_volume_20d': avg_volume_20d,
            'current_volume': current_volume,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_positive': macd_positive,
            'price_above_sma20': price_above_sma20,
            'consecutive_above_sma20': consecutive_above_sma20,
            'is_consolidation': is_consolidation,
            'is_breakout': is_breakout,
            'is_horizontal': is_horizontal,
            'price_change_3m': price_change_3m,
            'obv_positive_divergence': obv_positive_divergence,
            'price_change_1d': price_change_1d,
            'price_change_1w': price_change_1w,
            'price_change_1m': price_change_1m,
            'volatility': volatility,
            'score': score,
            'criteria_met': criteria_met,
            'criteria_count': sum(criteria_met.values())
        }
        
    except Exception as e:
        if not silent:
            st.error(f"❌ {symbol} analizi başarısız: {str(e)}")
        return None


def analyze_multiple_speculative_stocks(symbols, config, max_workers=5, interval="1d"):
    """Çoklu spekülatif hisse analizi - Paralel işlem"""
    results = []
    
    with st.spinner(f"🔍 {len(symbols)} hisse analiz ediliyor (Dar Tahta + Aşırı Yükselme Potansiyeli)..."):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(analyze_speculative_stock, symbol, config, "1y", interval): symbol 
                for symbol in symbols
            }
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    st.error(f"❌ {symbol} analizi başarısız: {str(e)}")
    
    return results


def show_speculative_opportunities_tab(bist_stocks, all_symbols, config, interval="1d", investment_horizon="MEDIUM_TERM"):
    """Dar Tahtalı ve Aşırı Yükselme Potansiyeli Olan Hisseler Tab"""
    
    st.markdown('<h2 class="section-title">🚀 Dar Tahtalı Fırsatlar - Aşırı Yükselme Potansiyeli</h2>', unsafe_allow_html=True)
    
    st.warning("""
    ⚠️ **YÜKSEK RİSK - YÜKSEK GETİRİ UYARISI**
    
    Bu sekme, dar tahtalı ve manipülatif hareketlere açık hisseleri analiz eder. 
    Bu hisselerde:
    - 📈 Çok hızlı yükselme potansiyeli var
    - 📉 Ancak çok hızlı düşme riski de yüksek
    - 💰 Likidite kapanması riski mevcut
    - 🎯 Kısa vadeli fırsatlar için uygundur
    
    **Mutlaka stop-loss kullanın ve risk yönetimine dikkat edin!**
    """)
    
    st.info("""
    🔍 **Bu Sekme Ne Analiz Ediyor?**
    
    Aşağıdaki kriterlere göre dar tahtalı ve aşırı yükselme potansiyeli olan hisseleri bulur:
    
    1. **📊 Düşük Piyasa Değeri + Dar Tahta**: Piyasa değeri 1-5 milyar TL arası, düşük işlem hacmi
    2. **📈 Hızla Artan Hacim**: Günlük hacim ortalamasının 3-5 katına çıkan hisseler
    3. **📉 Düşük Halka Açıklık Oranı**: %25'in altında halka açık pay oranı
    4. **🎯 Teknik Görünüm**: Yatay sıkışma, direnç kırılımı, MACD pozitif kesişim, RSI 55-65
    5. **💹 Hacim Destekli Sinyaller**: OBV pozitif uyumsuzluklar
    """)
    
    # Filtreleme seçenekleri
    st.markdown("### 🎯 Analiz Filtreleri")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider(
            "Minimum Skor:",
            min_value=0, max_value=100, value=40,
            help="Minimum skor eşiği (0-100 arası)",
            key="speculative_min_score"
        )
    
    with col2:
        min_criteria = st.slider(
            "Minimum Kriter Sayısı:",
            min_value=0, max_value=7, value=3,
            help="Kaç kriterin karşılanması gerekiyor?",
            key="speculative_min_criteria"
        )
    
    with col3:
        require_volume_spike = st.checkbox(
            "Hacim Patlaması Zorunlu",
            value=False,
            help="Sadece hacim patlaması gösteren hisseleri göster",
            key="speculative_require_volume_spike"
        )
    
    # Hisse seçimi
    st.markdown("### 📊 Analiz Edilecek Hisseler")
    
    selection_method = st.radio(
        "Hisse Seçim Yöntemi:",
        ["🎯 Sektörel Analiz", "📋 Manuel Seçim", "🏆 Popüler Hisseler"],
        horizontal=True,
        key="speculative_selection_method"
    )
    
    selected_symbols = []
    
    if selection_method == "🎯 Sektörel Analiz":
        selected_categories = st.multiselect(
            "Analiz Edilecek Sektörler:",
            list(bist_stocks.keys()),
            default=list(bist_stocks.keys())[:3],
            help="Hangi sektörlerden hisse analiz etmek istiyorsunuz?",
            key="speculative_selected_categories"
        )
        
        if selected_categories:
            for category in selected_categories:
                selected_symbols.extend(bist_stocks[category])
            
            max_stocks = st.slider("Maksimum Hisse Sayısı:", min_value=10, max_value=100, value=50, key="speculative_max_stocks")
            if len(selected_symbols) > max_stocks:
                selected_symbols = selected_symbols[:max_stocks]
    
    elif selection_method == "📋 Manuel Seçim":
        # Session state'te seçilen hisseleri ve mevcut listeyi sakla (cache için - rerun azaltma)
        if 'speculative_available_symbols' not in st.session_state:
            # BIST'teki TÜM hisseleri yükle (genişletilmiş liste) - sadece bir kez yükle
            all_bist_symbols = get_extended_bist_symbols()
            available = list(set(all_symbols + all_bist_symbols))
            available.sort()
            st.session_state.speculative_available_symbols = available
        
        # Mevcut listeyi kullan (cache - her rerun'da yeniden yüklenmez, performans için)
        available = st.session_state.speculative_available_symbols.copy()
        
        # Session state'te seçilen hisseleri sakla
        if 'speculative_selected_symbols' not in st.session_state:
            st.session_state.speculative_selected_symbols = []
        
        # Çok hızlı ve basit: Sadece multiselect - tüm hisseler burada!
        # Multiselect içinde arama yapabilirsiniz - Streamlit'in built-in arama özelliği
        selected_symbols = st.multiselect(
            "Analiz Edilecek Hisseler (Arama yapmak için yazın - örn: ISDMR, GEDZA, RAYSG):",
            available,
            default=st.session_state.speculative_selected_symbols,
            help="💡 Multiselect içinde direkt arama yapabilirsiniz! İstediğiniz hisse kodunu yazın (örn: ISDMR, GEDZA). Tüm BIST hisseleri burada.",
            key="speculative_manual_selection"
        )
        
        # Seçimi session state'e kaydet (sadece değiştiğinde - gereksiz rerun'ları önlemek için)
        if selected_symbols != st.session_state.speculative_selected_symbols:
            st.session_state.speculative_selected_symbols = selected_symbols
        
        # Seçilen hisse sayısı bilgisi
        if selected_symbols:
            st.info(f"✅ {len(selected_symbols)} hisse seçildi: {', '.join(selected_symbols[:5])}{'...' if len(selected_symbols) > 5 else ''}")
    
    else:  # Popüler Hisseler
        popular_stocks = ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS', 'GARAN.IS', 'ASELS.IS', 
                         'EREGL.IS', 'SAHOL.IS', 'TUPRS.IS', 'PETKM.IS', 'KRDMD.IS',
                         'FROTO.IS', 'ULKER.IS', 'MGROS.IS', 'OTKAR.IS', 'TKFEN.IS']
        
        selected_symbols = st.multiselect(
            "Popüler Hisseler:",
            popular_stocks,
            default=popular_stocks[:10],
            help="BIST'teki popüler hisselerden seçim yapın",
            key="speculative_popular_selection"
        )
    
    # Analiz butonu
    if selected_symbols and len(selected_symbols) > 0:
        st.markdown(f"**📊 Seçilen Hisse Sayısı:** {len(selected_symbols)}")
        
        if st.button("🚀 Dar Tahta Analizini Başlat", type="primary", key="speculative_analyze_button"):
            # Analizi başlat
            results = analyze_multiple_speculative_stocks(selected_symbols, config, interval=interval)
            
            if results:
                # DataFrame oluştur
                results_df = pd.DataFrame(results)
                
                # Filtreleri uygula
                filtered_df = results_df[
                    (results_df['score'] >= min_score) & 
                    (results_df['criteria_count'] >= min_criteria)
                ].copy()
                
                if require_volume_spike:
                    filtered_df = filtered_df[filtered_df['volume_spike_3x'] == True]
                
                # Skora göre sırala
                filtered_df = filtered_df.sort_values('score', ascending=False)
                
                st.markdown("---")
                st.markdown("### 🏆 Analiz Sonuçları")
                
                # Özet metrikler
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_score = filtered_df['score'].mean() if len(filtered_df) > 0 else 0
                    st.metric("Ortalama Skor", f"{avg_score:.1f}")
                
                with col2:
                    high_score_count = len(filtered_df[filtered_df['score'] >= 70])
                    st.metric("🟢 Yüksek Skor (≥70)", f"{high_score_count}")
                
                with col3:
                    volume_spike_count = len(filtered_df[filtered_df['volume_spike_3x'] == True])
                    st.metric("📈 Hacim Patlaması", f"{volume_spike_count}")
                
                with col4:
                    low_float_count = len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('low_float_ratio', False))])
                    st.metric("📉 Dar Tahta", f"{low_float_count}")
                
                # Filtrelenmiş sonuç sayısı
                st.info(f"📊 {len(filtered_df)} hisse filtrelendi (toplam {len(results_df)})")
                
                if len(filtered_df) > 0:
                    # Top 20 hisse tablosu
                    st.markdown("### 🥇 En Yüksek Potansiyelli Hisseler")
                    
                    display_df = filtered_df.head(20).copy()
                    
                    # Tablo için veri hazırla
                    display_df['Fiyat'] = display_df['current_price'].round(2)
                    display_df['Piyasa Değeri (Milyar)'] = display_df['market_cap_billion'].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                    )
                    display_df['Halka Açıklık %'] = display_df['float_ratio'].apply(
                        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
                    )
                    display_df['Hacim Oranı'] = display_df['volume_ratio'].round(2)
                    display_df['RSI'] = display_df['rsi'].round(1)
                    display_df['Skor'] = display_df['score'].round(1)
                    display_df['Kriter Sayısı'] = display_df['criteria_count']
                    
                    # Kriter durumu
                    def format_criteria(criteria_dict):
                        active = [k.replace('_', ' ').title() for k, v in criteria_dict.items() if v]
                        return ', '.join(active[:3])  # İlk 3'ünü göster
                    
                    display_df['Aktif Kriterler'] = display_df['criteria_met'].apply(format_criteria)
                    
                    # Tablo göster
                    table_columns = ['symbol', 'Fiyat', 'Piyasa Değeri (Milyar)', 'Halka Açıklık %', 
                                   'Hacim Oranı', 'RSI', 'Kriter Sayısı', 'Skor', 'Aktif Kriterler']
                    
                    st.dataframe(
                        display_df[table_columns],
                        column_config={
                            "symbol": "Hisse",
                            "Fiyat": st.column_config.NumberColumn("Fiyat (TL)", format="%.2f"),
                            "Piyasa Değeri (Milyar)": "Piyasa Değeri",
                            "Halka Açıklık %": "Halka Açıklık",
                            "Hacim Oranı": st.column_config.NumberColumn("Hacim Oranı", format="%.2fx"),
                            "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                            "Kriter Sayısı": "Kriter",
                            "Skor": st.column_config.NumberColumn("Skor", format="%.1f"),
                            "Aktif Kriterler": "Kriterler"
                        }
                    )
                    
                    # En iyi 5 hisse detayı
                    st.markdown("### 🔍 En İyi 5 Hissenin Detaylı Analizi")
                    
                    top_5 = filtered_df.head(5)
                    
                    for i, (_, stock) in enumerate(top_5.iterrows(), 1):
                        with st.expander(f"🥇 #{i} {stock['symbol']} - Skor: {stock['score']:.1f} | Kriter: {stock['criteria_count']}/7", expanded=i==1):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown("**💰 Temel Bilgiler**")
                                st.write(f"Güncel Fiyat: {stock['current_price']:.2f} TL")
                                if stock['market_cap_billion']:
                                    st.write(f"Piyasa Değeri: {stock['market_cap_billion']:.2f} Milyar TL")
                                if stock['float_ratio']:
                                    st.write(f"Halka Açıklık: {stock['float_ratio']*100:.1f}%")
                                st.write(f"1 Gün: {stock['price_change_1d']:+.2f}%")
                                st.write(f"1 Hafta: {stock['price_change_1w']:+.2f}%")
                                st.write(f"1 Ay: {stock['price_change_1m']:+.2f}%")
                            
                            with col2:
                                st.markdown("**📊 Hacim ve Teknik**")
                                st.write(f"Hacim Oranı: {stock['volume_ratio']:.2f}x")
                                if stock['volume_spike_5x']:
                                    st.success("🚀 5x+ Hacim Patlaması!")
                                elif stock['volume_spike_3x']:
                                    st.warning("📈 3x+ Hacim Artışı")
                                st.write(f"RSI: {stock['rsi']:.1f}")
                                if stock['macd_positive']:
                                    st.success("✅ MACD Pozitif")
                                st.write(f"Fiyat > SMA20: {'✅' if stock['price_above_sma20'] else '❌'}")
                                st.write(f"2 Gün SMA20 Üzeri: {'✅' if stock['consecutive_above_sma20'] else '❌'}")
                            
                            with col3:
                                st.markdown("**🎯 Kriterler**")
                                criteria = stock['criteria_met']
                                for key, value in criteria.items():
                                    emoji = "✅" if value else "❌"
                                    label = key.replace('_', ' ').title()
                                    st.write(f"{emoji} {label}")
                                
                                if stock['is_consolidation'] and stock['is_breakout']:
                                    st.success("🚀 Yatay Sıkışma + Direnç Kırılımı!")
                                if stock['obv_positive_divergence']:
                                    st.info("💹 OBV Pozitif Uyumsuzluk")
                            
                            # Risk uyarısı
                            st.warning(f"⚠️ **Risk Seviyesi**: Bu hisse yüksek risk taşır. Volatilite: {stock['volatility']:.1f}% - Mutlaka stop-loss kullanın!")
                    
                    # Grafik analizi
                    st.markdown("### 📊 Karşılaştırma Grafikleri")
                    
                    fig = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=(
                            'Piyasa Değeri Dağılımı (Milyar TL)',
                            'Halka Açıklık Oranı (%)',
                            'Hacim Oranı',
                            'RSI Dağılımı'
                        )
                    )
                    
                    # Piyasa değeri
                    valid_mcap = display_df[display_df['market_cap_billion'].notna()]
                    if len(valid_mcap) > 0:
                        fig.add_trace(
                            go.Bar(x=valid_mcap['symbol'], y=valid_mcap['market_cap_billion'],
                                   name='Piyasa Değeri', marker_color='lightblue'),
                            row=1, col=1
                        )
                    
                    # Halka açıklık
                    valid_float = display_df[display_df['float_ratio'].notna()]
                    if len(valid_float) > 0:
                        fig.add_trace(
                            go.Bar(x=valid_float['symbol'], y=valid_float['float_ratio']*100,
                                   name='Halka Açıklık %', marker_color='orange'),
                            row=1, col=2
                        )
                    
                    # Hacim oranı
                    fig.add_trace(
                        go.Bar(x=display_df['symbol'], y=display_df['volume_ratio'],
                               name='Hacim Oranı', marker_color='green'),
                        row=2, col=1
                    )
                    
                    # RSI
                    fig.add_trace(
                        go.Bar(x=display_df['symbol'], y=display_df['rsi'],
                               name='RSI', marker_color='red'),
                        row=2, col=2
                    )
                    
                    fig.update_layout(height=600, showlegend=False, title_text="Dar Tahtalı Hisseler Karşılaştırması")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Kriter dağılımı
                    st.markdown("### 📈 Kriter Karşılama Dağılımı")
                    
                    criteria_summary = {
                        'Düşük Piyasa Değeri': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('low_market_cap', False))]),
                        'Düşük Halka Açıklık': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('low_float_ratio', False))]),
                        'Hacim Patlaması': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('volume_spike', False))]),
                        'Teknik Boğa': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('technical_bullish', False))]),
                        'Konsolidasyon + Kırılım': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('consolidation_breakout', False))]),
                        'Optimal RSI': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('rsi_optimal', False))]),
                        'OBV Uyumsuzluk': len(filtered_df[filtered_df['criteria_met'].apply(lambda x: x.get('obv_divergence', False))])
                    }
                    
                    criteria_df = pd.DataFrame(list(criteria_summary.items()), columns=['Kriter', 'Hisse Sayısı'])
                    fig_criteria = px.bar(criteria_df, x='Kriter', y='Hisse Sayısı', 
                                         title="Her Kriteri Karşılayan Hisse Sayısı")
                    st.plotly_chart(fig_criteria, use_container_width=True)
                    
                    # Yatırım önerileri
                    st.markdown("### 💡 Yatırım Önerileri ve Risk Uyarıları")
                    
                    # En yüksek potansiyelli
                    top_potential = filtered_df.head(3)
                    st.success("🎯 **En Yüksek Potansiyelli 3 Hisse**")
                    for _, stock in top_potential.iterrows():
                        st.write(f"• **{stock['symbol']}**: Skor {stock['score']:.1f}, {stock['criteria_count']}/7 kriter, Hacim: {stock['volume_ratio']:.1f}x")
                    
                    # Risk uyarıları
                    st.error("""
                    ⚠️ **ÖNEMLİ RİSK UYARILARI:**
                    
                    1. **Manipülasyon Riski**: Dar tahtalı hisselerde fiyat manipülasyonu yaygındır
                    2. **Likidite Riski**: Tahta kilitlenebilir, istediğinizde satamayabilirsiniz
                    3. **Sert Düzeltme**: Tavan serisi bittiğinde %10-15 düşüş olabilir
                    4. **Stop-Loss Zorunlu**: Mutlaka stop-loss kullanın (%5-10 arası önerilir)
                    5. **Kısa Vadeli**: Uzun vadeli yatırım mantığıyla yaklaşmayın
                    6. **Pozisyon Boyutu**: Sermayenizin küçük bir kısmını (%5-10) kullanın
                    
                    **Bu tür yatırımlar yüksek risk taşır - sadece kaybetmeyi göze alabileceğiniz parayla yatırım yapın!**
                    """)
                    
                else:
                    st.warning("⚠️ Seçilen filtre kriterlerine uygun hisse bulunamadı! Filtreleri gevşetip tekrar deneyin.")
            else:
                st.error("❌ Analiz sonucu bulunamadı!")
    
    else:
        st.warning("⚠️ Lütfen analiz edilecek hisseleri seçin!")

