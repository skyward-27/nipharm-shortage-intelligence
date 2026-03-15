"""
SCRIPT 11: Time-Series Panel Feature Store
==========================================
Rebuilds the feature store as a drug × month panel using 74 months of
CPE concession history (Jan 2020 – Feb 2026).

Instead of one row per drug (758 rows), this produces one row per
drug-month combination (~18,000 rows) where the label is:
  "Did this drug get a price concession 1 month later?"

This gives the ML model proper temporal structure and 7,742 positive
training examples instead of 154.

Inputs:
  data/concessions/cpe_archive_full.csv   — 7,742 concession events (2020-2026)
  data/drug_tariff/drug_tariff_202603.csv — 24mo Cat M prices (VMPP codes)
  data/mhra/govuk_shortage_publications.csv
  data/market_signals/fx_rates_stress.csv
  data/market_signals/boe_inflation.csv
  data/market_signals/openfda_shortages.csv

Outputs:
  data/features/panel_feature_store.csv       — full panel (~18k rows)
  data/features/panel_feature_store_train.csv — rows with known labels
  data/features/panel_label_summary.csv       — label balance stats
"""

import pandas as pd
import numpy as np
import os
import re
from datetime import datetime

OUT_DIR = "data/features"
os.makedirs(OUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# 1. LOAD CONCESSION ARCHIVE (labels)
# ─────────────────────────────────────────────

def load_concessions() -> pd.DataFrame:
    path = "data/concessions/cpe_archive_full.csv"
    df = pd.read_csv(path)
    df["month"] = pd.to_datetime(df["month"]).dt.to_period("M")
    df["vmpp_code"] = df["vmpp_code"].astype(str).str.strip().str.split(".").str[0]
    df["drug_name_clean"] = df["drug_name"].str.lower().str.strip()
    df["on_concession"] = 1
    print(f"Concessions loaded: {len(df):,} rows, {df.month.nunique()} months, {df.drug_name.nunique()} drugs")
    return df


# ─────────────────────────────────────────────
# 2. LOAD DRUG TARIFF (price history)
# ─────────────────────────────────────────────

def load_tariff() -> pd.DataFrame:
    path = "data/drug_tariff/drug_tariff_202603.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={
        "vmpp_snomed_code": "vmpp_code",
        "drug_name": "drug_name",
        "pack_size": "pack_size",
        "basic_price": "price_pence",
        "unnamed:_3": "unit",
    })
    df["vmpp_code"] = pd.to_numeric(df["vmpp_code"], errors="coerce")
    df = df.dropna(subset=["vmpp_code"])
    df["vmpp_code"] = df["vmpp_code"].astype(np.int64).astype(str)
    df["price_gbp"] = pd.to_numeric(df["price_pence"], errors="coerce") / 100
    df = df.dropna(subset=["vmpp_code", "price_gbp"])

    # Parse month from source_file string e.g. "Category M Prices - Quarter 4 January 2026"
    def parse_month(s):
        months = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"]
        if not isinstance(s, str):
            return None
        for m in months:
            if m in s:
                year_match = re.search(r'(\d{4})', s)
                if year_match:
                    try:
                        return pd.Period(f"{year_match.group(1)}-{months.index(m)+1:02d}", freq="M")
                    except:
                        return None
        return None

    df["tariff_month"] = df["source_file"].apply(parse_month)
    df = df.dropna(subset=["tariff_month"])
    print(f"Tariff loaded: {len(df):,} rows, {df.tariff_month.nunique()} months, {df.vmpp_code.nunique()} VMPPs")
    return df


# ─────────────────────────────────────────────
# 3. COMPUTE ROLLING PRICE FEATURES
# ─────────────────────────────────────────────

def compute_price_features(tariff: pd.DataFrame) -> pd.DataFrame:
    """Per VMPP per month: price, 3mo avg, 6mo avg, MoM change, YoY change, floor proximity."""
    df = tariff[["vmpp_code", "drug_name", "pack_size", "unit", "tariff_month", "price_gbp"]].copy()
    df = df.sort_values(["vmpp_code", "tariff_month"])

    # Rolling calculations per VMPP
    records = []
    for vmpp, grp in df.groupby("vmpp_code"):
        grp = grp.sort_values("tariff_month").reset_index(drop=True)
        prices = grp["price_gbp"].values
        months = grp["tariff_month"].values

        for i, row in grp.iterrows():
            p = row["price_gbp"]
            # Rolling 6mo floor (5th pct of available history up to this point)
            hist = prices[:i+1]
            floor = np.percentile(hist, 5) if len(hist) >= 3 else p
            floor_prox = p / floor if floor > 0 else 1.0

            # MoM change
            mom = (p - prices[i-1]) / prices[i-1] if i > 0 else 0.0

            # 6mo avg
            avg6 = np.mean(prices[max(0,i-5):i+1])

            # YoY change (12mo ago)
            yoy = (p - prices[i-12]) / prices[i-12] if i >= 12 else 0.0

            records.append({
                "vmpp_code":        row["vmpp_code"],
                "drug_name":        row["drug_name"],
                "pack_size":        row["pack_size"],
                "unit":             row["unit"],
                "month":            row["tariff_month"],
                "price_gbp":        round(p, 4),
                "floor_price_gbp":  round(floor, 4),
                "floor_proximity":  round(floor_prox, 4),
                "within_15pct_of_floor": int(floor_prox <= 1.15),
                "price_mom_pct":    round(mom * 100, 2),
                "price_6mo_avg":    round(avg6, 4),
                "price_yoy_pct":    round(yoy * 100, 2),
            })

    result = pd.DataFrame(records)
    print(f"Price features computed: {len(result):,} drug-month rows")
    return result


# ─────────────────────────────────────────────
# 4. MHRA MENTION COUNTS (static per drug)
# ─────────────────────────────────────────────

def load_mhra_counts() -> pd.DataFrame:
    path = "data/mhra/govuk_shortage_publications.csv"
    if not os.path.exists(path):
        return pd.DataFrame(columns=["drug_name_clean", "mhra_mention_count"])
    df = pd.read_csv(path)
    title_col = next((c for c in df.columns if "title" in c.lower()), None)
    if not title_col:
        return pd.DataFrame(columns=["drug_name_clean", "mhra_mention_count"])
    # Count per drug name (static — not time-varying for now)
    all_titles = " ".join(df[title_col].dropna().str.lower().tolist())
    return all_titles  # return raw text for matching


def match_mhra(drug_name: str, mhra_text: str) -> int:
    first_word = drug_name.lower().split()[0] if drug_name else ""
    if len(first_word) < 4:
        return 0
    return mhra_text.count(first_word)


# ─────────────────────────────────────────────
# 5. MACRO SIGNALS (monthly)
# ─────────────────────────────────────────────

def load_macro() -> pd.DataFrame:
    """Returns a monthly macro signal table."""
    records = []

    # FX rates
    fx_path = "data/market_signals/fx_rates_stress.csv"
    if os.path.exists(fx_path):
        fx = pd.read_csv(fx_path, parse_dates=["date"])
        fx["month"] = fx["date"].dt.to_period("M")
        fx_monthly = fx.groupby("month").agg(
            gbp_inr=("gbp_inr", "mean"),
            fx_stress_score=("gbp_inr", lambda x: max(0, (x.mean() - 100) / 10))
        ).reset_index()
    else:
        fx_monthly = pd.DataFrame(columns=["month", "gbp_inr", "fx_stress_score"])

    # BoE rate
    boe_path = "data/market_signals/boe_inflation.csv"
    if os.path.exists(boe_path):
        boe = pd.read_csv(boe_path)
        date_col = next((c for c in boe.columns if "date" in c.lower()), None)
        rate_col = next((c for c in boe.columns if "rate" in c.lower() or "bank" in c.lower()), None)
        if date_col and rate_col:
            boe["month"] = pd.to_datetime(boe[date_col], errors="coerce").dt.to_period("M")
            boe_monthly = boe.groupby("month")[rate_col].last().rename("boe_bank_rate").reset_index()
        else:
            boe_monthly = pd.DataFrame(columns=["month", "boe_bank_rate"])
    else:
        boe_monthly = pd.DataFrame(columns=["month", "boe_bank_rate"])

    # Merge macro signals
    macro = fx_monthly.copy()
    if len(boe_monthly):
        macro = macro.merge(boe_monthly, on="month", how="outer")

    if len(macro) == 0:
        return pd.DataFrame(columns=["month", "gbp_inr", "fx_stress_score", "boe_bank_rate"])

    print(f"Macro signals: {len(macro):,} monthly rows")
    return macro


# ─────────────────────────────────────────────
# 6. US SHORTAGE FLAG (static set)
# ─────────────────────────────────────────────

def load_us_shortage_names() -> set:
    path = "data/market_signals/openfda_shortages.csv"
    if not os.path.exists(path):
        return set()
    df = pd.read_csv(path)
    name_col = next((c for c in df.columns if "drug" in c.lower() or "name" in c.lower()), None)
    if not name_col:
        return set()
    names = set()
    for name in df[name_col].dropna():
        m = re.match(r'^([a-zA-Z]+)', str(name).strip())
        if m and len(m.group(1)) > 4:
            names.add(m.group(1).lower())
    return names


# ─────────────────────────────────────────────
# 7. BUILD PANEL
# ─────────────────────────────────────────────

def build_panel(price_features: pd.DataFrame,
                concessions: pd.DataFrame,
                macro: pd.DataFrame,
                mhra_text: str,
                us_shortage_names: set) -> pd.DataFrame:
    """
    Join all signals. Create forward-looking label:
      label_next_month = 1 if drug had a concession the following month
    """
    panel = price_features.copy()

    # ── Concession label: was this drug on concession THIS month?
    conc_keys = concessions[["vmpp_code", "month", "on_concession"]].copy()
    panel = panel.merge(conc_keys, on=["vmpp_code", "month"], how="left")
    panel["on_concession"] = panel["on_concession"].fillna(0).astype(int)

    # ── Forward label: concession NEXT month (1-month lead)
    conc_next = conc_keys.copy()
    conc_next["month"] = conc_next["month"] + 1
    conc_next = conc_next.rename(columns={"on_concession": "label_next_month"})
    panel = panel.merge(conc_next, on=["vmpp_code", "month"], how="left")
    panel["label_next_month"] = panel["label_next_month"].fillna(0).astype(int)

    # ── Macro signals
    if len(macro):
        panel = panel.merge(macro, on="month", how="left")
        for col in ["gbp_inr", "fx_stress_score", "boe_bank_rate"]:
            if col in panel.columns:
                panel[col] = panel[col].fillna(method="ffill").fillna(panel[col].median())

    # ── MHRA mention count (static per drug)
    panel["mhra_mention_count"] = panel["drug_name"].apply(
        lambda d: match_mhra(d, mhra_text) if isinstance(d, str) else 0
    )

    # ── US shortage flag (static)
    def us_flag(drug_name):
        if not isinstance(drug_name, str):
            return 0
        first = drug_name.lower().split()[0]
        return int(first in us_shortage_names or any(first.startswith(n[:6]) for n in us_shortage_names))

    panel["us_shortage_flag"] = panel["drug_name"].apply(us_flag)

    # ── Consecutive months on concession (momentum feature)
    panel = panel.sort_values(["vmpp_code", "month"])
    panel["concession_streak"] = (
        panel.groupby("vmpp_code")["on_concession"]
        .transform(lambda x: x.groupby((x != x.shift()).cumsum()).cumcount() + 1) * panel["on_concession"]
    )

    # ── Times on concession in last 6 months (frequency feature)
    def rolling_concession_count(grp):
        grp = grp.sort_values("month")
        grp["conc_last_6mo"] = grp["on_concession"].rolling(6, min_periods=1).sum().shift(1).fillna(0)
        return grp
    panel = panel.groupby("vmpp_code", group_keys=False).apply(rolling_concession_count)

    print(f"\nPanel built: {len(panel):,} drug-month rows")
    print(f"  Positive labels (next month): {panel['label_next_month'].sum():,} / {len(panel):,} ({panel['label_next_month'].mean():.1%})")
    print(f"  Current month on concession:  {panel['on_concession'].sum():,}")
    print(f"  Unique drugs: {panel['vmpp_code'].nunique():,}")
    print(f"  Date range: {panel['month'].min()} to {panel['month'].max()}")

    return panel


# ─────────────────────────────────────────────
# 8. RUN
# ─────────────────────────────────────────────

def run():
    print("=" * 65)
    print("SCRIPT 11: Time-Series Panel Feature Store")
    print("=" * 65)

    concessions    = load_concessions()
    tariff         = load_tariff()
    price_features = compute_price_features(tariff)
    macro          = load_macro()
    mhra_text      = load_mhra_counts()
    us_names       = load_us_shortage_names()

    print(f"\nUS shortage first-words loaded: {len(us_names)}")

    panel = build_panel(price_features, concessions, macro, mhra_text, us_names)

    # Save full panel
    panel_path = f"{OUT_DIR}/panel_feature_store.csv"
    panel.to_csv(panel_path, index=False)
    print(f"\nFull panel saved: {panel_path}")

    # Save labelled-only subset (rows where next month is known)
    # Drop the last month since we don't know the future label yet
    latest_month = panel["month"].max()
    train = panel[panel["month"] < latest_month].copy()
    train_path = f"{OUT_DIR}/panel_feature_store_train.csv"
    train.to_csv(train_path, index=False)
    print(f"Training subset saved: {train_path}  ({len(train):,} rows)")

    # Label balance stats
    label_stats = pd.DataFrame({
        "split": ["full_panel", "train_subset"],
        "total_rows": [len(panel), len(train)],
        "positive_labels": [panel["label_next_month"].sum(), train["label_next_month"].sum()],
        "positive_rate_pct": [
            round(panel["label_next_month"].mean() * 100, 1),
            round(train["label_next_month"].mean() * 100, 1),
        ],
        "unique_drugs": [panel["vmpp_code"].nunique(), train["vmpp_code"].nunique()],
        "months_covered": [panel["month"].nunique(), train["month"].nunique()],
    })
    label_stats.to_csv(f"{OUT_DIR}/panel_label_summary.csv", index=False)
    print("\nLabel balance summary:")
    print(label_stats.to_string(index=False))

    # Top features preview
    print("\n" + "=" * 65)
    print("SAMPLE: Top 10 highest-risk drug-months (by floor proximity)")
    print("=" * 65)
    cols = ["drug_name", "month", "price_gbp", "floor_proximity",
            "on_concession", "label_next_month", "concession_streak", "conc_last_6mo"]
    available = [c for c in cols if c in panel.columns]
    top = panel[available].sort_values("floor_proximity").head(10)
    print(top.to_string(index=False))

    return panel


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
