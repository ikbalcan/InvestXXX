#!/usr/bin/env python3
"""
Hızlı Test Scripti
Sistemin temel bileşenlerini test eder
"""

import sys
import os
import yaml
import logging
from datetime import datetime

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from backtest import Backtester

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_loading():
    """Veri yükleme testi"""
    print("🔍 Veri yükleme testi...")
    
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        loader = DataLoader(config)
        
        # Test sembolü
        test_symbol = "THYAO.IS"
        data = loader.fetch_stock_data(test_symbol, "30d")
        
        if data.empty:
            print("❌ Veri yüklenemedi!")
            return False
        
        print(f"✅ {test_symbol} için {len(data)} günlük veri yüklendi")
        print(f"   Tarih aralığı: {data.index.min()} - {data.index.max()}")
        print(f"   Son fiyat: {data['close'].iloc[-1]:.2f} TL")
        
        return True
        
    except Exception as e:
        print(f"❌ Veri yükleme hatası: {str(e)}")
        return False

def test_feature_engineering():
    """Özellik mühendisliği testi"""
    print("\n🔧 Özellik mühendisliği testi...")
    
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        loader = DataLoader(config)
        engineer = FeatureEngineer(config)
        
        # Veri yükle
        data = loader.fetch_stock_data("THYAO.IS", "90d")
        
        if data.empty:
            print("❌ Veri yüklenemedi!")
            return False
        
        # Özellikler oluştur
        features_df = engineer.create_all_features(data)
        
        if features_df.empty:
            print("❌ Özellikler oluşturulamadı!")
            return False
        
        print(f"✅ {len(features_df.columns)} özellik oluşturuldu")
        print(f"   Veri boyutu: {features_df.shape}")
        
        # Özellik kolonlarını göster
        feature_cols = engineer.get_feature_columns(features_df)
        print(f"   Model özellikleri: {len(feature_cols)}")
        
        # Hedef değişken dağılımı
        if 'direction_binary' in features_df.columns:
            direction_counts = features_df['direction_binary'].value_counts()
            print(f"   Hedef dağılım: {direction_counts.to_dict()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Özellik mühendisliği hatası: {str(e)}")
        return False

def test_model_training():
    """Model eğitimi testi"""
    print("\n🤖 Model eğitimi testi...")
    
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        loader = DataLoader(config)
        engineer = FeatureEngineer(config)
        predictor = StockDirectionPredictor(config)
        
        # Veri yükle
        data = loader.fetch_stock_data("THYAO.IS", "1y")
        
        if data.empty:
            print("❌ Veri yüklenemedi!")
            return False
        
        # Özellikler oluştur
        features_df = engineer.create_all_features(data)
        
        if features_df.empty:
            print("❌ Özellikler oluşturulamadı!")
            return False
        
        # Model için veriyi hazırla
        X, y = predictor.prepare_data(features_df)
        
        if X.empty or y.empty:
            print("❌ Model verisi hazırlanamadı!")
            return False
        
        print(f"✅ Model verisi hazırlandı: {X.shape}")
        
        # Model eğitimi
        results = predictor.train_model(X, y)
        
        print(f"✅ Model eğitimi tamamlandı")
        print(f"   Test Accuracy: {results['test_metrics']['accuracy']:.4f}")
        print(f"   Test F1 Score: {results['test_metrics']['f1']:.4f}")
        
        # Modeli kaydet
        model_path = predictor.save_model()
        print(f"   Model kaydedildi: {model_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model eğitimi hatası: {str(e)}")
        return False

def test_backtesting():
    """Backtesting testi"""
    print("\n📈 Backtesting testi...")
    
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        loader = DataLoader(config)
        engineer = FeatureEngineer(config)
        predictor = StockDirectionPredictor(config)
        backtester = Backtester(config)
        
        # Veri yükle
        data = loader.fetch_stock_data("THYAO.IS", "6mo")
        
        if data.empty:
            print("❌ Veri yüklenemedi!")
            return False
        
        # Özellikler oluştur
        features_df = engineer.create_all_features(data)
        
        if features_df.empty:
            print("❌ Özellikler oluşturulamadı!")
            return False
        
        # Model için veriyi hazırla
        X, y = predictor.prepare_data(features_df)
        
        if X.empty or y.empty:
            print("❌ Model verisi hazırlanamadı!")
            return False
        
        # Basit model eğitimi (hızlı test için)
        results = predictor.train_model(X, y)
        
        # Tahminler
        predictions, probabilities = predictor.predict(X)
        
        # Backtest
        backtest_results = backtester.run_backtest(
            features_df, predictions, probabilities, "THYAO.IS"
        )
        
        if backtest_results:
            metrics = backtest_results['performance_metrics']
            print(f"✅ Backtest tamamlandı")
            print(f"   Toplam Getiri: {metrics['total_return']:.2%}")
            print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            print(f"   Max Drawdown: {metrics['max_drawdown']:.2%}")
            print(f"   Toplam İşlem: {metrics['total_trades']}")
            
            return True
        else:
            print("❌ Backtest başarısız!")
            return False
        
    except Exception as e:
        print(f"❌ Backtesting hatası: {str(e)}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🚀 Hisse Senedi Yön Tahmini Sistemi - Hızlı Test")
    print("=" * 60)
    
    # Test sonuçları
    test_results = []
    
    # Testleri çalıştır
    test_results.append(("Veri Yükleme", test_data_loading()))
    test_results.append(("Özellik Mühendisliği", test_feature_engineering()))
    test_results.append(("Model Eğitimi", test_model_training()))
    test_results.append(("Backtesting", test_backtesting()))
    
    # Sonuçları göster
    print("\n" + "=" * 60)
    print("📊 TEST SONUÇLARI")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"{test_name:20} : {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"Toplam: {passed}/{total} test başarılı")
    
    if passed == total:
        print("\n🎉 Tüm testler başarılı! Sistem kullanıma hazır.")
        print("\n📋 Sonraki adımlar:")
        print("1. python main.py train --period 2y")
        print("2. python main.py backtest --model-path src/models/[model_file]")
        print("3. streamlit run dashboard.py")
    else:
        print(f"\n⚠️  {total - passed} test başarısız. Lütfen hataları kontrol edin.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
