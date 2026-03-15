"""
NPT DRUG PRICE INTELLIGENCE PLATFORM
=====================================
Master Data Pipeline Runner
Run this script to execute all scrapers in the correct order.

Usage:
    python 00_run_all_scrapers.py              # Run everything
    python 00_run_all_scrapers.py --source 01  # Run only scraper 01
    python 00_run_all_scrapers.py --test       # Test connectivity only

Data Sources Covered:
    01 — NHSBSA Drug Tariff Part VIIIA         (unprofitable floor)
    02 — NHSBSA/CPE Price Concessions (NCSO)   (ML training labels)
    03 — English Prescribing Dataset (EPD)     (demand signals)
    04 — MHRA Shortage Alerts & SSPs           (ground truth labels)
    05 — Market Signals (FX, BoE, ONS, OpenFDA)(macro cost signals)
    06 — Molecule Master Builder               (identity resolution)

Requirements:
    pip install requests pandas beautifulsoup4 lxml
    pip install yfinance  (optional — falls back to exchangerate.host)

Output:
    All data saved to ./data/ subdirectories as CSV files
    Summary report saved to ./data/pipeline_run_report.csv
"""

import sys
import os
import time
import traceback
from datetime import datetime

os.makedirs("data", exist_ok=True)

# ── SOURCE REGISTRY ───────────────────────────────────────────────────────────
SOURCES = {
    "01": {
        "name":        "NHSBSA Drug Tariff (Category M)",
        "module":      "01_nhsbsa_drug_tariff",
        "url":         "https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/drug-tariff/drug-tariff-part-viii",
        "output_dir":  "data/drug_tariff",
        "priority":    1,
        "cost":        "FREE",
        "description": "Cat M reimbursement prices (direct NHSBSA page). Core signal: unprofitable floor. ✅ WORKING",
    },
    "02": {
        "name":        "CPE Price Concessions (current month)",
        "module":      "02_ncso_price_concessions",
        "url":         "https://cpe.org.uk/funding-and-reimbursement/reimbursement/price-concessions/",
        "output_dir":  "data/concessions",
        "priority":    1,
        "cost":        "FREE",
        "description": "Current month concessions from CPE. Primary ML training labels. ✅ WORKING (URL moved)",
    },
    "03": {
        "name":        "English Prescribing Dataset (EPD) — BROKEN",
        "module":      "03_nhsbsa_epd_prescribing",
        "url":         "https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd",
        "output_dir":  "data/epd",
        "priority":    3,
        "cost":        "FREE",
        "description": "BROKEN: NHSBSA SQL API returns 500. Use scraper 07 (PCA) instead.",
    },
    "04": {
        "name":        "MHRA Shortage Alerts & SSPs",
        "module":      "04_mhra_shortage_alerts",
        "url":         "https://www.gov.uk/government/publications/serious-shortage-protocols-ssps",
        "output_dir":  "data/mhra",
        "priority":    1,
        "cost":        "FREE",
        "description": "MHRA official shortage declarations and Serious Shortage Protocols.",
    },
    "05": {
        "name":        "Market Signals (FX / BoE / ONS / OpenFDA)",
        "module":      "05_market_signals",
        "url":         "Multiple — see scraper for details",
        "output_dir":  "data/market_signals",
        "priority":    2,
        "cost":        "FREE",
        "description": "GBP/INR FX rates, UK inflation, pharma PPI, US FDA shortage early warnings.",
    },
    "06": {
        "name":        "Molecule Master Builder",
        "module":      "06_molecule_master",
        "url":         "https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/6",
        "output_dir":  "data/molecule_master",
        "priority":    1,
        "cost":        "FREE",
        "description": "BNF → dm+d → product name identity resolution. Must run before any JOIN.",
    },
    "07": {
        "name":        "NHSBSA PCA Demand Signal",
        "module":      "07_nhsbsa_pca_demand",
        "url":         "https://opendata.nhsbsa.net/dataset/prescription-cost-analysis-pca-monthly-data",
        "output_dir":  "data/pca_demand",
        "priority":    1,
        "cost":        "FREE",
        "description": "Monthly PCA aggregates — demand trends per BNF code. Replaces broken EPD scraper. ✅ WORKING",
    },
    "08": {
        "name":        "CPE Historical Concessions Archive",
        "module":      "08_cpe_historical_concessions",
        "url":         "https://cpe.org.uk/funding-and-reimbursement/reimbursement/price-concessions/",
        "output_dir":  "data/concessions",
        "priority":    1,
        "cost":        "FREE",
        "description": "Historical CPE concessions (archive months). Run once to build ML training labels. ✅ WORKING",
    },
}

# ── CONNECTIVITY TEST ─────────────────────────────────────────────────────────
def test_connectivity() -> dict:
    """Quick check which data sources are reachable from the current network."""
    import requests

    test_urls = {
        "NHSBSA CKAN API":      "https://opendata.nhsbsa.net/api/3/action/site_read",
        "CPE Concessions":      "https://cpe.org.uk/dispensing-and-supply/supply-chain/medicine-shortages/price-concessions/",
        "OpenPrescribing API":  "https://openprescribing.net/api/1.0/bnf_code/?format=json&limit=1",
        "MHRA SSP GOV.UK":      "https://www.gov.uk/government/publications/serious-shortage-protocols-ssps",
        "OpenFDA":              "https://api.fda.gov/drug/event.json?limit=1",
        "Bank of England API":  "https://www.bankofengland.co.uk/boeapps/database",
        "ONS API":              "https://api.ons.gov.uk/v1/datasets",
        "Companies House":      "https://api.company-information.service.gov.uk/",
        "ClinicalTrials.gov":   "https://clinicaltrials.gov/api/v2/studies?format=json&pageSize=1",
        "EMA EPAR":             "https://www.ema.europa.eu/en/medicines/field_ema_web_categories%253Aname_field/Human/ema_group_types/ema_medicine",
        "HMRC Trade Data":      "https://www.uktradeinfo.com/trade-data/",
        "Exchange Rate API":    "https://api.exchangerate.host/latest?base=GBP&symbols=INR,CNY,USD",
        "GOV.UK Content API":   "https://www.gov.uk/api/search.json?q=drug+shortage&count=1",
    }

    results = {}
    print("\n" + "=" * 60)
    print("CONNECTIVITY TEST — Which sources are accessible?")
    print("=" * 60)

    for name, url in test_urls.items():
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            status = "✅ ACCESSIBLE" if r.status_code < 400 else f"⚠️  HTTP {r.status_code}"
            results[name] = {"url": url, "status": status, "http_code": r.status_code}
        except requests.exceptions.ConnectionError:
            status = "❌ BLOCKED/UNREACHABLE"
            results[name] = {"url": url, "status": status, "http_code": None}
        except Exception as e:
            status = f"❌ ERROR: {str(e)[:40]}"
            results[name] = {"url": url, "status": status, "http_code": None}

        print(f"  {status:30s}  {name}")

    # Save results
    df = pd.DataFrame([{"source": k, **v} for k, v in results.items()])
    df.to_csv("data/connectivity_test.csv", index=False)
    print(f"\nResults saved to: data/connectivity_test.csv")

    accessible = sum(1 for v in results.values() if "ACCESSIBLE" in v["status"])
    print(f"\n{accessible}/{len(results)} sources accessible from current network")
    return results

# ── PIPELINE RUNNER ───────────────────────────────────────────────────────────
def run_scraper(source_id: str) -> dict:
    """Run a single scraper and return a status report."""
    source = SOURCES.get(source_id)
    if not source:
        return {"id": source_id, "status": "ERROR", "message": "Unknown source ID"}

    print(f"\n{'='*60}")
    print(f"[{source_id}] {source['name']}")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        # Dynamically import and run the scraper
        module_name = source["module"]
        spec = importlib.util.spec_from_file_location(module_name, f"{module_name}.py")
        if spec is None:
            return {"id": source_id, "status": "ERROR", "message": f"File {module_name}.py not found"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.run()

        elapsed = round(time.time() - start_time, 1)
        return {
            "id":       source_id,
            "name":     source["name"],
            "status":   "SUCCESS",
            "elapsed_s": elapsed,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        print(f"\nERROR in {source_id}: {e}")
        traceback.print_exc()
        return {
            "id":        source_id,
            "name":      source["name"],
            "status":    "ERROR",
            "message":   str(e)[:200],
            "elapsed_s": elapsed,
            "timestamp": datetime.now().isoformat(),
        }

def print_source_map():
    """Print a formatted map of all sources."""
    print("\n" + "=" * 60)
    print("NPT DATA SOURCE MAP")
    print("=" * 60)
    for sid, s in sorted(SOURCES.items()):
        print(f"\n  [{sid}] {s['name']}")
        print(f"       Cost:        {s['cost']}")
        print(f"       Priority:    {s['priority']} (1=PoC essential, 2=Phase 2)")
        print(f"       URL:         {s['url']}")
        print(f"       Description: {s['description']}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import importlib.util
    import pandas as pd

    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    if "--sources" in args or "--map" in args:
        print_source_map()
        sys.exit(0)

    if "--test" in args:
        test_connectivity()
        sys.exit(0)

    # Which sources to run
    if "--source" in args:
        idx = args.index("--source")
        target_sources = [args[idx + 1]]
    else:
        # Run all in priority order
        target_sources = sorted(SOURCES.keys())

    print("=" * 60)
    print("NPT DRUG PRICE INTELLIGENCE — DATA PIPELINE")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # First run connectivity test
    print("\nRunning connectivity test...")
    conn_results = test_connectivity()

    # Run scrapers
    reports = []
    for sid in target_sources:
        report = run_scraper(sid)
        reports.append(report)

    # Summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    for r in reports:
        icon = "✅" if r["status"] == "SUCCESS" else "❌"
        print(f"  {icon} [{r['id']}] {r.get('name', '')} — {r['status']} ({r.get('elapsed_s', '?')}s)")

    # Save report
    report_df = pd.DataFrame(reports)
    report_path = "data/pipeline_run_report.csv"
    report_df.to_csv(report_path, index=False)
    print(f"\nFull report saved: {report_path}")

    success_count = sum(1 for r in reports if r["status"] == "SUCCESS")
    print(f"\nCompleted: {success_count}/{len(reports)} scrapers successful")
