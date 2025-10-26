"""
Paper Trading ve Canlı Sinyal Sistemi
Gerçek zamanlı tahminler ve simüle edilmiş işlemler
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
import schedule
import time

logger = logging.getLogger(__name__)

class PaperTrader:
    def __init__(self, config: Dict):
        self.config = config
        self.risk_config = config.get('RISK_MANAGEMENT', {})
        self.telegram_config = config.get('TELEGRAM', {})
        
        # Paper trading parametreleri - localStorage'dan yükle
        self.initial_capital = self.load_initial_capital()
        self.current_capital = self.load_current_capital()
        self.positions = self.load_positions()  # {symbol: {'quantity': float, 'entry_price': float, 'entry_date': datetime}}
        self.trade_history = self.load_trade_history()
        
        # Risk yönetimi
        self.max_position_size = self.risk_config.get('max_position_size', 0.02)
        self.stop_loss_pct = self.risk_config.get('stop_loss_pct', 0.05)
        self.take_profit_pct = self.risk_config.get('take_profit_pct', 0.10)
        self.max_daily_trades = self.risk_config.get('max_daily_trades', 5)
        
        # Fiyat cache sistemi
        self.price_cache = {}  # {symbol: {'price': float, 'timestamp': datetime}}
        self.cache_duration = 300  # 5 dakika cache süresi
        
        # Telegram bot
        self.telegram_bot = None
        if self.telegram_config.get('enabled', False):
            try:
                # Telegram bot kodu burada olacak (opsiyonel)
                pass
            except Exception as e:
                logger.warning(f"Telegram bot başlatılamadı: {str(e)}")
        
        # Log dosyaları
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # localStorage dosyası
        self.local_storage_file = os.path.join(self.log_dir, "paper_trading_localStorage.json")
    
    def load_initial_capital(self) -> float:
        """Başlangıç sermayesini localStorage'dan yükler"""
        try:
            if hasattr(self, 'local_storage_file') and os.path.exists(self.local_storage_file):
                with open(self.local_storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('initial_capital', 100000)
        except Exception as e:
            logger.warning(f"localStorage yükleme hatası: {str(e)}")
        return 100000  # Varsayılan değer
    
    def load_current_capital(self) -> float:
        """Mevcut sermayeyi localStorage'dan yükler"""
        try:
            if hasattr(self, 'local_storage_file') and os.path.exists(self.local_storage_file):
                with open(self.local_storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('current_capital', 100000)
        except Exception as e:
            logger.warning(f"localStorage yükleme hatası: {str(e)}")
        return 100000  # Varsayılan değer
    
    def load_positions(self) -> Dict:
        """Pozisyonları localStorage'dan yükler"""
        try:
            if hasattr(self, 'local_storage_file') and os.path.exists(self.local_storage_file):
                with open(self.local_storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    positions = data.get('positions', {})
                    
                    # Datetime objelerini geri yükle
                    for symbol, pos in positions.items():
                        pos['entry_date'] = datetime.fromisoformat(pos['entry_date'])
                    
                    return positions
        except Exception as e:
            logger.warning(f"localStorage yükleme hatası: {str(e)}")
        return {}
    
    def load_trade_history(self) -> List:
        """İşlem geçmişini localStorage'dan yükler"""
        try:
            if hasattr(self, 'local_storage_file') and os.path.exists(self.local_storage_file):
                with open(self.local_storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    trade_history = data.get('trade_history', [])
                    
                    # Datetime objelerini geri yükle
                    for trade in trade_history:
                        trade['date'] = datetime.fromisoformat(trade['date'])
                    
                    return trade_history
        except Exception as e:
            logger.warning(f"localStorage yükleme hatası: {str(e)}")
        return []
    
    def save_to_localStorage(self):
        """Verileri localStorage'a kaydeder"""
        try:
            data = {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'positions': {},
                'trade_history': [],
                'last_updated': datetime.now().isoformat()
            }
            
            # Pozisyonları JSON serializable hale getir
            for symbol, pos in self.positions.items():
                data['positions'][symbol] = {
                    'quantity': pos['quantity'],
                    'entry_price': pos['entry_price'],
                    'entry_date': pos['entry_date'].isoformat(),
                    'confidence': pos['confidence']
                }
            
            # Trade history'yi JSON serializable hale getir
            for trade in self.trade_history:
                trade_copy = trade.copy()
                trade_copy['date'] = trade['date'].isoformat()
                data['trade_history'].append(trade_copy)
            
            with open(self.local_storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Veriler localStorage'a kaydedildi: {self.local_storage_file}")
            
        except Exception as e:
            logger.error(f"localStorage kaydetme hatası: {str(e)}")
    
    def reset_portfolio(self, new_capital: float = 100000):
        """Portföyü sıfırlar"""
        self.initial_capital = new_capital
        self.current_capital = new_capital
        self.positions = {}
        self.trade_history = []
        self.save_to_localStorage()
        logger.info(f"Portföy sıfırlandı. Yeni sermaye: {new_capital:,.0f} TL")
        
    def send_telegram_message(self, message: str) -> bool:
        """Telegram mesajı gönderir (opsiyonel)"""
        if not self.telegram_bot:
            logger.info(f"Telegram mesajı: {message}")
            return False
            
        try:
            # Telegram bot kodu burada olacak
            logger.info(f"Telegram mesajı: {message}")
            return True
        except Exception as e:
            logger.error(f"Telegram mesaj hatası: {str(e)}")
            return False
    
    def calculate_position_size(self, price: float, confidence: float) -> float:
        """Pozisyon büyüklüğünü hesaplar"""
        base_position = self.current_capital * self.max_position_size
        confidence_multiplier = min(confidence * 2, 1.0)
        return base_position * confidence_multiplier
    
    def can_trade(self, symbol: str) -> bool:
        """İşlem yapılabilir mi kontrol eder"""
        # Günlük işlem sayısı kontrolü
        today = datetime.now().date()
        today_trades = [t for t in self.trade_history if t['date'].date() == today]
        
        if len(today_trades) >= self.max_daily_trades:
            logger.warning(f"Günlük işlem limiti aşıldı: {symbol}")
            return False
        
        return True
    
    def open_position(self, symbol: str, price: float, confidence: float, 
                     prediction: int) -> bool:
        """Pozisyon açar"""
        if not self.can_trade(symbol):
            return False
        
        if prediction != 1:  # Sadece yükseliş sinyali için pozisyon aç
            return False
        
        if symbol in self.positions:
            logger.warning(f"Zaten pozisyon var: {symbol}")
            return False
        
        # Pozisyon büyüklüğünü hesapla
        position_size = self.calculate_position_size(price, confidence)
        quantity = position_size / price
        
        # Sermaye kontrolü
        if position_size > self.current_capital:
            logger.warning(f"Yetersiz sermaye: {symbol}")
            return False
        
        # Pozisyonu aç
        self.positions[symbol] = {
            'quantity': quantity,
            'entry_price': price,
            'entry_date': datetime.now(),
            'confidence': confidence
        }
        
        # Sermayeyi güncelle
        self.current_capital -= position_size
        
        # İşlemi kaydet
        trade = {
            'date': datetime.now(),
            'symbol': symbol,
            'action': 'BUY',
            'price': price,
            'quantity': quantity,
            'position_size': position_size,
            'confidence': confidence,
            'capital_after': self.current_capital
        }
        
        self.trade_history.append(trade)
        
        # localStorage'a kaydet
        self.save_to_localStorage()
        
        # Log ve bildirim
        message = f"🟢 POZİSYON AÇILDI\n{symbol}\nFiyat: {price:.2f} TL\nMiktar: {quantity:.0f}\nGüven: {confidence:.2f}"
        logger.info(message)
        self.send_telegram_message(message)
        
        return True
    
    def close_position(self, symbol: str, price: float, reason: str = "Sinyal") -> bool:
        """Pozisyonu kapatır"""
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        quantity = position['quantity']
        entry_price = position['entry_price']
        
        # Pozisyon değerini hesapla
        position_value = quantity * price
        
        # Sermayeyi güncelle
        self.current_capital += position_value
        
        # Getiri hesapla
        return_pct = (price - entry_price) / entry_price
        
        # İşlemi kaydet
        trade = {
            'date': datetime.now(),
            'symbol': symbol,
            'action': 'SELL',
            'price': price,
            'quantity': quantity,
            'position_value': position_value,
            'return_pct': return_pct,
            'reason': reason,
            'capital_after': self.current_capital
        }
        
        self.trade_history.append(trade)
        
        # Pozisyonu kaldır
        del self.positions[symbol]
        
        # localStorage'a kaydet
        self.save_to_localStorage()
        
        # Log ve bildirim
        emoji = "🟢" if return_pct > 0 else "🔴"
        message = f"{emoji} POZİSYON KAPATILDI\n{symbol}\nFiyat: {price:.2f} TL\nGetiri: {return_pct:.2%}\nSebep: {reason}"
        logger.info(message)
        self.send_telegram_message(message)
        
        return True
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[str]:
        """Stop loss ve take profit kontrolü"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        
        # Stop loss kontrolü
        if current_price <= entry_price * (1 - self.stop_loss_pct):
            return "Stop Loss"
        
        # Take profit kontrolü
        if current_price >= entry_price * (1 + self.take_profit_pct):
            return "Take Profit"
        
        return None
    
    def process_signal(self, symbol: str, current_price: float, 
                      prediction: int, confidence: float) -> Dict:
        """Sinyali işler"""
        result = {
            'action_taken': None,
            'reason': None,
            'success': False
        }
        
        # Mevcut pozisyon kontrolü
        if symbol in self.positions:
            # Stop loss / Take profit kontrolü
            sl_tp_reason = self.check_stop_loss_take_profit(symbol, current_price)
            if sl_tp_reason:
                success = self.close_position(symbol, current_price, sl_tp_reason)
                result['action_taken'] = 'CLOSE'
                result['reason'] = sl_tp_reason
                result['success'] = success
                return result
            
            # Model sinyali ile çıkış
            if prediction == 0 and confidence > 0.50:  # Düşüş sinyali (eşik düşürüldü)
                success = self.close_position(symbol, current_price, "Düşüş Sinyali")
                result['action_taken'] = 'CLOSE'
                result['reason'] = "Düşüş Sinyali"
                result['success'] = success
                return result
        
        # Yeni pozisyon açma
        else:
            if prediction == 1 and confidence > 0.50:  # Yükseliş sinyali (eşik düşürüldü)
                success = self.open_position(symbol, current_price, confidence, prediction)
                result['action_taken'] = 'OPEN'
                result['reason'] = "Yükseliş Sinyali"
                result['success'] = success
        
        return result
    
    def get_current_price(self, symbol: str) -> float:
        """Gerçek zamanlı fiyat alır (cache ile optimize edilmiş)"""
        try:
            # Cache kontrolü
            now = datetime.now()
            if symbol in self.price_cache:
                cache_data = self.price_cache[symbol]
                cache_age = (now - cache_data['timestamp']).total_seconds()
                
                if cache_age < self.cache_duration:
                    logger.info(f"Cache'den fiyat alındı: {symbol} = {cache_data['price']:.2f} TL")
                    return cache_data['price']
            
            # Cache yoksa veya süresi dolmuşsa API'den çek
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__)))
            from data_loader import DataLoader
            
            loader = DataLoader(self.config)
            
            # Son 1 günlük veri çek (güncel fiyat için)
            data = loader.fetch_stock_data(symbol, "1d")
            
            if not data.empty:
                # Son kapanış fiyatını al
                current_price = data['close'].iloc[-1]
                
                # Cache'e kaydet
                self.price_cache[symbol] = {
                    'price': float(current_price),
                    'timestamp': now
                }
                
                logger.info(f"Güncel fiyat çekildi ve cache'e kaydedildi: {symbol} = {current_price:.2f} TL")
                return float(current_price)
            else:
                # Veri çekilemezse entry price'ı döndür
                if symbol in self.positions:
                    entry_price = self.positions[symbol]['entry_price']
                    logger.warning(f"Veri çekilemedi, entry price kullanılıyor: {symbol} = {entry_price:.2f} TL")
                    return entry_price
                else:
                    logger.warning(f"Veri çekilemedi ve pozisyon yok: {symbol}")
                    return 100.0  # Varsayılan fiyat
                    
        except Exception as e:
            logger.error(f"Fiyat çekme hatası {symbol}: {str(e)}")
            # Hata durumunda entry price'ı döndür
            if symbol in self.positions:
                return self.positions[symbol]['entry_price']
            return 100.0
    
    def get_portfolio_summary(self) -> Dict:
        """Portföy özetini döndürür"""
        total_value = self.current_capital
        
        # Pozisyon değerlerini hesapla
        position_values = {}
        position_details = {}
        for symbol, position in self.positions.items():
            # Gerçek zamanlı fiyat alınması gerekir (şimdilik entry price kullanıyoruz)
            current_price = self.get_current_price(symbol)
            position_value = position['quantity'] * current_price
            position_values[symbol] = position_value
            total_value += position_value
            
            # Getiri hesapla
            unrealized_return = (current_price - position['entry_price']) / position['entry_price']
            
            # Pozisyon detayları
            position_details[symbol] = {
                'quantity': position['quantity'],
                'entry_price': position['entry_price'],
                'current_price': current_price,
                'current_value': position_value,
                'unrealized_return': unrealized_return,
                'entry_date': position['entry_date'],
                'confidence': position['confidence'],
                'days_held': (datetime.now() - position['entry_date']).days
            }
        
        # Performans metrikleri
        total_return = (total_value - self.initial_capital) / self.initial_capital
        
        # Son işlemler
        recent_trades = self.trade_history[-5:] if self.trade_history else []
        
        # Bugünkü işlemler
        today = datetime.now().date()
        today_trades = [t for t in self.trade_history if t['date'].date() == today]
        
        # En iyi ve en kötü işlemler
        profitable_trades = [t for t in self.trade_history if t.get('return_pct', 0) > 0]
        losing_trades = [t for t in self.trade_history if t.get('return_pct', 0) < 0]
        
        # Portföy performans analizi
        portfolio_performance = self.calculate_portfolio_performance()
        
        summary = {
            'current_capital': self.current_capital,
            'total_value': total_value,
            'total_return': total_return,
            'positions': len(self.positions),
            'position_values': position_values,
            'position_details': position_details,
            'recent_trades': recent_trades,
            'total_trades': len(self.trade_history),
            'today_trades': len(today_trades),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(profitable_trades) / len(self.trade_history) if self.trade_history else 0,
            'portfolio_performance': portfolio_performance
        }
        
        return summary
    
    def calculate_portfolio_performance(self) -> Dict:
        """Portföy performans analizi yapar"""
        if not self.trade_history:
            return {
                'total_profit_loss': 0,
                'avg_return_per_trade': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        # Tamamlanmış işlemlerden getiri hesapla
        completed_trades = [t for t in self.trade_history if 'return_pct' in t]
        
        if not completed_trades:
            return {
                'total_profit_loss': 0,
                'avg_return_per_trade': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        returns = [t['return_pct'] for t in completed_trades]
        
        # Temel metrikler
        total_profit_loss = sum(returns)
        avg_return_per_trade = np.mean(returns)
        best_trade = max(returns)
        worst_trade = min(returns)
        
        # Maksimum düşüş hesapla
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        # Sharpe ratio (basit versiyon)
        sharpe_ratio = avg_return_per_trade / np.std(returns) if np.std(returns) > 0 else 0
        
        return {
            'total_profit_loss': total_profit_loss,
            'avg_return_per_trade': avg_return_per_trade,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }
    
    def save_state(self):
        """Durumu kaydeder"""
        state = {
            'current_capital': self.current_capital,
            'positions': self.positions,
            'trade_history': self.trade_history,
            'timestamp': datetime.now().isoformat()
        }
        
        # Pozisyonları JSON serializable hale getir
        for symbol, pos in state['positions'].items():
            pos['entry_date'] = pos['entry_date'].isoformat()
        
        # Trade history'yi JSON serializable hale getir
        for trade in state['trade_history']:
            trade['date'] = trade['date'].isoformat()
        
        filepath = os.path.join(self.log_dir, f"paper_trader_state_{datetime.now().strftime('%Y%m%d')}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Durum kaydedildi: {filepath}")
    
    def load_state(self, filepath: str) -> bool:
        """Durumu yükler"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.current_capital = state['current_capital']
            
            # Pozisyonları yükle
            self.positions = {}
            for symbol, pos in state['positions'].items():
                self.positions[symbol] = {
                    'quantity': pos['quantity'],
                    'entry_price': pos['entry_price'],
                    'entry_date': datetime.fromisoformat(pos['entry_date']),
                    'confidence': pos['confidence']
                }
            
            # Trade history'yi yükle
            self.trade_history = []
            for trade in state['trade_history']:
                trade['date'] = datetime.fromisoformat(trade['date'])
                self.trade_history.append(trade)
            
            logger.info(f"Durum yüklendi: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Durum yükleme hatası: {str(e)}")
            return False
    
    def generate_daily_report(self) -> str:
        """Günlük rapor oluşturur"""
        summary = self.get_portfolio_summary()
        
        report = f"""
📊 GÜNLÜK RAPOR - {datetime.now().strftime('%Y-%m-%d')}

💰 SERMAYE DURUMU:
- Mevcut Sermaye: {summary['current_capital']:,.0f} TL
- Toplam Değer: {summary['total_value']:,.0f} TL
- Toplam Getiri: {summary['total_return']:.2%}

📈 POZİSYONLAR ({summary['positions']} adet):
"""
        
        for symbol, value in summary['position_values'].items():
            position = self.positions[symbol]
            report += f"- {symbol}: {value:,.0f} TL (Giriş: {position['entry_price']:.2f})\n"
        
        report += f"""
📋 SON İŞLEMLER:
"""
        
        for trade in summary['recent_trades']:
            emoji = "🟢" if trade['action'] == 'BUY' else "🔴"
            report += f"{emoji} {trade['date'].strftime('%H:%M')} - {trade['symbol']} - {trade['action']} - {trade['price']:.2f}\n"
        
        report += f"""
📊 ÖZET:
- Toplam İşlem: {summary['total_trades']}
- Bugünkü İşlem: {len([t for t in self.trade_history if t['date'].date() == datetime.now().date()])}
"""
        
        return report

class LiveSignalGenerator:
    def __init__(self, config: Dict):
        self.config = config
        self.paper_trader = PaperTrader(config)
        self.model = None
        self.scaler = None
        self.feature_columns = None
        
    def load_model(self, model_path: str) -> bool:
        """Modeli yükler"""
        try:
            import joblib
            model_data = joblib.load(model_path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            
            logger.info(f"Model yüklendi: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            return False
    
    def generate_signals(self, symbols: List[str]) -> Dict[str, Dict]:
        """Tüm semboller için sinyal üretir"""
        signals = {}
        
        for symbol in symbols:
            try:
                # Veri yükle
                from data_loader import DataLoader
                from feature_engineering import FeatureEngineer
                
                loader = DataLoader(self.config)
                engineer = FeatureEngineer(self.config)
                
                # Son 30 günlük veri
                data = loader.fetch_stock_data(symbol, "30d")
                
                if data.empty:
                    logger.warning(f"Veri bulunamadı: {symbol}")
                    continue
                
                # Özellikleri oluştur
                features_df = engineer.create_all_features(data)
                
                if features_df.empty:
                    logger.warning(f"Özellik oluşturulamadı: {symbol}")
                    continue
                
                # Son günün özelliklerini al
                latest_features = features_df[self.feature_columns].iloc[-1:].copy()
                
                # Tahmin yap
                prediction, probabilities = self.model.predict(latest_features)
                confidence = np.abs(probabilities[0][1] - 0.5) * 2  # 0-1 arası normalize
                
                # Mevcut fiyat
                current_price = data['close'].iloc[-1]
                
                # Sinyali işle
                result = self.paper_trader.process_signal(
                    symbol, current_price, prediction[0], confidence
                )
                
                signals[symbol] = {
                    'prediction': prediction[0],
                    'confidence': confidence,
                    'current_price': current_price,
                    'action_taken': result['action_taken'],
                    'reason': result['reason'],
                    'success': result['success']
                }
                
                logger.info(f"Sinyal üretildi: {symbol} - Tahmin: {prediction[0]} - Güven: {confidence:.2f}")
                
            except Exception as e:
                logger.error(f"Sinyal üretme hatası {symbol}: {str(e)}")
                signals[symbol] = None
        
        return signals
    
    def run_daily_signal_generation(self):
        """Günlük sinyal üretimi çalıştırır"""
        logger.info("Günlük sinyal üretimi başlıyor...")
        
        symbols = self.config.get('TARGET_STOCKS', [])
        signals = self.generate_signals(symbols)
        
        # Özet raporu gönder
        summary = self.paper_trader.get_portfolio_summary()
        daily_report = self.paper_trader.generate_daily_report()
        
        # Telegram'a gönder
        self.paper_trader.send_telegram_message(daily_report)
        
        # Durumu kaydet
        self.paper_trader.save_state()
        
        logger.info("Günlük sinyal üretimi tamamlandı")

def main():
    """Test fonksiyonu"""
    import yaml
    
    # Config yükle
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Paper trader oluştur
    trader = PaperTrader(config)
    
    # Test sinyali
    result = trader.process_signal("THYAO.IS", 100.0, 1, 0.8)
    print(f"İşlem sonucu: {result}")
    
    # Portföy özeti
    summary = trader.get_portfolio_summary()
    print(f"Portföy özeti: {summary}")
    
    # Günlük rapor
    report = trader.generate_daily_report()
    print(report)

if __name__ == "__main__":
    main()

