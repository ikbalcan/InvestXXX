#!/usr/bin/env python3
"""
Hisse Senedi Yön Tahmini Sistemi - Ana Çalıştırma Scripti
"""

import sys
import os
import yaml
import logging
import argparse
import pandas as pd
import numpy as np
import time
import schedule
from datetime import datetime
from typing import Dict, List

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from backtest import Backtester
from live_trade import PaperTrader, LiveSignalGenerator

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system.log'),
        logging.StreamHandler()
    ]
)


logger = logging.getLogger(__name__)

class StockPredictionSystem:
    def __init__(self, config_path: str = 'config.yaml'):
        """Sistemi başlatır"""
        self.config_path = config_path
        self.config = self.load_config()
        
        # Modülleri başlat
        self.data_loader = DataLoader(self.config)
        self.feature_engineer = FeatureEngineer(self.config, data_loader=self.data_loader)
        self.predictor = StockDirectionPredictor(self.config)
        self.backtester = Backtester(self.config)
        self.paper_trader = PaperTrader(self.config)
        self.signal_generator = LiveSignalGenerator(self.config)
        
        logger.info("Hisse Senedi Yön Tahmini Sistemi başlatıldı")
    
    def load_config(self) -> Dict:
        """Konfigürasyon dosyasını yükler"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Konfigürasyon yüklendi: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Konfigürasyon yükleme hatası: {str(e)}")
            raise
    
    def train_model(self, symbols: List[str] = None, period: str = "2y", model_name: str = None) -> str:
        """Model eğitir"""
        logger.info("Model eğitimi başlıyor...")
        
        if symbols is None:
            symbols = self.config.get('TARGET_STOCKS', [])
        
        # Veri yükle
        logger.info(f"Veri yükleniyor: {symbols}")
        all_data = self.data_loader.fetch_multiple_stocks(symbols, period)
        
        if not all_data:
            logger.error("Veri yüklenemedi!")
            return None
        
        # BIST 100 endeks verisini yükle (tüm hisseler için ortak)
        logger.info("BIST 100 endeks verisi yükleniyor...")
        index_data = self.data_loader.get_index_data(period=period)
        
        # Özellikleri oluştur ve birleştir
        all_features = []
        
        for symbol, data in all_data.items():
            logger.info(f"Özellikler oluşturuluyor: {symbol}")
            features_df = self.feature_engineer.create_all_features(data, index_data=index_data)
            
            if not features_df.empty:
                features_df['symbol'] = symbol
                all_features.append(features_df)
        
        if not all_features:
            logger.error("Özellik oluşturulamadı!")
            return None
        
        # Tüm verileri birleştir
        combined_features = pd.concat(all_features, ignore_index=False)
        logger.info(f"Birleştirilmiş veri boyutu: {combined_features.shape}")
        
        # Model için veriyi hazırla
        X, y = self.predictor.prepare_data(combined_features)
        
        # Model eğitimi
        results = self.predictor.train_model(X, y)
        
        # Modeli kaydet
        if model_name:
            # Özel isimle kaydet
            model_path = self.predictor.save_model(f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib")
        else:
            model_path = self.predictor.save_model()
        
        logger.info("Model eğitimi tamamlandı!")
        logger.info(f"Test Accuracy: {results['test_metrics']['accuracy']:.4f}")
        logger.info(f"Test F1 Score: {results['test_metrics']['f1']:.4f}")
        logger.info(f"Model kaydedildi: {model_path}")
        
        return model_path
    
    def run_backtest(self, model_path: str, symbols: List[str] = None) -> Dict:
        """Backtest çalıştırır"""
        logger.info("Backtest başlıyor...")
        
        if symbols is None:
            symbols = self.config.get('TARGET_STOCKS', [])
        
        # Modeli yükle
        if not self.predictor.load_model(model_path):
            logger.error("Model yüklenemedi!")
            return None
        
        all_results = {}
        
        # BIST 100 endeks verisini yükle (tüm hisseler için ortak)
        logger.info("BIST 100 endeks verisi yükleniyor...")
        index_data = self.data_loader.get_index_data(period="2y")
        
        for symbol in symbols:
            logger.info(f"Backtest çalıştırılıyor: {symbol}")
            
            # Veri yükle
            data = self.data_loader.fetch_stock_data(symbol, "2y")
            
            if data.empty:
                logger.warning(f"Veri bulunamadı: {symbol}")
                continue
            
            # Özellikleri oluştur
            features_df = self.feature_engineer.create_all_features(data, index_data=index_data)
            
            if features_df.empty:
                logger.warning(f"Özellik oluşturulamadı: {symbol}")
                continue
            
            # Tahminler
            X, y = self.predictor.prepare_data(features_df)
            predictions, probabilities = self.predictor.predict(X)
            
            # Backtest
            results = self.backtester.run_backtest(features_df, predictions, probabilities, symbol)
            
            if results:
                all_results[symbol] = results
                
                # Grafik kaydet
                plot_path = f"logs/backtest_{symbol}_{datetime.now().strftime('%Y%m%d')}.png"
                self.backtester.plot_results(plot_path)
                
                # Rapor yazdır
                report = self.backtester.generate_report()
                logger.info(f"\n{report}")
        
        # Genel özet
        if all_results:
            total_return = sum([r['total_return'] for r in all_results.values()]) / len(all_results)
            logger.info(f"\n=== GENEL BACKTEST ÖZETİ ===")
            logger.info(f"Ortalama Getiri: {total_return:.2%}")
            logger.info(f"Test Edilen Hisse Sayısı: {len(all_results)}")
        
        return all_results
    
    def run_paper_trading(self, model_path: str, symbols: List[str] = None) -> None:
        """Paper trading başlatır"""
        logger.info("Paper trading başlıyor...")
        
        if symbols is None:
            symbols = self.config.get('TARGET_STOCKS', [])
        
        # Modeli yükle
        if not self.predictor.load_model(model_path):
            logger.error("Model yüklenemedi!")
            return
        
        # Signal generator'ı başlat
        self.signal_generator.load_model(model_path)
        
        # Günlük sinyal üretimi
        def daily_signal_job():
            self.signal_generator.run_daily_signal_generation()
        
        # Schedule ayarla (her gün saat 09:30'da)
        schedule.every().day.at("09:30").do(daily_signal_job)
        
        logger.info("Paper trading başlatıldı. Günlük sinyaller saat 09:30'da üretilecek.")
        logger.info("Çıkmak için Ctrl+C basın.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Her dakika kontrol et
        except KeyboardInterrupt:
            logger.info("Paper trading durduruldu.")
    
    def generate_signals(self, model_path: str, symbols: List[str] = None) -> Dict:
        """Anlık sinyal üretir"""
        logger.info("Sinyal üretimi başlıyor...")
        
        if symbols is None:
            symbols = self.config.get('TARGET_STOCKS', [])
        
        # Modeli yükle
        if not self.predictor.load_model(model_path):
            logger.error("Model yüklenemedi!")
            return None
        
        # Signal generator'ı başlat
        self.signal_generator.load_model(model_path)
        
        # Sinyalleri üret
        signals = self.signal_generator.generate_signals(symbols)
        
        # Sonuçları göster
        logger.info("\n=== SİNYAL RAPORU ===")
        for symbol, signal in signals.items():
            if signal:
                action = "🟢 AL" if signal['prediction'] == 1 else "🔴 SAT"
                logger.info(f"{symbol}: {action} - Güven: {signal['confidence']:.2f} - "
                          f"Fiyat: {signal['current_price']:.2f} - "
                          f"İşlem: {signal['action_taken']}")
        
        return signals
    
    def show_portfolio_status(self) -> None:
        """Portföy durumunu gösterir"""
        summary = self.paper_trader.get_portfolio_summary()
        
        logger.info("\n=== PORTFÖY DURUMU ===")
        logger.info(f"Mevcut Sermaye: {summary['current_capital']:,.0f} TL")
        logger.info(f"Toplam Değer: {summary['total_value']:,.0f} TL")
        logger.info(f"Toplam Getiri: {summary['total_return']:.2%}")
        logger.info(f"Aktif Pozisyonlar: {summary['positions']}")
        
        if summary['position_values']:
            logger.info("\nPozisyonlar:")
            for symbol, value in summary['position_values'].items():
                logger.info(f"  {symbol}: {value:,.0f} TL")
        
        if summary['recent_trades']:
            logger.info("\nSon İşlemler:")
            for trade in summary['recent_trades']:
                logger.info(f"  {trade['date'].strftime('%H:%M')} - {trade['symbol']} - "
                          f"{trade['action']} - {trade['price']:.2f}")

def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description='Hisse Senedi Yön Tahmini Sistemi')
    parser.add_argument('command', choices=['train', 'backtest', 'paper-trade', 'signals', 'portfolio'],
                       help='Çalıştırılacak komut')
    parser.add_argument('--model-path', help='Model dosya yolu')
    parser.add_argument('--symbols', nargs='+', help='İşlem yapılacak hisse senetleri')
    parser.add_argument('--period', default='2y', help='Veri periyodu')
    parser.add_argument('--model-name', help='Model ismi (opsiyonel)')
    
    args = parser.parse_args()
    
    try:
        # Sistemi başlat
        system = StockPredictionSystem()
        
        if args.command == 'train':
            # Model eğitimi
            model_path = system.train_model(args.symbols, args.period, args.model_name)
            if model_path:
                logger.info(f"Model eğitimi tamamlandı: {model_path}")
        
        elif args.command == 'backtest':
            # Backtest
            if not args.model_path:
                logger.error("Backtest için model yolu gerekli!")
                return
            
            results = system.run_backtest(args.model_path, args.symbols)
            if results:
                logger.info("Backtest tamamlandı!")
        
        elif args.command == 'paper-trade':
            # Paper trading
            if not args.model_path:
                logger.error("Paper trading için model yolu gerekli!")
                return
            
            system.run_paper_trading(args.model_path, args.symbols)
        
        elif args.command == 'signals':
            # Sinyal üretimi
            if not args.model_path:
                logger.error("Sinyal üretimi için model yolu gerekli!")
                return
            
            signals = system.generate_signals(args.model_path, args.symbols)
            if signals:
                logger.info("Sinyal üretimi tamamlandı!")
        
        elif args.command == 'portfolio':
            # Portföy durumu
            system.show_portfolio_status()
    
    except Exception as e:
        logger.error(f"Sistem hatası: {str(e)}")
        raise

if __name__ == "__main__":
    # Import and run the Streamlit dashboard
    try:
        from dashboard_main import main as run_dashboard
        run_dashboard()
    except Exception as e:
        logger.error(f"Could not run dashboard: {e}")
        # Fallback to CLI only if CLI args are provided
        import sys as _sys
        if len(_sys.argv) > 1:
            main()
        else:
            # No CLI args provided; avoid argparse error and exit gracefully
            logger.info("No CLI arguments provided; exiting without invoking CLI parser.")
