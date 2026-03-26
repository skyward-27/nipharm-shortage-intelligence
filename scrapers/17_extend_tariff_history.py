"""
SCRIPT 17: Extend Cat M Tariff History (2021 → 2026)
=====================================================
Downloads ALL Cat M quarterly CSVs from NHSBSA (Jan 2021 → present).
Currently we only have 24 months (Jan 2024 → Mar 2026).
This adds ~3 more years of price history, giving the panel model
proper price features for 2021-2023 concession events.

Outputs:
  data/drug_tariff/catm_history_all.csv   — all quarters combined
  data/drug_tariff/drug_tariff_extended.csv — merged with existing tariff
"""

import requests
import pandas as pd
import numpy as np
import os, re, io, time
from bs4 import BeautifulSoup

BASE    = "https://www.nhsbsa.nhs.uk"
PAGE    = BASE + "/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-viii"
OUT_DIR = "data/drug_tariff"
os.makedirs(OUT_DIR, exist_ok=True)

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
QUARTER_MAP = {
    "quarter 1": "April", "quarter 2": "July",
    "quarter 3": "October", "quarter 4": "January",
}


def parse_label_to_period(label: str):
    """Convert link text like 'Category M Prices - Quarter 4 January 2026' to pd.Period."""
    label = label.lower().strip()
    # Remove prefix and size suffix
    label = re.sub(r'category\s*m prices\s*[-–]?\s*', '', label)
    label = re.sub(r'\(.*?\)', '', label).strip()
    label = re.sub(r'updated', '', label).strip()

    # Try month name + year  e.g. "september 2025"
    m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', label)
    if m:
        month_num = MONTH_MAP[m.group(1)]
        year = int(m.group(2))
        return pd.Period(f"{year}-{month_num:02d}", freq="M")

    # Try quarter + month + year  e.g. "quarter 4 january 2026"
    m = re.search(r'(quarter \d)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', label)
    if m:
        month_num = MONTH_MAP[m.group(2)]
        year = int(m.group(3))
        return pd.Period(f"{year}-{month_num:02d}", freq="M")

    return None


def get_csv_links():
    """Scrape NHSBSA page for all Cat M CSV download links."""
    r = requests.get(PAGE, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)

        if "Cat" not in text and "Category" not in text:
            continue
        if ".csv" not in href.lower() and "csv" not in text.lower():
            continue
        if "CSV" not in text:
            continue

        period = parse_label_to_period(text)
        if period is None:
            continue

        url = BASE + href if href.startswith("/") else href
        results.append({"label": text, "period": period, "url": url})

    # Deduplicate by period (keep first)
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["period"]):
        if r["period"] not in seen:
            seen.add(r["period"])
            unique.append(r)

    print(f"Found {len(unique)} Cat M CSV files  ({unique[0]['period']} → {unique[-1]['period']})")
    return unique


def download_catm(resource: dict) -> pd.DataFrame:
    """Download one Cat M CSV and return normalised DataFrame."""
    try:
        r = requests.get(resource["url"], timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            return pd.DataFrame()

        # Files have title row + blank row before headers (row index 2)
        df = pd.read_csv(io.StringIO(r.text), header=2, dtype=str)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Normalise column names across different file vintages
        rename = {
            "vmpp_snomed_code": "vmpp_code",
            "snomed_code":       "vmpp_code",
            "drug_name":         "drug_name",
            "pack_size":         "pack_size",
            "basic_price":       "basic_price_pence",
            "price_(pence)":     "basic_price_pence",
            "price":             "basic_price_pence",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        if "vmpp_code" not in df.columns or "basic_price_pence" not in df.columns:
            print(f"  Missing cols: {list(df.columns)}")
            return pd.DataFrame()

        df["vmpp_code"] = pd.to_numeric(df["vmpp_code"], errors="coerce")
        df = df.dropna(subset=["vmpp_code"])
        df["vmpp_code"] = df["vmpp_code"].astype(np.int64).astype(str)

        df["price_gbp"] = pd.to_numeric(df["basic_price_pence"], errors="coerce") / 100
        df = df.dropna(subset=["price_gbp"])

        df["tariff_month"]  = resource["period"]
        df["tariff_month_str"] = str(resource["period"])
        df["source_label"]  = resource["label"]

        keep = ["vmpp_code", "drug_name", "pack_size", "price_gbp",
                "tariff_month", "tariff_month_str", "source_label"]
        df = df[[c for c in keep if c in df.columns]]

        return df

    except Exception as e:
        print(f"  Error: {e}")
        return pd.DataFrame()


def run():
    print("=" * 65)
    print("SCRIPT 17: Extend Cat M Tariff History")
    print("=" * 65)

    links = get_csv_links()

    all_months = []
    for i, res in enumerate(links):
        print(f"  [{i+1:02d}/{len(links)}] {res['period']}...", end=" ", flush=True)
        df = download_catm(res)
        if len(df):
            all_months.append(df)
            print(f"{len(df):,} VMPPs")
        else:
            print("skipped")
        time.sleep(0.25)

    if not all_months:
        print("No data downloaded.")
        return

    combined = pd.concat(all_months, ignore_index=True)
    out_path = f"{OUT_DIR}/catm_history_all.csv"
    combined.to_csv(out_path, index=False)

    print(f"\nCombined: {len(combined):,} rows")
    print(f"Months  : {combined['tariff_month_str'].nunique()}  ({combined['tariff_month_str'].min()} → {combined['tariff_month_str'].max()})")
    print(f"VMPPs   : {combined['vmpp_code'].nunique():,} unique")
    print(f"Saved   : {out_path}")

    # Quick summary per year
    combined["year"] = combined["tariff_month_str"].str[:4]
    print("\nRows per year:")
    print(combined.groupby("year").size().to_string())

    return combined


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
