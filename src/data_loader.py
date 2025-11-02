"""
Veri Yükleme ve Temizleme Modülü
BIST hisse senetleri için OHLCV verisi çeker ve temizler
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, config: Dict):
        self.config = config
        self.data_dir = "data/raw"
        os.makedirs(self.data_dir, exist_ok=True)
        # BIST 100 endeks sembolü
        self.bist_index_symbol = config.get('MARKET_INDEX', {}).get('BIST100_SYMBOL', 'XU100.IS')
        
    def fetch_stock_data(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        """
        Tek bir hisse senedi için veri çeker
        
        Args:
            symbol: Hisse senedi sembolü (örn: "THYAO.IS")
            period: Veri periyodu ("1y", "2y", "5y", "max")
            interval: Zaman dilimi ("1d", "1h", "4h", "1wk")
            
        Returns:
            OHLCV verisi içeren DataFrame
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Interval parametresi ile veri çek
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"Veri bulunamadı: {symbol}")
                return pd.DataFrame()
                
            # Kolon isimlerini standardize et
            data.columns = [col.lower() for col in data.columns]
            data = data.rename(columns={'adj close': 'adj_close'})
            
            # Eksik değerleri temizle
            data = data.dropna()
            
            # Volume kontrolü (interval'e göre dinamik threshold)
            if interval in ["1h", "4h"]:
                # Saatlik veriler için daha düşük volume threshold
                min_volume = self.config.get('MODEL_CONFIG', {}).get('min_volume_threshold', 1000000) / 8
            else:
                min_volume = self.config.get('MODEL_CONFIG', {}).get('min_volume_threshold', 1000000)
            
            data = data[data['volume'] >= min_volume]
            
            logger.info(f"{symbol} için {len(data)} {interval} veri yüklendi")
            return data
            
        except Exception as e:
            logger.error(f"Veri yükleme hatası {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_multiple_stocks(self, symbols: List[str], period: str = "2y") -> Dict[str, pd.DataFrame]:
        """
        Birden fazla hisse senedi için veri çeker
        
        Args:
            symbols: Hisse senedi sembolleri listesi
            period: Veri periyodu
            
        Returns:
            Sembol -> DataFrame mapping'i
        """
        all_data = {}
        
        for symbol in symbols:
            logger.info(f"Veri yükleniyor: {symbol}")
            data = self.fetch_stock_data(symbol, period)
            
            if not data.empty:
                all_data[symbol] = data
                # Veriyi kaydet
                file_path = os.path.join(self.data_dir, f"{symbol.replace('.IS', '')}.csv")
                data.to_csv(file_path)
            else:
                logger.warning(f"Veri yüklenemedi: {symbol}")
                
        logger.info(f"Toplam {len(all_data)} hisse senedi verisi yüklendi")
        return all_data
    
    def load_saved_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Kaydedilmiş veriyi yükler
        
        Args:
            symbol: Hisse senedi sembolü
            
        Returns:
            DataFrame veya None
        """
        file_path = os.path.join(self.data_dir, f"{symbol.replace('.IS', '')}.csv")
        
        if os.path.exists(file_path):
            try:
                data = pd.read_csv(file_path, index_col=0, parse_dates=True)
                logger.info(f"Kaydedilmiş veri yüklendi: {symbol}")
                return data
            except Exception as e:
                logger.error(f"Kaydedilmiş veri yükleme hatası {symbol}: {str(e)}")
                return None
        else:
            logger.warning(f"Kaydedilmiş veri bulunamadı: {symbol}")
            return None
    
    def update_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Mevcut verileri günceller (son 30 gün)
        
        Args:
            symbols: Güncellenecek semboller
            
        Returns:
            Güncellenmiş veriler
        """
        updated_data = {}
        
        for symbol in symbols:
            # Mevcut veriyi yükle
            existing_data = self.load_saved_data(symbol)
            
            if existing_data is not None:
                # Son tarihi bul
                last_date = existing_data.index.max()
                
                # Son 30 günü tekrar çek
                ticker = yf.Ticker(symbol)
                new_data = ticker.history(start=last_date, period="30d")
                
                if not new_data.empty:
                    # Yeni veriyi ekle
                    new_data.columns = [col.lower() for col in new_data.columns]
                    new_data = new_data.rename(columns={'adj close': 'adj_close'})
                    
                    # Duplicate'leri temizle ve birleştir
                    combined_data = pd.concat([existing_data, new_data])
                    combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
                    combined_data = combined_data.sort_index()
                    
                    updated_data[symbol] = combined_data
                    
                    # Güncellenmiş veriyi kaydet
                    file_path = os.path.join(self.data_dir, f"{symbol.replace('.IS', '')}.csv")
                    combined_data.to_csv(file_path)
                    
                    logger.info(f"Veri güncellendi: {symbol}")
            else:
                # Veri yoksa tamamen yükle
                data = self.fetch_stock_data(symbol)
                if not data.empty:
                    updated_data[symbol] = data
                    
        return updated_data
    
    def fetch_index_data(self, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        """
        BIST 100 endeksi verisi çeker
        
        Args:
            period: Veri periyodu ("1y", "2y", "5y", "max")
            interval: Zaman dilimi ("1d", "1h", "4h", "1wk")
            
        Returns:
            BIST 100 endeksi OHLCV verisi içeren DataFrame
        """
        try:
            ticker = yf.Ticker(self.bist_index_symbol)
            
            # Interval parametresi ile veri çek
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"BIST 100 endeks verisi bulunamadı: {self.bist_index_symbol}")
                return pd.DataFrame()
                
            # Kolon isimlerini standardize et
            data.columns = [col.lower() for col in data.columns]
            data = data.rename(columns={'adj close': 'adj_close'})
            
            # Eksik değerleri temizle
            data = data.dropna()
            
            logger.info(f"BIST 100 endeksi için {len(data)} {interval} veri yüklendi")
            return data
            
        except Exception as e:
            logger.error(f"BIST 100 endeks verisi yükleme hatası: {str(e)}")
            return pd.DataFrame()
    
    def get_index_data(self, period: str = "2y", interval: str = "1d", use_cache: bool = True) -> pd.DataFrame:
        """
        BIST 100 endeksi verisini yükler (cache desteği ile)
        
        Args:
            period: Veri periyodu
            interval: Zaman dilimi
            use_cache: Cache kullanılsın mı
            
        Returns:
            BIST 100 endeksi DataFrame'i
        """
        cache_file = os.path.join(self.data_dir, f"XU100_index.csv")
        
        # Cache kontrolü
        if use_cache and os.path.exists(cache_file):
            try:
                cached_data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                # Cache'deki son tarihi kontrol et
                last_date = cached_data.index.max()
                days_diff = (datetime.now() - last_date).days
                
                # Cache 1 günden eskiyse güncelle
                if days_diff < 1:
                    logger.info("BIST 100 endeks verisi cache'den yüklendi")
                    return cached_data
            except Exception as e:
                logger.warning(f"Cache okuma hatası: {str(e)}")
        
        # Veriyi çek
        data = self.fetch_index_data(period, interval)
        
        # Cache'e kaydet
        if not data.empty and use_cache:
            try:
                data.to_csv(cache_file)
                logger.info(f"BIST 100 endeks verisi cache'e kaydedildi")
            except Exception as e:
                logger.warning(f"Cache kaydetme hatası: {str(e)}")
        
        return data

def main():
    """Test fonksiyonu"""
    import yaml
    
    # Config yükle
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # DataLoader oluştur
    loader = DataLoader(config)
    
    # Test sembolleri
    test_symbols = ["THYAO.IS", "AKBNK.IS", "BIMAS.IS"]
    
    # Veri yükle
    data = loader.fetch_multiple_stocks(test_symbols)
    
    # Sonuçları göster
    for symbol, df in data.items():
        print(f"\n{symbol}:")
        print(f"Veri boyutu: {df.shape}")
        print(f"Tarih aralığı: {df.index.min()} - {df.index.max()}")
        print(f"Son fiyat: {df['close'].iloc[-1]:.2f}")

if __name__ == "__main__":
    main()

