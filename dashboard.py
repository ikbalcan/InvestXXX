"""
Hisse Senedi Yön Tahmini Sistemi - Streamlit Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yaml
import sys
import os
from datetime import datetime, timedelta
import logging
import yfinance as yf

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from backtest import Backtester
from live_trade import PaperTrader

def analyze_stock_characteristics(symbol, period="2y"):
    """
    Hisse karakteristiklerini analiz eder ve parametre önerileri döndürür
    """
    try:
        # Veri yükle
        data = yf.download(symbol, period=period, progress=False)
        if data.empty:
            return None
            
        # Temel istatistikler
        returns = data['Close'].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252))  # Yıllık volatilite - scalar'a çevir
        avg_volume = float(data['Volume'].mean())  # scalar'a çevir
        price_range = float((data['Close'].max() - data['Close'].min()) / data['Close'].mean())
        
        # Trend analizi
        sma_20 = data['Close'].rolling(20).mean()
        sma_50 = data['Close'].rolling(50).mean()
        trend_strength = float(abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1])
        
        # Parametre önerileri
        if volatility > 0.4:  # Yüksek volatilite
            model_complexity = "Basit"
            risk_level = "Konservatif"
            max_depth = 3
            learning_rate = 0.03
            stop_loss = 0.15
            take_profit = 0.25
        elif volatility > 0.25:  # Orta volatilite
            model_complexity = "Orta"
            risk_level = "Orta"
            max_depth = 4
            learning_rate = 0.05
            stop_loss = 0.20
            take_profit = 0.30
        else:  # Düşük volatilite
            model_complexity = "Karmaşık"
            risk_level = "Agresif"
            max_depth = 6
            learning_rate = 0.08
            stop_loss = 0.25
            take_profit = 0.40
            
        # Hacim analizi
        if avg_volume > 10000000:  # Yüksek hacim
            max_daily_trades = 3
            confidence_threshold = 0.55
        elif avg_volume > 5000000:  # Orta hacim
            max_daily_trades = 2
            confidence_threshold = 0.60
        else:  # Düşük hacim
            max_daily_trades = 1
            confidence_threshold = 0.65
            
        return {
            'volatility': volatility,
            'avg_volume': avg_volume,
            'price_range': price_range,
            'trend_strength': trend_strength,
            'recommendations': {
                'model_complexity': model_complexity,
                'risk_level': risk_level,
                'max_depth': max_depth,
                'learning_rate': learning_rate,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'max_daily_trades': max_daily_trades,
                'confidence_threshold': confidence_threshold
            }
        }
    except Exception as e:
        st.error(f"Hisse analizi hatası: {str(e)}")
        return None

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="Hisse Senedi Yön Tahmini",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS stilleri
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_config():
    """Konfigürasyonu yükler"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except:
        return {}

@st.cache_data(ttl=300)  # 5 dakika cache
def load_stock_data(symbol, period="1y"):
    """Hisse verisi yükler - API call ile cache'li"""
    try:
        import yfinance as yf
        import os
        
        # Cache dosya yolu
        cache_dir = "data/raw"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{symbol.replace('.IS', '')}_cache.csv")
        
        # Cache kontrolü
        if os.path.exists(cache_file):
            import time
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < 300:  # 5 dakikadan yeni
                try:
                    data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    st.sidebar.success(f"📦 Cache'den yüklendi: {symbol}")
                    return data
                except:
                    pass
        
        # API'den veri çek
        st.sidebar.info(f"🌐 API'den yükleniyor: {symbol}")
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        
        if data.empty:
            st.sidebar.error(f"❌ Veri bulunamadı: {symbol}")
            return pd.DataFrame()
        
        # Kolon isimlerini standardize et
        data.columns = [col.lower() for col in data.columns]
        data = data.rename(columns={'adj close': 'adj_close'})
        data = data.dropna()
        
        # Cache'e kaydet
        data.to_csv(cache_file)
        st.sidebar.success(f"✅ Veri yüklendi ve cache'lendi: {symbol}")
        
        return data
        
    except Exception as e:
        st.sidebar.error(f"❌ Veri yükleme hatası {symbol}: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def create_features(data):
    """Özellikler oluşturur"""
    try:
        engineer = FeatureEngineer(load_config())
        return engineer.create_all_features(data)
    except:
        return pd.DataFrame()

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

def main():
    """Ana dashboard"""
    
    # Başlık
    st.markdown('<h1 class="main-header">📈 Hisse Senedi Yön Tahmini Sistemi</h1>', 
                unsafe_allow_html=True)
    
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
        placeholder="örn: FONET.IS",
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
    
    # Ana içerik
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Veri Analizi", "🤖 Model Tahminleri", "📈 Backtest", "💼 Paper Trading", "🎯 Model Eğitimi"])
    
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
        selected_model = st.selectbox("Model Seçin:", model_files, index=0)
        
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
    
    with tab3:
        st.header("📈 Backtest Sonuçları")
        
        if not model_files:
            st.warning("Backtest için model gerekli!")
            return
        
        # En son modeli otomatik seç
        model_files.sort(reverse=True)  # En yeni modeli başa al
        selected_model = st.selectbox("Backtest Modeli:", model_files, key="backtest_model", index=0)
        
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
    
    with tab4:
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
            action = st.selectbox("İşlem Türü:", ["BUY", "SELL"])
        
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
    
    with tab5:
        st.header("🎯 Akıllı Model Eğitimi")
        
        # Hisse seçimi ve analiz
        stock_options = all_symbols  # Ana dropdown'daki tüm hisseleri kullan
        selected_stock = st.selectbox("📊 Eğitim için Hisse Seçin:", stock_options)
        
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
        
        # Parametre ayarları
        st.subheader("⚙️ Parametre Ayarları")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🔧 Model Parametreleri:**")
            
            # Basit parametreler
            model_complexity = st.selectbox(
                "Model Karmaşıklığı:", 
                ["Basit", "Orta", "Karmaşık"],
                help="Basit: Hızlı eğitim, az overfitting\nOrta: Dengeli performans\nKarmaşık: Detaylı analiz, uzun eğitim"
            )
            
            risk_level = st.selectbox(
                "Risk Seviyesi:",
                ["Konservatif", "Orta", "Agresif"],
                help="Konservatif: Düşük risk, küçük kar/zarar\nOrta: Dengeli risk\nAgresif: Yüksek risk, büyük kar/zarar"
            )
            
            # Teknik parametreler (gelişmiş kullanıcılar için)
            with st.expander("🔬 Gelişmiş Parametreler"):
                max_depth = st.slider(
                    "Max Depth:", 3, 10, 
                    value=recommendations['max_depth'] if analysis else 4,
                    help="Ağaç derinliği. Yüksek değer = karmaşık model"
                )
                learning_rate = st.slider(
                    "Learning Rate:", 0.01, 0.3, 
                    value=recommendations['learning_rate'] if analysis else 0.05,
                    step=0.01,
                    help="Öğrenme hızı. Düşük = yavaş ama kararlı"
                )
                n_estimators = st.slider(
                    "N Estimators:", 50, 500, 200,
                    help="Ağaç sayısı. Fazla = uzun eğitim"
                )
                subsample = st.slider(
                    "Subsample:", 0.5, 1.0, 0.7, 0.1,
                    help="Her ağaç için kullanılan veri oranı"
                )
        
        with col2:
            st.write("**🛡️ Risk Yönetimi:**")
            
            max_position_size = st.slider(
                "Maksimum Pozisyon (%):", 0.01, 1.0, 0.8, 0.01,
                help="Sermayenin ne kadarını kullanabilir"
            )
            
            stop_loss_pct = st.slider(
                "Stop Loss (%):", 0.05, 0.5, 
                value=recommendations['stop_loss'] if analysis else 0.4,
                step=0.01,
                help="Maksimum kayıp toleransı"
            )
            
            take_profit_pct = st.slider(
                "Take Profit (%):", 0.1, 1.0, 
                value=recommendations['take_profit'] if analysis else 0.8,
                step=0.01,
                help="Hedef kar oranı"
            )
            
            max_daily_trades = st.slider(
                "Günlük Maksimum İşlem:", 1, 10, 
                value=recommendations['max_daily_trades'] if analysis else 1,
                help="Günde kaç işlem yapabilir"
            )
        
        # Model ismi
        model_name = st.text_input(
            "📝 Model İsmi:", 
            value=f"{selected_stock.replace('.IS', '')}_Model",
            help="Modeli kaydetmek için benzersiz isim"
        )
        
        # Eğitim parametreleri
        st.subheader("📊 Eğitim Ayarları")
        
        col3, col4 = st.columns(2)
        
        with col3:
            period = st.selectbox(
                "Veri Periyodu:", ["1y", "2y", "5y"], index=1,
                help="Ne kadar geçmiş veri kullanılacak"
            )
            train_test_split = st.slider(
                "Train/Test Split:", 0.7, 0.9, 0.8, 0.05,
                help="Verinin ne kadarını eğitim için kullan"
            )
        
        with col4:
            min_volume_threshold = st.number_input(
                "Min Volume Threshold:", value=1000000,
                help="Minimum hacim filtresi"
            )
            confidence_threshold = st.slider(
                "Confidence Threshold:", 0.5, 0.9, 
                value=recommendations['confidence_threshold'] if analysis else 0.6,
                step=0.05,
                help="İşlem için minimum güven skoru"
            )
        
        # Dinamik parametre önerisi
        if analysis:
            st.subheader("🎯 Dinamik Parametre Önerisi")
            
            volatility = analysis['volatility']
            if volatility > 0.6:  # Yüksek volatilite (FONET gibi)
                st.warning(f"🔥 Yüksek Volatilite (%{volatility*100:.1f}) - Özel Parametreler:")
                st.code(f"""
# FONET için önerilen parametreler:
Güven Eşiği: 0.45 (düşük)
Stop Loss: %25 (geniş)
Take Profit: %40 (büyük)
Pozisyon: %5-10 (küçük)
Günlük İşlem: 1-2 (az)
Model Karmaşıklığı: Basit (overfitting önleme)
                """)
            elif volatility > 0.4:
                st.info(f"⚠️ Orta-Yüksek Volatilite (%{volatility*100:.1f})")
            else:
                st.success(f"✅ Düşük Volatilite (%{volatility*100:.1f}) - Standart parametreler uygun")
        
        # Akıllı parametre önerisi
        if analysis:
            volatility = analysis['volatility']
            
            # Volatiliteye göre otomatik parametre önerisi
            if volatility > 0.6:  # Yüksek volatilite
                st.warning(f"🔥 Yüksek Volatilite (%{volatility*100:.1f}) - Konservatif parametreler öneriliyor")
                auto_params = {
                    'confidence': 0.45,
                    'stop_loss': 0.25,
                    'take_profit': 0.40,
                    'position_size': 0.10,
                    'max_trades': 2,
                    'max_depth': 3,
                    'learning_rate': 0.03
                }
            elif volatility > 0.4:  # Orta-yüksek volatilite
                st.info(f"⚠️ Orta-Yüksek Volatilite (%{volatility*100:.1f}) - Dengeli parametreler")
                auto_params = {
                    'confidence': 0.50,
                    'stop_loss': 0.20,
                    'take_profit': 0.35,
                    'position_size': 0.15,
                    'max_trades': 3,
                    'max_depth': 4,
                    'learning_rate': 0.05
                }
            else:  # Düşük volatilite
                st.success(f"✅ Düşük Volatilite (%{volatility*100:.1f}) - Agresif parametreler")
                auto_params = {
                    'confidence': 0.60,
                    'stop_loss': 0.15,
                    'take_profit': 0.30,
                    'position_size': 0.20,
                    'max_trades': 5,
                    'max_depth': 6,
                    'learning_rate': 0.08
                }
            
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
                    
                    # Tam konfigürasyonu oluştur (dinamik parametrelerle)
                    full_config = {
                        'MODEL_CONFIG': {
                            'max_depth': dynamic_max_depth,  # Dinamik
                            'learning_rate': dynamic_learning_rate,  # Dinamik
                            'n_estimators': n_estimators,
                            'subsample': subsample,
                            'colsample_bytree': 0.7,
                            'min_child_weight': 5,
                            'reg_alpha': 0.1,
                            'reg_lambda': 0.1,
                            'random_state': 42,
                            'n_jobs': -1
                        },
                        'RISK_MANAGEMENT': {
                            'max_position_size': dynamic_position_size,  # Dinamik
                            'stop_loss_pct': dynamic_stop_loss,  # Dinamik
                            'take_profit_pct': dynamic_take_profit,  # Dinamik
                            'max_daily_trades': dynamic_max_trades,  # Dinamik
                            'confidence_threshold': dynamic_confidence  # Dinamik güven eşiği
                        },
                        'DATA_CONFIG': {
                            'train_test_split': train_test_split,
                            'min_volume_threshold': min_volume_threshold
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
                    data = data_loader.fetch_stock_data(selected_stock, period)
                    
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
                    model_path = predictor.save_model(f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib")
                    
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
                    
                    # Feature importance
                    if 'feature_importance' in results:
                        st.subheader("🔍 En Önemli Özellikler")
                        importance_df = results['feature_importance'].head(10)
                        
                        fig = px.bar(
                            importance_df, 
                            x='importance', 
                            y='feature',
                            orientation='h',
                            title="Top 10 Feature Importance"
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    
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
                            
                            # Backtest sonuçları - Anlaşılır format
                            st.subheader("📈 Backtest Sonuçları")
                            
                            total_return = backtest_results['total_return']
                            win_rate = backtest_results['win_rate']
                            sharpe_ratio = backtest_results['sharpe_ratio']
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if total_return > 50:
                                    st.success(f"🚀 Model Getirisi: +%{total_return:.1f}")
                                elif total_return > 20:
                                    st.warning(f"📈 Model Getirisi: +%{total_return:.1f}")
                                elif total_return > 0:
                                    st.info(f"📊 Model Getirisi: +%{total_return:.1f}")
                                else:
                                    st.error(f"📉 Model Getirisi: %{total_return:.1f}")
                                
                            with col2:
                                if win_rate > 70:
                                    st.success(f"🎯 Kazanma Oranı: %{win_rate:.1f}")
                                elif win_rate > 60:
                                    st.warning(f"⚖️ Kazanma Oranı: %{win_rate:.1f}")
                                else:
                                    st.error(f"❌ Kazanma Oranı: %{win_rate:.1f}")
                            
                            with col3:
                                if sharpe_ratio > 2:
                                    st.success(f"⭐ Risk/Getiri: Mükemmel ({sharpe_ratio:.2f})")
                                elif sharpe_ratio > 1:
                                    st.warning(f"📊 Risk/Getiri: İyi ({sharpe_ratio:.2f})")
                                else:
                                    st.error(f"⚠️ Risk/Getiri: Zayıf ({sharpe_ratio:.2f})")
                            
                            # Buy & Hold karşılaştırması
                            try:
                                # Buy & Hold hesapla
                                data = yf.download(selected_stock, period="2y", progress=False)
                                if not data.empty:
                                    initial_price = data['Close'].iloc[0]
                                    final_price = data['Close'].iloc[-1]
                                    buy_hold_return = ((final_price - initial_price) / initial_price) * 100
                                    
                                    st.subheader("🏆 Buy & Hold Karşılaştırması")
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.metric("Buy & Hold Getirisi", f"%{buy_hold_return:.1f}")
                                    
                                    with col2:
                                        outperformance = total_return - buy_hold_return
                                        if outperformance > 0:
                                            st.success(f"🎉 Model {outperformance:.1f}% daha iyi!")
                                        else:
                                            st.error(f"📉 Model {abs(outperformance):.1f}% daha kötü")
                            except:
                                pass
                                
                                # Sermaye eğrisi
                                if 'equity_curve' in backtest_results:
                                    equity_df = backtest_results['equity_curve']
                                    
                                    fig = go.Figure()
                                    fig.add_trace(go.Scatter(
                                        x=equity_df.index,
                                        y=equity_df['equity'],
                                        mode='lines',
                                        name='Sermaye',
                                        line=dict(color='blue', width=2)
                                    ))
                                    
                                    fig.update_layout(
                                        title="Sermaye Eğrisi",
                                        xaxis_title="Tarih",
                                        yaxis_title="Sermaye (TL)",
                                        height=400
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                
                            except Exception as e:
                                st.error(f"Backtest hatası: {str(e)}")
                    
                except Exception as e:
                    st.error(f"Model eğitimi hatası: {str(e)}")

if __name__ == "__main__":
    main()
