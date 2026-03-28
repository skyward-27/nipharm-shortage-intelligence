# NiPharm Drug Shortage Intelligence Platform
## Project Status Report — 15 March 2026

---

## 1. MODEL PERFORMANCE (as of today)

| Metric | Score | Interpretation |
|--------|-------|----------------|
| **ROC-AUC** | **0.982** ± 0.002 | Excellent — model distinguishes shortage/non-shortage almost perfectly |
| **PR-AUC** | **0.935** ± 0.008 | High precision on positive class (shortage) |
| **F1** | **0.846** ± 0.012 | Strong balance of precision and recall |
| Training rows | 14,764 drug-months | 754 drugs × 23 months |
| Positive labels | 2,187 (14.8%) | Months where drug had concession next month |

**Top predictive features:**
1. `concession_streak` — 27.6% — consecutive months already on concession
2. `on_concession` — 25.8% — currently on concession this month
3. `conc_last_6mo` — 18.9% — frequency of concessions over last 6 months
4. `price_mom_pct` — 16.1% — month-on-month price change
5. `floor_proximity` — 5.2% — price relative to unprofitable floor

**What this means:** The model is excellent at predicting *continuing* shortages (drugs already on concession). The momentum features dominate. Price signals are secondary but still relevant for predicting NEW entries.

---

## 2. DATA SOURCES STATUS

### ✅ WORKING — Data Collected

| Source | Script | Data Collected | Quality |
|--------|--------|----------------|---------|
| NHSBSA Drug Tariff (Cat M) | 01 | 15,379 rows, 24 months | HIGH — core price signal |
| CPE Concessions (current) | 02 | 174 drugs (March 2026) | HIGH — ground truth labels |
| CPE Concessions Archive | 08 | **7,742 rows, Jan 2020–Feb 2026** | CRITICAL — ML training labels |
| MHRA Shortage Publications | 04 | 3,372 publications | MEDIUM — mention counts only |
| FX Rates (GBP/INR/CNY/USD) | 05 | 105 days (Frankfurter API) | MEDIUM — macro signal |
| BoE Bank Rate | 05 | 133 records | LOW — weak predictor (1.7%) |
| OpenFDA US Shortages | 05 | 76 active shortages | LOW — name matching issues |
| dm+d Molecule Master | 06 | 24,465 molecules | MEDIUM — identity mapping |
| NHSBSA SSP Register | 14 | **87 SSPs (9 currently active)** | HIGH — strongest shortage signal |

### ⚠️ WRITTEN — Run in Terminal (not via Claude)

| Source | Script | Issue | How to Run |
|--------|--------|-------|------------|
| ML Panel Model | 12 | ✅ Already ran successfully | Done |
| PCA Demand Signal | 13 | NHSBSA server slow in Claude | `python 13_openprescribing.py` |
| FRED PPIs | 15 | Connection reset — ISP throttles Python requests; curl gets 200 but data never arrives | Manual download in browser (see Section 4) |

### ❌ BROKEN / BLOCKED

| Source | Script | Error | Criticality | Alternative |
|--------|--------|-------|-------------|-------------|
| OpenPrescribing API | 13 | **Cloudflare JS challenge** — blocks all automated requests | HIGH | ✅ **FIXED**: Replaced with NHSBSA PCA direct CSV |
| NHSBSA EPD SQL API | 03 | **HTTP 500** — SQL endpoint broken since ~2024 | MEDIUM | ✅ **FIXED**: PCA dataset has same data |
| exchangerate.host FX | 05 | **Requires paid API key** | LOW | ✅ **FIXED**: Switched to Frankfurter (free) |
| NHSBSA CKAN `drug-tariff` | 01 | **Dataset removed** from portal | HIGH | ✅ **FIXED**: Direct page scrape |
| NHSBSA CKAN `ncso-concessions` | 02 | **Dataset removed** | HIGH | ✅ **FIXED**: CPE direct scrape |
| FRED.org CSV endpoint | 15 | **Timeout** — may be rate-limited or geo-blocked | MEDIUM | Manual download (30 seconds) |
| CPE PDF archive (pre-2020) | N/A | PDFs not machine-readable via scraping | LOW | CPE XLSX covers Jan 2020+ — sufficient |

---

## 3. HOW CRITICAL ARE THE GAPS?

### Gap 1: OpenPrescribing / PCA Demand Signal
**Criticality: MEDIUM**
- The model currently scores 0.982 ROC-AUC WITHOUT Rx volume data
- The dominant features are all concession-momentum signals, not demand
- Adding demand would help predict NEW shortages (drugs not yet on concession)
- **Current workaround:** PCA scraper (script 13) downloads same data from NHSBSA
- **Action:** Run `python 13_openprescribing.py` in Terminal

### Gap 2: FRED Pharma PPI (cost-push signal)
**Criticality: LOW-MEDIUM**
- Currently only 1.7% feature importance (BoE rate)
- US manufacturing costs do lead UK shortage by ~2-6 months
- Would improve early-warning on NEW shortages
- **Current workaround:** Already have FX stress score as partial proxy
- **Action:** 2-minute manual download (see Section 4)

### Gap 3: SSP Register — Needs Parsing Improvement
**Criticality: HIGH — already collected but needs cleaning**
- 87 SSPs collected, 9 currently active
- Raw text not yet parsed into structured drug_name / dates columns
- SSP = confirmed severe shortage — strongest label we have
- **Action:** Add SSP drug names as features in next model version

### Gap 4: No BNF codes in molecule_master.csv
**Criticality: MEDIUM**
- Cannot join PCA/EPD data (BNF-coded) to drug tariff (VMPP-coded) without a lookup
- dm+d API would resolve this: VMPP → BNF code
- **Action:** Either use TRUD dm+d download or NHS API for BNF→VMPP mapping

### Gap 5: Drug Tariff only covers 24 months (Apr 2021 – Jan 2026)
**Criticality: MEDIUM**
- CPE archive goes back to Jan 2020 but tariff only to Apr 2021
- 15-month gap in the panel where concession labels exist but price features don't
- **Action:** Download older Drug Tariff Cat M CSVs from NHSBSA page (264 files available back to 2014)

---

## 4. MANUAL DOWNLOADS NEEDED (30-60 seconds each)

### FRED Pharma PPI (critical cost-push signal)
1. Go to: https://fred.stlouisfed.org/series/PCU325412325412
2. Click **Download → CSV**
3. Save as: `scrapers/data/fred/fred_pharma_ppi.csv`
4. Repeat for plastics: https://fred.stlouisfed.org/series/WPU0913
5. Save as: `scrapers/data/fred/fred_plastics_ppi.csv`

### Older Drug Tariff Data (extend panel to 2014)
- NHSBSA page has 264 monthly Cat M CSVs back to 2014
- URL: https://www.nhsbsa.nhs.uk/.../drug-tariff-part-viii
- Script 01 can download these — just needs more months parameter

---

## 5. SCRIPTS TO RUN IN TERMINAL (outside Claude)

```bash
cd "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/scrapers"

# 1. PCA demand signal (52 months, ~10 min)
python 13_openprescribing.py

# 2. FRED PPIs (only if manual CSVs downloaded first)
python 15_fred_ppi.py

# 3. Re-run ML model after PCA data is added to panel
python 11_feature_store_panel.py  # rebuild panel with PCA
python 12_ml_model_panel.py       # retrain model
```

---

## 6. NEXT DEVELOPMENT PHASES

### Phase 2 — Improve Early Warning (predict NEW shortages)
Current model is great at predicting *continuing* shortages.
To catch drugs BEFORE they go on concession:
- Add PCA demand surge as feature (script 13)
- Add FRED cost-push index (script 15)
- Add SSP flag as binary feature (script 14 — needs parsing)
- Extend tariff history to 2014 (60+ months of price data)
- Try LightGBM / XGBoost (better with imbalanced tabular data)

### Phase 3 — GitHub + Data Storage
```
GitHub repo (code only — NO data files):
  scrapers/
  app.py
  requirements.txt
  .gitignore  ← add data/ and *.pkl

Data storage options:
  Google Drive — easiest, free 15GB
  Kaggle Datasets — free 20GB, versioned, public/private
  AWS S3 (free tier) — 5GB, good for automated pipeline
```

### Phase 4 — Streamlit Dashboard
```python
# Key views needed:
# 1. Top 30 drugs at risk this month (from panel_predictions.csv)
# 2. Drug detail: price history + concession history chart
# 3. Feature importance bar chart
# 4. Monthly model refresh status
# Host free at: streamlit.io/cloud
```

### Phase 5 — Scheduled Pipeline
```bash
# Monthly cron (1st of each month):
# 1. python 01_nhsbsa_drug_tariff.py   (new Cat M prices)
# 2. python 02_ncso_price_concessions.py (new concessions)
# 3. python 13_openprescribing.py       (new Rx volumes)
# 4. python 14_nhsbsa_ssp.py            (current SSPs)
# 5. python 11_feature_store_panel.py   (rebuild panel)
# 6. python 12_ml_model_panel.py        (retrain model)
```

---

## 7. CURRENT OUTPUT FILES

```
data/
├── drug_tariff/
│   ├── drug_tariff_202603.csv         15,379 rows — 24mo Cat M prices
│   └── tariff_with_floors.csv         floor calculations per VMPP
├── concessions/
│   ├── cpe_archive_full.csv           7,742 rows — Jan 2020 to Feb 2026
│   ├── cpe_archive_full.xlsx          original spreadsheet
│   └── cpe_current_month.csv          174 drugs — March 2026
├── mhra/
│   ├── govuk_shortage_publications.csv  3,372 publications
│   └── mhra_rss_alerts.csv              114 alerts
├── market_signals/
│   ├── fx_rates_stress.csv              105 days FX
│   ├── boe_inflation.csv                133 records
│   └── openfda_shortages.csv            76 US shortages
├── ssp/
│   ├── ssp_active.csv                   87 SSPs (9 currently active)
│   └── ssp_all.csv                      full history
├── features/
│   ├── panel_feature_store.csv          15,378 drug-month rows
│   ├── panel_feature_store_train.csv    14,764 training rows
│   ├── feature_store.csv                758 molecules (flat, legacy)
│   └── shortage_risk_alerts.csv         583 RED/AMBER/CONFIRMED
└── model/
    ├── panel_model.pkl                  trained Random Forest
    ├── panel_predictions.csv            top drugs at risk
    ├── panel_feature_importance.csv     feature rankings
    └── panel_cv_metrics.txt             ROC-AUC 0.982
```

---

*Report generated: 2026-03-15 | Model version: panel_v1 | Scripts: 01–15*
