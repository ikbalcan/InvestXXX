import streamlit as st


def show_guide_tab():
    """Rehber (Yatırım Rehberi) sekmesi: konu arama, başlıklar, öğrenme patikası."""

    st.markdown('<h2 class="section-title">📘 Yatırım Rehberi</h2>', unsafe_allow_html=True)
    st.info(
        "Bu bölüm, borsada hisse senetlerine yatırım yapanlar için hızlı hap bilgiler ve detaylı öğrenme içerikleri sunar."
    )

    # Psikoloji vurgusu (üstte, en kritik blok)
    st.markdown('<h3 class="subsection-title">🧠 Yatırım Psikolojisi – En Kritik İlkeler</h3>', unsafe_allow_html=True)
    st.write(
        """
        - Planı yaz ve uygula: Kural setini (giriş/çıkış/risk) işlemlerden önce netleştir.
        - Disiplin: Stop-loss'a sadakat; "umudu" değil olasılıkları yönet.
        - Duygu kontrolü: FOMO ve intikam işlemlerinden kaçın, günlük limit koy.
        - Süreç odaklılık: Tek işlem sonucu değil, 50+ işlem serisinin istatistiği önemlidir.
        - Günlük/haftalık değerlendirme: Hata günlüğü tut, hatadan öğren.
        """
    )

    # En önemli Hap Bilgiler (üstte)
    st.markdown('<h3 class="subsection-title">⚡ Hap Bilgiler</h3>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Teknik Analiz – En Önemli 5 İlke**")
        st.write(
            """
            - Trend yönüne işlem yap; büyük zaman dilimi ile hizalan.
            - Destek/direnç kırılımında retest ve hacim teyidi ara.
            - Stop-loss'u teknik seviyeye (swing/ATR) koy; duygusal değil kural bazlı.
            - Risk/Ödül oranı ≥ 1:2; hedefi baştan belirle.
            - Aynı anda çok gösterge kullanıp kararı sulandırma; sade tut.
            """
        )
    with col_b:
        st.markdown("**Temel Analiz – En Önemli 5 İlke**")
        st.write(
            """
            - Kârlılık kalitesi: ROE sektör üstü ve istikrarlı olsun.
            - Borçluluk: Net Borç/FAVÖK makul ve düşen trendde olsun.
            - Büyüme: Satış ve FAVÖK 3Y CAGR pozitif ve sürdürülebilir olsun.
            - Değerleme: Sektör emsallerine göre iskontoyu teyit et (F/K, FD/FAVÖK, PD/DD, PEG).
            - Nakit akımı: Operasyonel nakit akımı kârı desteklesin; stok/alacak döngüsü sağlıklı olsun.
            """
        )

    # Konu kataloğu: kolay genişleyebilir yapı
    # Her konu: id, kategori, başlık, özet, detay, kaynaklar
    topics = [
        {
            "id": "psy_disciplines",
            "category": "Psikoloji",
            "title": "Psikoloji: Disiplin ve Davranışsal Tuzaklar",
            "summary": (
                "Planlı hareket et, duygularını yönet (FOMO/overtrading/intikam), süreç istatistiğine odaklan."
            ),
            "details": (
                "- Kural seti: Giriş/çıkış/pozisyon boyutu yazılı olsun.\n"
                "- Bilişsel yanlılıklar: Kayıp korkusu, onay yanlılığı; kayıtla görünür kıl.\n"
                "- Ritüel: Seans öncesi/sonrası kontrol listesi, hata günlüğü."
            ),
            "resources": [],
        },
        {
            "id": "tech_trend",
            "category": "Teknik Analiz",
            "title": "Trend Analizi ve Çoklu Zaman Dilimi",
            "summary": (
                "Ana trendi 1D/1W EMA(50/200) ile belirle; giriş/çıkışı 1H/4H hizala; kırılımlarda hacim teyidi."
            ),
            "details": (
                "- EMA50>EMA200 (boğa), EMA50<EMA200 (ayı).\n"
                "- En az 3 temaslı trend çizgileri güven verir.\n"
                "- Kırılım + retest + hacim artışı sürdürülebilirliği destekler."
            ),
            "resources": [],
        },
        {
            "id": "tech_support_resistance",
            "category": "Teknik Analiz",
            "title": "Destek/Direnç ve Kırılım Taktikleri",
            "summary": (
                "Yoğun işlem bölgeleri güçlü seviyelerdir; kırılım + retest + hacim teyidi, sahte kırılım riskini azaltır."
            ),
            "details": (
                "- Yatay seviyeler ve trend çizgilerini birlikte kullan.\n"
                "- Stop, son swing'in biraz ötesinde olmalı.\n"
                "- Zaman dilimi uyumu hatalı sinyal riskini azaltır."
            ),
            "resources": [],
        },
        {
            "id": "tech_momentum",
            "category": "Teknik Analiz",
            "title": "Momentum: RSI, MACD, Stokastik",
            "summary": (
                "RSI 40-60 konsolidasyon; 60 üstü boğa önyargı; MACD sıfır üstü güç; uyumsuzluklar dönüş sinyali verebilir."
            ),
            "details": (
                "- Boğa rejiminde RSI 50-60 dönüşleri takip edilebilir.\n"
                "- MACD histogram zayıflama, momentum kaybına işaret edebilir."
            ),
            "resources": [],
        },
        {
            "id": "tech_volume",
            "category": "Teknik Analiz",
            "title": "Hacim ve Likidite İpuçları",
            "summary": (
                "Kırılımlarda artan hacim hareketin sürdürülebilirliğini destekler; düşüşte azalan hacim satış baskısının zayıflaması olabilir."
            ),
            "details": (
                "- Hacim profili (VAP) ile yoğun bölgeleri izle.\n"
                "- Likit olmayan hisselerde teknik sinyaller daha geç çalışabilir."
            ),
            "resources": [],
        },
        {
            "id": "tech_risk",
            "category": "Risk Yönetimi",
            "title": "Risk Yönetimi ve Pozisyon Boyutu",
            "summary": (
                "İşlem başına %1-2 risk, teknik seviyeye dayalı stop-loss, en az 1:2 risk/ödül."
            ),
            "details": (
                "- ATR tabanlı stop/pozisyon boyutu volatiliteye uyum sağlar.\n"
                "- Seri kayıplarda risk azalt, sermayeyi koru."
            ),
            "resources": [],
        },
        
        {
            "id": "fund_profitability",
            "category": "Temel Analiz",
            "title": "Kârlılık: Net Marj, ROE, ROA",
            "summary": (
                "ROE sektör ortalamasının üzerinde ve artan trendde olmalı; marj sürekliliği kalite göstergesidir."
            ),
            "details": (
                "- Döngüsel sektörlerde 3-5 yıllık ortalamalarla kıyas yap.\n"
                "- Brüt → FAVÖK → Net kâr marjı zincirini birlikte incele."
            ),
            "resources": [],
        },
        {
            "id": "fund_leverage",
            "category": "Temel Analiz",
            "title": "Borçluluk: Net Borç/FAVÖK, Faiz Karşılama",
            "summary": (
                "Net Borç/FAVÖK < 3 genelde sağlıklı (sektöre göre değişir); faiz karşılama oranı yükselen trendde olmalı."
            ),
            "details": (
                "- Kısa vadeli borçların çevrilebilirliği ve likidite oranlarını izle."
            ),
            "resources": [],
        },
        {
            "id": "fund_growth",
            "category": "Temel Analiz",
            "title": "Büyüme: Satış ve FAVÖK (3Y CAGR)",
            "summary": (
                "Satış ve FAVÖK büyümesinin kârlılık ile birlikte gelmesi kaliteyi artırır; 3Y CAGR ile takip et."
            ),
            "details": (
                "- Organik/inorganik ayrımı ve sürdürülebilirlik kritik."
            ),
            "resources": [],
        },
        {
            "id": "fund_valuation",
            "category": "Temel Analiz",
            "title": "Değerleme: F/K, FD/FAVÖK, PD/DD, PEG",
            "summary": (
                "Sektör emsalleriyle kıyas; büyüme ayarlı F/K (PEG) ≈ 1 iskontoya işaret edebilir; rejime göre çarpanlar değişir."
            ),
            "details": (
                "- Döngüsel dönemlerde tek başına çarpanlara yaslanma; çoklu metrik kullan."
            ),
            "resources": [],
        },
        {
            "id": "fund_cashflow",
            "category": "Temel Analiz",
            "title": "Nakit Akımı Kalitesi",
            "summary": (
                "Operasyonel nakit akımının kârı desteklemesi, stok/alacak döngüsünün sağlıklı olması kalite göstergesidir."
            ),
            "details": (
                "- Yüksek capex dönemlerinde serbest nakit akımı düşebilir; bağlamı göz önünde tut."
            ),
            "resources": [],
        },
    ]

    # Kategorilere göre gösterim
    categories = ["Psikoloji", "Teknik Analiz", "Temel Analiz", "Risk Yönetimi"]
    for category in categories:
        cat_topics = [t for t in topics if t["category"] == category]
        if not cat_topics:
            continue

        st.markdown(f'<h3 class="subsection-title">{("📈" if category=="Teknik Analiz" else "📑" if category=="Temel Analiz" else "⚠️")} {category}</h3>', unsafe_allow_html=True)

        for t in cat_topics:
            with st.expander(t["title"], expanded=False):
                st.write(t["summary"])
                if t.get("details"):
                    st.write(t["details"])

    st.caption("Not: Konu kataloğu esnektir; yeni göstergeler ve temel başlıklar kolayca eklenebilir.")


