"""
SCRIPT 15: FRED — Pharma & Packaging PPI (Cost-Push Signals)
=============================================================
Fetches Producer Price Index series from FRED (Federal Reserve Bank of St. Louis).
These are COST-PUSH signals: when manufacturing costs rise, drug prices get squeezed
toward the unprofitable floor, increasing shortage risk.

Series used:
  PCU325412325412  — Pharmaceutical Preparation Manufacturing PPI (US, monthly)
  WPU0913          — Plastics & Synthetic Rubber PPI (packaging)
  WPU061           — Industrial Chemicals PPI (API feedstock)
  DPCCRV1Q225SBEA  — Alternative: PCE Price Index for Pharma (quarterly)

FRED API: https://fred.stlouisfed.org/docs/api/fred/
API Key: Free from https://fred.stlouisfed.org/docs/api/api_key.html
         (Register with email — instant approval, no payment)

Outputs:
  data/fred/fred_ppi_pharma.csv     — pharma manufacturing PPI
  data/fred/fred_ppi_plastics.csv   — plastics packaging PPI
  data/fred/fred_cost_push.csv      — combined monthly cost-push index
"""

import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

OUT_DIR = "data/fred"
os.makedirs(OUT_DIR, exist_ok=True)

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# Series to download — no API key needed for CSV endpoint
SERIES = {
    "pharma_ppi":      "PCU325412325412",   # pharma manufacturing PPI
    "plastics_ppi":    "WPU0913",            # plastics & rubber PPI
    "chemicals_ppi":   "WPU061",             # industrial chemicals
    "medical_ppi":     "PCU3254132541",      # pharmaceutical & medicine mfg
}


def fetch_fred_series(series_id: str, name: str) -> pd.DataFrame:
    """
    Download a FRED series via the public CSV endpoint (no API key needed).
    URL: https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES_ID>
    """
    url = f"{FRED_BASE}?id={series_id}"
    try:
        r = requests.get(url, timeout=120,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; NiPharm/1.0)"})
        if r.status_code != 200:
            print(f"  [{series_id}] HTTP {r.status_code}")
            return pd.DataFrame()

        # FRED CSV has two columns: DATE, VALUE
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])
        df["series_id"] = series_id
        df["series_name"] = name
        df["month"] = df["date"].dt.to_period("M").astype(str)

        print(f"  [{series_id}] {len(df):,} rows  ({df['date'].min().date()} → {df['date'].max().date()})")
        return df

    except Exception as e:
        print(f"  [{series_id}] Error: {e}")
        return pd.DataFrame()


def compute_cost_push_index(df_combined: pd.DataFrame) -> pd.DataFrame:
    """
    Build a monthly composite cost-push index:
      - Normalise each series to 100 at 2020-01
      - Average available series per month
      - MoM % change
      - 3-month rolling average
      - cost_stress flag: index > 110 (10% above 2020 baseline)
    """
    pivot = df_combined.pivot_table(
        index="month", columns="series_name", values="value", aggfunc="last"
    )

    # Normalise to Jan 2020 = 100
    base_month = "2020-01"
    if base_month in pivot.index:
        base = pivot.loc[base_month]
        pivot = pivot / base * 100
    else:
        # Use first available month as base
        pivot = pivot / pivot.iloc[0] * 100

    pivot["composite_index"] = pivot.mean(axis=1)
    pivot["mom_pct"] = pivot["composite_index"].pct_change() * 100
    pivot["rolling_3mo"] = pivot["composite_index"].rolling(3).mean()
    pivot["cost_stress"] = (pivot["composite_index"] > 110).astype(int)
    pivot = pivot.reset_index()

    return pivot


def run():
    print("=" * 65)
    print("SCRIPT 15: FRED — Pharma & Packaging PPI")
    print("=" * 65)

    all_series = []
    for name, series_id in SERIES.items():
        print(f"  Fetching {name} ({series_id})...")
        df = fetch_fred_series(series_id, name)
        if len(df):
            all_series.append(df)
            df.to_csv(f"{OUT_DIR}/fred_{name}.csv", index=False)

    if not all_series:
        print("\nNo FRED data retrieved.")
        print("If all series returned 403/errors, FRED may be blocking automated requests.")
        print("Manual download: https://fred.stlouisfed.org/series/PCU325412325412")
        print("Click 'Download' → CSV → save to data/fred/")
        return pd.DataFrame()

    combined = pd.concat(all_series, ignore_index=True)
    combined.to_csv(f"{OUT_DIR}/fred_ppi_all_series.csv", index=False)

    # Cost-push composite
    cost_push = compute_cost_push_index(combined)
    cost_push.to_csv(f"{OUT_DIR}/fred_cost_push.csv", index=False)

    print(f"\nAll series saved: {OUT_DIR}/fred_ppi_all_series.csv  ({len(combined):,} rows)")
    print(f"Cost-push index: {OUT_DIR}/fred_cost_push.csv  ({len(cost_push):,} months)")

    # Latest reading
    latest = cost_push.dropna(subset=["composite_index"]).iloc[-1]
    print(f"\nLatest cost-push index: {latest['composite_index']:.1f}  (month: {latest['month']})")
    print(f"Cost stress flag: {'YES ⚠' if latest.get('cost_stress', 0) else 'No'}")

    stress_months = cost_push[cost_push["cost_stress"] == 1]
    print(f"Months under cost stress: {len(stress_months)}")

    return cost_push


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
