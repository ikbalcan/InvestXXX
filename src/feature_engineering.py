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
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            features_df[f'sma_{period}'] = ta.trend.sma_indicator(features_df['close'], period)
            features_df[f'ema_{period}'] = ta.trend.ema_indicator(features_df['close'], period)
            
        # Moving average crossovers
        features_df['sma_5_20_cross'] = np.where(features_df['sma_5'] > features_df['sma_20'], 1, 0)
        features_df['sma_10_50_cross'] = np.where(features_df['sma_10'] > features_df['sma_50'], 1, 0)
        
        # Bollinger Bands
        bb = ta.volatility.bollinger_hband_indicator(features_df['close'])
        features_df['bb_position'] = (features_df['close'] - features_df['sma_20']) / bb
        
        # Volume özellikleri
        features_df['volume_sma_20'] = features_df['volume'].rolling(20).mean()
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma_20']
        features_df['volume_spike'] = np.where(features_df['volume_ratio'] > 2, 1, 0)
        
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
        
        prediction_horizon = self.config.get('MODEL_CONFIG', {}).get('prediction_horizon', 1)
        
        # Gelecek fiyat
        features_df['future_price'] = features_df['close'].shift(-prediction_horizon)
        
        # Gelecek getiri
        features_df['future_return'] = (features_df['future_price'] / features_df['close']) - 1
        
        # Volatilite hesapla
        volatility = features_df['returns'].rolling(20).std().mean() * np.sqrt(252)
        
        # Volatiliteye göre dinamik threshold belirle
        if volatility <= 0.25:
            threshold = 0.01  # %1+ hareket
        elif volatility <= 0.40:
            threshold = 0.015  # %1.5+ hareket
        elif volatility <= 0.60:
            threshold = 0.02  # %2+ hareket
        else:
            threshold = 0.03  # %3+ hareket
        
        logger.info(f"Volatilite: %{volatility*100:.1f}, Threshold: %{threshold*100:.1f}")
        
        # Yön sınıflandırması (volatilite bazlı)
        features_df['direction'] = np.where(features_df['future_return'] > threshold, 1,  # Yukarı
                                  np.where(features_df['future_return'] < -threshold, -1, 0))  # Aşağı, yoksa nötr
        
        # Binary classification (yukarı/aşağı) - volatilite bazlı
        features_df['direction_binary'] = np.where(features_df['future_return'] > threshold, 1, 0)
        
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

