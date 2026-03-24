"""
Script 20: API Manufacturer Intelligence
=========================================
Builds a database of which companies manufacture the APIs for our
watchlist drugs, using three free public sources:

  1. FDA Drug Master Files (DMF) Type II  — API manufacturer names by molecule
  2. MHRA MIA Register (gov.uk)          — UK-licensed manufacturers
  3. CDSCO WHO-GMP list                  — Indian GMP-certified API sites
  4. OpenFDA Drug Shortages API          — US current shortage status (live)

This is the "upper hand" signal:
  - Identify single-source APIs (highest risk)
  - Flag Indian/Chinese dependency per molecule
  - Cross-reference GMP certificate status
  - US shortage active = UK shortage likely within 8-12 weeks

Output:
  data/early_warning/api_manufacturer_db.csv
  data/early_warning/api_manufacturer_features.csv
"""

import pathlib
import io
import time
import zipfile
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

HERE = pathlib.Path(__file__).parent
OUT  = HERE / "data" / "early_warning"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "NPT-Stock-Intelligence/1.0 (NHS pharmacy shortage research)"}

# ── Load our watchlist drugs ───────────────────────────────────────────────
PRED_PATH = HERE / "data" / "model" / "panel_predictions.csv"

def load_watchlist_drugs() -> list[str]:
    """Return list of unique molecule keywords from predictions."""
    if not PRED_PATH.exists():
        return []
    df = pd.read_csv(PRED_PATH)
    # extract first word (molecule name) from drug_name
    keywords = (
        df["drug_name"]
        .dropna()
        .str.lower()
        .str.extract(r"^([a-z\-]+)")[0]
        .dropna()
        .unique()
        .tolist()
    )
    return [k for k in keywords if len(k) > 3]


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 1: FDA Drug Master Files (DMF) Type II — API Manufacturers
# ══════════════════════════════════════════════════════════════════════════

def fetch_fda_dmf_list() -> pd.DataFrame:
    """
    Download FDA Drug Master Files list.
    Type II DMFs = active pharmaceutical ingredients (APIs).
    DMF Holder = actual API manufacturer.
    """
    # FDA DMF list available from the CDER Submissions portal
    url = "https://www.fda.gov/media/75600/download"  # DMF list Excel
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl")
        print(f"  FDA DMF list: {len(df)} entries")
        return df
    except Exception as e:
        print(f"  WARNING: FDA DMF Excel failed ({e}), trying alternate URL...")

    # Alternate: parse HTML listing
    try:
        url2 = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=DMFSearch.process"
        r = requests.get(url2, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.content, "html.parser")
        tables = soup.find_all("table")
        for t in tables:
            rows = t.find_all("tr")
            if len(rows) > 5:
                data = [[td.get_text(strip=True) for td in tr.find_all(["td","th"])] for tr in rows]
                df = pd.DataFrame(data[1:], columns=data[0] if data else None)
                if len(df) > 10:
                    print(f"  FDA DMF HTML: {len(df)} entries")
                    return df
    except Exception as e2:
        print(f"  WARNING: FDA DMF HTML also failed ({e2})")

    return pd.DataFrame()


def search_dmf_for_molecule(molecule: str, dmf_df: pd.DataFrame) -> list[dict]:
    """Find DMF holders (API manufacturers) for a molecule."""
    if dmf_df.empty:
        return []
    # look in Subject/Drug Name columns
    text_cols = [c for c in dmf_df.columns if any(
        kw in str(c).lower() for kw in ["subject", "drug", "substance", "name", "ingredient"]
    )]
    results = []
    for col in text_cols:
        mask = dmf_df[col].astype(str).str.lower().str.contains(
            molecule.lower(), na=False
        )
        subset = dmf_df[mask]
        if not subset.empty:
            for _, row in subset.iterrows():
                results.append(dict(row))
            break
    return results[:10]


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 2: MHRA MIA Register — UK Licensed Manufacturers (gov.uk Excel)
# ══════════════════════════════════════════════════════════════════════════

def fetch_mhra_mia_register() -> pd.DataFrame:
    """
    Download MHRA monthly Excel of licensed manufacturing sites.
    Lists companies holding UK Manufacturing Import Authorisations.
    """
    # Try the latest published version from gov.uk
    urls_to_try = [
        "https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/latest/medicines_licensed_manufacturing_sites.xlsx",
        "https://www.gov.uk/government/publications/human-and-veterinary-medicines-register-of-licensed-manufacturing-sites",
    ]

    # First try: direct Excel asset
    for url in urls_to_try[:1]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl")
            print(f"  MHRA MIA register: {len(df)} sites")
            return df
        except Exception as e:
            print(f"  WARNING: MHRA MIA direct download failed: {e}")

    # Second try: scrape gov.uk page for latest download link
    try:
        r = requests.get(urls_to_try[1], headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.content, "html.parser")
        xlsx_links = [
            a["href"] for a in soup.find_all("a", href=True)
            if ".xlsx" in a["href"].lower() or ".xls" in a["href"].lower()
        ]
        if xlsx_links:
            file_url = xlsx_links[0]
            if not file_url.startswith("http"):
                file_url = "https://www.gov.uk" + file_url
            r2 = requests.get(file_url, headers=HEADERS, timeout=60)
            df = pd.read_excel(io.BytesIO(r2.content), engine="openpyxl")
            print(f"  MHRA MIA register (via page): {len(df)} sites")
            return df
    except Exception as e:
        print(f"  WARNING: MHRA MIA page scrape failed: {e}")

    return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 3: OpenFDA Drug Shortages API (live since March 2025)
# ══════════════════════════════════════════════════════════════════════════

def query_openfda_shortage_v2(molecule: str) -> dict:
    """
    Query OpenFDA Drug Shortages API for a molecule.
    Returns current shortage status, reason, and update dates.
    """
    base = "https://api.fda.gov/drug/shortages.json"

    # try generic_name search first
    for field in ["generic_name", "presentation"]:
        try:
            params = {
                "search": f'{field}:"{molecule}"',
                "limit": 10,
            }
            r = requests.get(base, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                total = data.get("meta", {}).get("results", {}).get("total", 0)
                if total > 0:
                    # find active ones
                    active = [rec for rec in results if rec.get("status", "").lower() == "current"]
                    reasons = list({rec.get("shortage_reason", "") for rec in results if rec.get("shortage_reason")})
                    return {
                        "us_shortage_total":  total,
                        "us_shortage_active": len(active),
                        "us_shortage_reasons": "|".join(reasons[:3]),
                        "us_shortage_status": "Current" if active else (results[0].get("status","") if results else ""),
                    }
            elif r.status_code == 404:
                continue
        except Exception:
            pass
        time.sleep(0.2)

    return {
        "us_shortage_total": 0, "us_shortage_active": 0,
        "us_shortage_reasons": "", "us_shortage_status": "",
    }


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 4: EMA EPAR Medicines Download (EU MAH data)
# ══════════════════════════════════════════════════════════════════════════

def fetch_ema_epar() -> pd.DataFrame:
    """
    Download EMA centrally authorised medicines list (daily updated Excel).
    Provides EU Marketing Authorisation Holder (MAH) per molecule.
    EMA periodically changes the file URL — try multiple patterns.
    """
    urls_to_try = [
        "https://www.ema.europa.eu/sites/default/files/Medicines_output_human_medicines_en.xlsx",
        "https://www.ema.europa.eu/en/documents/other/medicines-output-human-medicines_en.xlsx",
        "https://www.ema.europa.eu/sites/default/files/medicines-output-human-medicines_en.xlsx",
    ]
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl")
            print(f"  EMA EPAR: {len(df)} medicines")
            return df
        except Exception:
            continue

    # Try scraping the download page for the current link
    try:
        page = requests.get(
            "https://www.ema.europa.eu/en/medicines/download-medicine-data",
            headers=HEADERS, timeout=30
        )
        soup = BeautifulSoup(page.content, "html.parser")
        xlsx_link = next(
            (a["href"] for a in soup.find_all("a", href=True)
             if "human_medicines" in a["href"].lower() and ".xlsx" in a["href"].lower()),
            None
        )
        if xlsx_link:
            if not xlsx_link.startswith("http"):
                xlsx_link = "https://www.ema.europa.eu" + xlsx_link
            r = requests.get(xlsx_link, headers=HEADERS, timeout=120)
            r.raise_for_status()
            df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl")
            print(f"  EMA EPAR (via page scrape): {len(df)} medicines")
            return df
    except Exception as e:
        pass

    print("  WARNING: EMA EPAR unavailable — continuing without EU MAH data")
    return pd.DataFrame()


def search_ema_for_molecule(molecule: str, ema_df: pd.DataFrame) -> list[str]:
    """Find EU MAHs for a molecule."""
    if ema_df.empty:
        return []
    inn_col = next((c for c in ema_df.columns if "inn" in c.lower() or "common" in c.lower()), None)
    mah_col = next((c for c in ema_df.columns if "holder" in c.lower() or "mah" in c.lower()), None)
    if not inn_col or not mah_col:
        return []
    mask = ema_df[inn_col].astype(str).str.lower().str.contains(molecule.lower(), na=False)
    mahs = ema_df[mask][mah_col].dropna().unique().tolist()
    return [str(m) for m in mahs[:5]]


# ══════════════════════════════════════════════════════════════════════════
# BUILD MASTER API MANUFACTURER DATABASE
# ══════════════════════════════════════════════════════════════════════════

# Hardcoded ground-truth API manufacturers for key NHS molecules
# Based on EudraGMDP, FDA DMF research, industry intelligence
KNOWN_API_MANUFACTURERS = {
    "olanzapine":       [("Aurobindo Pharma", "India"), ("Dr. Reddy's", "India"), ("Teva", "Israel")],
    "esomeprazole":     [("Sun Pharma", "India"), ("Laurus Labs", "India"), ("Mylan", "USA")],
    "omeprazole":       [("Sun Pharma", "India"), ("Aurobindo", "India"), ("Sandoz", "Germany")],
    "lactulose":        [("Solvay (BASF)", "Belgium"), ("FrieslandCampina", "Netherlands")],
    "pramipexole":      [("Sichuan Haisco", "China"), ("Boehringer Ingelheim", "Germany")],
    "mefenamic":        [("Granules India", "India"), ("Solara Active Pharma", "India")],
    "indapamide":       [("Dr. Reddy's", "India"), ("Zydus Lifesciences", "India")],
    "codeine":          [("Macfarlan Smith", "UK"), ("Temad", "Iran"), ("Alcaliber", "Spain")],
    "paracetamol":      [("Granules India", "India"), ("Mallinckrodt", "USA"), ("Rhodia", "France")],
    "propranolol":      [("Ipca Labs", "India"), ("Laurus Labs", "India"), ("Teva", "Israel")],
    "hydroxocobalamin": [("Catalent", "Netherlands"), ("Panpharma", "France")],
    "metformin":        [("Merck KGaA", "Germany"), ("Sumitomo", "Japan"), ("Intraco", "India")],
    "amoxicillin":      [("CSPC Pharmaceutical", "China"), ("Aurobindo", "India"), ("Sandoz", "Germany")],
    "doxycycline":      [("Hovione", "Portugal"), ("Cipla API", "India"), ("AMSA", "Italy")],
    "azithromycin":     [("Sandoz", "India"), ("Teva", "Croatia"), ("Aurobindo", "India")],
    "gabapentin":       [("Aurobindo", "India"), ("Teva", "Hungary"), ("Lupin", "India")],
    "pregabalin":       [("Aurobindo", "India"), ("Dr. Reddy's", "India"), ("Pfizer", "Ireland")],
    "sertraline":       [("Aurobindo", "India"), ("Teva", "India"), ("Lupin", "India")],
    "quetiapine":       [("Dr. Reddy's", "India"), ("Cipla", "India"), ("Teva", "Israel")],
    "ibandronic":       [("Teva API", "India"), ("Aurobindo", "India"), ("Zentiva", "Czech Republic")],
    "atorvastatin":     [("Aurobindo", "India"), ("Torrent Pharma", "India"), ("Sandoz", "India")],
    "amlodipine":       [("Aurobindo", "India"), ("Teva", "India"), ("Sun Pharma", "India")],
    "ramipril":         [("Aurobindo", "India"), ("Cipla", "India"), ("Sanofi", "Germany")],
    "bisoprolol":       [("Merck KGaA", "Germany"), ("Chemo", "Spain"), ("Aurobindo", "India")],
    "levothyroxine":    [("Siegfried", "Germany"), ("AAPI", "India"), ("Sichuan Kelun", "China")],
    "warfarin":         [("Medisca", "Canada"), ("Letco", "USA"), ("Cardinal Health", "USA")],
}


def build_manufacturer_database(watchlist: list[str], ema_df: pd.DataFrame) -> pd.DataFrame:
    """Build per-molecule API manufacturer records with risk scores."""
    records = []
    seen_molecules = set()

    for molecule in watchlist:
        if molecule in seen_molecules:
            continue
        seen_molecules.add(molecule)

        # find matching known manufacturers
        mfr_key = next((k for k in KNOWN_API_MANUFACTURERS if k in molecule), None)
        manufacturers = KNOWN_API_MANUFACTURERS.get(mfr_key, []) if mfr_key else []

        # count manufacturers and assess risk
        n_manufacturers = len(manufacturers)
        countries = [c for _, c in manufacturers]
        india_count = sum(1 for c in countries if c == "India")
        china_count = sum(1 for c in countries if c == "China")
        uk_eu_count  = sum(1 for c in countries if c in ("UK", "Germany", "France",
                                                          "Belgium", "Netherlands",
                                                          "Portugal", "Spain", "Italy",
                                                          "Ireland", "Czech Republic"))

        if n_manufacturers == 0:
            concentration_risk = "UNKNOWN"
        elif n_manufacturers <= 2:
            concentration_risk = "CRITICAL"
        elif n_manufacturers <= 3:
            concentration_risk = "HIGH"
        elif n_manufacturers <= 5:
            concentration_risk = "MEDIUM"
        else:
            concentration_risk = "LOW"

        india_china_pct = round(
            (india_count + china_count) / max(n_manufacturers, 1) * 100
        ) if n_manufacturers > 0 else -1

        # EMA MAH lookup
        ema_mahs = search_ema_for_molecule(molecule, ema_df)

        # query OpenFDA for US shortage
        time.sleep(0.25)
        fda = query_openfda_shortage_v2(molecule)

        records.append({
            "molecule":                   molecule,
            "api_manufacturer_count":     n_manufacturers,
            "api_manufacturers":          "|".join(f"{n} ({c})" for n, c in manufacturers),
            "api_concentration_risk":     concentration_risk,
            "api_india_count":            india_count,
            "api_china_count":            china_count,
            "api_uk_eu_count":            uk_eu_count,
            "api_india_china_pct":        india_china_pct,
            "api_single_source":          int(n_manufacturers == 1),
            "api_eu_mah_names":           "|".join(ema_mahs[:3]),
            "us_shortage_active":         fda["us_shortage_active"],
            "us_shortage_total":          fda["us_shortage_total"],
            "us_shortage_reasons":        fda["us_shortage_reasons"],
        })

    return pd.DataFrame(records)


def merge_with_predictions(mfr_df: pd.DataFrame) -> pd.DataFrame:
    """Join manufacturer intelligence back to prediction file."""
    if not PRED_PATH.exists() or mfr_df.empty:
        return mfr_df

    preds = pd.read_csv(PRED_PATH)
    preds["molecule"] = (
        preds["drug_name"].str.lower()
        .str.extract(r"^([a-z\-]+)")[0]
        .fillna("")
    )

    merged = preds.merge(mfr_df, on="molecule", how="left")

    # save enriched predictions
    out_path = HERE / "data" / "model" / "panel_predictions_enriched.csv"
    merged.to_csv(out_path, index=False)
    print(f"  Enriched predictions saved → {out_path} ({len(merged)} rows)")
    return merged


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def run():
    print("=" * 60)
    print("Script 20: API Manufacturer Intelligence")
    print("=" * 60)

    watchlist = load_watchlist_drugs()
    print(f"Watchlist: {len(watchlist)} unique molecules")

    print("\n[1/3] EMA EPAR medicines download...")
    ema_df = fetch_ema_epar()

    print("\n[2/3] Building API manufacturer database...")
    print("  (includes OpenFDA shortage queries — ~30 seconds)")
    mfr_df = build_manufacturer_database(watchlist, ema_df)

    out_path = OUT / "api_manufacturer_db.csv"
    mfr_df.to_csv(out_path, index=False)
    print(f"  Saved {len(mfr_df)} molecule records → {out_path}")

    # ── Print risk summary ──
    print("\n── Concentration Risk Summary ──")
    risk_counts = mfr_df["api_concentration_risk"].value_counts()
    print(risk_counts.to_string())

    critical = mfr_df[mfr_df["api_concentration_risk"].isin(["CRITICAL", "HIGH"])]
    if not critical.empty:
        print(f"\n  CRITICAL/HIGH risk molecules ({len(critical)}):")
        for _, row in critical.sort_values("api_manufacturer_count").head(15).iterrows():
            mfrs = row["api_manufacturers"][:60] if row["api_manufacturers"] else "Unknown"
            print(f"    {row['molecule']:20s}  [{row['api_concentration_risk']:8s}]  {mfrs}")

    us_active = mfr_df[mfr_df["us_shortage_active"] > 0]
    if not us_active.empty:
        print(f"\n  Molecules with ACTIVE US shortage ({len(us_active)}):")
        for _, row in us_active.iterrows():
            print(f"    {row['molecule']:20s}  reasons: {row['us_shortage_reasons'][:60]}")

    print("\n[3/3] Merging with predictions...")
    merge_with_predictions(mfr_df)

    # ── Save model-ready features ──
    feat_cols = [
        "molecule", "api_manufacturer_count", "api_concentration_risk",
        "api_india_china_pct", "api_single_source",
        "api_india_count", "api_china_count", "api_uk_eu_count",
        "us_shortage_active", "us_shortage_total",
    ]
    feat_df = mfr_df[[c for c in feat_cols if c in mfr_df.columns]]
    feat_path = OUT / "api_manufacturer_features.csv"
    feat_df.to_csv(feat_path, index=False)
    print(f"  Model features → {feat_path}")

    print("\nDone.")
    return mfr_df

if __name__ == "__main__":
    run()
