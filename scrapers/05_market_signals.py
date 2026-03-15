"""
SCRAPER 05: Market Signals — yfinance, Bank of England, ONS, OpenFDA
====================================================================
Sources:
  A) yfinance     — GBP/INR, GBP/CNY, GBP/USD exchange rates + pharma indices
  B) Bank of England API — UK CPI, PPI, inflation data
  C) ONS API      — Producer Price Index (pharma sector)
  D) OpenFDA API  — US drug shortage database (leading indicator for UK)
  E) HMRC trade   — UK pharmaceutical import volumes

Use:    Macro Cost Environment Score + Supply Disruption early warning
Freq:   Daily (FX) / Monthly (inflation) / Real-time (OpenFDA)
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from io import StringIO
from bs4 import BeautifulSoup

OUTPUT_DIR = "data/market_signals"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NPTResearchBot/1.0)"}

# ── METHOD A: yfinance Exchange Rates ────────────────────────────────────────
def fetch_fx_rates_yfinance(lookback_days: int = 365) -> pd.DataFrame:
    """
    Fetch key currency pairs relevant to API drug manufacturing costs.
    GBP/INR — India API manufacturing (primary)
    GBP/CNY — China API manufacturing
    GBP/USD — USD-denominated commodity prices
    EUR/GBP — EU parallel import economics

    NOTE: If yfinance is unavailable, use the fallback (requests) below.
    """
    try:
        import yfinance as yf
        tickers = {
            "GBPINR=X":  "gbp_inr",  # India API cost proxy
            "GBPCNY=X":  "gbp_cny",  # China API cost proxy
            "GBPUSD=X":  "gbp_usd",  # USD commodity base
            "EURGBP=X":  "eur_gbp",  # EU parallel import economics
        }
        end   = datetime.now()
        start = end - timedelta(days=lookback_days)
        dfs = []
        for ticker, name in tickers.items():
            hist = yf.Ticker(ticker).history(start=start, end=end)[["Close"]].rename(columns={"Close": name})
            dfs.append(hist)
        combined = pd.concat(dfs, axis=1).reset_index().rename(columns={"Date": "date"})
        combined["date"] = pd.to_datetime(combined["date"]).dt.date.astype(str)
        return combined

    except ImportError:
        print("  yfinance not installed — using requests fallback")
        return fetch_fx_rates_requests()

def fetch_fx_rates_requests() -> pd.DataFrame:
    """
    Fallback: use Frankfurter API (completely free, no key required, daily data).
    Source: https://www.frankfurter.app — European Central Bank data
    """
    end_date   = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    url = f"https://api.frankfurter.app/{start_date}..{end_date}?base=GBP&symbols=INR,CNY,USD,EUR"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        print(f"  ERROR: Frankfurter API returned {r.status_code}")
        return pd.DataFrame()

    data = r.json()
    rates = data.get("rates", {})
    records = []
    for date, fx in rates.items():
        records.append({
            "date":    date,
            "gbp_inr": fx.get("INR"),
            "gbp_cny": fx.get("CNY"),
            "gbp_usd": fx.get("USD"),
            "eur_gbp": round(1 / fx["EUR"], 6) if fx.get("EUR") else None,
        })
    df = pd.DataFrame(records).sort_values("date")
    print(f"  Retrieved {len(df)} days of FX data (Frankfurter/ECB)")
    return df

def calculate_fx_stress_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    FX stress = GBP weakening vs INR/CNY = higher API import costs.
    Score: 1 = neutral, >1 = cost pressure, <1 = cost relief.
    Uses 6-month average as baseline.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # For GBP/INR: lower GBP/INR = GBP weaker = more expensive imports
    # Rolling 6-month baseline
    for col in ["gbp_inr", "gbp_cny", "gbp_usd"]:
        if col in df.columns:
            df[f"{col}_6mo_avg"] = df[col].rolling(window=180, min_periods=30).mean()
            df[f"{col}_vs_baseline"] = df[col] / df[f"{col}_6mo_avg"]

    # Composite FX stress (GBP/INR most important; India supplies ~70% of UK generic APIs)
    if "gbp_inr_vs_baseline" in df.columns:
        df["fx_stress_score"] = (
            df["gbp_inr_vs_baseline"] * 0.6 +
            df.get("gbp_cny_vs_baseline", pd.Series(1, index=df.index)) * 0.3 +
            df.get("gbp_usd_vs_baseline", pd.Series(1, index=df.index)) * 0.1
        )
        df["fx_high_stress"] = (df["fx_stress_score"] < 0.95).astype(int)

    return df

# ── METHOD B: Bank of England Statistics API ─────────────────────────────────
def fetch_boe_inflation_data() -> pd.DataFrame:
    """
    BoE free API — no key required.
    Series of interest:
      CPIAUCSL  — UK CPI (consumer prices)
      RPIX      — Retail Price Index excl mortgage interest
      IUMBV34   — PPI Output prices

    API format: https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?...
    Alternative: https://api.bankofengland.co.uk/chart/series/{series_id}
    """
    series = {
        "IUMABEDR":  "boe_bank_rate",         # Bank rate
        "IUMBV34":   "ppi_output_index",       # PPI output prices
    }

    records = []
    for series_id, name in series.items():
        # BoE CSV download endpoint
        url = f"https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp?csv.x=yes&Datefrom=01/Jan/2015&Dateto=now&SeriesCodes={series_id}&CSVF=TN&UsingCodes=Y"
        try:
            r = requests.get(url, timeout=30, headers=HEADERS)
            if r.status_code == 200:
                df = pd.read_csv(StringIO(r.text), skiprows=1)
                df.columns = ["date", name]
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"])
                records.append(df)
                print(f"  BoE {name}: {len(df)} records")
        except Exception as e:
            print(f"  BoE {series_id} error: {e}")

    if records:
        combined = records[0]
        for df in records[1:]:
            combined = combined.merge(df, on="date", how="outer")
        return combined.sort_values("date")
    return pd.DataFrame()

# ── METHOD C: ONS API — PPI Pharmaceuticals ──────────────────────────────────
def fetch_ons_ppi() -> pd.DataFrame:
    """
    ONS Statistics API — Producer Price Index for pharmaceutical products.
    No API key required. Data: monthly from 2000.
    Dataset: MM23 (Producer Price Indices)
    """
    # ONS API v1
    base_url = "https://api.ons.gov.uk/v1"

    # Search for pharma-related PPI series
    search_url = f"{base_url}/search?q=pharmaceutical+producer+price&dataset=mm23"
    try:
        r = requests.get(search_url, timeout=30)
        if r.status_code == 200:
            series_list = r.json().get("items", [])
            print(f"  ONS: found {len(series_list)} relevant series")

            # Fetch data for pharma PPI (series K37F or similar)
            pharma_series = [s for s in series_list if "pharma" in s.get("description", "").lower()]
            if pharma_series:
                series_id = pharma_series[0]["id"]
                data_url = f"{base_url}/series/{series_id}/dataset/mm23/timeseries"
                dr = requests.get(data_url, timeout=30)
                if dr.status_code == 200:
                    return pd.DataFrame(dr.json().get("data", []))
    except Exception as e:
        print(f"  ONS API error: {e}")

    # Fallback: direct download of MM23 bulk data
    print("  ONS API unavailable — using bulk download fallback")
    try:
        r = requests.get("https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/k37f/mm23", timeout=30)
        if r.status_code == 200:
            df = pd.read_csv(StringIO(r.text), skiprows=7)
            df.columns = ["period", "ppi_pharma"]
            return df
    except Exception as e:
        print(f"  ONS fallback error: {e}")

    return pd.DataFrame()

# ── METHOD D: OpenFDA Drug Shortage API ──────────────────────────────────────
def fetch_openfda_shortages(limit: int = 1000) -> pd.DataFrame:
    """
    OpenFDA Drug Shortages endpoint — US market data.
    No API key required for most endpoints.
    US shortages precede UK shortages by 2-4 weeks for common API manufacturers.

    Endpoint: https://api.fda.gov/drug/shortage.json
    Note: If endpoint 404s, use the drug/drugsfda endpoint with status filters.
    """
    endpoints = [
        f"https://api.fda.gov/drug/shortage.json?limit={limit}",
        f"https://api.fda.gov/drug/drugsfda.json?search=shortage&limit=100",
    ]

    for url in endpoints:
        try:
            print(f"  OpenFDA: {url}")
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                df = pd.json_normalize(results)
                print(f"  OpenFDA: {len(df)} shortage records")
                return df
        except Exception as e:
            print(f"  OpenFDA error on {url}: {e}")

    # Fallback: scrape FDA Drug Shortage Database page
    print("  Trying FDA shortage page scrape...")
    try:
        url = "https://www.accessdata.fda.gov/scripts/drugshortages/dsp_SearchResults.cfm?drugName=&shortagetype=All"
        r = requests.get(url, timeout=30, headers=HEADERS)
        soup = BeautifulSoup(r.content, "lxml")
        tables = soup.find_all("table")
        if tables:
            df = pd.read_html(str(tables[0]))[0]
            print(f"  FDA scrape: {len(df)} shortage records")
            return df
    except Exception as e:
        print(f"  FDA scrape error: {e}")

    return pd.DataFrame()

# ── METHOD E: HMRC UK Trade Data ─────────────────────────────────────────────
def fetch_hmrc_pharma_imports() -> pd.DataFrame:
    """
    HMRC UK Trade Data — pharmaceutical import volumes from India/China.
    No API key required. Use the HMRC bulk data download.
    Commodity codes relevant to pharmaceutical APIs:
      2937 — Hormones and their derivatives
      2941 — Antibiotics
      3004 — Medicaments for retail sale
      3006 — Pharmaceutical goods
    """
    # HMRC Overseas Trade Statistics API
    base_url = "https://api.uktradeinfo.com/OTS"
    # Pharmaceutical HS codes
    commodity_codes = ["2937", "2941", "3004", "3006"]

    records = []
    for code in commodity_codes:
        url = f"{base_url}?$filter=CommodityId eq '{code}' and FlowTypeId eq 1&$top=100"  # FlowTypeId 1 = imports
        try:
            r = requests.get(url, timeout=30, headers=HEADERS)
            if r.status_code == 200:
                data = r.json().get("value", [])
                for item in data:
                    item["hs_code"] = code
                    records.append(item)
        except Exception as e:
            print(f"  HMRC API error for {code}: {e}")

    if records:
        df = pd.DataFrame(records)
        print(f"  HMRC trade data: {len(df)} import records")
        return df

    print("  HMRC API unavailable — download from uktradeinfo.com")
    return pd.DataFrame()

def run():
    print("=" * 60)
    print("Market Signals Scraper (FX, BoE, ONS, OpenFDA, HMRC)")
    print("=" * 60)

    # FX Rates
    print("\n[A] Exchange Rates (GBP/INR focus):")
    try:
        df_fx = fetch_fx_rates_yfinance(lookback_days=730)
        if not df_fx.empty:
            df_fx = calculate_fx_stress_score(df_fx)
            df_fx.to_csv(f"{OUTPUT_DIR}/fx_rates_stress.csv", index=False)
            latest = df_fx.tail(1)
            print(f"  Latest GBP/INR: {latest.get('gbp_inr', ['N/A']).values[0]:.4f}")
            if "fx_stress_score" in df_fx.columns:
                print(f"  FX Stress Score (today): {latest['fx_stress_score'].values[0]:.3f}")
    except Exception as e:
        print(f"  FX error: {e}")

    # BoE
    print("\n[B] Bank of England Inflation Data:")
    try:
        df_boe = fetch_boe_inflation_data()
        if not df_boe.empty:
            df_boe.to_csv(f"{OUTPUT_DIR}/boe_inflation.csv", index=False)
    except Exception as e:
        print(f"  BoE error: {e}")

    # ONS PPI
    print("\n[C] ONS Pharma Producer Price Index:")
    try:
        df_ons = fetch_ons_ppi()
        if not df_ons.empty:
            df_ons.to_csv(f"{OUTPUT_DIR}/ons_ppi_pharma.csv", index=False)
    except Exception as e:
        print(f"  ONS error: {e}")

    # OpenFDA
    print("\n[D] OpenFDA US Drug Shortages (UK leading indicator):")
    try:
        df_fda = fetch_openfda_shortages()
        if not df_fda.empty:
            df_fda.to_csv(f"{OUTPUT_DIR}/openfda_shortages.csv", index=False)
    except Exception as e:
        print(f"  OpenFDA error: {e}")

    # HMRC
    print("\n[E] HMRC Pharmaceutical Import Data:")
    try:
        df_hmrc = fetch_hmrc_pharma_imports()
        if not df_hmrc.empty:
            df_hmrc.to_csv(f"{OUTPUT_DIR}/hmrc_pharma_imports.csv", index=False)
    except Exception as e:
        print(f"  HMRC error: {e}")

    print("\n[DONE] Market signals collection complete")

if __name__ == "__main__":
    run()
