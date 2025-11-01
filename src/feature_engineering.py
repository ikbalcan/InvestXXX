"""
Özellik Mühendisliği Modülü
Teknik analiz göstergeleri ve momentum özelliklerini oluşturur
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    def __init__(self, config: Dict):
        self.config = config
        self.lookback_window = config.get('MODEL_CONFIG', {}).get('lookback_window', 30)
        # Volatilite analizi bilgilerini sakla
        self.volatility_info = {
            'volatility': None,
            'stock_type': None,
            'volatility_scale': None,
            'threshold_up': None,
            'threshold_down': None
        }
        
    def create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Teknik analiz özelliklerini oluşturur
        
        Args:
            df: OHLCV verisi
            
        Returns:
            Özelliklerle zenginleştirilmiş DataFrame
        """
        features_df = df.copy()
        
        # Temel fiyat özellikleri
        features_df['returns'] = features_df['close'].pct_change()
        features_df['log_returns'] = np.log(features_df['close'] / features_df['close'].shift(1))
        features_df['high_low_ratio'] = features_df['high'] / features_df['low']
        features_df['close_open_ratio'] = features_df['close'] / features_df['open']
        
        # Volatilite özellikleri
        features_df['volatility_5d'] = features_df['returns'].rolling(5).std()
        features_df['volatility_20d'] = features_df['returns'].rolling(20).std()
        features_df['atr'] = ta.volatility.average_true_range(features_df['high'], 
                                                              features_df['low'], 
                                                              features_df['close'])
        
        # Momentum göstergeleri
        features_df['rsi'] = ta.momentum.rsi(features_df['close'])
        features_df['macd'] = ta.trend.macd(features_df['close'])
        features_df['macd_signal'] = ta.trend.macd_signal(features_df['close'])
        features_df['macd_diff'] = features_df['macd'] - features_df['macd_signal']
        features_df['macd_histogram'] = features_df['macd'] - features_df['macd_signal']
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            features_df[f'sma_{period}'] = ta.trend.sma_indicator(features_df['close'], period)
            features_df[f'ema_{period}'] = ta.trend.ema_indicator(features_df['close'], period)
            
        # Moving average crossovers
        features_df['sma_5_20_cross'] = np.where(features_df['sma_5'] > features_df['sma_20'], 1, 0)
        features_df['sma_10_50_cross'] = np.where(features_df['sma_10'] > features_df['sma_50'], 1, 0)
        
        # Bollinger Bands
        features_df['bb_upper'] = ta.volatility.bollinger_hband_indicator(features_df['close'])
        features_df['bb_lower'] = ta.volatility.bollinger_lband_indicator(features_df['close'])
        features_df['bb_middle'] = features_df['sma_20']  # Orta band SMA 20
        features_df['bb_width'] = (features_df['bb_upper'] - features_df['bb_lower']) / features_df['bb_middle']
        features_df['bb_position'] = (features_df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])
        
        # Volume özellikleri
        features_df['volume_sma_20'] = features_df['volume'].rolling(20).mean()
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma_20']
        features_df['volume_spike'] = np.where(features_df['volume_ratio'] > 2, 1, 0)
        
        # OBV (On-Balance Volume) - Hacim destekli göstergeler
        obv = pd.Series(index=features_df.index, dtype=float)
        obv.iloc[0] = features_df['volume'].iloc[0]
        for i in range(1, len(features_df)):
            if features_df['close'].iloc[i] > features_df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + features_df['volume'].iloc[i]
            elif features_df['close'].iloc[i] < features_df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - features_df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        features_df['obv'] = obv
        
        # Price position features
        features_df['price_vs_sma20'] = features_df['close'] / features_df['sma_20'] - 1
        features_df['price_vs_sma50'] = features_df['close'] / features_df['sma_50'] - 1
        
        # Gap features
        features_df['gap'] = (features_df['open'] - features_df['close'].shift(1)) / features_df['close'].shift(1)
        features_df['gap_up'] = np.where(features_df['gap'] > 0.02, 1, 0)  # %2+ gap up
        features_df['gap_down'] = np.where(features_df['gap'] < -0.02, 1, 0)  # %2+ gap down
        
        return features_df
    
    def create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Momentum tabanlı özellikler oluşturur
        
        Args:
            df: Özelliklerle zenginleştirilmiş DataFrame
            
        Returns:
            Momentum özellikleri eklenmiş DataFrame
        """
        features_df = df.copy()
        
        # Çeşitli periyotlar için momentum
        for period in [1, 3, 5, 10, 20]:
            features_df[f'momentum_{period}d'] = features_df['close'].pct_change(period)
            features_df[f'momentum_{period}d_rank'] = features_df[f'momentum_{period}d'].rolling(20).rank(pct=True)
        
        # Volatilite ayarlı momentum
        features_df['momentum_vol_adj'] = features_df['momentum_5d'] / features_df['volatility_20d']
        
        # Trend gücü
        features_df['trend_strength'] = np.abs(features_df['momentum_20d'])
        
        # Mean reversion sinyalleri
        features_df['mean_reversion'] = -features_df['momentum_5d']  # Negatif momentum = mean reversion
        
        return features_df
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Zaman tabanlı özellikler oluşturur
        
        Args:
            df: DataFrame
            
        Returns:
            Zaman özellikleri eklenmiş DataFrame
        """
        features_df = df.copy()
        
        # Gün, hafta, ay bilgileri
        features_df['day_of_week'] = features_df.index.dayofweek
        features_df['day_of_month'] = features_df.index.day
        features_df['month'] = features_df.index.month
        features_df['quarter'] = features_df.index.quarter
        
        # Hafta sonu etkisi
        features_df['is_monday'] = np.where(features_df['day_of_week'] == 0, 1, 0)
        features_df['is_friday'] = np.where(features_df['day_of_week'] == 4, 1, 0)
        
        # Ay sonu etkisi
        features_df['is_month_end'] = np.where(features_df['day_of_month'] >= 28, 1, 0)
        
        return features_df
    
    def create_target_variable(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Hedef değişkeni oluşturur (gelecek fiyat yönü)
        
        Args:
            df: DataFrame
            
        Returns:
            Hedef değişken eklenmiş DataFrame
        """
        features_df = df.copy()
        
        # Önce yatırım süresini kontrol et
        investment_horizon = self.config.get('MODEL_CONFIG', {}).get('investment_horizon', 'MEDIUM_TERM')
        horizon_configs = self.config.get('MODEL_CONFIG', {}).get('INVESTMENT_HORIZON_CONFIGS', {})
        horizon_config = horizon_configs.get(investment_horizon, horizon_configs.get('MEDIUM_TERM', {}))
        
        # Yatırım süresine göre tahmin periyotunu belirle
        prediction_days = horizon_config.get('prediction_days', 30)
        
        # Interval'a göre prediction horizon belirle
        interval = self.config.get('MODEL_CONFIG', {}).get('interval', '1d')
        if interval == '1h':
            # Günlük veri için 1h interval'ında kaç periyot var
            prediction_horizon = int(prediction_days * 24)  # Günlük veri = 24 saat
        elif interval == '4h':
            prediction_horizon = int(prediction_days * 6)  # Günlük veri = 6 periyot
        elif interval == '1wk':
            # Haftalık veri için
            prediction_horizon = max(1, int(prediction_days / 7))  # Kaç hafta
        else:  # 1d
            prediction_horizon = int(prediction_days)  # Kaç gün
        
        # Config'den override varsa kullan
        prediction_horizon = self.config.get('MODEL_CONFIG', {}).get('prediction_horizon', prediction_horizon)
        
        # Gelecek fiyat
        features_df['future_price'] = features_df['close'].shift(-prediction_horizon)
        
        # Gelecek getiri
        features_df['future_return'] = (features_df['future_price'] / features_df['close']) - 1
        
        # Yatırım süresine göre base threshold'ları al
        base_threshold_up = horizon_config.get('threshold_up', 0.02)
        base_threshold_down = horizon_config.get('threshold_down', -0.02)
        
        # Volatiliteyi hesapla
        volatility = features_df['returns'].rolling(20).std().mean() * np.sqrt(252)
        
        # ATR (Average True Range) hesapla - daha güvenilir volatilite ölçüsü
        atr = features_df['atr'].rolling(20).mean() if 'atr' in features_df.columns else features_df['high'] - features_df['low']
        atr_volatility = (atr / features_df['close']).mean() * np.sqrt(252)
        
        # Her iki volatilite metrikini birleştir
        combined_volatility = (volatility + atr_volatility) / 2
        
        # AKILLI DINAMIK THRESHOLD AYARLAMA
        # Yatırım süresine göre base threshold'ları kullan
        # Ama her hissenin kendi volatilitesine göre ayarla
        
        # Yatırım süresine özel volatilite ayarlamaları
        if investment_horizon == 'LONG_TERM':
            # Uzun vade: Yumuşak threshold'lar, trend takibi
            # Volatilite arttıkça threshold'ları sadece hafif artır
            if combined_volatility <= 0.20:
                volatility_scale = 0.6  # Küçük hareketleri yakala
                stock_type = "Çok Stabil"
            elif combined_volatility <= 0.35:
                volatility_scale = 0.8  # Hafif yumuşak
                stock_type = "Stabil"
            elif combined_volatility <= 0.50:
                volatility_scale = 1.0  # Normal
                stock_type = "Orta"
            elif combined_volatility <= 0.70:
                volatility_scale = 1.2  # Orta-güçlü
                stock_type = "Volatil"
            else:
                volatility_scale = 1.5  # Güçlü ama abartmasız
                stock_type = "Çok Volatil"
        
        elif investment_horizon == 'SHORT_TERM':
            # Kısa vade: Sıkı threshold'lar
            if combined_volatility <= 0.20:
                volatility_scale = 0.4
                stock_type = "Çok Stabil"
            elif combined_volatility <= 0.35:
                volatility_scale = 0.6
                stock_type = "Stabil"
            elif combined_volatility <= 0.50:
                volatility_scale = 1.0
                stock_type = "Orta"
            elif combined_volatility <= 0.70:
                volatility_scale = 1.8
                stock_type = "Volatil"
            else:
                volatility_scale = 2.5
                stock_type = "Çok Volatil"
        
        else:  # MEDIUM_TERM
            # Orta vade: Dengeli
            if combined_volatility <= 0.20:
                volatility_scale = 0.5
                stock_type = "Çok Stabil"
            elif combined_volatility <= 0.35:
                volatility_scale = 0.7
                stock_type = "Stabil"
            elif combined_volatility <= 0.50:
                volatility_scale = 1.0
                stock_type = "Orta"
            elif combined_volatility <= 0.70:
                volatility_scale = 1.5
                stock_type = "Volatil"
            else:
                volatility_scale = 2.0
                stock_type = "Çok Volatil"
        
        # Threshold'ları uygula
        threshold_up = base_threshold_up * volatility_scale
        threshold_down = base_threshold_down * volatility_scale
        
        # Min/Max sınırları koy (çok küçük veya çok büyük threshold'ları önle)
        min_threshold = 0.001  # En az %0.1 hareket
        max_threshold = 0.20   # En fazla %20 hareket (çok agresif olmasın)
        
        threshold_up = max(min_threshold, min(max_threshold, threshold_up))
        threshold_down = max(-max_threshold, min(-min_threshold, threshold_down))
        
        logger.info(f"Yatırım Süresi: {investment_horizon}, Horizon: {prediction_days} gün")
        logger.info(f"Hisse Tipi: {stock_type}, Volatilite: %{combined_volatility*100:.1f}, Scale: {volatility_scale:.1f}")
        logger.info(f"Threshold Up: %{threshold_up*100:.2f}, Threshold Down: %{threshold_down*100:.2f}")
        
        # Volatilite bilgilerini kaydet
        self.volatility_info = {
            'volatility': combined_volatility,
            'stock_type': stock_type,
            'volatility_scale': volatility_scale,
            'threshold_up': threshold_up,
            'threshold_down': threshold_down,
            'investment_horizon': investment_horizon
        }
        
        # Yön sınıflandırması (volatilite bazlı)
        features_df['direction'] = np.where(features_df['future_return'] > threshold_up, 1,  # Yukarı
                                  np.where(features_df['future_return'] < threshold_down, -1, 0))  # Aşağı, yoksa nötr
        
        # Binary classification (yukarı/aşağı) - GELİŞTİRİLMİŞ LOKİĞE:
        # 1 (Yukarı): Pozitif ve anlamlı yükseliş
        # 0 (Aşağı): Negatif ve anlamlı düşüş + küçük pozitif hareketler (nötr kabul etme)
        features_df['direction_binary'] = np.where(features_df['future_return'] > threshold_up, 1, 
                                   np.where(features_df['future_return'] < threshold_down, 0, 
                                   np.where(features_df['future_return'] > 0, 1, 0)))  # Küçük pozitif hareketlerde YUKARI
        
        # Volatilite ayarlı hedef
        features_df['future_return_vol_adj'] = features_df['future_return'] / features_df['volatility_20d']
        
        return features_df
    
    def create_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tüm özellikleri oluşturur
        
        Args:
            df: Ham OHLCV verisi
            
        Returns:
            Tüm özelliklerle zenginleştirilmiş DataFrame
        """
        logger.info("Teknik özellikler oluşturuluyor...")
        features_df = self.create_technical_features(df)
        
        logger.info("Momentum özellikleri oluşturuluyor...")
        features_df = self.create_momentum_features(features_df)
        
        logger.info("Zaman özellikleri oluşturuluyor...")
        features_df = self.create_time_features(features_df)
        
        logger.info("Hedef değişken oluşturuluyor...")
        features_df = self.create_target_variable(features_df)
        
        # Eksik değerleri temizle
        features_df = features_df.dropna()
        
        logger.info(f"Toplam {len(features_df.columns)} özellik oluşturuldu")
        logger.info(f"Veri boyutu: {features_df.shape}")
        
        return features_df
    
    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Model için kullanılacak özellik kolonlarını döndürür
        
        Args:
            df: Özelliklerle zenginleştirilmiş DataFrame
            
        Returns:
            Özellik kolonları listesi
        """
        # Hedef değişkenleri ve ham fiyat verilerini çıkar
        exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'adj_close',
                       'future_price', 'future_return', 'direction', 'direction_binary',
                       'future_return_vol_adj']
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        logger.info(f"Model için {len(feature_cols)} özellik seçildi")
        return feature_cols

def main():
    """Test fonksiyonu"""
    import yaml
    from data_loader import DataLoader
    
    # Config yükle
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Test verisi yükle
    loader = DataLoader(config)
    data = loader.fetch_stock_data("THYAO.IS", "1y")
    
    if not data.empty:
        # Özellik mühendisliği
        engineer = FeatureEngineer(config)
        features_df = engineer.create_all_features(data)
        
        # Özellik kolonlarını al
        feature_cols = engineer.get_feature_columns(features_df)
        
        print(f"\nToplam özellik sayısı: {len(feature_cols)}")
        print(f"Veri boyutu: {features_df.shape}")
        print(f"Hedef değişken dağılımı:")
        print(features_df['direction'].value_counts())
        
        # İlk birkaç özelliği göster
        print(f"\nİlk 10 özellik:")
        for col in feature_cols[:10]:
            print(f"- {col}")

if __name__ == "__main__":
    main()

