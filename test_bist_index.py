#!/usr/bin/env python3
"""
BIST 100 Endeksi Entegrasyonu Test Scripti
Bu script yeni eklenen endeks özelliklerini test eder.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

import yaml
import pandas as pd
from src.data_loader import DataLoader
from src.feature_engineering import FeatureEngineer

def test_index_data_loading():
    """BIST 100 endeks verisi yükleme testi"""
    print("=" * 60)
    print("TEST 1: BIST 100 Endeks Verisi Yükleme")
    print("=" * 60)
    
    try:
        # Config yükle
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # DataLoader oluştur
        loader = DataLoader(config)
        
        # Endeks verisini yükle
        print("\n📊 BIST 100 endeks verisi yükleniyor...")
        index_data = loader.get_index_data(period='1y')
        
        if index_data.empty:
            print("❌ Endeks verisi yüklenemedi!")
            return False
        
        print(f"✅ Endeks verisi yüklendi: {len(index_data)} gün")
        print(f"📅 Tarih aralığı: {index_data.index.min()} - {index_data.index.max()}")
        print(f"💰 Son fiyat: {index_data['close'].iloc[-1]:.2f}")
        
        if len(index_data) >= 30:
            ret_30d = (index_data['close'].iloc[-1] / index_data['close'].iloc[-30] - 1) * 100
            print(f"📈 Son 30 gün getiri: {ret_30d:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_index_features():
    """Endeks özellikleri oluşturma testi"""
    print("\n" + "=" * 60)
    print("TEST 2: Endeks Özellikleri Oluşturma")
    print("=" * 60)
    
    try:
        # Config yükle
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Modülleri oluştur
        loader = DataLoader(config)
        engineer = FeatureEngineer(config, data_loader=loader)
        
        # Test hissesi verisi yükle
        print("\n📊 THYAO verisi yükleniyor...")
        stock_data = loader.fetch_stock_data('THYAO.IS', period='1y')
        
        if stock_data.empty:
            print("❌ Hisse verisi yüklenemedi!")
            return False
        
        print(f"✅ Hisse verisi yüklendi: {len(stock_data)} gün")
        
        # Endeks verisi yükle
        print("\n📊 BIST 100 endeks verisi yükleniyor...")
        index_data = loader.get_index_data(period='1y')
        
        if index_data.empty:
            print("❌ Endeks verisi yüklenemedi!")
            return False
        
        print(f"✅ Endeks verisi yüklendi: {len(index_data)} gün")
        
        # Özellikler oluştur
        print("\n🔧 Özellikler oluşturuluyor...")
        features_df = engineer.create_all_features(stock_data, index_data=index_data)
        
        if features_df.empty:
            print("❌ Özellikler oluşturulamadı!")
            return False
        
        print(f"✅ Toplam {len(features_df.columns)} özellik oluşturuldu")
        print(f"📊 Veri boyutu: {features_df.shape}")
        
        # Endeks özelliklerini kontrol et
        index_features = [col for col in features_df.columns 
                         if 'index' in col.lower() or 'beta' in col.lower() 
                         or 'divergence' in col.lower() or 'relative' in col.lower()]
        
        print(f"\n✅ {len(index_features)} endeks özelliği oluşturuldu:")
        for feat in sorted(index_features):
            if feat in features_df.columns:
                last_val = features_df[feat].iloc[-1]
                if pd.notna(last_val):
                    if 'divergence' in feat:
                        print(f"  - {feat}: {int(last_val)}")
                    else:
                        print(f"  - {feat}: {last_val:.4f}")
        
        # Son değerleri göster
        print("\n📊 Son Önemli Değerler:")
        if 'beta_20d' in features_df.columns:
            beta_val = features_df['beta_20d'].iloc[-1]
            if pd.notna(beta_val):
                print(f"  📈 Beta (20 gün): {beta_val:.3f}")
                if beta_val > 1:
                    print(f"     → Hisse endeksten %{(beta_val-1)*100:.1f} daha volatil")
                else:
                    print(f"     → Hisse endeksten %{(1-beta_val)*100:.1f} daha az volatil")
        
        if 'index_correlation_20d' in features_df.columns:
            corr_val = features_df['index_correlation_20d'].iloc[-1]
            if pd.notna(corr_val):
                print(f"  🔗 Korelasyon (20 gün): {corr_val:.3f}")
                if corr_val > 0.7:
                    print(f"     → Güçlü pozitif korelasyon (birlikte hareket)")
                elif corr_val < -0.3:
                    print(f"     → Negatif korelasyon (ters hareket)")
                else:
                    print(f"     → Zayıf korelasyon")
        
        if 'relative_strength_20d' in features_df.columns:
            rs_val = features_df['relative_strength_20d'].iloc[-1]
            if pd.notna(rs_val):
                print(f"  💪 Relative Strength (20 gün): {rs_val:.4f}")
                if rs_val > 0:
                    print(f"     → Hisse endeksten %{rs_val*100:.2f} daha iyi performans")
                else:
                    print(f"     → Hisse endeksten %{abs(rs_val)*100:.2f} daha kötü performans")
        
        if 'positive_divergence_5d' in features_df.columns:
            pos_div = features_df['positive_divergence_5d'].iloc[-1]
            neg_div = features_df['negative_divergence_5d'].iloc[-1] if 'negative_divergence_5d' in features_df.columns else 0
            if pos_div == 1:
                print(f"  ⬆️  Pozitif Divergence: Endeks düşerken hisse yükseliyor (GÜÇLÜ SİNYAL!)")
            elif neg_div == 1:
                print(f"  ⬇️  Negatif Divergence: Endeks yükselirken hisse düşüyor (ZAYIFLIK SİNYALI)")
            else:
                print(f"  ➡️  Divergence yok: Hisse ve endeks birlikte hareket ediyor")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_stocks():
    """Birden fazla hisse için endeks özellikleri testi"""
    print("\n" + "=" * 60)
    print("TEST 3: Birden Fazla Hisse Testi")
    print("=" * 60)
    
    try:
        # Config yükle
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Modülleri oluştur
        loader = DataLoader(config)
        engineer = FeatureEngineer(config, data_loader=loader)
        
        # Test hisseleri
        test_symbols = ['THYAO.IS', 'AKBNK.IS', 'BIMAS.IS']
        
        # Endeks verisi yükle (bir kez, tüm hisseler için ortak)
        print("\n📊 BIST 100 endeks verisi yükleniyor...")
        index_data = loader.get_index_data(period='1y')
        
        results = {}
        
        for symbol in test_symbols:
            print(f"\n📊 {symbol} verisi yükleniyor...")
            stock_data = loader.fetch_stock_data(symbol, period='1y')
            
            if stock_data.empty:
                print(f"❌ {symbol} verisi yüklenemedi!")
                continue
            
            # Özellikler oluştur
            features_df = engineer.create_all_features(stock_data, index_data=index_data)
            
            if features_df.empty:
                print(f"❌ {symbol} özellikler oluşturulamadı!")
                continue
            
            # Beta değerini al
            beta_val = None
            if 'beta_20d' in features_df.columns:
                beta_val = features_df['beta_20d'].iloc[-1]
            
            results[symbol] = {
                'beta': beta_val,
                'features_count': len(features_df.columns)
            }
            
            print(f"✅ {symbol}: Beta={beta_val:.3f if beta_val and pd.notna(beta_val) else 'N/A'}, "
                  f"Özellik sayısı={len(features_df.columns)}")
        
        print("\n📊 Özet:")
        for symbol, res in results.items():
            print(f"  {symbol}: Beta={res['beta']:.3f if res['beta'] and pd.notna(res['beta']) else 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ana test fonksiyonu"""
    print("\n" + "🚀" * 30)
    print("BIST 100 ENDEKS ENTEGRASYONU TEST SÜİTİ")
    print("🚀" * 30 + "\n")
    
    results = []
    
    # Test 1: Endeks verisi yükleme
    results.append(("Endeks Verisi Yükleme", test_index_data_loading()))
    
    # Test 2: Endeks özellikleri
    results.append(("Endeks Özellikleri Oluşturma", test_index_features()))
    
    # Test 3: Birden fazla hisse
    results.append(("Birden Fazla Hisse Testi", test_multiple_stocks()))
    
    # Özet
    print("\n" + "=" * 60)
    print("TEST SONUÇLARI ÖZETİ")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\n📊 Toplam: {success_count}/{total_count} test başarılı")
    
    if success_count == total_count:
        print("\n🎉 Tüm testler başarılı! BIST 100 endeksi entegrasyonu çalışıyor.")
        print("\n💡 Şimdi yapabilecekleriniz:")
        print("   1. Dashboard'u başlatın: streamlit run dashboard_main.py")
        print("   2. Model eğitin: python main.py train --symbols THYAO.IS")
        print("   3. Tahmin yapın ve endeks özelliklerinin etkisini gözlemleyin")
    else:
        print("\n⚠️  Bazı testler başarısız. Lütfen hataları kontrol edin.")

if __name__ == "__main__":
    main()

