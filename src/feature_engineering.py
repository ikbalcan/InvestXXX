"""
Özellik Mühendisliği Modülü
Teknik analiz göstergeleri ve momentum özelliklerini oluşturur
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    def __init__(self, config: Dict, data_loader=None):
        self.config = config
        self.lookback_window = config.get('MODEL_CONFIG', {}).get('lookback_window', 30)
        self.data_loader = data_loader  # DataLoader instance (opsiyonel)
        # Volatilite analizi bilgilerini sakla
        self.volatility_info = {
            'volatility': None,
            'stock_type': None,
            'volatility_scale': None,
            'threshold_up': None,
            'threshold_down': None
        }
        # Endeks verisi cache
        self._index_data_cache = None
        
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
    
    def create_index_features(self, df: pd.DataFrame, index_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        BIST 100 endeksi ile ilgili özellikler oluşturur
        
        Args:
            df: Hisse senedi DataFrame'i
            index_data: BIST 100 endeks verisi (None ise data_loader'dan yüklenir)
            
        Returns:
            Endeks özellikleri eklenmiş DataFrame
        """
        features_df = df.copy()
        
        # Endeks verisini yükle
        if index_data is None:
            if self.data_loader is None:
                logger.warning("DataLoader bulunamadı, endeks özellikleri atlanıyor")
                return features_df
            
            # Cache kontrolü
            if self._index_data_cache is None:
                try:
                    # Hisse verisiyle aynı tarih aralığını kullan
                    period = "2y"  # Varsayılan
                    interval = self.config.get('MODEL_CONFIG', {}).get('interval', '1d')
                    self._index_data_cache = self.data_loader.get_index_data(period=period, interval=interval)
                except Exception as e:
                    logger.error(f"Endeks verisi yüklenemedi: {str(e)}")
                    return features_df
            
            index_data = self._index_data_cache
        
        if index_data.empty:
            logger.warning("Endeks verisi boş, endeks özellikleri atlanıyor")
            return features_df
        
        # Tarih uyumluluğunu sağla
        # Her iki DataFrame'in de ortak tarihlerini bul
        common_dates = df.index.intersection(index_data.index)
        
        if len(common_dates) == 0:
            logger.warning("Hisse ve endeks verilerinde ortak tarih bulunamadı")
            return features_df
        
        # Endeks verilerini hisse verisiyle birleştir
        index_close = index_data.loc[common_dates, 'close']
        index_returns = index_close.pct_change()
        
        # Hisse verilerini aynı tarihler için al
        stock_close = df.loc[common_dates, 'close']
        stock_returns = stock_close.pct_change()
        
        # 1. Beta (Rolling Beta) - Hisse ve endeks getirileri arasındaki ilişki
        # Beta = Cov(stock_returns, index_returns) / Var(index_returns)
        for window in [20, 60, 120]:
            beta_values = []
            for i in range(len(common_dates)):
                if i < window:
                    beta_values.append(np.nan)
                else:
                    stock_window = stock_returns.iloc[i-window:i]
                    index_window = index_returns.iloc[i-window:i]
                    # NaN değerleri temizle
                    valid_mask = ~(stock_window.isna() | index_window.isna())
                    if valid_mask.sum() < 10:  # Minimum 10 veri noktası
                        beta_values.append(np.nan)
                    else:
                        stock_clean = stock_window[valid_mask]
                        index_clean = index_window[valid_mask]
                        if index_clean.var() > 0:
                            beta = np.cov(stock_clean, index_clean)[0, 1] / index_clean.var()
                            beta_values.append(beta)
                        else:
                            beta_values.append(np.nan)
            
            features_df[f'beta_{window}d'] = pd.Series(beta_values, index=common_dates).reindex(df.index)
        
        # 2. Rolling Correlation - Hisse ve endeks arasındaki korelasyon
        for window in [20, 60, 120]:
            corr_values = []
            for i in range(len(common_dates)):
                if i < window:
                    corr_values.append(np.nan)
                else:
                    stock_window = stock_returns.iloc[i-window:i]
                    index_window = index_returns.iloc[i-window:i]
                    valid_mask = ~(stock_window.isna() | index_window.isna())
                    if valid_mask.sum() < 10:
                        corr_values.append(np.nan)
                    else:
                        stock_clean = stock_window[valid_mask]
                        index_clean = index_window[valid_mask]
                        corr = stock_clean.corr(index_clean)
                        corr_values.append(corr if not np.isnan(corr) else 0)
            
            features_df[f'index_correlation_{window}d'] = pd.Series(corr_values, index=common_dates).reindex(df.index)
        
        # 3. Relative Strength - Hisse performansı vs Endeks performansı
        for period in [5, 10, 20, 60]:
            stock_perf = stock_returns.rolling(period).sum()
            index_perf = index_returns.rolling(period).sum()
            relative_strength = stock_perf - index_perf
            features_df[f'relative_strength_{period}d'] = relative_strength.reindex(df.index)
        
        # 4. Divergence Detection - Hisse ve endeks ters hareket ettiğinde
        # Pozitif divergence: Endeks düşerken hisse yükseliyor
        # Negatif divergence: Endeks yükselirken hisse düşüyor
        
        # Momentum divergence (kısa vade) - Threshold ile daha güvenilir
        stock_momentum_5d = stock_returns.rolling(5).sum()
        index_momentum_5d = index_returns.rolling(5).sum()
        
        # Threshold: En az %1 hareket olmalı (gürültüyü filtrele)
        momentum_threshold = 0.01  # %1
        
        # Pozitif divergence: Endeks belirgin düşerken hisse belirgin yükseliyor
        positive_divergence = ((index_momentum_5d < -momentum_threshold) & (stock_momentum_5d > momentum_threshold)).astype(int)
        features_df['positive_divergence_5d'] = positive_divergence.reindex(df.index, fill_value=0)
        
        # Negatif divergence: Endeks belirgin yükselirken hisse belirgin düşüyor
        negative_divergence = ((index_momentum_5d > momentum_threshold) & (stock_momentum_5d < -momentum_threshold)).astype(int)
        features_df['negative_divergence_5d'] = negative_divergence.reindex(df.index, fill_value=0)
        
        # 20 günlük divergence - Daha uzun vadeli ve güvenilir
        stock_momentum_20d = stock_returns.rolling(20).sum()
        index_momentum_20d = index_returns.rolling(20).sum()
        # 20 günlük için daha yumuşak threshold (%0.5)
        momentum_threshold_20d = 0.005  # %0.5
        positive_divergence_20d = ((index_momentum_20d < -momentum_threshold_20d) & (stock_momentum_20d > momentum_threshold_20d)).astype(int)
        negative_divergence_20d = ((index_momentum_20d > momentum_threshold_20d) & (stock_momentum_20d < -momentum_threshold_20d)).astype(int)
        features_df['positive_divergence_20d'] = positive_divergence_20d.reindex(df.index, fill_value=0)
        features_df['negative_divergence_20d'] = negative_divergence_20d.reindex(df.index, fill_value=0)
        
        # 5. Endeks Momentum ve Volatilite Özellikleri
        # NOT: index_momentum pozitif = endeks yükselişte (AL için pozitif sinyal)
        #      index_momentum negatif = endeks düşüşte (SAT için pozitif sinyal)
        index_momentum_5d = index_returns.rolling(5).sum()
        index_momentum_20d = index_returns.rolling(20).sum()
        index_volatility_20d = index_returns.rolling(20).std()
        
        # Endeks momentum özelliklerini ekle (model için doğru yönde)
        features_df['index_momentum_5d'] = index_momentum_5d.reindex(df.index)
        features_df['index_momentum_20d'] = index_momentum_20d.reindex(df.index)
        features_df['index_volatility_20d'] = index_volatility_20d.reindex(df.index)
        
        # Ek olarak: Endeks momentum'un normalize edilmiş versiyonları
        # Bu, modelin endeks momentum'unu daha iyi yorumlamasına yardımcı olur
        # Pozitif momentum = pozitif değer (AL sinyali için)
        # Negatif momentum = negatif değer (SAT sinyali için)
        # Normalize: -1 ile 1 arasında değerler
        if len(index_momentum_5d) > 0 and index_momentum_5d.std() > 0:
            features_df['index_momentum_5d_normalized'] = (index_momentum_5d / index_momentum_5d.abs().rolling(60).mean()).reindex(df.index)
        else:
            features_df['index_momentum_5d_normalized'] = 0
        
        if len(index_momentum_20d) > 0 and index_momentum_20d.std() > 0:
            features_df['index_momentum_20d_normalized'] = (index_momentum_20d / index_momentum_20d.abs().rolling(60).mean()).reindex(df.index)
        else:
            features_df['index_momentum_20d_normalized'] = 0
        
        # 6. Hisse/Endeks Fiyat Oranı (normalize edilmiş)
        price_ratio = stock_close / index_close
        price_ratio_normalized = (price_ratio - price_ratio.rolling(60).mean()) / price_ratio.rolling(60).std()
        features_df['price_vs_index_ratio'] = price_ratio.reindex(df.index)
        features_df['price_vs_index_ratio_normalized'] = price_ratio_normalized.reindex(df.index)
        
        # 7. Endeks RSI ve MACD
        index_rsi = ta.momentum.rsi(index_close)
        index_macd = ta.trend.macd(index_close)
        index_macd_signal = ta.trend.macd_signal(index_close)
        
        features_df['index_rsi'] = index_rsi.reindex(df.index)
        features_df['index_macd'] = index_macd.reindex(df.index)
        features_df['index_macd_diff'] = (index_macd - index_macd_signal).reindex(df.index)
        
        logger.info(f"Endeks özellikleri oluşturuldu: {len([col for col in features_df.columns if 'index' in col or 'beta' in col or 'divergence' in col or 'relative' in col])} özellik")
        
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
    
    def create_all_features(self, df: pd.DataFrame, index_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Tüm özellikleri oluşturur
        
        Args:
            df: Ham OHLCV verisi
            index_data: BIST 100 endeks verisi (opsiyonel)
            
        Returns:
            Tüm özelliklerle zenginleştirilmiş DataFrame
        """
        logger.info("Teknik özellikler oluşturuluyor...")
        features_df = self.create_technical_features(df)
        
        logger.info("Momentum özellikleri oluşturuluyor...")
        features_df = self.create_momentum_features(features_df)
        
        logger.info("Endeks özellikleri oluşturuluyor...")
        features_df = self.create_index_features(features_df, index_data)
        
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
                       'future_return_vol_adj', 'price_vs_index_ratio']  # price_vs_index_ratio ham fiyat içeriyor
        
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

