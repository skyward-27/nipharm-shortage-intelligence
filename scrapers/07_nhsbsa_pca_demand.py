"""
SCRAPER 07: NHSBSA Prescription Cost Analysis (PCA) — Demand Signal
====================================================================
Source:  https://opendata.nhsbsa.net/dataset/prescription-cost-analysis-pca-monthly-data
Data:    Monthly summary of all prescriptions dispensed in England by BNF code.
         PCA is a pre-aggregated summary (~3MB/month vs EPD's ~500MB/month).
Use:     Demand signal — volume trends, demand spikes, seasonal patterns.
         Replaces Scraper 03 (EPD) which has a broken SQL API.
Freq:    Monthly (published ~2 months after prescription month)
Format:  CSV per month via NHSBSA CKAN API

Note:    PCA differs from EPD in that it is aggregated nationally (not by GP practice).
         For the NPT model this is sufficient — we need total demand, not practice-level.
"""

import requests
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

OUTPUT_DIR = "data/pca_demand"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CKAN_BASE  = "https://opendata.nhsbsa.net/api/3/action"
DATASET_ID = "prescription-cost-analysis-pca-monthly-data"
HEADERS    = {"User-Agent": "Mozilla/5.0 (compatible; NPTResearchBot/1.0)"}

# Target BNF code prefixes — high-volume generics at shortage risk
# Expand this list as needed
TARGET_BNF_PREFIXES = [
    "0601023A0",  # Metformin
    "0212000B0",  # Atorvastatin
    "0212000AA",  # Simvastatin
    "0402030Z0",  # Amoxicillin
    "0501013B0",  # Co-amoxiclav
    "0408010AC",  # Pregabalin
    "0409020S0",  # Omeprazole
    "0602010V0",  # Levothyroxine
    "0205010N0",  # Amlodipine
    "0212000Y0",  # Rosuvastatin
    "0205010D0",  # Lisinopril
    "0205051P0",  # Ramipril
    "0206020A0",  # Bisoprolol
    "0408010A0",  # Gabapentin
    "0407010H0",  # Ibuprofen
    "0407010B0",  # Co-codamol 8/500
    "0601021M0",  # Gliclazide
    "0601023B0",  # Metformin SR
    "0410010B0",  # Fluoxetine
    "0410030C0",  # Sertraline
]


def get_pca_resources() -> list:
    """Get list of all PCA resource files from NHSBSA CKAN."""
    url = f"{CKAN_BASE}/package_show?id={DATASET_ID}"
    r = requests.get(url, timeout=60, headers=HEADERS)
    r.raise_for_status()
    resources = r.json()["result"]["resources"]
    return sorted(
        [{"name": res["name"], "url": res["url"], "id": res.get("id", "")} for res in resources],
        key=lambda x: x["name"],
        reverse=True,
    )


def download_pca_month(resource_url: str) -> pd.DataFrame:
    """Download a single PCA monthly CSV and return as DataFrame."""
    r = requests.get(resource_url, timeout=120, headers=HEADERS)
    if r.status_code != 200:
        return pd.DataFrame()
    df = pd.read_csv(BytesIO(r.content), encoding="latin-1")
    return df


def filter_target_bnf(df: pd.DataFrame, prefixes: list) -> pd.DataFrame:
    """Keep only rows matching target BNF code prefixes."""
    if "BNF_CODE" not in df.columns:
        # Try lowercase
        df.columns = [c.strip().upper() for c in df.columns]
    if "BNF_CODE" not in df.columns:
        return pd.DataFrame()
    mask = df["BNF_CODE"].astype(str).str[:9].isin(prefixes)
    return df[mask].copy()


def calculate_demand_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive demand pressure signals for the NPT feature store:
    - items_mom_change_pct:  month-on-month % change in items dispensed
    - items_6mo_delta:       absolute change in items over 6 months
    - items_yoy_pct:         year-on-year % change
    - demand_spike_flag:     1 if MoM >20% or YoY >15%
    """
    ym_col = next((c for c in df.columns if "YEAR" in c.upper() and "MONTH" in c.upper()), None)
    if not ym_col:
        return df

    df[ym_col] = pd.to_datetime(df[ym_col].astype(str), format="%Y%m", errors="coerce")
    df["ITEMS"] = pd.to_numeric(df.get("ITEMS", 0), errors="coerce")

    monthly = (
        df.groupby(["BNF_CODE", "BNF_NAME", ym_col])["ITEMS"]
        .sum()
        .reset_index()
        .sort_values(["BNF_CODE", ym_col])
        .rename(columns={ym_col: "YEAR_MONTH"})
    )

    monthly["items_mom_change_pct"] = (
        monthly.groupby("BNF_CODE")["ITEMS"].pct_change(1).mul(100).round(1)
    )
    monthly["items_6mo_delta"] = monthly.groupby("BNF_CODE")["ITEMS"].diff(6)
    monthly["items_yoy_pct"] = (
        monthly.groupby("BNF_CODE")["ITEMS"].pct_change(12).mul(100).round(1)
    )
    monthly["demand_spike_flag"] = (
        (monthly["items_mom_change_pct"] > 20) | (monthly["items_yoy_pct"] > 15)
    ).astype(int)

    return monthly


def run():
    print("=" * 60)
    print("NHSBSA PCA Demand Signal Scraper")
    print("=" * 60)
    print(f"\nTarget BNF prefixes: {len(TARGET_BNF_PREFIXES)} molecules")

    print("\n[1] Fetching PCA resource list from NHSBSA CKAN...")
    try:
        resources = get_pca_resources()
        print(f"    Found {len(resources)} monthly PCA files (from {resources[-1]['name']} to {resources[0]['name']})")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    # Download most recent 24 months
    recent = resources[:24]
    all_dfs = []

    for res in recent:
        print(f"\n[2] Downloading: {res['name']}")
        try:
            df_raw = download_pca_month(res["url"])
            if df_raw.empty:
                print(f"    Empty — skipping")
                continue
            print(f"    Full file: {len(df_raw):,} rows, cols: {df_raw.columns.tolist()[:5]}")
            df_filtered = filter_target_bnf(df_raw, TARGET_BNF_PREFIXES)
            if not df_filtered.empty:
                all_dfs.append(df_filtered)
                print(f"    Target molecules: {len(df_filtered):,} rows")
            else:
                print(f"    No target BNF codes found in this file")
        except Exception as e:
            print(f"    ERROR: {e}")

    if not all_dfs:
        print("\nERROR: No PCA data collected. Check CKAN API connectivity.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\n[3] Combined: {len(combined):,} rows across {len(all_dfs)} months")

    print("[4] Computing demand signals...")
    signals = calculate_demand_signals(combined)

    out_path = f"{OUTPUT_DIR}/pca_demand_signals.csv"
    signals.to_csv(out_path, index=False)
    print(f"    Saved to: {out_path}")

    spikes = signals[signals.get("demand_spike_flag", pd.Series(dtype=int)) == 1]
    if not spikes.empty:
        print(f"\n    DEMAND SPIKE ALERTS: {len(spikes)} events")
        print(spikes[["BNF_CODE", "BNF_NAME", "YEAR_MONTH", "ITEMS", "items_mom_change_pct"]].head(10).to_string(index=False))
    else:
        print(f"    No demand spikes detected")


if __name__ == "__main__":
    run()
