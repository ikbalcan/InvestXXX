import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Local imports
from src.fundamentals_loader import load_fundamentals


def _format_pct(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.2%}"
    except Exception:
        return "-"


def _format_num(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "-"


def _format_tr_lira_compact(value):
    if value is None:
        return "-"
    try:
        num = float(value)
    except Exception:
        return "-"
    units = [
        (1_000_000_000_000, "Trilyon TL"),
        (1_000_000_000, "Milyar TL"),
        (1_000_000, "Milyon TL"),
        (1_000, "Bin TL"),
    ]
    for threshold, suffix in units:
        if abs(num) >= threshold:
            return f"{num/threshold:.1f} {suffix}"
    return f"{num:,.0f} TL"


def _classify_ratio(value, breaks, labels, colors):
    """
    breaks: sorted list of upper bounds (e.g., [8, 15, 25, float('inf')])
    labels/colors: same length as breaks
    """
    if value is None:
        return ("-", "#adb5bd")
    try:
        v = float(value)
    except Exception:
        return ("-", "#adb5bd")
    for bound, label, color in zip(breaks, labels, colors):
        if v <= bound:
            return (label, color)
    return (labels[-1], colors[-1])


def _mini_range_bar(title, value, max_value, ranges):
    """Draw a small horizontal bar with colored ranges and a marker for value.

    ranges: list of tuples (end_value, color)
    """
    import plotly.graph_objects as go
    v = 0 if value is None else float(max(0, min(value, max_value)))
    fig = go.Figure()
    start = 0
    for end, color in ranges:
        width = max(0, min(end, max_value) - start)
        if width > 0:
            fig.add_trace(go.Bar(x=[width], y=[title], orientation='h', marker_color=color, showlegend=False, hoverinfo='skip'))
            start = min(end, max_value)
    # Marker
    fig.add_shape(type="line", x0=v, x1=v, y0=-0.5, y1=0.5, line=dict(color="#212529", width=3))
    fig.update_yaxes(visible=False)
    fig.update_xaxes(range=[0, max_value], visible=False)
    fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0), barmode='stack')
    return fig


def show_fundamental_analysis_tab(selected_symbol: str):
    st.markdown('<h2 class="section-title">📑 Temel Analiz</h2>', unsafe_allow_html=True)

    with st.spinner("Temel veriler yükleniyor..."):
        data = load_fundamentals(selected_symbol)

    info = data.get("info", {})
    metrics = data.get("key_metrics", {})

    # Company header
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Piyasa Değeri", _format_tr_lira_compact(metrics.get("market_cap")))
    with col2:
        st.metric("F/K", f"{metrics.get('trailing_pe'):.2f}" if metrics.get("trailing_pe") is not None else "-")
    with col3:
        st.metric("PD/DD", f"{metrics.get('price_to_book'):.2f}" if metrics.get("price_to_book") is not None else "-")
    with col4:
        st.metric("Temettü Verimi", _format_pct(metrics.get("dividend_yield")))

    # Explanations for FK and PD/DD
    with st.expander("ℹ️ Tanımlar ve İpuçları"):
        fk = metrics.get("trailing_pe")
        pdd = metrics.get("price_to_book")
        fk_label, fk_color = _classify_ratio(
            fk,
            breaks=[8, 15, 25, float("inf")],
            labels=["Ucuz", "Adil", "Pahalı", "Çok Pahalı"],
            colors=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        )
        pdd_label, pdd_color = _classify_ratio(
            pdd,
            breaks=[1, 2, 4, float("inf")],
            labels=["İskontolu", "Adil", "Primli", "Çok Primli"],
            colors=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        )

        col_a, col_b = st.columns(2)
        with col_a:
            # FK badge just above FK bar
            st.markdown(
                f"""
                <div style="background:{fk_color}; color:white; padding:4px 8px; border-radius:12px; font-weight:600; display:inline-block;">
                    F/K: {f"{fk:.2f}" if fk is not None else '-'} → {fk_label}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption("F/K konumu (0-40 aralığı)")
            fig_fk = _mini_range_bar(
                title="F/K",
                value=fk if fk is not None else 0,
                max_value=40,
                ranges=[(8, "#2ecc71"), (15, "#f1c40f"), (25, "#e67e22"), (40, "#e74c3c")],
            )
            st.plotly_chart(fig_fk, use_container_width=True)
        with col_b:
            # PD/DD badge just above PD/DD bar
            st.markdown(
                f"""
                <div style="background:{pdd_color}; color:white; padding:4px 8px; border-radius:12px; font-weight:600; display:inline-block;">
                    PD/DD: {f"{pdd:.2f}" if pdd is not None else '-'} → {pdd_label}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption("PD/DD konumu (0-6 aralığı)")
            fig_pdd = _mini_range_bar(
                title="PD/DD",
                value=pdd if pdd is not None else 0,
                max_value=6,
                ranges=[(1, "#2ecc71"), (2, "#f1c40f"), (4, "#e67e22"), (6, "#e74c3c")],
            )
            st.plotly_chart(fig_pdd, use_container_width=True)

        st.markdown(
            """
            - **F/K (Fiyat/Kazanç)**: Genel rehber (sektöre göre değişir):
              - < 8: "Ucuz"; 8-15: "Adil"; 15-25: "Pahalı"; > 25: "Çok Pahalı".
              - Düşük F/K her zaman fırsat değildir; geçici yüksek kârlar, döngüsellik veya riskleri kontrol edin.
            - **PD/DD (Piyasa Değeri/Defter Değeri)**: Genel rehber:
              - < 1: "İskontolu"; 1-2: "Adil"; 2-4: "Primli"; > 4: "Çok Primli".
              - Varlık ağır sektörlerde doğal olarak daha düşük olabilir; marka/teknoloji ağırlıklı işlerde yüksek PD/DD normaldir.
            - **Temettü Verimi**: Sürdürülebilirlik, nakit yaratımı ve büyüme planları ile birlikte değerlendirilmelidir (temettü tuzağına dikkat).
            - **ROE (Özsermaye Karlılığı)**: Net kâr / Özsermaye. Kaynakların kârlı kullanımını gösterir. Uzun süreli yüksek ROE (örn. > %15) kalite sinyali olabilir; kaldıraç etkisini de kontrol edin.
            - **ROA (Varlık Karlılığı)**: Net kâr / Toplam varlıklar. Varlıkların verimli kullanımını gösterir. Sermaye yoğun sektörlerde doğal olarak daha düşük olur.
            """
        )

    with st.expander("🧭 Temel Analiz Nasıl Yapılmalı? Kısa Rehber"):
        st.markdown(
            """
            - **Kârlılık Kalitesi**: ROE/ROA, brüt kâr marjı, operasyonel nakit akımı/Net kâr.
            - **Büyüme**: Hasılat ve net kâr CAGR, marj trendleri, yatırım harcamaları (CAPEX).
            - **Finansal Sağlamlık**: Borç/Özsermaye, Net borç/FAVÖK, kısa/uzun vadeli yükümlülük yapısı.
            - **Değerleme**: F/K, PD/DD, EV/FAVÖK; aynı sektör ve tarihsel ortalamalarla karşılaştırın.
            - **Sermaye Dağıtımı**: Temettü politikası, geri alımlar, yatırımların getirisi (ROIC).
            - **Riskler**: Döngüsellik, regülasyon, kur riski, müşteri/tedarikçi yoğunlaşması.
            """
        )

    st.markdown('<h3 class="subsection-title">🔎 Kârlılık ve Sağlamlık</h3>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("ROE", _format_pct(metrics.get("roe")))
        st.caption("Net kâr / Özsermaye: özkaynakların kârlılık verimi")
    with col2:
        st.metric("ROA", _format_pct(metrics.get("roa")))
        st.caption("Net kâr / Toplam varlıklar: varlıkların verimliliği")
    with col3:
        st.metric("Net Marj", _format_pct(metrics.get("net_margin")))
        st.caption("Net kâr / Hasılat: her 1 TL satıştan kalan oran")
    with col4:
        st.metric("Borç / Özsermaye", f"{metrics.get('debt_to_equity'):.2f}" if metrics.get("debt_to_equity") is not None else "-")
        st.caption("Toplam yükümlülükler / Özsermaye: kaldıraç seviyesi")

    st.write("---")

    # Time series section
    view = st.radio("Dönem", ["Yıllık", "Çeyreklik"], index=0, horizontal=True)
    if view == "Yıllık":
        income_df = data.get("financials_annual", pd.DataFrame())
        balance_df = data.get("balance_annual", pd.DataFrame())
        cash_df = data.get("cashflow_annual", pd.DataFrame())
    else:
        income_df = data.get("financials_quarterly", pd.DataFrame())
        balance_df = data.get("balance_quarterly", pd.DataFrame())
        cash_df = data.get("cashflow_quarterly", pd.DataFrame())

    # Normalize columns to be datetime index for plotting (transpose if needed)
    def _prep(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        t = df.copy()
        # yfinance provides periods as columns; transpose to rows for plotting
        t = t.T
        t.index = pd.to_datetime(t.index, errors='coerce')
        # drop invalid dates
        t = t[~t.index.isna()]
        t = t.sort_index()
        return t

    def _series_by_candidates(df: pd.DataFrame, candidates: list[str]):
        if df is None or df.empty:
            return None, None
        # build lowercase map for case-insensitive matching
        col_map = {str(c).strip().lower(): c for c in df.columns}
        for name in candidates:
            key = str(name).strip().lower()
            if key in col_map:
                s = df[col_map[key]]
                # ensure numeric
                s = pd.to_numeric(s, errors='coerce')
                return s, col_map[key]
        return None, None

    income_ts = _prep(income_df)
    balance_ts = _prep(balance_df)
    cash_ts = _prep(cash_df)

    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Gelir Kalemleri**")
        if not income_ts.empty:
            plot_df = pd.DataFrame({
                "Tarih": income_ts.index,
                "Hasılat": income_ts.get("Total Revenue"),
                "Net Kâr": income_ts.get("Net Income"),
            })
            fig = go.Figure()
            if "Hasılat" in plot_df:
                fig.add_trace(go.Bar(x=plot_df["Tarih"], y=plot_df["Hasılat"], name="Hasılat"))
            if "Net Kâr" in plot_df:
                fig.add_trace(go.Bar(x=plot_df["Tarih"], y=plot_df["Net Kâr"], name="Net Kâr"))
            fig.update_layout(barmode="group", height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Gelir tablosu verisi bulunamadı.")

    with cols[1]:
        st.markdown("**Bilanço Kalemleri**")
        if not balance_ts.empty:
            plot_df = pd.DataFrame({
                "Tarih": balance_ts.index,
                "Varlıklar": balance_ts.get("Total Assets"),
                "Özsermaye": balance_ts.get("Total Stockholder Equity"),
                "Yükümlülükler": balance_ts.get("Total Liab"),
            })
            fig = go.Figure()
            if "Varlıklar" in plot_df:
                fig.add_trace(go.Bar(x=plot_df["Tarih"], y=plot_df["Varlıklar"], name="Varlıklar"))
            if "Özsermaye" in plot_df:
                fig.add_trace(go.Bar(x=plot_df["Tarih"], y=plot_df["Özsermaye"], name="Özsermaye"))
            if "Yükümlülükler" in plot_df:
                fig.add_trace(go.Bar(x=plot_df["Tarih"], y=plot_df["Yükümlülükler"], name="Yükümlülükler"))
            fig.update_layout(barmode="group", height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Bilanço verisi bulunamadı.")

    st.markdown("**Nakit Akımları**")
    if not cash_ts.empty:
        op_series, op_col = _series_by_candidates(cash_ts, [
            "Total Cash From Operating Activities",
            "Operating Cash Flow",
            "Net Cash Provided by Operating Activities",
            "Net cash provided by operating activities",
            "Cash Provided by Operating Activities",
        ])
        inv_series, inv_col = _series_by_candidates(cash_ts, [
            "Total Cashflows From Investing Activities",
            "Investing Cash Flow",
            "Net Cash Used for Investing Activities",
            "Net cash used for investing activities",
            "Cash Used for Investing Activities",
            "Total Cash From Investing Activities",
        ])
        fin_series, fin_col = _series_by_candidates(cash_ts, [
            "Total Cash From Financing Activities",
            "Financing Cash Flow",
            "Net Cash Provided by Financing Activities",
            "Net cash provided by financing activities",
            "Cash Provided by Financing Activities",
        ])

        def _nncount(s):
            return int(s.notna().sum()) if s is not None else 0

        has_any = any(_nncount(s) > 0 for s in [op_series, inv_series, fin_series])
        if has_any:
            # Align by union of available series indices to prevent misalignment → all-NaN rows
            union_index = pd.Index([])
            for s in [op_series, inv_series, fin_series]:
                if s is not None and _nncount(s) > 0:
                    union_index = union_index.union(pd.to_datetime(s.index, errors='coerce'))
            union_index = union_index.sort_values()

            plot_df = pd.DataFrame(index=union_index)
            if op_series is not None and _nncount(op_series) > 0:
                plot_df["Operasyonel Nakit"] = pd.to_numeric(op_series, errors='coerce').astype(float).reindex(union_index)
            if inv_series is not None and _nncount(inv_series) > 0:
                plot_df["Yatırım Nakit"] = pd.to_numeric(inv_series, errors='coerce').astype(float).reindex(union_index)
            if fin_series is not None and _nncount(fin_series) > 0:
                plot_df["Finansman Nakit"] = pd.to_numeric(fin_series, errors='coerce').astype(float).reindex(union_index)

            # keep only rows having at least one non-null numeric value
            value_cols = [c for c in ["Operasyonel Nakit", "Yatırım Nakit", "Finansman Nakit"] if c in plot_df.columns]
            if value_cols:
                plot_df = plot_df[plot_df[value_cols].notna().any(axis=1)]
            plot_df = plot_df.reset_index().rename(columns={"index": "Tarih"})

            # Net nakit akımı (operasyonel + yatırım + finansman)
            plot_df["Net Nakit"] = (
                plot_df.get("Operasyonel Nakit", 0).fillna(0)
                + plot_df.get("Yatırım Nakit", 0).fillna(0)
                + plot_df.get("Finansman Nakit", 0).fillna(0)
            )

            # Daha okunur y-ekseni için ölçek: Bin/Milyon/Milyar/Trilyon
            def _unit_scale(max_abs):
                if max_abs >= 1_000_000_000_000:
                    return 1_000_000_000_000, "Trilyon TL"
                if max_abs >= 1_000_000_000:
                    return 1_000_000_000, "Milyar TL"
                if max_abs >= 1_000_000:
                    return 1_000_000, "Milyon TL"
                if max_abs >= 1_000:
                    return 1_000, "Bin TL"
                return 1, "TL"

            max_abs_val = float(plot_df[[c for c in ["Operasyonel Nakit", "Yatırım Nakit", "Finansman Nakit", "Net Nakit"] if c in plot_df.columns]].abs().max().max())
            scale_value, scale_label = _unit_scale(max_abs_val if max_abs_val == max_abs_val else 1)

            def _scaled(series):
                return series / scale_value if series is not None else None

            # Görünüm tipi seçici
            view_type = st.radio("Görünüm", ["Yığılmış", "Gruplu", "Waterfall (Son dönem)"], index=0, horizontal=True)

            if view_type in ("Yığılmış", "Gruplu"):
                fig = go.Figure()
                if "Operasyonel Nakit" in plot_df.columns:
                    fig.add_trace(go.Bar(
                        x=plot_df["Tarih"], y=_scaled(plot_df["Operasyonel Nakit"]), name="Operasyonel",
                        marker_color="#1f77b4", hovertemplate="Operasyonel: %{customdata:,} TL<extra></extra>",
                        customdata=plot_df["Operasyonel Nakit"]
                    ))
                if "Yatırım Nakit" in plot_df.columns:
                    fig.add_trace(go.Bar(
                        x=plot_df["Tarih"], y=_scaled(plot_df["Yatırım Nakit"]), name="Yatırım",
                        marker_color="#7fc8ff", hovertemplate="Yatırım: %{customdata:,} TL<extra></extra>",
                        customdata=plot_df["Yatırım Nakit"]
                    ))
                if "Finansman Nakit" in plot_df.columns:
                    fig.add_trace(go.Bar(
                        x=plot_df["Tarih"], y=_scaled(plot_df["Finansman Nakit"]), name="Finansman",
                        marker_color="#e74c3c", hovertemplate="Finansman: %{customdata:,} TL<extra></extra>",
                        customdata=plot_df["Finansman Nakit"]
                    ))

                # Net çizgisi (her iki görünümde de gösterelim; okunurluk için)
                fig.add_trace(go.Scatter(
                    x=plot_df["Tarih"], y=_scaled(plot_df["Net Nakit"]), name="Net Nakit",
                    mode="lines+markers", line=dict(color="#2ecc71", width=2),
                    hovertemplate="Net: %{customdata:,} TL<extra></extra>",
                    customdata=plot_df["Net Nakit"]
                ))

                fig.add_hline(y=0, line_color="#adb5bd", line_width=1)
                fig.update_layout(
                    barmode="relative" if view_type == "Yığılmış" else "group",
                    height=360,
                    yaxis=dict(tickformat=",.1f", title=scale_label),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig.update_xaxes(type='date')
                st.plotly_chart(fig, use_container_width=True)

            else:
                # Waterfall for the most recent period
                last_row = plot_df.sort_values("Tarih").iloc[-1]
                wf = go.Figure(go.Waterfall(
                    name="Son Dönem",
                    orientation="v",
                    measure=["relative", "relative", "relative", "total"],
                    x=["Operasyonel", "Yatırım", "Finansman", "Net"],
                    textposition="outside",
                    y=[
                        last_row.get("Operasyonel Nakit", 0.0),
                        last_row.get("Yatırım Nakit", 0.0),
                        last_row.get("Finansman Nakit", 0.0),
                        last_row.get("Net Nakit", 0.0),
                    ],
                ))
                wf.update_layout(height=360, yaxis=dict(title="TL", tickformat=",~s"))
                st.plotly_chart(wf, use_container_width=True)

            st.caption("Yorum: Operasyonel nakit + (genelde negatif) yatırım nakdi + finansman nakdi = Net nakit. Net pozitif → kasa artar; negatif → nakit tükenir.")
        else:
            st.info("Bu sembol için Yahoo Finance nakit akım kalemleri sağlanmıyor.")
    else:
        st.info("Nakit akım verisi bulunamadı.")

    # Learning mode: practical guide with live numbers
    def _last_from_df(df: pd.DataFrame, row: str):
        if df is None or df.empty or row not in df.index:
            return None
        try:
            s = df.loc[row]
            return float(s.iloc[0]) if len(s) > 0 else None
        except Exception:
            return None

    with st.expander("🎓 Öğrenme Modu: Bilanço, Gelir, Nakit Akımı"):
        # choose the same view as selected above
        inc_df = data.get("financials_annual", pd.DataFrame()) if view == "Yıllık" else data.get("financials_quarterly", pd.DataFrame())
        bal_df = data.get("balance_annual", pd.DataFrame()) if view == "Yıllık" else data.get("balance_quarterly", pd.DataFrame())
        cfs_df = data.get("cashflow_annual", pd.DataFrame()) if view == "Yıllık" else data.get("cashflow_quarterly", pd.DataFrame())

        total_assets = _last_from_df(bal_df, "Total Assets")
        total_equity = _last_from_df(bal_df, "Total Stockholder Equity")
        total_liab = _last_from_df(bal_df, "Total Liab")
        current_assets = _last_from_df(bal_df, "Total Current Assets")
        current_liab = _last_from_df(bal_df, "Total Current Liabilities")

        revenue = _last_from_df(inc_df, "Total Revenue")
        net_income = _last_from_df(inc_df, "Net Income")

        cfo = _last_from_df(cfs_df, "Total Cash From Operating Activities")
        cfi = _last_from_df(cfs_df, "Total Cashflows From Investing Activities")
        cff = _last_from_df(cfs_df, "Total Cash From Financing Activities")

        # Derived ratios
        current_ratio = (current_assets / current_liab) if current_assets and current_liab else None
        equity_ratio = (total_equity / total_assets) if total_equity and total_assets else None
        cfo_to_net = (cfo / net_income) if cfo and net_income else None

        # Simple color helper
        def _colorize(val, good_thresh, warn_thresh=None, reverse=False):
            if val is None:
                return ("-", "#6c757d")
            v = float(val)
            if reverse:
                # lower is better
                if v <= good_thresh:
                    return (f"{v:.2f}", "#2ecc71")
                if warn_thresh is not None and v <= warn_thresh:
                    return (f"{v:.2f}", "#f1c40f")
                return (f"{v:.2f}", "#e74c3c")
            else:
                # higher is better
                if v >= good_thresh:
                    return (f"{v:.2f}", "#2ecc71")
                if warn_thresh is not None and v >= warn_thresh:
                    return (f"{v:.2f}", "#f1c40f")
                return (f"{v:.2f}", "#e74c3c")

        st.markdown("**1) Bilanço (Finansal Sağlamlık)**")
        colA, colB, colC, colD = st.columns(4)
        with colA:
            st.metric("Varlıklar", _format_tr_lira_compact(total_assets))
        with colB:
            st.metric("Özsermaye", _format_tr_lira_compact(total_equity))
        with colC:
            st.metric("Yükümlülükler", _format_tr_lira_compact(total_liab))
        with colD:
            val, color = _colorize(current_ratio, good_thresh=1.5, warn_thresh=1.0)
            st.markdown(f"<div class='info-card' style='border-left-color:{color};'><strong>Current Ratio</strong>: {val if val!='-' else '-'} (Dönen Varlıklar / KV Yükümlülükler)</div>", unsafe_allow_html=True)

        st.caption("Rehber: Current ratio ≥ 1.5 genellikle güvenli; aşırı yüksek değer stok/debitor riski barındırabilir.")

        st.markdown("**2) Gelir Tablosu (Kârlılık & Büyüme)**")
        colE, colF, colG = st.columns(3)
        with colE:
            st.metric("Hasılat", _format_tr_lira_compact(revenue))
        with colF:
            st.metric("Net Kâr", _format_tr_lira_compact(net_income))
        with colG:
            roe_val = metrics.get("roe")
            roe_fmt, color = _colorize(roe_val if roe_val is not None else None, good_thresh=0.15, warn_thresh=0.08)
            st.markdown(f"<div class='info-card' style='border-left-color:{color};'><strong>ROE</strong>: {roe_fmt if roe_fmt!='-' else '-'} (Net Kâr/Özsermaye)</div>", unsafe_allow_html=True)

        st.caption("Rehber: Sürdürülebilir ROE > %15 kalite sinyali; kaldıraç etkisini kontrol edin.")

        st.markdown("**3) Nakit Akımı (Nakdin Kalitesi)**")
        colH, colI, colJ, colK = st.columns(4)
        with colH:
            st.metric("Operasyonel Nakit", _format_tr_lira_compact(cfo))
        with colI:
            st.metric("Yatırım Nakit", _format_tr_lira_compact(cfi))
        with colJ:
            st.metric("Finansman Nakit", _format_tr_lira_compact(cff))
        with colK:
            cfo_net_fmt, color = _colorize(cfo_to_net if cfo_to_net is not None else None, good_thresh=1.0, warn_thresh=0.7)
            st.markdown(f"<div class='info-card' style='border-left-color:{color};'><strong>CFO/Net Kâr</strong>: {cfo_net_fmt if cfo_net_fmt!='-' else '-'} (Nakit kalitesini gösterir)</div>", unsafe_allow_html=True)

        st.caption("Rehber: Oran ≥ 1 sağlıklı; kalıcı olarak < 1 ise kâr kalitesi sorgulanmalı.")

        st.markdown("**Özet Kontrol Listesi**")
        st.write("- Bilanço sağlam mı? (Current ratio, Borç/Özsermaye, Özsermaye/Varlıklar)")
        st.write("- Kârlılık kalıcı mı? (ROE/ROA, marj trendi)")
        st.write("- Nakit akımı kârı destekliyor mu? (CFO ≥ Net kâr, yatırım finansmanı)")


