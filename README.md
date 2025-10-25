# 📈 Hisse Senedi Yön Tahmini Sistemi

Bu proje, BIST hisse senetleri için makine öğrenmesi tabanlı yön tahmini sistemi sunar. XGBoost algoritması kullanarak teknik analiz göstergeleri ve momentum özelliklerine dayalı tahminler üretir.

## 🎯 Özellikler

- **Gerçek Zamanlı Veri**: yfinance API ile BIST hisse verileri
- **Teknik Analiz**: RSI, MACD, Bollinger Bands, Moving Averages
- **Momentum Özellikleri**: Çoklu zaman dilimi momentum analizi
- **XGBoost Modeli**: Yüksek performanslı gradient boosting
- **Gerçekçi Backtesting**: Komisyon, slippage ve risk yönetimi
- **Paper Trading**: Simüle edilmiş işlem sistemi
- **Streamlit Dashboard**: Kullanıcı dostu web arayüzü
- **Telegram Bildirimleri**: Otomatik sinyal bildirimleri

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
# Projeyi klonlayın
git clone <repository-url>
cd InvestXXX

# Sanal ortam oluşturun
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

### 2. Konfigürasyon

`config.yaml` dosyasını düzenleyin:

```yaml
# Hedef hisse senetleri
TARGET_STOCKS:
  - "THYAO.IS"  # Türk Hava Yolları
  - "AKBNK.IS"  # Akbank
  - "BIMAS.IS"  # BİM
  # ... diğer hisseler

# Risk yönetimi
RISK_MANAGEMENT:
  max_position_size: 0.02  # Maksimum %2 pozisyon
  stop_loss_pct: 0.05      # %5 stop loss
  take_profit_pct: 0.10    # %10 take profit

# Telegram bildirimleri (opsiyonel)
TELEGRAM:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"
  enabled: true
```

### 3. Model Eğitimi

```bash
# Model eğitimi
python main.py train --period 2y

# Belirli hisseler için
python main.py train --symbols THYAO.IS AKBNK.IS --period 1y
```

### 4. Backtest

```bash
# Backtest çalıştır
python main.py backtest --model-path src/models/stock_predictor_20241201_143022.joblib

# Belirli hisseler için
python main.py backtest --model-path src/models/model.joblib --symbols THYAO.IS
```

### 5. Paper Trading

```bash
# Paper trading başlat
python main.py paper-trade --model-path src/models/model.joblib

# Anlık sinyal üret
python main.py signals --model-path src/models/model.joblib
```

### 6. Dashboard

```bash
# Streamlit dashboard başlat
streamlit run dashboard.py
```

## 📊 Kullanım Örnekleri

### Model Eğitimi ve Değerlendirme

```python
from src.model_train import StockDirectionPredictor
from src.data_loader import DataLoader
from src.feature_engineering import FeatureEngineer

# Veri yükle
loader = DataLoader(config)
data = loader.fetch_stock_data("THYAO.IS", "2y")

# Özellikler oluştur
engineer = FeatureEngineer(config)
features_df = engineer.create_all_features(data)

# Model eğit
predictor = StockDirectionPredictor(config)
X, y = predictor.prepare_data(features_df)
results = predictor.train_model(X, y)

print(f"Test Accuracy: {results['test_metrics']['accuracy']:.4f}")
```

### Backtesting

```python
from src.backtest import Backtester

# Backtest çalıştır
backtester = Backtester(config)
results = backtester.run_backtest(features_df, predictions, probabilities, "THYAO.IS")

# Sonuçları görselleştir
backtester.plot_results("results.png")
print(backtester.generate_report())
```

### Paper Trading

```python
from src.live_trade import PaperTrader

# Paper trader başlat
trader = PaperTrader(config)

# Sinyal işle
result = trader.process_signal("THYAO.IS", 100.0, 1, 0.8)

# Portföy durumu
summary = trader.get_portfolio_summary()
print(f"Toplam getiri: {summary['total_return']:.2%}")
```

## 🏗️ Proje Yapısı

```
InvestXXX/
├── src/
│   ├── data_loader.py          # Veri yükleme modülü
│   ├── feature_engineering.py  # Özellik mühendisliği
│   ├── model_train.py          # Model eğitimi
│   ├── backtest.py            # Backtesting sistemi
│   ├── live_trade.py          # Paper trading
│   └── models/                # Eğitilmiş modeller
├── data/
│   ├── raw/                   # Ham veriler
│   ├── processed/            # İşlenmiş veriler
│   └── features/             # Özellik verileri
├── logs/                     # Log dosyaları
├── notebooks/               # Jupyter notebook'lar
├── config.yaml              # Konfigürasyon
├── requirements.txt         # Python bağımlılıkları
├── main.py                  # Ana çalıştırma scripti
├── dashboard.py             # Streamlit dashboard
└── README.md                # Bu dosya
```

## 📈 Performans Metrikleri

Sistem aşağıdaki metrikleri kullanır:

- **Accuracy**: Doğru tahmin oranı
- **Sharpe Ratio**: Risk ayarlı getiri
- **Maximum Drawdown**: Maksimum düşüş
- **Win Rate**: Kazançlı işlem oranı
- **Volatility**: Fiyat volatilitesi

## ⚠️ Risk Uyarıları

- Bu sistem eğitim amaçlıdır
- Gerçek para ile işlem yapmadan önce kapsamlı test yapın
- Geçmiş performans gelecek sonuçları garanti etmez
- Risk yönetimi kurallarına uyun
- Sadece kaybetmeyi göze alabileceğiniz para ile işlem yapın

## 🔧 Gelişmiş Özellikler

### Özellik Mühendisliği

Sistem aşağıdaki özellikleri otomatik oluşturur:

- **Teknik Göstergeler**: RSI, MACD, Bollinger Bands, Moving Averages
- **Momentum**: Çoklu zaman dilimi momentum analizi
- **Volatilite**: ATR, volatilite spike'ları
- **Hacim**: Hacim anomalileri, hacim oranları
- **Zaman**: Gün/hafta/ay etkileri

### Risk Yönetimi

- Pozisyon büyüklüğü kontrolü
- Stop loss ve take profit
- Günlük işlem limitleri
- Sermaye koruma kuralları

### Model Optimizasyonu

- Walk-forward validation
- Feature importance analizi
- Hyperparameter tuning
- Model ensemble

## 📞 Destek

Sorularınız için:
- GitHub Issues kullanın
- Dokümantasyonu inceleyin
- Örnek kodları çalıştırın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🙏 Teşekkürler

- yfinance: Veri sağlayıcısı
- XGBoost: Makine öğrenmesi algoritması
- Streamlit: Web dashboard
- Plotly: Veri görselleştirme

---

**Not**: Bu sistem sadece eğitim ve araştırma amaçlıdır. Gerçek para ile işlem yapmadan önce profesyonel finansal danışmanlık alın.
