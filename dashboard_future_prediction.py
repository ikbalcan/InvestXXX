"""
Gelecek Tahmin Tab - Dashboard Modülü
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
import json

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from price_target_predictor import PriceTargetPredictor
from dashboard_utils import load_config, load_stock_data
from src.export_utils import create_export_buttons

@st.cache_data
def create_features(data, config=None, interval="1d"):
    """Özellikler oluşturur"""
    try:
        if config is None:
            config = load_config()
        
        # Interval'ı config'e ekle
        if 'MODEL_CONFIG' not in config:
            config['MODEL_CONFIG'] = {}
        config['MODEL_CONFIG']['interval'] = interval
        
        engineer = FeatureEngineer(config)
        return engineer.create_all_features(data)
    except:
        return pd.DataFrame()

def remove_duplicate_factors(factors):
    """Tekrar eden faktörleri temizler"""
    seen = set()
    clean_factors = {
        'positive': [],
        'negative': [],
        'neutral': []
    }
    
    for category in ['positive', 'negative', 'neutral']:
        for factor in factors[category]:
            # Emoji ve sayıları temizle, karşılaştırma için normalize et
            normalized = factor.split(' - ')[-1].lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                clean_factors[category].append(factor)
    
    return clean_factors

def analyze_prediction_factors(data, features_df, prediction, confidence, model_metrics):
    """
    Tahminin hangi faktörlere dayandığını analiz eder
    """
    factors = {
        'positive': [],
        'negative': [],
        'neutral': []
    }
    
    if features_df.empty or len(features_df) < 10:
        return factors
    
    # Son günün verilerini al
    last_data = features_df.iloc[-1]
    recent_data = features_df.tail(5)
    
    # 1. Teknik Göstergeler Analizi
    if 'rsi' in features_df.columns:
        rsi = last_data['rsi']
        if rsi < 30:
            if prediction == 1:  # AL sinyali
                factors['positive'].append(f"RSI aşırı satım seviyesinde ({rsi:.1f}) - Yükseliş sinyali")
            else:
                factors['negative'].append(f"RSI aşırı satım seviyesinde ({rsi:.1f}) - Düşüş riski")
        elif rsi > 70:
            if prediction == 0:  # SAT sinyali
                factors['positive'].append(f"RSI aşırı alım seviyesinde ({rsi:.1f}) - Düşüş sinyali")
            else:
                factors['negative'].append(f"RSI aşırı alım seviyesinde ({rsi:.1f}) - Yükseliş riski")
        else:
            factors['neutral'].append(f"RSI normal seviyede ({rsi:.1f})")
    
    # 2. Hareketli Ortalamalar Analizi
    if 'sma_20' in features_df.columns and 'sma_50' in features_df.columns:
        sma_20 = last_data['sma_20']
        sma_50 = last_data['sma_50']
        current_price = last_data['close']
        
        if sma_20 > sma_50:
            if prediction == 1:
                factors['positive'].append(f"📈 Yükseliş trendi - Kısa vadeli ortalama uzun vadeli ortalamanın üzerinde")
            else:
                factors['negative'].append(f"⚠️ Trend tersine dönebilir - Yükseliş trendi zayıflayabilir")
    else:
        if prediction == 0:
            factors['positive'].append(f"📉 Düşüş trendi - Kısa vadeli ortalama uzun vadeli ortalamanın altında")
        else:
            factors['negative'].append(f"⚠️ Düşüş trendi var - Yükseliş önünde engel")
    
    # 3. Hacim Analizi
    if 'volume' in features_df.columns:
        recent_volume = recent_data['volume'].mean()
        avg_volume = features_df['volume'].tail(20).mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 1.5:
            if prediction == 1:
                factors['positive'].append(f"Hacim ortalamadan %{(volume_ratio-1)*100:.0f} yüksek - Güçlü yükseliş sinyali")
            else:
                factors['positive'].append(f"Hacim ortalamadan %{(volume_ratio-1)*100:.0f} yüksek - Güçlü düşüş sinyali")
        elif volume_ratio < 0.7:
            factors['negative'].append(f"Hacim ortalamadan %{(1-volume_ratio)*100:.0f} düşük - Zayıf sinyal")
        else:
            factors['neutral'].append(f"Hacim normal seviyede")
    
    # 4. Fiyat Momentum Analizi
    if len(recent_data) >= 3:
        price_change_3d = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[-3]) / recent_data['close'].iloc[-3]
        
        if price_change_3d > 0.03:  # %3'ten fazla artış
            if prediction == 1:
                factors['positive'].append(f"🚀 Son 3 günde güçlü artış - Yükseliş momentumu devam ediyor")
            else:
                factors['negative'].append(f"⚠️ Son 3 günde güçlü artış - Aşırı alım riski")
        elif price_change_3d < -0.03:  # %3'ten fazla düşüş
            if prediction == 0:
                factors['positive'].append(f"📉 Son 3 günde güçlü düşüş - Düşüş momentumu devam ediyor")
            else:
                factors['negative'].append(f"⚠️ Son 3 günde güçlü düşüş - Yükseliş için olumsuz")
        else:
            factors['neutral'].append(f"📊 Son 3 günde fiyat stabil - Belirsizlik")
    
    # 5. Volatilite Analizi
    if len(recent_data) >= 10:
        recent_volatility = recent_data['close'].pct_change().std() * np.sqrt(252)
        long_term_volatility = features_df['close'].pct_change().std() * np.sqrt(252)
        
        if recent_volatility > long_term_volatility * 1.3:
            factors['negative'].append(f"🌪️ Yüksek volatilite - Fiyat dalgalanması riski artıyor")
        elif recent_volatility < long_term_volatility * 0.7:
            factors['positive'].append(f"🛡️ Düşük volatilite - Stabil ve güvenli hareket")
        else:
            factors['neutral'].append(f"📊 Normal volatilite seviyesi")
    
    # 6. Model Güvenilirliği Analizi
    accuracy = model_metrics.get('test_metrics', {}).get('accuracy', 0.5)
    f1_score = model_metrics.get('test_metrics', {}).get('f1_score', 0.5)
    
    if accuracy > 0.7 and f1_score > 0.6:
        factors['positive'].append(f"🎯 Model yüksek doğrulukta - Güvenilir tahmin")
    elif accuracy < 0.6 or f1_score < 0.5:
        factors['negative'].append(f"⚠️ Model düşük doğrulukta - Riskli tahmin")
    else:
        factors['neutral'].append(f"📊 Model orta doğrulukta")
    
    # 7. Güven Skoru Analizi
    if confidence > 0.8:
        factors['positive'].append(f"💪 Çok yüksek güven skoru - Güçlü sinyal")
    elif confidence > 0.6:
        factors['neutral'].append(f"📊 Orta güven skoru")
    else:
        factors['negative'].append(f"⚠️ Düşük güven skoru - Zayıf sinyal")
    
    # 8. Destek/Direnç Analizi
    if len(data) >= 20:
        recent_high = data['high'].tail(20).max()
        recent_low = data['low'].tail(20).min()
        current_price = data['close'].iloc[-1]
        
        # Destek seviyesine yakınlık
        support_distance = (current_price - recent_low) / current_price
        resistance_distance = (recent_high - current_price) / current_price
        
        if support_distance < 0.05:  # %5'ten yakın
            if prediction == 1:
                factors['positive'].append(f"🛡️ Destek seviyesine yakın - Güçlü yükseliş potansiyeli")
            else:
                factors['negative'].append(f"⚠️ Destek seviyesine yakın - Kırılma riski")
        
        if resistance_distance < 0.05:  # %5'ten yakın
            if prediction == 0:
                factors['positive'].append(f"🚧 Direnç seviyesine yakın - Güçlü düşüş potansiyeli")
            else:
                factors['negative'].append(f"🚧 Direnç seviyesine yakın - Yükseliş engeli")
    
    # 9. MACD Analizi
    if 'macd' in features_df.columns and 'macd_signal' in features_df.columns:
        macd = last_data['macd']
        macd_signal = last_data['macd_signal']
        
        if macd > macd_signal:
            if prediction == 1:
                factors['positive'].append(f"MACD sinyal çizgisinin üzerinde - Yükseliş momentumu")
            else:
                factors['negative'].append(f"MACD sinyal çizgisinin üzerinde - Momentum zayıflayabilir")
        else:
            if prediction == 0:
                factors['positive'].append(f"MACD sinyal çizgisinin altında - Düşüş momentumu")
            else:
                factors['positive'].append(f"MACD sinyal çizgisinin altında - Momentum tersine dönebilir")
    
    # 10. Bollinger Bands Analizi
    if 'bb_upper' in features_df.columns and 'bb_lower' in features_df.columns:
        bb_upper = last_data['bb_upper']
        bb_lower = last_data['bb_lower']
        bb_middle = (bb_upper + bb_lower) / 2
        
        if current_price > bb_upper:
            if prediction == 0:
                factors['positive'].append(f"Bollinger üst bandının üzerinde - Aşırı alım, düşüş sinyali")
            else:
                factors['negative'].append(f"Bollinger üst bandının üzerinde - Aşırı alım riski")
        elif current_price < bb_lower:
            if prediction == 1:
                factors['positive'].append(f"Bollinger alt bandının altında - Aşırı satım, yükseliş sinyali")
            else:
                factors['negative'].append(f"Bollinger alt bandının altında - Aşırı satım riski")
        else:
            factors['neutral'].append(f"Bollinger bantları içinde - Normal seviye")
    
    # 11. Stochastic Analizi
    if 'stoch_k' in features_df.columns and 'stoch_d' in features_df.columns:
        stoch_k = last_data['stoch_k']
        stoch_d = last_data['stoch_d']
        
        if stoch_k > 80 and stoch_d > 80:
            if prediction == 0:
                factors['positive'].append(f"Stochastic aşırı alım seviyesinde ({stoch_k:.1f}) - Düşüş sinyali")
            else:
                factors['negative'].append(f"Stochastic aşırı alım seviyesinde ({stoch_k:.1f}) - Risk")
        elif stoch_k < 20 and stoch_d < 20:
            if prediction == 1:
                factors['positive'].append(f"Stochastic aşırı satım seviyesinde ({stoch_k:.1f}) - Yükseliş sinyali")
            else:
                factors['negative'].append(f"Stochastic aşırı satım seviyesinde ({stoch_k:.1f}) - Risk")
    
    # 12. Williams %R Analizi
    if 'williams_r' in features_df.columns:
        williams_r = last_data['williams_r']
        
        if williams_r > -20:
            if prediction == 0:
                factors['positive'].append(f"Williams %R aşırı alım ({williams_r:.1f}) - Düşüş sinyali")
            else:
                factors['negative'].append(f"Williams %R aşırı alım ({williams_r:.1f}) - Risk")
        elif williams_r < -80:
            if prediction == 1:
                factors['positive'].append(f"Williams %R aşırı satım ({williams_r:.1f}) - Yükseliş sinyali")
            else:
                factors['negative'].append(f"Williams %R aşırı satım ({williams_r:.1f}) - Risk")
    
    # 13. CCI (Commodity Channel Index) Analizi
    if 'cci' in features_df.columns:
        cci = last_data['cci']
        
        if cci > 100:
            if prediction == 0:
                factors['positive'].append(f"CCI aşırı alım ({cci:.1f}) - Düşüş sinyali")
            else:
                factors['negative'].append(f"CCI aşırı alım ({cci:.1f}) - Risk")
        elif cci < -100:
            if prediction == 1:
                factors['positive'].append(f"CCI aşırı satım ({cci:.1f}) - Yükseliş sinyali")
            else:
                factors['negative'].append(f"CCI aşırı satım ({cci:.1f}) - Risk")
    
    # 14. ADX (Average Directional Index) Analizi
    if 'adx' in features_df.columns:
        adx = last_data['adx']
        
        if adx > 25:
            factors['positive'].append(f"ADX güçlü trend ({adx:.1f}) - Momentum devam edecek")
        elif adx < 20:
            factors['negative'].append(f"ADX zayıf trend ({adx:.1f}) - Momentum kaybolabilir")
        else:
            factors['neutral'].append(f"ADX orta trend ({adx:.1f})")
    
    # 15. OBV (On-Balance Volume) Analizi
    if 'obv' in features_df.columns and len(features_df) >= 5:
        obv_trend = features_df['obv'].tail(5).pct_change().mean()
        
        if obv_trend > 0.02:
            if prediction == 1:
                factors['positive'].append(f"OBV artış trendi - Güçlü alım baskısı")
            else:
                factors['negative'].append(f"OBV artış trendi - Alım baskısı riski")
        elif obv_trend < -0.02:
            if prediction == 0:
                factors['positive'].append(f"OBV düşüş trendi - Güçlü satım baskısı")
            else:
                factors['negative'].append(f"OBV düşüş trendi - Satım baskısı riski")
    
    # 16. Price Action Analizi
    if len(recent_data) >= 3:
        # Son 3 günün kapanış fiyatları
        closes = recent_data['close'].tail(3).values
        
        # Yükseliş/azalış kalıbı
        if closes[0] < closes[1] < closes[2]:  # 3 gün üst üste artış
            if prediction == 1:
                factors['positive'].append(f"3 gün üst üste artış - Güçlü yükseliş kalıbı")
            else:
                factors['negative'].append(f"3 gün üst üste artış - Aşırı alım riski")
        elif closes[0] > closes[1] > closes[2]:  # 3 gün üst üste düşüş
            if prediction == 0:
                factors['positive'].append(f"3 gün üst üste düşüş - Güçlü düşüş kalıbı")
            else:
                factors['negative'].append(f"⚠️ 3 gün üst üste düşüş - Yükseliş için olumsuz")
    
    # 17. Gap Analizi
    if len(data) >= 2:
        gap = (data['open'].iloc[-1] - data['close'].iloc[-2]) / data['close'].iloc[-2]
        
        if gap > 0.02:  # %2'den büyük gap
            if prediction == 1:
                factors['positive'].append(f"Yukarı gap (%{gap*100:.1f}) - Güçlü yükseliş sinyali")
            else:
                factors['negative'].append(f"Yukarı gap (%{gap*100:.1f}) - Aşırı alım riski")
        elif gap < -0.02:  # %2'den büyük gap
            if prediction == 0:
                factors['positive'].append(f"Aşağı gap (%{abs(gap)*100:.1f}) - Güçlü düşüş sinyali")
            else:
                factors['negative'].append(f"⚠️ Aşağı gap (%{abs(gap)*100:.1f}) - Yükseliş için olumsuz")
    
    # 18. Modelin Gerçek Özelliklerini Analiz Et - Kullanıcı Dostu
    if not features_df.empty:
        # Momentum özellikleri - Kullanıcı dostu açıklamalar
        momentum_features = [col for col in features_df.columns if 'momentum' in col.lower() or 'roc' in col.lower()]
        if momentum_features:
            for feature in momentum_features[:3]:  # İlk 3 momentum özelliği
                if feature in last_data.index:
                    value = last_data[feature]
                    if abs(value) > 0.05:  # %5'ten büyük momentum
                        if prediction == 1 and value > 0:
                            factors['positive'].append(f"📈 Güçlü yükseliş momentumu - Fiyat hızla artıyor")
                        elif prediction == 0 and value < 0:
                            factors['positive'].append(f"📉 Güçlü düşüş momentumu - Fiyat hızla düşüyor")
                        else:
                            factors['negative'].append(f"⚠️ Momentum tersine dönebilir - Trend riski")
        
        # Volatilite özellikleri - Kullanıcı dostu açıklamalar (sadece 1 kez ekle)
        volatility_features = [col for col in features_df.columns if 'volatility' in col.lower() or 'std' in col.lower()]
        if volatility_features:
            for feature in volatility_features[:1]:  # Sadece 1 volatilite özelliği
                if feature in last_data.index:
                    value = last_data[feature]
                    if value > 0.3:  # Yüksek volatilite
                        factors['negative'].append(f"🌪️ Yüksek volatilite - Fiyat dalgalanması riski")
                    elif value < 0.1:  # Düşük volatilite
                        factors['positive'].append(f"🛡️ Düşük volatilite - Stabil ve güvenli hareket")
        
        # Fiyat özellikleri - Kullanıcı dostu açıklamalar
        price_features = [col for col in features_df.columns if 'price' in col.lower() and 'change' in col.lower()]
        if price_features:
            for feature in price_features[:2]:  # İlk 2 fiyat değişim özelliği
                if feature in last_data.index:
                    value = last_data[feature]
                    if abs(value) > 0.02:  # %2'den büyük değişim
                        if prediction == 1 and value > 0:
                            factors['positive'].append(f"🚀 Son günlerde güçlü fiyat artışı - Trend devam edecek")
                        elif prediction == 0 and value < 0:
                            factors['positive'].append(f"📉 Son günlerde güçlü fiyat düşüşü - Trend devam edecek")
                        else:
                            factors['negative'].append(f"🔄 Fiyat hareketi tersine dönebilir - Trend riski")
        
        # Hacim özellikleri - Kullanıcı dostu açıklamalar
        volume_features = [col for col in features_df.columns if 'volume' in col.lower() and 'ratio' in col.lower()]
        if volume_features:
            for feature in volume_features[:1]:  # Sadece 1 hacim özelliği
                if feature in last_data.index:
                    value = last_data[feature]
                    if value > 1.5:  # Ortalamadan %50 fazla hacim
                        if prediction == 1:
                            factors['positive'].append(f"💰 Yüksek işlem hacmi - Güçlü alım ilgisi")
                        else:
                            factors['positive'].append(f"💸 Yüksek işlem hacmi - Güçlü satım baskısı")
                    elif value < 0.5:  # Ortalamadan %50 az hacim
                        factors['negative'].append(f"😴 Düşük işlem hacmi - Zayıf piyasa katılımı")
        
        # Zaman özellikleri - Kullanıcı dostu açıklamalar (sadece 1 kez ekle)
        time_features = [col for col in features_df.columns if 'day' in col.lower() or 'week' in col.lower() or 'month' in col.lower()]
        if time_features:
            for feature in time_features[:1]:  # Sadece 1 zaman özelliği
                if feature in last_data.index:
                    value = last_data[feature]
                    if value > 0.5:  # Pozitif zaman etkisi
                        factors['positive'].append(f"📅 Zaman avantajı - Bu dönemde genelde pozitif performans")
                    elif value < -0.5:  # Negatif zaman etkisi
                        factors['negative'].append(f"📅 Zaman dezavantajı - Bu dönemde genelde negatif performans")
    
    # Tekrar eden faktörleri temizle
    factors = remove_duplicate_factors(factors)
    
    return factors

def train_model_for_symbol(symbol, config, progress_callback=None, interval="1d", investment_horizon="MEDIUM_TERM"):
    """Tek hisse için model eğitimi"""
    try:
        if progress_callback:
            progress_callback(f"📊 {symbol} verisi yükleniyor...")
        
        # Veri yükle
        data = load_stock_data(symbol, "2y", interval=interval)
        if data.empty:
            return False, f"{symbol} verisi yüklenemedi"
        
        if progress_callback:
            progress_callback(f"🔧 {symbol} özellikler oluşturuluyor...")
        
        # Özellikler oluştur
        try:
            # Interval ve investment_horizon'ı config'e ekle
            config_with_interval = config.copy()
            if 'MODEL_CONFIG' not in config_with_interval:
                config_with_interval['MODEL_CONFIG'] = {}
            config_with_interval['MODEL_CONFIG']['interval'] = interval
            config_with_interval['MODEL_CONFIG']['investment_horizon'] = investment_horizon
            
            engineer = FeatureEngineer(config_with_interval)
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
        
        # Modeli kaydet (yatırım süresini dahil et)
        from datetime import datetime
        symbol_name = symbol.replace('.IS', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol_name}_{investment_horizon}_Model_{timestamp}.joblib"
        
        model_path = predictor.save_model(filename)
        
        if progress_callback:
            progress_callback(f"✅ {symbol} model eğitimi tamamlandı!")
        
        return True, f"{symbol} model eğitildi - Accuracy: {results['test_metrics']['accuracy']:.3f}"
        
    except Exception as e:
        return False, f"{symbol} model eğitimi başarısız: {str(e)}"

def analyze_model_info(model_data, features_df):
    """Model hakkında detaylı bilgi analizi"""
    model_info = {
        'training_period': 'Bilinmiyor',
        'data_points': len(features_df) if not features_df.empty else 0,
        'features_count': len(features_df.columns) if not features_df.empty else 0,
        'accuracy': model_data.get('test_metrics', {}).get('accuracy', 0),
        'f1_score': model_data.get('test_metrics', {}).get('f1_score', 0),
        'precision': model_data.get('test_metrics', {}).get('precision', 0),
        'recall': model_data.get('test_metrics', {}).get('recall', 0),
        'strongest_features': [],
        'model_type': 'Gradient Boosting',
        'training_date': 'Bilinmiyor'
    }
    
    # Model dosya adından tarih çıkarma
    if 'model_file' in model_data:
        model_file = model_data['model_file']
        if '_Model_' in model_file:
            try:
                date_part = model_file.split('_Model_')[1].split('.')[0]
                model_info['training_date'] = date_part
            except:
                pass
    
    # En güçlü özellikleri belirleme (detaylı analiz)
    if not features_df.empty and len(features_df) > 10:
        # Teknik göstergeler
        if 'rsi' in features_df.columns:
            model_info['strongest_features'].append("RSI momentum analizi")
        
        if 'sma_20' in features_df.columns and 'sma_50' in features_df.columns:
            model_info['strongest_features'].append("Hareketli ortalama trend analizi")
        
        if 'macd' in features_df.columns:
            model_info['strongest_features'].append("MACD momentum analizi")
        
        if 'volume' in features_df.columns:
            model_info['strongest_features'].append("İşlem hacmi analizi")
        
        # Momentum özellikleri
        momentum_features = [col for col in features_df.columns if 'momentum' in col.lower() or 'roc' in col.lower()]
        if momentum_features:
            model_info['strongest_features'].append(f"{len(momentum_features)} momentum göstergesi")
        
        # Volatilite özellikleri
        volatility_features = [col for col in features_df.columns if 'volatility' in col.lower() or 'std' in col.lower()]
        if volatility_features:
            model_info['strongest_features'].append(f"{len(volatility_features)} volatilite göstergesi")
        
        # Fiyat özellikleri
        price_features = [col for col in features_df.columns if 'price' in col.lower() and 'change' in col.lower()]
        if price_features:
            model_info['strongest_features'].append(f"{len(price_features)} fiyat değişim göstergesi")
        
        # Hacim özellikleri
        volume_features = [col for col in features_df.columns if 'volume' in col.lower() and 'ratio' in col.lower()]
        if volume_features:
            model_info['strongest_features'].append(f"{len(volume_features)} hacim oranı göstergesi")
        
        # Zaman özellikleri
        time_features = [col for col in features_df.columns if 'day' in col.lower() or 'week' in col.lower() or 'month' in col.lower()]
        if time_features:
            model_info['strongest_features'].append(f"{len(time_features)} zaman etkisi göstergesi")
        
        # Bollinger Bands
        if 'bb_upper' in features_df.columns and 'bb_lower' in features_df.columns:
            model_info['strongest_features'].append("Bollinger Bands volatilite analizi")
        
        # Stochastic
        if 'stoch_k' in features_df.columns and 'stoch_d' in features_df.columns:
            model_info['strongest_features'].append("Stochastic momentum analizi")
        
        # Williams %R
        if 'williams_r' in features_df.columns:
            model_info['strongest_features'].append("Williams %R momentum analizi")
        
        # CCI
        if 'cci' in features_df.columns:
            model_info['strongest_features'].append("CCI trend analizi")
        
        # ADX
        if 'adx' in features_df.columns:
            model_info['strongest_features'].append("ADX trend gücü analizi")
        
        # OBV
        if 'obv' in features_df.columns:
            model_info['strongest_features'].append("OBV hacim analizi")
    
    return model_info

def show_future_prediction_tab(selected_symbol, config, interval="1d", investment_horizon="MEDIUM_TERM"):
    """Gelecek Tahmin Tab"""
    
    # Config'e yatırım süresini ekle
    config['MODEL_CONFIG']['investment_horizon'] = investment_horizon
    
    # Yatırım süresi bilgisi
    horizon_names = {
        "SHORT_TERM": "⚡ Kısa Vade (1 hafta - 1 ay)",
        "MEDIUM_TERM": "📊 Orta Vade (1 ay - 3 ay)",
        "LONG_TERM": "🏆 Uzun Vade (3 ay - 1 yıl)"
    }
    
    st.header("🔮 Gelecek Tahmin")
    st.info(f"🎯 Bu sekme hissenin **bir sonraki hamlesini** tahmin eder ve size net sinyal verir! (Strateji: {horizon_names.get(investment_horizon, investment_horizon)}, Zaman Dilimi: {interval})")
    
    # Model seçimi - Otomatik hisse bazlı seçim (yatırım süresine göre filtrelenmiş)
    model_files = []
    if os.path.exists('src/models'):
        model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
    
    if not model_files:
        st.warning("⚠️ Eğitilmiş model bulunamadı! Önce model eğitimi yapın.")
    else:
        # Hisse bazlı model bul
        symbol_name = selected_symbol.replace('.IS', '') if selected_symbol else None
        
        # Önce yatırım süresine göre filtrele
        filtered_models = [f for f in model_files if f'{investment_horizon}' in f]
        
        # Sonra hisse bazlı filtrele
        symbol_models = []
        if filtered_models:
            symbol_models = [f for f in filtered_models if symbol_name and symbol_name in f] if symbol_name else []
        
        # Eğer yeni format yoksa eski format modelleri kontrol et
        if not symbol_models and symbol_name:
            # Eski format modelleri kullan (horizon içermeyen)
            old_format_models = [f for f in model_files if symbol_name in f and all(h not in f for h in ['SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM'])]
            if old_format_models:
                symbol_models = old_format_models
                st.warning(f"⚠️ **Eski formatta model bulundu. Doğru tahmin için {investment_horizon} stratejisi için yeni model eğitin!**")
        
        # Hala model yoksa
        if not symbol_models:
            st.warning(f"⚠️ {selected_symbol} için {investment_horizon} stratejisinde model bulunamadı!")
        
        if symbol_models:
            # En son modeli otomatik seç
            symbol_models.sort(reverse=True)
            auto_selected_model = symbol_models[0]
            
            # Model formatını kontrol et
            is_old_format = investment_horizon not in auto_selected_model
            
            if is_old_format:
                st.warning(f"⚠️ **ESKİ MODEL KULLANILIYOR**: {auto_selected_model}")
                st.error(f"Bu model yatırım süresi bilgisi içermiyor. Seçtiğiniz '{investment_horizon}' stratejisi için doğru tahmin yapamayabilir.")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Doğru Model İçin Eğit", type="primary", key="train_correct_model"):
                        with st.spinner("🔮 Model eğitiliyor..."):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            call_count = [0]
                            
                            def update_progress(message):
                                call_count[0] += 1
                                status_text.text(message)
                                progress_bar.progress(min(100, call_count[0] * 20))
                            
                            success, message = train_model_for_symbol(selected_symbol, config, update_progress, interval=interval, investment_horizon=investment_horizon)
                            
                            if success:
                                st.success(f"✅ {message}")
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                
                with col2:
                    st.info("💡 Doğru model için sağdaki butonu kullanın")
            else:
                st.success(f"✅ {selected_symbol} için {investment_horizon} stratejisinde uygun model bulundu: **{auto_selected_model}**")
            
            # Manuel model seçimi (isteğe bağlı)
            if st.checkbox("🔄 Manuel model seçimi", value=False, key="manual_model_selection"):
                selected_model = st.selectbox("🔮 Tahmin Modeli:", symbol_models, key="prediction_model_selection")
            else:
                selected_model = auto_selected_model
        else:
            # Model bulunamadı - Eğitim seçeneği
            st.warning(f"⚠️ {selected_symbol} için model bulunamadı!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🤖 Model Eğit (Önerilen)", type="primary", key="train_model_button"):
                    with st.spinner("🔮 Model eğitiliyor, lütfen bekleyin..."):
                        # Progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Progress değişkeni
                        call_count = [0]
                        
                        def update_progress(message):
                            call_count[0] += 1
                            status_text.text(message)
                            # 5 aşamalı progress (0, 25, 50, 75, 100)
                            progress = min(100, call_count[0] * 20)
                            progress_bar.progress(progress)
                        
                        # Model eğit
                        success, message = train_model_for_symbol(selected_symbol, config, update_progress, interval=interval, investment_horizon=investment_horizon)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🔄 Sayfayı yenileyin ve yeniden deneyin.")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            with col2:
                st.info("💡 Model yoksa, genel bir model kullanılabilir (daha az doğru olabilir)")
            
            st.markdown("---")
            st.info(f"ℹ️ Alternatif: Genel bir model kullanmak isterseniz aşağıdaki butonu kullanın")
            
            # Model eğitimi - Doğru yatırım süresinde
            st.warning(f"⚠️ {selected_symbol} için {investment_horizon} stratejisinde model bulunamadı!")
            st.info(f"💡 **Yatırım süresini değiştirdiyseniz, yeni strateji için model eğitmeniz gerekir.**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"🤖 {investment_horizon} için Model Eğit", type="primary", key="train_horizon_model"):
                    with st.spinner("🔮 Model eğitiliyor, lütfen bekleyin..."):
                        # Progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Progress değişkeni
                        call_count = [0]
                        
                        def update_progress(message):
                            call_count[0] += 1
                            status_text.text(message)
                            progress = min(100, call_count[0] * 20)
                            progress_bar.progress(progress)
                        
                        # Model eğit
                        success, message = train_model_for_symbol(selected_symbol, config, update_progress, interval=interval, investment_horizon=investment_horizon)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🔄 Sayfa yenileniyor...")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            with col2:
                st.info(f"📊 Seçili Strateji: {horizon_names.get(investment_horizon, investment_horizon)}")
            
            selected_model = None  # Model seçilmedi
        
        # Tahmin butonu
        if st.button("🔮 Gelecek Hamleyi Tahmin Et", type="primary", disabled=(selected_model is None)):
            if selected_model is None:
                st.error("❌ Lütfen önce model eğitin veya genel model seçin!")
            else:
                with st.spinner("🔮 Gelecek hamle tahmin ediliyor..."):
                    try:
                        # Modeli yükle
                        predictor = StockDirectionPredictor(config)
                        model_path = f'src/models/{selected_model}'
                        
                        # Model dosyasının var olup olmadığını kontrol et
                        if not os.path.exists(model_path):
                            st.error(f"❌ Model dosyası bulunamadı: {model_path}")
                        elif not predictor.load_model(model_path):
                            st.error(f"❌ Model yüklenemedi: {model_path}")
                            st.warning("⚠️ **Model yüklenemiyor - Numpy uyumsuzluğu olabilir.**")
                            
                            # Otomatik model eğitimi seçeneği
                            st.info("💡 **Çözüm:** Aynı anda yeni model eğitelim mi?")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("🤖 Hemen Model Eğit", type="primary"):
                                    # Önce eski modelleri temizle
                                    symbol_name = selected_symbol.replace('.IS', '')
                                    old_models = [f for f in os.listdir('src/models') if f.endswith('.joblib') and symbol_name in f]
                                    for old_model in old_models:
                                        try:
                                            os.remove(f'src/models/{old_model}')
                                        except:
                                            pass
                                    
                                    # Progress container
                                    progress_container = st.container()
                                    progress_bar = progress_container.progress(0)
                                    status_text = progress_container.empty()
                                    
                                    # Model eğit (Hisse Avcısı'ndaki gibi)
                                    def update_status(message):
                                        status_text.text(message)
                                    
                                    success, message = train_model_for_symbol(selected_symbol, config, update_status, interval=interval, investment_horizon=investment_horizon)
                                    
                                    if success:
                                        st.success(f"✅ {message}")
                                        progress_bar.progress(1.0)
                                        st.balloons()
                                        st.info("🔄 Sayfa yenileniyor...")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
                            
                            with col2:
                                if st.button("🗑️ Eski Modelleri Sil", type="secondary"):
                                    try:
                                        import glob
                                        old_models = glob.glob('src/models/*.joblib')
                                        for model in old_models:
                                            os.remove(model)
                                        st.success("✅ Eski modeller temizlendi! Yukarıdaki buton ile yeni model eğitebilirsiniz.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Silme hatası: {str(e)}")
                        else:
                            # Güncel veri yükle
                            data = load_stock_data(selected_symbol, "1y", interval=interval)
                            features_df = create_features(data, config=config, interval=interval)
                            
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
                            
                            # Tahmin faktörlerini analiz et
                            prediction_factors = analyze_prediction_factors(data, features_df, last_prediction, last_confidence, model_data)
                            
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
                                
                                # Basit öneriler - Alt alta düzenlenmiş
                                st.info(f"""
                                **📈 Pozisyonunuz Yoksa:**
                                ✅ **AL** - Yükseliş bekleniyor
                                
                                **🎯 Hedef:** {price_targets['targets']['moderate']:.2f} TL
                                
                                **⏰ Tahmini süre:** {price_targets['time_targets']['moderate']['estimated_days']} gün
                                """)
                                
                                st.info(f"""
                                **📊 Pozisyonunuz Varsa:**
                                ✅ **KORU** - Yükseliş devam edecek
                                
                                **🎯 Hedef:** {price_targets['targets']['aggressive']:.2f} TL
                                
                                **⏰ Tahmini süre:** {price_targets['time_targets']['aggressive']['estimated_days']} gün
                                """)
                                
                            else:  # SAT sinyali
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); padding: 30px; border-radius: 20px; text-align: center; border: 3px solid #dc3545; margin: 20px 0; box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);">
                                    <h1 style="color: #721c24; margin: 0; font-size: 3em;">🔴 SAT</h1>
                                    <h3 style="color: #721c24; margin: 15px 0;">Hisse düşüşe geçecek!</h3>
                                    <p style="color: #721c24; margin: 0; font-size: 1.3em; font-weight: bold;">Güven: %{last_confidence*100:.1f}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Basit öneriler - Alt alta düzenlenmiş
                                st.warning(f"""
                                **📉 Pozisyonunuz Yoksa:**
                                ⏳ **BEKLE** - Düşüş bekleniyor
                                
                                **🎯 Hedef:** {price_targets['targets']['moderate']:.2f} TL
                                
                                **⏰ Tahmini süre:** {price_targets['time_targets']['moderate']['estimated_days']} gün
                                """)
                                
                                st.error(f"""
                                **📊 Pozisyonunuz Varsa:**
                                ❌ **SAT** - Düşüş başlayacak
                                
                                **🛡️ Stop Loss:** {price_targets['stop_loss']:.2f} TL
                                
                                **⏰ Tahmini süre:** {price_targets['time_targets']['conservative']['estimated_days']} gün
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
                            
                            # Destek/Direnç Seviyeleri - Detaylı Analiz
                            st.subheader("🎯 Destek/Direnç Seviyeleri")
                            
                            chart_analysis = price_targets['time_targets']['conservative']['chart_analysis']
                            
                            # Ana seviyeler
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                support_distance = ((chart_analysis['support_level'] - last_price) / last_price * 100)
                                support_color = "#28a745" if support_distance < -5 else "#ffc107" if support_distance < -2 else "#dc3545"
                                st.markdown(f"""
                                <div style="background-color: #e8f5e8; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid {support_color};">
                                    <h3 style="color: #155724; margin: 0;">🛡️ Destek Seviyesi</h3>
                                    <h2 style="color: #155724; margin: 10px 0;">{chart_analysis['support_level']:.2f} TL</h2>
                                    <p style="color: #666; margin: 0;">Mevcut fiyattan %{support_distance:+.1f}</p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.9em;">
                                        {'⚠️ Kritik seviye!' if abs(support_distance) < 3 else '✅ Güvenli mesafe'}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with col2:
                                st.markdown(f"""
                                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #6c757d;">
                                    <h3 style="color: #495057; margin: 0;">💰 Mevcut Fiyat</h3>
                                    <h2 style="color: #495057; margin: 10px 0;">{last_price:.2f} TL</h2>
                                    <p style="color: #666; margin: 0;">Son kapanış fiyatı</p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.9em;">
                                        Volatilite: %{volatility*100:.1f}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with col3:
                                resistance_distance = ((chart_analysis['resistance_level'] - last_price) / last_price * 100)
                                resistance_color = "#28a745" if resistance_distance > 5 else "#ffc107" if resistance_distance > 2 else "#dc3545"
                                st.markdown(f"""
                                <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid {resistance_color};">
                                    <h3 style="color: #721c24; margin: 0;">🚀 Direnç Seviyesi</h3>
                                    <h2 style="color: #721c24; margin: 10px 0;">{chart_analysis['resistance_level']:.2f} TL</h2>
                                    <p style="color: #666; margin: 0;">Mevcut fiyattan %{resistance_distance:+.1f}</p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.9em;">
                                        {'⚠️ Kritik seviye!' if abs(resistance_distance) < 3 else '✅ Güvenli mesafe'}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Ek destek/direnç seviyeleri
                            st.markdown("---")
                            st.subheader("📊 Ek Destek/Direnç Seviyeleri")
                            
                            # Geçmiş verilerden ek seviyeler hesapla
                            if len(data) >= 50:
                                # 50 günlük destek/direnç
                                support_50d = data['low'].tail(50).min()
                                resistance_50d = data['high'].tail(50).max()
                                
                                # 20 günlük destek/direnç
                                support_20d = data['low'].tail(20).min()
                                resistance_20d = data['high'].tail(20).max()
                                
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric(
                                        "🛡️ 20 Günlük Destek",
                                        f"{support_20d:.2f} TL",
                                        f"{((support_20d - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                with col2:
                                    st.metric(
                                        "🚀 20 Günlük Direnç", 
                                        f"{resistance_20d:.2f} TL",
                                        f"{((resistance_20d - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                with col3:
                                    st.metric(
                                        "🛡️ 50 Günlük Destek",
                                        f"{support_50d:.2f} TL", 
                                        f"{((support_50d - last_price) / last_price * 100):+.1f}%"
                                    )
                                
                                with col4:
                                    st.metric(
                                        "🚀 50 Günlük Direnç",
                                        f"{resistance_50d:.2f} TL",
                                        f"{((resistance_50d - last_price) / last_price * 100):+.1f}%"
                                    )
                            
                            # Detaylı Hedef Fiyatlar ve Süreler
                            st.markdown("---")
                            st.subheader("🎯 Hedef Fiyatlar ve Tahmini Süreler")
                            
                            # Konservatif hedef
                            conservative_info = price_targets['time_targets']['conservative']
                            conservative_target = price_targets['targets']['conservative']
                            conservative_change = ((conservative_target - last_price) / last_price * 100)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #28a745;">
                                    <h3 style="color: #155724; margin: 0;">🛡️ Konservatif</h3>
                                    <h2 style="color: #155724; margin: 10px 0;">{conservative_target:.2f} TL</h2>
                                    <p style="color: #155724; margin: 5px 0; font-weight: bold;">%{conservative_change:+.1f}</p>
                                    <hr style="margin: 10px 0; border-color: #28a745;">
                                    <p style="color: #155724; margin: 5px 0; font-size: 0.9em;">
                                        <strong>⏰ Süre:</strong> {conservative_info['estimated_days']} gün
                                    </p>
                                    <p style="color: #155724; margin: 5px 0; font-size: 0.9em;">
                                        <strong>📅 Tarih:</strong> {conservative_info['estimated_date']}
                                    </p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.8em;">
                                        ({conservative_info['min_days']}-{conservative_info['max_days']} gün arası)
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Orta hedef
                            moderate_info = price_targets['time_targets']['moderate']
                            moderate_target = price_targets['targets']['moderate']
                            moderate_change = ((moderate_target - last_price) / last_price * 100)
                            
                            with col2:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #ffc107;">
                                    <h3 style="color: #856404; margin: 0;">⚖️ Orta</h3>
                                    <h2 style="color: #856404; margin: 10px 0;">{moderate_target:.2f} TL</h2>
                                    <p style="color: #856404; margin: 5px 0; font-weight: bold;">%{moderate_change:+.1f}</p>
                                    <hr style="margin: 10px 0; border-color: #ffc107;">
                                    <p style="color: #856404; margin: 5px 0; font-size: 0.9em;">
                                        <strong>⏰ Süre:</strong> {moderate_info['estimated_days']} gün
                                    </p>
                                    <p style="color: #856404; margin: 5px 0; font-size: 0.9em;">
                                        <strong>📅 Tarih:</strong> {moderate_info['estimated_date']}
                                    </p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.8em;">
                                        ({moderate_info['min_days']}-{moderate_info['max_days']} gün arası)
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Agresif hedef
                            aggressive_info = price_targets['time_targets']['aggressive']
                            aggressive_target = price_targets['targets']['aggressive']
                            aggressive_change = ((aggressive_target - last_price) / last_price * 100)
                            
                            with col3:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #dc3545;">
                                    <h3 style="color: #721c24; margin: 0;">🚀 Agresif</h3>
                                    <h2 style="color: #721c24; margin: 10px 0;">{aggressive_target:.2f} TL</h2>
                                    <p style="color: #721c24; margin: 5px 0; font-weight: bold;">%{aggressive_change:+.1f}</p>
                                    <hr style="margin: 10px 0; border-color: #dc3545;">
                                    <p style="color: #721c24; margin: 5px 0; font-size: 0.9em;">
                                        <strong>⏰ Süre:</strong> {aggressive_info['estimated_days']} gün
                                    </p>
                                    <p style="color: #721c24; margin: 5px 0; font-size: 0.9em;">
                                        <strong>📅 Tarih:</strong> {aggressive_info['estimated_date']}
                                    </p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.8em;">
                                        ({aggressive_info['min_days']}-{aggressive_info['max_days']} gün arası)
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Stop Loss
                            stop_loss = price_targets['stop_loss']
                            stop_loss_change = ((stop_loss - last_price) / last_price * 100)
                            
                            with col4:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #17a2b8;">
                                    <h3 style="color: #0c5460; margin: 0;">🛡️ Stop Loss</h3>
                                    <h2 style="color: #0c5460; margin: 10px 0;">{stop_loss:.2f} TL</h2>
                                    <p style="color: #0c5460; margin: 5px 0; font-weight: bold;">%{stop_loss_change:+.1f}</p>
                                    <hr style="margin: 10px 0; border-color: #17a2b8;">
                                    <p style="color: #0c5460; margin: 5px 0; font-size: 0.9em;">
                                        <strong>⚠️ Risk:</strong> {'Yüksek' if abs(stop_loss_change) > 5 else 'Orta' if abs(stop_loss_change) > 3 else 'Düşük'}
                                    </p>
                                    <p style="color: #0c5460; margin: 5px 0; font-size: 0.9em;">
                                        <strong>📊 R/G:</strong> {price_targets['risk_reward_ratio']:.2f}
                                    </p>
                                    <p style="color: #666; margin: 5px 0; font-size: 0.8em;">
                                        {'Hemen satış' if last_prediction == 0 else 'Koruma seviyesi'}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Ortalama Süre Analizi
                            st.markdown("---")
                            st.subheader("📊 Ortalama Süre Analizi")
                            
                            # Geçmiş hareket analizi bilgilerini göster
                            if 'historical_analysis' in conservative_info and not conservative_info['historical_analysis'].get('insufficient_data', False):
                                historical_analysis = conservative_info['historical_analysis']
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.markdown(f"""
                                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3;">
                                        <h4 style="color: #0d47a1; margin: 0 0 10px 0;">📈 Trend Analizi</h4>
                                        <p style="color: #1565c0; margin: 5px 0;"><strong>Güç:</strong> {historical_analysis.get('trend_strength', 0):.2f}</p>
                                        <p style="color: #1565c0; margin: 5px 0;"><strong>Yön:</strong> {'Yükseliş' if historical_analysis.get('trend_direction', 0) > 0 else 'Düşüş'}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col2:
                                    st.markdown(f"""
                                    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 10px; border-left: 5px solid #4caf50;">
                                        <h4 style="color: #1b5e20; margin: 0 0 10px 0;">📊 Volatilite Analizi</h4>
                                        <p style="color: #2e7d32; margin: 5px 0;"><strong>Son 20 gün:</strong> %{historical_analysis.get('recent_volatility', 0)*100:.1f}</p>
                                        <p style="color: #2e7d32; margin: 5px 0;"><strong>Uzun vadeli:</strong> %{historical_analysis.get('long_term_volatility', 0)*100:.1f}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col3:
                                    volatility_ratio = historical_analysis.get('volatility_ratio', 1.0)
                                    volatility_status = "Yüksek" if volatility_ratio > 1.2 else "Normal" if volatility_ratio > 0.8 else "Düşük"
                                    volatility_color = "#f44336" if volatility_ratio > 1.2 else "#4caf50" if volatility_ratio > 0.8 else "#ff9800"
                                    
                                    st.markdown(f"""
                                    <div style="background-color: #fff3e0; padding: 15px; border-radius: 10px; border-left: 5px solid {volatility_color};">
                                        <h4 style="color: #e65100; margin: 0 0 10px 0;">⚡ Volatilite Durumu</h4>
                                        <p style="color: #f57c00; margin: 5px 0;"><strong>Oran:</strong> {volatility_ratio:.2f}</p>
                                        <p style="color: #f57c00; margin: 5px 0;"><strong>Durum:</strong> {volatility_status}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Geçmiş hareket analizi detayları
                                movement_analysis = historical_analysis.get('movement_analysis', {})
                                if movement_analysis:
                                    st.markdown("---")
                                    st.subheader("📈 Geçmiş Hareket Analizi")
                                    st.info("💡 Geçmişte benzer hareketlerin kaç günde tamamlandığını görün")
                                    
                                    for i, (movement_key, movement_data) in enumerate(movement_analysis.items()):
                                        change_pct = float(movement_key) * 100
                                        avg_days = movement_data['avg_days']
                                        sample_count = movement_data['sample_count']
                                        min_days = movement_data.get('min_days', avg_days)
                                        max_days = movement_data.get('max_days', avg_days)
                                        std_days = movement_data.get('std_days', 0)
                                        
                                        # Renk kodlaması: Hareket büyüklüğüne göre
                                        if change_pct >= 10:
                                            border_color = "#f44336"  # Kırmızı
                                            color = "#721c24"
                                        elif change_pct >= 5:
                                            border_color = "#ff9800"  # Turuncu
                                            color = "#e65100"
                                        elif change_pct >= 2:
                                            border_color = "#ffc107"  # Sarı
                                            color = "#856404"
                                        else:
                                            border_color = "#4caf50"  # Yeşil
                                            color = "#1b5e20"
                                        
                                        with st.expander(f"📊 %{change_pct:+.1f} Hareket - {sample_count} örnek bulundu", expanded=False):
                                            # İstatistikler
                                            col1, col2, col3, col4 = st.columns(4)
                                            
                                            with col1:
                                                st.metric(
                                                    "⏱️ Ortalama Süre",
                                                    f"{avg_days:.1f} gün",
                                                    help="Bu büyüklükteki hareketin ortalama süresi"
                                                )
                                            
                                            with col2:
                                                st.metric(
                                                    "📊 Örnek Sayısı",
                                                    f"{sample_count}",
                                                    help=f"Geçmişte {sample_count} kez benzer hareket görülmüş"
                                                )
                                            
                                            with col3:
                                                st.metric(
                                                    "⚡ Min/Max",
                                                    f"{min_days:.0f}-{max_days:.0f} gün",
                                                    help="En kısa ve en uzun süreler"
                                                )
                                            
                                            with col4:
                                                variability = "Yüksek" if std_days > avg_days * 0.5 else "Orta" if std_days > avg_days * 0.25 else "Düşük"
                                                st.metric(
                                                    "📈 Tutarlılık",
                                                    variability,
                                                    help="Hareket süresinin tutarlılığı"
                                                )
                                            
                                            st.markdown("---")
                                            
                                            # Detaylı analiz
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                st.markdown("""
                                                **📊 Süre Dağılımı:**
                                                """)
                                                
                                                if std_days > 0:
                                                    # Standart sapma açıklaması
                                                    st.markdown(f"""
                                                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px;">
                                                        <p style="margin: 0;"><strong>📊 Ortalama:</strong> {avg_days:.1f} gün</p>
                                                        <p style="margin: 0;"><strong>📏 Standart Sapma:</strong> {std_days:.1f} gün</p>
                                                        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                                            <strong>🎯 En Olası Aralık:</strong> {max(1, int(avg_days - std_days)):.0f} - {int(avg_days + std_days):.0f} gün
                                                        </p>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                                else:
                                                    st.markdown(f"""
                                                    <div style="background-color: #e8f5e9; padding: 15px; border-radius: 8px;">
                                                        <p style="margin: 0;"><strong>✅ Sabit Süre:</strong> {avg_days:.1f} gün</p>
                                                        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                                            Tüm hareketler neredeyse aynı sürede tamamlanmış
                                                        </p>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                            
                                            with col2:
                                                st.markdown("""
                                                **🎯 Tahmin Güvenilirliği:**
                                                """)
                                                
                                                # Güvenilirlik hesapla
                                                if sample_count >= 20:
                                                    reliability = "Çok Yüksek"
                                                    reliability_color = "#4caf50"
                                                    emoji = "🟢"
                                                elif sample_count >= 10:
                                                    reliability = "Yüksek"
                                                    reliability_color = "#8bc34a"
                                                    emoji = "🟡"
                                                elif sample_count >= 5:
                                                    reliability = "Orta"
                                                    reliability_color = "#ff9800"
                                                    emoji = "🟠"
                                                else:
                                                    reliability = "Düşük"
                                                    reliability_color = "#f44336"
                                                    emoji = "🔴"
                                                
                                                # STD bazlı ek değerlendirme
                                                if std_days / avg_days > 0.75:
                                                    reliability = reliability + " (Değişken)"
                                                
                                                st.markdown(f"""
                                                <div style="background-color: {reliability_color}20; padding: 15px; border-radius: 8px; border-left: 4px solid {reliability_color};">
                                                    <p style="margin: 0;"><strong>{emoji} Güvenilirlik:</strong> {reliability}</p>
                                                    <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                                        {sample_count} örnek {'yeterli' if sample_count >= 10 else 'sınırlı'} veri sağlıyor
                                                    </p>
                                                    {'<p style="margin: 5px 0; font-size: 0.9em; color: #f44336;"><strong>⚠️:</strong> Süre değişkenliği yüksek</p>' if std_days / avg_days > 0.75 else ''}
                                                </div>
                                                """, unsafe_allow_html=True)
                                            
                                            # Örnekler
                                            st.markdown("---")
                                            st.markdown(f"""
                                            **📋 Analiz Detayı:**
                                            - <strong>🎯 Hedef:</strong> %{change_pct:.1f} fiyat değişimi
                                            - <strong>📅 Görüldü:</strong> Son {len(data)} gün içinde {sample_count} kez
                                            - <strong>🔄 Sıklık:</strong> Her {len(data)/max(sample_count, 1):.1f} günde bir ortalama
                                            - <strong>⏱️ Süre:</strong> {min_days:.0f} - {max_days:.0f} gün arası değişiyor
                                            {f'- <strong>📏 Dağılım:</strong> {std_days:.1f} gün standart sapma' if std_days > 0 else ''}
                                            """, unsafe_allow_html=True)
                            else:
                                st.info("📊 Geçmiş hareket analizi için yeterli veri bulunamadı.")
                            
                            # Detaylı Analiz (Daraltılabilir)
                            with st.expander("🔍 Detaylı Grafik ve Model Analizi", expanded=False):
                                st.subheader("📊 Grafik Analizi Detayları")
                                
                                chart_analysis = price_targets['time_targets']['conservative']['chart_analysis']
                                
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    trend_color = "green" if chart_analysis['trend_strength'] == 'Strong' else "orange" if chart_analysis['trend_strength'] == 'Medium' else "red"
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {trend_color};">
                                        <h5 style="color: {trend_color}; margin: 0 0 10px 0;">📈 Trend Gücü</h5>
                                        <p style="margin: 5px 0; font-size: 1.2em;"><strong>{chart_analysis['trend_strength']}</strong></p>
                                        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                            Değer: {chart_analysis.get('trend_strength_value', 0):.3f}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col2:
                                    volume_color = "green" if chart_analysis['volume_trend'] == 'Increasing' else "orange" if chart_analysis['volume_trend'] == 'Stable' else "red"
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {volume_color};">
                                        <h5 style="color: {volume_color}; margin: 0 0 10px 0;">📊 Hacim Trendi</h5>
                                        <p style="margin: 5px 0; font-size: 1.2em;"><strong>{chart_analysis['volume_trend']}</strong></p>
                                        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                            {'Artan hacim = Güçlü sinyal' if chart_analysis['volume_trend'] == 'Increasing' else 'Stabil hacim = Normal' if chart_analysis['volume_trend'] == 'Stable' else 'Azalan hacim = Zayıf sinyal'}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col3:
                                    sr_status = "⚠️ Yakın" if chart_analysis['near_support_resistance'] else "✅ Uzak"
                                    sr_color = "orange" if chart_analysis['near_support_resistance'] else "green"
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {sr_color};">
                                        <h5 style="color: {sr_color}; margin: 0 0 10px 0;">🎯 Destek/Direnç</h5>
                                        <p style="margin: 5px 0; font-size: 1.2em;"><strong>{sr_status}</strong></p>
                                        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                            {'Kritik seviyeler yakın' if chart_analysis['near_support_resistance'] else 'Güvenli mesafe'}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col4:
                                    pattern_color = "green" if 'Uptrend' in chart_analysis['pattern'] else "red" if 'Downtrend' in chart_analysis['pattern'] else "orange"
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {pattern_color};">
                                        <h5 style="color: {pattern_color}; margin: 0 0 10px 0;">🔍 Pattern</h5>
                                        <p style="margin: 5px 0; font-size: 1.1em;"><strong>{chart_analysis['pattern']}</strong></p>
                                        <p style="margin: 5px 0; font-size: 0.8em; color: #666;">
                                            Grafik kalıbı
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Model Performans Analizi
                                if 'model_analysis' in conservative_info and conservative_info['model_analysis']:
                                    st.markdown("---")
                                    st.subheader("🤖 Model Performans Analizi")
                                    
                                    model_analysis = conservative_info['model_analysis']
                                    
                                    col1, col2, col3 = st.columns(3)
                                    
                                    with col1:
                                        accuracy = model_analysis.get('accuracy', 0)
                                        accuracy_color = "green" if accuracy > 0.7 else "orange" if accuracy > 0.6 else "red"
                                        st.markdown(f"""
                                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {accuracy_color};">
                                            <h5 style="color: {accuracy_color}; margin: 0 0 10px 0;">🎯 Model Doğruluğu</h5>
                                            <p style="margin: 5px 0; font-size: 1.5em;"><strong>%{accuracy*100:.1f}</strong></p>
                                            <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                                {'Mükemmel' if accuracy > 0.8 else 'İyi' if accuracy > 0.7 else 'Orta' if accuracy > 0.6 else 'Zayıf'}
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    with col2:
                                        reliability = model_analysis.get('reliability_score', 0)
                                        reliability_color = "green" if reliability > 0.7 else "orange" if reliability > 0.6 else "red"
                                        st.markdown(f"""
                                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {reliability_color};">
                                            <h5 style="color: {reliability_color}; margin: 0 0 10px 0;">💪 Güvenilirlik</h5>
                                            <p style="margin: 5px 0; font-size: 1.5em;"><strong>%{reliability*100:.1f}</strong></p>
                                            <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                                {'Çok güvenilir' if reliability > 0.8 else 'Güvenilir' if reliability > 0.7 else 'Orta' if reliability > 0.6 else 'Zayıf'}
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    with col3:
                                        performance = model_analysis.get('performance_category', 'Unknown')
                                        perf_color = "green" if performance == 'Excellent' else "orange" if performance == 'Good' else "red"
                                        st.markdown(f"""
                                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid {perf_color};">
                                            <h5 style="color: {perf_color}; margin: 0 0 10px 0;">📊 Performans</h5>
                                            <p style="margin: 5px 0; font-size: 1.2em;"><strong>{performance}</strong></p>
                                            <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                                {'Mükemmel' if performance == 'Excellent' else 'İyi' if performance == 'Good' else 'Orta' if performance == 'Fair' else 'Zayıf'}
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                            
                            # Tahmin Sebepleri Analizi
                            st.markdown("---")
                            st.subheader("🔍 Tahmin Sebepleri")
                            st.info("💡 Bu tahminin hangi faktörlere dayandığını görün:")
                            
                            # Başlıkları belirle (AL veya SAT sinyaline göre)
                            if last_prediction == 1:  # AL sinyali
                                col1_title = "✅ Yükselişi Destekleyen"
                                col2_title = "❌ Yükselişi Engelleyen"
                            else:  # SAT sinyali
                                col1_title = "✅ Düşüşü Destekleyen"
                                col2_title = "❌ Düşüşü Engelleyen"
                            
                            # Olumlu faktörler, olumsuz faktörler ve riskler
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #28a745;">
                                    <h3 style="color: #155724; margin: 0 0 15px 0;">{col1_title}</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if prediction_factors['positive']:
                                    for i, factor in enumerate(prediction_factors['positive'], 1):
                                        st.markdown(f"""
                                        <div style="background-color: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 3px solid #28a745;">
                                            <strong>{i}.</strong> {factor}
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown("""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; color: #6c757d;">
                                        <em>Bu tahmin için özel faktör bulunamadı</em>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            with col2:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #dc3545;">
                                    <h3 style="color: #721c24; margin: 0 0 15px 0;">{col2_title}</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if prediction_factors['negative']:
                                    for i, factor in enumerate(prediction_factors['negative'], 1):
                                        st.markdown(f"""
                                        <div style="background-color: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 3px solid #dc3545;">
                                            <strong>{i}.</strong> {factor}
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown("""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; color: #6c757d;">
                                        <em>Bu tahmin için özel faktör bulunamadı</em>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            with col3:
                                st.markdown("""
                                <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ffc107;">
                                    <h3 style="color: #856404; margin: 0 0 15px 0;">⚠️ Riskler</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Risk faktörlerini oluştur
                                risk_factors = []
                                
                                # Model güvenilirliği riski
                                accuracy = model_data.get('test_metrics', {}).get('accuracy', 0.5)
                                if accuracy < 0.6:
                                    risk_factors.append("Model doğruluğu düşük - Tahmin riski yüksek")
                                
                                # Güven skoru riski
                                if last_confidence < 0.6:
                                    risk_factors.append("Düşük güven skoru - Belirsizlik yüksek")
                                
                                # Volatilite riski
                                if len(features_df) >= 10:
                                    recent_volatility = features_df['close'].pct_change().tail(10).std() * np.sqrt(252)
                                    if recent_volatility > 0.4:  # %40'ten yüksek
                                        risk_factors.append("Yüksek volatilite - Fiyat dalgalanması riski")
                                
                                # Hacim riski
                                if 'volume' in features_df.columns:
                                    recent_volume = features_df['volume'].tail(5).mean()
                                    avg_volume = features_df['volume'].tail(20).mean()
                                    if recent_volume < avg_volume * 0.5:
                                        risk_factors.append("Düşük işlem hacmi - Likidite riski")
                                
                                # Genel piyasa riski
                                risk_factors.append("Genel piyasa koşulları değişebilir")
                                risk_factors.append("Makroekonomik faktörler etkileyebilir")
                                
                                if risk_factors:
                                    for i, risk in enumerate(risk_factors, 1):
                                        st.markdown(f"""
                                        <div style="background-color: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 3px solid #ffc107;">
                                            <strong>{i}.</strong> {risk}
                                        </div>
                                        """, unsafe_allow_html=True)
                            
                            # Nötr faktörler (varsa)
                            if prediction_factors['neutral']:
                                st.markdown("---")
                                st.subheader("⚖️ Nötr Faktörler")
                                
                                col1, col2, col3 = st.columns(3)
                                neutral_factors = prediction_factors['neutral']
                                
                                # Nötr faktörleri 3 sütuna böl
                                factors_per_col = len(neutral_factors) // 3 + (1 if len(neutral_factors) % 3 > 0 else 0)
                                
                                for i, factor in enumerate(neutral_factors):
                                    col_idx = i // factors_per_col
                                    if col_idx == 0:
                                        with col1:
                                            st.markdown(f"""
                                            <div style="background-color: #f8f9fa; padding: 8px; margin: 3px 0; border-radius: 6px; border-left: 3px solid #6c757d; font-size: 0.9em;">
                                                {factor}
                                            </div>
                                            """, unsafe_allow_html=True)
                                    elif col_idx == 1:
                                        with col2:
                                            st.markdown(f"""
                                            <div style="background-color: #f8f9fa; padding: 8px; margin: 3px 0; border-radius: 6px; border-left: 3px solid #6c757d; font-size: 0.9em;">
                                                {factor}
                                            </div>
                                            """, unsafe_allow_html=True)
                                    else:
                                        with col3:
                                            st.markdown(f"""
                                            <div style="background-color: #f8f9fa; padding: 8px; margin: 3px 0; border-radius: 6px; border-left: 3px solid #6c757d; font-size: 0.9em;">
                                                {factor}
                                            </div>
                                            """, unsafe_allow_html=True)
                                
                                # Model Bilgileri Bölümü
                                st.markdown("---")
                                st.subheader("🤖 Model Bilgileri")
                                st.info("📊 Bu tahminin hangi model ile yapıldığını ve modelin özelliklerini görün:")
                                
                                # Model bilgilerini analiz et
                                model_info = analyze_model_info(model_data, features_df)
                                
                                # Model bilgilerini göster
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("""
                                    <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #2196f3;">
                                        <h3 style="color: #0d47a1; margin: 0 0 15px 0;">📈 Model Özellikleri</h3>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                                        <strong>🎯 Model Türü:</strong> {model_info['model_type']}<br>
                                        <strong>📅 Eğitim Tarihi:</strong> {model_info['training_date']}<br>
                                        <strong>📊 Veri Noktası:</strong> {model_info['data_points']:,} gün<br>
                                        <strong>🔧 Özellik Sayısı:</strong> {model_info['features_count']} teknik gösterge
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col2:
                                    st.markdown("""
                                    <div style="background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #4caf50;">
                                        <h3 style="color: #1b5e20; margin: 0 0 15px 0;">📊 Model Performansı</h3>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown(f"""
                                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                                        <strong>🎯 Doğruluk:</strong> %{model_info['accuracy']*100:.1f}<br>
                                        <strong>⚖️ F1 Skoru:</strong> %{model_info['f1_score']*100:.1f}<br>
                                        <strong>🎯 Kesinlik:</strong> %{model_info['precision']*100:.1f}<br>
                                        <strong>📈 Duyarlılık:</strong> %{model_info['recall']*100:.1f}
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # En güçlü özellikler
                                if model_info['strongest_features']:
                                    st.markdown("---")
                                    st.subheader("💪 Modelin En Güçlü Yanları")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    for i, feature in enumerate(model_info['strongest_features']):
                                        if i % 3 == 0:
                                            with col1:
                                                st.markdown(f"""
                                                <div style="background-color: #e3f2fd; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 3px solid #2196f3;">
                                                    <strong>✨</strong> {feature}
                                                </div>
                                                """, unsafe_allow_html=True)
                                        elif i % 3 == 1:
                                            with col2:
                                                st.markdown(f"""
                                                <div style="background-color: #e3f2fd; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 3px solid #2196f3;">
                                                    <strong>✨</strong> {feature}
                                                </div>
                                                """, unsafe_allow_html=True)
                                        else:
                                            with col3:
                                                st.markdown(f"""
                                                <div style="background-color: #e3f2fd; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 3px solid #2196f3;">
                                                    <strong>✨</strong> {feature}
                                                </div>
                                                """, unsafe_allow_html=True)
                                
                                # Model açıklaması
                                st.markdown("---")
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff9800;">
                                    <h4 style="color: #e65100; margin: 0 0 10px 0;">🔍 Model Hakkında</h4>
                                    <p style="color: #bf360c; margin: 0; line-height: 1.6;">
                                        Bu model <strong>{model_info['data_points']:,} günlük</strong> geçmiş veri ile eğitilmiştir ve 
                                        <strong>{model_info['features_count']} farklı teknik göstergeyi</strong> analiz eder. 
                                        Model, hisse senedi fiyat hareketlerini tahmin etmek için makine öğrenmesi algoritmaları kullanır.
                                        <br><br>
                                        <strong>En güçlü yanları:</strong> {', '.join(model_info['strongest_features'][:3]) if model_info['strongest_features'] else 'Teknik analiz ve momentum göstergeleri'}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Export butonları - Son bölüm
                                try:
                                    # Export için gerekli veriler
                                    export_data = {
                                        'prediction': last_prediction,
                                        'confidence': last_confidence,
                                        'current_price': last_price,
                                        'targets': price_targets['targets'],
                                        'time_targets': price_targets['time_targets'],
                                        'volatility': volatility,
                                        'risk_reward_ratio': price_targets['risk_reward_ratio'],
                                        'stop_loss': price_targets['stop_loss'],
                                        'prediction_factors': prediction_factors,
                                        'model_info': model_info
                                    }
                                    
                                    # Export butonlarını göster
                                    create_export_buttons(selected_symbol, export_data)
                                    
                                except Exception as export_error:
                                    st.warning(f"⚠️ Export özelliği şu anda kullanılamıyor: {str(export_error)}")
                                
                    except Exception as e:
                        st.error(f"❌ Tahmin hatası: {str(e)}")
