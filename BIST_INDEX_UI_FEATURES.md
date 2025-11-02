# BIST 100 Endeksi - Kullanıcı Arayüzü Özellikleri

## 🎯 Kullanıcıya Gösterilen Bilgiler

### 1. **Gelecek Tahmin Sekmesi** ✅

**Yeni Eklenen Bölüm:** "📊 BIST 100 Endeks Analizi"

#### Gösterilen Metrikler:

1. **📊 Beta (20 gün)**
   - Hisse volatilitesi vs Endeks volatilitesi
   - Örnek: "Yüksek Volatil (1.35)" → Hisse endeksten %35 daha volatil
   - Delta: Endekse göre fark yüzdesi

2. **🔗 Korelasyon (20 gün)**
   - Hisse ve endeks arasındaki korelasyon
   - Durumlar:
     - "Güçlü Pozitif" (>0.7) → Birlikte hareket ediyorlar
     - "Negatif" (<-0.3) → Ters hareket ediyorlar
     - "Zayıf" (arada) → Bağımsız hareket

3. **💪 Relative Strength (20 gün)**
   - Hisse performansı - Endeks performansı
   - Örnek: "Güçlü (+%8.5)" → Hisse endeksten %8.5 daha iyi performans gösteriyor
   - Delta: Performans farkı yüzdesi

4. **⚡ Divergence (5 gün)**
   - Pozitif/Negatif/Yok
   - Pozitif: "Endeks düşerken hisse yükseliyor!" → Güçlü AL sinyali
   - Negatif: "Endeks yükselirken hisse düşüyor!" → Güçlü SAT sinyali

#### Detaylı Bilgiler:

- **BIST 100 Momentum (20 gün)**: Endeksin genel trend durumu
- **BIST 100 RSI**: Endeksin teknik durumu (aşırı alım/satım)

#### Tahmin Faktörlerinde Gösterilen:

✅ **Yükselişi Destekleyen Faktörler:**
- "🔗 BIST 100 ile güçlü pozitif korelasyon (0.85) - Birlikte yükseliş bekleniyor"
- "💪 Relative Strength: %8.5 - Hisse endeksten çok daha güçlü!"
- "⬆️ POZİTİF DİVERGENCE! Endeks düşerken hisse yükseliyor - GÜÇLÜ AL SİNYALİ!"
- "📈 BIST 100 güçlü yükselişte (%5.2) - Piyasa desteği var"

❌ **Yükselişi Engelleyen Faktörler:**
- "🔗 BIST 100 ile güçlü pozitif korelasyon (0.82) - Birlikte düşüş riski"
- "📉 BIST 100 düşüşte ama hisse yükseliş bekleniyor - Dikkat!"

⚖️ **Nötr Faktörler:**
- "📊 Beta: 1.15 - Hisse endeksten %15 daha volatil"
- "🔗 BIST 100 ile zayıf korelasyon (0.35) - Bağımsız hareket"
- "📊 BIST 100 stabil (%1.2) - Nötr piyasa"
- "📊 BIST 100 RSI normal (52.3)"

### 2. **Hisse Avcısı Sekmesi** (Yakında)

Hisse listesinde gösterilecek kolonlar:
- **Beta**: Hisse volatilitesi
- **Korelasyon**: Endeksle uyum
- **Relative Strength**: Performans farkı
- **Divergence**: Ters hareket sinyali

### 3. **Portföy Yöneticisi** (Yakında)

Portföy analizinde:
- Portföyün genel beta değeri
- Portföy-endeks korelasyonu
- Portföyün endekse göre performansı

## 📊 Örnek Senaryolar

### Senaryo 1: Endeksle Birlikte Hareket Eden Hisse
```
Beta: 1.05 (Normal)
Korelasyon: 0.85 (Güçlü Pozitif)
Relative Strength: +%2.1 (Benzer)
Divergence: Yok

→ Bu hisse endeksle birlikte hareket ediyor. 
  Endeks yükselirse hisse de yükselir.
```

### Senaryo 2: Endekse Ters Hareket Eden Hisse
```
Beta: 0.75 (Düşük Volatil)
Korelasyon: -0.45 (Negatif)
Relative Strength: +%12.5 (Güçlü)
Divergence: ⬆️ Pozitif

→ Bu hisse endekse ters hareket ediyor.
  Endeks düşerken hisse yükseliyor - GÜÇLÜ AL SİNYALİ!
```

### Senaryo 3: Bağımsız Hareket Eden Hisse
```
Beta: 0.95 (Normal)
Korelasyon: 0.25 (Zayıf)
Relative Strength: +%1.2 (Benzer)
Divergence: Yok

→ Bu hisse endeksten bağımsız hareket ediyor.
  Kendi sektörel/şirket özel faktörleri daha önemli.
```

## 🎨 Görsel Gösterim

### Renk Kodlaması:

- 🟢 **Yeşil**: Pozitif/İyi durum
- 🔴 **Kırmızı**: Negatif/Riskli durum
- 🟡 **Sarı**: Normal/Orta durum
- ⚪ **Beyaz**: Nötr durum

### Metrik Gösterimi:

```
📊 Beta (20 gün)
Yüksek Volatil (1.35)
%35 endekse göre ↑
```

## 💡 Kullanıcı İçin Anlamı

1. **Beta Bilgisi**: 
   - Yüksek beta → Daha riskli ama daha yüksek getiri potansiyeli
   - Düşük beta → Daha güvenli ama daha düşük getiri potansiyeli

2. **Korelasyon Bilgisi**:
   - Güçlü pozitif → Endeks yükselirse hisse de yükselir
   - Negatif → Endeks düşerken hisse yükselebilir (fırsat!)

3. **Relative Strength**:
   - Pozitif → Hisse endeksten daha güçlü (iyi işaret)
   - Negatif → Hisse endeksten daha zayıf (dikkat!)

4. **Divergence**:
   - Pozitif divergence → Güçlü AL sinyali (endeks düşerken hisse yükseliyor)
   - Negatif divergence → Güçlü SAT sinyali (endeks yükselirken hisse düşüyor)

## 🚀 Kullanım Senaryoları

### Senaryo A: Endeks Yükselişte, Hisse de Yükseliş Bekleniyor
**Durum:** Beta 1.1, Korelasyon 0.8, AL sinyali
**Öneri:** ✅ GÜÇLÜ AL SİNYALİ - Endeks desteği var

### Senaryo B: Endeks Düşüşte, Ama Hisse Yükseliş Bekleniyor
**Durum:** Negatif korelasyon, Pozitif divergence, AL sinyali
**Öneri:** ✅ ÇOK GÜÇLÜ AL SİNYALİ - Ters hareket, bağımsız güçlü trend

### Senaryo C: Endeks Yükselişte, Ama Hisse Düşüş Bekleniyor
**Durum:** Güçlü pozitif korelasyon, SAT sinyali
**Öneri:** ⚠️ DİKKAT - Endeks desteği yok, düşüş riski yüksek

## 📝 Notlar

- Tüm endeks bilgileri gerçek zamanlı BIST 100 verilerinden hesaplanıyor
- Endeks verisi otomatik cache'leniyor (1 gün)
- Model eğitiminde otomatik dahil ediliyor
- Kullanıcı hiçbir şey yapmadan bu bilgileri görebiliyor

