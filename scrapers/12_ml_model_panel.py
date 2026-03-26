"""
SCRIPT 12: ML Model — Time-Series Panel  (v6)
==============================================
Trains a Random Forest on the drug × month panel (14,764 rows, 2,187 positives).
Target: Will this drug get a price concession NEXT month?

v6 adds 7 new features from scripts 18/19/20:
  - api_cascade_on_concession  (how many cascade drugs already on concession)
  - api_cascade_count          (how many drugs share same API)
  - api_india_dependency       (binary: ≥60% India/China sourced API)
  - api_cascade_us_shortage    (active US shortage for this API)
  - govuk_mhra_mentions_30d    (MHRA publications last 30 days)
  - cpe_concession_flag        (CPE news flagged this drug)
  - early_warning_score        (composite early-warning signal)

Inputs:  data/features/panel_feature_store_train.csv
         data/early_warning/api_cascade_features.csv   (script 19)
         data/early_warning/early_warning_features.csv  (script 18)
Outputs: data/model/panel_model.pkl
         data/model/panel_predictions.csv
         data/model/panel_feature_importance.csv
         data/model/panel_cv_metrics.txt

Run directly in Terminal (not via Claude Code to avoid memory issues):
  cd scrapers && python 12_ml_model_panel.py
"""

import pandas as pd
import numpy as np
import os, pickle
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report

MODEL_DIR = "data/model"
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURES = [
    # ── Core price signals ───────────────────────────────────────────────────
    "floor_proximity",           # price / rolling floor (lower = more risk)
    "within_15pct_of_floor",     # binary: near unprofitable floor
    "price_mom_pct",             # month-on-month price change %
    "price_yoy_pct",             # year-on-year price change %
    # ── Concession history ──────────────────────────────────────────────────
    "on_concession",             # was it on concession THIS month
    "concession_streak",         # consecutive months on concession
    "conc_last_6mo",             # times on concession in last 6 months
    # ── MHRA / regulatory ───────────────────────────────────────────────────
    "mhra_mention_count",        # MHRA publications about this drug (historical)
    "govuk_mhra_mentions_30d",   # NEW(18): MHRA alert in last 30 days
    "cpe_concession_flag",       # NEW(18): CPE news feed flagged this drug
    "early_warning_score",       # NEW(18): composite early-warning signal
    # ── US shortage leading indicator ───────────────────────────────────────
    "us_shortage_flag",          # matching active US FDA shortage (script 05)
    "api_cascade_us_shortage",   # NEW(19): active US shortage for this drug's API
    # ── API supply chain risk ────────────────────────────────────────────────
    "api_cascade_count",         # NEW(19): drugs sharing same API (cascade exposure)
    "api_cascade_on_concession", # NEW(19): of those cascade drugs, how many on conc now
    "api_india_dependency",      # NEW(19): binary — API ≥60% India/China sourced
    # ── SSP / severe shortage ───────────────────────────────────────────────
    "ssp_flag",                  # drug has ever had an SSP (severe shortage)
    # ── Macro cost environment ──────────────────────────────────────────────
    "fx_stress_score",           # GBP/INR stress score
    "boe_bank_rate",             # UK base rate
    "brent_stress",              # Brent crude z-score (packaging/logistics cost pressure)
    "sunpharma_stress",          # Sun Pharma stock z-score (India API supply proxy)
    "brent_mom_pct",             # Brent crude 1-month % change
    # ── PCA demand signal (script 13) — zero-filled if not available ────────
    "items_mom_pct",             # prescription volume MoM change %
    "demand_spike",              # binary: Rx volume surge >20%
    "demand_trend_6mo",          # 6-month linear trend in Rx volumes
    # ── Pharmacy invoice signals — zero-filled if not available ────────────
    "pharmacy_over_tariff",      # 1 if pharmacy ever paid over NHS tariff for this drug
    "pharmacy_unit_price",       # actual price pharmacy paid (vs NHS tariff)
]

TARGET = "label_next_month"


def load_enrichment_features() -> pd.DataFrame:
    """
    Load and merge drug-level enrichment features from scripts 18 and 19.
    Returns a DataFrame keyed on drug_name with new feature columns.
    All columns filled with 0 if file is missing (model degrades gracefully).
    """
    enriched = None

    # Script 19: API cascade features
    cascade_path = "data/early_warning/api_cascade_features.csv"
    if os.path.exists(cascade_path):
        cas = pd.read_csv(cascade_path)
        # rename us_shortage_active → api_cascade_us_shortage (avoid clash with existing flag)
        cas = cas.rename(columns={"api_us_shortage_active": "api_cascade_us_shortage"})
        keep = ["drug_name", "api_cascade_count", "api_cascade_on_concession",
                "api_india_dependency", "api_cascade_us_shortage"]
        cas = cas[[c for c in keep if c in cas.columns]]
        enriched = cas
        print(f"  Cascade features: {len(cas)} drugs")
    else:
        print(f"  WARNING: {cascade_path} not found — cascade features zeroed")

    # Script 18: Early warning features
    ew_path = "data/early_warning/early_warning_features.csv"
    if os.path.exists(ew_path):
        ew = pd.read_csv(ew_path)
        keep = ["drug_name", "govuk_mhra_mentions_30d", "cpe_concession_flag", "early_warning_score"]
        ew = ew[[c for c in keep if c in ew.columns]]
        if enriched is not None:
            enriched = enriched.merge(ew, on="drug_name", how="left")
        else:
            enriched = ew
        print(f"  Early warning features: {len(ew)} drugs (rest zeroed)")
    else:
        print(f"  WARNING: {ew_path} not found — early warning features zeroed")

    return enriched if enriched is not None else pd.DataFrame()


def load_data():
    path = "data/features/panel_feature_store_train.csv"
    df = pd.read_csv(path)
    print(f"Loaded {len(df):,} rows, {df['vmpp_code'].nunique()} drugs, {df[TARGET].sum()} positives ({df[TARGET].mean():.1%})")

    # Merge enrichment features from scripts 18 / 19
    print("\nLoading enrichment features (scripts 18/19):")
    enriched = load_enrichment_features()
    if not enriched.empty and "drug_name" in df.columns:
        before = len(df)
        df = df.merge(enriched, on="drug_name", how="left")
        assert len(df) == before, "Merge changed row count — check for duplicate drug_names in enrichment"
        # Fill new feature columns with 0 for drugs not in enrichment files
        new_cols = [c for c in enriched.columns if c != "drug_name"]
        df[new_cols] = df[new_cols].fillna(0)
        print(f"  Merged. New columns: {new_cols}")
    else:
        print("  No enrichment features merged (zeroed in model).")

    return df


def prepare(df):
    df = df.copy()
    for col in FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = 0
    X = df[FEATURES].values
    y = df[TARGET].values
    return X, y


def train(X, y):
    print("\n5-Fold Stratified Cross-Validation...")
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        clf, X, y, cv=cv,
        scoring=["roc_auc", "average_precision", "f1"],
        return_train_score=True,
    )
    print(f"  ROC-AUC  : {cv_results['test_roc_auc'].mean():.3f} ± {cv_results['test_roc_auc'].std():.3f}")
    print(f"  PR-AUC   : {cv_results['test_average_precision'].mean():.3f} ± {cv_results['test_average_precision'].std():.3f}")
    print(f"  F1       : {cv_results['test_f1'].mean():.3f} ± {cv_results['test_f1'].std():.3f}")

    print("Training final model on full dataset...")
    clf.fit(X, y)
    return clf, cv_results


def save_outputs(clf, cv_results, df, X):
    # Feature importance
    fi = pd.DataFrame({"feature": FEATURES, "importance": clf.feature_importances_})
    fi = fi.sort_values("importance", ascending=False)
    fi["importance_pct"] = (fi["importance"] * 100).round(1)
    fi.to_csv(f"{MODEL_DIR}/panel_feature_importance.csv", index=False)
    print("\nFeature Importance:")
    for _, r in fi.iterrows():
        bar = "█" * int(r["importance_pct"] / 2)
        print(f"  {r['feature']:30s} {r['importance_pct']:5.1f}%  {bar}")

    # Predictions on latest month
    latest = df[df["month"] == df["month"].max()].copy()
    for col in FEATURES:
        if col not in latest.columns:
            latest[col] = 0
    X_latest = latest[FEATURES].fillna(0).values
    latest["shortage_probability"] = clf.predict_proba(X_latest)[:, 1].round(4)
    latest["predicted_shortage"] = clf.predict(X_latest)
    latest = latest.sort_values("shortage_probability", ascending=False)
    latest.to_csv(f"{MODEL_DIR}/panel_predictions.csv", index=False)

    # Metrics report
    roc = cv_results["test_roc_auc"].mean()
    pr  = cv_results["test_average_precision"].mean()
    f1  = cv_results["test_f1"].mean()
    with open(f"{MODEL_DIR}/panel_cv_metrics.txt", "w") as f:
        f.write(f"NPT Panel Model v6 — CV Metrics\nGenerated: {datetime.now():%Y-%m-%d %H:%M}\n\n")
        f.write(f"ROC-AUC            : {roc:.3f}\n")
        f.write(f"PR-AUC             : {pr:.3f}\n")
        f.write(f"F1                 : {f1:.3f}\n\n")
        f.write("Feature Importance:\n")
        for _, r in fi.iterrows():
            f.write(f"  {r['feature']:30s} {r['importance_pct']:5.1f}%\n")

    # Save model
    with open(f"{MODEL_DIR}/panel_model.pkl", "wb") as f:
        pickle.dump({"model": clf, "features": FEATURES, "cv": cv_results}, f)
    print(f"\nModel saved: {MODEL_DIR}/panel_model.pkl")

    # Top 30 predictions
    print("\n" + "="*80)
    print("TOP 30 DRUGS AT RISK NEXT MONTH")
    print("="*80)
    cols = ["drug_name", "month", "shortage_probability", "floor_proximity",
            "on_concession", "concession_streak", "conc_last_6mo", "mhra_mention_count",
            "api_cascade_on_concession", "cpe_concession_flag", "govuk_mhra_mentions_30d"]
    avail = [c for c in cols if c in latest.columns]
    print(latest[avail].head(30).to_string(index=False))


def run():
    print("="*65)
    print("SCRIPT 12: NPT Shortage Prediction — Panel Model v6")
    print("="*65)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    df     = load_data()
    X, y   = prepare(df)
    clf, cv = train(X, y)
    save_outputs(clf, cv, df, X)
    print("\nDone.")


if __name__ == "__main__":
    run()
