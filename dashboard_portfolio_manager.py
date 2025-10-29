"""
Robot Portföy Yöneticisi Tab - Günlük Portföy Önerileri
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import json

# Proje modüllerini import et
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from dashboard_utils import load_config, load_stock_data
from dashboard_stock_hunter import analyze_single_stock, train_model_for_symbol
from price_target_predictor import PriceTargetPredictor

# Portföy verilerini sakla
PORTFOLIO_FILE = 'logs/robot_portfolio.json'

def load_portfolio():
    """Portföy verilerini yükle"""
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'cash': 0,
        'stocks': {}  # {symbol: {'quantity': int, 'avg_cost': float}}
    }

def save_portfolio(portfolio):
    """Portföy verilerini kaydet"""
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)

def format_currency(amount):
    """Parayı 2 ondalık basamakla formatla"""
    return round(amount, 2)

def get_all_bist_stocks():
    """Tüm BIST hisselerini döndür"""
    return [
        'THYAO.IS', 'AKBNK.IS', 'BIMAS.IS', 'EREGL.IS', 'FONET.IS', 'GARAN.IS',
        'ISCTR.IS', 'KRDMD.IS', 'PETKM.IS', 'SAHOL.IS', 'TUPRS.IS', 'ALBRK.IS',
        'ASELS.IS', 'FROTO.IS', 'HALKB.IS', 'TSKB.IS', 'VAKBN.IS', 'VAKFN.IS',
        'YKBNK.IS', 'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KCHOL.IS', 'KOZAL.IS',
        'MGROS.IS', 'OTKAR.IS', 'SISE.IS', 'TCELL.IS', 'TOASO.IS', 'TKFEN.IS',
        'ULKER.IS', 'VESTL.IS', 'ZOREN.IS', 'ARCLK.IS', 'AZTEK.IS', 'NETAS.IS',
        'PAMEL.IS', 'SELEC.IS', 'SMRTG.IS', 'TATGD.IS', 'ERSU.IS', 'KONYA.IS',
        'MARTI.IS', 'UNYEC.IS', 'GENIL.IS', 'PGSUS.IS', 'MEGMT.IS'
    ]

def calculate_daily_recommendations(portfolio, config, interval="1d", investment_horizon="MEDIUM_TERM"):
    """Günlük önerileri hesapla"""
    recommendations = []
    cash = portfolio['cash']
    stocks = portfolio['stocks']
    
    # Önce mevcut pozisyonlar için analiz yap - SAT/ARTIR/TUT
    analyzed_positions = {}
    
    # Mevcut pozisyonlar için öneri üret
    for symbol in stocks:
        try:
            stock_info = stocks[symbol]
            quantity = stock_info['quantity']
            avg_cost = stock_info['avg_cost']
            
            # Model kontrolü ve otomatik eğitim
            symbol_name = symbol.replace('.IS', '')
            model_exists = False
            
            if os.path.exists('src/models'):
                model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
                model_exists = any(symbol_name in f for f in model_files)
            
            # Model yoksa otomatik eğit (sessiz mod)
            if not model_exists:
                try:
                    # Sessiz modda model eğit (mesaj gösterme)
                    success, message = train_model_for_symbol(
                        symbol, config, 
                        progress_callback=None,  # Sessiz mod
                        interval=interval, 
                        investment_horizon=investment_horizon
                    )
                except Exception as e:
                    # Model eğitimi başarısız olsa bile devam et
                    pass
            
            # Hisse analizi yap
            result = analyze_single_stock(symbol, config, period="1y", interval=interval)
            
            if result is None:
                continue
            
            current_price = result['current_price']
            prediction = result.get('prediction')
            confidence = result.get('confidence', 0.5)
            
            # Mevcut değer
            current_value = quantity * current_price
            total_cost = quantity * avg_cost
            profit_loss = current_value - total_cost
            profit_loss_pct = (current_value / total_cost - 1) * 100 if total_cost > 0 else 0
            
            # Öneri mantığı - Daha agresif ve öneri odaklı
            action = "TUT"
            action_reason = "Sinyal net değil - Bekle"
            
            # Teknik analiz sinyalleri de kontrol et (model yoksa veya güven düşükse)
            rsi = result.get('rsi', 50)
            trend_strength = result.get('trend_strength', '')
            volume_ratio = result.get('volume_ratio', 1.0)
            
            # Teknik analiz tabanlı sinyal hesapla
            technical_signal = None
            technical_confidence = 0.5
            
            if rsi < 35 and trend_strength == "Yükseliş" and volume_ratio > 1.2:
                technical_signal = 1  # AL
                technical_confidence = 0.60
            elif rsi > 65 and trend_strength == "Düşüş" and volume_ratio > 1.2:
                technical_signal = 0  # SAT
                technical_confidence = 0.60
            elif rsi < 30:
                technical_signal = 1  # AL (aşırı satım)
                technical_confidence = 0.55
            elif rsi > 70:
                technical_signal = 0  # SAT (aşırı alım)
                technical_confidence = 0.55
            
            # Model tahmini yoksa teknik analizi kullan
            if prediction is None and technical_signal is not None:
                prediction = technical_signal
                confidence = technical_confidence
            
            # Güçlü AL sinyali (>60% güven) - Eşik düşürüldü
            if prediction == 1 and confidence > 0.60:
                if profit_loss_pct > -5:  # %5'ten fazla zararda değilse
                    action = "ARTIR"
                    action_reason = f"🟢 Güçlü yükseliş sinyali - Fırsat (%{confidence*100:.0f} güven)"
                else:
                    action = "TUT"
                    action_reason = f"⚠️ Zararda pozisyon - Bekle (%{profit_loss_pct:.1f}%)"
            # Güçlü SAT sinyali (>60% güven)
            elif prediction == 0 and confidence > 0.60:
                if profit_loss_pct > 3:  # %3'ten fazla karda ise - eşik düşürüldü
                    action = "KISMEN SAT"
                    action_reason = f"🔴 Karı realize et - Düşüş sinyali (%{confidence*100:.0f} güven, %{profit_loss_pct:.1f} kar)"
                elif profit_loss_pct < -7:  # %7'den fazla zarardaysa - eşik düşürüldü
                    action = "SAT"
                    action_reason = f"⚠️ Stop Loss - Güçlü düşüş sinyali (%{confidence*100:.0f} güven, %{profit_loss_pct:.1f} zarar)"
                elif profit_loss_pct < 0 and profit_loss_pct > -5:
                    action = "KISMEN SAT"  # Küçük zararda kısmi satış öner
                    action_reason = f"💰 Küçük zarar - Kısmi stop loss (%{profit_loss_pct:.1f}%)"
                else:
                    action = "TUT"
                    action_reason = "📊 Pozisyon durumu normal"
            # Orta güvenli sinyal (55-60%) - Artık öneri veriyor
            elif prediction == 1 and 0.55 < confidence <= 0.60:
                if profit_loss_pct > -3:
                    action = "ARTIR"
                    action_reason = f"📈 Orta güvenli yükseliş sinyali - İhtiyatlı artırım (%{confidence*100:.0f} güven)"
                else:
                    action = "TUT"
                    action_reason = f"📈 Yükseliş ama zararda - Bekle (%{confidence*100:.0f} güven)"
            elif prediction == 0 and 0.55 < confidence <= 0.60:
                if profit_loss_pct > 2:  # Biraz karda ise
                    action = "KISMEN SAT"
                    action_reason = f"📉 Orta güvenli düşüş riski - İhtiyatlı satış (%{confidence*100:.0f} güven)"
                elif profit_loss_pct < -5:
                    action = "KISMEN SAT"
                    action_reason = f"📉 Küçük stop loss önerisi (%{profit_loss_pct:.1f}%)"
                else:
                    action = "TUT"
                    action_reason = f"📉 Düşüş riski orta seviyede - İzle (%{confidence*100:.0f} güven)"
            # Hafif sinyal (50-55%) - En azından bilgi ver
            elif prediction == 1 and 0.50 < confidence <= 0.55:
                if profit_loss_pct > 0:
                    action = "TUT"
                    action_reason = f"📊 Hafif yükseliş eğilimi - Karda olduğun için bekle (%{confidence*100:.0f} güven)"
                else:
                    action = "TUT"
                    action_reason = f"📊 Hafif yükseliş ama zararda - Dikkatli takip et (%{confidence*100:.0f} güven)"
            elif prediction == 0 and 0.50 < confidence <= 0.55:
                if profit_loss_pct > 5:
                    action = "TUT"
                    action_reason = f"📊 Hafif düşüş riski ama iyi karda - Dikkatli takip et (%{confidence*100:.0f} güven)"
                elif profit_loss_pct < -3:
                    action = "TUT"
                    action_reason = f"📊 Hafif düşüş riski ve zararda - Dikkatli izle (%{confidence*100:.0f} güven)"
                else:
                    action = "TUT"
                    action_reason = f"📊 Hafif sinyal - Net değil (%{confidence*100:.0f} güven)"
            # Düşük güven veya sinyal yok - Teknik analizle öner
            else:
                if technical_signal == 1:
                    action = "TUT"
                    action_reason = f"📊 Teknik analiz: Aşırı satım bölgesinde - Dikkatli takip (RSI: {rsi:.1f})"
                elif technical_signal == 0:
                    if profit_loss_pct > 2:
                        action = "KISMEN SAT"
                        action_reason = f"📊 Teknik analiz: Aşırı alım bölgesinde - İhtiyatlı satış (RSI: {rsi:.1f})"
                    else:
                        action = "TUT"
                        action_reason = f"📊 Teknik analiz: Aşırı alım ama karda değilsin (RSI: {rsi:.1f})"
                else:
                    action = "TUT"
                    action_reason = "⏳ Sinyal belirsiz - Pozisyon koru"
            
            # Hesaplanacak miktar
            recommended_quantity = 0
            recommended_value = 0
            recommended_price = current_price
            
            if action == "ARTIR":
                # Nakit varsa artırım öner
                if cash > 0:
                    # Maksimum %15 sermaye ile artırım - daha agresif
                    max_addition = cash * 0.15
                    recommended_value = min(max_addition, current_value * 0.4)  # Mevcut pozisyonun %40'ına kadar
                    recommended_quantity = int(recommended_value / current_price)
                    # En az 1 lot öner
                    if recommended_quantity == 0:
                        recommended_quantity = 1
                        recommended_value = recommended_quantity * current_price
                else:
                    # Nakit yoksa öneriyi göster ama miktar 0
                    recommended_quantity = 0
                    recommended_value = 0
                    # Öneri sebebini güncelle
                    action_reason += " (Nakit gerekli)"
            elif action == "KISMEN SAT":
                # Yarısını sat
                recommended_quantity = int(quantity / 2)
                if recommended_quantity == 0:
                    recommended_quantity = quantity  # Eğer 1 adetteyse tümünü sat
                recommended_value = recommended_quantity * current_price
            elif action == "SAT":
                # Tümünü sat
                recommended_quantity = quantity
                recommended_value = current_value
            
            recommendations.append({
                'symbol': symbol,
                'current_price': current_price,
                'recommended_price': recommended_price,
                'quantity': quantity,
                'avg_cost': avg_cost,
                'current_value': current_value,
                'total_cost': total_cost,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'prediction': prediction,
                'confidence': confidence,
                'action': action,
                'action_reason': action_reason,
                'recommended_quantity': recommended_quantity,
                'recommended_value': recommended_value,
                'signal_strength': result.get('score', 0),
                'result': result  # Analiz sonucunu ekle
            })
            
        except Exception as e:
            st.warning(f"❌ {symbol} analizi hatası: {str(e)}")
            continue
    
    # Yeni alım önerileri için satışlardan gelecek nakit'i hesapla
    remaining_cash = cash
    
    # İlk olarak önerilen işlemleri kontrol et
    for rec in recommendations:
        if rec['action'] == "ARTIR":
            remaining_cash -= rec['recommended_value']
        elif rec['action'] in ["SAT", "KISMEN SAT"]:
            remaining_cash += rec['recommended_value']  # Satıştan gelen para
    
    # Mevcut portföyde olmayan hisseler için öneriler
    all_stocks = get_all_bist_stocks()
    # 50K yerine daha esnek: en az satıştan gelen nakit varsa öner
    min_cash_for_new_stocks = max(30000, remaining_cash * 0.3)  # En az 30K veya mevcut nakitin %30'u
    
    # HISSE AVCISI TARZI - Tüm hisseleri analiz et ve en iyilerini seç
    if remaining_cash > min_cash_for_new_stocks:
        scored_candidates = []
        
        for symbol in all_stocks:
            if symbol not in stocks:  # Sadece portföyde olmayan hisseler
                try:
                    # Model kontrolü ve otomatik eğitim
                    symbol_name = symbol.replace('.IS', '')
                    model_exists = False
                    
                    if os.path.exists('src/models'):
                        model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
                        model_exists = any(symbol_name in f for f in model_files)
                    
                    # Model yoksa otomatik eğit (sessiz mod)
                    if not model_exists:
                        try:
                            # Sessiz modda model eğit (mesaj gösterme)
                            success, message = train_model_for_symbol(
                                symbol, config, 
                                progress_callback=None,  # Sessiz mod
                                interval=interval, 
                                investment_horizon=investment_horizon
                            )
                        except Exception as e:
                            # Model eğitimi başarısız olsa bile devam et
                            pass
                    
                    result = analyze_single_stock(symbol, config, period="1y", interval=interval, silent=True)
                    
                    if result is None:
                        continue
                    
                    prediction = result.get('prediction')
                    confidence = result.get('confidence', 0.5)
                    score = result.get('score', 0)
                    current_price = result['current_price']
                    
                    # AL sinyali olan hisseleri düşün - güven eşiğini %48'e düşür (daha fazla seçenek için)
                    if prediction == 1 and confidence > 0.48:
                        scored_candidates.append({
                            'symbol': symbol,
                            'current_price': current_price,
                            'prediction': prediction,
                            'confidence': confidence,
                            'score': score,
                            'result': result
                        })
                
                except:
                    continue
        
        # En yüksek skorlu olanları seç - HISSE AVCISI MANTIGI
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Satıştan gelen toplam parayı hesapla
        sell_cash = sum([r['recommended_value'] for r in recommendations if r['action'] in ['SAT', 'KISMEN SAT']])
        total_cash_after_sell = cash + sell_cash
        
        # RİSK YÖNETİMİ: En az 3-5 hisse seç (çeşitlendirme için zorunlu)
        # Sadece 1-2 hisse bulunursa bile, güven eşiğini düşürerek daha fazla hisse bul
        
        # Önce en iyi 7-10 hisseyi dene (daha fazla seçenek)
        num_candidates = min(10, len(scored_candidates))
        top_candidates = scored_candidates[:num_candidates]
        
        # RİSK YÖNETİMİ: En az 3-5 hisse bulunmalı - eğer yoksa daha fazla hisse bul
        if len(top_candidates) < 5:
            # Tüm scored_candidates listesini kontrol et (zaten %50 güven eşiği ile geldi)
            # Skorlarına göre sırala ve en iyi olanları ekle
            all_candidates = sorted(scored_candidates, key=lambda x: x['score'], reverse=True)
            
            # En az 5 hisse bulunana kadar ekle
            needed = 5 - len(top_candidates)
            additional_candidates = all_candidates[len(top_candidates):len(top_candidates) + needed + 3]  # Biraz fazla seç
            
            # Eğer hala yeterli değilse, güven eşiğini %45'e düşür ve yeniden ara
            if len(top_candidates) + len(additional_candidates) < 5:
                # Tüm hisseleri yeniden kontrol et (daha düşük eşikle)
                checked_symbols = set([c['symbol'] for c in top_candidates + additional_candidates])
                for symbol in all_stocks:
                    if symbol not in stocks and symbol not in checked_symbols:
                        try:
                            # Model kontrolü ve otomatik eğitim
                            symbol_name = symbol.replace('.IS', '')
                            model_exists = False
                            
                            if os.path.exists('src/models'):
                                model_files = [f for f in os.listdir('src/models') if f.endswith('.joblib')]
                                model_exists = any(symbol_name in f for f in model_files)
                            
                            # Model yoksa otomatik eğit (sessiz mod)
                            if not model_exists:
                                try:
                                    success, message = train_model_for_symbol(
                                        symbol, config, 
                                        progress_callback=None,
                                        interval=interval, 
                                        investment_horizon=investment_horizon
                                    )
                                except Exception as e:
                                    pass
                            
                            result = analyze_single_stock(symbol, config, period="1y", interval=interval, silent=True)
                            if result is None:
                                continue
                            
                            prediction = result.get('prediction')
                            confidence = result.get('confidence', 0.5)
                            if prediction == 1 and confidence > 0.45:  # %45'e düşür
                                additional_candidates.append({
                                    'symbol': symbol,
                                    'current_price': result['current_price'],
                                    'prediction': prediction,
                                    'confidence': confidence,
                                    'score': result.get('score', 0),
                                    'result': result
                                })
                                checked_symbols.add(symbol)
                                if len(top_candidates) + len(additional_candidates) >= 7:
                                    break
                        except:
                            continue
            
            top_candidates.extend(additional_candidates[:needed])
            
            # Son durumda skorlarına göre sırala ve en iyi 5-7 hisseyi seç
            top_candidates = sorted(top_candidates, key=lambda x: x['score'], reverse=True)[:min(7, len(top_candidates))]
            
            # Minimum 3 hisse garantisi - eğer hala azsa en iyi olanları zorla seç
            if len(top_candidates) < 3 and len(scored_candidates) >= 3:
                top_candidates = scored_candidates[:3]  # En az 3 hisse zorla seç
        
        for idx, candidate in enumerate(top_candidates):
            symbol = candidate['symbol']
            current_price = candidate['current_price']
            confidence = candidate['confidence']
            score = candidate['score']
            
            # Dinamik tahsis: RİSK YÖNETİMİ - Çeşitlendirme önemli!
            num_candidates = len(top_candidates)
            
            if num_candidates == 1:
                # Sadece 1 hisse varsa bile - maksimum %30 (risk yönetimi)
                allocation_pct = 0.30
            elif num_candidates == 2:
                # 2 hisse varsa - her birine %25-30
                allocation_pct = 0.30
            elif num_candidates == 3:
                # 3 hisse varsa - her birine %20 (60% toplam)
                allocation_pct = 0.20
            elif num_candidates <= 5:
                # 4-5 hisse varsa - her birine %15-18
                allocation_pct = 0.18
            else:
                # 6+ hisse varsa - her birine %12-15
                allocation_pct = 0.15
            
            # Sermayenin tahsis edilen yüzdesi kadar öner
            recommended_value = min(
                total_cash_after_sell * allocation_pct,  # Toplam sermayenin tahsis yüzdesi
                remaining_cash  # Kalan nakitten fazla olmamalı
            )
            
            # En az fiyatın 50 katı kadar öner
            min_value = current_price * 50
            recommended_value = max(min_value, recommended_value)
            
            # Eğer son hisseyse ve hala çok nakit kaldıysa, makul bir şekilde kullan
            if idx == len(top_candidates) - 1:
                # Son hisse için kalan paranın %50'sini kullan (maksimum)
                if remaining_cash > recommended_value * 1.5:  # Eğer kalan nakit önerilenden 1.5x fazlaysa
                    # Ama toplam tahsisi %30'u geçmesin (risk yönetimi)
                    max_allocation = total_cash_after_sell * 0.30
                    recommended_value = min(remaining_cash * 0.50, max_allocation)
            
            recommended_quantity = int(recommended_value / current_price)
            
            if recommended_quantity > 0 and remaining_cash >= recommended_value:
                # Hedef fiyat ve tarih bilgilerini hesapla
                try:
                    result_data = candidate['result']
                    volatility = result_data.get('volatility', 0.3)
                    data = load_stock_data(symbol, period="1y", interval=interval, silent=True)
                    
                    if not data.empty:
                        price_predictor = PriceTargetPredictor(config)
                        price_targets = price_predictor.calculate_price_targets(
                            current_price, 
                            candidate['prediction'], 
                            confidence, 
                            volatility / 100 if volatility > 1 else volatility, 
                            data,
                            {}
                        )
                        
                        # Hedef fiyat bilgilerini ekle
                        target_moderate = price_targets['targets']['moderate']
                        time_targets = price_targets.get('time_targets', {})
                        moderate_time = time_targets.get('moderate', {})
                        
                        estimated_days = moderate_time.get('estimated_days', 30)
                        min_date = moderate_time.get('min_date', '')
                        max_date = moderate_time.get('max_date', '')
                    else:
                        target_moderate = current_price * 1.10  # Varsayılan %10 artış
                        estimated_days = 30
                        min_date = ''
                        max_date = ''
                except Exception as e:
                    # Hata durumunda varsayılan değerler
                    target_moderate = current_price * 1.10
                    estimated_days = 30
                    min_date = ''
                    max_date = ''
                
                recommendations.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'recommended_price': current_price,
                    'target_price': target_moderate,
                    'target_days': estimated_days,
                    'target_min_date': min_date,
                    'target_max_date': max_date,
                    'quantity': 0,
                    'avg_cost': 0,
                    'current_value': 0,
                    'total_cost': 0,
                    'profit_loss': 0,
                    'profit_loss_pct': 0,
                    'prediction': candidate['prediction'],
                    'confidence': confidence,
                    'action': "YENİ AL",
                    'action_reason': f"Güçlü yükseliş fırsatı (%{confidence*100:.0f} güven)",
                    'recommended_quantity': recommended_quantity,
                    'recommended_value': recommended_value,
                    'signal_strength': score,
                    'from_sell': True,
                    'allocation_pct': allocation_pct,
                    'result': candidate.get('result', {})  # Analiz sonucunu ekle
                })
                remaining_cash -= recommended_value
                
                # Kalan nakdi azaldıysa dur
                if remaining_cash < total_cash_after_sell * 0.05:  # %5'in altındaysa dur
                    break
    
    return recommendations

def show_portfolio_manager_tab(config, interval="1d", investment_horizon="MEDIUM_TERM"):
    """Robot Portföy Yöneticisi sekmesini göster"""
    
    # Başlık
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; 
                border-radius: 15px; 
                margin-bottom: 30px;
                text-align: center;">
        <h1 style="color: white; margin: 0;">🤖 Robot Portföy Yöneticisi</h1>
        <p style="color: white; margin: 10px 0 0 0; font-size: 1.1em;">
            AI Destekli Günlük Yatırım Kararları
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Bilgilendirme
    with st.expander("ℹ️ Robot Portföy Yöneticisi Nedir?", expanded=False):
        st.markdown("""
        **Robot Portföy Yöneticisi**, gün sonunda hisse senedi borsasını kapattıktan sonra yapmanız gereken işlemleri gösterir.
        
        #### 🎯 Nasıl Çalışır?
        - **Nakit paranızı** girin (örn: 100,000 TL)
        - **Mevcut portföyünüzü** ekleyin (hangi hisselerden kaç adet var, ortalama maliyetiniz ne?)
        - Sistem **AI analizi** yaparak günlük öneriler sunar
        
        #### 🤖 Öneri Mantığı:
        - **AL/ARTIR:** Güçlü yükseliş sinyali varsa - Fırsat kaçmasın
        - **SAT:** Karı realize et veya zararı durdur - Risk yönetimi
        - **TUT:** Sinyal net değil - Zırt pırt değişiklik yapma
        
        #### 💡 Özellikleri:
        - Gereksiz işlem önleme (zırt pırt değişiklik yapmaz)
        - Maliyet bazlı karar (aldığınız fiyata göre)
        - Net öneriler (ne kadar al, ne kadar sat - çok net)
        """)
    
    # Portföy yükle
    portfolio = load_portfolio()
    
    # === PORTFÖY GİRİŞİ ===
    st.markdown("---")
    st.markdown("### 📝 Portföy Bilgileri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cash = st.number_input(
            "💵 Nakit Para (TL):",
            min_value=0,
            value=portfolio['cash'],
            step=1000,
            help="Borsaya yatırılacak nakit parayı girin"
        )
    
    with col2:
        st.metric(
            "📊 Mevcut Portföy",
            f"{len(portfolio['stocks'])} hisse",
            help="Portföydeki hisse sayısı"
        )
    
    # === HİSSE EKLEME/SİLME ===
    st.markdown("#### 📋 Portföydeki Hisseler")
    
    all_stocks = get_all_bist_stocks()
    
    # Yeni hisse ekleme
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        new_stock = st.selectbox(
            "Hisse Seç:",
            all_stocks,
            key="new_stock_select"
        )
    
    with col2:
        stock_quantity = st.number_input(
            "Adet:",
            min_value=1,
            value=100,
            step=10,
            key="stock_quantity"
        )
    
    with col3:
        stock_cost = st.number_input(
            "Ortalama Maliyet (TL):",
            min_value=0.01,
            value=100.0,
            step=0.10,
            key="stock_cost"
        )
    
    if st.button("➕ Hisse Ekle", type="primary"):
        portfolio['stocks'][new_stock] = {
            'quantity': int(stock_quantity),
            'avg_cost': float(stock_cost)
        }
        save_portfolio(portfolio)
        st.success(f"✅ {new_stock} eklendi!")
        st.rerun()
    
    # Mevcut hisseleri göster
    if portfolio['stocks']:
        st.markdown("**Mevcut Pozisyonlar:**")
        for symbol, info in portfolio['stocks'].items():
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            
            with col1:
                st.write(f"📊 {symbol}")
            
            with col2:
                st.write(f"{info['quantity']:.0f} adet")
            
            with col3:
                st.write(f"{info['avg_cost']:.2f} TL")
            
            with col4:
                total_cost = info['quantity'] * info['avg_cost']
                st.write(f"{format_currency(total_cost):,.2f} TL")
            
            with col5:
                if st.button(f"❌", key=f"del_{symbol}", help="Sil"):
                    del portfolio['stocks'][symbol]
                    save_portfolio(portfolio)
                    st.rerun()
    
    # Nakit güncelle
    portfolio['cash'] = cash
    save_portfolio(portfolio)
    
    # === GÜNLÜK ÖNERİLER ===
    if portfolio['cash'] > 0 or portfolio['stocks']:
        st.markdown("---")
        
        # Kompakt başlık
        st.markdown("### 🤖 Günlük Portföy Analizi")
        st.info("💡 AI senin için bugün ne yapman gerektiğine karar verdi!")
        
        # Portföy özeti
        total_portfolio_value = sum([s['quantity'] * s['avg_cost'] for s in portfolio['stocks'].values()])
        total_cash = portfolio['cash']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💵 Toplam Nakit", f"{format_currency(total_cash):,.2f} TL")
        with col2:
            st.metric("📊 Portföy Değeri", f"{format_currency(total_portfolio_value):,.2f} TL")
        with col3:
            st.metric("💰 Toplam Sermaye", f"{format_currency(total_cash + total_portfolio_value):,.2f} TL")
        
        st.markdown("---")
        
        # Büyük analiz başlat butonu ve durumu
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            # Loading durumunu kontrol et
            is_analyzing = st.session_state.get('analyze_clicked', False)
            
            if is_analyzing:
                # Analiz yapılırken butonu göster (devre dışı görünüm)
                st.button("⏳ ANALİZ YAPILIYOR...", disabled=True, use_container_width=True)
            else:
                analyze_button = st.button("🤖 GÜNLÜK ANALİZİ BAŞLAT - AI ÖNERİLERİNİ AL", type="primary", use_container_width=True)
                if analyze_button:
                    st.session_state.analyze_clicked = True
                    st.rerun()  # Sayfayı yenileyerek loading göster
        
        # Progress mesajı - Sadece butona basıldığında analiz yap
        if st.session_state.get('analyze_clicked', False):
            # UI Friendly loading
            with st.spinner("🔍 AI analizi başladı..."):
                progress_bar = st.progress(0)
                progress_status = st.empty()
                
                # Simüle edilmiş progress
                progress_bar.progress(10)
                progress_status.text("📊 Mevcut pozisyonlar analiz ediliyor...")
                
                progress_bar.progress(20)
                progress_status.text("🤖 Model durumu kontrol ediliyor...")
                
                progress_bar.progress(40)
                progress_status.text("💰 Satış önerileri hesaplanıyor...")
                
                progress_bar.progress(60)
                progress_status.text("🔍 Yeni hisse fırsatları taraniyor...")
                
                progress_bar.progress(80)
                progress_status.text("🎯 En iyi fırsatlar seçiliyor...")
                
                recommendations = calculate_daily_recommendations(
                    portfolio, config, interval, investment_horizon
                )
                
                progress_bar.progress(90)
                progress_status.text("📋 Öneriler hazırlanıyor...")
                
                # Sonuçları sakla
                st.session_state.last_recommendations = recommendations
                st.session_state.analyze_clicked = False  # Analiz tamamlandı
                
                progress_bar.progress(100)
                progress_status.text("✅ Analiz tamamlandı!")
                
        else:
            # Önceki sonuçları kullan veya boş
            recommendations = st.session_state.get('last_recommendations', [])
            
            # Eğer hiç analiz yoksa kullanıcıya bilgi ver
            if not recommendations:
                st.warning("ℹ️ Analizi başlatmak için yukarıdaki butona basın.")
        
        if recommendations:
            # Özet kartları
            actions = [r['action'] for r in recommendations]
            st.metrics = {"Önerilen İşlem": f"{len(recommendations)} hisse"}
            
            # İşlem grupları - İŞLEM SIRASINA GÖRE (SAT → AL → ARTIR → TUT)
            sell_actions = [r for r in recommendations if r['action'] in ['SAT', 'KISMEN SAT']]
            new_buy_actions = [r for r in recommendations if r['action'] == 'YENİ AL']
            increase_actions = [r for r in recommendations if r['action'] == 'ARTIR']
            hold_actions = [r for r in recommendations if r['action'] == 'TUT']
            
            # Tüm buy actions (gösterim için)
            buy_actions = new_buy_actions + increase_actions
            
            # Satıştan gelen nakit bilgisi - BÜYÜK VE ÇARPICI
            total_sell_cash = sum([r['recommended_value'] for r in sell_actions])
            if total_sell_cash > 0:
                # Bu nakitle nereye yatırım yapılacağını göster
                new_buy_from_sell = [r for r in buy_actions if r.get('from_sell', False)]
                
                if new_buy_from_sell:
                    total_buy_from_sell = sum([r['recommended_value'] for r in new_buy_from_sell])
                    usage_pct = (total_buy_from_sell / total_sell_cash * 100) if total_sell_cash > 0 else 0
                    
                    # BÜYÜK BANNER - ÖNEMLİ BİLGİ
                    # Kompakt banner
                    st.success(f"💰 **SATIŞLARDAN GELECEK:** {format_currency(total_sell_cash):,.2f} TL\n"
                              f"💡 Bu para ile {format_currency(total_buy_from_sell):,.2f} TL ({usage_pct:.0f}%) tutarında **{len(new_buy_from_sell)} yeni hisse** önerisi hazırlandı!")
            
            # 1. SATIŞ ÖNERİLERİ (ÖNCE SAT - PARA ÇIKACAK)
            if sell_actions:
                st.markdown("#### 🔴 1️⃣ SATIŞ ÖNERİLERİ (Önce bunları yap)")
                for rec_idx, rec in enumerate(sell_actions):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.markdown(f"### 📉 {rec['symbol']}")
                        if rec['action'] == 'SAT':
                            st.error("⚠️ Tüm Pozisyonu Sat")
                        else:
                            st.warning("⚠️ Kısmi Satış")
                    
                    with col2:
                        st.metric("💰 Güncel Fiyat", f"{format_currency(rec['current_price']):,.2f} TL")
                        st.metric("📦 Önerilen Satış", f"{rec['recommended_quantity']:.0f} adet")
                        st.metric("📊 Mevcut", f"{rec['quantity']:.0f} adet")
                    
                    with col3:
                        st.metric("💵 Satış Tutarı", f"{format_currency(rec['recommended_value']):,.2f} TL")
                        st.metric("📈 Kar/Zarar", f"{rec['profit_loss_pct']:+.2f}%", 
                                delta=f"{format_currency(rec['profit_loss']):+,.2f} TL")
                        st.caption(f"Ortalama maliyet: {format_currency(rec['avg_cost']):,.2f} TL")
                    st.markdown(f"**💬 Ne Yapılacak:** {rec['recommended_quantity']:.0f} adet {rec['symbol']} sat, {format_currency(rec['recommended_value']):,.2f} TL al")
                    # Sadece neden varsa göster
                    if rec.get('action_reason'):
                        st.caption(f"💡 {rec['action_reason']}")
                    st.divider()
            
            # 2. YENİ ALIM ÖNERİLERİ (SATIŞTAN SONRA - YENİ HİSSELER)
            if new_buy_actions:
                st.markdown("#### 🟢 2️⃣ YENİ ALIM ÖNERİLERİ (Satıştan gelen parayla)")
                for rec in new_buy_actions:
                    is_from_sell = rec.get('from_sell', False)
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.markdown(f"### 📈 {rec['symbol']}")
                        if is_from_sell:
                            st.success("🆕 Yeni Alım (Satıştan gelen parayla)")
                        else:
                            st.success("🆕 Yeni Alım Önerisi")
                    
                    with col2:
                        st.metric("💰 Güncel Fiyat", f"{format_currency(rec['current_price']):,.2f} TL")
                        st.metric("📦 Önerilen Miktar", f"{rec['recommended_quantity']:.0f} adet")
                        # Hedef fiyat bilgisi
                        target_price = rec.get('target_price', rec['current_price'])
                        potential_return = ((target_price - rec['current_price']) / rec['current_price']) * 100
                        st.metric("🎯 Hedef Fiyat", f"{format_currency(target_price):,.2f} TL", 
                                delta=f"%{potential_return:+.1f} getiri")
                    
                    with col3:
                        st.metric("💵 İşlem Tutarı", f"{format_currency(rec['recommended_value']):,.2f} TL")
                        st.metric("🎯 Güven Skoru", f"%{rec['confidence']*100:.0f}")
                        allocation = rec.get('allocation_pct', 0)
                        if allocation > 0:
                            st.caption(f"📊 Portföy Tahsisi: %{allocation*100:.0f}")
                        
                        # Hedef tarih bilgisi
                        target_days = rec.get('target_days', 30)
                        target_min_date = rec.get('target_min_date', '')
                        target_max_date = rec.get('target_max_date', '')
                        if target_min_date and target_max_date:
                            st.caption(f"📅 Hedef Tarih: {target_min_date} - {target_max_date}")
                        elif target_days:
                            target_date = (datetime.now() + timedelta(days=target_days)).strftime('%d.%m.%Y')
                            st.caption(f"📅 Tahmini Süre: ~{target_days} gün ({target_date})")
                        
                        if is_from_sell:
                            st.markdown(f"**💬 Ne Yapılacak:** Satıştan gelen parayla {rec['recommended_quantity']:.0f} adet {rec['symbol']} al, {format_currency(rec['recommended_value']):,.2f} TL harca")
                        else:
                            st.markdown(f"**💬 Ne Yapılacak:** {rec['recommended_quantity']:.0f} adet {rec['symbol']} al, {format_currency(rec['recommended_value']):,.2f} TL harca")
                    
                    # Sadece neden varsa göster
                    if rec.get('action_reason'):
                        st.caption(f"💡 {rec['action_reason']}")
                    
                    # Neden AL dediğinin detaylı özeti
                    st.markdown("**📋 Neden AL Önerisi:**")
                    from dashboard_portfolio_export import generate_buy_reasons
                    buy_reasons = generate_buy_reasons(rec)
                    for reason in buy_reasons:
                        st.markdown(f"  • {reason}")
                    
                    st.divider()
            
            # 3. MEVCUT POZİSYON ARTIRIMI (OPTIONAL)
            if increase_actions:
                st.markdown("#### 📈 3️⃣ MEVCUT POZİSYON ARTIRIMLARI")
                for rec in increase_actions:
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.markdown(f"### 📈 {rec['symbol']}")
                        st.success("📊 Mevcut Pozisyon Artırımı")
                    
                    with col2:
                        st.metric("💰 Güncel Fiyat", f"{format_currency(rec['current_price']):,.2f} TL")
                        st.metric("📦 Önerilen Miktar", f"{rec['recommended_quantity']:.0f} adet")
                        st.caption(f"Şu an: {rec['quantity']:.0f} adet")
                    
                    with col3:
                        st.metric("💵 İşlem Tutarı", f"{format_currency(rec['recommended_value']):,.2f} TL")
                        st.metric("🎯 Güven Skoru", f"%{rec['confidence']*100:.0f}")
                        st.caption(f"Ortalama maliyet: {format_currency(rec['avg_cost']):,.2f} TL")
                    st.markdown(f"**💬 Ne Yapılacak:** {rec['recommended_quantity']:.0f} adet {rec['symbol']} al, {format_currency(rec['recommended_value']):,.2f} TL harca")
                    # Sadece neden varsa göster
                    if rec.get('action_reason'):
                        st.caption(f"💡 {rec['action_reason']}")
                    
                    # Neden ARTIR dediğinin detaylı özeti
                    st.markdown("**📋 Neden ARTIR Önerisi:**")
                    from dashboard_portfolio_export import generate_increase_reasons
                    increase_reasons = generate_increase_reasons(rec)
                    for reason in increase_reasons:
                        st.markdown(f"  • {reason}")
                    
                    st.divider()
            
            # 4. TUT/BEKLETİLECEK HİSSELER - Her zaman göster, detaylı açıkla
            if hold_actions:
                # Aktif işlem varsa "BEKLE-GÖR" yerine daha açıklayıcı başlık
                if buy_actions or sell_actions:
                    st.markdown("#### 🟡 4️⃣ Takip Edilecek Hisseler (İşlem yok)")
                else:
                    st.markdown("#### 🟡 BEKLE-GÖR - Detaylı Analiz")
                
                # TUT önerilerini detaylı göster - HER ZAMAN AÇIK
                st.markdown("**📊 Pozisyon Analizi:**")
                for rec in hold_actions:
                    # Mevcut pozisyon bilgisi
                    current_value = rec.get('current_value', 0)
                    profit_loss = rec.get('profit_loss', 0)
                    profit_loss_pct = rec.get('profit_loss_pct', 0)
                    
                    # Renk kodlu bilgi
                    if profit_loss_pct > 0:
                        status_emoji = "🟢"
                        status_color = "green"
                    elif profit_loss_pct < -5:
                        status_emoji = "🔴"
                        status_color = "red"
                    else:
                        status_emoji = "🟡"
                        status_color = "orange"
                    
                    # Kar/zarar rengi
                    profit_color = "green" if profit_loss >= 0 else "red"
                    
                    # Model güveni bilgisi
                    confidence_html = ""
                    if rec.get('confidence'):
                        confidence_val = rec.get('confidence', 0) * 100
                        confidence_html = f"<p style='margin: 5px 0; color: #6c757d; font-size: 0.9em;'>🤖 Model Güveni: {confidence_val:.0f}%</p>"
                    
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid {status_color}">
                        <h4 style="margin: 0 0 10px 0;">{status_emoji} <strong>{rec['symbol']}</strong></h4>
                        <p style="margin: 5px 0;"><strong>Mevcut Pozisyon:</strong> {rec['quantity']:.0f} adet × {rec.get('current_price', 0):.2f} TL = {current_value:,.0f} TL</p>
                        <p style="margin: 5px 0;"><strong>Ortalama Maliyet:</strong> {rec.get('avg_cost', 0):.2f} TL</p>
                        <p style="margin: 5px 0;"><strong>Kar/Zarar:</strong> <span style="color: {profit_color}; font-weight: bold;">{profit_loss:+,.0f} TL ({profit_loss_pct:+.1f}%)</span></p>
                        <p style="margin: 5px 0; padding-top: 10px; border-top: 1px solid #ddd;"><strong>💡 Analiz:</strong> {rec['action_reason']}</p>
                        {confidence_html}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Toplam işlem özeti
            total_buy = sum([r['recommended_value'] for r in buy_actions])
            total_sell = sum([r['recommended_value'] for r in sell_actions])
            
            # Export butonu ekle
            st.markdown("---")
            st.markdown("### 📄 Rapor Export")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export için verileri hazırla
                export_date = datetime.now()
                export_portfolio = {
                    'cash': portfolio.get('cash', 0),
                    'stocks': portfolio.get('stocks', {})
                }
                
                try:
                    from dashboard_portfolio_export import create_portfolio_recommendations_export
                    
                    # Session state key
                    export_key = f"export_word_{len(recommendations)}_{export_date.strftime('%Y%m%d')}"
                    
                    # Word dosyasını oluştur
                    if export_key not in st.session_state:
                        if st.button("📝 Word Raporu Oluştur", type="primary", use_container_width=True):
                            with st.spinner("📄 Word raporu oluşturuluyor..."):
                                doc = create_portfolio_recommendations_export(recommendations, export_portfolio, export_date)
                                
                                # Logs klasörünü oluştur
                                logs_dir = "logs"
                                os.makedirs(logs_dir, exist_ok=True)
                                
                                # Dosya adı
                                filename = f"portfoy_onerileri_{export_date.strftime('%Y%m%d_%H%M%S')}.docx"
                                filepath = os.path.join(logs_dir, filename)
                                
                                # Dosyayı kaydet
                                doc.save(filepath)
                                
                                # Dosyayı oku ve session state'e kaydet
                                with open(filepath, "rb") as f:
                                    file_data = f.read()
                                    st.session_state[export_key] = {
                                        'data': file_data,
                                        'filename': filename
                                    }
                                
                                st.success(f"✅ Word raporu oluşturuldu!")
                                st.rerun()
                    
                    # Download butonu
                    if export_key in st.session_state:
                        file_data = st.session_state[export_key]['data']
                        filename = st.session_state[export_key]['filename']
                        
                        st.download_button(
                            label="⬇️ Word Dosyasını İndir",
                            data=file_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_word_{export_date.strftime('%Y%m%d_%H%M%S')}",
                            type="primary",
                            use_container_width=True
                        )
                        
                        if st.button("🔄 Yeniden Oluştur", use_container_width=True):
                            del st.session_state[export_key]
                            st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Export hatası: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
            
            with col2:
                st.info("""
                **📋 Export Özellikleri:**
                - Tüm alım/satım önerileri
                - Neden AL/ARTIR/SAT dediğinin detayları
                - Portföy özeti ve işlem tutarları
                - Takip edilecek hisseler listesi
                """)
            
            st.markdown("---")
            st.markdown("### 📊 İşlem Özeti")
            
            # İşlem özeti - kompakt format
            current_total = sum([s['quantity'] * s['avg_cost'] for s in portfolio['stocks'].values()])
            net_cash = portfolio['cash'] + total_sell - total_buy
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); 
                        padding: 20px; 
                        border-radius: 10px; 
                        margin: 10px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="border-bottom: 2px solid #ddd;">
                        <td style="padding: 8px; font-weight: bold;">📊 Portföy Değeri</td>
                        <td style="padding: 8px; text-align: right; font-weight: bold; color: #28a745;">{:.2f} TL</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">💵 Başlangıç Nakit</td>
                        <td style="padding: 8px; text-align: right;">{:.2f} TL</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">💰 Toplam Satış</td>
                        <td style="padding: 8px; text-align: right; color: #dc3545;">+{:.2f} TL</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">💸 Toplam Alım</td>
                        <td style="padding: 8px; text-align: right; color: #6c757d;">-{:.2f} TL</td>
                    </tr>
                    <tr style="background: #28a745; color: white; border-top: 2px solid #28a745;">
                        <td style="padding: 10px; font-weight: bold;">💵 Kalan Nakit</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{:.2f} TL</td>
                    </tr>
                </table>
            </div>
            """.format(current_total, portfolio['cash'], total_sell, total_buy, net_cash), unsafe_allow_html=True)
        else:
            st.info("📝 Henüz hisse eklenmemiş veya analiz için yeterli veri yok.")
    else:
        st.info("💡 Lütfen nakit para veya portföy bilgilerinizi girin.")

