# NPT Drug Price Intelligence — Data Scrapers

## Quick Start (Run on your local machine)

```bash
# 1. Install dependencies
pip install requests pandas beautifulsoup4 lxml yfinance

# 2. Test which sources are accessible from your network
python 00_run_all_scrapers.py --test

# 3. Run all scrapers in order
python 00_run_all_scrapers.py

# 4. Or run a single scraper
python 00_run_all_scrapers.py --source 01
```

---

## Data Sources & URLs

| # | Name | URL | Cost | Priority |
|---|------|-----|------|----------|
| 01 | NHSBSA Drug Tariff Part VIIIA | https://opendata.nhsbsa.net/dataset/drug-tariff | FREE | P1 |
| 02 | NHSBSA/CPE Price Concessions | https://cpe.org.uk/dispensing-and-supply/supply-chain/medicine-shortages/price-concessions/ | FREE | P1 |
| 03 | English Prescribing Dataset | https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd | FREE | P1 |
| 04 | MHRA Shortage Alerts & SSPs | https://www.gov.uk/government/publications/serious-shortage-protocols-ssps | FREE | P1 |
| 05 | Market Signals (FX/BoE/ONS/FDA) | Multiple — see scraper | FREE | P2 |
| 06 | Molecule Master (dm+d) | https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/6 | FREE* | P1 |

*dm+d requires free TRUD registration. Takes 5 minutes.

---

## Output Structure

```
data/
├── drug_tariff/
│   ├── drug_tariff_YYYYMM.csv          # Raw tariff download
│   └── tariff_with_floors.csv          # + unprofitable floor calculation
├── concessions/
│   ├── cpe_current_month.csv           # This month's concessions
│   ├── nhsbsa_historical.csv           # All concessions 2019+
│   └── all_concessions_combined.csv    # Merged, deduplicated
├── epd/
│   └── epd_demand_signals.csv          # Demand trends by BNF code
├── mhra/
│   ├── ssps.csv                        # Active Serious Shortage Protocols
│   ├── mhra_rss_alerts.csv             # All MHRA alerts + shortage flag
│   └── govuk_shortage_publications.csv # GOV.UK content search results
├── market_signals/
│   ├── fx_rates_stress.csv             # GBP/INR + stress score daily
│   ├── boe_inflation.csv               # UK inflation + bank rate
│   ├── ons_ppi_pharma.csv              # Pharma producer price index
│   └── openfda_shortages.csv           # US drug shortages (UK leading indicator)
├── molecule_master/
│   └── molecule_master.csv             # BNF → dm+d → clean name mapping
└── pipeline_run_report.csv             # Status of last run
```

---

## Source Details

### 01 — NHSBSA Drug Tariff (Core Signal)
**URL:** https://opendata.nhsbsa.net/dataset/drug-tariff
**API:** https://opendata.nhsbsa.net/api/3/action/package_show?id=drug-tariff
**Format:** CSV, updated monthly (~5th of each month)
**Key fields:** BNF_CODE, DRUG_NAME, PACK_SIZE, BASIC_PRICE (pence)
**What we compute:** 5th percentile 5-year price = unprofitable floor proxy

### 02 — NHSBSA/CPE Price Concessions (Training Labels)
**CPE URL:** https://cpe.org.uk/dispensing-and-supply/supply-chain/medicine-shortages/price-concessions/
**CKAN API:** https://opendata.nhsbsa.net/api/3/action/package_show?id=nhsbsa-national-cost-of-supply-ncso-concessions
**OpenPrescribing:** https://openprescribing.net/api/1.0/ncso-concessions/?format=json
**Format:** HTML table (CPE current month) + CSV (NHSBSA historical) + JSON (OpenPrescribing)
**Key fields:** drug_name, bnf_code, concession_price_p, dt_price_p, month
**What we use:** Every concession event = positive label (is_shortage=1) for ML model

### 03 — English Prescribing Dataset (Demand Signal)
**URL:** https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd
**CKAN SQL API:** https://opendata.nhsbsa.net/api/3/action/datastore_search_sql
**Format:** Large CSV (~500MB/month) — use SQL API to filter by BNF code
**Key fields:** YEAR_MONTH, BNF_CODE, BNF_NAME, ITEMS, NIC, ACTUAL_COST, QUANTITY
**What we compute:** month-on-month demand change, 6-month delta, demand spike flag

### 04 — MHRA Shortage Alerts & SSPs
**SSP page:** https://www.gov.uk/government/publications/serious-shortage-protocols-ssps
**RSS feed:** https://www.gov.uk/drug-safety-update.atom
**GOV.UK API:** https://www.gov.uk/api/search.json?filter_organisations=medicines-and-healthcare-products-regulatory-agency
**Format:** HTML + Atom XML + JSON
**Key fields:** drug_name, ssp_number, issue_date, status

### 05 — Market Signals
**Bank of England:** https://www.bankofengland.co.uk/boeapps/database
**ONS API:** https://api.ons.gov.uk/v1
**OpenFDA:** https://api.fda.gov/drug/shortage.json
**Exchange Rates:** https://api.exchangerate.host/timeseries (free, no key)
**HMRC Trade:** https://api.uktradeinfo.com/OTS

### 06 — Molecule Master / dm+d
**TRUD:** https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/6
*(Free registration required — takes 5 minutes)*
**OpenPrescribing BNF:** https://openprescribing.net/api/1.0/bnf_code/?format=json
**Format:** XML weekly download (dm+d) + JSON API (OpenPrescribing)

---

## Environment Variables

```bash
# Optional — for Companies House manufacturer data enrichment
export COMPANIES_HOUSE_API_KEY="your_key_here"
# Get free key at: https://developer.company-information.service.gov.uk/

# Optional — for OpenFDA higher rate limits
export FDA_API_KEY="your_key_here"
# Get free key at: https://open.fda.gov/apis/authentication/
```

---

## Notes

- All scrapers include fallback methods if primary API is unavailable
- NHSBSA EPD is large (~500MB/month) — the scraper uses CKAN SQL API to filter by BNF code
- dm+d XML requires TRUD registration but is free and updated weekly
- OpenFDA US shortage data is a 2-4 week leading indicator for UK shortages
- The sandbox/VM environment these scripts were written in has egress blocked — run on your local machine
