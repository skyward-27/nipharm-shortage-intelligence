"""
SCRIPT 10: NPT Shortage Prediction ML Model
============================================
Trains a Random Forest classifier on the feature store to predict
which generic drugs will receive a price concession (= shortage event)
in the next 1-3 months.

Inputs:   data/features/feature_store.csv
Outputs:  data/model/model.pkl                — trained model
          data/model/predictions.csv          — all 758 molecules scored
          data/model/feature_importance.csv   — ranked feature contributions
          data/model/cv_metrics.txt           — cross-validation performance

Usage:
    python 10_ml_model.py              # Train + predict
    python 10_ml_model.py --predict    # Score only (use saved model)
"""

import pandas as pd
import numpy as np
import os
import sys
import pickle
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder

MODEL_DIR = "data/model"
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURES = [
    "floor_proximity",          # Core: price / historical floor (lower = more risk)
    "within_15pct_of_floor",    # Binary flag: at or near unprofitable floor
    "price_change_pct",         # Price trend over 24 months (falling = risk)
    "mhra_mention_count",       # MHRA publications mentioning this drug
    "us_shortage_flag",         # Matching active US FDA shortage
    "fx_stress_score",          # GBP/INR stress (higher = import costs up)
    "boe_bank_rate",            # UK base rate (macro risk environment)
]

TARGET = "is_shortage_label"


def load_features() -> pd.DataFrame:
    path = "data/features/feature_store.csv"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Feature store not found: {path}. Run 09_feature_store_builder.py first.")
    df = pd.read_csv(path)
    print(f"Loaded {len(df):,} molecules from feature store")
    return df


def prepare_data(df: pd.DataFrame):
    """Clean and split into X, y. Returns X, y, feature_names."""
    # Encode boolean
    df = df.copy()
    df["within_15pct_of_floor"] = df["within_15pct_of_floor"].astype(int)

    # Fill any remaining nulls with median
    for col in FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    available = [f for f in FEATURES if f in df.columns]
    X = df[available].values
    y = df[TARGET].values
    return X, y, available


def train_and_evaluate(X, y, feature_names: list) -> dict:
    """
    Train Random Forest with 5-fold stratified CV.
    Returns best model + metrics.
    """
    print("\n" + "=" * 60)
    print("MODEL TRAINING — 5-Fold Stratified Cross-Validation")
    print("=" * 60)

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        class_weight="balanced",   # handles 1:4 imbalance
        random_state=42,
        n_jobs=-1,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        clf, X, y, cv=cv,
        scoring=["roc_auc", "average_precision", "f1"],
        return_train_score=True,
    )

    print(f"\n  ROC-AUC   (test):  {cv_results['test_roc_auc'].mean():.3f} ± {cv_results['test_roc_auc'].std():.3f}")
    print(f"  PR-AUC    (test):  {cv_results['test_average_precision'].mean():.3f} ± {cv_results['test_average_precision'].std():.3f}")
    print(f"  F1        (test):  {cv_results['test_f1'].mean():.3f} ± {cv_results['test_f1'].std():.3f}")
    print(f"  ROC-AUC   (train): {cv_results['train_roc_auc'].mean():.3f} ± {cv_results['train_roc_auc'].std():.3f}")

    # Train final model on all data
    print("\n  Training final model on full dataset...")
    clf.fit(X, y)

    return {
        "model":      clf,
        "cv_results": cv_results,
        "feature_names": feature_names,
    }


def make_predictions(model, X, df: pd.DataFrame, feature_names: list) -> pd.DataFrame:
    """Score all molecules and return ranked predictions."""
    proba = model.predict_proba(X)[:, 1]
    pred  = model.predict(X)

    results = df[["vmpp_code", "drug_name", "pack_size",
                   "price_gbp", "floor_proximity", "risk_tier",
                   "is_shortage_label"]].copy()
    results["shortage_probability"] = proba.round(4)
    results["predicted_shortage"]   = pred
    results["prediction_correct"]   = (pred == df[TARGET].values).astype(int)

    # Add key features for transparency
    for f in ["within_15pct_of_floor", "mhra_mention_count", "us_shortage_flag", "price_change_pct"]:
        if f in df.columns:
            results[f] = df[f].values

    results = results.sort_values("shortage_probability", ascending=False)
    return results


def feature_importance_report(model, feature_names: list) -> pd.DataFrame:
    """Extract and rank feature importances."""
    fi = pd.DataFrame({
        "feature":    feature_names,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi["importance_pct"] = (fi["importance"] * 100).round(1)
    return fi


def print_top_predictions(predictions: pd.DataFrame, n: int = 30):
    print("\n" + "=" * 90)
    print(f"TOP {n} MOLECULES BY PREDICTED SHORTAGE PROBABILITY")
    print("=" * 90)
    top = predictions.head(n)[[
        "drug_name", "pack_size", "shortage_probability",
        "floor_proximity", "within_15pct_of_floor",
        "mhra_mention_count", "us_shortage_flag",
        "risk_tier", "is_shortage_label"
    ]]
    # Rename for display
    top = top.rename(columns={
        "shortage_probability": "prob",
        "floor_proximity":      "floor_prox",
        "within_15pct_of_floor": "near_floor",
        "mhra_mention_count":   "mhra_n",
        "us_shortage_flag":     "us_flag",
        "is_shortage_label":    "confirmed",
    })
    print(top.to_string(index=False))


def save_metrics(cv_results: dict, feature_importance: pd.DataFrame, predictions: pd.DataFrame):
    """Write a human-readable metrics report."""
    path = f"{MODEL_DIR}/cv_metrics.txt"
    with open(path, "w") as f:
        f.write(f"NPT Shortage Prediction Model — Metrics Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("CROSS-VALIDATION PERFORMANCE (5-fold stratified)\n")
        f.write("-" * 40 + "\n")
        for metric in ["roc_auc", "average_precision", "f1"]:
            test_scores = cv_results[f"test_{metric}"]
            f.write(f"  {metric:25s}: {test_scores.mean():.3f} ± {test_scores.std():.3f}\n")

        f.write("\n\nFEATURE IMPORTANCE RANKING\n")
        f.write("-" * 40 + "\n")
        for _, row in feature_importance.iterrows():
            bar = "█" * int(row["importance_pct"] / 2)
            f.write(f"  {row['feature']:30s} {row['importance_pct']:5.1f}%  {bar}\n")

        f.write("\n\nPREDICTION SUMMARY\n")
        f.write("-" * 40 + "\n")
        confirmed_correct = predictions[(predictions["is_shortage_label"] == 1) &
                                         (predictions["predicted_shortage"] == 1)]
        all_confirmed     = predictions[predictions["is_shortage_label"] == 1]
        f.write(f"  Total molecules scored:       {len(predictions):,}\n")
        f.write(f"  Predicted shortage:           {predictions['predicted_shortage'].sum():,}\n")
        f.write(f"  Known shortage labels:        {all_confirmed['is_shortage_label'].sum():,}\n")
        f.write(f"  Known shortages caught:       {len(confirmed_correct):,} / {len(all_confirmed):,} "
                f"({len(confirmed_correct)/len(all_confirmed)*100:.0f}% recall)\n")

        # Precision in top-50
        top50 = predictions.head(50)
        prec50 = top50["is_shortage_label"].mean()
        f.write(f"\n  Precision in top 50 alerts:  {prec50:.1%}\n")
        f.write(f"  (i.e. {prec50:.1%} of the top 50 predictions are confirmed shortages)\n")

    print(f"\n  Metrics saved: {path}")
    return path


def run():
    print("=" * 60)
    print("NPT Shortage Prediction Model")
    print("=" * 60)

    predict_only = "--predict" in sys.argv

    # Load data
    df = load_features()
    X, y, feature_names = prepare_data(df)
    print(f"Features: {feature_names}")
    print(f"Positive labels: {y.sum()} / {len(y)} ({y.mean():.1%})")

    model_path = f"{MODEL_DIR}/model.pkl"

    if predict_only and os.path.exists(model_path):
        print("\nLoading saved model for prediction...")
        with open(model_path, "rb") as f:
            saved = pickle.load(f)
        model        = saved["model"]
        feature_names = saved["feature_names"]
        cv_results   = saved.get("cv_results", {})
    else:
        # Train
        result    = train_and_evaluate(X, y, feature_names)
        model     = result["model"]
        cv_results = result["cv_results"]

        # Save model
        with open(model_path, "wb") as f:
            pickle.dump({"model": model, "feature_names": feature_names, "cv_results": cv_results}, f)
        print(f"\n  Model saved: {model_path}")

    # Feature importance
    fi = feature_importance_report(model, feature_names)
    fi.to_csv(f"{MODEL_DIR}/feature_importance.csv", index=False)
    print("\nFEATURE IMPORTANCE:")
    for _, row in fi.iterrows():
        bar = "█" * int(row["importance_pct"] / 2)
        print(f"  {row['feature']:32s} {row['importance_pct']:5.1f}%  {bar}")

    # Predictions
    predictions = make_predictions(model, X, df, feature_names)
    predictions.to_csv(f"{MODEL_DIR}/predictions.csv", index=False)
    print(f"\n  All predictions saved: {MODEL_DIR}/predictions.csv")

    # Metrics report
    metrics_path = save_metrics(cv_results, fi, predictions)

    # Print top predictions
    print_top_predictions(predictions, n=30)

    # Summary stats
    top50 = predictions.head(50)
    prec50 = top50["is_shortage_label"].mean()
    all_confirmed = predictions[predictions["is_shortage_label"] == 1]
    caught = predictions.head(50)[predictions.head(50)["is_shortage_label"] == 1]
    roc = cv_results.get("test_roc_auc", [0]).mean() if cv_results else 0

    print("\n" + "=" * 60)
    print("MODEL SUMMARY")
    print("=" * 60)
    print(f"  ROC-AUC (5-fold CV):         {roc:.3f}")
    print(f"  Total molecules scored:      {len(predictions):,}")
    print(f"  Predicted shortages:         {predictions['predicted_shortage'].sum():,}")
    print(f"  Confirmed shortages (labels): {all_confirmed['is_shortage_label'].sum():,}")
    print(f"  Precision in top 50:         {prec50:.1%}")
    print(f"  Confirmed shortages in top 50: {len(caught)} / {len(all_confirmed)} labelled")

    return predictions


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
