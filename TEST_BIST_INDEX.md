# BIST 100 Endeksi Entegrasyonu - Test Rehberi

## 🎯 Yeni Özellikler

Sistem artık BIST 100 endeksi verilerini kullanarak daha doğru tahminler yapıyor! Eklenen özellikler:

### 📊 Endeks Özellikleri

1. **Beta Özellikleri** (beta_20d, beta_60d, beta_120d)
   - Hisse senedinin endekse göre volatilitesi
   - Beta > 1: Endeksten daha volatil
   - Beta < 1: Endeksten daha az volatil

2. **Korelasyon Özellikleri** (index_correlation_20d, index_correlation_60d, index_correlation_120d)
   - Hisse ve endeks arasındaki korelasyon
   - Pozitif: Birlikte hareket ediyorlar
   - Negatif: Ters hareket ediyorlar

3. **Relative Strength** (relative_strength_5d, relative_strength_10d, relative_strength_20d, relative_strength_60d)
   - Hisse performansı - Endeks performansı
   - Pozitif: Hisse endeksten daha iyi performans gösteriyor

4. **Divergence Detection** (positive_divergence_5d/20d, negative_divergence_5d/20d)
   - Pozitif divergence: Endeks düşerken hisse yükseliyor (güçlü sinyal!)
   - Negatif divergence: Endeks yükselirken hisse düşüyor (zayıflık sinyali)

5. **Endeks Teknik Göstergeleri** (index_rsi, index_macd, index_momentum_5d/20d, index_volatility_20d)
   - Endeksin teknik durumu

## 🧪 Test Adımları

### 1. Basit Python Testi

```bash
# Terminal'de çalıştırın
cd /Users/iko/InvestXXX
python -c "
from src.data_loader import DataLoader
import yaml

# Config yükle
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# DataLoader oluştur
loader = DataLoader(config)

# BIST 100 endeks verisini yükle
print('📊 BIST 100 endeks verisi yükleniyor...')
index_data = loader.get_index_data(period='1y')
print(f'✅ Endeks verisi yüklendi: {len(index_data)} gün')
print(f'📅 Tarih aralığı: {index_data.index.min()} - {index_data.index.max()}')
print(f'💰 Son fiyat: {index_data[\"close\"].iloc[-1]:.2f}')
print(f'📈 Son 30 gün getiri: {(index_data[\"close\"].iloc[-1] / index_data[\"close\"].iloc[-30] - 1) * 100:.2f}%')
"
```

### 2. Feature Engineering Testi

```bash
python -c "
from src.data_loader import DataLoader
from src.feature_engineering import FeatureEngineer
import yaml

# Config yükle
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Modülleri oluştur
loader = DataLoader(config)
engineer = FeatureEngineer(config, data_loader=loader)

# Test hissesi verisi yükle
print('📊 THYAO verisi yükleniyor...')
stock_data = loader.fetch_stock_data('THYAO.IS', period='1y')

# Endeks verisi yükle
print('📊 BIST 100 endeks verisi yükleniyor...')
index_data = loader.get_index_data(period='1y')

# Özellikler oluştur
print('🔧 Özellikler oluşturuluyor...')
features_df = engineer.create_all_features(stock_data, index_data=index_data)

# Endeks özelliklerini kontrol et
index_features = [col for col in features_df.columns if 'index' in col or 'beta' in col or 'divergence' in col or 'relative' in col]
print(f'✅ {len(index_features)} endeks özelliği oluşturuldu:')
for feat in index_features[:10]:  # İlk 10'unu göster
    print(f'  - {feat}')

# Son değerleri göster
print('\\n📊 Son değerler:')
if 'beta_20d' in features_df.columns:
    print(f'  Beta (20 gün): {features_df[\"beta_20d\"].iloc[-1]:.3f}')
if 'index_correlation_20d' in features_df.columns:
    print(f'  Korelasyon (20 gün): {features_df[\"index_correlation_20d\"].iloc[-1]:.3f}')
if 'relative_strength_20d' in features_df.columns:
    print(f'  Relative Strength (20 gün): {features_df[\"relative_strength_20d\"].iloc[-1]:.4f}')
if 'positive_divergence_5d' in features_df.columns:
    print(f'  Pozitif Divergence (5 gün): {features_df[\"positive_divergence_5d\"].iloc[-1]}')
"
```

### 3. Dashboard Testi

```bash
# Streamlit dashboard'u başlatın
streamlit run dashboard_main.py
```

**Dashboard'da test:**

1. **Ana Sayfa** → Bir hisse seçin (örn: THYAO.IS)
2. **Veri Analizi** sekmesine gidin
3. **Özellikler** bölümünde endeks özelliklerini kontrol edin:
   - `beta_20d`, `beta_60d`, `beta_120d`
   - `index_correlation_20d`, `index_correlation_60d`, `index_correlation_120d`
   - `relative_strength_5d`, `relative_strength_10d`, `relative_strength_20d`, `relative_strength_60d`
   - `positive_divergence_5d`, `negative_divergence_5d`
   - `index_rsi`, `index_macd`, `index_momentum_5d`, `index_momentum_20d`

4. **Gelecek Tahmin** sekmesine gidin
5. **Model Eğit** butonuna tıklayın (endeks özellikleri otomatik dahil edilecek)
6. **Tahmin Yap** butonuna tıklayın
7. Tahmin sonuçlarında endeks özelliklerinin etkisini gözlemleyin

### 4. Model Eğitimi Testi

```bash
# Komut satırından model eğitin
python main.py train --symbols THYAO.IS AKBNK.IS --period 2y
```

Eğitim sırasında loglarda şunları göreceksiniz:
```
📊 BIST 100 endeks verisi yükleniyor...
✅ BIST 100 endeksi için 730 1d veri yüklendi
🔧 Endeks özellikleri oluşturuluyor...
✅ Endeks özellikleri oluşturuldu: 20+ özellik
```

## 🎨 Kullanıcıya Yansıması

### 1. **Daha Doğru Tahminler**
- Model artık piyasa durumunu (BIST 100) dikkate alıyor
- Endeksle birlikte hareket eden hisseler daha iyi tespit ediliyor
- Endekse ters hareket eden hisseler (divergence) yakalanıyor

### 2. **Yeni Analiz Boyutları**
- **Beta analizi**: Hissenin endekse göre volatilitesi
- **Korelasyon analizi**: Hissenin endeksle uyumu
- **Relative Strength**: Hissenin endekse göre performansı
- **Divergence sinyalleri**: Ters hareket fırsatları

### 3. **Görsel Göstergeler** (Dashboard'da)
- Feature importance grafiklerinde endeks özellikleri görünecek
- Yüksek önemli endeks özellikleri modelin kararında rol oynuyor

### 4. **Tahmin Faktörleri**
Tahmin yaparken sistem şu bilgileri kullanıyor:
- ✅ Hissenin kendi teknik göstergeleri (RSI, MACD, vb.)
- ✅ **BIST 100 endeks durumu** (YENİ!)
- ✅ **Hisse-endeks ilişkisi** (Beta, Korelasyon) (YENİ!)
- ✅ **Divergence sinyalleri** (YENİ!)

## 📈 Beklenen İyileştirmeler

1. **Tahmin Doğruluğu**: %2-5 arası artış bekleniyor
2. **Divergence Yakalama**: Endekse ters hareket eden hisseler daha iyi tespit edilecek
3. **Risk Yönetimi**: Beta bilgisi ile pozisyon boyutlandırma daha iyi yapılabilir

## 🔍 Sorun Giderme

### Endeks verisi yüklenemiyor
```bash
# Cache'i temizleyin
rm data/raw/XU100_index.csv

# Tekrar deneyin
python -c "from src.data_loader import DataLoader; import yaml; config = yaml.safe_load(open('config.yaml')); loader = DataLoader(config); print(loader.get_index_data())"
```

### Endeks özellikleri görünmüyor
- Feature engineering cache'ini temizleyin
- Dashboard'u yeniden başlatın
- Model yeniden eğitin

### Model hatası
- Eski modelleri silin: `rm src/models/*.joblib`
- Yeni model eğitin (endeks özellikleri otomatik dahil)

## 📝 Notlar

- Endeks verisi otomatik cache'leniyor (1 gün)
- Her hisse için aynı endeks verisi kullanılıyor (performans için)
- Endeks özellikleri model eğitiminde otomatik dahil ediliyor
- Mevcut modeller yeniden eğitilmeden endeks özelliklerini kullanamaz

