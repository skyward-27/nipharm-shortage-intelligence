"""
SCRIPT 12: ML Model — Time-Series Panel
========================================
Trains a Random Forest on the drug × month panel (14,764 rows, 2,187 positives).
Target: Will this drug get a price concession NEXT month?

Inputs:  data/features/panel_feature_store_train.csv
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
    "floor_proximity",           # price / rolling floor (lower = more risk)
    "within_15pct_of_floor",     # binary: near unprofitable floor
    "price_mom_pct",             # month-on-month price change %
    "price_yoy_pct",             # year-on-year price change %
    "on_concession",             # was it on concession THIS month
    "concession_streak",         # consecutive months on concession
    "conc_last_6mo",             # times on concession in last 6 months
    "mhra_mention_count",        # MHRA publications about this drug
    "us_shortage_flag",          # matching active US FDA shortage
    "ssp_flag",                  # drug has ever had an SSP (severe shortage)
    "fx_stress_score",           # GBP/INR stress score
    "boe_bank_rate",             # UK base rate
]

TARGET = "label_next_month"


def load_data():
    path = "data/features/panel_feature_store_train.csv"
    df = pd.read_csv(path)
    print(f"Loaded {len(df):,} rows, {df['vmpp_code'].nunique()} drugs, {df[TARGET].sum()} positives ({df[TARGET].mean():.1%})")
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
        f.write(f"NPT Panel Model — CV Metrics\nGenerated: {datetime.now():%Y-%m-%d %H:%M}\n\n")
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
            "on_concession", "concession_streak", "conc_last_6mo", "mhra_mention_count"]
    avail = [c for c in cols if c in latest.columns]
    print(latest[avail].head(30).to_string(index=False))


def run():
    print("="*65)
    print("SCRIPT 12: NPT Shortage Prediction — Panel Model")
    print("="*65)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    df     = load_data()
    X, y   = prepare(df)
    clf, cv = train(X, y)
    save_outputs(clf, cv, df, X)
    print("\nDone.")


if __name__ == "__main__":
    run()
