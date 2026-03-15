"""
SCRAPER 02: NHSBSA / CPE Price Concessions (NCSO)
===================================================
Sources:
  A) CPE (Community Pharmacy England) — current month concessions (HTML table)
     https://cpe.org.uk/dispensing-and-supply/supply-chain/medicine-shortages/price-concessions/
  B) NHSBSA CKAN API — historical concessions (CSV, 2019+)
     https://opendata.nhsbsa.net/dataset/nhsbsa-national-cost-of-supply-ncso-concessions
  C) OpenPrescribing API — pre-processed concession data (JSON, 2010+)
     https://openprescribing.net/api/1.0/ncso-concessions/?format=json

Data:    Every price concession granted by DHSC; drug name, BNF code,
         concession price, Drug Tariff price, month
Use:     PRIMARY TRAINING LABELS for the ML model (positive = shortage event)
Freq:    Monthly (CPE announces ~5th of each month)
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime

OUTPUT_DIR = "data/concessions"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NPTResearchBot/1.0)"
}

# ── METHOD A: Scrape CPE current-month concession table ──────────────────────
def scrape_cpe_concessions() -> pd.DataFrame:
    """
    Scrape the CPE price concessions page for the current month's concessions.
    Returns a DataFrame with: drug_name, bnf_code, pack_size,
                               drug_tariff_price_p, concession_price_p, month
    """
    url = "https://cpe.org.uk/funding-and-reimbursement/reimbursement/price-concessions/"
    print(f"  Fetching CPE concessions from: {url}")

    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")

    # CPE renders concessions as an HTML table
    tables = soup.find_all("table")
    if not tables:
        print("  WARNING: No table found on CPE page — layout may have changed")
        return pd.DataFrame()

    # Take the largest table (most rows)
    table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = table.find_all("tr")

    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    data = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if cells:
            data.append(dict(zip(headers, cells)))

    df = pd.DataFrame(data)
    df["source"] = "CPE"
    df["scraped_date"] = datetime.now().strftime("%Y-%m-%d")
    df["month"] = datetime.now().strftime("%Y-%m")

    print(f"  Found {len(df)} concessions on CPE page")
    return df

# ── METHOD B: NHSBSA CKAN API — historical concessions ───────────────────────
def fetch_nhsbsa_concessions_ckan(year_from: int = 2019) -> pd.DataFrame:
    """
    Pull historical concessions from NHSBSA Open Data Portal via CKAN API.
    Dataset: nhsbsa-national-cost-of-supply-ncso-concessions
    """
    CKAN_BASE = "https://opendata.nhsbsa.net/api/3/action"
    DATASET_ID = "nhsbsa-national-cost-of-supply-ncso-concessions"

    print(f"  Fetching NHSBSA CKAN dataset: {DATASET_ID}")
    url = f"{CKAN_BASE}/package_show?id={DATASET_ID}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    resources = r.json()["result"]["resources"]
    print(f"  Found {len(resources)} resource files")

    dfs = []
    for res in resources:
        # Filter to CSV files from year_from onwards
        name = res.get("name", "")
        if not any(str(y) in name for y in range(year_from, datetime.now().year + 1)):
            continue
        if res.get("format", "").upper() not in ["CSV", "XLSX", "XLS"]:
            continue

        print(f"  Downloading: {name}")
        file_r = requests.get(res["url"], timeout=60)
        if file_r.status_code == 200:
            from io import BytesIO
            if res["format"].upper() == "CSV":
                df = pd.read_csv(BytesIO(file_r.content), encoding="latin-1")
            else:
                df = pd.read_excel(BytesIO(file_r.content))
            dfs.append(df)

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        print(f"  Total historical concessions: {len(combined):,} rows")
        return combined
    return pd.DataFrame()

# ── METHOD C: OpenPrescribing API — processed concession data ─────────────────
def fetch_openprescribing_concessions() -> pd.DataFrame:
    """
    OpenPrescribing pre-processes NHSBSA concessions and exposes them via API.
    Returns: date, drug, bnf_code, drug_tariff_price, concession_price
    """
    url = "https://openprescribing.net/api/1.0/ncso-concessions/?format=json"
    print(f"  Fetching OpenPrescribing concessions API: {url}")

    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data)
    print(f"  Found {len(df):,} concession records from OpenPrescribing")
    return df

# ── NORMALISE to standard schema ──────────────────────────────────────────────
def normalise_concessions(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Standardise column names across data sources to NPT schema:
      bnf_code | drug_name | pack_size | dt_price_p | concession_price_p
      | price_delta_p | price_delta_pct | month | source | is_shortage
    """
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Map common variations to standard names
    rename_map = {
        "drug":                       "drug_name",
        "drug_name":                  "drug_name",
        "medicine":                   "drug_name",
        "bnf_code":                   "bnf_code",
        "bnf":                        "bnf_code",
        "pack_size":                  "pack_size",
        "drug_tariff_price":          "dt_price_p",
        "dt_price":                   "dt_price_p",
        "basic_price_in_pence":       "dt_price_p",
        "concession_price_in_pence":  "concession_price_p",
        "price_concession":           "concession_price_p",
        "date":                       "month",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Calculate price delta (concession above DT price = shortage severity indicator)
    if "dt_price_p" in df.columns and "concession_price_p" in df.columns:
        df["dt_price_p"] = pd.to_numeric(df["dt_price_p"], errors="coerce")
        df["concession_price_p"] = pd.to_numeric(df["concession_price_p"], errors="coerce")
        df["price_delta_p"] = df["concession_price_p"] - df["dt_price_p"]
        df["price_delta_pct"] = (df["price_delta_p"] / df["dt_price_p"] * 100).round(1)

    df["source"] = source
    df["is_shortage"] = 1  # All concession events are positive shortage labels

    return df

def run():
    print("=" * 60)
    print("NCSO Price Concessions Scraper")
    print("=" * 60)
    all_dfs = []

    # Try each method in order of preference
    try:
        print("\n[METHOD A] CPE current-month scrape:")
        df_cpe = scrape_cpe_concessions()
        if not df_cpe.empty:
            df_cpe = normalise_concessions(df_cpe, "CPE")
            all_dfs.append(df_cpe)
            df_cpe.to_csv(f"{OUTPUT_DIR}/cpe_current_month.csv", index=False)
    except Exception as e:
        print(f"  ERROR: {e}")

    try:
        print("\n[METHOD B] NHSBSA CKAN historical:")
        df_nhsbsa = fetch_nhsbsa_concessions_ckan(year_from=2019)
        if not df_nhsbsa.empty:
            df_nhsbsa = normalise_concessions(df_nhsbsa, "NHSBSA")
            all_dfs.append(df_nhsbsa)
            df_nhsbsa.to_csv(f"{OUTPUT_DIR}/nhsbsa_historical.csv", index=False)
    except Exception as e:
        print(f"  ERROR: {e}")

    try:
        print("\n[METHOD C] OpenPrescribing API:")
        df_op = fetch_openprescribing_concessions()
        if not df_op.empty:
            df_op = normalise_concessions(df_op, "OpenPrescribing")
            all_dfs.append(df_op)
            df_op.to_csv(f"{OUTPUT_DIR}/openprescribing_concessions.csv", index=False)
    except Exception as e:
        print(f"  ERROR: {e}")

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        # Deduplicate on available keys — bnf_code may not exist if only CPE data
        dedup_cols = [c for c in ["bnf_code", "drug_name", "month"] if c in combined.columns]
        combined = combined.drop_duplicates(subset=dedup_cols, keep="first")
        combined.to_csv(f"{OUTPUT_DIR}/all_concessions_combined.csv", index=False)
        print(f"\n[DONE] Total unique concession events: {len(combined):,}")
        print(f"       Saved to: {OUTPUT_DIR}/all_concessions_combined.csv")

        # Summary statistics
        print(f"\nDate range: {combined['month'].min()} to {combined['month'].max()}")
        id_col = "bnf_code" if "bnf_code" in combined.columns else "drug_name"
        print(f"Unique molecules affected: {combined[id_col].nunique()}")
        if "price_delta_pct" in combined.columns:
            print(f"Avg concession uplift: {combined['price_delta_pct'].mean():.1f}%")
    else:
        print("\nERROR: No concession data retrieved from any source.")

if __name__ == "__main__":
    run()
