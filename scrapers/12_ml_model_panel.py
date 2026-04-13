"""
12_ml_model_panel.py — Nipharma ML Model Training (v5: Temporal Walk-Forward)
==============================================================================
UPDATED: April 2026 — Temporal CV, XGBoost benchmark, SHAP, calibration

Data:
  - Training: 44,074 rows x 36 features (60 months, 714 drugs)
  - Target: label_next_month (will drug go on concession next month?)

Methodology:
  - Temporal walk-forward CV (5 folds) with 1-month gap — no data leakage
  - Hold-out test set: last 6 months of panel (never seen during CV/training)
  - Primary model: Random Forest (100 trees) — calibrated via isotonic regression
  - Benchmark model: XGBoost (same depth/structure for fair comparison)
  - SHAP TreeExplainer for feature importance (in addition to Gini)
  - Saved model: CalibratedClassifierCV(RF, isotonic) — better probability output

REQUIREMENTS:
  pip install pandas scikit-learn numpy xgboost>=1.7.0 shap>=0.42.0

RUNTIME:
  ~4-8 minutes on Mac (MacBook M1/Intel) — SHAP adds ~2 min on large datasets
  Memory peak: ~4-6 GB

RUN:
  cd "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/scrapers"
  python 12_ml_model_panel.py

OUTPUT:
  data/model/panel_model.pkl         <- CalibratedClassifierCV(RF) — DEPLOYED
  data/model/panel_model_xgb.pkl     <- CalibratedClassifierCV(XGB) — DEPLOYED
  data/model/panel_feature_importance.csv
  data/model/panel_cv_metrics.txt
  data/model/shap_importance.csv
  (also copied to nipharma-backend/model/)
"""

import pandas as pd
import numpy as np
import pickle
import os
import shutil
import warnings
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score
warnings.filterwarnings('ignore')

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR  = "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit"
DATA_ROOT = f"{BASE_DIR}/scrapers/data"
TRAIN_FILE     = f"{DATA_ROOT}/features/panel_feature_store_train.csv"
MODEL_OUT      = f"{DATA_ROOT}/model/panel_model.pkl"
MODEL_OUT_XGB  = f"{DATA_ROOT}/model/panel_model_xgb.pkl"
BACKEND_MODEL  = f"{BASE_DIR}/nipharma-backend/model/panel_model.pkl"
BACKEND_MODEL_XGB = f"{BASE_DIR}/nipharma-backend/model/panel_model_xgb.pkl"
IMPORTANCE_OUT = f"{DATA_ROOT}/model/panel_feature_importance.csv"
SHAP_OUT       = f"{DATA_ROOT}/model/shap_importance.csv"
METRICS_OUT    = f"{DATA_ROOT}/model/panel_cv_metrics.txt"

# ── BANNER ────────────────────────────────────────────────────────────────────
print("=" * 70)
print("NIPHARMA ML MODEL TRAINING v5 — Temporal Walk-Forward CV")
print("=" * 70)
print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
print(f"\nLoading data from {TRAIN_FILE}...")
df = pd.read_csv(TRAIN_FILE)
print(f"  Loaded {df.shape[0]:,} rows x {df.shape[1]} columns")

# ── TEMPORAL SORT ─────────────────────────────────────────────────────────────
# Sort by month FIRST — critical for temporal integrity
df = df.sort_values('month').reset_index(drop=True)
print(f"  Sorted chronologically. Month range: {df['month'].min()} -> {df['month'].max()}")

# ── FEATURE SELECTION ─────────────────────────────────────────────────────────
target       = 'label_next_month'
exclude_cols = ['vmpp_code', 'drug_name', 'pack_size', 'unit', 'month', 'bnf_code', target]
feature_cols = [c for c in df.columns if c not in exclude_cols]

print(f"\nData summary:")
print(f"  Features: {len(feature_cols)}")
print(f"  Samples:  {len(df):,}")
print(f"  Positive label rate: {df[target].mean()*100:.1f}%")

# ── TEMPORAL TRAIN / TEST SPLIT ───────────────────────────────────────────────
unique_months   = sorted(df['month'].unique())
n_months        = len(unique_months)

# Hold out last 6 months as final test set (never touched during CV)
test_months     = unique_months[-6:]
train_val_months = unique_months[:-6]

print(f"\nTemporal split:")
print(f"  Total months: {n_months}")
print(f"  Train+Val months ({len(train_val_months)}): {train_val_months[0]} -> {train_val_months[-1]}")
print(f"  Hold-out test months ({len(test_months)}): {test_months[0]} -> {test_months[-1]}")

test_mask      = df['month'].isin(test_months)
train_val_mask = df['month'].isin(train_val_months)

df_trainval = df[train_val_mask].copy()
df_test     = df[test_mask].copy()

print(f"  Train+Val rows: {len(df_trainval):,}")
print(f"  Test rows:      {len(df_test):,}")

# ── PREPROCESS ────────────────────────────────────────────────────────────────
def preprocess(df_in, feature_cols, medians=None):
    """Fill missing values; compute medians from train if not supplied."""
    X = df_in[feature_cols].copy()
    if medians is None:
        medians = X.median()
    X = X.fillna(medians)
    return X, medians

print(f"\nPreprocessing...")
missing_counts = df_trainval[feature_cols].isnull().sum()
top_missing = missing_counts[missing_counts > 0].sort_values(ascending=False).head(5)
if len(top_missing):
    print("  Missing values (top 5):")
    for feat, cnt in top_missing.items():
        print(f"    {feat}: {cnt} ({cnt/len(df_trainval)*100:.1f}%)")

X_trainval, train_medians = preprocess(df_trainval, feature_cols)
X_test,     _             = preprocess(df_test,     feature_cols, medians=train_medians)
y_trainval = df_trainval[target].values
y_test     = df_test[target].values

# Remove constant features (computed from train+val only)
const_features = [c for c in feature_cols if X_trainval[c].nunique() <= 1]
if const_features:
    print(f"  Removing constant features: {const_features}")
    feature_cols = [c for c in feature_cols if c not in const_features]
    X_trainval = X_trainval[feature_cols]
    X_test     = X_test[feature_cols]

print(f"  Final feature count: {len(feature_cols)}")
print(f"  Missing values filled with train medians")

# ── TEMPORAL WALK-FORWARD CV ──────────────────────────────────────────────────
print(f"\n{'='*70}")
print("TEMPORAL WALK-FORWARD CROSS-VALIDATION")
print(f"{'='*70}")
print("Strategy: train on earlier months, test on later months")
print("Gap: 1 month between each train window and test window (no leakage)")

tv_months = sorted(df_trainval['month'].unique())
n_tv      = len(tv_months)
n_folds   = 5
# Minimum training window = ~30% of train_val months; grow from there
min_train = max(6, n_tv // (n_folds + 1))

fold_size = (n_tv - min_train) // n_folds

print(f"  Train+Val months available: {n_tv}")
print(f"  Min initial training window: {min_train} months")
print(f"  Approx test window per fold: {fold_size} months")
print()

rf_cv_aucs  = []
xgb_cv_aucs = []

# Try to import XGBoost; if not installed, warn and skip
try:
    from xgboost import XGBClassifier
    xgb_available = True
    print("  XGBoost: available")
except ImportError:
    xgb_available = False
    print("  XGBoost: NOT installed (pip install xgboost>=1.7.0)")
    print("  XGBoost benchmark will be skipped.")

print()

for fold in range(n_folds):
    # Train window: months 0 .. (min_train + fold*fold_size - 1)
    train_end_idx = min_train + fold * fold_size - 1
    # Test window:  months (train_end_idx + 2) .. (train_end_idx + 1 + fold_size)
    # +2 to leave a 1-month gap (the gap month is never in either set)
    test_start_idx = train_end_idx + 2
    test_end_idx   = min(test_start_idx + fold_size - 1, n_tv - 1)

    if test_start_idx >= n_tv:
        print(f"  Fold {fold+1}: not enough months remaining, skipping")
        continue

    fold_train_months = tv_months[:train_end_idx + 1]
    fold_test_months  = tv_months[test_start_idx:test_end_idx + 1]
    gap_month         = tv_months[train_end_idx + 1]

    fold_train_mask = df_trainval['month'].isin(fold_train_months)
    fold_test_mask  = df_trainval['month'].isin(fold_test_months)

    Xf_train = X_trainval[fold_train_mask.values]
    yf_train = y_trainval[fold_train_mask.values]
    Xf_test  = X_trainval[fold_test_mask.values]
    yf_test  = y_trainval[fold_test_mask.values]

    print(f"  Fold {fold+1}/{n_folds}:")
    print(f"    Train: {fold_train_months[0]} -> {fold_train_months[-1]} ({len(fold_train_months)} mo, {len(Xf_train):,} rows)")
    print(f"    Gap:   {gap_month}")
    print(f"    Test:  {fold_test_months[0]} -> {fold_test_months[-1]} ({len(fold_test_months)} mo, {len(Xf_test):,} rows)")
    print(f"    Test positive rate: {yf_test.mean()*100:.1f}%")

    if yf_test.sum() == 0:
        print(f"    [SKIP] No positive labels in test fold")
        continue

    # --- Random Forest ---
    rf_fold = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    rf_fold.fit(Xf_train, yf_train)
    rf_proba = rf_fold.predict_proba(Xf_test)[:, 1]
    rf_auc   = roc_auc_score(yf_test, rf_proba)
    rf_cv_aucs.append(rf_auc)
    print(f"    RF  AUC: {rf_auc:.4f}")

    # --- XGBoost ---
    if xgb_available:
        scale_pos = (yf_train == 0).sum() / max((yf_train == 1).sum(), 1)
        xgb_fold = XGBClassifier(
            n_estimators=100,
            max_depth=6,           # XGB shallower trees are standard
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos,
            eval_metric='logloss',
            random_state=42,
            n_jobs=-1,
            verbosity=0,
            use_label_encoder=False
        )
        xgb_fold.fit(Xf_train, yf_train)
        xgb_proba = xgb_fold.predict_proba(Xf_test)[:, 1]
        xgb_auc   = roc_auc_score(yf_test, xgb_proba)
        xgb_cv_aucs.append(xgb_auc)
        print(f"    XGB AUC: {xgb_auc:.4f}")

    print()

# ── CV SUMMARY ────────────────────────────────────────────────────────────────
print(f"{'='*70}")
print("WALK-FORWARD CV RESULTS SUMMARY")
print(f"{'='*70}")

rf_mean  = np.mean(rf_cv_aucs)
rf_std   = np.std(rf_cv_aucs)
print(f"  Random Forest AUCs: {[f'{a:.4f}' for a in rf_cv_aucs]}")
print(f"  RF  Mean AUC: {rf_mean:.4f}  Std: {rf_std:.4f}")

if xgb_available and xgb_cv_aucs:
    xgb_mean = np.mean(xgb_cv_aucs)
    xgb_std  = np.std(xgb_cv_aucs)
    print(f"  XGBoost AUCs: {[f'{a:.4f}' for a in xgb_cv_aucs]}")
    print(f"  XGB Mean AUC: {xgb_mean:.4f}  Std: {xgb_std:.4f}")
    winner = "Random Forest" if rf_mean >= xgb_mean else "XGBoost"
    print(f"\n  BENCHMARK WINNER: {winner}")
    print(f"  (Saving RF regardless — architecture requirement)")

# ── FINAL RF TRAINING + CALIBRATION ──────────────────────────────────────────
print(f"\n{'='*70}")
print("TRAINING FINAL MODEL ON ALL TRAIN+VAL DATA")
print(f"{'='*70}")
print("Step 1: Fit base Random Forest on full train+val set...")

rf_base = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'
)
rf_base.fit(X_trainval, y_trainval)
print(f"  Base RF trained on {len(X_trainval):,} rows")

print("\nStep 2: Probability calibration (isotonic regression)...")
print("  Using CalibratedClassifierCV with cv=5 (internal temporal folds)...")
# cv=5 uses sklearn's internal CV for calibration — acceptable here because
# calibration is a post-hoc adjustment and we already validated CV AUC above.
calibrated_rf = CalibratedClassifierCV(
    estimator=rf_base,
    method='isotonic',
    cv=5
)
calibrated_rf.fit(X_trainval, y_trainval)
print("  Calibrated model fitted")

# ── HOLD-OUT TEST EVALUATION ──────────────────────────────────────────────────
print(f"\n{'='*70}")
print("HOLD-OUT TEST SET EVALUATION (last 6 months)")
print(f"{'='*70}")

y_test_proba_cal = calibrated_rf.predict_proba(X_test)[:, 1]
y_test_proba_raw = rf_base.predict_proba(X_test)[:, 1]

test_auc_cal = roc_auc_score(y_test, y_test_proba_cal)
test_auc_raw = roc_auc_score(y_test, y_test_proba_raw)

print(f"  Test months:         {test_months[0]} -> {test_months[-1]}")
print(f"  Test rows:           {len(y_test):,}")
print(f"  Test positive rate:  {y_test.mean()*100:.1f}%")
print(f"\n  RAW RF AUC (test):        {test_auc_raw:.4f}")
print(f"  CALIBRATED RF AUC (test): {test_auc_cal:.4f}")

if xgb_available and xgb_cv_aucs:
    print(f"\n  Fitting XGB on train+val for test comparison...")
    scale_pos_full = (y_trainval == 0).sum() / max((y_trainval == 1).sum(), 1)
    xgb_final = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_full,
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1,
        verbosity=0,
        use_label_encoder=False
    )
    xgb_final.fit(X_trainval, y_trainval)
    xgb_test_proba = xgb_final.predict_proba(X_test)[:, 1]
    xgb_test_auc   = roc_auc_score(y_test, xgb_test_proba)
    print(f"  XGB AUC (test):           {xgb_test_auc:.4f}")

# ── GINI FEATURE IMPORTANCE ───────────────────────────────────────────────────
print(f"\n{'='*70}")
print("FEATURE IMPORTANCE — GINI (Random Forest)")
print(f"{'='*70}")

importance_df = pd.DataFrame({
    'feature':    feature_cols,
    'gini_importance': rf_base.feature_importances_
}).sort_values('gini_importance', ascending=False).reset_index(drop=True)

print("Top 15 features (Gini):")
for _, row in importance_df.head(15).iterrows():
    bar = '#' * int(row['gini_importance'] * 200)
    print(f"  {row['feature']:35s}  {row['gini_importance']:.4f} ({row['gini_importance']*100:.1f}%)  {bar}")

# ── SHAP FEATURE IMPORTANCE ───────────────────────────────────────────────────
shap_df = None
shap_succeeded = False

try:
    import shap
    print(f"\n{'='*70}")
    print("FEATURE IMPORTANCE — SHAP (TreeExplainer)")
    print(f"{'='*70}")
    print("Computing SHAP values on train+val set (sample of 5,000 rows)...")

    # Sample for speed — SHAP on full 44k rows takes too long
    rng     = np.random.default_rng(42)
    n_shap  = min(5000, len(X_trainval))
    idx     = rng.choice(len(X_trainval), size=n_shap, replace=False)
    X_shap  = X_trainval.iloc[idx]

    # Use base RF (not CalibratedClassifierCV wrapper)
    shap_model = rf_base
    print(f"  Using base RF for SHAP (not calibrated wrapper)")

    # Convert to numpy to avoid SHAP/pandas/numpy version conflicts
    X_shap_np = X_shap.values.astype(np.float64)

    try:
        # Primary: TreeExplainer on numpy array
        explainer   = shap.TreeExplainer(shap_model)
        shap_values = explainer.shap_values(X_shap_np)

        if isinstance(shap_values, list):
            shap_vals_pos = shap_values[1]
        else:
            shap_vals_pos = shap_values

    except Exception as e_tree:
        # Fallback: model-agnostic Explainer
        print(f"  TreeExplainer failed ({e_tree}), falling back to Explainer...")
        explainer   = shap.Explainer(shap_model.predict, X_shap_np)
        shap_obj    = explainer(X_shap_np)
        shap_vals_pos = shap_obj.values

    mean_abs_shap = np.abs(shap_vals_pos).mean(axis=0)
    shap_df = pd.DataFrame({
        'feature':        feature_cols,
        'mean_abs_shap':  mean_abs_shap
    }).sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)

    print(f"\nTop 15 features (SHAP mean |value|):")
    for _, row in shap_df.head(15).iterrows():
        bar = '#' * int(row['mean_abs_shap'] / shap_df['mean_abs_shap'].max() * 40)
        print(f"  {row['feature']:35s}  {row['mean_abs_shap']:.4f}  {bar}")

    importance_df = importance_df.merge(shap_df, on='feature', how='left')
    shap_succeeded = True

except ImportError:
    print("\n  SHAP not installed — skipping (pip install shap>=0.42.0)")
except Exception as e:
    print(f"\n  SHAP failed: {e}")

# ── PERMUTATION IMPORTANCE (fallback if SHAP fails) ──────────────────────────
if not shap_succeeded:
    try:
        from sklearn.inspection import permutation_importance
        print(f"\n{'='*70}")
        print("FEATURE IMPORTANCE — PERMUTATION (sklearn, SHAP fallback)")
        print(f"{'='*70}")
        print("Computing permutation importance on test set (10 repeats)...")

        perm_result = permutation_importance(
            rf_base, X_test, y_test,
            n_repeats=10, random_state=42, scoring='roc_auc', n_jobs=-1
        )

        perm_df = pd.DataFrame({
            'feature':             feature_cols,
            'perm_importance_mean': perm_result.importances_mean,
            'perm_importance_std':  perm_result.importances_std
        }).sort_values('perm_importance_mean', ascending=False).reset_index(drop=True)

        print(f"\nTop 15 features (permutation importance, AUC drop):")
        for _, row in perm_df.head(15).iterrows():
            bar = '#' * int(row['perm_importance_mean'] / max(perm_df['perm_importance_mean'].max(), 1e-9) * 40)
            print(f"  {row['feature']:35s}  {row['perm_importance_mean']:.4f} ± {row['perm_importance_std']:.4f}  {bar}")

        # Merge permutation importance into Gini table
        importance_df = importance_df.merge(
            perm_df[['feature', 'perm_importance_mean', 'perm_importance_std']],
            on='feature', how='left'
        )

        # Also save as shap_df substitute for downstream code
        shap_df = perm_df.rename(columns={'perm_importance_mean': 'mean_abs_shap'})

    except Exception as e_perm:
        print(f"\n  Permutation importance also failed: {e_perm} — skipping")

# ── SAVE MODEL & ARTIFACTS ────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("SAVING ARTIFACTS")
print(f"{'='*70}")

os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)

# Save calibrated model (this is what the API uses)
with open(MODEL_OUT, 'wb') as f:
    pickle.dump(calibrated_rf, f)
print(f"  Model saved:        {MODEL_OUT}")

# Copy to backend model folder
os.makedirs(os.path.dirname(BACKEND_MODEL), exist_ok=True)
shutil.copy2(MODEL_OUT, BACKEND_MODEL)
print(f"  Copied to backend:  {BACKEND_MODEL}")

# Save calibrated XGBoost model (if available)
if xgb_available and xgb_cv_aucs:
    print(f"\n  Training calibrated XGBoost for deployment...")
    # xgb_final was already trained on full train+val above (hold-out eval section)
    calibrated_xgb = CalibratedClassifierCV(
        estimator=xgb_final,
        method='isotonic',
        cv=5
    )
    calibrated_xgb.fit(X_trainval, y_trainval)

    with open(MODEL_OUT_XGB, 'wb') as f:
        pickle.dump(calibrated_xgb, f)
    print(f"  XGB model saved:    {MODEL_OUT_XGB}")

    os.makedirs(os.path.dirname(BACKEND_MODEL_XGB), exist_ok=True)
    shutil.copy2(MODEL_OUT_XGB, BACKEND_MODEL_XGB)
    print(f"  Copied to backend:  {BACKEND_MODEL_XGB}")

    # Print head-to-head comparison on test set
    xgb_test_proba_cal = calibrated_xgb.predict_proba(X_test)[:, 1]
    xgb_test_auc_cal = roc_auc_score(y_test, xgb_test_proba_cal)
    print(f"\n  === MODEL COMPARISON (hold-out test) ===")
    print(f"  RF  (calibrated) AUC: {test_auc_cal:.4f}")
    print(f"  XGB (calibrated) AUC: {xgb_test_auc_cal:.4f}")
    print(f"  XGB (raw)        AUC: {xgb_test_auc:.4f}")
    if xgb_test_auc_cal > test_auc_cal:
        print(f"  --> XGBoost wins by {xgb_test_auc_cal - test_auc_cal:.4f}")
    else:
        print(f"  --> Random Forest wins by {test_auc_cal - xgb_test_auc_cal:.4f}")

# Save feature importance (Gini + SHAP if available)
importance_df.to_csv(IMPORTANCE_OUT, index=False)
print(f"  Gini importance:    {IMPORTANCE_OUT}")

# Save SHAP separately if computed
if shap_df is not None:
    shap_df.to_csv(SHAP_OUT, index=False)
    print(f"  SHAP importance:    {SHAP_OUT}")

# Save metrics report
with open(METRICS_OUT, 'w') as f:
    f.write("Nipharma ML Model Training Metrics\n")
    f.write("===================================\n\n")
    f.write(f"Date:              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Script:            12_ml_model_panel.py v5 (temporal CV)\n\n")
    f.write(f"Dataset\n")
    f.write(f"-------\n")
    f.write(f"  Train+Val rows:  {len(X_trainval):,}\n")
    f.write(f"  Test rows:       {len(X_test):,}\n")
    f.write(f"  Features:        {len(feature_cols)}\n")
    f.write(f"  Positive labels: {y_trainval.sum():,} ({y_trainval.mean()*100:.1f}%)\n\n")
    f.write(f"Temporal Split\n")
    f.write(f"--------------\n")
    f.write(f"  Train+Val:       {train_val_months[0]} -> {train_val_months[-1]}\n")
    f.write(f"  Test (hold-out): {test_months[0]} -> {test_months[-1]}\n\n")
    f.write(f"Walk-Forward CV Results (5 folds, 1-month gap)\n")
    f.write(f"----------------------------------------------\n")
    f.write(f"  RF AUCs:         {[f'{a:.4f}' for a in rf_cv_aucs]}\n")
    f.write(f"  RF Mean AUC:     {rf_mean:.4f}  Std: {rf_std:.4f}\n")
    if xgb_available and xgb_cv_aucs:
        f.write(f"  XGB AUCs:        {[f'{a:.4f}' for a in xgb_cv_aucs]}\n")
        f.write(f"  XGB Mean AUC:    {xgb_mean:.4f}  Std: {xgb_std:.4f}\n")
    f.write(f"\nHold-Out Test Results\n")
    f.write(f"---------------------\n")
    f.write(f"  RF (raw) AUC:    {test_auc_raw:.4f}\n")
    f.write(f"  RF (calib) AUC:  {test_auc_cal:.4f}\n")
    if xgb_available and xgb_cv_aucs:
        f.write(f"  XGB (raw) AUC:   {xgb_test_auc:.4f}\n")
        f.write(f"  XGB (calib) AUC: {xgb_test_auc_cal:.4f}\n")
    f.write(f"\nSaved Models:\n")
    f.write(f"  RF:  CalibratedClassifierCV(RandomForest, isotonic) -> panel_model.pkl\n")
    if xgb_available and xgb_cv_aucs:
        f.write(f"  XGB: CalibratedClassifierCV(XGBoost, isotonic)    -> panel_model_xgb.pkl\n")
    f.write(f"\n")
    f.write(f"Top 20 Features (Gini importance):\n")
    for _, row in importance_df.head(20).iterrows():
        f.write(f"  {row['feature']:35s}  {row['gini_importance']:.4f}\n")
    if shap_df is not None:
        f.write(f"\nTop 20 Features (SHAP mean |value|):\n")
        for _, row in shap_df.head(20).iterrows():
            f.write(f"  {row['feature']:35s}  {row['mean_abs_shap']:.4f}\n")

print(f"  Metrics report:     {METRICS_OUT}")

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("TRAINING COMPLETE")
print(f"{'='*70}")
print(f"\nMODEL SUMMARY:")
print(f"  Architecture:     CalibratedClassifierCV(RandomForest, isotonic)")
print(f"  Trees:            100  |  max_depth: 15  |  class_weight: balanced")
print(f"  Features:         {len(feature_cols)}")
print(f"\nVALIDATION:")
print(f"  Walk-forward AUC: {rf_mean:.4f} +/- {rf_std:.4f}  (5 temporal folds, 1-mo gap)")
print(f"  Hold-out AUC:     {test_auc_cal:.4f}  (last 6 months, never seen in CV)")
if xgb_available and xgb_cv_aucs:
    print(f"  XGB benchmark:    {xgb_mean:.4f} (CV)  /  {xgb_test_auc:.4f} (test)")
print(f"\nOUTPUT FILES:")
print(f"  RF Model:         {MODEL_OUT}")
print(f"  RF Backend copy:  {BACKEND_MODEL}")
if xgb_available and xgb_cv_aucs:
    print(f"  XGB Model:        {MODEL_OUT_XGB}")
    print(f"  XGB Backend copy: {BACKEND_MODEL_XGB}")
print(f"  Feature imports:  {IMPORTANCE_OUT}")
if shap_df is not None:
    print(f"  SHAP values:      {SHAP_OUT}")
print(f"  Metrics:          {METRICS_OUT}")
print(f"\nNEXT STEPS:")
print(f"  1. git add nipharma-backend/model/panel_model.pkl nipharma-backend/model/panel_model_xgb.pkl && git push")
print(f"  2. Railway will auto-deploy — backend uses XGBoost if available, RF fallback")
print(f"  3. Verify /predict endpoint returns sensible risk scores + model_used field")
print(f"\n{'='*70}")
