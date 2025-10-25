"""
Dashboard Yardımcı Fonksiyonları
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yaml
import os
from datetime import datetime
import yfinance as yf

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

def analyze_stock_characteristics(symbol, period="2y"):
    """Hisse karakteristiklerini analiz eder ve parametre önerileri döndürür"""
    try:
        # Veri yükle
        data = yf.download(symbol, period=period, progress=False)
        if data.empty:
            return None
            
        # Temel istatistikler
        returns = data['Close'].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252))  # Yıllık volatilite
        avg_volume = float(data['Volume'].mean())
        price_range = float((data['Close'].max() - data['Close'].min()) / data['Close'].mean())
        
        # Volatilite kategorisi belirle
        if volatility <= 0.25:
            volatility_category = "Düşük"
            volatility_color = "green"
        elif volatility <= 0.40:
            volatility_category = "Orta"
            volatility_color = "orange"
        elif volatility <= 0.60:
            volatility_category = "Yüksek"
            volatility_color = "red"
        else:
            volatility_category = "Çok Yüksek"
            volatility_color = "darkred"
        
        # Trend analizi
        sma_20 = data['Close'].rolling(20).mean()
        sma_50 = data['Close'].rolling(50).mean()
        trend_strength = float(abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1])
        
        # Parametre önerileri (volatilite bazlı)
        if volatility > 0.6:  # Çok yüksek volatilite
            model_complexity = "Çok Basit"
            risk_level = "Çok Konservatif"
            max_depth = 2
            learning_rate = 0.01
            stop_loss = 0.12
            take_profit = 0.25
            confidence_threshold = 0.35
        elif volatility > 0.4:  # Yüksek volatilite
            model_complexity = "Basit"
            risk_level = "Konservatif"
            max_depth = 2
            learning_rate = 0.02
            stop_loss = 0.08
            take_profit = 0.15
            confidence_threshold = 0.45
        elif volatility > 0.25:  # Orta volatilite
            model_complexity = "Orta"
            risk_level = "Orta"
            max_depth = 3
            learning_rate = 0.05
            stop_loss = 0.20
            take_profit = 0.30
            confidence_threshold = 0.55
        else:  # Düşük volatilite
            model_complexity = "Karmaşık"
            risk_level = "Agresif"
            max_depth = 4
            learning_rate = 0.05
            stop_loss = 0.03
            take_profit = 0.06
            confidence_threshold = 0.60
            
        # Hacim analizi
        if avg_volume > 10000000:  # Yüksek hacim
            max_daily_trades = 3
        elif avg_volume > 5000000:  # Orta hacim
            max_daily_trades = 2
        else:  # Düşük hacim
            max_daily_trades = 1
            
        return {
            'volatility': volatility,
            'volatility_category': volatility_category,
            'volatility_color': volatility_color,
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

def get_auto_params(volatility):
    """Volatiliteye göre otomatik parametreler döndürür - Gelecek tahmin odaklı"""
    if volatility > 0.6:  # Yüksek volatilite (FONET gibi)
        return {
            'confidence': 0.20,  # Daha düşük eşik - daha fazla sinyal
            'stop_loss': 0.25,  # Daha dar stop loss
            'take_profit': 0.40,  # Daha küçük take profit
            'position_size': 0.08,  # Daha büyük pozisyon
            'max_trades': 2,  # Günde 2 işlem
            'max_depth': 3,  # Biraz daha karmaşık model
            'learning_rate': 0.01,  # Biraz daha hızlı öğrenme
            'n_estimators': 50,  # Daha fazla ağaç
            'subsample': 0.6,  # Daha yüksek subsample
            'colsample_bytree': 0.6,  # Daha yüksek feature sampling
            'reg_alpha': 0.5,  # Daha az L1 regularization
            'reg_lambda': 0.5,  # Daha az L2 regularization
            'min_child_weight': 10,  # Daha düşük min_child_weight
            'early_stopping_rounds': 15,  # Daha az erken durma
            'validation_fraction': 0.2  # Daha fazla validation
        }
    elif volatility > 0.4:  # Orta-yüksek volatilite
        return {
            'confidence': 0.30,  # Daha düşük eşik
            'stop_loss': 0.20,
            'take_profit': 0.35,
            'position_size': 0.12,
            'max_trades': 3,
            'max_depth': 4,
            'learning_rate': 0.02,
            'n_estimators': 80,
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'reg_alpha': 0.3,
            'reg_lambda': 0.3,
            'min_child_weight': 8,
            'early_stopping_rounds': 20,
            'validation_fraction': 0.2
        }
    else:  # Düşük volatilite
        return {
            'confidence': 0.40,  # Orta eşik
            'stop_loss': 0.15,
            'take_profit': 0.30,
            'position_size': 0.18,
            'max_trades': 4,
            'max_depth': 5,
            'learning_rate': 0.03,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.2,
            'reg_lambda': 0.2,
            'min_child_weight': 5,
            'early_stopping_rounds': 25,
            'validation_fraction': 0.2
        }
