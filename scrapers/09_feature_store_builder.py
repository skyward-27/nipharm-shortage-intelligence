"""
SCRAPER 09: NPT Feature Store Builder
======================================
Joins all collected data sources into a single flat feature table
ready for ML model training and inference.

Input files (must exist before running):
  data/drug_tariff/tariff_with_floors.csv       — core price signal
  data/concessions/cpe_current_month.csv        — current shortage labels
  data/concessions/cpe_historical_concessions.csv — historical labels
  data/market_signals/fx_rates_stress.csv       — FX cost pressure
  data/market_signals/boe_inflation.csv         — macro signals
  data/market_signals/openfda_shortages.csv     — US leading indicator
  data/mhra/govuk_shortage_publications.csv     — MHRA supply notices
  data/molecule_master/molecule_master.csv      — identity / API country

Output:
  data/features/feature_store.csv               — one row per molecule (latest)
  data/features/feature_store_labelled.csv      — rows with known shortage labels (training set)

Schema of feature_store.csv:
  vmpp_code            — VMPP Snomed Code (primary key)
  drug_name            — canonical drug name
  pack_size            — pack size
  price_gbp            — latest Cat M reimbursement price (£)
  floor_price_gbp      — 5th percentile historical price = unprofitable floor
  floor_proximity      — price_gbp / floor_price_gbp (<=1.0 = at/below floor)
  within_15pct_of_floor — bool: floor_proximity <= 1.15
  price_12mo_change    — price change over 12 months (%)
  gbp_inr_latest       — latest GBP/INR rate
  fx_stress_score      — composite FX stress (>1 = cost pressure)
  fx_high_stress       — bool: fx_stress < 0.95
  boe_bank_rate        — latest BoE base rate
  ppi_output_index     — latest pharma producer price index
  us_shortage_flag     — 1 if drug name matches active US FDA shortage
  mhra_mention_count   — number of MHRA publications mentioning this drug
  api_country          — primary API manufacturing country (from dm+d)
  is_shortage_label    — 1 if drug is on current CPE concession list (training label)
  data_date            — date this feature row was generated
"""

import pandas as pd
import numpy as np
import os
import re
from datetime import datetime

OUTPUT_DIR = "data/features"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DIR = "data"


# ── LOADERS ───────────────────────────────────────────────────────────────────

def load_tariff_floors() -> pd.DataFrame:
    """Load latest price per molecule from tariff_with_floors.csv."""
    path = f"{DATA_DIR}/drug_tariff/tariff_with_floors.csv"
    if not os.path.exists(path):
        print(f"  MISSING: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    # Keep only one row per vmpp_code — the one from the most recent source_file
    df = df.sort_values("source_file", ascending=False)
    latest = df.drop_duplicates(subset=["vmpp_code"], keep="first").copy()
    print(f"  Tariff floors: {len(latest):,} unique molecules (from {df['source_file'].nunique()} monthly files)")
    return latest[["vmpp_code", "drug_name", "pack_size", "unit",
                   "price_gbp", "floor_price_gbp", "floor_proximity",
                   "within_15pct_of_floor", "source_file"]]


def load_price_trend(df_all_tariff: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 12-month price change per molecule using the full historical tariff data.
    """
    path = f"{DATA_DIR}/drug_tariff/tariff_with_floors.csv"
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_csv(path)
    df = df.dropna(subset=["vmpp_code", "price_gbp"])

    # Sort by source_file (proxy for date)
    df = df.sort_values("source_file")

    # Get first and last price per molecule
    oldest = df.drop_duplicates("vmpp_code", keep="first")[["vmpp_code", "price_gbp"]].rename(columns={"price_gbp": "oldest_price"})
    newest = df.drop_duplicates("vmpp_code", keep="last")[["vmpp_code", "price_gbp"]].rename(columns={"price_gbp": "newest_price"})

    trend = oldest.merge(newest, on="vmpp_code")
    trend["price_change_pct"] = ((trend["newest_price"] - trend["oldest_price"]) / trend["oldest_price"] * 100).round(1)
    print(f"  Price trends: {len(trend):,} molecules with historical data")
    return trend[["vmpp_code", "price_change_pct"]]


def load_fx_signals() -> dict:
    """Load latest FX stress signal."""
    path = f"{DATA_DIR}/market_signals/fx_rates_stress.csv"
    if not os.path.exists(path):
        print(f"  MISSING: {path} — FX signals skipped")
        return {}

    df = pd.read_csv(path).sort_values("date")
    latest = df.dropna(subset=["gbp_inr"]).iloc[-1]
    result = {
        "gbp_inr_latest":  round(float(latest.get("gbp_inr", 0)), 4),
        "gbp_usd_latest":  round(float(latest.get("gbp_usd", 0)), 4),
        "fx_stress_score": round(float(latest.get("fx_stress_score", 1.0)), 4),
        "fx_high_stress":  int(latest.get("fx_high_stress", 0)),
        "fx_data_date":    str(latest.get("date", "")),
    }
    print(f"  FX signals: GBP/INR={result['gbp_inr_latest']}, stress={result['fx_stress_score']}")
    return result


def load_boe_signals() -> dict:
    """Load latest BoE macro signals."""
    path = f"{DATA_DIR}/market_signals/boe_inflation.csv"
    if not os.path.exists(path):
        return {}

    df = pd.read_csv(path).sort_values("date")
    latest = df.dropna(subset=["boe_bank_rate"]).iloc[-1]
    return {
        "boe_bank_rate":    round(float(latest.get("boe_bank_rate", 0)), 4),
        "ppi_output_index": round(float(latest.get("ppi_output_index", 0)), 4) if pd.notna(latest.get("ppi_output_index")) else None,
    }


def load_us_shortage_flags() -> set:
    """Load active US FDA shortages. Returns a set of lowercase drug name fragments."""
    path = f"{DATA_DIR}/market_signals/openfda_shortages.csv"
    if not os.path.exists(path):
        return set()

    df = pd.read_csv(path)
    name_col = next((c for c in df.columns if "name" in c.lower() or "generic" in c.lower()), None)
    if not name_col:
        return set()

    names = set()
    for name in df[name_col].dropna():
        # Extract first word only (active ingredient) for cross-standard matching
        # US uses USAN, UK uses INN — first word is usually the same
        first_word = re.match(r'^([a-zA-Z]+)', str(name).strip())
        if first_word and len(first_word.group(1)) > 4:
            names.add(first_word.group(1).lower())

    print(f"  US shortage flags: {len(names)} active generic names (first-word matched)")
    return names


def load_mhra_mention_counts() -> pd.DataFrame:
    """
    Count MHRA publication mentions per drug name fragment.
    Returns a lookup: drug_name_fragment → mention_count
    """
    path = f"{DATA_DIR}/mhra/govuk_shortage_publications.csv"
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_csv(path)
    text_col = "title" if "title" in df.columns else df.columns[0]

    # Build mention frequency for common terms
    all_text = " ".join(df[text_col].dropna().str.lower().tolist())
    return all_text  # raw text for matching


def load_concession_labels() -> set:
    """
    Load all known concession drug names as positive labels.
    Returns lowercase drug name set.
    """
    labels = set()

    for path in [
        f"{DATA_DIR}/concessions/cpe_current_month.csv",
        f"{DATA_DIR}/concessions/cpe_historical_concessions.csv",
    ]:
        if os.path.exists(path):
            df = pd.read_csv(path)
            name_col = next((c for c in df.columns if "drug" in c.lower()), None)
            if name_col:
                for name in df[name_col].dropna():
                    # Normalise: lowercase, strip strength/form for matching
                    labels.add(str(name).strip().lower())

    print(f"  Shortage labels: {len(labels)} unique concession drug names")
    return labels


def load_api_country() -> pd.DataFrame:
    """Load API manufacturing country from molecule master."""
    path = f"{DATA_DIR}/molecule_master/molecule_master.csv"
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_csv(path)
    if "api_country_primary" not in df.columns:
        return pd.DataFrame()

    # Map by drug_name_clean → api_country
    df = df.dropna(subset=["drug_name_clean"])
    return df[["drug_name_clean", "api_country_primary"]].drop_duplicates("drug_name_clean")


# ── NAME MATCHING ─────────────────────────────────────────────────────────────

def fuzzy_name_match(drug_name: str, name_set: set) -> bool:
    """
    Check if drug_name matches any entry in name_set.
    Strategy: exact match first, then first-word match.
    """
    name_lower = str(drug_name).strip().lower()

    # Exact match
    if name_lower in name_set:
        return True

    # Extract active ingredient (first word before space/digit)
    active = re.match(r'^([a-zA-Z]+)', name_lower)
    if active:
        return active.group(1) in name_set

    return False


def count_mhra_mentions(drug_name: str, mhra_text: str) -> int:
    """Count how many times a drug name appears in MHRA publications."""
    if not mhra_text:
        return 0
    active = re.match(r'^([a-zA-Z]+)', str(drug_name).strip().lower())
    if not active or len(active.group(1)) < 5:
        return 0
    return mhra_text.count(active.group(1).lower())


# ── RISK TIER ─────────────────────────────────────────────────────────────────

def assign_risk_tier(row) -> str:
    """
    Rule-based risk tier for PoC (before ML model is trained):
      RED    — price below floor AND on US shortage list
      AMBER  — within 15% of floor OR on US shortage list
      YELLOW — within 30% of floor
      GREEN  — price comfortably above floor
    """
    proximity   = row.get("floor_proximity", 999)
    us_shortage = row.get("us_shortage_flag", 0)
    is_label    = row.get("is_shortage_label", 0)

    if is_label == 1:
        return "CONFIRMED"   # Already on concession list

    if proximity < 1.0 and us_shortage:
        return "RED"
    elif proximity < 1.0:
        return "RED"
    elif proximity <= 1.15 and us_shortage:
        return "RED"
    elif proximity <= 1.15:
        return "AMBER"
    elif proximity <= 1.30:
        return "YELLOW"
    else:
        return "GREEN"


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("NPT Feature Store Builder")
    print("=" * 60)
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # ── Load base: tariff floors ──────────────────────────────────────
    print("[1] Loading Drug Tariff floors (base table)...")
    base = load_tariff_floors()
    if base.empty:
        print("FATAL: No tariff floor data. Run scraper 01 first.")
        return

    # ── Price trend ───────────────────────────────────────────────────
    print("\n[2] Calculating price trends...")
    trend = load_price_trend(base)
    if not trend.empty:
        base = base.merge(trend, on="vmpp_code", how="left")

    # ── Scalar signals (broadcast to all rows) ────────────────────────
    print("\n[3] Loading market signals...")
    fx      = load_fx_signals()
    boe     = load_boe_signals()

    for k, v in {**fx, **boe}.items():
        base[k] = v

    # ── Drug-level flags ──────────────────────────────────────────────
    print("\n[4] Matching US shortage flags...")
    us_names = load_us_shortage_flags()
    base["us_shortage_flag"] = base["drug_name"].apply(
        lambda n: int(fuzzy_name_match(n, us_names))
    )
    print(f"  Matched {base['us_shortage_flag'].sum()} molecules to US shortages")

    print("\n[5] Counting MHRA publication mentions...")
    mhra_text = load_mhra_mention_counts()
    if mhra_text:
        base["mhra_mention_count"] = base["drug_name"].apply(
            lambda n: count_mhra_mentions(n, mhra_text)
        )
        print(f"  Molecules with ≥1 MHRA mention: {(base['mhra_mention_count'] > 0).sum()}")
    else:
        base["mhra_mention_count"] = 0

    print("\n[6] Attaching shortage labels...")
    labels = load_concession_labels()
    base["is_shortage_label"] = base["drug_name"].apply(
        lambda n: int(str(n).strip().lower() in labels)
    )
    print(f"  Labelled positive (is_shortage=1): {base['is_shortage_label'].sum()}")

    print("\n[7] Loading API country from molecule master...")
    api_df = load_api_country()
    if not api_df.empty:
        base["drug_name_lower"] = base["drug_name"].str.lower().str.strip()
        api_df["drug_name_clean_lower"] = api_df["drug_name_clean"].str.lower().str.strip()
        base = base.merge(
            api_df.rename(columns={"drug_name_clean_lower": "drug_name_lower", "api_country_primary": "api_country"}),
            on="drug_name_lower", how="left"
        ).drop(columns=["drug_name_lower"])
    else:
        base["api_country"] = None

    # ── Risk tier ─────────────────────────────────────────────────────
    print("\n[8] Assigning risk tiers...")
    base["risk_tier"] = base.apply(assign_risk_tier, axis=1)
    tier_counts = base["risk_tier"].value_counts()
    for tier, count in tier_counts.items():
        print(f"  {tier:12s}: {count:,}")

    # ── Metadata ──────────────────────────────────────────────────────
    base["data_date"] = datetime.now().strftime("%Y-%m-%d")

    # ── Clean column order ────────────────────────────────────────────
    col_order = [
        "vmpp_code", "drug_name", "pack_size", "unit",
        "price_gbp", "floor_price_gbp", "floor_proximity", "within_15pct_of_floor",
        "price_change_pct",
        "gbp_inr_latest", "fx_stress_score", "fx_high_stress",
        "boe_bank_rate", "ppi_output_index",
        "us_shortage_flag", "mhra_mention_count",
        "api_country",
        "risk_tier", "is_shortage_label",
        "data_date", "source_file",
    ]
    existing_cols = [c for c in col_order if c in base.columns]
    base = base[existing_cols]

    # ── Save full feature store ───────────────────────────────────────
    out_all = f"{OUTPUT_DIR}/feature_store.csv"
    base.to_csv(out_all, index=False)
    print(f"\n[9] Full feature store saved: {out_all}")
    print(f"    Shape: {base.shape[0]:,} rows × {base.shape[1]} features")

    # ── Save labelled subset (for ML training) ────────────────────────
    labelled = base[base["is_shortage_label"] == 1].copy()
    out_labelled = f"{OUTPUT_DIR}/feature_store_labelled.csv"
    labelled.to_csv(out_labelled, index=False)
    print(f"    Labelled training rows: {len(labelled):,} → {out_labelled}")

    # ── Save RED + AMBER alert list ───────────────────────────────────
    alerts = base[base["risk_tier"].isin(["RED", "AMBER", "CONFIRMED"])].sort_values("floor_proximity")
    out_alerts = f"{OUTPUT_DIR}/shortage_risk_alerts.csv"
    alerts.to_csv(out_alerts, index=False)
    print(f"    HIGH RISK alerts (RED/AMBER/CONFIRMED): {len(alerts):,} → {out_alerts}")

    # ── Print top 25 risk molecules ───────────────────────────────────
    print("\n" + "=" * 80)
    print("TOP 25 HIGHEST SHORTAGE RISK MOLECULES")
    print("=" * 80)
    top = alerts.head(25)[[
        "drug_name", "pack_size", "price_gbp", "floor_proximity",
        "us_shortage_flag", "mhra_mention_count", "risk_tier", "is_shortage_label"
    ]]
    print(top.to_string(index=False))

    return base


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
