"""
Hisse Avcısı Tab - Toplu Analiz ve Karşılaştırma Sistemi
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
import threading

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from price_target_predictor import PriceTargetPredictor
from dashboard_utils import load_config, load_stock_data

@st.cache_data(ttl=300)  # 5 dakika cache
def load_stock_data_cached(symbol, period="1y"):
    """Hisse verilerini cache'li olarak yükle"""
    try:
        return load_stock_data(symbol, period)
    except Exception as e:
        st.error(f"❌ {symbol} verisi yüklenemedi: {str(e)}")
        return pd.DataFrame()


def analyze_single_stock(symbol, config, period="1y"):
    """Tek hisse analizi - Thread-safe"""
    try:
        # Veri yükle
        data = load_stock_data_cached(symbol, period)
        if data.empty:
            return None
        
        # Özellikler oluştur
        try:
            engineer = FeatureEngineer(config)
            features_df = engineer.create_all_features(data)
        except Exception as e:
            st.error(f"❌ {symbol} özellikler oluşturulamadı: {str(e)}")
            return None
        if features_df.empty:
            return None
        
        # Temel metrikler
        current_price = data['close'].iloc[-1]
        price_change_1d = data['close'].pct_change().iloc[-1] * 100
        price_change_1w = ((data['close'].iloc[-1] / data['close'].iloc[-5]) - 1) * 100 if len(data) >= 5 else 0
        price_change_1m = ((data['close'].iloc[-1] / data['close'].iloc[-20]) - 1) * 100 if len(data) >= 20 else 0
        
        # Volatilite
        volatility = data['close'].pct_change().std() * np.sqrt(252) * 100
        
        # Hacim analizi
        avg_volume = data['volume'].tail(20).mean()
        current_volume = data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Teknik göstergeler
        rsi = features_df['rsi'].iloc[-1] if 'rsi' in features_df.columns else 50
        macd = features_df['macd'].iloc[-1] if 'macd' in features_df.columns else 0
        macd_signal = features_df['macd_signal'].iloc[-1] if 'macd_signal' in features_df.columns else 0
        
        # Trend analizi
        sma_20 = features_df['sma_20'].iloc[-1] if 'sma_20' in features_df.columns else current_price
        sma_50 = features_df['sma_50'].iloc[-1] if 'sma_50' in features_df.columns else current_price
        
        trend_strength = "Yükseliş" if sma_20 > sma_50 else "Düşüş"
        
        # Model tahmini (varsa) - AI model öncelikli
        prediction = None
        confidence = None
        price_target = None
        
        # AI model tahmini (varsa) - Öncelik
        try:
            # En uygun modeli bul
            model_files = []
            if os.path.exists('src/models'):
                model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
            
            symbol_name = symbol.replace('.IS', '')
            symbol_models = [f for f in model_files if symbol_name in f]
            
            if symbol_models:
                # En son modeli seç
                symbol_models.sort(reverse=True)
                selected_model = symbol_models[0]
                
                # Modeli yükle ve tahmin yap
                predictor = StockDirectionPredictor(config)
                model_path = f'src/models/{selected_model}'
                
                if predictor.load_model(model_path):
                    # prepare_data otomatik olarak hedef değişkenleri filtreler
                    X, y = predictor.prepare_data(features_df)
                    predictions, probabilities = predictor.predict(X)
                    
                    # AI model tahmini
                    prediction = predictions[-1]
                    confidence = np.max(probabilities[-1])
                    
                    # Hedef fiyat hesapla
                    price_predictor = PriceTargetPredictor(config)
                    price_targets = price_predictor.calculate_price_targets(
                        current_price, prediction, confidence, volatility/100, data, {}
                    )
                    price_target = price_targets['targets']['moderate']
        
        except Exception as e:
            # Model tahmini başarısız olursa teknik analiz kullan
            technical_confidence = 0
            
            # RSI sinyali
            if rsi < 30:
                technical_confidence += 0.3
            elif rsi > 70:
                technical_confidence -= 0.2
            
            # MACD sinyali
            if macd > macd_signal:
                technical_confidence += 0.2
            else:
                technical_confidence -= 0.1
            
            # Trend sinyali
            if trend_strength == "Yükseliş":
                technical_confidence += 0.2
            else:
                technical_confidence -= 0.1
            
            # Momentum sinyali
            if price_change_1w > 5:
                technical_confidence += 0.2
            elif price_change_1w < -5:
                technical_confidence -= 0.2
            
            # Hacim sinyali
            if volume_ratio > 1.5:
                technical_confidence += 0.1
            elif volume_ratio < 0.5:
                technical_confidence -= 0.1
            
            # Teknik analiz bazlı tahmin
            if technical_confidence > 0.4:
                prediction = 1  # AL
                confidence = min(0.8, abs(technical_confidence))
            elif technical_confidence < -0.4:
                prediction = 0  # SAT
                confidence = min(0.8, abs(technical_confidence))
            else:
                prediction = None
                confidence = 0.5
            
            # Hedef fiyat hesapla (teknik analiz bazlı)
            if prediction is not None:
                if prediction == 1:  # AL sinyali
                    price_target = current_price * (1 + (confidence * 0.1))
                else:  # SAT sinyali
                    price_target = current_price * (1 - (confidence * 0.1))
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'price_change_1d': price_change_1d,
            'price_change_1w': price_change_1w,
            'price_change_1m': price_change_1m,
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'trend_strength': trend_strength,
            'prediction': prediction,
            'confidence': confidence,
            'price_target': price_target,
            'data_points': len(data)
        }
        
    except Exception as e:
        st.error(f"❌ {symbol} analizi başarısız: {str(e)}")
        return None

def train_model_for_symbol(symbol, config, progress_callback=None):
    """Tek hisse için model eğitimi"""
    try:
        if progress_callback:
            progress_callback(f"📊 {symbol} verisi yükleniyor...")
        
        # Veri yükle
        data = load_stock_data(symbol, "2y")
        if data.empty:
            return False, f"{symbol} verisi yüklenemedi"
        
        if progress_callback:
            progress_callback(f"🔧 {symbol} özellikler oluşturuluyor...")
        
        # Özellikler oluştur
        try:
            engineer = FeatureEngineer(config)
            features_df = engineer.create_all_features(data)
        except Exception as e:
            return False, f"{symbol} özellikler oluşturulamadı: {str(e)}"
        
        if features_df.empty:
            return False, f"{symbol} özellikler oluşturulamadı"
        
        if progress_callback:
            progress_callback(f"🤖 {symbol} model eğitiliyor...")
        
        # Model eğit
        predictor = StockDirectionPredictor(config)
        X, y = predictor.prepare_data(features_df)
        
        if len(X) < 100:  # Yeterli veri yok
            return False, f"{symbol} yeterli veri yok ({len(X)} gün)"
        
        # Model eğitimi
        results = predictor.train_model(X, y)
        
        if progress_callback:
            progress_callback(f"💾 {symbol} model kaydediliyor...")
        
        # Modeli kaydet
        symbol_name = symbol.replace('.IS', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol_name}_Model_{timestamp}.joblib"
        
        model_path = predictor.save_model(filename)
        
        if progress_callback:
            progress_callback(f"✅ {symbol} model eğitimi tamamlandı!")
        
        return True, f"{symbol} model eğitildi - Accuracy: {results['test_metrics']['accuracy']:.3f}"
        
    except Exception as e:
        return False, f"{symbol} model eğitimi başarısız: {str(e)}"

def train_models_batch(symbols, config, progress_container):
    """Toplu model eğitimi - Progress bar ile"""
    results = []
    total_symbols = len(symbols)
    
    # Progress bar oluştur
    progress_bar = progress_container.progress(0)
    status_text = progress_container.empty()
    
    for i, symbol in enumerate(symbols):
        # Progress güncelle
        progress = (i + 1) / total_symbols
        progress_bar.progress(progress)
        
        # Model eğit
        success, message = train_model_for_symbol(symbol, config, status_text.text)
        results.append({
            'symbol': symbol,
            'success': success,
            'message': message
        })
        
        # Kısa bekleme
        time.sleep(0.1)
    
    return results

def analyze_multiple_stocks(symbols, config, max_workers=5):
    """Çoklu hisse analizi - Paralel işlem"""
    results = []
    
    with st.spinner(f"🔍 {len(symbols)} hisse analiz ediliyor..."):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Tüm hisseleri paralel olarak analiz et
            future_to_symbol = {
                executor.submit(analyze_single_stock, symbol, config): symbol 
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

def calculate_stock_score(stock_data):
    """Hisse skoru hesapla - AI sinyali öncelikli"""
    score = 0
    weights = {
        'momentum': 0.25,      # Fiyat momentumu
        'volatility': 0.10,    # Volatilite (düşük = iyi)
        'volume': 0.10,        # Hacim artışı
        'technical': 0.15,     # Teknik göstergeler
        'prediction': 0.40     # Model tahmini (öncelikli - artırıldı)
    }
    
    # AI Sinyal kontrolü - Öncelikli!
    prediction = stock_data.get('prediction')
    confidence = stock_data.get('confidence')
    
    # SAT sinyali varsa ve confidence yüksekse, skorun büyük bir kısmını kes
    if prediction == 0 and confidence is not None and confidence > 0.6:
        # Yüksek güvenlilikle SAT sinyali = çok düşük skor
        return max(0, 30)  # Maksimum 30 puan (diğer faktörlerle)
    
    # Momentum skoru (1 haftalık ve 1 aylık performans)
    momentum_score = 0
    
    # 1 haftalık performans
    weekly_change = stock_data['price_change_1w']
    if weekly_change > 10:
        momentum_score += 50
    elif weekly_change > 5:
        momentum_score += 40
    elif weekly_change > 2:
        momentum_score += 30
    elif weekly_change > 0:
        momentum_score += 20
    elif weekly_change > -2:
        momentum_score += 10
    elif weekly_change > -5:
        momentum_score += 5
    
    # 1 aylık performans
    monthly_change = stock_data['price_change_1m']
    if monthly_change > 20:
        momentum_score += 50
    elif monthly_change > 10:
        momentum_score += 40
    elif monthly_change > 5:
        momentum_score += 30
    elif monthly_change > 0:
        momentum_score += 20
    elif monthly_change > -5:
        momentum_score += 10
    elif monthly_change > -10:
        momentum_score += 5
    
    score += momentum_score * weights['momentum']
    
    # Volatilite skoru (düşük volatilite = yüksek skor)
    volatility_score = max(0, 100 - stock_data['volatility'])
    score += volatility_score * weights['volatility']
    
    # Hacim skoru
    volume_score = min(100, stock_data['volume_ratio'] * 50)
    score += volume_score * weights['volume']
    
    # Teknik skoru
    technical_score = 0
    
    # RSI skoru
    if stock_data['rsi'] < 30:  # Aşırı satım - fırsat
        technical_score += 30
    elif stock_data['rsi'] > 70:  # Aşırı alım - risk
        technical_score += 5
    else:
        technical_score += 20
    
    # MACD skoru
    if stock_data['macd'] > stock_data['macd_signal']:
        technical_score += 30
    else:
        technical_score += 10
    
    # Trend skoru
    if stock_data['trend_strength'] == "Yükseliş":
        technical_score += 20
    else:
        technical_score += 5
    
    score += max(0, technical_score) * weights['technical']
    
    # Model tahmin skoru - En önemli faktör
    prediction_score = 0
    if prediction is not None and confidence is not None:
        if prediction == 1:  # AL sinyali
            prediction_score = confidence * 100  # Yüksek puan
        else:  # SAT sinyali
            prediction_score = (1 - confidence) * 10  # Çok düşük puan
    
    score += prediction_score * weights['prediction']
    
    # Final kontrol: SAT sinyali varsa skoru kısıtla
    if prediction == 0:
        return min(40, score)  # SAT sinyali için maksimum 40 puan
    
    return min(100, max(0, score))

def create_stock_comparison_chart(results_df):
    """Hisse karşılaştırma grafiği"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Son 1 Haftalık Fiyat Performansı (%)', 
            'Fiyat Dalgalanması - Risk Seviyesi (%)', 
            'İşlem Hacmi (Günlük/Ortalama)', 
            'RSI Göstergesi - Aşırı Alım/Satım'
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 1 haftalık fiyat değişimi
    fig.add_trace(
        go.Bar(x=results_df['symbol'], y=results_df['price_change_1w'], 
               name='1 Hafta Performansı', marker_color='lightblue',
               hovertemplate='<b>%{x}</b><br>1 Haftalık Değişim: %{y:.2f}%<extra></extra>'),
        row=1, col=1
    )
    
    # Volatilite (Risk seviyesi)
    fig.add_trace(
        go.Bar(x=results_df['symbol'], y=results_df['volatility'], 
               name='Fiyat Dalgalanması', marker_color='orange',
               hovertemplate='<b>%{x}</b><br>Risk Seviyesi: %{y:.2f}%<br><i>Düşük = Kararlı, Yüksek = Riskli</i><extra></extra>'),
        row=1, col=2
    )
    
    # Hacim oranı (Günlük/ortalama)
    fig.add_trace(
        go.Bar(x=results_df['symbol'], y=results_df['volume_ratio'], 
               name='Hacim Oranı', marker_color='green',
               hovertemplate='<b>%{x}</b><br>Günlük/Ortalama: %{y:.2f}x<br><i>1x = Normal, &gt;1.5x = İlgi Artışı</i><extra></extra>'),
        row=2, col=1
    )
    
    # RSI göstergesi
    fig.add_trace(
        go.Bar(x=results_df['symbol'], y=results_df['rsi'], 
               name='RSI', marker_color='red',
               hovertemplate='<b>%{x}</b><br>RSI: %{y:.1f}<br><i>&lt;30 = Aşırı Satım, &gt;70 = Aşırı Alım</i><extra></extra>'),
        row=2, col=2
    )
    
    # Y ekseni başlıklarını güncelle
    fig.update_yaxes(title_text="Değişim (%)", row=1, col=1)
    fig.update_yaxes(title_text="Volatilite (%)", row=1, col=2)
    fig.update_yaxes(title_text="Hacim Oranı", row=2, col=1)
    fig.update_yaxes(title_text="RSI Değeri", row=2, col=2)
    
    fig.update_layout(
        height=600, 
        showlegend=False, 
        title_text="Hisse Karşılaştırma Analizi",
        hovermode='closest'
    )
    return fig

def show_stock_hunter_tab(bist_stocks, all_symbols, config):
    """Hisse Avcısı Tab"""
    
    st.markdown('<h2 class="section-title">🎯 Hisse Avcısı - BIST Avı</h2>', unsafe_allow_html=True)
    
    st.info("""
    🔍 **Hisse Avcısı Nedir?**
    
    Bu sekme ile birden fazla hisseyi aynı anda analiz edebilir, karşılaştırabilir ve 
    en iyi fırsatları bulabilirsiniz. Sistem hisseleri çeşitli kriterlere göre sıralar:
    
    - 📈 **Getiri Potansiyeli**: En yüksek yükseliş potansiyeli olan hisseler
    - 🌪️ **Volatilite Analizi**: Yüksek volatilite ama pozitif görünen hisseler  
    - 🎯 **Teknik Sinyaller**: Güçlü teknik analiz sinyalleri veren hisseler
    - 🤖 **AI Tahminleri**: Model tahminleri en güvenilir olan hisseler
    """)
    
    # Seçim yöntemi
    st.markdown("### 🎯 Analiz Stratejisi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_type = st.selectbox(
            "Analiz Türü:",
            ["🏆 En İyi Fırsatlar", "🌪️ Yüksek Volatilite", "📈 Momentum Avcısı", "🤖 AI Destekli"],
            help="Hangi kriterlere göre hisse arayacağınızı seçin"
        )
    
    with col2:
        max_stocks = st.slider(
            "Maksimum Hisse Sayısı:",
            min_value=5, max_value=50, value=20,
            help="Analiz edilecek maksimum hisse sayısı"
        )
    
    # Otomatik model eğitimi seçeneği
    st.markdown("### 🤖 Model Yönetimi")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        auto_train_models = st.checkbox(
            "🔄 Otomatik Model Eğitimi",
            value=False,
            help="Eğitilmiş model yoksa otomatik eğit"
        )
    
    with col2:
        update_existing_models = st.checkbox(
            "🔄 Mevcut Modelleri Güncelle",
            value=False,
            help="Eski modelleri yenileriyle değiştir"
        )
    
    with col3:
        if st.button("🧹 Eski Modelleri Temizle", help="7 günden eski modelleri sil"):
            # Eski modelleri temizle
            if os.path.exists('src/models'):
                model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
                old_models = []
                cutoff_date = datetime.now() - timedelta(days=7)
                
                for model_file in model_files:
                    model_path = f'src/models/{model_file}'
                    if os.path.getctime(model_path) < cutoff_date.timestamp():
                        old_models.append(model_file)
                
                if old_models:
                    for model_file in old_models:
                        os.remove(f'src/models/{model_file}')
                    st.success(f"✅ {len(old_models)} eski model temizlendi!")
                else:
                    st.info("ℹ️ Temizlenecek eski model bulunamadı.")
            else:
                st.warning("⚠️ Model klasörü bulunamadı.")
    
    # Hisse seçimi
    st.markdown("### 📊 Analiz Edilecek Hisseler")
    
    selection_method = st.radio(
        "Hisse Seçim Yöntemi:",
        ["🎯 Sektörel Analiz", "📋 Manuel Seçim", "🏆 Popüler Hisseler"],
        horizontal=True
    )
    
    selected_symbols = []
    
    if selection_method == "🎯 Sektörel Analiz":
        # Sektör seçimi
        selected_categories = st.multiselect(
            "Analiz Edilecek Sektörler:",
            list(bist_stocks.keys()),
            default=list(bist_stocks.keys())[:3],
            help="Hangi sektörlerden hisse analiz etmek istiyorsunuz?"
        )
        
        if selected_categories:
            for category in selected_categories:
                selected_symbols.extend(bist_stocks[category])
            
            # Maksimum sayıya göre sınırla
            if len(selected_symbols) > max_stocks:
                selected_symbols = selected_symbols[:max_stocks]
    
    elif selection_method == "📋 Manuel Seçim":
        # Manuel seçim
        selected_symbols = st.multiselect(
            "Analiz Edilecek Hisseler:",
            all_symbols,
            default=all_symbols[:10],
            help="Analiz etmek istediğiniz hisseleri seçin"
        )
    
    else:  # Popüler Hisseler
        # Popüler hisseler
        popular_stocks = ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS', 'GARAN.IS', 'ASELS.IS', 
                         'EREGL.IS', 'SAHOL.IS', 'TUPRS.IS', 'PETKM.IS', 'KRDMD.IS',
                         'FROTO.IS', 'ULKER.IS', 'MGROS.IS', 'OTKAR.IS', 'TKFEN.IS']
        
        selected_symbols = st.multiselect(
            "Popüler Hisseler:",
            popular_stocks,
            default=popular_stocks[:10],
            help="BIST'teki popüler hisselerden seçim yapın"
        )
    
    # Analiz butonu
    if selected_symbols and len(selected_symbols) > 0:
        st.markdown(f"**📊 Seçilen Hisse Sayısı:** {len(selected_symbols)}")
        
        if st.button("🚀 Analizi Başlat", type="primary"):
            # Otomatik model eğitimi kontrolü
            if auto_train_models or update_existing_models:
                st.markdown("### 🤖 Model Durumu Kontrol Ediliyor...")
                
                # Model durumunu kontrol et
                symbols_without_models = []
                symbols_to_update = []
                
                if os.path.exists('src/models'):
                    model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
                    existing_models = {f.split('_')[0]: f for f in model_files}
                else:
                    existing_models = {}
                
                for symbol in selected_symbols:
                    symbol_name = symbol.replace('.IS', '')
                    
                    if symbol_name not in existing_models:
                        symbols_without_models.append(symbol)
                    elif update_existing_models:
                        symbols_to_update.append(symbol)
                
                # Model eğitimi gereken hisseler
                symbols_to_train = symbols_without_models + symbols_to_update
                
                if symbols_to_train:
                    st.info(f"🔄 {len(symbols_to_train)} hisse için model eğitimi başlatılıyor...")
                    
                    # Progress container oluştur
                    progress_container = st.container()
                    
                    # Model eğitimi başlat
                    training_results = train_models_batch(symbols_to_train, config, progress_container)
                    
                    # Sonuçları göster
                    successful_trainings = [r for r in training_results if r['success']]
                    failed_trainings = [r for r in training_results if not r['success']]
                    
                    if successful_trainings:
                        st.success(f"✅ {len(successful_trainings)} model başarıyla eğitildi!")
                        for result in successful_trainings:
                            st.write(f"• {result['message']}")
                    
                    if failed_trainings:
                        st.warning(f"⚠️ {len(failed_trainings)} model eğitimi başarısız:")
                        for result in failed_trainings:
                            st.write(f"• {result['message']}")
                    
                    st.markdown("---")
                
                else:
                    st.success("✅ Tüm hisseler için güncel modeller mevcut!")
            
            # Analizi başlat
            results = analyze_multiple_stocks(selected_symbols, config)
            
            if results:
                # DataFrame oluştur
                results_df = pd.DataFrame(results)
                
                # None değerleri temizle ve güvenli hale getir
                results_df['prediction'] = results_df['prediction'].where(pd.notna(results_df['prediction']), None)
                results_df['confidence'] = results_df['confidence'].where(pd.notna(results_df['confidence']), None)
                results_df['price_target'] = results_df['price_target'].where(pd.notna(results_df['price_target']), None)
                
                # Skor hesapla
                results_df['score'] = results_df.apply(calculate_stock_score, axis=1)
                
                # Analiz türüne göre sırala
                if analysis_type == "🏆 En İyi Fırsatlar":
                    results_df = results_df.sort_values('score', ascending=False)
                elif analysis_type == "🌪️ Yüksek Volatilite":
                    results_df = results_df.sort_values('volatility', ascending=False)
                elif analysis_type == "📈 Momentum Avcısı":
                    results_df = results_df.sort_values('price_change_1w', ascending=False)
                elif analysis_type == "🤖 AI Destekli":
                    # Model tahmini olan hisseleri öncele
                    results_df = results_df.sort_values(['confidence', 'score'], ascending=[False, False])
                
                # Sonuçları göster
                st.markdown("---")
                st.markdown("### 🏆 Analiz Sonuçları")
                
                # Özet metrikler
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_score = results_df['score'].mean()
                    st.metric("Ortalama Skor", f"{avg_score:.1f}")
                
                with col2:
                    buy_signals = len(results_df[results_df['prediction'] == 1])
                    st.metric("🟢 AL Sinyali", f"{buy_signals}/{len(results_df)}")
                
                with col3:
                    high_conf_stocks = len(results_df[(results_df['confidence'] >= 0.7)])
                    st.metric("Yüksek Güven", f"{high_conf_stocks}/{len(results_df)}")
                
                with col4:
                    low_risk_stocks = len(results_df[results_df['volatility'] < 30])
                    st.metric("Düşük Risk", f"{low_risk_stocks}/{len(results_df)}")
                
                # Filtreleme seçenekleri
                st.markdown("### 🔍 Filtreleme Seçenekleri")
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    show_only = st.selectbox(
                        "Göster:",
                        ["Tümü", "🟢 Sadece AL", "🔴 Sadece SAT", "🟢 Yüksek Skor (>60)", "🟡 Orta Skor (40-60)", "🔴 Düşük Skor (<40)"],
                        key="filter_show"
                    )
                
                with filter_col2:
                    risk_level = st.selectbox(
                        "Risk Seviyesi:",
                        ["Tümü", "🟢 Düşük (<30%)", "🟡 Orta (30-50%)", "🔴 Yüksek (>50%)"],
                        key="filter_risk"
                    )
                
                with filter_col3:
                    confidence_level = st.selectbox(
                        "Güven Seviyesi:",
                        ["Tümü", "🟢 Çok Yüksek (≥0.8)", "🟡 Yüksek (0.6-0.8)", "🔴 Düşük (<0.6)"],
                        key="filter_confidence"
                    )
                
                # Filtreleri uygula
                filtered_df = results_df.copy()
                
                if show_only == "🟢 Sadece AL":
                    filtered_df = filtered_df[filtered_df['prediction'] == 1]
                elif show_only == "🔴 Sadece SAT":
                    filtered_df = filtered_df[filtered_df['prediction'] == 0]
                elif show_only == "🟢 Yüksek Skor (>60)":
                    filtered_df = filtered_df[filtered_df['score'] > 60]
                elif show_only == "🟡 Orta Skor (40-60)":
                    filtered_df = filtered_df[(filtered_df['score'] >= 40) & (filtered_df['score'] <= 60)]
                elif show_only == "🔴 Düşük Skor (<40)":
                    filtered_df = filtered_df[filtered_df['score'] < 40]
                
                if risk_level == "🟢 Düşük (<30%)":
                    filtered_df = filtered_df[filtered_df['volatility'] < 30]
                elif risk_level == "🟡 Orta (30-50%)":
                    filtered_df = filtered_df[(filtered_df['volatility'] >= 30) & (filtered_df['volatility'] < 50)]
                elif risk_level == "🔴 Yüksek (>50%)":
                    filtered_df = filtered_df[filtered_df['volatility'] > 50]
                
                if confidence_level == "🟢 Çok Yüksek (≥0.8)":
                    filtered_df = filtered_df[filtered_df['confidence'] >= 0.8]
                elif confidence_level == "🟡 Yüksek (0.6-0.8)":
                    filtered_df = filtered_df[(filtered_df['confidence'] >= 0.6) & (filtered_df['confidence'] < 0.8)]
                elif confidence_level == "🔴 Düşük (<0.6)":
                    filtered_df = filtered_df[filtered_df['confidence'] < 0.6]
                
                # Filtrelenmiş sonuç sayısı
                st.info(f"📊 {len(filtered_df)} hisse listelendi (toplam {len(results_df)})")
                
                # Top 10 hisse tablosu - Dinamik başlık
                if len(filtered_df) > 0:
                    avg_score = filtered_df['score'].mean()
                    if avg_score >= 60:
                        table_title = f"### 🥇 En İyi Hisseler (Skor: {avg_score:.1f})"
                    elif avg_score >= 40:
                        table_title = f"### 📊 Analiz Edilen Hisseler (Skor: {avg_score:.1f})"
                    else:
                        table_title = f"### ⚠️ Düşük Skorlu Hisseler (Skor: {avg_score:.1f})"
                    
                    st.markdown(table_title)
                    
                    # Tablo için veri hazırla (filtrelenmiş verilerden)
                    display_df = filtered_df.head(10).copy()
                else:
                    st.warning("⚠️ Seçilen filtre kriterlerine uygun hisse bulunamadı!")
                    display_df = pd.DataFrame()
                
                if not display_df.empty:
                    # Kolonları hazırla
                    display_df['Fiyat'] = display_df['current_price'].round(2)
                    display_df['1Gün %'] = display_df['price_change_1d'].round(2)
                    display_df['1Hafta %'] = display_df['price_change_1w'].round(2)
                    display_df['1Ay %'] = display_df['price_change_1m'].round(2)
                    display_df['Volatilite %'] = display_df['volatility'].round(1)
                    display_df['Skor'] = display_df['score'].round(1)
                    display_df['RSI'] = display_df['rsi'].round(1)
                    display_df['Trend'] = display_df['trend_strength']
                    
                    # AI tahminleri
                    display_df['AI Sinyal'] = display_df.apply(lambda x: 
                        f"{'🟢 AL' if x['prediction'] == 1 else '🔴 SAT' if x['prediction'] == 0 else '⚪ N/A'}", axis=1)
                    
                    # AI Güven kategorisi (Yüksek güven = iyi)
                    def categorize_confidence(conf):
                        if pd.isna(conf) or conf is None:
                            return "⚪ N/A"
                        if conf >= 0.8:
                            return "🟢 Çok Yüksek"
                        elif conf >= 0.6:
                            return "🟡 Orta"
                        else:
                            return "🔴 Düşük"
                    
                    display_df['AI Güven'] = display_df['confidence'].apply(categorize_confidence)
                    
                    # Hedef fiyat
                    display_df['Hedef Fiyat'] = display_df['price_target'].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
                    )
                    
                    # Risk Kategorisi
                    def categorize_risk(volatility):
                        if volatility > 50:
                            return "🔴 Yüksek"
                        elif volatility > 30:
                            return "🟡 Orta"
                        else:
                            return "🟢 Düşük"
                    
                    display_df['Risk'] = display_df['volatility'].apply(categorize_risk)
                    
                    # Skor kategorisi
                    def categorize_score(score):
                        if score >= 70:
                            return "🟢 Mükemmel"
                        elif score >= 50:
                            return "🟡 İyi"
                        else:
                            return "🔴 Orta"
                    
                    display_df['Skor Kategori'] = display_df['score'].apply(categorize_score)
                    
                    # Tablo göster
                    table_columns = ['symbol', 'Fiyat', '1Hafta %', 'Skor Kategori', 'Skor', 
                                   'AI Sinyal', 'AI Güven', 'Risk', 'RSI', 'Hedef Fiyat']
                    
                    st.dataframe(
                        display_df[table_columns],
                        use_container_width=True,
                        column_config={
                            "symbol": "Hisse",
                            "Fiyat": st.column_config.NumberColumn("Fiyat (TL)", format="%.2f"),
                            "1Hafta %": st.column_config.NumberColumn("1 Hafta %", format="%.2f"),
                            "Skor Kategori": "Kategori",
                            "Skor": st.column_config.NumberColumn("Skor", format="%.1f"),
                            "AI Sinyal": "AI Sinyal",
                            "AI Güven": "AI Güven",
                            "Risk": "Risk",
                            "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                            "Hedef Fiyat": "Hedef (TL)"
                        }
                    )
                    
                    # Grafik analizi
                    st.markdown("### 📊 Karşılaştırma Grafikleri")
                    comparison_chart = create_stock_comparison_chart(filtered_df if len(filtered_df) > 0 else results_df)
                    st.plotly_chart(comparison_chart, use_container_width=True)
                
                # Detaylı analiz
                st.markdown("### 🔍 Detaylı Analiz")
                
                # En iyi 3 hisse detayı
                top_3 = results_df.head(3)
                
                for i, (_, stock) in enumerate(top_3.iterrows(), 1):
                    with st.expander(f"🥇 #{i} {stock['symbol']} - Skor: {stock['score']:.1f}", expanded=i==1):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**💰 Fiyat Bilgileri**")
                            st.write(f"Güncel Fiyat: {stock['current_price']:.2f} TL")
                            st.write(f"1 Gün: {stock['price_change_1d']:+.2f}%")
                            st.write(f"1 Hafta: {stock['price_change_1w']:+.2f}%")
                            st.write(f"1 Ay: {stock['price_change_1m']:+.2f}%")
                        
                        with col2:
                            st.markdown("**📊 Teknik Analiz**")
                            st.write(f"Volatilite: {stock['volatility']:.1f}%")
                            st.write(f"RSI: {stock['rsi']:.1f}")
                            st.write(f"Trend: {stock['trend_strength']}")
                            st.write(f"Hacim Oranı: {stock['volume_ratio']:.2f}x")
                        
                        with col3:
                            st.markdown("**🤖 AI Tahmini**")
                            if stock['prediction'] is not None:
                                signal = "🟢 AL" if stock['prediction'] == 1 else "🔴 SAT"
                                st.write(f"Sinyal: {signal}")
                                st.write(f"Güven: {stock['confidence']:.2f}")
                                if stock['price_target']:
                                    st.write(f"Hedef: {stock['price_target']:.2f} TL")
                            else:
                                st.write("Model tahmini yok")
                
                # Sektörel dağılım
                st.markdown("### 🏭 Sektörel Dağılım")
                
                # Hangi sektörden kaç hisse var
                sector_counts = {}
                for _, stock in results_df.iterrows():
                    symbol = stock['symbol']
                    for sector, stocks in bist_stocks.items():
                        if symbol in stocks:
                            sector_counts[sector] = sector_counts.get(sector, 0) + 1
                            break
                
                if sector_counts:
                    sector_df = pd.DataFrame(list(sector_counts.items()), columns=['Sektör', 'Hisse Sayısı'])
                    fig = px.pie(sector_df, values='Hisse Sayısı', names='Sektör', 
                               title="Analiz Edilen Hisselerin Sektörel Dağılımı")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Risk analizi
                st.markdown("### ⚠️ Risk Analizi")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🌪️ Volatilite Dağılımı**")
                    volatility_ranges = {
                        'Düşük (<20%)': len(results_df[results_df['volatility'] < 20]),
                        'Orta (20-40%)': len(results_df[(results_df['volatility'] >= 20) & (results_df['volatility'] < 40)]),
                        'Yüksek (40-60%)': len(results_df[(results_df['volatility'] >= 40) & (results_df['volatility'] < 60)]),
                        'Çok Yüksek (>60%)': len(results_df[results_df['volatility'] >= 60])
                    }
                    
                    for range_name, count in volatility_ranges.items():
                        st.write(f"{range_name}: {count} hisse")
                
                with col2:
                    st.markdown("**📈 Performans Dağılımı**")
                    performance_ranges = {
                        'Güçlü Yükseliş (>10%)': len(results_df[results_df['price_change_1w'] > 10]),
                        'Yükseliş (0-10%)': len(results_df[(results_df['price_change_1w'] >= 0) & (results_df['price_change_1w'] <= 10)]),
                        'Düşüş (0-(-10%))': len(results_df[(results_df['price_change_1w'] >= -10) & (results_df['price_change_1w'] < 0)]),
                        'Güçlü Düşüş (<-10%)': len(results_df[results_df['price_change_1w'] < -10])
                    }
                    
                    for range_name, count in performance_ranges.items():
                        st.write(f"{range_name}: {count} hisse")
                
                # Yatırım önerileri
                st.markdown("### 💡 Yatırım Önerileri")
                
                # En iyi fırsatlar
                best_opportunities = results_df[
                    (results_df['score'] > 70) & 
                    (results_df['price_change_1w'] > 0) & 
                    (results_df['volatility'] < 50)
                ].head(5)
                
                if not best_opportunities.empty:
                    st.success("🎯 **En İyi Fırsatlar** (Yüksek skor + Pozitif momentum + Düşük risk)")
                    for _, stock in best_opportunities.iterrows():
                        st.write(f"• **{stock['symbol']}**: Skor {stock['score']:.1f}, 1 hafta {stock['price_change_1w']:+.1f}%")
                
                # Yüksek volatilite fırsatları
                high_vol_opportunities = results_df[
                    (results_df['volatility'] > 40) & 
                    (results_df['price_change_1w'] > 0) & 
                    (results_df['prediction'] == 1)
                ].head(5)
                
                if not high_vol_opportunities.empty:
                    st.warning("🌪️ **Yüksek Volatilite Fırsatları** (Riskli ama pozitif)")
                    for _, stock in high_vol_opportunities.iterrows():
                        st.write(f"• **{stock['symbol']}**: Volatilite {stock['volatility']:.1f}%, AI sinyali AL")
                
                # AI destekli öneriler
                ai_recommendations = results_df[
                    (results_df['prediction'].notna()) & 
                    (results_df['confidence'] > 0.7)
                ].head(5)
                
                if not ai_recommendations.empty:
                    st.info("🤖 **AI Destekli Öneriler** (Yüksek güven skorlu)")
                    for _, stock in ai_recommendations.iterrows():
                        signal = "AL" if stock['prediction'] == 1 else "SAT"
                        st.write(f"• **{stock['symbol']}**: {signal} sinyali, güven {stock['confidence']:.2f}")
                
                # Teknik analiz önerileri
                technical_buy_signals = results_df[
                    (results_df['rsi'] < 30) & 
                    (results_df['price_change_1w'] > 0) & 
                    (results_df['trend_strength'] == "Yükseliş")
                ].head(5)
                
                if not technical_buy_signals.empty:
                    st.success("📈 **Teknik Analiz AL Sinyalleri** (RSI Aşırı Satım + Yükseliş)")
                    for _, stock in technical_buy_signals.iterrows():
                        st.write(f"• **{stock['symbol']}**: RSI {stock['rsi']:.1f}, Trend {stock['trend_strength']}")
                
                # Momentum fırsatları
                momentum_opportunities = results_df[
                    (results_df['price_change_1w'] > 10) & 
                    (results_df['volume_ratio'] > 1.5) & 
                    (results_df['volatility'] < 60)
                ].head(5)
                
                if not momentum_opportunities.empty:
                    st.info("🚀 **Momentum Fırsatları** (Güçlü yükseliş + Yüksek hacim)")
                    for _, stock in momentum_opportunities.iterrows():
                        st.write(f"• **{stock['symbol']}**: 1 hafta {stock['price_change_1w']:+.1f}%, Hacim {stock['volume_ratio']:.1f}x")
                
                # Düşük riskli fırsatlar
                low_risk_opportunities = results_df[
                    (results_df['volatility'] < 25) & 
                    (results_df['price_change_1w'] > 0) & 
                    (results_df['score'] > 60)
                ].head(5)
                
                if not low_risk_opportunities.empty:
                    st.success("🛡️ **Düşük Riskli Fırsatlar** (Düşük volatilite + Pozitif)")
                    for _, stock in low_risk_opportunities.iterrows():
                        st.write(f"• **{stock['symbol']}**: Volatilite {stock['volatility']:.1f}%, Skor {stock['score']:.1f}")
                
                # Sektörel öneriler
                st.markdown("### 🏭 Sektörel Öneriler")
                
                sector_recommendations = {}
                for _, stock in results_df.iterrows():
                    symbol = stock['symbol']
                    for sector, stocks in bist_stocks.items():
                        if symbol in stocks:
                            if sector not in sector_recommendations:
                                sector_recommendations[sector] = []
                            sector_recommendations[sector].append(stock)
                            break
                
                # Her sektör için en iyi hisseyi öner
                for sector, stocks in sector_recommendations.items():
                    if stocks:
                        best_stock = max(stocks, key=lambda x: x['score'])
                        if best_stock['score'] > 60:
                            signal_emoji = "🟢" if best_stock['prediction'] == 1 else "🔴" if best_stock['prediction'] == 0 else "⚪"
                            st.write(f"**{sector}**: {signal_emoji} **{best_stock['symbol']}** - Skor: {best_stock['score']:.1f}")
                
                # Risk uyarıları
                st.markdown("### ⚠️ Risk Uyarıları")
                
                high_risk_stocks = results_df[
                    (results_df['volatility'] > 60) & 
                    (results_df['price_change_1w'] < -5)
                ].head(3)
                
                if not high_risk_stocks.empty:
                    st.error("🚨 **Yüksek Riskli Hisseler** (Yüksek volatilite + Düşüş)")
                    for _, stock in high_risk_stocks.iterrows():
                        st.write(f"• **{stock['symbol']}**: Volatilite {stock['volatility']:.1f}%, 1 hafta {stock['price_change_1w']:+.1f}%")
                
                # Genel piyasa durumu
                st.markdown("### 📊 Genel Piyasa Durumu")
                
                positive_count = len(results_df[results_df['price_change_1w'] > 0])
                total_count = len(results_df)
                positive_ratio = positive_count / total_count if total_count > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if positive_ratio > 0.6:
                        st.success(f"📈 **Piyasa Durumu: Pozitif** ({positive_count}/{total_count})")
                    elif positive_ratio > 0.4:
                        st.warning(f"⚖️ **Piyasa Durumu: Karışık** ({positive_count}/{total_count})")
                    else:
                        st.error(f"📉 **Piyasa Durumu: Negatif** ({positive_count}/{total_count})")
                
                with col2:
                    avg_volatility = results_df['volatility'].mean()
                    if avg_volatility < 30:
                        st.success(f"🛡️ **Volatilite: Düşük** ({avg_volatility:.1f}%)")
                    elif avg_volatility < 50:
                        st.warning(f"⚠️ **Volatilite: Orta** ({avg_volatility:.1f}%)")
                    else:
                        st.error(f"🌪️ **Volatilite: Yüksek** ({avg_volatility:.1f}%)")
                
                with col3:
                    ai_signals_count = len(results_df[results_df['prediction'].notna()])
                    if ai_signals_count > 0:
                        ai_buy_count = len(results_df[results_df['prediction'] == 1])
                        ai_sell_count = len(results_df[results_df['prediction'] == 0])
                        st.info(f"🤖 **AI Sinyalleri**: {ai_buy_count} AL, {ai_sell_count} SAT")
                    else:
                        st.info("🤖 **AI Sinyalleri**: Teknik analiz bazlı")
                
            else:
                st.error("❌ Analiz sonucu bulunamadı!")
    
    else:
        st.warning("⚠️ Lütfen analiz edilecek hisseleri seçin!")
