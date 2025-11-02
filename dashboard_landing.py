"""
Landing Page - Uygulama Tanıtım ve Bilgilendirme Sekmesi
"""

import streamlit as st
from datetime import datetime


def show_landing_page():
    """Güzel bir landing page gösterir"""
    
    # Hero Section - Gradient Arkaplanlı
    st.markdown("""
    <style>
        .hero-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 60px 40px;
            border-radius: 20px;
            margin-bottom: 40px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            color: white;
            margin-bottom: 20px;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        }
        
        .hero-subtitle {
            font-size: 1.5rem;
            color: rgba(255,255,255,0.95);
            margin-bottom: 30px;
            font-weight: 300;
        }
        
        .feature-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin: 20px 0;
            transition: transform 0.3s ease;
            border-left: 5px solid #28a745;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .feature-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }
        
        .feature-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #495057;
            margin-bottom: 10px;
        }
        
        .feature-description {
            font-size: 1.1rem;
            color: #6c757d;
            line-height: 1.6;
        }
        
        .research-badge {
            display: inline-block;
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
            color: white;
            padding: 10px 25px;
            border-radius: 25px;
            font-weight: 700;
            font-size: 1rem;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(23,162,184,0.3);
        }
        
        .stats-container {
            display: flex;
            justify-content: space-around;
            margin: 40px 0;
            flex-wrap: wrap;
        }
        
        .stat-box {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            min-width: 200px;
            margin: 10px;
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 800;
            color: #28a745;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 1.1rem;
            color: #6c757d;
            font-weight: 600;
        }
        
        .cta-section {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            margin: 40px 0;
            box-shadow: 0 10px 40px rgba(40,167,69,0.3);
        }
        
        .cta-title {
            font-size: 2rem;
            font-weight: 700;
            color: white;
            margin-bottom: 15px;
        }
        
        .cta-text {
            font-size: 1.2rem;
            color: rgba(255,255,255,0.95);
            margin-bottom: 25px;
        }
        
        .value-proposition {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 40px;
            border-radius: 15px;
            margin: 30px 0;
            border-left: 8px solid #667eea;
        }
        
        .value-title {
            font-size: 2rem;
            font-weight: 700;
            color: #495057;
            margin-bottom: 20px;
        }
        
        .value-text {
            font-size: 1.15rem;
            color: #495057;
            line-height: 1.8;
            margin: 15px 0;
        }
        
        .benefit-list {
            list-style: none;
            padding: 0;
        }
        
        .benefit-item {
            padding: 15px 0;
            font-size: 1.1rem;
            color: #495057;
            border-bottom: 1px solid #dee2e6;
        }
        
        .benefit-item:last-child {
            border-bottom: none;
        }
        
        .benefit-icon {
            margin-right: 10px;
            font-size: 1.3rem;
        }
        
        @media (max-width: 768px) {
            .hero-title {
                font-size: 2.5rem;
            }
            
            .hero-subtitle {
                font-size: 1.2rem;
            }
            
            .feature-card {
                padding: 20px;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">📈 Hisse Senedi Analiz ve Tahmin Sistemi</div>
        <div class="hero-subtitle">Makine Öğrenmesi ile Güçlendirilmiş Akıllı Yatırım Analiz Platformu</div>
        <div class="research-badge">🔬 AR-GE Projesi</div>
    </div>
    """, unsafe_allow_html=True)
    
    # SPK Uyarısı - Önemli ve Belirgin - Streamlit standart component kullanarak
    st.error("""
    **⚠️ ÖNEMLİ SPK UYARISI**
    
    **Bu platform bir araştırma ve geliştirme (AR-GE) projesidir.**
    
    Bu platform tarafından sunulan tüm analizler, tahminler ve öneriler **sadece eğitim ve bilgilendirme amaçlıdır**.
    
    • Hiçbir şekilde yatırım tavsiyesi niteliği taşımamaktadır.
    • Yatırım kararlarınızı sadece bu platforma dayanarak almamanız gerekmektedir.
    • Sermaye Piyasası Kurulu (SPK) tarafından yetkilendirilmiş bir yatırım danışmanlığı hizmeti değildir.
    • Her yatırım kararında mutlaka profesyonel finansal danışmanlardan görüş alınmalıdır.
    • Yatırımlarınızda doğabilecek tüm riskler size aittir.
    • Bu platform, hiçbir şekilde yatırım zararlarından sorumlu tutulamaz.
    
    **⚠️ ÖNEMLİ: Yatırım yapmadan önce mutlaka kendi araştırmanızı yapın ve riskleri değerlendirin.**
    """)
    
    # Ek bir warning kutusu ile vurgulama
    st.warning("""
    **UYARI:** Bu platform eğitim ve bilgilendirme amaçlıdır. Yatırım kararlarınızda mutlaka profesyonel danışmanlık alın ve kendi araştırmanızı yapın.
    """)
    
    # Değer Önerisi - Platform'un Amacı
    st.markdown("""
    <div class="value-proposition">
        <div class="value-title">🎯 Misyonumuz: Bilinçli Yatırımcı Yetiştirmek</div>
        <div class="value-text">
            <strong>Bu platform, yatırımcıların analiz yeteneklerini güçlendirmeyi ve bilinçli yatırım kararları almalarını hedefleyen bir AR-GE projesidir.</strong>
        </div>
        <div class="value-text">
            Amacımız, kullanıcılarımıza sadece hazır öneriler sunmak değil, <strong>analiz kaslarını geliştirmek</strong> ve 
            <strong>kendi başlarına nitelikli analiz yapabilme yetkinliği kazandırmaktır</strong>. Bu nedenle platform içerisinde hem 
            gelişmiş analiz araçları hem de eğitici içerikler bulunmaktadır.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Özellikler Grid
    st.markdown("### 🌟 Platform Özellikleri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Teknik Analiz Araçları</div>
            <div class="feature-description">
                Gelişmiş teknik analiz göstergeleri, grafik analizi ve fiyat hareketlerini inceleme araçları ile 
                hisselerin teknik durumunu detaylı şekilde analiz edin.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📑</div>
            <div class="feature-title">Temel Analiz Modülü</div>
            <div class="feature-description">
                Finansal tablolar, oranlar, karlılık analizleri ve şirket temel değerlerini inceleyerek 
                şirketlerin sağlıklı bir şekilde değerlendirilmesini öğrenin.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">Makine Öğrenmesi Tahminleri</div>
            <div class="feature-description">
                AR-GE kapsamında geliştirilmiş makine öğrenmesi modelleri ile fiyat yönü tahminleri ve 
                olası senaryoları keşfedin. Her tahmin bir öğrenme fırsatıdır.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📚</div>
            <div class="feature-title">Eğitim ve Rehberlik</div>
            <div class="feature-description">
                Teknik ve temel analiz konularında kapsamlı rehberler, terim sözlüğü ve pratik örneklerle 
                analiz bilginizi artırın. Her özellik nasıl kullanılacağı ile birlikte sunulur.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">Hisse Avcısı</div>
            <div class="feature-description">
                Çoklu hisse analizi ve karşılaştırma araçları ile piyasadaki fırsatları keşfedin. 
                Farklı kriterlere göre hisseleri filtreleyin ve analiz edin.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💼</div>
            <div class="feature-title">Portföy Yönetimi</div>
            <div class="feature-description">
                Portföy analizi, risk yönetimi ve dağılım önerileri ile portföy yönetimi yeteneklerinizi 
                geliştirin. Paper trading ile pratik yapın.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Faydalar Bölümü
    st.markdown("### 💪 Bu Platform Size Nasıl Yardımcı Olur?")
    
    st.markdown("""
    <div class="value-proposition">
        <ul class="benefit-list">
            <li class="benefit-item">
                <span class="benefit-icon">💡</span>
                <strong>Analiz Yeteneklerinizi Geliştirin:</strong> Her araç ve özellik, kullanım amacı ve nasıl yorumlanacağı ile birlikte sunulur. 
                Böylece sadece sonuçları görmek yerine, analiz mantığını öğrenirsiniz.
            </li>
            <li class="benefit-item">
                <span class="benefit-icon">📖</span>
                <strong>Eğitim İçeriği ile Güçlenin:</strong> Platform içinde bulunan rehberler ve açıklamalar ile teknik analiz, 
                temel analiz ve yatırım kavramlarını derinlemesine öğrenin.
            </li>
            <li class="benefit-item">
                <span class="benefit-icon">🔬</span>
                <strong>Deneyerek Öğrenin:</strong> Paper trading özelliği ile gerçek para riski olmadan yatırım stratejilerinizi test edin 
                ve deneyim kazanın.
            </li>
            <li class="benefit-item">
                <span class="benefit-icon">📊</span>
                <strong>Veri Odaklı Kararlar Alın:</strong> Duygusal değil, veri ve analiz temelli yatırım kararları almayı öğrenin. 
                Platform size gerekli tüm veriyi ve analiz araçlarını sağlar.
            </li>
            <li class="benefit-item">
                <span class="benefit-icon">🎓</span>
                <strong>Yetkinlik Kazanın:</strong> Sadece önerileri takip etmek yerine, kendi analizinizi yapabilme yeteneği kazanın. 
                Bu, uzun vadede en değerli kazanımdır.
            </li>
            <li class="benefit-item">
                <span class="benefit-icon">🛡️</span>
                <strong>Risk Bilinci Geliştirin:</strong> Platform üzerindeki uyarılar ve eğitim içerikleri ile risk farkındalığınızı artırın 
                ve daha bilinçli yatırım yapın.
            </li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # İstatistikler (Opsiyonel - Demo amaçlı)
    st.markdown("""
    <div class="stats-container">
        <div class="stat-box">
            <div class="stat-number">50+</div>
            <div class="stat-label">Analiz Göstergesi</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">100+</div>
            <div class="stat-label">BIST Hissesi</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">∞</div>
            <div class="stat-label">Öğrenme Fırsatı</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Call to Action
    st.markdown("""
    <div class="cta-section">
        <div class="cta-title">🚀 Hemen Başlayın!</div>
        <div class="cta-text">
            Analiz yeteneklerinizi geliştirmek ve bilinçli yatırım kararları almak için yanınızdayız.<br>
            Üst menüden sekmeleri keşfedin ve analiz yolculuğunuza başlayın.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Son Uyarı
    st.markdown("---")
    st.info("""
    **📌 Hatırlatma:** Bu platform bir AR-GE projesidir ve eğitim amaçlıdır. Yatırım kararlarınızda mutlaka profesyonel 
    danışmanlık alın ve kendi araştırmanızı yapın. Platform tarafından sunulan tüm bilgiler sadece eğitim ve bilgilendirme amaçlıdır.
    """)
    
    # Footer
    st.markdown("---")
    current_year = datetime.now().year
    st.markdown(f"""
    <div style="text-align: center; color: #6c757d; padding: 20px;">
        <p style="font-size: 0.9rem;">
            📈 Hisse Senedi Analiz ve Tahmin Sistemi<br>
            AR-GE Projesi • Eğitim ve Bilgilendirme Amaçlı<br>
            © {current_year} - Tüm hakları saklıdır
        </p>
    </div>
    """, unsafe_allow_html=True)

