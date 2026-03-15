"""
SCRAPER 01: NHSBSA Drug Tariff Part VIIIA
==========================================
Source:  https://opendata.nhsbsa.net/dataset/drug-tariff
         https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-viii
Data:    Monthly reimbursement prices for all generic drugs (2014–present)
Use:     Unprofitable floor calculation — core signal for NPT prediction model
Freq:    Monthly (released ~5th of each month for the current month)
Format:  CSV / Excel via CKAN API
"""

import requests
import pandas as pd
import os
import re
from datetime import datetime

OUTPUT_DIR = "data/drug_tariff"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── CKAN API endpoint ────────────────────────────────────────────────────────
CKAN_BASE = "https://opendata.nhsbsa.net/api/3/action"
DATASET_ID = "drug-tariff"  # NHSBSA CKAN dataset ID

def get_tariff_resource_list():
    """Fetch list of all available Drug Tariff files from NHSBSA Open Data Portal."""
    url = f"{CKAN_BASE}/package_show?id={DATASET_ID}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    resources = data["result"]["resources"]
    return [
        {
            "name": res["name"],
            "url":  res["url"],
            "format": res["format"],
            "created": res.get("created", ""),
        }
        for res in resources
        if "VIIIA" in res["name"].upper() or "8A" in res["name"].upper()
    ]

def download_tariff_file(resource_url: str, filename: str) -> pd.DataFrame:
    """Download a single Drug Tariff CSV/Excel and return as DataFrame."""
    r = requests.get(resource_url, timeout=60)
    r.raise_for_status()

    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(r.content)

    if filename.endswith(".csv"):
        df = pd.read_csv(filepath, encoding="latin-1")
    else:
        df = pd.read_excel(filepath, sheet_name=None)
        # Part VIIIA is typically in the first sheet
        df = list(df.values())[0]

    return df

def calculate_unprofitable_floor(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each molecule, calculate:
    - 5th percentile of price over the historical window = proxy unprofitable floor
    - Current price / floor = proximity score (1.0 = at floor, <1.0 = below floor)

    Works with Cat M columns: VMPP Snomed Code, Drug Name, Pack size, Basic price
    """
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Cat M columns → standard NPT schema
    col_map = {
        "vmpp_snomed_code": "vmpp_code",
        "drug_name":        "drug_name",
        "drug":             "drug_name",
        "pack_size":        "pack_size",
        "basic_price":      "price_pence",
        "unnamed:_3":       "unit",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Determine molecule grouping key (prefer vmpp_code, fall back to drug_name)
    if "vmpp_code" in df.columns:
        group_col = "vmpp_code"
        df[group_col] = pd.to_numeric(df[group_col], errors="coerce")
        df = df.dropna(subset=[group_col])
    else:
        group_col = "drug_name"

    # Price column
    df["price_pence"] = pd.to_numeric(df["price_pence"], errors="coerce")
    df = df.dropna(subset=["price_pence"])
    df["price_gbp"] = df["price_pence"] / 100  # Cat M prices are always in pence

    # Floor = 5th percentile of historical prices per molecule
    floors = (
        df.groupby(group_col)["price_gbp"]
        .quantile(0.05)
        .rename("floor_price_gbp")
        .reset_index()
    )

    df = df.merge(floors, on=group_col, how="left")
    df["floor_proximity"] = df["price_gbp"] / df["floor_price_gbp"]
    df["within_15pct_of_floor"] = df["floor_proximity"] <= 1.15

    return df

def run():
    print("=" * 60)
    print("NHSBSA Drug Tariff Scraper")
    print("=" * 60)

    print("\n[1] Fetching Drug Tariff Category M files from NHSBSA direct page...")
    links = scrape_tariff_download_page()

    # Filter to CSV files only and sort newest first
    csv_links = [l for l in links if ".csv" in l["url"].lower()]
    print(f"    Found {len(csv_links)} CSV download links")

    if not csv_links:
        print("ERROR: No CSV links found on NHSBSA Drug Tariff page.")
        return

    # Download multiple files to build a historical dataset for floor calculation
    # Latest ~24 files (covers ~2 years of monthly/quarterly data)
    all_dfs = []
    for link in csv_links[:24]:
        try:
            print(f"  Downloading: {link['text'][:60]}")
            r = requests.get(link["url"], timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                from io import BytesIO
                df_raw = pd.read_csv(BytesIO(r.content), encoding="latin-1", skiprows=2)
                df_raw["source_file"] = link["text"]
                all_dfs.append(df_raw)
        except Exception as e:
            print(f"    SKIP ({e})")

    if not all_dfs:
        print("ERROR: Could not download any tariff files.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\n[2] Combined {len(combined):,} rows from {len(all_dfs)} files")

    # Save raw combined
    raw_path = os.path.join(OUTPUT_DIR, f"drug_tariff_{datetime.now().strftime('%Y%m')}.csv")
    combined.to_csv(raw_path, index=False)

    print("\n[3] Calculating unprofitable floors...")
    df_floors = calculate_unprofitable_floor(combined)
    near_floor = df_floors[df_floors["within_15pct_of_floor"]]
    print(f"    Molecules within 15% of floor: {len(near_floor):,}")

    out_path = os.path.join(OUTPUT_DIR, "tariff_with_floors.csv")
    df_floors.to_csv(out_path, index=False)
    print(f"\n[4] Saved to: {out_path}")

    # Top 20 highest risk
    top_risk = df_floors.sort_values("floor_proximity").head(20)[
        [c for c in ["bnf_code", "drug_name", "price_gbp", "floor_price_gbp", "floor_proximity"] if c in df_floors.columns]
    ]
    print("\nTop 20 molecules closest to unprofitable floor:")
    print(top_risk.to_string(index=False))

# ── ALTERNATIVE: Direct NHSBSA Drug Tariff page scrape ───────────────────────
# If CKAN API is unavailable, scrape the Drug Tariff page directly:
def scrape_tariff_download_page():
    """Scrape the NHSBSA Drug Tariff Part VIII page for download links."""
    from bs4 import BeautifulSoup

    url = "https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-viii"
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.content, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(ext in href.lower() for ext in [".csv", ".xlsx", ".xls"]):
            links.append({
                "text": a.get_text(strip=True),
                "url":  href if href.startswith("http") else "https://www.nhsbsa.nhs.uk" + href
            })

    print(f"Found {len(links)} download links:")
    for link in links:
        print(f"  {link['text']}: {link['url']}")
    return links

if __name__ == "__main__":
    run()
