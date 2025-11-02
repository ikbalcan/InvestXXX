"""
Gerçekçi Backtesting Sistemi
Komisyon, slippage ve risk yönetimi ile gerçekçi performans ölçümü
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, config: Dict):
        self.config = config
        self.backtest_config = config.get('BACKTEST_CONFIG', {})
        self.risk_config = config.get('RISK_MANAGEMENT', {})
        
        # Backtest parametreleri
        self.initial_capital = self.backtest_config.get('initial_capital', 100000)
        self.commission_rate = self.backtest_config.get('commission_rate', 0.0015)
        self.slippage_rate = self.backtest_config.get('slippage_rate', 0.0005)
        
        # Risk yönetimi parametreleri
        self.max_position_size = self.risk_config.get('max_position_size', 0.02)
        self.stop_loss_pct = self.risk_config.get('stop_loss_pct', 0.05)
        self.take_profit_pct = self.risk_config.get('take_profit_pct', 0.10)
        self.max_daily_trades = self.risk_config.get('max_daily_trades', 5)
        
        # Backtest sonuçları
        self.results = None
        self.trades = []
        self.equity_curve = None
        
    def calculate_position_size(self, price: float, confidence: float) -> float:
        """
        Pozisyon büyüklüğünü hesaplar
        
        Args:
            price: Hisse fiyatı
            confidence: Model güven skoru
            
        Returns:
            Pozisyon büyüklüğü (TL cinsinden)
        """
        # Temel pozisyon büyüklüğü
        base_position = self.initial_capital * self.max_position_size
        
        # Güven skoruna göre ayarla
        confidence_multiplier = min(confidence * 2, 1.0)  # Max 1.0
        
        # Final pozisyon büyüklüğü
        position_size = base_position * confidence_multiplier
        
        return position_size
    
    def calculate_trade_costs(self, price: float, quantity: float) -> float:
        """
        İşlem maliyetlerini hesaplar
        
        Args:
            price: Hisse fiyatı
            quantity: Miktar
            
        Returns:
            Toplam maliyet
        """
        trade_value = price * quantity
        
        # Komisyon
        commission = trade_value * self.commission_rate
        
        # Slippage
        slippage = trade_value * self.slippage_rate
        
        return commission + slippage
    
    def execute_trade(self, date: datetime, symbol: str, action: str, 
                     price: float, confidence: float, current_capital: float) -> Dict:
        """
        İşlem gerçekleştirir
        
        Args:
            date: İşlem tarihi
            symbol: Hisse sembolü
            action: 'buy' veya 'sell'
            price: İşlem fiyatı
            confidence: Model güven skoru
            current_capital: Mevcut sermaye
            
        Returns:
            İşlem detayları
        """
        # Pozisyon büyüklüğünü hesapla
        position_size = self.calculate_position_size(price, confidence)
        
        # Miktarı hesapla
        quantity = position_size / price
        
        # İşlem maliyetlerini hesapla
        costs = self.calculate_trade_costs(price, quantity)
        
        # Sermaye kontrolü
        if action == 'buy' and position_size + costs > current_capital:
            logger.warning(f"Yetersiz sermaye: {symbol} - {date}")
            return None
        
        # İşlem detayları
        if action == 'buy':
            capital_after = current_capital - (position_size + costs)
        else:  # sell
            capital_after = current_capital + (quantity * price) - costs
            
        trade = {
            'date': date,
            'symbol': symbol,
            'action': action,
            'price': price,
            'quantity': quantity,
            'position_size': position_size,
            'costs': costs,
            'confidence': confidence,
            'capital_after': capital_after
        }
        
        return trade
    
    def calculate_dynamic_confidence_threshold(self, symbol: str, volatility: float) -> float:
        """
        Volatiliteye göre dinamik güven eşiği hesaplar
        
        Args:
            symbol: Hisse sembolü
            volatility: Yıllık volatilite
            
        Returns:
            Dinamik güven eşiği
        """
        # Config'den volatilite bazlı risk parametrelerini al
        risk_configs = self.config.get('RISK_MANAGEMENT', {}).get('VOLATILITY_RISK_CONFIGS', {})
        
        if volatility <= 0.25:
            config = risk_configs.get('LOW_VOLATILITY', {})
            logger.info(f"{symbol} - Düşük volatilite (%{volatility*100:.1f})")
        elif volatility <= 0.40:
            config = risk_configs.get('MEDIUM_VOLATILITY', {})
            logger.info(f"{symbol} - Orta volatilite (%{volatility*100:.1f})")
        elif volatility <= 0.60:
            config = risk_configs.get('HIGH_VOLATILITY', {})
            logger.info(f"{symbol} - Yüksek volatilite (%{volatility*100:.1f})")
        else:
            config = risk_configs.get('VERY_HIGH_VOLATILITY', {})
            logger.info(f"{symbol} - Çok yüksek volatilite (%{volatility*100:.1f})")
        
        # Güven eşiğini al
        confidence_threshold = config.get('confidence_threshold', 0.50)
        
        # Risk parametrelerini güncelle
        self.max_position_size = config.get('max_position_size', self.max_position_size)
        self.stop_loss_pct = config.get('stop_loss_pct', self.stop_loss_pct)
        self.take_profit_pct = config.get('take_profit_pct', self.take_profit_pct)
        self.max_daily_trades = config.get('max_daily_trades', self.max_daily_trades)
        
        logger.info(f"Risk parametreleri - Pozisyon: %{self.max_position_size*100:.1f}, "
                   f"Stop Loss: %{self.stop_loss_pct*100:.1f}, "
                   f"Take Profit: %{self.take_profit_pct*100:.1f}")
        
        return confidence_threshold
    
    def run_backtest(self, features_df: pd.DataFrame, predictions: np.ndarray, 
                    probabilities: np.ndarray, symbol: str) -> Dict:
        """
        Backtest çalıştırır
        
        Args:
            features_df: Özellikler DataFrame'i
            predictions: Model tahminleri
            probabilities: Tahmin olasılıkları
            symbol: Hisse sembolü
            
        Returns:
            Backtest sonuçları
        """
        logger.info(f"Backtest başlıyor: {symbol}")
        
        # Volatilite hesapla ve dinamik eşik belirle
        returns = features_df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Yıllık volatilite
        confidence_threshold = self.calculate_dynamic_confidence_threshold(symbol, volatility)
        
        logger.info(f"{symbol} volatilitesi: %{volatility*100:.1f}, Güven eşiği: {confidence_threshold:.2f}")
        
        # Başlangıç değerleri
        capital = self.initial_capital
        position = 0  # Pozisyon miktarı
        position_entry_price = 0
        position_entry_date = None
        daily_trades = 0
        last_trade_date = None
        
        # Sonuç listeleri
        equity_values = []
        trade_log = []
        
        # Güven skorları (0-1 arası normalize) - Düzeltilmiş hesaplama
        confidence_scores = np.max(probabilities, axis=1)  # En yüksek olasılığı al
        
        for i, (date, row) in enumerate(features_df.iterrows()):
            current_price = row['close']
            prediction = predictions[i]
            confidence = confidence_scores[i]
            
            # Günlük işlem sayısı kontrolü
            if last_trade_date != date.date():
                daily_trades = 0
                last_trade_date = date.date()
            
            # Mevcut pozisyon kontrolü
            if position > 0:  # Long pozisyon var
                # Stop loss kontrolü
                if current_price <= position_entry_price * (1 - self.stop_loss_pct):
                    # Stop loss tetiklendi
                    trade = self.execute_trade(date, symbol, 'sell', current_price, 
                                             confidence, capital)
                    if trade:
                        # Pozisyonun gerçek değerini sermayeye ekle
                        capital = capital + (position * current_price) - trade['costs']
                        position = 0
                        trade_log.append(trade)
                        daily_trades += 1
                        logger.info(f"Stop loss: {symbol} - {date} - Fiyat: {current_price:.2f}")
                
                # Take profit kontrolü
                elif current_price >= position_entry_price * (1 + self.take_profit_pct):
                    # Take profit tetiklendi
                    trade = self.execute_trade(date, symbol, 'sell', current_price, 
                                             confidence, capital)
                    if trade:
                        # Pozisyonun gerçek değerini sermayeye ekle
                        capital = capital + (position * current_price) - trade['costs']
                        position = 0
                        trade_log.append(trade)
                        daily_trades += 1
                        logger.info(f"Take profit: {symbol} - {date} - Fiyat: {current_price:.2f}")
                
                # Model sinyali ile çıkış
                elif prediction == 0 and confidence > confidence_threshold:  # Dinamik düşüş sinyali
                    trade = self.execute_trade(date, symbol, 'sell', current_price, 
                                             confidence, capital)
                    if trade:
                        # Pozisyonun gerçek değerini sermayeye ekle
                        capital = capital + (position * current_price) - trade['costs']
                        position = 0
                        trade_log.append(trade)
                        daily_trades += 1
            
            # Yeni pozisyon açma
            elif position == 0 and daily_trades < self.max_daily_trades:
                if prediction == 1 and confidence > confidence_threshold:  # Dinamik yükseliş sinyali
                    trade = self.execute_trade(date, symbol, 'buy', current_price, 
                                             confidence, capital)
                    if trade:
                        capital = trade['capital_after']
                        position = trade['quantity']
                        position_entry_price = current_price
                        position_entry_date = date
                        trade_log.append(trade)
                        daily_trades += 1
            
            # Sermaye değerini hesapla
            if position > 0:
                current_equity = capital + (position * current_price)
            else:
                current_equity = capital
            
            equity_values.append({
                'date': date,
                'equity': current_equity,
                'capital': capital,
                'position_value': position * current_price if position > 0 else 0,
                'position': position
            })
        
        # Son pozisyonu kapat
        if position > 0:
            last_price = features_df['close'].iloc[-1]
            trade = self.execute_trade(features_df.index[-1], symbol, 'sell', last_price, 
                                     0.5, capital)
            if trade:
                capital = trade['capital_after']
                trade_log.append(trade)
        
        # Sonuçları hazırla
        equity_df = pd.DataFrame(equity_values)
        equity_df.set_index('date', inplace=True)
        
        # Performans metrikleri
        performance_metrics = self._calculate_performance_metrics(equity_df, trade_log)
        
        # Sonuçları kaydet
        self.results = {
            'symbol': symbol,
            'equity_curve': equity_df,
            'trades': trade_log,
            'performance_metrics': performance_metrics,
            'final_capital': capital,
            'total_return': (capital - self.initial_capital) / self.initial_capital
        }
        
        logger.info(f"Backtest tamamlandı: {symbol}")
        logger.info(f"Toplam getiri: {self.results['total_return']:.2%}")
        logger.info(f"Toplam işlem sayısı: {len(trade_log)}")
        
        return self.results
    
    def _calculate_performance_metrics(self, equity_df: pd.DataFrame, trades: List[Dict]) -> Dict:
        """Performans metriklerini hesaplar"""
        
        # Temel metrikler
        total_return = (equity_df['equity'].iloc[-1] - self.initial_capital) / self.initial_capital
        
        # Günlük getiriler
        daily_returns = equity_df['equity'].pct_change().dropna()
        
        # Sharpe ratio
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        # Maximum drawdown
        rolling_max = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Win rate - doğru hesaplama
        profitable_trades = []
        for i, trade in enumerate(trades):
            if trade['action'] == 'sell' and i > 0:
                prev_trade = trades[i-1]
                if prev_trade['action'] == 'buy' and trade['price'] > prev_trade['price']:
                    profitable_trades.append(trade)
        
        total_sell_trades = len([t for t in trades if t['action'] == 'sell'])
        win_rate = len(profitable_trades) / total_sell_trades if total_sell_trades > 0 else 0
        
        # Ortalama işlem süresi
        trade_durations = []
        for i, trade in enumerate(trades):
            if trade['action'] == 'sell' and i > 0:
                prev_trade = trades[i-1]
                if prev_trade['action'] == 'buy':
                    duration = (trade['date'] - prev_trade['date']).days
                    trade_durations.append(duration)
        
        avg_trade_duration = np.mean(trade_durations) if trade_durations else 0
        
        metrics = {
            'total_return': total_return,
            'annualized_return': (1 + total_return) ** (252 / len(equity_df)) - 1,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'avg_trade_duration': avg_trade_duration,
            'volatility': daily_returns.std() * np.sqrt(252)
        }
        
        return metrics
    
    def plot_results(self, save_path: str = None):
        """Sonuçları görselleştirir"""
        if self.results is None:
            logger.error("Backtest sonuçları yok!")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Equity curve
        equity_df = self.results['equity_curve']
        axes[0, 0].plot(equity_df.index, equity_df['equity'])
        axes[0, 0].set_title(f"Equity Curve - {self.results['symbol']}")
        axes[0, 0].set_ylabel("Sermaye (TL)")
        axes[0, 0].grid(True)
        
        # Drawdown
        rolling_max = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - rolling_max) / rolling_max * 100
        axes[0, 1].fill_between(equity_df.index, drawdown, 0, alpha=0.3, color='red')
        axes[0, 1].set_title("Drawdown (%)")
        axes[0, 1].set_ylabel("Drawdown (%)")
        axes[0, 1].grid(True)
        
        # Trade distribution
        trades = self.results['trades']
        trade_returns = []
        for i, trade in enumerate(trades):
            if trade['action'] == 'sell' and i > 0:
                prev_trade = trades[i-1]
                if prev_trade['action'] == 'buy':
                    ret = (trade['price'] - prev_trade['price']) / prev_trade['price']
                    trade_returns.append(ret)
        
        if trade_returns:
            axes[1, 0].hist(trade_returns, bins=20, alpha=0.7)
            axes[1, 0].set_title("İşlem Getirileri Dağılımı")
            axes[1, 0].set_xlabel("Getiri")
            axes[1, 0].set_ylabel("Frekans")
            axes[1, 0].grid(True)
        
        # Performance metrics
        metrics = self.results['performance_metrics']
        metric_names = ['Total Return', 'Sharpe Ratio', 'Max Drawdown', 'Win Rate']
        metric_values = [
            metrics['total_return'] * 100,
            metrics['sharpe_ratio'],
            metrics['max_drawdown'] * 100,
            metrics['win_rate'] * 100
        ]
        
        axes[1, 1].bar(metric_names, metric_values)
        axes[1, 1].set_title("Performans Metrikleri")
        axes[1, 1].set_ylabel("Değer")
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Grafik kaydedildi: {save_path}")
        
        plt.show()
    
    def generate_report(self) -> str:
        """Detaylı rapor oluşturur"""
        if self.results is None:
            return "Backtest sonuçları yok!"
        
        metrics = self.results['performance_metrics']
        trades = self.results['trades']
        
        report = f"""
=== BACKTEST RAPORU ===
Hisse: {self.results['symbol']}
Başlangıç Sermayesi: {self.initial_capital:,.0f} TL
Final Sermayesi: {self.results['final_capital']:,.0f} TL

PERFORMANS METRİKLERİ:
- Toplam Getiri: {metrics['total_return']:.2%}
- Yıllık Getiri: {metrics['annualized_return']:.2%}
- Sharpe Ratio: {metrics['sharpe_ratio']:.3f}
- Maksimum Drawdown: {metrics['max_drawdown']:.2%}
- Kazanma Oranı: {metrics['win_rate']:.2%}
- Toplam İşlem: {metrics['total_trades']}
- Ortalama İşlem Süresi: {metrics['avg_trade_duration']:.1f} gün
- Volatilite: {metrics['volatility']:.2%}

İŞLEM DETAYLARI:
"""
        
        for i, trade in enumerate(trades[:10]):  # İlk 10 işlem
            report += f"{i+1}. {trade['date'].strftime('%Y-%m-%d')} - {trade['action'].upper()} - "
            report += f"{trade['price']:.2f} TL - Güven: {trade['confidence']:.2f}\n"
        
        if len(trades) > 10:
            report += f"... ve {len(trades) - 10} işlem daha\n"
        
        return report

def main():
    """Test fonksiyonu"""
    import yaml
    from data_loader import DataLoader
    from feature_engineering import FeatureEngineer
    from model_train import StockDirectionPredictor
    
    # Config yükle
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Veri yükle ve model eğit
    loader = DataLoader(config)
    engineer = FeatureEngineer(config, data_loader=loader)
    predictor = StockDirectionPredictor(config)
    
    # Test verisi
    data = loader.fetch_stock_data("THYAO.IS", "2y")
    
    # BIST 100 endeks verisini yükle
    index_data = loader.get_index_data(period="2y")
    
    if not data.empty:
        features_df = engineer.create_all_features(data, index_data=index_data)
        X, y = predictor.prepare_data(features_df)
        
        # Model eğitimi
        predictor.train_model(X, y)
        
        # Tahminler
        predictions, probabilities = predictor.predict(X)
        
        # Backtest
        backtester = Backtester(config)
        results = backtester.run_backtest(features_df, predictions, probabilities, "THYAO.IS")
        
        # Rapor
        print(backtester.generate_report())
        
        # Grafik
        backtester.plot_results("backtest_results.png")

if __name__ == "__main__":
    main()

