"""
NiPharm Stock Intelligence Dashboard
=====================================
Streamlit app — run with:
  cd scrapers && streamlit run app.py

Shows:
  - Top 30 drugs at shortage risk (from ML model)
  - Feature importance chart
  - Historical concession trend
  - Drug detail lookup
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import pickle
from datetime import datetime

# ── Page config
st.set_page_config(
    page_title="NiPharm — Shortage Intelligence",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR  = "data"
MODEL_DIR = "data/model"

# ── Colour map for risk tiers
TIER_COLOURS = {
    "CONFIRMED": "#d62728",
    "RED":       "#ff7f0e",
    "AMBER":     "#ffbb00",
    "YELLOW":    "#bcbd22",
    "GREEN":     "#2ca02c",
}

# ────────────────────────────────────────────
# DATA LOADERS (cached)
# ────────────────────────────────────────────

@st.cache_data
def load_predictions():
    path = f"{MODEL_DIR}/panel_predictions.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df = df.sort_values("shortage_probability", ascending=False)
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


# ────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────

st.sidebar.markdown("### 💊 NiPharm")
st.sidebar.title("NiPharm Intelligence")
st.sidebar.caption(f"Data as of: March 2026")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Top Risk Alerts", "🔍 Drug Lookup", "📈 Concession Trends", "🤖 Model Info"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Model:** Random Forest (panel)")
st.sidebar.markdown("**ROC-AUC:** 0.982")
st.sidebar.markdown("**Training rows:** 14,764")
st.sidebar.markdown("**Drugs:** 754")
st.sidebar.markdown("**Months:** Apr 2021 – Jan 2026")


# ────────────────────────────────────────────
# PAGE 1 — TOP RISK ALERTS
# ────────────────────────────────────────────

if page == "📊 Top Risk Alerts":
    st.title("📊 Shortage Risk Alerts")
    st.caption("Drugs most likely to receive a price concession next month, ranked by ML model probability.")

    predictions = load_predictions()

    if predictions is None:
        st.error("No predictions found. Run `python 12_ml_model_panel.py` in Terminal first.")
        st.stop()

    # ── Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        n_show = st.slider("Show top N drugs", 10, 100, 30)
    with col2:
        min_prob = st.slider("Min probability", 0.0, 1.0, 0.5, 0.05)
    with col3:
        only_new = st.checkbox("Hide already-on-concession", False)

    df = predictions[predictions["shortage_probability"] >= min_prob].head(n_show)
    if only_new and "on_concession" in df.columns:
        df = df[df["on_concession"] == 0]

    # ── Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Drugs at risk (≥50%)", int((predictions["shortage_probability"] >= 0.5).sum()))
    m2.metric("Already on concession", int(predictions["on_concession"].sum()) if "on_concession" in predictions.columns else "—")
    m3.metric("New risk (not on concession)", int(((predictions["shortage_probability"] >= 0.5) & (predictions.get("on_concession", 0) == 0)).sum()))
    m4.metric("Total drugs scored", len(predictions))

    st.markdown("---")

    # ── Table
    display_cols = ["drug_name", "shortage_probability", "floor_proximity",
                    "on_concession", "concession_streak", "conc_last_6mo",
                    "mhra_mention_count"]
    avail_cols = [c for c in display_cols if c in df.columns]

    def colour_prob(val):
        if val >= 0.9:  return "background-color: #ffcccc"
        if val >= 0.7:  return "background-color: #ffe0b2"
        if val >= 0.5:  return "background-color: #fff9c4"
        return ""

    display = df[avail_cols].rename(columns={
        "drug_name": "Drug",
        "shortage_probability": "Risk %",
        "floor_proximity": "Floor Prox.",
        "on_concession": "On Conc.",
        "concession_streak": "Streak (mo)",
        "conc_last_6mo": "Last 6mo",
        "mhra_mention_count": "MHRA Mentions",
    })
    display["Risk %"] = display["Risk %"].map("{:.1%}".format)
    display["Floor Prox."] = display["Floor Prox."].map("{:.2f}".format)

    st.dataframe(display, width="stretch", height=600)

    # ── Download
    csv = df[avail_cols].to_csv(index=False)
    st.download_button("⬇️ Download CSV", csv, "shortage_alerts.csv", "text/csv")


# ────────────────────────────────────────────
# PAGE 2 — DRUG LOOKUP
# ────────────────────────────────────────────

elif page == "🔍 Drug Lookup":
    st.title("🔍 Drug Lookup")
    st.caption("Search for a specific drug to see its full risk profile and price history.")

    panel = load_panel()
    if panel is None:
        st.error("Panel feature store not found.")
        st.stop()

    drug_list = sorted(panel["drug_name"].dropna().unique().tolist())
    selected  = st.selectbox("Select drug", drug_list)

    drug_data = panel[panel["drug_name"] == selected].copy()
    drug_data["month"] = drug_data["month"].astype(str)
    drug_data = drug_data.sort_values("month")

    if len(drug_data) == 0:
        st.warning("No data found.")
        st.stop()

    # ── Summary
    latest = drug_data.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", f"£{latest.get('price_gbp', 0):.4f}")
    c2.metric("Floor Proximity", f"{latest.get('floor_proximity', 1):.2f}",
              help="< 1.0 = below historical floor = critical")
    c3.metric("On Concession Now", "Yes" if latest.get("on_concession", 0) == 1 else "No")
    c4.metric("Concession Streak", f"{int(latest.get('concession_streak', 0))} months")

    st.markdown("---")

    # ── Price chart
    if "price_gbp" in drug_data.columns:
        st.subheader("Price History (£)")
        chart_data = drug_data.set_index("month")[["price_gbp"]].rename(columns={"price_gbp": "Price £"})
        st.line_chart(chart_data)

    # ── Floor proximity chart
    if "floor_proximity" in drug_data.columns:
        st.subheader("Floor Proximity (lower = more risk)")
        fp_data = drug_data.set_index("month")[["floor_proximity"]]
        st.line_chart(fp_data)
        st.caption("Values ≤ 1.15 = within 15% of unprofitable floor (danger zone)")

    # ── Concession history
    if "on_concession" in drug_data.columns:
        conc_months = drug_data[drug_data["on_concession"] == 1]["month"].tolist()
        st.subheader(f"Concession History ({len(conc_months)} months)")
        if conc_months:
            st.write(", ".join(conc_months))
        else:
            st.write("No historical concessions found.")

    # ── Raw data
    with st.expander("Raw data"):
        st.dataframe(drug_data, width="stretch")


# ────────────────────────────────────────────
# PAGE 3 — CONCESSION TRENDS
# ────────────────────────────────────────────

elif page == "📈 Concession Trends":
    st.title("📈 Concession Trends")
    st.caption("Monthly count of NHS price concessions — the primary shortage signal.")

    history = load_concession_history()
    if history is None:
        st.error("CPE archive not found.")
        st.stop()

    # ── Monthly count
    monthly = (
        history.groupby(history["month"].dt.to_period("M"))
        .size()
        .reset_index(name="concession_count")
    )
    monthly["month"] = monthly["month"].astype(str)
    monthly = monthly.sort_values("month")

    st.subheader("Monthly Concession Count (Jan 2020 – Feb 2026)")
    st.bar_chart(monthly.set_index("month")["concession_count"])

    # ── Top chronic drugs
    st.subheader("Most Frequently Conceded Drugs (all time)")
    top_drugs = (
        history.groupby("drug_name")
        .size()
        .reset_index(name="concession_count")
        .sort_values("concession_count", ascending=False)
        .head(20)
    )
    st.bar_chart(top_drugs.set_index("drug_name")["concession_count"])

    # ── Stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Concession Events", f"{len(history):,}")
    col2.metric("Unique Drugs Ever Conceded", history["drug_name"].nunique())
    col3.metric("Months of History", history["month"].dt.to_period("M").nunique())

    with st.expander("View raw CPE archive"):
        st.dataframe(history.head(500), width="stretch")


# ────────────────────────────────────────────
# PAGE 4 — MODEL INFO
# ────────────────────────────────────────────

elif page == "🤖 Model Info":
    st.title("🤖 Model Information")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Performance Metrics")
        st.metric("ROC-AUC (5-fold CV)", "0.982 ± 0.002")
        st.metric("PR-AUC (5-fold CV)", "0.935 ± 0.008")
        st.metric("F1 Score (5-fold CV)", "0.846 ± 0.012")
        st.caption("Trained on 14,764 drug-month rows, 2,187 positive labels (14.8%)")

    fi = load_feature_importance()
    if fi is not None:
        with col2:
            st.subheader("Feature Importance")
            fi_chart = fi.set_index("feature")["importance_pct"]
            st.bar_chart(fi_chart)

    st.markdown("---")
    st.subheader("Model Architecture")
    st.code("""
RandomForestClassifier(
    n_estimators = 300,
    max_depth    = 10,
    min_samples_leaf = 5,
    class_weight = 'balanced',   # handles 85:15 imbalance
    random_state = 42,
    n_jobs       = -1,
)

Training data: panel_feature_store_train.csv
  - 754 unique drugs
  - 23 months (Apr 2021 – Dec 2025)
  - 14,764 drug-month rows
  - 2,187 positives (14.8%)

Target: label_next_month
  = 1 if drug received price concession the following month
    """, language="python")

    st.markdown("---")
    metrics_text = load_cv_metrics()
    if metrics_text:
        with st.expander("Full CV Metrics Report"):
            st.text(metrics_text)
