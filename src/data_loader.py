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

