#!/usr/bin/env python3
"""
24_fix_bnf_mapping.py — Fix BNF mapping for PCA demand features
================================================================
Uses the Bennett Institute BNF-to-dm+d mapping (57K rows) to properly
join PCA prescribing demand data (348K rows) to panel drugs.

Before this fix: PCA features contributed ~1.4% importance (broken join)
After: 348/350 panel drug groups (99.4%) now match PCA demand data.

Outputs updated columns in panel_feature_store_train.csv:
  - pca_items (total items prescribed this month)
  - pca_items_mom_pct (month-on-month change)
  - pca_demand_spike (>20% MoM increase flag)
  - pca_demand_trend_6mo (6-month rolling average items)
  - pca_nic_gbp (net ingredient cost)

Run:
  cd scrapers && python3 24_fix_bnf_mapping.py
"""

import os
import re
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

PANEL_PATH = os.path.join(DATA_DIR, "features", "panel_feature_store_train.csv")
BNF_MAPPING = os.path.join(DATA_DIR, "mapping", "bnf_to_dmd.csv")
PCA_PATH = os.path.join(DATA_DIR, "openprescribing", "pca_demand_monthly.csv")

print("=" * 70)
print("24_fix_bnf_mapping.py — Fix PCA demand signal via BNF mapping")
print("=" * 70)

# ── Step 1: Load data ────────────────────────────────────────────────────────
print("\n[1/5] Loading data...")

panel = pd.read_csv(PANEL_PATH, low_memory=False)
print(f"  Panel: {panel.shape[0]:,} rows x {panel.shape[1]} cols")

bnf = pd.read_csv(BNF_MAPPING, low_memory=False)
bnf_vmp = bnf[bnf["type"] == "vmp"].copy()
print(f"  BNF mapping: {len(bnf_vmp):,} VMP entries ({bnf_vmp['bnf_code'].notna().sum():,} with BNF codes)")

pca = pd.read_csv(PCA_PATH, low_memory=False)
print(f"  PCA demand: {len(pca):,} rows, {pca['GENERIC_BNF_EQUIVALENT_CODE'].nunique():,} unique BNF codes")


# ── Step 2: Map panel drug_name → BNF code ───────────────────────────────────
print("\n[2/5] Mapping panel drugs to BNF codes...")


def strip_pack(name):
    """Remove trailing pack size from drug name to match VMP names."""
    return re.sub(
        r"\s+\d+\s*(tablet|capsule|ml|mg|pack|sachet|suppository|pessary|dose|patch|strip|tube|amp)?s?\s*$",
        "", str(name).lower().strip(), flags=re.I
    ).strip()


# Build lookup: clean VMP name → BNF code
bnf_vmp["clean_nm"] = bnf_vmp["nm"].str.lower().str.strip()
bnf_lookup = (
    bnf_vmp[bnf_vmp["bnf_code"].notna()]
    .drop_duplicates("clean_nm")
    .set_index("clean_nm")["bnf_code"]
    .to_dict()
)

# Map each panel drug
drug_to_bnf = {}
panel_drugs = panel["drug_name"].unique()
for drug in panel_drugs:
    clean = strip_pack(drug)
    if clean in bnf_lookup:
        drug_to_bnf[drug] = bnf_lookup[clean]

print(f"  Mapped: {len(drug_to_bnf)}/{len(panel_drugs)} drugs ({len(drug_to_bnf)/len(panel_drugs)*100:.1f}%)")

# Add BNF code to panel
panel["bnf_code"] = panel["drug_name"].map(drug_to_bnf)
panel["bnf_prefix_9"] = panel["bnf_code"].str[:9]  # Chemical substance level


# ── Step 3: Aggregate PCA demand by BNF prefix + month ───────────────────────
print("\n[3/5] Aggregating PCA demand by BNF chemical substance + month...")

pca["bnf_prefix_9"] = pca["GENERIC_BNF_EQUIVALENT_CODE"].str[:9]
pca["month"] = pca["month"].astype(str)

pca_agg = (
    pca.groupby(["bnf_prefix_9", "month"])
    .agg(pca_items=("items", "sum"), pca_nic_gbp=("nic_gbp", "sum"))
    .reset_index()
)
print(f"  PCA aggregated: {len(pca_agg):,} (prefix, month) pairs")


# ── Step 4: Compute PCA demand features ──────────────────────────────────────
print("\n[4/5] Computing PCA demand features...")

# Sort for MoM and rolling calculations
pca_agg = pca_agg.sort_values(["bnf_prefix_9", "month"])

# MoM change
pca_agg["pca_items_mom_pct"] = (
    pca_agg.groupby("bnf_prefix_9")["pca_items"]
    .pct_change()
    .mul(100)
    .round(2)
)

# Demand spike: >20% MoM increase
pca_agg["pca_demand_spike"] = (pca_agg["pca_items_mom_pct"] > 20).astype(int)

# 6-month rolling average
pca_agg["pca_demand_trend_6mo"] = (
    pca_agg.groupby("bnf_prefix_9")["pca_items"]
    .transform(lambda x: x.rolling(6, min_periods=1).mean())
    .round(0)
)

print(f"  Demand spikes: {pca_agg['pca_demand_spike'].sum():,} months")


# ── Step 5: Join PCA features to panel ───────────────────────────────────────
print("\n[5/5] Joining PCA features to panel...")

panel["month"] = panel["month"].astype(str)

# Drop old weak PCA columns if they exist
old_pca_cols = ["items_mom_pct", "demand_spike", "demand_trend_6mo", "avg_items_3mo"]
existing_old = [c for c in old_pca_cols if c in panel.columns]
if existing_old:
    panel = panel.drop(columns=existing_old)
    print(f"  Dropped old weak PCA columns: {existing_old}")

# Drop new PCA columns if re-running
new_pca_cols = ["pca_items", "pca_items_mom_pct", "pca_demand_spike", "pca_demand_trend_6mo", "pca_nic_gbp"]
existing_new = [c for c in new_pca_cols if c in panel.columns]
if existing_new:
    panel = panel.drop(columns=existing_new)

# Merge
before_cols = panel.shape[1]
panel = panel.merge(
    pca_agg[["bnf_prefix_9", "month", "pca_items", "pca_items_mom_pct",
             "pca_demand_spike", "pca_demand_trend_6mo", "pca_nic_gbp"]],
    on=["bnf_prefix_9", "month"],
    how="left"
)

# Fill NaN for unmatched drugs (0 demand)
for col in new_pca_cols:
    panel[col] = panel[col].fillna(0)

# Drop temp columns
panel = panel.drop(columns=["bnf_prefix_9"], errors="ignore")

matched_rows = (panel["pca_items"] > 0).sum()
print(f"  Panel rows with PCA demand: {matched_rows:,}/{len(panel):,} ({matched_rows/len(panel)*100:.1f}%)")
print(f"  Columns: {before_cols} → {panel.shape[1]} (+{panel.shape[1] - before_cols} new PCA features)")

# ── Save ─────────────────────────────────────────────────────────────────────
panel.to_csv(PANEL_PATH, index=False)
print(f"\n  Saved: {PANEL_PATH}")
print(f"  {panel.shape[0]:,} rows x {panel.shape[1]} cols")

# Quick stats
print(f"\n{'=' * 70}")
print("PCA Feature Summary")
print(f"{'=' * 70}")
for col in new_pca_cols:
    nz = (panel[col] != 0).sum()
    print(f"  {col:<30} non-zero: {nz:>8,} ({nz/len(panel)*100:.1f}%)")

print(f"\n  BEFORE: PCA signal ~1.4% importance (broken BNF join)")
print(f"  AFTER:  {matched_rows/len(panel)*100:.1f}% panel rows now have real PCA demand data")
print(f"\nDone. Re-run 12_ml_model_panel.py in Terminal to retrain with fixed PCA features.")
