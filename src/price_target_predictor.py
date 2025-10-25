"""
Hedef Fiyat ve Süre Tahmini Modülü
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PriceTargetPredictor:
    def __init__(self, config: Dict):
        self.config = config
        
    def calculate_price_targets(self, current_price: float, prediction: int, 
                              confidence: float, volatility: float, 
                              data: pd.DataFrame, model_data: Dict = None) -> Dict:
        """
        Hedef fiyatları ve tahmini süreleri hesaplar
        
        Args:
            current_price: Mevcut fiyat
            prediction: Model tahmini (1: yukarı, 0: aşağı)
            confidence: Model güven skoru
            volatility: Yıllık volatilite
            data: Geçmiş fiyat verisi
            
        Returns:
            Hedef fiyatlar ve süreler
        """
        # Volatilite bazlı risk parametrelerini al
        risk_configs = self.config.get('RISK_MANAGEMENT', {}).get('VOLATILITY_RISK_CONFIGS', {})
        
        if volatility <= 0.25:
            config = risk_configs.get('LOW_VOLATILITY', {})
        elif volatility <= 0.40:
            config = risk_configs.get('MEDIUM_VOLATILITY', {})
        elif volatility <= 0.60:
            config = risk_configs.get('HIGH_VOLATILITY', {})
        else:
            config = risk_configs.get('VERY_HIGH_VOLATILITY', {})
        
        # Temel parametreler
        stop_loss_pct = config.get('stop_loss_pct', 0.05)
        take_profit_pct = config.get('take_profit_pct', 0.10)
        
        # Güven skoruna göre hedef ayarlaması
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5-1.0 arası
        
        if prediction == 1:  # Yukarı tahmin
            # Hedef fiyatlar
            conservative_target = current_price * (1 + take_profit_pct * 0.5 * confidence_multiplier)
            moderate_target = current_price * (1 + take_profit_pct * confidence_multiplier)
            aggressive_target = current_price * (1 + take_profit_pct * 1.5 * confidence_multiplier)
            
            # Stop loss
            stop_loss_price = current_price * (1 - stop_loss_pct)
            
            # Tahmini süreler - Model ve grafik analizi ile
            time_targets = self._calculate_realistic_time_targets(
                data, current_price, [conservative_target, moderate_target, aggressive_target], 
                volatility, confidence, prediction, model_data
            )
            
        else:  # Aşağı tahmin
            # Hedef fiyatlar
            conservative_target = current_price * (1 - take_profit_pct * 0.5 * confidence_multiplier)
            moderate_target = current_price * (1 - take_profit_pct * confidence_multiplier)
            aggressive_target = current_price * (1 - take_profit_pct * 1.5 * confidence_multiplier)
            
            # Stop loss
            stop_loss_price = current_price * (1 + stop_loss_pct)
            
            # Tahmini süreler - Model ve grafik analizi ile
            time_targets = self._calculate_realistic_time_targets(
                data, current_price, [conservative_target, moderate_target, aggressive_target], 
                volatility, confidence, prediction, model_data
            )
        
        return {
            'current_price': current_price,
            'prediction': prediction,
            'confidence': confidence,
            'volatility': volatility,
            'targets': {
                'conservative': conservative_target,
                'moderate': moderate_target,
                'aggressive': aggressive_target
            },
            'stop_loss': stop_loss_price,
            'time_targets': time_targets,
            'risk_reward_ratio': self._calculate_risk_reward_ratio(
                current_price, moderate_target, stop_loss_price, prediction
            )
        }
    
    def _calculate_time_targets(self, data: pd.DataFrame, current_price: float, 
                              targets: list, volatility: float, confidence: float) -> Dict:
        """
        Hedef fiyatlara ulaşma sürelerini tahmin eder - Grafik analizi ile
        """
        # Grafik analizi yap
        chart_analysis = self._analyze_chart_patterns(data)
        
        # Geçmiş hareket analizi
        returns = data['close'].pct_change().dropna()
        
        # Volatilite bazlı günlük hareket tahmini
        daily_volatility = volatility / np.sqrt(252)
        
        # Güven skoruna göre momentum faktörü
        momentum_factor = 0.5 + (confidence * 0.5)  # 0.5-1.0
        
        # Grafik analizi faktörü
        chart_factor = self._get_chart_time_factor(chart_analysis)
        
        time_targets = {}
        
        for i, target in enumerate(targets):
            target_names = ['conservative', 'moderate', 'aggressive']
            target_name = target_names[i]
            
            # Hedef fiyata ulaşma için gereken hareket
            price_change_needed = abs(target - current_price) / current_price
            
            # Tahmini günlük hareket (volatilite + momentum + grafik analizi)
            estimated_daily_move = daily_volatility * momentum_factor * chart_factor
            
            # Tahmini süre (gün) - Grafik analizi ile ayarlanmış
            base_days = price_change_needed / estimated_daily_move
            
            # Grafik analizi ile süre ayarlaması
            if chart_analysis['trend_strength'] == 'Strong':
                estimated_days = base_days * 0.7  # Güçlü trend = daha hızlı
            elif chart_analysis['trend_strength'] == 'Weak':
                estimated_days = base_days * 1.5  # Zayıf trend = daha yavaş
            else:
                estimated_days = base_days
            
            # Destek/direnç seviyeleri analizi
            if chart_analysis['near_support_resistance']:
                estimated_days *= 1.3  # Destek/direnç yakınında = daha yavaş
            
            # Hacim analizi
            if chart_analysis['volume_trend'] == 'Increasing':
                estimated_days *= 0.8  # Artan hacim = daha hızlı
            elif chart_analysis['volume_trend'] == 'Decreasing':
                estimated_days *= 1.2  # Azalan hacim = daha yavaş
            
            # Minimum ve maksimum süre tahmini (daha gerçekçi)
            min_days = max(3, int(estimated_days * 0.6))  # En az 3 gün
            max_days = int(estimated_days * 2.5)  # Daha geniş aralık
            
            # Tarih tahminleri
            today = datetime.now()
            min_date = today + timedelta(days=min_days)
            max_date = today + timedelta(days=max_days)
            
            time_targets[target_name] = {
                'min_days': min_days,
                'max_days': max_days,
                'estimated_days': int(estimated_days),
                'min_date': min_date.strftime('%d.%m.%Y'),
                'max_date': max_date.strftime('%d.%m.%Y'),
                'estimated_date': (today + timedelta(days=int(estimated_days))).strftime('%d.%m.%Y'),
                'chart_analysis': chart_analysis  # Grafik analizi bilgisi
            }
        
        return time_targets
    
    def _calculate_realistic_time_targets(self, data: pd.DataFrame, current_price: float, 
                                        targets: list, volatility: float, confidence: float,
                                        prediction: int, model_data: Dict = None) -> Dict:
        """
        Gerçek grafik analizi ve model verilerine dayalı gerçekçi süre tahmini
        """
        # Grafik analizi yap
        chart_analysis = self._analyze_chart_patterns(data)
        
        # Geçmiş hareket analizi - Gerçek verilerden
        historical_analysis = self._analyze_historical_movements(data, targets, current_price)
        
        # Model performans analizi
        model_analysis = self._analyze_model_performance(model_data, confidence) if model_data else {}
        
        time_targets = {}
        
        for i, target in enumerate(targets):
            target_names = ['conservative', 'moderate', 'aggressive']
            target_name = target_names[i]
            
            # Hedef fiyata ulaşma için gereken hareket
            price_change_needed = abs(target - current_price) / current_price
            
            # Gerçekçi süre hesaplama - Çoklu faktör analizi
            estimated_days = self._calculate_realistic_days(
                price_change_needed, chart_analysis, historical_analysis, 
                model_analysis, volatility, confidence, prediction, target_name
            )
            
            # Minimum ve maksimum süre tahmini (çok daha gerçekçi)
            min_days = max(7, int(estimated_days * 0.7))  # En az 1 hafta
            max_days = int(estimated_days * 3.0)  # Çok geniş aralık
            
            # Tarih tahminleri
            today = datetime.now()
            min_date = today + timedelta(days=min_days)
            max_date = today + timedelta(days=max_days)
            
            time_targets[target_name] = {
                'min_days': min_days,
                'max_days': max_days,
                'estimated_days': int(estimated_days),
                'min_date': min_date.strftime('%d.%m.%Y'),
                'max_date': max_date.strftime('%d.%m.%Y'),
                'estimated_date': (today + timedelta(days=int(estimated_days))).strftime('%d.%m.%Y'),
                'chart_analysis': chart_analysis,
                'historical_analysis': historical_analysis,
                'model_analysis': model_analysis
            }
        
        return time_targets
    
    def _analyze_historical_movements(self, data: pd.DataFrame, targets: list, current_price: float) -> Dict:
        """
        Geçmiş hareketleri analiz eder - Gerçek verilerden
        """
        if len(data) < 100:
            return {'insufficient_data': True}
        
        # Son 100 günlük analiz
        recent_data = data.tail(100)
        
        # Farklı büyüklükteki hareketlerin sürelerini analiz et
        movement_analysis = {}
        
        for target in targets:
            target_change = abs(target - current_price) / current_price
            
            # Bu büyüklükteki hareketlerin geçmişte ne kadar sürdüğünü bul
            durations = []
            
            for i in range(20, len(recent_data) - 10):  # En az 20 gün önce başla
                start_price = recent_data['close'].iloc[i]
                
                # Bu fiyattan başlayarak target_change kadar hareket eden süreleri bul
                for j in range(i + 1, min(i + 50, len(recent_data))):  # Max 50 gün ara
                    end_price = recent_data['close'].iloc[j]
                    actual_change = abs(end_price - start_price) / start_price
                    
                    # %10 toleransla benzer hareketleri bul
                    if abs(actual_change - target_change) < target_change * 0.1:
                        durations.append(j - i)
                        break
            
            if durations:
                avg_duration = np.mean(durations)
                std_duration = np.std(durations)
                movement_analysis[f'{target_change:.3f}'] = {
                    'avg_days': avg_duration,
                    'std_days': std_duration,
                    'min_days': min(durations),
                    'max_days': max(durations),
                    'sample_count': len(durations)
                }
        
        # Trend analizi
        sma_20 = recent_data['close'].rolling(20).mean()
        sma_50 = recent_data['close'].rolling(50).mean()
        
        # Trend gücü ve yönü
        trend_strength = abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1]
        trend_direction = 1 if sma_20.iloc[-1] > sma_50.iloc[-1] else -1
        
        # Volatilite analizi
        returns = recent_data['close'].pct_change().dropna()
        recent_volatility = returns.tail(20).std() * np.sqrt(252)
        long_term_volatility = returns.std() * np.sqrt(252)
        
        return {
            'movement_analysis': movement_analysis,
            'trend_strength': trend_strength,
            'trend_direction': trend_direction,
            'recent_volatility': recent_volatility,
            'long_term_volatility': long_term_volatility,
            'volatility_ratio': recent_volatility / long_term_volatility if long_term_volatility > 0 else 1.0
        }
    
    def _analyze_model_performance(self, model_data: Dict, confidence: float) -> Dict:
        """
        Model performansını analiz eder
        """
        if not model_data:
            return {}
        
        # Model doğruluk oranı
        accuracy = model_data.get('test_metrics', {}).get('accuracy', 0.5)
        
        # Model güvenilirliği
        reliability_score = accuracy * confidence
        
        # Model performans kategorisi
        if reliability_score > 0.8:
            performance_category = 'Excellent'
            time_factor = 0.8  # Daha hızlı
        elif reliability_score > 0.7:
            performance_category = 'Good'
            time_factor = 0.9
        elif reliability_score > 0.6:
            performance_category = 'Fair'
            time_factor = 1.0
        else:
            performance_category = 'Poor'
            time_factor = 1.2  # Daha yavaş
        
        return {
            'accuracy': accuracy,
            'reliability_score': reliability_score,
            'performance_category': performance_category,
            'time_factor': time_factor
        }
    
    def _calculate_realistic_days(self, price_change_needed: float, chart_analysis: Dict, 
                                historical_analysis: Dict, model_analysis: Dict,
                                volatility: float, confidence: float, prediction: int, target_type: str) -> float:
        """
        Gerçekçi gün sayısını hesaplar - Çoklu faktör analizi
        """
        # Temel süre hesaplama (volatilite bazlı)
        base_days = price_change_needed / (volatility / np.sqrt(252)) * 10  # 10x faktör
        
        # Grafik analizi faktörü
        chart_factor = 1.0
        
        if chart_analysis['trend_strength'] == 'Strong':
            chart_factor *= 0.6  # Güçlü trend = çok daha hızlı
        elif chart_analysis['trend_strength'] == 'Weak':
            chart_factor *= 1.8  # Zayıf trend = çok daha yavaş
        
        if chart_analysis['near_support_resistance']:
            chart_factor *= 1.5  # Destek/direnç yakınında = çok daha yavaş
        
        if chart_analysis['volume_trend'] == 'Increasing':
            chart_factor *= 0.7  # Artan hacim = daha hızlı
        elif chart_analysis['volume_trend'] == 'Decreasing':
            chart_factor *= 1.3  # Azalan hacim = daha yavaş
        
        # Geçmiş hareket analizi faktörü
        historical_factor = 1.0
        
        if not historical_analysis.get('insufficient_data', False):
            # Benzer hareketlerin ortalama süresini kullan
            movement_key = f'{price_change_needed:.3f}'
            if movement_key in historical_analysis['movement_analysis']:
                historical_avg = historical_analysis['movement_analysis'][movement_key]['avg_days']
                historical_factor = historical_avg / base_days if base_days > 0 else 1.0
            
            # Volatilite trendi faktörü
            volatility_ratio = historical_analysis.get('volatility_ratio', 1.0)
            if volatility_ratio > 1.2:  # Yüksek volatilite
                historical_factor *= 0.8
            elif volatility_ratio < 0.8:  # Düşük volatilite
                historical_factor *= 1.3
        
        # Model performans faktörü
        model_factor = model_analysis.get('time_factor', 1.0)
        
        # Hedef tipi faktörü
        target_factor = 1.0
        if target_type == 'conservative':
            target_factor = 0.8  # Konservatif hedefler daha hızlı
        elif target_type == 'aggressive':
            target_factor = 1.5  # Agresif hedefler daha yavaş
        
        # Güven skoru faktörü
        confidence_factor = 0.7 + (confidence * 0.6)  # 0.7-1.3 arası
        
        # Final hesaplama
        estimated_days = base_days * chart_factor * historical_factor * model_factor * target_factor * confidence_factor
        
        # Minimum ve maksimum sınırlar
        estimated_days = max(14, min(estimated_days, 180))  # 2 hafta - 6 ay arası
        
        return estimated_days
    
    def _analyze_chart_patterns(self, data: pd.DataFrame) -> Dict:
        """
        Grafik kalıplarını analiz eder
        """
        if len(data) < 50:
            return {
                'trend_strength': 'Unknown',
                'near_support_resistance': False,
                'volume_trend': 'Unknown',
                'pattern': 'Insufficient Data'
            }
        
        # Trend analizi
        sma_20 = data['close'].rolling(20).mean()
        sma_50 = data['close'].rolling(50).mean()
        
        # Trend gücü
        trend_strength = abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1]
        
        if trend_strength > 0.1:
            trend_strength_text = 'Strong'
        elif trend_strength > 0.05:
            trend_strength_text = 'Medium'
        else:
            trend_strength_text = 'Weak'
        
        # Destek/direnç analizi
        recent_high = data['high'].rolling(20).max().iloc[-1]
        recent_low = data['low'].rolling(20).min().iloc[-1]
        current_price = data['close'].iloc[-1]
        
        # Mevcut fiyatın destek/direnç seviyelerine yakınlığı
        near_support = abs(current_price - recent_low) / current_price < 0.03
        near_resistance = abs(current_price - recent_high) / current_price < 0.03
        near_support_resistance = near_support or near_resistance
        
        # Hacim analizi
        volume_sma_20 = data['volume'].rolling(20).mean()
        recent_volume = data['volume'].iloc[-5:].mean()
        avg_volume = volume_sma_20.iloc[-1]
        
        if recent_volume > avg_volume * 1.2:
            volume_trend = 'Increasing'
        elif recent_volume < avg_volume * 0.8:
            volume_trend = 'Decreasing'
        else:
            volume_trend = 'Stable'
        
        # Pattern analizi
        pattern = self._identify_pattern(data)
        
        return {
            'trend_strength': trend_strength_text,
            'near_support_resistance': near_support_resistance,
            'volume_trend': volume_trend,
            'pattern': pattern,
            'support_level': recent_low,
            'resistance_level': recent_high,
            'trend_strength_value': trend_strength
        }
    
    def _get_chart_time_factor(self, chart_analysis: Dict) -> float:
        """
        Grafik analizine göre zaman faktörü döndürür
        """
        factor = 1.0
        
        # Trend gücü faktörü
        if chart_analysis['trend_strength'] == 'Strong':
            factor *= 0.8  # Güçlü trend = daha hızlı
        elif chart_analysis['trend_strength'] == 'Weak':
            factor *= 1.3  # Zayıf trend = daha yavaş
        
        # Destek/direnç faktörü
        if chart_analysis['near_support_resistance']:
            factor *= 1.2  # Destek/direnç yakınında = daha yavaş
        
        # Hacim faktörü
        if chart_analysis['volume_trend'] == 'Increasing':
            factor *= 0.9  # Artan hacim = biraz daha hızlı
        elif chart_analysis['volume_trend'] == 'Decreasing':
            factor *= 1.1  # Azalan hacim = biraz daha yavaş
        
        return factor
    
    def _identify_pattern(self, data: pd.DataFrame) -> str:
        """
        Basit grafik kalıplarını tanımlar
        """
        if len(data) < 20:
            return 'Insufficient Data'
        
        # Son 20 günlük analiz
        recent_data = data.tail(20)
        
        # Fiyat hareketi
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        
        # Volatilite
        volatility = recent_data['close'].pct_change().std()
        
        # Pattern belirleme
        if price_change > 0.05 and volatility < 0.02:
            return 'Strong Uptrend'
        elif price_change < -0.05 and volatility < 0.02:
            return 'Strong Downtrend'
        elif abs(price_change) < 0.02 and volatility < 0.015:
            return 'Sideways/Consolidation'
        elif volatility > 0.03:
            return 'High Volatility'
        else:
            return 'Mixed Signals'
    
    def _calculate_risk_reward_ratio(self, current_price: float, target_price: float, 
                                   stop_loss_price: float, prediction: int) -> float:
        """
        Risk/Getiri oranını hesaplar
        """
        if prediction == 1:  # Yukarı tahmin
            potential_profit = target_price - current_price
            potential_loss = current_price - stop_loss_price
        else:  # Aşağı tahmin
            potential_profit = current_price - target_price
            potential_loss = stop_loss_price - current_price
        
        if potential_loss <= 0:
            return 0
        
        return potential_profit / potential_loss
    
    def get_price_target_summary(self, prediction_result: Dict) -> str:
        """
        Hedef fiyat özetini metin olarak döndürür
        """
        targets = prediction_result['targets']
        time_targets = prediction_result['time_targets']
        prediction = prediction_result['prediction']
        
        direction = "yükseliş" if prediction == 1 else "düşüş"
        
        summary = f"""
🎯 **Hedef Fiyat Analizi ({direction.title()})**

**Konservatif Hedef:** {targets['conservative']:.2f} TL
   📅 Tahmini süre: {time_targets['conservative']['min_days']}-{time_targets['conservative']['max_days']} gün
   📆 Beklenen tarih: {time_targets['conservative']['estimated_date']}

**Orta Hedef:** {targets['moderate']:.2f} TL  
   📅 Tahmini süre: {time_targets['moderate']['min_days']}-{time_targets['moderate']['max_days']} gün
   📆 Beklenen tarih: {time_targets['moderate']['estimated_date']}

**Agresif Hedef:** {targets['aggressive']:.2f} TL
   📅 Tahmini süre: {time_targets['aggressive']['min_days']}-{time_targets['aggressive']['max_days']} gün
   📆 Beklenen tarih: {time_targets['aggressive']['estimated_date']}

🛡️ **Stop Loss:** {prediction_result['stop_loss']:.2f} TL
📊 **Risk/Getiri Oranı:** {prediction_result['risk_reward_ratio']:.2f}
        """
        
        return summary
