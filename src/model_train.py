"""
XGBoost Tabanlı Hisse Senedi Yön Tahmini Modeli
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit, train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from typing import Dict, List, Tuple, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class StockDirectionPredictor:
    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.model_dir = "src/models"
        os.makedirs(self.model_dir, exist_ok=True)
        
    def prepare_data(self, features_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Model için veriyi hazırlar
        
        Args:
            features_df: Özelliklerle zenginleştirilmiş DataFrame
            
        Returns:
            X (özellikler), y (hedef) tuple'ı
        """
        # Hedef değişkeni seç
        target_col = 'direction_binary'  # Binary classification
        
        # Özellik kolonlarını belirle
        exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'adj_close',
                       'future_price', 'future_return', 'direction', 'direction_binary',
                       'future_return_vol_adj']
        
        self.feature_columns = [col for col in features_df.columns if col not in exclude_cols]
        
        # Veriyi hazırla
        X = features_df[self.feature_columns].copy()
        y = features_df[target_col].copy()
        
        # Veri tiplerini kontrol et ve düzelt
        X = X.select_dtypes(include=[np.number])
        
        # Eksik değerleri ve infinity değerleri temizle
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median())
        
        mask = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[mask]
        y = y[mask]
        
        logger.info(f"Model için hazırlanan veri boyutu: {X.shape}")
        logger.info(f"Hedef değişken dağılımı: {y.value_counts().to_dict()}")
        
        return X, y
    
    def calculate_volatility(self, X: pd.DataFrame) -> float:
        """
        Veri setinden volatilite hesaplar
        
        Args:
            X: Özellik matrisi
            
        Returns:
            Yıllık volatilite
        """
        # Returns özelliğini bul
        if 'returns' in X.columns:
            returns = X['returns'].dropna()
        else:
            # Eğer returns yoksa, volatility_20d kullan
            if 'volatility_20d' in X.columns:
                returns = X['volatility_20d'].dropna()
            else:
                logger.warning("Volatilite hesaplanamadı, varsayılan değer kullanılıyor")
                return 0.3  # Varsayılan orta volatilite
        
        if len(returns) == 0:
            return 0.3
            
        # Yıllık volatilite hesapla
        volatility = returns.std() * np.sqrt(252)
        return volatility
    
    def get_volatility_config(self, volatility: float) -> Dict:
        """
        Volatiliteye göre model konfigürasyonu döndürür
        
        Args:
            volatility: Yıllık volatilite
            
        Returns:
            Model konfigürasyonu
        """
        model_config = self.config.get('MODEL_CONFIG', {})
        volatility_configs = model_config.get('VOLATILITY_CONFIGS', {})
        
        if volatility <= 0.25:
            config_name = 'LOW_VOLATILITY'
            logger.info(f"Volatilite: %{volatility*100:.1f} - Düşük volatilite konfigürasyonu")
        elif volatility <= 0.40:
            config_name = 'MEDIUM_VOLATILITY'
            logger.info(f"Volatilite: %{volatility*100:.1f} - Orta volatilite konfigürasyonu")
        elif volatility <= 0.60:
            config_name = 'HIGH_VOLATILITY'
            logger.info(f"Volatilite: %{volatility*100:.1f} - Yüksek volatilite konfigürasyonu")
        else:
            config_name = 'VERY_HIGH_VOLATILITY'
            logger.info(f"Volatilite: %{volatility*100:.1f} - Çok yüksek volatilite konfigürasyonu")
        
        return volatility_configs.get(config_name, volatility_configs.get('MEDIUM_VOLATILITY', {}))

    def train_model(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> Dict:
        """
        XGBoost modelini eğitir
        
        Args:
            X: Özellik matrisi
            y: Hedef değişken
            test_size: Test seti oranı
            
        Returns:
            Eğitim metrikleri
        """
        logger.info("Model eğitimi başlıyor...")
        
        # Volatilite hesapla ve konfigürasyonu belirle
        volatility = self.calculate_volatility(X)
        volatility_config = self.get_volatility_config(volatility)
        
        # Zaman serisi split (son %20 test için)
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Özellikleri ölçeklendir
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Class imbalance check and weight calculation
        y_train_counts = y_train.value_counts()
        if len(y_train_counts) == 2:
            scale_pos_weight = y_train_counts[0] / y_train_counts[1]
            logger.info(f"Class distribution: {y_train_counts.to_dict()}, scale_pos_weight: {scale_pos_weight:.2f}")
        else:
            scale_pos_weight = 1.0
        
        # XGBoost parametreleri (volatilite bazlı)
        xgb_params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': volatility_config.get('max_depth', 4),
            'learning_rate': volatility_config.get('learning_rate', 0.05),
            'n_estimators': volatility_config.get('n_estimators', 200),
            'subsample': volatility_config.get('subsample', 0.7),
            'colsample_bytree': volatility_config.get('colsample_bytree', 0.7),
            'min_child_weight': volatility_config.get('min_child_weight', 5),
            'reg_alpha': volatility_config.get('reg_alpha', 0.1),
            'reg_lambda': volatility_config.get('reg_lambda', 0.1),
            'scale_pos_weight': scale_pos_weight,  # Class imbalance için
            'random_state': 42,
            'n_jobs': -1
        }
        
        logger.info(f"Volatilite bazlı parametreler: {xgb_params}")
        
        # Model oluştur ve eğit
        self.model = xgb.XGBClassifier(**xgb_params)
        self.model.fit(X_train_scaled, y_train)
        
        # Tahminler
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        # Metrikleri hesapla
        train_metrics = self._calculate_metrics(y_train, y_pred_train, "Train")
        test_metrics = self._calculate_metrics(y_test, y_pred_test, "Test")
        
        # Feature importance
        feature_importance = self._get_feature_importance()
        
        # Sonuçları birleştir
        results = {
            'train_metrics': train_metrics,
            'test_metrics': test_metrics,
            'feature_importance': feature_importance,
            'model_params': xgb_params
        }
        
        logger.info("Model eğitimi tamamlandı")
        return results
    
    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray, set_name: str) -> Dict:
        """Metrikleri hesaplar"""
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted'),
            'recall': recall_score(y_true, y_pred, average='weighted'),
            'f1': f1_score(y_true, y_pred, average='weighted')
        }
        
        logger.info(f"{set_name} Metrikleri:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
            
        return metrics
    
    def _get_feature_importance(self) -> pd.DataFrame:
        """Özellik önemini döndürür"""
        if self.model is None:
            return pd.DataFrame()
        
        # Feature columns ve importance'ları eşleştir
        feature_names = self.feature_columns[:len(self.model.feature_importances_)]
        importances = self.model.feature_importances_[:len(self.feature_columns)]
            
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        logger.info("En önemli 10 özellik:")
        for _, row in importance_df.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")
            
        return importance_df
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Tahmin yapar
        
        Args:
            X: Özellik matrisi
            
        Returns:
            Tahminler ve olasılıklar tuple'ı
        """
        if self.model is None:
            raise ValueError("Model henüz eğitilmemiş!")
            
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        return predictions, probabilities
    
    def save_model(self, filename: str = None) -> str:
        """
        Modeli kaydeder
        
        Args:
            filename: Dosya adı (opsiyonel)
            
        Returns:
            Kaydedilen dosya yolu
        """
        if self.model is None:
            raise ValueError("Kaydedilecek model yok!")
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stock_predictor_{timestamp}.joblib"
            
        filepath = os.path.join(self.model_dir, filename)
        
        # Model, scaler ve feature columns'ı kaydet
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'config': self.config,
            'timestamp': datetime.now()
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Model kaydedildi: {filepath}")
        
        return filepath
    
    def load_model(self, filepath: str) -> bool:
        """
        Modeli yükler
        
        Args:
            filepath: Model dosya yolu
            
        Returns:
            Yükleme başarılı mı
        """
        try:
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            
            logger.info(f"Model yüklendi: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            return False
    
    def get_prediction_confidence(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Tahmin güven skorlarını döndürür
        
        Args:
            X: Özellik matrisi
            
        Returns:
            Güven skorları DataFrame'i
        """
        predictions, probabilities = self.predict(X)
        
        confidence_df = pd.DataFrame({
            'prediction': predictions,
            'confidence': np.abs(probabilities[:, 1] - 0.5) * 2,  # 0-1 arası normalize
            'prob_up': probabilities[:, 1],
            'prob_down': probabilities[:, 0]
        })
        
        return confidence_df
    
    def evaluate_model_performance(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """
        Model performansını değerlendirir
        
        Args:
            X: Özellik matrisi
            y: Gerçek değerler
            
        Returns:
            Performans metrikleri
        """
        predictions, probabilities = self.predict(X)
        
        # Temel metrikler
        metrics = self._calculate_metrics(y, predictions, "Evaluation")
        
        # Detaylı analiz
        report = classification_report(y, predictions, output_dict=True)
        
        # Güven skorları
        confidence_scores = np.max(probabilities, axis=1)
        
        results = {
            'metrics': metrics,
            'classification_report': report,
            'avg_confidence': np.mean(confidence_scores),
            'high_confidence_accuracy': accuracy_score(
                y[confidence_scores > 0.7], 
                predictions[confidence_scores > 0.7]
            ) if len(y[confidence_scores > 0.7]) > 0 else 0
        }
        
        return results

def main():
    """Test fonksiyonu"""
    import yaml
    from data_loader import DataLoader
    from feature_engineering import FeatureEngineer
    
    # Config yükle
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Veri yükle ve özellik oluştur
    loader = DataLoader(config)
    engineer = FeatureEngineer(config)
    
    # Test verisi
    data = loader.fetch_stock_data("THYAO.IS", "2y")
    
    if not data.empty:
        features_df = engineer.create_all_features(data)
        
        # Model oluştur ve eğit
        predictor = StockDirectionPredictor(config)
        X, y = predictor.prepare_data(features_df)
        
        # Model eğitimi
        results = predictor.train_model(X, y)
        
        # Modeli kaydet
        model_path = predictor.save_model()
        
        print(f"\nModel eğitimi tamamlandı!")
        print(f"Test Accuracy: {results['test_metrics']['accuracy']:.4f}")
        print(f"Test F1 Score: {results['test_metrics']['f1']:.4f}")
        print(f"Model kaydedildi: {model_path}")

if __name__ == "__main__":
    main()

