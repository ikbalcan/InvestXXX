"""
Model Eğitimi Tab - Dashboard Modülü
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
import os
from datetime import datetime

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from model_train import StockDirectionPredictor
from backtest import Backtester
from dashboard_utils import load_config, analyze_stock_characteristics, get_auto_params

def show_model_training_tab(all_symbols):
    """Model Eğitimi Tab"""
    
    st.header("🎯 Akıllı Model Eğitimi")
    
    # Hisse seçimi ve analiz
    stock_options = all_symbols  # Ana dropdown'daki tüm hisseleri kullan
    selected_stock = st.selectbox("📊 Eğitim için Hisse Seçin:", stock_options, key="training_stock_selection")
    
    # Hisse analizi
    if selected_stock:
        with st.spinner("Hisse analiz ediliyor..."):
            analysis = analyze_stock_characteristics(selected_stock)
            
            # Dinamik güven eşiği hesapla
            if analysis:
                volatility = analysis['volatility']
                if volatility > 0.6:
                    dynamic_threshold = 0.45
                    threshold_color = "error"
                elif volatility > 0.4:
                    dynamic_threshold = 0.50
                    threshold_color = "warning"
                elif volatility > 0.25:
                    dynamic_threshold = 0.55
                    threshold_color = "info"
                else:
                    dynamic_threshold = 0.60
                    threshold_color = "success"
                
                st.info(f"🎯 Dinamik Güven Eşiği: **{dynamic_threshold:.2f}** (Volatilite: %{volatility*100:.1f})")
            
        if analysis:
            st.success("✅ Hisse analizi tamamlandı!")
            
            # Hisse karakteristikleri
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                volatility_pct = analysis['volatility'] * 100
                if volatility_pct > 40:
                    st.error(f"🔥 Volatilite: %{volatility_pct:.1f} (Yüksek)")
                elif volatility_pct > 25:
                    st.warning(f"⚠️ Volatilite: %{volatility_pct:.1f} (Orta)")
                else:
                    st.success(f"✅ Volatilite: %{volatility_pct:.1f} (Düşük)")
            
            with col2:
                volume_millions = analysis['avg_volume'] / 1_000_000
                st.info(f"📊 Ortalama Hacim: {volume_millions:.1f}M")
            
            with col3:
                range_pct = analysis['price_range'] * 100
                st.info(f"📈 Fiyat Aralığı: %{range_pct:.1f}")
            
            with col4:
                trend_pct = analysis['trend_strength'] * 100
                st.info(f"📊 Trend Gücü: %{trend_pct:.1f}")
            
            # Akıllı parametre önerileri
            st.subheader("🧠 Akıllı Parametre Önerileri")
            
            recommendations = analysis['recommendations']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🎯 Model Önerileri:**")
                st.success(f"Model Karmaşıklığı: {recommendations['model_complexity']}")
                st.success(f"Risk Seviyesi: {recommendations['risk_level']}")
                
                # Önerilen parametreler
                st.write("**📋 Önerilen Değerler:**")
                st.code(f"""
Max Depth: {recommendations['max_depth']}
Learning Rate: {recommendations['learning_rate']}
Stop Loss: %{recommendations['stop_loss']*100:.0f}
Take Profit: %{recommendations['take_profit']*100:.0f}
Günlük İşlem: {recommendations['max_daily_trades']}
Güven Eşiği: {recommendations['confidence_threshold']:.2f}
                """)
            
            with col2:
                st.write("**💡 Neden Bu Parametreler?**")
                if analysis['volatility'] > 0.4:
                    st.info("🔥 Yüksek volatilite → Konservatif yaklaşım")
                    st.info("📉 Düşük risk toleransı")
                    st.info("🛡️ Güçlü stop-loss")
                elif analysis['volatility'] > 0.25:
                    st.info("⚖️ Orta volatilite → Dengeli yaklaşım")
                    st.info("📊 Orta risk seviyesi")
                    st.info("🎯 Optimal parametreler")
                else:
                    st.info("📈 Düşük volatilite → Agresif yaklaşım")
                    st.info("🚀 Yüksek risk toleransı")
                    st.info("💪 Büyük hedefler")
    
    # Akıllı parametre önerisi - auto_params'ı her zaman tanımla
    auto_params = None
    if analysis:
        volatility = analysis['volatility']
        
        # Volatiliteye göre otomatik parametre önerisi
        if volatility > 0.6:  # Yüksek volatilite
            st.warning(f"🔥 Yüksek Volatilite (%{volatility*100:.1f}) - Konservatif parametreler öneriliyor")
            auto_params = get_auto_params(volatility)
        elif volatility > 0.4:  # Orta-yüksek volatilite
            st.info(f"⚠️ Orta-Yüksek Volatilite (%{volatility*100:.1f}) - Dengeli parametreler")
            auto_params = get_auto_params(volatility)
        else:  # Düşük volatilite
            st.success(f"✅ Düşük Volatilite (%{volatility*100:.1f}) - Agresif parametreler")
            auto_params = get_auto_params(volatility)
        
        # Otomatik parametreleri göster
        st.subheader("🎯 Otomatik Parametre Önerisi")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Güven Eşiği", f"{auto_params['confidence']:.2f}")
            st.metric("Stop Loss", f"%{auto_params['stop_loss']*100:.0f}")
        
        with col2:
            st.metric("Take Profit", f"%{auto_params['take_profit']*100:.0f}")
            st.metric("Pozisyon Büyüklüğü", f"%{auto_params['position_size']*100:.0f}")
        
        with col3:
            st.metric("Max Depth", auto_params['max_depth'])
            st.metric("Günlük İşlem", auto_params['max_trades'])
    
    # Eğitim başlat
    if st.button("🚀 Model Eğitimini Başlat", type="primary"):
        with st.spinner("Model eğitiliyor..."):
            try:
                # Otomatik parametreleri kullan
                if analysis and auto_params is not None:
                    # Volatilite analizi yapıldıysa otomatik parametreleri kullan
                    dynamic_confidence = auto_params['confidence']
                    dynamic_stop_loss = auto_params['stop_loss']
                    dynamic_take_profit = auto_params['take_profit']
                    dynamic_position_size = auto_params['position_size']
                    dynamic_max_trades = auto_params['max_trades']
                    dynamic_max_depth = auto_params['max_depth']
                    dynamic_learning_rate = auto_params['learning_rate']
                else:
                    # Varsayılan parametreler
                    dynamic_confidence = 0.60
                    dynamic_stop_loss = 0.20
                    dynamic_take_profit = 0.30
                    dynamic_position_size = 0.20
                    dynamic_max_trades = 3
                    dynamic_max_depth = 4
                    dynamic_learning_rate = 0.05
                
                # Tam konfigürasyonu oluştur (gelecek tahmin odaklı)
                full_config = {
                    'MODEL_CONFIG': {
                        'max_depth': dynamic_max_depth,  # Dinamik
                        'learning_rate': dynamic_learning_rate,  # Dinamik
                        'n_estimators': auto_params['n_estimators'] if auto_params else 100,  # Dinamik
                        'subsample': auto_params['subsample'] if auto_params else 0.8,  # Dinamik
                        'colsample_bytree': auto_params['colsample_bytree'] if auto_params else 0.8,  # Dinamik
                        'min_child_weight': auto_params['min_child_weight'] if auto_params else 1,  # Dinamik
                        'reg_alpha': auto_params['reg_alpha'] if auto_params else 0.1,  # Dinamik
                        'reg_lambda': auto_params['reg_lambda'] if auto_params else 0.1,  # Dinamik
                        'early_stopping_rounds': auto_params.get('early_stopping_rounds', 20) if auto_params else 20,  # Overfitting önleme
                        'validation_fraction': auto_params.get('validation_fraction', 0.2) if auto_params else 0.2,  # Daha fazla validation
                        'random_state': 42,
                        'n_jobs': -1
                    },
                    'RISK_MANAGEMENT': {
                        'max_position_size': dynamic_position_size,  # Dinamik
                        'stop_loss_pct': dynamic_stop_loss,  # Dinamik
                        'take_profit_pct': dynamic_take_profit,  # Dinamik
                        'max_daily_trades': dynamic_max_trades,  # Dinamik
                        'confidence_threshold': dynamic_confidence  # Dinamik güven eşiği
                    },
                    'DATA_CONFIG': {
                        'train_test_split': 0.8,
                        'min_volume_threshold': 1000000
                    },
                    'BACKTEST_CONFIG': {
                        'start_date': "2020-01-01",
                        'end_date': "2024-01-01",
                        'initial_capital': 100000,
                        'commission_rate': 0.0000,
                        'slippage_rate': 0.0000
                    },
                    'TARGET_STOCKS': [selected_stock]
                }
                
                # Model eğitimi
                predictor = StockDirectionPredictor(full_config)
                
                # Veri yükle
                data_loader = DataLoader(full_config)
                data = data_loader.fetch_stock_data(selected_stock, "2y")
                
                if data.empty:
                    st.error("Veri yüklenemedi!")
                    return
                
                # Özellikler oluştur
                feature_engineer = FeatureEngineer(full_config)
                features_df = feature_engineer.create_all_features(data)
                
                if features_df.empty:
                    st.error("Özellikler oluşturulamadı!")
                    return
                
                # Veriyi hazırla
                X, y = predictor.prepare_data(features_df)
                
                # Model eğitimi
                results = predictor.train_model(X, y)
                
                # Tahminler oluştur (backtest için gerekli)
                predictions, probabilities = predictor.predict(X)
                results['predictions'] = predictions
                results['probabilities'] = probabilities
                
                # Modeli kaydet
                model_path = predictor.save_model(f"{selected_stock.replace('.IS', '')}_Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib")
                
                st.success("✅ Model eğitimi tamamlandı!")
                
                # Sonuçları göster - Anlaşılır format
                st.subheader("📊 Model Performansı")
                
                # Model güvenilirliği
                test_accuracy = results['test_metrics']['accuracy']
                test_f1 = results['test_metrics']['f1']
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if test_accuracy > 0.7:
                        st.success(f"🎯 Model Güvenilirliği: Yüksek (%{test_accuracy*100:.1f})")
                    elif test_accuracy > 0.6:
                        st.warning(f"⚠️ Model Güvenilirliği: Orta (%{test_accuracy*100:.1f})")
                    else:
                        st.error(f"❌ Model Güvenilirliği: Düşük (%{test_accuracy*100:.1f})")
                
                with col2:
                    if test_f1 > 0.7:
                        st.success(f"🎯 Kazanma Şansı: Yüksek (%{test_f1*100:.1f})")
                    elif test_f1 > 0.6:
                        st.warning(f"⚠️ Kazanma Şansı: Orta (%{test_f1*100:.1f})")
                    else:
                        st.error(f"❌ Kazanma Şansı: Düşük (%{test_f1*100:.1f})")
                
                with col3:
                    train_accuracy = results['train_metrics']['accuracy']
                    if train_accuracy - test_accuracy > 0.1:
                        st.warning("⚠️ Overfitting Riski")
                    else:
                        st.success("✅ Model Dengeli")
                
                with col4:
                    st.success("✅ Model Kaydedildi")
                
                # Model durumu özeti
                if test_accuracy > 0.7 and test_f1 > 0.6:
                    st.success("🚀 Model durumu: Mükemmel! Hemen kullanabilirsin.")
                elif test_accuracy > 0.6 and test_f1 > 0.5:
                    st.warning("⚠️ Model durumu: İyi ama daha iyi olabilir.")
                else:
                    st.error("❌ Model durumu: Zayıf. Parametreleri ayarla.")
                
                # Feature importance
                st.subheader("🔍 En Önemli Özellikler")
                
                if isinstance(results, dict) and 'feature_importance' in results:
                    importance_data = results['feature_importance']
                    
                    if importance_data is not None and not importance_data.empty:
                        importance_df = importance_data.head(10)
                        
                        fig = px.bar(
                            importance_df, 
                            x='importance', 
                            y='feature',
                            orientation='h',
                            title="Top 10 Feature Importance"
                        )
                        fig.update_layout(height=500)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("⚠️ Feature importance verisi boş!")
                        
                        # Alternatif: Model'den direkt feature importance al
                        if hasattr(predictor.model, 'feature_importances_'):
                            st.info("🔄 Model'den direkt feature importance alınıyor...")
                            
                            # Feature isimlerini al
                            feature_names = X.columns.tolist()
                            importances = predictor.model.feature_importances_
                            
                            # DataFrame oluştur
                            importance_df = pd.DataFrame({
                                'feature': feature_names,
                                'importance': importances
                            }).sort_values('importance', ascending=False).head(10)
                            
                            fig = px.bar(
                                importance_df, 
                                x='importance', 
                                y='feature',
                                orientation='h',
                                title="Top 10 Feature Importance (Direct)"
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error("❌ Model'de feature importance bulunamadı!")
                else:
                    st.warning("⚠️ Feature importance bulunamadı!")
                
                # Model dosya yolu
                st.info(f"📁 Model kaydedildi: `{model_path}`")
                
                # Dinamik parametreler bilgisi
                st.subheader("🎯 Kullanılan Dinamik Parametreler")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Güven Eşiği", f"{dynamic_confidence:.2f}")
                    st.metric("Stop Loss", f"%{dynamic_stop_loss*100:.0f}")
                
                with col2:
                    st.metric("Take Profit", f"%{dynamic_take_profit*100:.0f}")
                    st.metric("Pozisyon Büyüklüğü", f"%{dynamic_position_size*100:.0f}")
                
                with col3:
                    st.metric("Max Depth", dynamic_max_depth)
                    st.metric("Günlük İşlem", dynamic_max_trades)
                
                # Otomatik backtest çalıştır
                st.subheader("📈 Otomatik Backtest")
                st.info("Model eğitimi tamamlandı! Dinamik parametrelerle backtest çalıştırılıyor...")
                
                with st.spinner("Backtest çalıştırılıyor..."):
                    try:
                        backtester = Backtester(full_config)
                        backtest_results = backtester.run_backtest(features_df, 
                                                                 results['predictions'], 
                                                                 results['probabilities'], 
                                                                 selected_stock)
                        
                        st.success("✅ Backtest tamamlandı!")
                        
                        # Sonuçları göster
                        col1, col2, col3 = st.columns(3)
                        
                        # Performans metriklerini al
                        performance_metrics = backtest_results.get('performance_metrics', {})
                        
                        with col1:
                            st.metric("Toplam Getiri", f"%{backtest_results['total_return']*100:.1f}")
                        with col2:
                            st.metric("Kazanma Oranı", f"%{performance_metrics.get('win_rate', 0)*100:.1f}")
                        with col3:
                            st.metric("Sharpe Ratio", f"{performance_metrics.get('sharpe_ratio', 0):.2f}")
                        
                        # İşlem sayısı ve detaylı bilgi
                        trades_count = len(backtest_results.get('trades', []))
                        st.info(f"📊 Toplam İşlem Sayısı: {trades_count}")
                        
                        # Detaylı performans bilgileri
                        st.subheader("📈 Detaylı Performans")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Yıllık Getiri", f"%{performance_metrics.get('annualized_return', 0)*100:.1f}")
                        with col2:
                            st.metric("Max Drawdown", f"%{performance_metrics.get('max_drawdown', 0)*100:.1f}")
                        with col3:
                            st.metric("Volatilite", f"%{performance_metrics.get('volatility', 0)*100:.1f}")
                        with col4:
                            st.metric("Ort. İşlem Süresi", f"{performance_metrics.get('avg_trade_duration', 0):.1f} gün")
                        
                        # Kullanılan parametreler
                        st.subheader("⚙️ Kullanılan Parametreler")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.info(f"""
                            **Risk Yönetimi:**
                            - Güven Eşiği: {dynamic_confidence:.2f}
                            - Stop Loss: %{dynamic_stop_loss*100:.0f}
                            - Take Profit: %{dynamic_take_profit*100:.0f}
                            """)
                        
                        with col2:
                            st.info(f"""
                            **Pozisyon Yönetimi:**
                            - Pozisyon Büyüklüğü: %{dynamic_position_size*100:.0f}
                            - Max Günlük İşlem: {dynamic_max_trades}
                            - Model Karmaşıklığı: {dynamic_max_depth}
                            """)
                        
                        with col3:
                            st.info(f"""
                            **Backtest Bilgileri:**
                            - Başlangıç Sermayesi: {full_config['BACKTEST_CONFIG']['initial_capital']:,} TL
                            - Final Sermayesi: {backtest_results.get('final_capital', 0):,.0f} TL
                            - Komisyon: %{full_config['BACKTEST_CONFIG']['commission_rate']*100:.2f}
                            """)
                        
                        if trades_count > 0:
                            st.success("🎉 Model çalışıyor! İşlemler yapıldı.")
                            
                            # İşlem detayları
                            with st.expander("🔍 İşlem Detayları", expanded=False):
                                trades = backtest_results.get('trades', [])
                                if trades:
                                    trades_df = pd.DataFrame(trades)
                                    st.dataframe(trades_df[['date', 'action', 'price', 'quantity', 'confidence', 'capital_after']])
                        else:
                            st.warning("⚠️ Henüz işlem yapılmadı. Parametreler ayarlanabilir.")
                            st.info("💡 **Düşük getiri sebepleri:**")
                            st.info("• Güven eşiği çok yüksek olabilir")
                            st.info("• Pozisyon büyüklüğü çok küçük olabilir")
                            st.info("• Model çok az sinyal üretiyor olabilir")
                    
                    except Exception as e:
                        st.error(f"Backtest hatası: {str(e)}")
            
            except Exception as e:
                st.error(f"Model eğitimi hatası: {str(e)}")
