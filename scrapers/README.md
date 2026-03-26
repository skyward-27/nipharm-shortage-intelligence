# 💊 Nipharma Tech Stock Intelligence Unit

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nipharma-stock-intelligence.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Scikit-learn](https://img.shields.io/badge/scikit--learn-Random%20Forest-orange?logo=scikit-learn)
![License](https://img.shields.io/badge/license-Private-red)

> **Predicting NHS drug shortages before they happen — 2–6 weeks ahead of official announcements.**

An ML platform that monitors 14+ UK pharmaceutical data sources, builds a 44,363-row time-series panel, and ranks 758 generic drugs by their probability of entering NHS price concession (shortage) — giving pharmacy procurement teams a critical procurement advantage.

---

## Live Dashboard

**[nipharma-stock-intelligence.streamlit.app](https://nipharma-stock-intelligence.streamlit.app)**

> _Screenshot placeholder — add a screenshot of the dashboard here_

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Dashboard Pages](#dashboard-pages)
3. [Model Performance](#model-performance)
4. [Data Sources](#data-sources)
5. [How the Model Works](#how-the-model-works)
6. [Quick Start](#quick-start)
7. [Project Structure](#project-structure)
8. [Deployment](#deployment)
9. [Critical Risk Molecules](#critical-risk-molecules-march-2026)
10. [Roadmap](#roadmap)
11. [Data Privacy](#data-privacy)
12. [License](#license)

---

## What It Does

NHS price concessions (shortages) are announced by the Community Pharmacy England (CPE) on or around the 10th of each month. By that point, prices have already spiked and stock is already constrained. This platform predicts which drugs will enter concession **2–6 weeks before** the announcement.

**Core pipeline:**

- Monitors **14+ UK pharmaceutical data sources** daily, weekly, and monthly — from NHS Drug Tariff prices to MHRA shortage alerts to GBP/INR exchange rates
- Builds a **44,363-row time-series panel** of drug × month feature vectors (758 drugs, 74 months)
- Trains a **Random Forest classifier** (v6, 300 trees, balanced class weights) to predict next-month NHS price concessions
- Surfaces **BUY NOW / BUY AHEAD / WATCH** procurement signals via a 7-page Streamlit dashboard
- Powers a **Claude AI analyst** (`agent.py`) for natural-language buying queries: _"What should I stock up on this week?"_

---

## Dashboard Pages

| Page | Description |
|---|---|
| 🏠 **Intelligence Dashboard** | ML predictions, critical alert banners, 3-column drug cards, one-click procurement order export |
| ⚠️ **Early Warning** | Live MHRA RSS alerts, FDA warning letters, CPE shortage news feeds |
| 🔗 **Supply Chain Risk** | API cascade dependency clusters, manufacturer concentration scores, US shortage cross-reference |
| 🔍 **Drug Lookup** | Per-drug price history, concession timeline, full supply chain profile |
| 📈 **Concession Trends** | Monthly NHS concession counts, year-on-year comparison charts |
| 📡 **Market Signals** | Brent crude price, GBP/INR FX rate, Bank of England base rate |
| 🤖 **Model Info** | RF v6 metrics, feature importance ranking, pipeline architecture diagram |

---

## Model Performance

Random Forest v6 — trained on 44,363 drug-month rows (January 2020 – February 2026).

| Metric | Score | Description |
|---|---|---|
| ROC-AUC | **0.998** | Near-perfect shortage discrimination |
| PR-AUC | **0.990** | High precision on positive class |
| F1 Score | **0.932** | Strong precision/recall balance |
| Training rows | **44,363** | 74 months × 758 drugs |
| Features | **27** | Across 7 signal categories |

**Feature categories (7 signal domains):**

1. Concession history — `concession_streak`, `on_concession`, `months_since_last_concession`
2. Price pressure — `price_vs_floor`, `price_momentum_3m`, `tariff_cut_flag`
3. Demand signals — `demand_spike_flag`, `items_mom_change`, `demand_volatility`
4. Macro environment — `gbp_inr_stress`, `boe_base_rate`, `brent_crude_price`
5. Regulatory alerts — `mhra_alert_count`, `ssp_active`, `fda_warning_flag`
6. Supply chain risk — `api_cascade_score`, `manufacturer_concentration`, `us_shortage_flag`
7. Manufacturer intelligence — `single_source_flag`, `country_risk_score`, `api_country`

**Key insight:** `concession_streak` (27.6% importance) and `on_concession` (25.8%) dominate — shortages are momentum-driven. The model excels at predicting continuation; early warning features (`mhra_alert_count`, `us_shortage_flag`) detect new shortage events.

---

## Data Sources

All data sources use **free public APIs** — no paid subscriptions required.

| Script | Source | Data | Frequency |
|---|---|---|---|
| `01` | NHSBSA Drug Tariff | 15,379 Category M prices (24 months) | Monthly |
| `02` | CPE Price Concessions | 7,742 concession records (2020–2026) | Monthly |
| `04` | MHRA Shortage Alerts | 3,372 regulatory publications | Weekly |
| `05` | Market Signals | GBP/INR FX, BoE base rate, US shortages | Daily |
| `06` | Molecule Master | 24,465 BNF → dm+d name mappings | One-time |
| `07` | NHSBSA PCA Demand | 348,000 prescription volume rows | Monthly |
| `08` | CPE Historical Archive | 74 months of full concession history | Monthly |
| `14` | NHSBSA SSP Register | 87 Serious Shortage Protocols (9 active) | Weekly |
| `16` | yfinance Signals | Brent crude price, Sun Pharma stock | Daily |
| `18` | Early Warning Feeds | MHRA + FDA + CPE RSS feeds | Daily |
| `19` | API Cascade Mapper | 797 drugs × API dependency graph | Weekly |
| `20` | API Manufacturer Intel | 322 molecules × manufacturer data (OpenFDA) | Monthly |

### Key API endpoints

```
NHSBSA Open Data Portal  : https://opendata.nhsbsa.net/api/3/action/
CPE Price Concessions    : https://cpe.org.uk/dispensing-and-supply/supply-chain/medicine-shortages/
OpenPrescribing          : https://openprescribing.net/api/1.0/ncso-concessions/
MHRA RSS                 : https://www.gov.uk/drug-safety-update.atom
OpenFDA Shortages        : https://api.fda.gov/drug/shortage.json
Bank of England          : https://www.bankofengland.co.uk/boeapps/database
Exchange Rates API       : https://api.exchangerate.host/timeseries
```

---

## How the Model Works

### 1. Feature Engineering (`11_feature_store_panel.py`)

For each drug × month combination, 27 features are computed across 7 signal categories (listed above). The panel spans 758 drugs and 74 months (January 2020 – February 2026), yielding 44,363 rows.

### 2. Target Variable

Binary label: did this drug receive an NHS price concession the **following month**?

- Positive class (shortage next month): ~8% of rows
- Class imbalance handled via `class_weight='balanced'` in Random Forest

### 3. Model Training (`12_ml_model_panel.py`)

```
RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    class_weight='balanced',
    random_state=42
)
```

Training uses a **time-based split**: drugs from months up to a cutoff date form the training set; the most recent months form the hold-out test set. This prevents data leakage across time.

### 4. Monthly Scoring

Each month, all 758 active drugs are scored with `predict_proba()`, ranked by shortage probability, and bucketed into signals:

| Signal | Threshold | Action |
|---|---|---|
| 🔴 BUY NOW | ≥ 0.75 | High confidence — procure immediately |
| 🟡 BUY AHEAD | 0.45–0.74 | Elevated risk — build safety stock |
| 🟢 WATCH | 0.20–0.44 | Monitor closely |
| ⚪ LOW RISK | < 0.20 | No action required |

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip
- (~200MB free disk space for data files)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/skyward-27/nipharm-shortage-intelligence.git
cd nipharm-shortage-intelligence

# 2. Install dependencies
pip install -r scrapers/requirements.txt

# 3. (Optional) Set environment variables
export ANTHROPIC_API_KEY="your_key_here"      # For AI analyst feature
export GMAIL_USER="your@gmail.com"             # For automated email reports
export GMAIL_APP_PASSWORD="your_app_password"  # Gmail app password
export REPORT_EMAIL="recipient@example.com"    # Report recipient

# 4. Run all data scrapers
python scrapers/00_run_all_scrapers.py

# 5. Build the feature panel and train the model
python scrapers/11_feature_store_panel.py
python scrapers/12_ml_model_panel.py

# 6. Launch the dashboard
cd scrapers && streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`.

### Running individual scrapers

```bash
# Run a single scraper by number
python scrapers/00_run_all_scrapers.py --source 01

# Test which sources are accessible from your network
python scrapers/00_run_all_scrapers.py --test
```

---

## Project Structure

```
nipharm-shortage-intelligence/
├── scrapers/
│   ├── app.py                          # Streamlit dashboard (7 pages)
│   ├── agent.py                        # Claude AI analyst (natural-language queries)
│   ├── 00_run_all_scrapers.py          # Master orchestrator
│   │
│   ├── — Data collection —
│   ├── 01_nhsbsa_drug_tariff.py        # NHS Drug Tariff Category M prices
│   ├── 02_ncso_price_concessions.py    # CPE + NHSBSA concession records
│   ├── 04_mhra_shortage_alerts.py      # MHRA alerts, SSPs, GOV.UK search
│   ├── 05_market_signals.py            # FX rates, BoE rate, OpenFDA shortages
│   ├── 06_molecule_master.py           # BNF → dm+d molecule mapping
│   ├── 07_nhsbsa_pca_demand.py         # Prescription volume by BNF code
│   ├── 08_cpe_historical_concessions.py# 74-month CPE archive
│   ├── 14_nhsbsa_ssp_register.py       # Serious Shortage Protocol register
│   ├── 16_yfinance_signals.py          # Brent crude, pharma equity signals
│   ├── 17_extend_tariff_history.py     # Extended tariff price history
│   ├── 18_early_warning_signals.py     # MHRA + FDA + CPE RSS monitoring
│   ├── 19_api_cascade_mapper.py        # API dependency graph builder
│   ├── 20_api_manufacturer_intelligence.py  # OpenFDA manufacturer data
│   │
│   ├── — ML pipeline —
│   ├── 09_feature_store_builder.py     # Legacy feature builder
│   ├── 10_ml_model.py                  # Legacy model (superseded by v6)
│   ├── 11_feature_store_panel.py       # Panel feature engineering (active)
│   ├── 12_ml_model_panel.py            # Random Forest v6 (active model)
│   │
│   ├── requirements.txt
│   ├── README.md                       # This file
│   └── data/                           # 141 MB datasets (gitignored)
│       ├── drug_tariff/
│       ├── concessions/
│       ├── mhra/
│       ├── market_signals/
│       ├── molecule_master/
│       ├── demand/
│       ├── supply_chain/
│       └── pipeline_run_report.csv
│
├── .streamlit/
│   └── config.toml                     # Streamlit theme + server config
├── render.yaml                         # Render.com deployment + cron job
└── README.md
```

---

## Deployment

### Streamlit Cloud (primary)

The dashboard auto-deploys on every push to `main`.

1. Connect the GitHub repo to [share.streamlit.io](https://share.streamlit.io)
2. Set `scrapers/app.py` as the main file path
3. Add the required secrets in the Streamlit Cloud dashboard

**URL:** [nipharma-stock-intelligence.streamlit.app](https://nipharma-stock-intelligence.streamlit.app)

### Render.com (alternative + cron)

`render.yaml` defines:
- A web service running the Streamlit dashboard
- A cron job that triggers the bi-weekly AI report generator

```bash
# Render deploys from render.yaml automatically on push to main
```

### Required environment variables

| Variable | Purpose | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude AI analyst in `agent.py` | For AI features |
| `GMAIL_USER` | Sender address for automated reports | For email reports |
| `GMAIL_APP_PASSWORD` | Gmail app password (not account password) | For email reports |
| `REPORT_EMAIL` | Recipient for bi-weekly PDF reports | For email reports |

---

## Critical Risk Molecules (March 2026)

Drugs with single-source manufacturers or active US shortage cross-signals:

| Molecule | Manufacturer | Country | US Shortage |
|---|---|---|---|
| Pramipexole | Sichuan Haisco Pharma (sole supplier) | China | — |
| Hydroxocobalamin | Merck KGaA | Germany | ⚠️ Active |
| Propranolol | Cambrex + IPCA Labs | India | ⚠️ Active |
| Mefenamic Acid | Divi's Laboratories | India | — |

Single-source drugs from a single country represent the highest geopolitical supply risk. These are flagged automatically by `19_api_cascade_mapper.py` and `20_api_manufacturer_intelligence.py`.

---

## Roadmap

- [ ] Model v6 retrain with full 27-feature set (post-Script 20 data)
- [ ] Script 21: Therapeutic Substitution Cascade Predictor
- [ ] AAH / Alliance Healthcare invoice integration (real purchase prices vs NHS tariff)
- [ ] FDA Import Alerts scraper — 3–6 month manufacturing lead time signal
- [ ] Supabase migration: replace CSV data store with persistent relational database
- [ ] Bi-weekly automated PDF report delivered via GitHub Actions
- [ ] Per-pharmacy stock optimisation mode (multi-branch inventory weighting)

---

## Data Privacy

- **No patient data.** All data is aggregated public NHS data published by NHSBSA, CPE, and MHRA.
- **No prescription-level data.** Demand signals use BNF-code-level aggregate prescription counts.
- **No PII.** No personally identifiable information is collected or stored at any point.
- Invoice data, when integrated, is gitignored and **never committed** to this repository.
- All scrapers use public APIs with standard rate limiting and respect robots.txt.

---

## Contributing

This is a private commercial project. See [.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) for internal contribution guidelines.

---

## License

**Private / Proprietary** — All rights reserved. Nipharma Tech Ltd.

This codebase is not licensed for public use, redistribution, or modification. Contact the maintainers for licensing enquiries.
