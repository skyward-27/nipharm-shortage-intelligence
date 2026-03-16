"""
NiPharm Stock Intelligence Dashboard  v2
==========================================
Streamlit app — run with:
  cd scrapers && streamlit run app.py

Pages:
  1. 📊 Top Risk Alerts      — ML predictions with interactive charts
  2. 🔍 Drug Lookup          — per-drug price + concession history
  3. 📈 Concession Trends    — monthly shortage count with date filters
  4. 📡 Market Signals       — Brent crude, FX rates, BoE rate
  5. 🤖 Model Info           — v5 performance metrics + feature importance
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
    page_title="NiPharm — Shortage Intelligence",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR  = "data"
MODEL_DIR = "data/model"

# ── Colour constants ────────────────────────────────────────────────────────────
TIER_COLOUR = {
    "CONFIRMED": "#d62728",
    "HIGH":      "#ff7f0e",
    "MEDIUM":    "#ffbb00",
    "LOW":       "#bcbd22",
    "WATCH":     "#2ca02c",
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
    """Translate risk probability + concession status into a buying recommendation."""
    on_conc = int(on_concession) if pd.notna(on_concession) else 0
    if prob >= 0.90 and not on_conc:
        return "🔴 BUY NOW"        # imminent — not yet priced in
    if prob >= 0.90 and on_conc:
        return "🟠 BUY MORE"       # already conceded, likely to continue
    if prob >= 0.70 and not on_conc:
        return "🟠 BUY AHEAD"      # high risk, accumulate before announcement
    if prob >= 0.70 and on_conc:
        return "🟡 MANAGE STOCK"   # ongoing concession, watch stock levels
    if prob >= 0.50:
        return "🟡 WATCH"          # elevated — monitor weekly
    if prob >= 0.30:
        return "⚪ NORMAL"          # low risk, standard ordering
    return "✅ NO ACTION"           # no signal


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
    df = df.sort_values("date")
    return df

@st.cache_data
def load_fx():
    path = f"{DATA_DIR}/market_signals/fx_rates_stress.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    return df

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


# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 💊 NiPharm")
    st.caption("Shortage Intelligence Platform")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["📊 Top Risk Alerts", "🔍 Drug Lookup",
         "📈 Concession Trends", "📡 Market Signals", "🤖 Model Info"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**Model v5** · Random Forest (panel)")

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


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — TOP RISK ALERTS
# ════════════════════════════════════════════════════════════════════════════════

if page == "📊 Top Risk Alerts":
    st.title("📊 Shortage Risk Alerts")
    st.caption(
        "Drugs most likely to receive a price concession **next month**, "
        "ranked by Random Forest probability (model v5 · ROC-AUC 0.998)."
    )

    predictions = load_predictions()
    if predictions is None:
        st.error("No predictions found. Run `python 12_ml_model_panel.py` in Terminal first.")
        st.stop()

    # ── Filters ────────────────────────────────────────────────────────────────
    with st.expander("⚙️ Filters", expanded=True):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            n_show = st.slider("Show top N drugs", 10, 150, 50)
        with fcol2:
            min_prob = st.slider("Min probability", 0.0, 1.0, 0.30, 0.05)
        with fcol3:
            tier_filter = st.multiselect(
                "Risk tier",
                ["CONFIRMED", "HIGH", "MEDIUM", "LOW", "WATCH"],
                default=["CONFIRMED", "HIGH", "MEDIUM"],
            )
        with fcol4:
            action_filter = st.multiselect(
                "Buy action",
                ["🔴 BUY NOW", "🟠 BUY MORE", "🟠 BUY AHEAD",
                 "🟡 MANAGE STOCK", "🟡 WATCH", "⚪ NORMAL", "✅ NO ACTION"],
                default=[],
                placeholder="All actions",
            )

    only_new = st.checkbox("New risk only (hide already on concession)", False)

    df = predictions[predictions["shortage_probability"] >= min_prob].copy()
    if tier_filter:
        df = df[df["risk_tier"].isin(tier_filter)]
    if action_filter:
        df = df[df["buy_action"].isin(action_filter)]
    if only_new and "on_concession" in df.columns:
        df = df[df["on_concession"] == 0]
    df = df.head(n_show)

    # ── KPI metrics ────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🔴 BUY NOW",
              int((predictions["buy_action"] == "🔴 BUY NOW").sum())
              if "buy_action" in predictions.columns else "—",
              help="≥90% risk, NOT on concession — most urgent")
    m2.metric("🟠 BUY AHEAD",
              int((predictions["buy_action"] == "🟠 BUY AHEAD").sum())
              if "buy_action" in predictions.columns else "—",
              help="≥70% risk, NOT on concession — accumulate now")
    m3.metric("🟠 BUY MORE",
              int((predictions["buy_action"] == "🟠 BUY MORE").sum())
              if "buy_action" in predictions.columns else "—",
              help="≥90% risk, already on concession")
    m4.metric("🟡 WATCH",
              int(predictions["buy_action"].isin(["🟡 WATCH", "🟡 MANAGE STOCK"]).sum())
              if "buy_action" in predictions.columns else "—")
    m5.metric("⚠️  On concession now",
              int(predictions["on_concession"].sum())
              if "on_concession" in predictions.columns else "—")
    m6.metric("📦 Total drugs scored", len(predictions))

    st.markdown("---")

    # ── Chart: horizontal bar ───────────────────────────────────────────────────
    chart_df = df.head(30).copy()
    chart_df["label"] = chart_df["drug_name"].str[:45]
    chart_df["prob_pct"] = (chart_df["shortage_probability"] * 100).round(1)
    chart_df["colour"] = chart_df["risk_tier"].map(TIER_COLOUR)

    fig = px.bar(
        chart_df.sort_values("shortage_probability"),
        x="prob_pct",
        y="label",
        orientation="h",
        color="risk_tier",
        color_discrete_map=TIER_COLOUR,
        labels={"prob_pct": "Shortage Probability (%)", "label": ""},
        title=f"Top {min(30, len(chart_df))} Drugs by Shortage Probability",
        text="prob_pct",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        height=max(400, min(30, len(chart_df)) * 28),
        showlegend=True,
        legend_title_text="Risk Tier",
        xaxis_range=[0, 115],
        margin=dict(l=10, r=30, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Table ───────────────────────────────────────────────────────────────────
    st.subheader(f"Alert Table — {len(df)} drugs")

    # ── Buying guide legend ─────────────────────────────────────────────────────
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

    # ── Downloads ───────────────────────────────────────────────────────────────
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        csv = df[avail_cols].to_csv(index=False)
        st.download_button("⬇️ Download filtered CSV", csv,
                           "shortage_alerts.csv", "text/csv")
    with dcol2:
        high_only = predictions[predictions["shortage_probability"] >= 0.70]
        csv2 = high_only[avail_cols].to_csv(index=False) if len(avail_cols) > 0 else ""
        st.download_button("⬇️ Download HIGH+ only CSV", csv2,
                           "shortage_alerts_high.csv", "text/csv")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — DRUG LOOKUP
# ════════════════════════════════════════════════════════════════════════════════

elif page == "🔍 Drug Lookup":
    st.title("🔍 Drug Lookup")
    st.caption("Drill into any drug — price history, concession timeline and risk score.")

    panel = load_panel()
    predictions = load_predictions()
    pca = load_pca_demand()

    if panel is None:
        st.error("Panel feature store not found.")
        st.stop()

    drug_list = sorted(panel["drug_name"].dropna().unique().tolist())

    # Search box + optional compare
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
    c1.metric("Current Price",
              f"£{latest.get('price_gbp', 0):.4f}")
    c2.metric("Floor Proximity",
              f"{latest.get('floor_proximity', 1):.3f}",
              delta=f"{latest.get('price_mom_pct', 0):+.1f}% MoM",
              delta_color="inverse")
    c3.metric("On Concession",
              "✅ Yes" if latest.get("on_concession", 0) == 1 else "No")
    c4.metric("Concession Streak",
              f"{int(latest.get('concession_streak', 0))} months")
    if pred_row is not None:
        p = pred_row["shortage_probability"]
        tier = pred_row["risk_tier"]
        c5.metric("Shortage Risk",
                  f"{p:.1%}",
                  delta=tier_badge(tier))
    else:
        c5.metric("Shortage Risk", "—")

    st.markdown("---")

    # ── Price + Concession combined chart ───────────────────────────────────────
    st.subheader("Price History & Concession Periods")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Concession periods as shaded rectangles
    conc_months = drug_data[drug_data["on_concession"] == 1]["month"].tolist()
    for m in conc_months:
        fig.add_vrect(
            x0=m - pd.Timedelta(days=15),
            x1=m + pd.Timedelta(days=15),
            fillcolor="rgba(214, 39, 40, 0.15)",
            line_width=0,
            annotation_text="",
        )

    # Price line
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

    # Floor price
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

    # Floor proximity (right axis)
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
        # Danger zone line
        fig.add_hline(y=1.15, line_dash="dot", line_color="orange",
                      annotation_text="Danger zone (1.15)",
                      secondary_y=True)

    # Compare drug overlay
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
            f"Orange dashed = danger zone threshold"
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
            fig2.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("🔴 Red bars = demand spike month (>1.5× rolling average). "
                       "Aggregated across all formulations.")

    # ── Concession history detail ────────────────────────────────────────────────
    st.subheader(f"Concession History")
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


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — CONCESSION TRENDS
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
    k3.metric("Peak month",
              monthly.loc[monthly["count"].idxmax(), "month"].strftime("%b %Y")
              if len(monthly) else "—")
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
    history["year"] = history["month"].dt.year
    history["mo_num"] = history["month"].dt.month
    yoy = history.groupby(["year", "mo_num"]).size().reset_index(name="count")
    yoy["month_name"] = yoy["mo_num"].apply(
        lambda m: ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"][m-1]
    )

    fig2 = px.line(
        yoy[yoy["year"] >= 2021],
        x="month_name",
        y="count",
        color="year",
        markers=True,
        labels={"count": "Concessions", "month_name": "Month", "year": "Year"},
        title="Concessions by month, compared year by year",
        category_orders={"month_name": ["Jan","Feb","Mar","Apr","May","Jun",
                                         "Jul","Aug","Sep","Oct","Nov","Dec"]},
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
# PAGE 4 — MARKET SIGNALS
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
            b2.metric("Stress z-score", f"{latest_brent['stress_zscore']:.2f}",
                      delta="⚠️ Elevated" if latest_brent['stress_zscore'] > 2 else "Normal",
                      delta_color="inverse")
        if "mom_pct" in brent.columns and pd.notna(latest_brent.get("mom_pct")):
            b3.metric("Month-on-month", f"{latest_brent['mom_pct']:+.1f}%",
                      delta_color="inverse")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=brent["date"], y=brent["close"],
            fill="tozeroy",
            line=dict(color="#1f77b4", width=1.5),
            fillcolor="rgba(31,119,180,0.15)",
            hovertemplate="$%{y:.2f}/bbl<br>%{x|%d %b %Y}<extra></extra>",
            name="Brent $",
        ))
        # Highlight stress periods
        if "stress_zscore" in brent.columns:
            stressed = brent[brent["stress_zscore"] > 2]
            fig.add_trace(go.Scatter(
                x=stressed["date"], y=stressed["close"],
                mode="markers",
                marker=dict(color="#d62728", size=4),
                name="High stress (z>2)",
                hovertemplate="STRESS $%{y:.2f}<extra></extra>",
            ))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                          hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("60% of UK generic APIs sourced from Indian manufacturers — "
                   "high Brent = elevated transport + energy cost.")
    else:
        st.warning("Brent data not found. Run `python 16_yfinance_signals.py`.")

    st.markdown("---")

    # ── FX Rates ────────────────────────────────────────────────────────────────
    st.subheader("💱 FX Rates — GBP vs India / China / USD")
    if fx is not None:
        fx_latest = fx.iloc[-1]
        f1, f2, f3 = st.columns(3)
        f1.metric("GBP/INR",   f"{fx_latest.get('gbp_inr', '—'):.2f}" if pd.notna(fx_latest.get('gbp_inr')) else "—")
        f2.metric("GBP/CNY",   f"{fx_latest.get('gbp_cny', '—'):.2f}" if pd.notna(fx_latest.get('gbp_cny')) else "—")
        f3.metric("GBP/USD",   f"{fx_latest.get('gbp_usd', '—'):.2f}" if pd.notna(fx_latest.get('gbp_usd')) else "—")

        fx_cols = [(c, name) for c, name in [
            ("gbp_inr", "GBP/INR"),
            ("gbp_cny", "GBP/CNY"),
            ("gbp_usd", "GBP/USD"),
        ] if c in fx.columns]

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
        st.caption("GBP weakening vs INR = Indian API manufacturers receive less per unit sold to UK "
                   "→ margin squeeze → supply reduction signal.")
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
# PAGE 5 — MODEL INFO
# ════════════════════════════════════════════════════════════════════════════════

elif page == "🤖 Model Info":
    st.title("🤖 Model v5 — Technical Details")

    # ── Metrics ──────────────────────────────────────────────────────────────────
    st.subheader("Cross-Validation Performance (5-fold stratified)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ROC-AUC", "0.998 ± 0.000", delta="↑ vs v3 (0.982)")
    m2.metric("PR-AUC",  "0.990 ± 0.001", delta="↑ vs v3 (0.936)")
    m3.metric("F1 Score", "0.932 ± 0.004", delta="↑ vs v3 (0.845)")
    m4.metric("Training rows", "44,363", delta="+29,599 vs v3 (14,764)")

    st.caption(
        "v5 improvements: full 60-month PCA prescribing data (348,610 rows), "
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
        | **Regulatory** | `mhra_mention_count` (0.8%), `ssp_flag` (0.3%) | Active shortage publications |
        | **Supply chain** | `sunpharma_stress` (0.9%), `fx_stress_score` (0.2%) | India-specific cost signals |
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

**Future: gradient boosting**
- XGBoost/LightGBM may squeeze +0.1% on edge cases
- Worth benchmarking when panel extends to 5+ years
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
    NHSBSA Drug Tariff (25 files) ──┐
    CPE Concession Archive (74mo)  ──┤
    MHRA Shortage Pubs (3,372)     ──┤──► Panel Feature Store ──► RF Model ──► Predictions
    PCA Prescribing (60mo, 348K)   ──┤     (44,363 drug-months)    v5           CSV + pickle
    Pharmacy Invoices (real data)  ──┤     (32 features)
    Brent Crude + Sun Pharma       ──┤
    BoE Rate + FX Rates            ──┤
    SSP Register (87 drugs)        ──┘
    ```
    """)
