"""
SCRAPER 03: NHSBSA English Prescribing Dataset (EPD)
=====================================================
Source:  https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd
Data:    Every drug dispensed in England by GP practices — items, quantity,
         actual cost, NIC (Net Ingredient Cost). Jan 2014 to present.
Use:     Demand signal — volume trends, demand spikes, seasonal patterns
Freq:    Monthly (published ~2 months after the prescription month)
Format:  Large CSV files (~500MB/month). Use CKAN API to get file URLs.
Note:    Filter to BNF codes of interest — do NOT download all 500MB monthly.
"""

import requests
import pandas as pd
import os
from io import StringIO, BytesIO
from datetime import datetime, timedelta

OUTPUT_DIR = "data/epd"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CKAN_BASE     = "https://opendata.nhsbsa.net/api/3/action"
DATASET_ID    = "english-prescribing-data-epd"
CKAN_SQL_BASE = "https://opendata.nhsbsa.net/api/3/action/datastore_search_sql"

# BNF code prefixes for generic drugs of interest (first 9 chars = presentation)
# Expand this list with your target molecules
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
]

def get_epd_resource_list() -> list:
    """Get list of all EPD resource files from CKAN."""
    url = f"{CKAN_BASE}/package_show?id={DATASET_ID}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    resources = r.json()["result"]["resources"]
    return [
        {
            "name":    res["name"],
            "url":     res["url"],
            "format":  res.get("format", ""),
            "id":      res.get("id", ""),
            "created": res.get("created", ""),
        }
        for res in resources
    ]

def fetch_epd_for_bnf_codes(resource_id: str, bnf_codes: list, limit: int = 10000) -> pd.DataFrame:
    """
    Use CKAN DataStore SQL API to pull only the rows for target BNF codes.
    Avoids downloading the full 500MB monthly file.

    CKAN SQL API endpoint:
      POST https://opendata.nhsbsa.net/api/3/action/datastore_search_sql
      Body: {"sql": "SELECT ... FROM \"resource_id\" WHERE BNF_CODE LIKE ..."}
    """
    bnf_filter = " OR ".join([f"\"BNF_CODE\" LIKE '{code}%'" for code in bnf_codes[:10]])
    sql = f"""
        SELECT
            "YEAR_MONTH", "BNF_CODE", "BNF_NAME",
            "ITEMS", "NIC", "ACTUAL_COST", "QUANTITY"
        FROM "{resource_id}"
        WHERE {bnf_filter}
        LIMIT {limit}
    """

    url = f"{CKAN_SQL_BASE}?sql={requests.utils.quote(sql)}"
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        return pd.DataFrame()

    result = r.json().get("result", {})
    records = result.get("records", [])
    return pd.DataFrame(records)

def fetch_epd_via_direct_download(resource_url: str, bnf_prefixes: list) -> pd.DataFrame:
    """
    For smaller historical files: download full CSV and filter in-memory.
    Only use for files < 100MB or when SQL API is unavailable.
    """
    print(f"  Downloading from: {resource_url}")
    r = requests.get(resource_url, timeout=120, stream=True)
    r.raise_for_status()

    # Stream into chunks to avoid memory issues
    chunks = []
    for chunk in pd.read_csv(
        BytesIO(r.content),
        chunksize=50000,
        encoding="latin-1",
        usecols=["YEAR_MONTH", "BNF_CODE", "BNF_NAME", "ITEMS", "NIC", "ACTUAL_COST", "QUANTITY"]
    ):
        mask = chunk["BNF_CODE"].astype(str).str[:9].isin(bnf_prefixes)
        filtered = chunk[mask]
        if not filtered.empty:
            chunks.append(filtered)

    if chunks:
        return pd.concat(chunks, ignore_index=True)
    return pd.DataFrame()

def calculate_demand_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive demand pressure signals for the NPT feature store:
    - items_6mo_delta:       change in dispensed items over last 6 months
    - items_mom_change_pct:  month-on-month % change
    - seasonal_factor:       ratio vs same month last year
    """
    df["YEAR_MONTH"] = pd.to_datetime(df["YEAR_MONTH"].astype(str), format="%Y%m")
    df["ITEMS"] = pd.to_numeric(df["ITEMS"], errors="coerce")

    monthly = (
        df.groupby(["BNF_CODE", "BNF_NAME", "YEAR_MONTH"])["ITEMS"]
        .sum()
        .reset_index()
        .sort_values(["BNF_CODE", "YEAR_MONTH"])
    )

    monthly["items_mom_change_pct"] = (
        monthly.groupby("BNF_CODE")["ITEMS"]
        .pct_change(periods=1)
        .mul(100)
        .round(1)
    )

    monthly["items_6mo_delta"] = (
        monthly.groupby("BNF_CODE")["ITEMS"]
        .diff(periods=6)
    )

    monthly["items_yoy_pct"] = (
        monthly.groupby("BNF_CODE")["ITEMS"]
        .pct_change(periods=12)
        .mul(100)
        .round(1)
    )

    # Flag demand spikes (>20% MoM or >15% YoY)
    monthly["demand_spike_flag"] = (
        (monthly["items_mom_change_pct"] > 20) |
        (monthly["items_yoy_pct"] > 15)
    ).astype(int)

    return monthly

def run():
    print("=" * 60)
    print("NHSBSA English Prescribing Dataset (EPD) Scraper")
    print("=" * 60)
    print(f"\nTarget BNF codes: {len(TARGET_BNF_PREFIXES)} molecules")

    print("\n[1] Fetching EPD resource list...")
    try:
        resources = get_epd_resource_list()
        print(f"    Found {len(resources)} EPD files")

        # Get most recent 24 months
        recent = sorted(resources, key=lambda x: x["created"], reverse=True)[:24]

        all_dfs = []
        for res in recent:
            print(f"\n[2] Querying: {res['name']}")
            if res.get("id"):
                df = fetch_epd_for_bnf_codes(res["id"], TARGET_BNF_PREFIXES)
                if not df.empty:
                    all_dfs.append(df)
                    print(f"    Retrieved {len(df):,} rows for target molecules")

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            print(f"\n[3] Computing demand signals...")
            signals = calculate_demand_signals(combined)

            out_path = f"{OUTPUT_DIR}/epd_demand_signals.csv"
            signals.to_csv(out_path, index=False)
            print(f"    Saved to: {out_path}")

            # Show demand spikes
            spikes = signals[signals["demand_spike_flag"] == 1].sort_values("YEAR_MONTH", ascending=False)
            print(f"\n    Demand spike alerts: {len(spikes)} events")
            if not spikes.empty:
                print(spikes[["BNF_CODE", "BNF_NAME", "YEAR_MONTH", "ITEMS", "items_mom_change_pct"]].head(10).to_string(index=False))

    except Exception as e:
        print(f"ERROR: {e}")
        print("Tip: Check CKAN API connectivity. For offline testing, download sample CSV from:")
        print("     https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd")

if __name__ == "__main__":
    run()
