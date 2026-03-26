"""
Nipharma Tech Stock Intelligence Unit  v3
==========================================
Streamlit app — run with:
  cd scrapers && streamlit run app.py

Pages:
  1. 🏠 Intelligence Dashboard  — ML predictions, critical alerts, watchlist cards
  2. ⚠️  Early Warning           — MHRA alerts, FDA warnings, CPE news, MIMS
  3. 🔗 Supply Chain Risk        — API cascade clusters, manufacturer intelligence
  4. 🔍 Drug Lookup              — per-drug price + concession history + supply chain
  5. 📈 Concession Trends        — monthly shortage count with date filters
  6. 📡 Market Signals           — Brent crude, FX rates, BoE rate
  7. 🤖 Model Info               — v6 performance metrics + feature importance
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nipharma Tech Stock Intelligence Unit",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pathlib
_HERE     = pathlib.Path(__file__).parent
DATA_DIR  = str(_HERE / "data")
MODEL_DIR = str(_HERE / "data" / "model")

# ── Colour constants ────────────────────────────────────────────────────────────
TIER_COLOUR = {
    "CONFIRMED": "#e63950",
    "HIGH":      "#f4845f",
    "MEDIUM":    "#f9c74f",
    "LOW":       "#90be6d",
    "WATCH":     "#43aa8b",
}

ACTION_COLOUR = {
    "🔴 BUY NOW":       "#e63950",
    "🟠 BUY MORE":      "#f4845f",
    "🟠 BUY AHEAD":     "#f8961e",
    "🟡 MANAGE STOCK":  "#f9c74f",
    "🟡 WATCH":         "#90be6d",
    "⚪ NORMAL":         "#90a0b0",
    "✅ NO ACTION":      "#43aa8b",
}

def risk_tier(p):
    if p >= 0.90: return "CONFIRMED"
    if p >= 0.70: return "HIGH"
    if p >= 0.50: return "MEDIUM"
    if p >= 0.30: return "LOW"
    return "WATCH"

def tier_badge(tier):
    colours = {
        "CONFIRMED": "🔴", "HIGH": "🟠",
        "MEDIUM": "🟡", "LOW": "🟢", "WATCH": "⚪",
    }
    return f"{colours.get(tier, '')} {tier}"

def buy_action(prob, on_concession):
    on_conc = int(on_concession) if pd.notna(on_concession) else 0
    if prob >= 0.90 and not on_conc:
        return "🔴 BUY NOW"
    if prob >= 0.90 and on_conc:
        return "🟠 BUY MORE"
    if prob >= 0.70 and not on_conc:
        return "🟠 BUY AHEAD"
    if prob >= 0.70 and on_conc:
        return "🟡 MANAGE STOCK"
    if prob >= 0.50:
        return "🟡 WATCH"
    if prob >= 0.30:
        return "⚪ NORMAL"
    return "✅ NO ACTION"


# ════════════════════════════════════════════════════════════════════════════════
# DATA LOADERS (cached)
# ════════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_predictions():
    path = f"{MODEL_DIR}/panel_predictions.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["risk_tier"] = df["shortage_probability"].apply(risk_tier)
    df["buy_action"] = df.apply(
        lambda r: buy_action(r["shortage_probability"], r.get("on_concession", 0)), axis=1
    )
    df = df.sort_values("shortage_probability", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df

@st.cache_data
def load_feature_importance():
    path = f"{MODEL_DIR}/panel_feature_importance.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_concession_history():
    path = f"{DATA_DIR}/concessions/cpe_archive_full.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    return df

@st.cache_data
def load_panel():
    path = f"{DATA_DIR}/features/panel_feature_store.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_cv_metrics():
    path = f"{MODEL_DIR}/panel_cv_metrics.txt"
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()

@st.cache_data
def load_brent():
    path = f"{DATA_DIR}/market_signals/brent_crude.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date")

@st.cache_data
def load_fx():
    path = f"{DATA_DIR}/market_signals/fx_rates_stress.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date")

@st.cache_data
def load_boe():
    path = f"{DATA_DIR}/market_signals/boe_inflation.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col)
        df = df.rename(columns={date_col: "date"})
    return df

@st.cache_data
def load_pca_demand():
    path = f"{DATA_DIR}/openprescribing/pca_demand_features.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_mhra_alerts():
    path = f"{DATA_DIR}/early_warning/govuk_mhra_alerts.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["published"] = pd.to_datetime(df["published"], errors="coerce")
    return df.sort_values("published", ascending=False)

@st.cache_data
def load_fda_warnings():
    path = f"{DATA_DIR}/early_warning/fda_warning_letters.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_cpe_news():
    path = f"{DATA_DIR}/early_warning/cpe_shortage_news.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_mims_shortages():
    path = f"{DATA_DIR}/early_warning/mims_shortages.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_api_cascade():
    path = f"{DATA_DIR}/early_warning/api_cascade_map.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_api_manufacturers():
    path = f"{DATA_DIR}/early_warning/api_manufacturer_db.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_early_warning_features():
    path = f"{DATA_DIR}/early_warning/early_warning_features.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def load_openfda_shortages():
    path = f"{DATA_DIR}/market_signals/openfda_shortages.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


# ════════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* Drug cards */
.drug-card {
    background: #1a2035;
    border-radius: 10px;
    padding: 14px 16px 12px;
    margin-bottom: 4px;
    min-height: 180px;
    box-sizing: border-box;
}
.dc-rank   { color:#6b7a99;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:4px }
.dc-name   { color:#e8ecf4;font-size:12px;font-weight:700;line-height:1.35;min-height:34px;margin-bottom:8px }
.dc-prob   { font-size:28px;font-weight:900;font-family:"Arial Black",Arial;line-height:1;margin-bottom:7px }
.dc-badge  { display:inline-block;padding:3px 8px;border-radius:5px;font-size:9px;font-weight:700;margin-bottom:8px }
.dc-dots   { font-size:11px;letter-spacing:3px;margin-bottom:7px }
.dc-meta   { display:flex;justify-content:space-between;font-size:9px;color:#6b7a99 }
.dc-meta b { color:#c8d0e0 }
.dc-conc   { color:#e63950;font-weight:700 }

/* Alert banners */
.alert-critical {
    background: linear-gradient(135deg, #2d0a0f 0%, #1a0608 100%);
    border: 1px solid #e63950;
    border-left: 5px solid #e63950;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.alert-high {
    background: linear-gradient(135deg, #2d1800 0%, #1a0f00 100%);
    border: 1px solid #f8961e;
    border-left: 5px solid #f8961e;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.alert-drug-name { color:#e8ecf4;font-weight:700;font-size:13px }
.alert-badge { display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;margin-left:8px }
.alert-meta  { color:#8896b3;font-size:11px;margin-top:4px }

/* News feed cards */
.news-card {
    background: #1a2035;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-left: 4px solid #4a90d9;
}
.news-title { color:#e8ecf4;font-weight:700;font-size:13px;margin-bottom:4px }
.news-summary { color:#8896b3;font-size:11px;margin-bottom:6px }
.news-meta { color:#5a6a8a;font-size:10px }
.source-badge { display:inline-block;padding:2px 7px;border-radius:3px;font-size:9px;font-weight:700;margin-left:6px }

/* KPI tile override */
div[data-testid="metric-container"] {
    background: #1a2035;
    border: 1px solid #2e3650;
    border-radius: 8px;
    padding: 12px 16px;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 💊 Nipharma Tech")
    st.caption("Stock Intelligence Unit")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Intelligence Dashboard",
            "⚠️  Early Warning",
            "🔗 Supply Chain Risk",
            "🔍 Drug Lookup",
            "📈 Concession Trends",
            "📡 Market Signals",
            "🤖 Model Info",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**Model v6** · Random Forest (panel)")

    predictions_sidebar = load_predictions()
    if predictions_sidebar is not None:
        n_high   = int((predictions_sidebar["shortage_probability"] >= 0.70).sum())
        n_conc   = int(predictions_sidebar["on_concession"].sum()) if "on_concession" in predictions_sidebar.columns else 0
        n_scored = len(predictions_sidebar)
        st.metric("Drugs scored", n_scored)
        st.metric("🔴 High risk (≥70%)", n_high)
        st.metric("⚠️  On concession now", n_conc)

    st.markdown("---")
    st.markdown(
        "| Metric | Score |\n|---|---|\n"
        "| ROC-AUC | **0.998** |\n"
        "| PR-AUC  | **0.990** |\n"
        "| F1      | **0.932** |\n"
        "| Training rows | 44,363 |"
    )
    st.caption("Data: March 2026")

    # ── Per-page sidebar filters ────────────────────────────────────────────────
    if page == "🏠 Intelligence Dashboard":
        st.markdown("---")
        st.markdown("#### Filters")
        n_show = st.select_slider("Top N drugs", [10, 20, 30, 50], value=20)
        min_prob = st.slider("Min risk %", 0, 100, 30, 5)
        tier_filter = st.multiselect(
            "Risk tier",
            ["CONFIRMED", "HIGH", "MEDIUM", "LOW", "WATCH"],
            default=["CONFIRMED", "HIGH", "MEDIUM"],
        )
        action_filter = st.multiselect(
            "Buy action",
            ["🔴 BUY NOW", "🟠 BUY MORE", "🟠 BUY AHEAD",
             "🟡 MANAGE STOCK", "🟡 WATCH", "⚪ NORMAL", "✅ NO ACTION"],
            default=[],
            placeholder="All actions",
        )
        only_new = st.checkbox("New risk only (hide on-concession)", False)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — INTELLIGENCE DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════

if page == "🏠 Intelligence Dashboard":
    st.title("🏠 Intelligence Dashboard")
    st.caption(
        "Drugs most likely to receive a price concession **next month**, "
        "ranked by Random Forest probability (Model v6 · ROC-AUC 0.998)."
    )

    predictions = load_predictions()
    if predictions is None:
        st.error("No predictions found. Run `python 12_ml_model_panel.py` in Terminal first.")
        st.stop()

    # Apply sidebar filters
    min_prob_frac = min_prob / 100.0
    df = predictions[predictions["shortage_probability"] >= min_prob_frac].copy()
    if tier_filter:
        df = df[df["risk_tier"].isin(tier_filter)]
    if action_filter:
        df = df[df["buy_action"].isin(action_filter)]
    if only_new and "on_concession" in df.columns:
        df = df[df["on_concession"] == 0]
    df = df.head(n_show)

    # ── CRITICAL ALERT BANNERS (above everything) ───────────────────────────────
    buy_now_drugs   = predictions[predictions["buy_action"] == "🔴 BUY NOW"].head(5)
    buy_ahead_drugs = predictions[predictions["buy_action"] == "🟠 BUY AHEAD"].head(5)

    if len(buy_now_drugs) > 0:
        st.markdown("### 🚨 Critical — Immediate Action Required")
        for _, drug in buy_now_drugs.iterrows():
            prob_pct = int(drug["shortage_probability"] * 100)
            streak   = int(drug.get("concession_streak", 0) or 0)
            fp       = float(drug.get("floor_proximity", 1.0) or 1.0)
            st.markdown(f"""
            <div class="alert-critical">
                <span class="alert-drug-name">{drug['drug_name']}</span>
                <span class="alert-badge" style="background:#e6395022;color:#e63950;border:1px solid #e63950">🔴 BUY NOW</span>
                <div class="alert-meta">{prob_pct}% risk · Floor proximity {fp:.3f} · Streak {streak} months · Rank #{int(drug['rank'])}</div>
            </div>
            """, unsafe_allow_html=True)

    if len(buy_ahead_drugs) > 0:
        st.markdown("### ⚠️ High Priority — Buy Ahead")
        for _, drug in buy_ahead_drugs.iterrows():
            prob_pct = int(drug["shortage_probability"] * 100)
            streak   = int(drug.get("concession_streak", 0) or 0)
            fp       = float(drug.get("floor_proximity", 1.0) or 1.0)
            st.markdown(f"""
            <div class="alert-high">
                <span class="alert-drug-name">{drug['drug_name']}</span>
                <span class="alert-badge" style="background:#f8961e22;color:#f8961e;border:1px solid #f8961e">🟠 BUY AHEAD</span>
                <div class="alert-meta">{prob_pct}% risk · Floor proximity {fp:.3f} · Streak {streak} months · Rank #{int(drug['rank'])}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── KPI metrics ────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric(
        "🔴 BUY NOW",
        int((predictions["buy_action"] == "🔴 BUY NOW").sum()) if "buy_action" in predictions.columns else "—",
        help="≥90% risk, NOT on concession — most urgent",
    )
    m2.metric(
        "🟠 BUY AHEAD",
        int((predictions["buy_action"] == "🟠 BUY AHEAD").sum()) if "buy_action" in predictions.columns else "—",
        help="≥70% risk, NOT on concession — accumulate now",
    )
    m3.metric(
        "🟠 BUY MORE",
        int((predictions["buy_action"] == "🟠 BUY MORE").sum()) if "buy_action" in predictions.columns else "—",
        help="≥90% risk, already on concession",
    )
    m4.metric(
        "🟡 WATCH",
        int(predictions["buy_action"].isin(["🟡 WATCH", "🟡 MANAGE STOCK"]).sum()) if "buy_action" in predictions.columns else "—",
    )
    m5.metric(
        "⚠️  On concession now",
        int(predictions["on_concession"].sum()) if "on_concession" in predictions.columns else "—",
    )
    m6.metric("📦 Total drugs scored", len(predictions))

    st.markdown("---")

    # ── Load panel data for sparklines ─────────────────────────────────────────
    panel = load_panel()

    # ── Main tab content ────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚨 Priority Watchlist",
        "📊 Risk Rankings",
        "📋 Full Table",
        "📦 Procurement Order",
    ])

    # ── TAB 1: Priority Watchlist (3 per row cards) ─────────────────────────────
    with tab1:
        cards_df     = df.head(12).reset_index(drop=True)
        n_cards      = len(cards_df)
        cols_per_row = 3

        for row_start in range(0, n_cards, cols_per_row):
            chunk = cards_df.iloc[row_start : row_start + cols_per_row]
            cols  = st.columns(cols_per_row)
            for col, (_, drug) in zip(cols, chunk.iterrows()):
                colour   = ACTION_COLOUR.get(drug["buy_action"], "#90a0b0")
                prob_pct = int(drug["shortage_probability"] * 100)
                streak   = int(drug.get("concession_streak", 0) or 0)
                fp       = float(drug.get("floor_proximity", 1.0) or 1.0)
                on_conc  = int(drug.get("on_concession", 0) or 0)
                last6    = int(drug.get("conc_last_6mo", 0) or 0)

                dots = "".join(
                    f'<span style="color:{colour}">●</span>' if i < last6
                    else '<span style="color:#2e3650">●</span>'
                    for i in range(6)
                )

                fp_col = "#e63950" if fp < 1.05 else ("#f8961e" if fp < 1.15 else "#90be6d")
                conc_badge = (
                    '<span class="dc-conc">● On concession</span>' if on_conc
                    else '<span style="color:#2e3650">○ Not on concession</span>'
                )

                card_html = f"""
                <div class="drug-card" style="border-left:4px solid {colour}">
                    <div class="dc-rank">#{int(drug['rank'])}</div>
                    <div class="dc-name">{drug['drug_name'][:42]}</div>
                    <div class="dc-prob" style="color:{colour}">{prob_pct}%</div>
                    <div class="dc-badge" style="background:{colour}22;color:{colour};border:1px solid {colour}55">{drug['buy_action']}</div>
                    <div class="dc-dots">{dots}</div>
                    <div class="dc-meta">
                        <span>Floor prox: <b style="color:{fp_col}">{fp:.3f}</b></span>
                        <span>Streak: <b>{streak}mo</b></span>
                        {conc_badge}
                    </div>
                </div>
                """
                col.markdown(card_html, unsafe_allow_html=True)

                # Expandable sparkline + detail
                with col.expander("→ Expand", expanded=False):
                    if panel is not None and "drug_name" in panel.columns:
                        d_panel = panel[panel["drug_name"] == drug["drug_name"]].copy()
                        if len(d_panel) > 0:
                            d_panel["month"] = pd.to_datetime(d_panel["month"].astype(str), errors="coerce")
                            d_panel = d_panel.sort_values("month").tail(12)
                            if "price_gbp" in d_panel.columns:
                                mini_fig = go.Figure(go.Scatter(
                                    x=d_panel["month"],
                                    y=d_panel["price_gbp"],
                                    mode="lines+markers",
                                    line=dict(color=colour, width=2),
                                    marker=dict(size=4),
                                    name="Price",
                                ))
                                mini_fig.update_layout(
                                    height=120,
                                    margin=dict(l=5, r=5, t=5, b=5),
                                    showlegend=False,
                                    xaxis=dict(showticklabels=False),
                                    plot_bgcolor="#0e1117",
                                    paper_bgcolor="#0e1117",
                                )
                                col.plotly_chart(mini_fig, use_container_width=True)

                    col.write(f"Floor proximity: {fp:.3f}")
                    col.write(f"MHRA mentions: {int(drug.get('mhra_mention_count', 0) or 0)}")
                    col.write(f"Demand spike: {'Yes' if drug.get('demand_spike', 0) else 'No'}")
                    if "pharmacy_over_tariff" in drug:
                        col.write(f"Over tariff: {'Yes' if drug.get('pharmacy_over_tariff', 0) else 'No'}")

    # ── TAB 2: Risk Rankings bar chart ─────────────────────────────────────────
    with tab2:
        chart_df = df.head(30).copy()
        chart_df["label"]    = chart_df["drug_name"].str[:48]
        chart_df["prob_pct"] = (chart_df["shortage_probability"] * 100).round(1)

        fig_bar = px.bar(
            chart_df.sort_values("shortage_probability"),
            x="prob_pct",
            y="label",
            orientation="h",
            color="buy_action",
            color_discrete_map=ACTION_COLOUR,
            labels={"prob_pct": "Shortage Probability (%)", "label": ""},
            title=f"Top {min(30, len(chart_df))} Drugs — Ranked by Risk",
            text="prob_pct",
            custom_data=["buy_action", "concession_streak"],
        )
        fig_bar.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Risk: %{x:.1f}%<br>Action: %{customdata[0]}<br>Streak: %{customdata[1]} months<extra></extra>",
        )
        fig_bar.update_layout(
            height=max(420, min(30, len(chart_df)) * 26),
            showlegend=True,
            legend_title_text="Buy Action",
            xaxis_range=[0, 118],
            margin=dict(l=10, r=30, t=40, b=10),
            plot_bgcolor="#161b27",
            paper_bgcolor="#161b27",
            font=dict(color="#c8d0e0"),
            xaxis=dict(gridcolor="#2e3650", tickcolor="#6b7a99"),
            yaxis=dict(gridcolor="#2e3650", tickcolor="#6b7a99"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── TAB 3: Full Table ───────────────────────────────────────────────────────
    with tab3:
        st.subheader(f"Alert Table — {len(df)} drugs")

        with st.expander("📖 Buying Action Guide", expanded=False):
            st.markdown("""
| Action | Condition | What to do |
|---|---|---|
| 🔴 **BUY NOW** | ≥90% risk · NOT on concession | Imminent shortage — stock up immediately before announcement |
| 🟠 **BUY MORE** | ≥90% risk · On concession | Already conceded, likely to continue — increase holding |
| 🟠 **BUY AHEAD** | ≥70% risk · NOT on concession | High risk — accumulate stock before competitors react |
| 🟡 **MANAGE STOCK** | ≥70% risk · On concession | Ongoing — track stock weekly, avoid over-exposure |
| 🟡 **WATCH** | ≥50% risk | Elevated signal — monitor monthly |
| ⚪ **NORMAL** | ≥30% risk | Standard purchasing, no special action |
| ✅ **NO ACTION** | <30% risk | No shortage signal — avoid overstocking |
            """)

        display_cols = [
            "rank", "drug_name", "buy_action", "shortage_probability", "risk_tier",
            "floor_proximity", "on_concession", "concession_streak",
            "conc_last_6mo", "mhra_mention_count", "demand_spike",
            "pharmacy_over_tariff",
        ]
        avail_cols = [c for c in display_cols if c in df.columns]
        display = df[avail_cols].copy()
        display["shortage_probability"] = (display["shortage_probability"] * 100).round(1).astype(str) + "%"
        display["floor_proximity"] = display["floor_proximity"].round(3)
        display["risk_tier"] = display["risk_tier"].apply(tier_badge)

        display = display.rename(columns={
            "rank": "#",
            "drug_name": "Drug",
            "buy_action": "Buy Action",
            "shortage_probability": "Risk %",
            "risk_tier": "Tier",
            "floor_proximity": "Floor Prox.",
            "on_concession": "On Conc.",
            "concession_streak": "Streak",
            "conc_last_6mo": "Last 6mo",
            "mhra_mention_count": "MHRA",
            "demand_spike": "Demand↑",
            "pharmacy_over_tariff": "Over Tariff",
        })

        st.dataframe(display, use_container_width=True, height=520)

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            csv = df[avail_cols].to_csv(index=False)
            st.download_button("⬇️ Download filtered CSV", csv, "shortage_alerts.csv", "text/csv")
        with dcol2:
            high_only = predictions[predictions["shortage_probability"] >= 0.70]
            avail_cols_high = [c for c in display_cols if c in high_only.columns]
            csv2 = high_only[avail_cols_high].to_csv(index=False)
            st.download_button("⬇️ Download HIGH+ only CSV", csv2, "shortage_alerts_high.csv", "text/csv")

    # ── TAB 4: Procurement Order ────────────────────────────────────────────────
    with tab4:
        st.subheader("📦 Procurement Priority Order")
        st.caption(
            "Filtered to actionable buy signals only. "
            "Use this to brief your procurement team or pharmacy buying group."
        )

        proc_actions = ["🔴 BUY NOW", "🟠 BUY AHEAD", "🟠 BUY MORE", "🟡 MANAGE STOCK"]
        proc_df = predictions[predictions["buy_action"].isin(proc_actions)].copy()

        action_priority = {
            "🔴 BUY NOW":      1,
            "🟠 BUY MORE":     2,
            "🟠 BUY AHEAD":    3,
            "🟡 MANAGE STOCK": 4,
        }
        proc_df["priority_rank"] = proc_df["buy_action"].map(action_priority)
        proc_df = proc_df.sort_values(["priority_rank", "shortage_probability"], ascending=[True, False])
        proc_df["Priority"] = proc_df["priority_rank"].map({1: "URGENT", 2: "HIGH", 3: "HIGH", 4: "MEDIUM"})

        proc_display_cols = [
            "Priority", "drug_name", "buy_action", "shortage_probability",
            "concession_streak", "floor_proximity",
        ]
        proc_avail = [c for c in proc_display_cols if c in proc_df.columns]
        proc_out = proc_df[proc_avail].copy()
        proc_out["shortage_probability"] = (proc_out["shortage_probability"] * 100).round(1).astype(str) + "%"
        if "floor_proximity" in proc_out.columns:
            proc_out["floor_proximity"] = proc_out["floor_proximity"].round(3)
        proc_out = proc_out.rename(columns={
            "drug_name": "Drug Name",
            "buy_action": "Action",
            "shortage_probability": "Risk %",
            "concession_streak": "Streak (mo)",
            "floor_proximity": "Floor Proximity",
        })

        p1, p2, p3 = st.columns(3)
        p1.metric("URGENT (BUY NOW)", int((proc_df["buy_action"] == "🔴 BUY NOW").sum()))
        p2.metric("HIGH (BUY AHEAD/MORE)", int(proc_df["buy_action"].isin(["🟠 BUY AHEAD", "🟠 BUY MORE"]).sum()))
        p3.metric("MEDIUM (MANAGE)", int((proc_df["buy_action"] == "🟡 MANAGE STOCK").sum()))

        st.dataframe(proc_out, use_container_width=True, height=480)

        from datetime import date
        today_str = date.today().strftime("%Y%m%d")
        proc_csv = proc_df[proc_avail].to_csv(index=False)
        st.download_button(
            f"⬇️ Download Procurement Order",
            proc_csv,
            f"procurement_order_{today_str}.csv",
            "text/csv",
        )


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — EARLY WARNING
# ════════════════════════════════════════════════════════════════════════════════

elif page == "⚠️  Early Warning":
    st.title("⚠️ Early Warning Intelligence")
    st.caption(
        "Live feed of regulatory signals that precede NHS price concessions by 4–16 weeks. "
        "Monitor these weekly to stay ahead of the market."
    )

    mhra_df   = load_mhra_alerts()
    fda_df    = load_fda_warnings()
    cpe_df    = load_cpe_news()
    mims_df   = load_mims_shortages()
    ew_df     = load_early_warning_features()

    from datetime import timedelta
    now = pd.Timestamp.now()
    cutoff_30d = now - timedelta(days=30)

    # ── KPI row ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    mhra_30d = 0
    if mhra_df is not None and "published" in mhra_df.columns:
        mhra_30d = int((mhra_df["published"] >= cutoff_30d).sum())
    k1.metric("📡 MHRA Alerts (30d)", mhra_30d)

    fda_count = len(fda_df) if fda_df is not None else 0
    k2.metric("🇺🇸 FDA Warnings", fda_count)

    cpe_count = len(cpe_df) if cpe_df is not None else 0
    k3.metric("💊 CPE Shortage News", cpe_count)

    mims_count = len(mims_df) if mims_df is not None else 0
    k4.metric("📰 MIMS Shortages", mims_count)

    st.markdown("---")

    tab_mhra, tab_fda, tab_cpe, tab_mims = st.tabs([
        "📡 MHRA Alerts",
        "🇺🇸 FDA Warnings",
        "💊 CPE News",
        "📰 MIMS",
    ])

    # ── MHRA Alerts tab ────────────────────────────────────────────────────────
    with tab_mhra:
        if mhra_df is None:
            st.warning("MHRA alerts not found. Run early warning scrapers.")
        else:
            date_range = st.selectbox(
                "Date range",
                ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
                index=1,
                key="mhra_range",
            )
            cutoff_map = {
                "Last 7 days": now - timedelta(days=7),
                "Last 30 days": now - timedelta(days=30),
                "Last 90 days": now - timedelta(days=90),
                "All time": pd.Timestamp("2000-01-01"),
            }
            cutoff = cutoff_map[date_range]

            if "published" in mhra_df.columns:
                filtered_mhra = mhra_df[mhra_df["published"] >= cutoff].copy()
            else:
                filtered_mhra = mhra_df.copy()

            st.markdown(f"**{len(filtered_mhra)} alerts** in selected period")

            if len(filtered_mhra) == 0:
                st.info("No MHRA alerts found for the selected date range.")
            else:
                for _, row in filtered_mhra.head(50).iterrows():
                    title   = str(row.get("title", "Untitled"))
                    summary = str(row.get("summary", ""))
                    summary_short = (summary[:150] + "…") if len(summary) > 150 else summary
                    pub_date = row.get("published", "")
                    pub_str  = pub_date.strftime("%d %b %Y") if pd.notna(pub_date) and hasattr(pub_date, "strftime") else str(pub_date)
                    source   = str(row.get("source", "MHRA"))
                    url      = str(row.get("url", ""))
                    drugs    = str(row.get("matched_drugs", ""))
                    drug_count = row.get("drug_count", 0)

                    drug_info = ""
                    if drugs and drugs != "nan":
                        drug_info = f" · Drugs: {drugs[:80]}"

                    link_html = f'<a href="{url}" target="_blank" style="color:#4a90d9;font-size:10px">→ View</a>' if url and url != "nan" else ""

                    st.markdown(f"""
                    <div class="news-card">
                        <div class="news-title">{title[:120]}</div>
                        <div class="news-summary">{summary_short}</div>
                        <div class="news-meta">{pub_str}
                            <span class="source-badge" style="background:#1a3050;color:#4a90d9">{source}</span>
                            {drug_info}
                            &nbsp;&nbsp;{link_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Early warning scores heat-map if available
            if ew_df is not None and "govuk_mhra_mentions" in ew_df.columns:
                st.markdown("---")
                st.subheader("MHRA Mention Frequency by Drug")
                top_mhra = ew_df[ew_df["govuk_mhra_mentions"] > 0].sort_values("govuk_mhra_mentions", ascending=False).head(20)
                if len(top_mhra) > 0:
                    fig_mhra = px.bar(
                        top_mhra,
                        x="govuk_mhra_mentions",
                        y="drug_name",
                        orientation="h",
                        color="govuk_mhra_mentions",
                        color_continuous_scale="Reds",
                        labels={"govuk_mhra_mentions": "MHRA Mentions", "drug_name": ""},
                        title="Top drugs by MHRA mention count",
                    )
                    fig_mhra.update_layout(
                        height=max(300, len(top_mhra) * 26),
                        coloraxis_showscale=False,
                        margin=dict(l=10, r=10, t=40, b=10),
                    )
                    st.plotly_chart(fig_mhra, use_container_width=True)

    # ── FDA Warnings tab ───────────────────────────────────────────────────────
    with tab_fda:
        if fda_df is None:
            st.warning("FDA warning letters not found. Run early warning scrapers.")
        else:
            st.subheader(f"FDA Warning Letters — {len(fda_df)} records")
            st.caption(
                "FDA warning letters to API manufacturers often precede UK supply disruptions "
                "by 8–24 weeks. Cross-reference with your current stock list."
            )
            # Show available columns
            fda_show = fda_df.copy()
            st.dataframe(fda_show, use_container_width=True, height=500)
            st.download_button(
                "⬇️ Download FDA Warnings CSV",
                fda_df.to_csv(index=False),
                "fda_warnings.csv",
                "text/csv",
            )

            # If we have early warning features, show fda_warning_mentions
            if ew_df is not None and "fda_warning_mentions" in ew_df.columns:
                st.markdown("---")
                st.subheader("FDA Warning Impact on UK Drugs")
                fda_ew = ew_df[ew_df["fda_warning_mentions"] > 0].sort_values("fda_warning_mentions", ascending=False).head(20)
                if len(fda_ew) > 0:
                    fig_fda = px.bar(
                        fda_ew,
                        x="fda_warning_mentions",
                        y="drug_name",
                        orientation="h",
                        color="fda_warning_mentions",
                        color_continuous_scale="Oranges",
                        labels={"fda_warning_mentions": "FDA Warning Mentions", "drug_name": ""},
                        title="UK drugs with FDA warning letter associations",
                    )
                    fig_fda.update_layout(
                        height=max(300, len(fda_ew) * 26),
                        coloraxis_showscale=False,
                        margin=dict(l=10, r=10, t=40, b=10),
                    )
                    st.plotly_chart(fig_fda, use_container_width=True)

    # ── CPE News tab ───────────────────────────────────────────────────────────
    with tab_cpe:
        if cpe_df is None:
            st.warning("CPE shortage news not found. Run early warning scrapers.")
        else:
            st.subheader(f"CPE Shortage News — {len(cpe_df)} items")
            st.caption(
                "Community Pharmacy England shortage news and concession notifications. "
                "Direct signal from the pharmacy sector."
            )
            st.dataframe(cpe_df, use_container_width=True, height=500)
            st.download_button(
                "⬇️ Download CPE News CSV",
                cpe_df.to_csv(index=False),
                "cpe_news.csv",
                "text/csv",
            )

    # ── MIMS tab ───────────────────────────────────────────────────────────────
    with tab_mims:
        if mims_df is None:
            st.warning("MIMS shortage data not found. Run early warning scrapers.")
        else:
            st.subheader(f"MIMS Shortage Register — {len(mims_df)} drugs")
            st.caption(
                "MIMS shortage alerts — a curated list of drugs with confirmed supply issues. "
                "High signal-to-noise, typically 2–6 weeks ahead of CPE concessions."
            )
            st.dataframe(mims_df, use_container_width=True, height=500)
            st.download_button(
                "⬇️ Download MIMS Shortages CSV",
                mims_df.to_csv(index=False),
                "mims_shortages.csv",
                "text/csv",
            )

    # ── Early Warning Score Summary ─────────────────────────────────────────────
    if ew_df is not None and "early_warning_score" in ew_df.columns:
        st.markdown("---")
        st.subheader("Early Warning Score — Top 25 Drugs at Risk")
        st.caption(
            "Composite score combining MHRA, FDA, CPE and MIMS signals. "
            "High score = multiple independent signals firing simultaneously."
        )
        ew_top = ew_df.sort_values("early_warning_score", ascending=False).head(25)
        score_cols = [c for c in [
            "drug_name", "early_warning_score", "govuk_mhra_mentions_30d",
            "fda_warning_mentions", "cpe_concession_flag", "mims_shortage_flag",
        ] if c in ew_df.columns]
        st.dataframe(ew_top[score_cols], use_container_width=True, height=500)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SUPPLY CHAIN RISK
# ════════════════════════════════════════════════════════════════════════════════

elif page == "🔗 Supply Chain Risk":
    st.title("🔗 Supply Chain Risk Intelligence")
    st.caption(
        "API cascade clusters and manufacturer concentration risk. "
        "A single API supplier failure can trigger shortages across dozens of drugs simultaneously."
    )

    cascade_df = load_api_cascade()
    mfr_df     = load_api_manufacturers()
    fda_df     = load_openfda_shortages()

    # ── KPI row ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    total_mapped = len(cascade_df) if cascade_df is not None else 0
    k1.metric("Total drugs mapped", total_mapped)

    high_cascade = 0
    if cascade_df is not None and "api_cascade_count" in cascade_df.columns:
        high_cascade = int((cascade_df["api_cascade_count"] >= 5).sum())
    k2.metric("High cascade risk (≥5 drugs)", high_cascade)

    critical_single = 0
    if mfr_df is not None and "api_concentration_risk" in mfr_df.columns:
        critical_single = int((mfr_df["api_concentration_risk"] == "CRITICAL").sum())
    k3.metric("Critical single-source APIs", critical_single)

    active_us = 0
    if fda_df is not None:
        active_us = int((fda_df.get("Status", pd.Series(dtype=str)) == "Current").sum()) if "Status" in fda_df.columns else len(fda_df)
    k4.metric("Active US shortages", active_us)

    st.markdown("---")

    tab_cascade, tab_mfr, tab_us = st.tabs([
        "🔗 Cascade Clusters",
        "🏭 Manufacturer Intelligence",
        "🇺🇸 US Shortage Watch",
    ])

    # ── Tab 1: Cascade Clusters ─────────────────────────────────────────────────
    with tab_cascade:
        if cascade_df is None:
            st.warning("API cascade map not found. Run `python 20_openfda_api_cascade.py`.")
        else:
            st.subheader("API Cascade Risk Map")
            st.caption(
                "APIs shared by many drugs represent concentration risk. "
                "A regulatory action or supply disruption on one API cascades to all dependent drugs."
            )

            sort_col = "api_cascade_count" if "api_cascade_count" in cascade_df.columns else cascade_df.columns[0]
            cascade_sorted = cascade_df.sort_values(sort_col, ascending=False)

            # Top 20 bar chart
            if "api_name" in cascade_df.columns and "api_cascade_count" in cascade_df.columns:
                top20 = cascade_sorted.head(20)
                conc_col = "api_concentration_risk" if "api_concentration_risk" in cascade_df.columns else None

                colour_map_cascade = {
                    "CRITICAL": "#e63950",
                    "HIGH": "#f8961e",
                    "MEDIUM": "#f9c74f",
                    "LOW": "#90be6d",
                }

                if conc_col:
                    top20 = top20.copy()
                    top20["bar_colour"] = top20[conc_col].map(colour_map_cascade).fillna("#90a0b0")

                fig_cas = px.bar(
                    top20,
                    x="api_cascade_count",
                    y="api_name",
                    orientation="h",
                    color=conc_col if conc_col else None,
                    color_discrete_map=colour_map_cascade if conc_col else None,
                    labels={"api_cascade_count": "Drugs sharing this API", "api_name": ""},
                    title="Top 20 APIs by cascade cluster size",
                    text="api_cascade_count",
                )
                fig_cas.update_traces(textposition="outside")
                fig_cas.update_layout(
                    height=max(400, len(top20) * 28),
                    margin=dict(l=10, r=30, t=40, b=10),
                    plot_bgcolor="#161b27",
                    paper_bgcolor="#161b27",
                    font=dict(color="#c8d0e0"),
                )
                st.plotly_chart(fig_cas, use_container_width=True)

            # Expandable cluster detail per API
            st.markdown("---")
            st.subheader("Cluster Detail")
            show_top_n = st.slider("Show top N API clusters", 5, 30, 10, key="cascade_slider")
            for _, row in cascade_sorted.head(show_top_n).iterrows():
                api_name = str(row.get("api_name", "Unknown API"))
                count    = int(row.get("api_cascade_count", 0) or 0)
                drugs_in_cluster = str(row.get("api_cascade_drugs", ""))
                on_conc_count    = int(row.get("api_cascade_on_concession", 0) or 0)
                conc_risk        = str(row.get("api_concentration_risk", ""))
                mfr_count        = int(row.get("api_manufacturer_count", 0) or 0)
                india_pct        = float(row.get("api_india_china_pct", 0) or 0)
                us_shortages     = int(row.get("api_us_shortage_count", 0) or 0)

                risk_colour = colour_map_cascade.get(conc_risk, "#90a0b0")

                with st.expander(f"**{api_name}** — {count} drugs · Risk: {conc_risk}", expanded=False):
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    cc1.metric("Drugs in cluster", count)
                    cc2.metric("On concession now", on_conc_count)
                    cc3.metric("Manufacturers", mfr_count)
                    cc4.metric("India+China %", f"{india_pct:.0f}%")

                    if drugs_in_cluster and drugs_in_cluster != "nan":
                        st.markdown(f"**Affected drugs:** {drugs_in_cluster[:500]}")

                    if us_shortages > 0:
                        st.warning(f"⚠️ {us_shortages} active US shortage(s) detected for this API.")

            st.markdown("---")
            st.dataframe(cascade_sorted, use_container_width=True, height=400)
            st.download_button(
                "⬇️ Download Cascade Map CSV",
                cascade_df.to_csv(index=False),
                "api_cascade_map.csv",
                "text/csv",
            )

    # ── Tab 2: Manufacturer Intelligence ───────────────────────────────────────
    with tab_mfr:
        if mfr_df is None:
            st.warning("API manufacturer database not found. Run `python 20_openfda_api_cascade.py`.")
        else:
            st.subheader("Manufacturer Concentration Intelligence")
            st.caption(
                "Drugs sourced from a single manufacturer, or from manufacturers "
                "heavily concentrated in India/China, carry the highest supply chain risk."
            )

            if "api_concentration_risk" in mfr_df.columns:
                risk_counts = mfr_df["api_concentration_risk"].value_counts().reset_index()
                risk_counts.columns = ["Risk Level", "Count"]

                col_chart, col_metrics = st.columns([2, 1])
                with col_chart:
                    fig_risk = px.bar(
                        risk_counts,
                        x="Risk Level",
                        y="Count",
                        color="Risk Level",
                        color_discrete_map={
                            "CRITICAL": "#e63950",
                            "HIGH": "#f8961e",
                            "MEDIUM": "#f9c74f",
                            "LOW": "#90be6d",
                        },
                        title="Manufacturer Concentration Risk Distribution",
                        text="Count",
                    )
                    fig_risk.update_traces(textposition="outside")
                    fig_risk.update_layout(
                        height=300,
                        showlegend=False,
                        margin=dict(l=10, r=10, t=40, b=10),
                    )
                    st.plotly_chart(fig_risk, use_container_width=True)

                with col_metrics:
                    for level, colour in [("CRITICAL", "#e63950"), ("HIGH", "#f8961e"), ("MEDIUM", "#f9c74f"), ("LOW", "#90be6d")]:
                        n = int((mfr_df["api_concentration_risk"] == level).sum())
                        st.markdown(f'<span style="color:{colour};font-weight:700">{level}</span>: {n} drugs', unsafe_allow_html=True)

            # Highlight CRITICAL rows
            if "api_concentration_risk" in mfr_df.columns:
                critical_df = mfr_df[mfr_df["api_concentration_risk"] == "CRITICAL"].copy()
                if len(critical_df) > 0:
                    st.markdown("---")
                    st.subheader(f"🚨 {len(critical_df)} CRITICAL concentration risk drugs")
                    st.dataframe(critical_df, use_container_width=True, height=350)

            st.markdown("---")
            st.subheader("Full Manufacturer Database")

            # India/China dependency chart
            if "api_india_china_pct" in mfr_df.columns and "molecule" in mfr_df.columns:
                top_india = mfr_df.sort_values("api_india_china_pct", ascending=False).head(20)
                fig_india = px.bar(
                    top_india,
                    x="api_india_china_pct",
                    y="molecule",
                    orientation="h",
                    color="api_india_china_pct",
                    color_continuous_scale="Oranges",
                    labels={"api_india_china_pct": "India+China API %", "molecule": ""},
                    title="Top 20 drugs by India/China API dependency",
                    text="api_india_china_pct",
                )
                fig_india.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
                fig_india.update_layout(
                    height=max(350, len(top_india) * 26),
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=30, t=40, b=10),
                )
                st.plotly_chart(fig_india, use_container_width=True)

            st.dataframe(mfr_df, use_container_width=True, height=400)
            st.download_button(
                "⬇️ Download Manufacturer DB CSV",
                mfr_df.to_csv(index=False),
                "api_manufacturer_db.csv",
                "text/csv",
            )

    # ── Tab 3: US Shortage Watch ───────────────────────────────────────────────
    with tab_us:
        if fda_df is None:
            st.warning("OpenFDA shortage data not found. Run `python 20_openfda_api_cascade.py`.")
        else:
            st.subheader(f"US FDA Drug Shortage Database — {len(fda_df)} records")
            st.caption(
                "Active US drug shortages often precede UK shortages by 4–12 weeks. "
                "US and UK generic markets share many of the same Indian API manufacturers."
            )

            predictions_sc = load_predictions()
            uk_drugs = set()
            if predictions_sc is not None:
                uk_drugs = set(predictions_sc["drug_name"].str.lower().str.split().str[0].dropna())

            # Cross-reference with UK drug list
            if "Generic Name or Active Ingredient" in fda_df.columns:
                fda_df_copy = fda_df.copy()
                fda_df_copy["in_uk_watchlist"] = fda_df_copy["Generic Name or Active Ingredient"].str.lower().str.split().str[0].isin(uk_drugs)
                uk_overlap = fda_df_copy[fda_df_copy["in_uk_watchlist"] == True]

                if len(uk_overlap) > 0:
                    st.markdown(f"#### ⚠️ {len(uk_overlap)} US shortages match UK high-risk drugs")
                    st.dataframe(uk_overlap, use_container_width=True, height=300)

                st.markdown("---")
                st.subheader("All US Shortages")

            if "Status" in fda_df.columns:
                status_filter = st.multiselect(
                    "Filter by status",
                    fda_df["Status"].dropna().unique().tolist(),
                    default=["Current"] if "Current" in fda_df["Status"].values else [],
                    key="fda_status_filter",
                )
                if status_filter:
                    fda_show = fda_df[fda_df["Status"].isin(status_filter)]
                else:
                    fda_show = fda_df
            else:
                fda_show = fda_df

            st.dataframe(fda_show, use_container_width=True, height=450)
            st.download_button(
                "⬇️ Download US Shortages CSV",
                fda_df.to_csv(index=False),
                "openfda_shortages.csv",
                "text/csv",
            )


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — DRUG LOOKUP
# ════════════════════════════════════════════════════════════════════════════════

elif page == "🔍 Drug Lookup":
    st.title("🔍 Drug Lookup")
    st.caption("Drill into any drug — price history, concession timeline, risk score, and supply chain profile.")

    panel       = load_panel()
    predictions = load_predictions()
    pca         = load_pca_demand()
    cascade_df  = load_api_cascade()
    mfr_df      = load_api_manufacturers()
    ew_df       = load_early_warning_features()

    if panel is None:
        st.error("Panel feature store not found.")
        st.stop()

    drug_list = sorted(panel["drug_name"].dropna().unique().tolist())

    lcol, rcol = st.columns([3, 1])
    with lcol:
        selected = st.selectbox("Select drug", drug_list)
    with rcol:
        compare_on = st.checkbox("Compare with another drug", False)
    if compare_on:
        selected2 = st.selectbox("Compare drug", [d for d in drug_list if d != selected])

    def get_drug_data(name):
        d = panel[panel["drug_name"] == name].copy()
        d["month"] = pd.to_datetime(d["month"].astype(str))
        d = d.sort_values("month")
        return d

    drug_data = get_drug_data(selected)

    if len(drug_data) == 0:
        st.warning("No data found.")
        st.stop()

    # ── Risk score from predictions ─────────────────────────────────────────────
    pred_row = None
    if predictions is not None and "drug_name" in predictions.columns:
        match = predictions[predictions["drug_name"] == selected]
        if len(match):
            pred_row = match.sort_values("shortage_probability", ascending=False).iloc[0]

    # ── KPI row ─────────────────────────────────────────────────────────────────
    latest = drug_data.iloc[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Price", f"£{latest.get('price_gbp', 0):.4f}")
    c2.metric(
        "Floor Proximity",
        f"{latest.get('floor_proximity', 1):.3f}",
        delta=f"{latest.get('price_mom_pct', 0):+.1f}% MoM",
        delta_color="inverse",
    )
    c3.metric("On Concession", "✅ Yes" if latest.get("on_concession", 0) == 1 else "No")
    c4.metric("Concession Streak", f"{int(latest.get('concession_streak', 0))} months")
    if pred_row is not None:
        p    = pred_row["shortage_probability"]
        tier = pred_row["risk_tier"]
        c5.metric("Shortage Risk", f"{p:.1%}", delta=tier_badge(tier))
    else:
        c5.metric("Shortage Risk", "—")

    st.markdown("---")

    # ── Price + Concession combined chart ───────────────────────────────────────
    st.subheader("Price History & Concession Periods")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    conc_months = drug_data[drug_data["on_concession"] == 1]["month"].tolist()
    for m in conc_months:
        fig.add_vrect(
            x0=m - pd.Timedelta(days=15),
            x1=m + pd.Timedelta(days=15),
            fillcolor="rgba(214, 39, 40, 0.15)",
            line_width=0,
        )

    fig.add_trace(
        go.Scatter(
            x=drug_data["month"],
            y=drug_data["price_gbp"],
            name="NHS Price (£)",
            line=dict(color="#1f77b4", width=2),
            hovertemplate="£%{y:.4f}<br>%{x|%b %Y}<extra></extra>",
        ),
        secondary_y=False,
    )

    if "floor_price_gbp" in drug_data.columns:
        fig.add_trace(
            go.Scatter(
                x=drug_data["month"],
                y=drug_data["floor_price_gbp"],
                name="Floor Price (£)",
                line=dict(color="#d62728", width=1.5, dash="dot"),
                hovertemplate="Floor: £%{y:.4f}<extra></extra>",
            ),
            secondary_y=False,
        )

    if "floor_proximity" in drug_data.columns:
        fig.add_trace(
            go.Scatter(
                x=drug_data["month"],
                y=drug_data["floor_proximity"],
                name="Floor Proximity",
                line=dict(color="#ff7f0e", width=1.5, dash="dash"),
                hovertemplate="Proximity: %{y:.3f}<extra></extra>",
                opacity=0.8,
            ),
            secondary_y=True,
        )
        fig.add_hline(
            y=1.15, line_dash="dot", line_color="orange",
            annotation_text="Danger zone (1.15)",
            secondary_y=True,
        )

    if compare_on:
        drug_data2 = get_drug_data(selected2)
        if len(drug_data2):
            fig.add_trace(
                go.Scatter(
                    x=drug_data2["month"],
                    y=drug_data2["price_gbp"],
                    name=f"{selected2[:30]} (£)",
                    line=dict(color="#9467bd", width=1.5, dash="longdash"),
                    hovertemplate=f"{selected2[:20]}: £%{{y:.4f}}<extra></extra>",
                ),
                secondary_y=False,
            )

    fig.update_layout(
        height=400,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_yaxes(title_text="Price (£)", secondary_y=False)
    fig.update_yaxes(title_text="Floor Proximity", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    if conc_months:
        st.caption(
            f"🔴 Shaded = concession months ({len(conc_months)} total) · "
            "Orange dashed = danger zone threshold"
        )

    # ── PCA demand chart ────────────────────────────────────────────────────────
    if pca is not None:
        first_word = selected.lower().split()[0]
        drug_pca = pca[pca["bnf_name"].str.lower().str.startswith(first_word)].copy()
        if len(drug_pca) > 5:
            drug_pca["month_dt"] = pd.to_datetime(drug_pca["month"].astype(str))
            drug_pca = drug_pca.groupby("month_dt").agg(
                items=("items", "sum"),
                demand_spike=("demand_spike", "max"),
            ).reset_index()
            drug_pca = drug_pca.sort_values("month_dt")

            st.subheader("NHS Prescribing Demand (PCA items/month)")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=drug_pca["month_dt"],
                y=drug_pca["items"],
                marker_color=np.where(drug_pca["demand_spike"] == 1, "#d62728", "#1f77b4"),
                name="Items prescribed",
                hovertemplate="%{x|%b %Y}: %{y:,} items<extra></extra>",
            ))
            fig2.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption(
                "🔴 Red bars = demand spike month (>1.5× rolling average). "
                "Aggregated across all formulations."
            )

    # ── Concession history detail ────────────────────────────────────────────────
    st.subheader("Concession History")
    if conc_months:
        conc_df = pd.DataFrame({"Month": [m.strftime("%b %Y") for m in conc_months]})
        st.dataframe(conc_df.T, use_container_width=True, hide_index=True)
    else:
        st.success("No historical concessions found for this drug.")

    # ── Raw data ────────────────────────────────────────────────────────────────
    with st.expander("📄 Raw panel data"):
        show_cols = [c for c in [
            "month", "price_gbp", "floor_price_gbp", "floor_proximity",
            "on_concession", "concession_streak", "conc_last_6mo",
            "price_mom_pct", "price_yoy_pct", "mhra_mention_count",
            "demand_spike", "items_mom_pct", "brent_stress", "boe_bank_rate",
        ] if c in drug_data.columns]
        dd = drug_data[show_cols].copy()
        dd["month"] = dd["month"].dt.strftime("%b %Y")
        st.dataframe(dd, use_container_width=True)

    # ── NEW: Supply Chain Profile ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔗 Supply Chain Profile")

    sc_found = False
    if cascade_df is not None and "drug_name" in cascade_df.columns:
        drug_sc = cascade_df[cascade_df["drug_name"].str.lower() == selected.lower()].copy()
        if len(drug_sc) > 0:
            sc_found = True
            row_sc = drug_sc.iloc[0]
            conc_risk = str(row_sc.get("api_concentration_risk", "UNKNOWN"))
            risk_col  = {"CRITICAL": "#e63950", "HIGH": "#f8961e", "MEDIUM": "#f9c74f", "LOW": "#90be6d"}.get(conc_risk, "#90a0b0")

            if conc_risk in ("CRITICAL", "HIGH"):
                st.error(f"⚠️ **{conc_risk} concentration risk** — this drug's API sourced from a limited number of manufacturers.")

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("API Name",         str(row_sc.get("api_name", "N/A")))
            sc2.metric("Cluster size",      int(row_sc.get("api_cascade_count", 0) or 0))
            sc3.metric("Manufacturers",     int(row_sc.get("api_manufacturer_count", 0) or 0))
            sc4.metric("India+China %",     f"{float(row_sc.get('api_india_china_pct', 0) or 0):.0f}%")

            cluster_drugs = str(row_sc.get("api_cascade_drugs", ""))
            if cluster_drugs and cluster_drugs != "nan":
                with st.expander("See all drugs sharing this API"):
                    st.write(cluster_drugs)

    if not sc_found:
        if cascade_df is None:
            st.info("Supply chain data not available. Run `python 20_openfda_api_cascade.py`.")
        else:
            st.info("No supply chain mapping found for this drug.")

    # Manufacturer detail
    if mfr_df is not None and "molecule" in mfr_df.columns:
        first_word = selected.lower().split()[0]
        drug_mfr = mfr_df[mfr_df["molecule"].str.lower().str.startswith(first_word)]
        if len(drug_mfr) > 0:
            row_mfr = drug_mfr.iloc[0]
            mfr_names = str(row_mfr.get("api_manufacturers", ""))
            if mfr_names and mfr_names != "nan":
                with st.expander("Known API manufacturers"):
                    st.write(mfr_names)
            us_active = row_mfr.get("us_shortage_active", 0)
            if us_active:
                st.warning(f"⚠️ Active US shortage detected for this molecule ({int(us_active)} active).")

    # ── NEW: Early Warning Signals ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Early Warning Signals")

    if ew_df is not None and "drug_name" in ew_df.columns:
        drug_ew = ew_df[ew_df["drug_name"].str.lower() == selected.lower()]
        if len(drug_ew) > 0:
            row_ew = drug_ew.iloc[0]
            ew_score = float(row_ew.get("early_warning_score", 0) or 0)

            ew_colour = "#e63950" if ew_score >= 3 else ("#f8961e" if ew_score >= 1 else "#90be6d")
            st.markdown(
                f'<div style="background:#1a2035;border-left:4px solid {ew_colour};padding:10px 16px;border-radius:6px;margin-bottom:12px">'
                f'<b style="color:{ew_colour}">Early Warning Score: {ew_score:.1f}</b>'
                f'</div>',
                unsafe_allow_html=True,
            )

            ew1, ew2, ew3, ew4 = st.columns(4)
            ew1.metric("MHRA mentions (30d)", int(row_ew.get("govuk_mhra_mentions_30d", 0) or 0))
            ew2.metric("FDA warning flag",    "Yes" if row_ew.get("fda_api_manufacturer_flag", 0) else "No")
            ew3.metric("CPE concession flag", "Yes" if row_ew.get("cpe_concession_flag", 0) else "No")
            ew4.metric("MIMS shortage flag",  "Yes" if row_ew.get("mims_shortage_flag", 0) else "No")
        else:
            st.info("No early warning features computed for this drug.")
    else:
        st.info("Early warning feature data not available. Run early warning scrapers.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 5 — CONCESSION TRENDS
# ════════════════════════════════════════════════════════════════════════════════

elif page == "📈 Concession Trends":
    st.title("📈 Concession Trends")
    st.caption("Monthly NHS price concession counts — the primary shortage signal (Jan 2020 – Feb 2026).")

    history = load_concession_history()
    if history is None:
        st.error("CPE archive not found.")
        st.stop()

    # ── Date range filter ───────────────────────────────────────────────────────
    min_date = history["month"].min().to_pydatetime()
    max_date = history["month"].max().to_pydatetime()

    dcol1, dcol2 = st.columns(2)
    with dcol1:
        start_date = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date)
    with dcol2:
        end_date = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date)

    mask = (history["month"] >= pd.to_datetime(start_date)) & \
           (history["month"] <= pd.to_datetime(end_date))
    h = history[mask].copy()

    # ── KPI row ─────────────────────────────────────────────────────────────────
    monthly = (
        h.groupby(h["month"].dt.to_period("M"))
        .size()
        .reset_index(name="count")
    )
    monthly["month_dt"] = monthly["month"].dt.to_timestamp()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total events (filtered)", f"{len(h):,}")
    k2.metric("Unique drugs conceded", h["drug_name"].nunique())
    k3.metric(
        "Peak month",
        monthly.loc[monthly["count"].idxmax(), "month"].strftime("%b %Y") if len(monthly) else "—",
    )
    k4.metric("Avg per month", f"{monthly['count'].mean():.0f}" if len(monthly) else "—")

    st.markdown("---")

    # ── Monthly trend chart ─────────────────────────────────────────────────────
    st.subheader("Monthly Concession Count")
    if len(monthly):
        monthly["rolling_3mo"] = monthly["count"].rolling(3, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["month_dt"],
            y=monthly["count"],
            name="Monthly count",
            marker_color="#1f77b4",
            opacity=0.7,
            hovertemplate="%{x|%b %Y}: %{y} drugs<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["month_dt"],
            y=monthly["rolling_3mo"],
            name="3-month avg",
            line=dict(color="#d62728", width=2.5),
            hovertemplate="3mo avg: %{y:.0f}<extra></extra>",
        ))
        fig.update_layout(
            height=350,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── YoY comparison ──────────────────────────────────────────────────────────
    st.subheader("Year-over-Year Comparison")
    history["year"]   = history["month"].dt.year
    history["mo_num"] = history["month"].dt.month
    yoy = history.groupby(["year", "mo_num"]).size().reset_index(name="count")
    yoy["month_name"] = yoy["mo_num"].apply(
        lambda m: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m-1]
    )

    fig2 = px.line(
        yoy[yoy["year"] >= 2021],
        x="month_name",
        y="count",
        color="year",
        markers=True,
        labels={"count": "Concessions", "month_name": "Month", "year": "Year"},
        title="Concessions by month, compared year by year",
        category_orders={"month_name": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]},
    )
    fig2.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    # ── Top chronic drugs ────────────────────────────────────────────────────────
    st.subheader("Most Frequently Conceded Drugs")
    top_n_drugs = st.slider("Show top N drugs", 10, 50, 20, key="trend_top_n")
    top_drugs = (
        h.groupby("drug_name")
        .size()
        .reset_index(name="concession_count")
        .sort_values("concession_count", ascending=True)
        .tail(top_n_drugs)
    )
    fig3 = px.bar(
        top_drugs,
        x="concession_count",
        y="drug_name",
        orientation="h",
        labels={"concession_count": "Times on concession", "drug_name": ""},
        color="concession_count",
        color_continuous_scale="Reds",
    )
    fig3.update_layout(
        height=max(350, top_n_drugs * 22),
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📄 Raw CPE archive (first 500 rows)"):
        st.dataframe(h.head(500), use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 6 — MARKET SIGNALS
# ════════════════════════════════════════════════════════════════════════════════

elif page == "📡 Market Signals":
    st.title("📡 Market Signals")
    st.caption(
        "Macro signals that drive UK generic drug cost pressure — "
        "Brent crude (API energy costs), GBP/INR (Indian manufacturer currency), "
        "BoE base rate (credit/supply chain)."
    )

    brent = load_brent()
    fx    = load_fx()
    boe   = load_boe()

    # ── Brent Crude ─────────────────────────────────────────────────────────────
    st.subheader("🛢️ Brent Crude Oil")
    if brent is not None:
        latest_brent = brent.iloc[-1]
        b1, b2, b3 = st.columns(3)
        b1.metric("Current price", f"${latest_brent['close']:.2f}/bbl")
        if "stress_zscore" in brent.columns and pd.notna(latest_brent.get("stress_zscore")):
            b2.metric(
                "Stress z-score",
                f"{latest_brent['stress_zscore']:.2f}",
                delta="⚠️ Elevated" if latest_brent["stress_zscore"] > 2 else "Normal",
                delta_color="inverse",
            )
        if "mom_pct" in brent.columns and pd.notna(latest_brent.get("mom_pct")):
            b3.metric("Month-on-month", f"{latest_brent['mom_pct']:+.1f}%", delta_color="inverse")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=brent["date"], y=brent["close"],
            fill="tozeroy",
            line=dict(color="#1f77b4", width=1.5),
            fillcolor="rgba(31,119,180,0.15)",
            hovertemplate="$%{y:.2f}/bbl<br>%{x|%d %b %Y}<extra></extra>",
            name="Brent $",
        ))
        if "stress_zscore" in brent.columns:
            stressed = brent[brent["stress_zscore"] > 2]
            fig.add_trace(go.Scatter(
                x=stressed["date"], y=stressed["close"],
                mode="markers",
                marker=dict(color="#d62728", size=4),
                name="High stress (z>2)",
                hovertemplate="STRESS $%{y:.2f}<extra></extra>",
            ))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "60% of UK generic APIs sourced from Indian manufacturers — "
            "high Brent = elevated transport + energy cost."
        )
    else:
        st.warning("Brent data not found. Run `python 16_yfinance_signals.py`.")

    st.markdown("---")

    # ── FX Rates ────────────────────────────────────────────────────────────────
    st.subheader("💱 FX Rates — GBP vs India / China / USD")
    if fx is not None:
        fx_latest = fx.iloc[-1]
        f1, f2, f3 = st.columns(3)
        f1.metric("GBP/INR", f"{fx_latest.get('gbp_inr', '—'):.2f}" if pd.notna(fx_latest.get("gbp_inr")) else "—")
        f2.metric("GBP/CNY", f"{fx_latest.get('gbp_cny', '—'):.2f}" if pd.notna(fx_latest.get("gbp_cny")) else "—")
        f3.metric("GBP/USD", f"{fx_latest.get('gbp_usd', '—'):.2f}" if pd.notna(fx_latest.get("gbp_usd")) else "—")

        fx_cols = [
            (c, name) for c, name in [
                ("gbp_inr", "GBP/INR"),
                ("gbp_cny", "GBP/CNY"),
                ("gbp_usd", "GBP/USD"),
            ] if c in fx.columns
        ]

        if fx_cols:
            fig2 = go.Figure()
            colours = ["#1f77b4", "#ff7f0e", "#2ca02c"]
            for (col, label), col_colour in zip(fx_cols, colours):
                fig2.add_trace(go.Scatter(
                    x=fx["date"], y=fx[col],
                    name=label,
                    line=dict(color=col_colour, width=1.5),
                    hovertemplate=f"{label}: %{{y:.4f}}<br>%{{x|%d %b %Y}}<extra></extra>",
                ))
            fig2.update_layout(
                height=280,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "GBP weakening vs INR = Indian API manufacturers receive less per unit sold to UK "
            "→ margin squeeze → supply reduction signal."
        )
    else:
        st.warning("FX data not found. Run `python 05_market_signals.py`.")

    st.markdown("---")

    # ── BoE Base Rate ────────────────────────────────────────────────────────────
    st.subheader("🏦 Bank of England Base Rate")
    if boe is not None:
        rate_col = next((c for c in boe.columns if "rate" in c.lower() or "bank" in c.lower()), None)
        if rate_col and "date" in boe.columns:
            latest_boe = boe.dropna(subset=[rate_col]).iloc[-1]
            st.metric("Current BoE Rate", f"{latest_boe[rate_col]:.2f}%")

            fig3 = go.Figure(go.Scatter(
                x=boe["date"], y=boe[rate_col],
                mode="lines+markers",
                line=dict(color="#9467bd", width=2),
                fill="tozeroy",
                fillcolor="rgba(148,103,189,0.12)",
                hovertemplate="Rate: %{y:.2f}%<br>%{x|%b %Y}<extra></extra>",
                name="BoE Rate",
            ))
            fig3.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Higher rates → higher supply chain financing costs → manufacturer cash flow pressure.")
        else:
            st.warning("BoE rate column not detected.")
    else:
        st.warning("BoE data not found. Run `python 05_market_signals.py`.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 7 — MODEL INFO
# ════════════════════════════════════════════════════════════════════════════════

elif page == "🤖 Model Info":
    st.title("🤖 Model v6 — Technical Details")

    # ── Metrics ──────────────────────────────────────────────────────────────────
    st.subheader("Cross-Validation Performance (5-fold stratified)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ROC-AUC",  "0.998 ± 0.000", delta="↑ vs v3 (0.982)")
    m2.metric("PR-AUC",   "0.990 ± 0.001", delta="↑ vs v3 (0.936)")
    m3.metric("F1 Score", "0.932 ± 0.004", delta="↑ vs v3 (0.845)")
    m4.metric("Training rows", "44,363",   delta="+29,599 vs v3 (14,764)")

    st.caption(
        "v6 improvements: early warning signal integration (MHRA, FDA, CPE, MIMS), "
        "API cascade features, manufacturer concentration risk scores, OpenFDA shortage signals. "
        "Built on v5 base: full 60-month PCA prescribing data (348,610 rows), "
        "pharmacy invoice over-tariff signals, yfinance Brent crude + Sun Pharma."
    )

    st.markdown("---")

    # ── Feature importance chart ─────────────────────────────────────────────────
    fi = load_feature_importance()
    if fi is not None:
        st.subheader("Feature Importance")

        fi_sorted = fi.sort_values("importance_pct")
        colours = [
            "#d62728" if v > 20 else
            "#ff7f0e" if v > 5  else
            "#2ca02c"
            for v in fi_sorted["importance_pct"]
        ]

        fig = go.Figure(go.Bar(
            x=fi_sorted["importance_pct"],
            y=fi_sorted["feature"],
            orientation="h",
            marker_color=colours,
            text=fi_sorted["importance_pct"].round(1).astype(str) + "%",
            textposition="outside",
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        ))
        fig.update_layout(
            height=max(400, len(fi) * 30),
            xaxis_title="Importance (%)",
            xaxis_range=[0, fi_sorted["importance_pct"].max() * 1.2],
            margin=dict(l=10, r=40, t=10, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
| Feature group | Key signals | Why it matters |
|---|---|---|
| **Concession history** | `conc_last_6mo` (37.6%), `concession_streak` (31.3%), `on_concession` (20.5%) | Once on concession, likely to stay — repeat cycle |
| **Price pressure** | `price_mom_pct` (3.5%), `floor_proximity` (1.2%) | Declining price vs historical floor = unprofitable to supply |
| **Demand** | `demand_trend_6mo` (0.4%), `items_mom_pct` (0.4%), `demand_spike` (0.1%) | Supply-demand gap amplifies shortage risk |
| **Macro** | `brent_stress` (1.1%), `brent_mom_pct` (0.9%), `boe_bank_rate` (0.6%) | Cost pressure on API manufacturers |
| **Regulatory** | `mhra_mention_count` (0.8%), `ssp_flag` (0.3%), `govuk_mhra_mentions_30d` (+) | Active shortage publications |
| **Supply chain** | `sunpharma_stress` (0.9%), `fx_stress_score` (0.2%), `api_concentration_risk` (+) | India-specific cost signals + manufacturer concentration |
| **Early warning** | `early_warning_score` (+), `fda_api_manufacturer_flag` (+), `mims_shortage_flag` (+) | Multi-source cross-validation signals |
        """)

    st.markdown("---")

    # ── Architecture ─────────────────────────────────────────────────────────────
    st.subheader("Model Architecture")
    c1, c2 = st.columns(2)
    with c1:
        st.code("""
RandomForestClassifier(
    n_estimators  = 300,
    max_depth     = 10,
    min_samples_leaf = 5,
    class_weight  = 'balanced',
    random_state  = 42,
    n_jobs        = -1,
)

Target: label_next_month
  = 1 if drug on concession next month
  = 0 otherwise
        """, language="python")
    with c2:
        st.markdown("""
**Why Random Forest?**
- Handles mixed feature types (binary flags, continuous ratios, counts)
- No scaling required
- Robust to missing values in low-importance features
- Built-in feature importance (GINI)
- 5-fold CV avoids temporal leakage via drug stratification
- Production cost: ~30ms inference, ~50MB model file

**Why not deep learning?**
- 44K rows is too small for LSTM/Transformer to outperform RF
- Temporal ordering only matters at label creation (1-month lead)
- RF at 0.998 AUC leaves no headroom to improve
- DL would need 10× data minimum

**v6 new features**
- MHRA 30d mention window (recency-weighted)
- FDA API manufacturer warning flag
- API cascade cluster size
- Manufacturer concentration risk (CRITICAL/HIGH/MEDIUM/LOW)
- OpenFDA US shortage cross-reference
- India/China dependency percentage
        """)

    # ── Full CV metrics ────────────────────────────────────────────────────────
    metrics_text = load_cv_metrics()
    if metrics_text:
        with st.expander("📄 Full CV Metrics Report (raw)"):
            st.text(metrics_text)

    st.markdown("---")
    st.subheader("Data Pipeline")
    st.markdown("""
    ```
    NHSBSA Drug Tariff (25 files)        ──┐
    CPE Concession Archive (74mo)        ──┤
    MHRA Shortage Pubs (3,372)           ──┤
    PCA Prescribing (60mo, 348K)         ──┤──► Panel Feature Store ──► RF Model ──► Predictions
    Pharmacy Invoices (real data)        ──┤     (44,363 drug-months)    v6           CSV + pickle
    Brent Crude + Sun Pharma             ──┤     (32+ features)
    BoE Rate + FX Rates                  ──┤
    SSP Register (87 drugs)              ──┤
    GOVUK MHRA RSS feeds (early warn.)   ──┤
    FDA Warning Letters (early warn.)    ──┤
    CPE Shortage News (early warn.)      ──┤
    MIMS Shortages (early warn.)         ──┤
    OpenFDA API Cascade Map              ──┤
    Manufacturer Intelligence DB         ──┘
    ```
    """)

    st.markdown("---")
    st.subheader("Version History")
    st.markdown("""
| Version | Key Changes | ROC-AUC | Training Rows |
|---|---|---|---|
| v1 | Basic price + concession features | 0.91 | 8,200 |
| v2 | MHRA mentions, SSP flag | 0.95 | 11,000 |
| v3 | PCA demand, floor proximity | 0.982 | 14,764 |
| v4 | Pharmacy invoices, brent crude | 0.994 | 32,000 |
| v5 | Full PCA (60mo), FX stress, Sun Pharma | 0.998 | 44,363 |
| **v6** | **Early warning signals, API cascade, manufacturer DB** | **0.998** | **44,363+** |
    """)
