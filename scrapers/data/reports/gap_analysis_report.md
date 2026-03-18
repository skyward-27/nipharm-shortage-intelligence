# NiPharm Data Gap Analysis Report
**Generated:** 2026-03-15
**Project:** NPT Stock Intelligence Unit — NHS Drug Shortage Predictor

---

## 1. MODEL PERFORMANCE (as of 2026-03-15)

| Metric | Score | Interpretation |
|--------|-------|----------------|
| ROC-AUC | **0.982** | Excellent — near-perfect ranking of shortage risk |
| PR-AUC | **0.935** | Excellent — high precision even at high recall |
| F1 | **0.846** | Strong — good balance of precision vs recall |
| Training rows | 14,764 | 754 drugs × 23 months |
| Positive labels | 2,187 (14.8%) | CPE concession events |

---

## 2. DATA SOURCES — FULL AUDIT

### ✅ WORKING (contributing to model)

| Source | Script | Data | Model Feature | Impact |
|--------|--------|------|---------------|--------|
| NHS Drug Tariff Cat M | 01 | 15,379 rows, 24 months | floor_proximity, price_mom_pct, price_yoy_pct | **HIGH** — top signal |
| CPE Concession Archive | 08 | 7,742 rows, Jan 2020–Feb 2026 | on_concession, concession_streak, conc_last_6mo, **LABEL** | **CRITICAL** — training labels |
| CPE Current Month | 02 | 174 drugs (March 2026) | on_concession | HIGH |
| MHRA Publications | 04 | 3,372 publications | mhra_mention_count | LOW (0.8% feature importance) |
| FX Rates (GBP/INR) | 05 | 105 days | fx_stress_score | LOW (0.9%) |
| BoE Bank Rate | 05 | 133 records | boe_bank_rate | LOW (1.7%) |
| OpenFDA Shortages | 05 | 76 US shortages | us_shortage_flag | VERY LOW (0.1%) |
| SSP Register | 14 | 87 SSPs, 6 active | ssp_flag | TBD — just added |
| dm+d Molecule Master | 06 | 24,465 molecules | identity matching | MEDIUM (joining) |

---

### ❌ BROKEN — Why, Criticality, and Alternatives

#### DSO-003: OpenPrescribing / EPD Prescribing Demand
- **Status:** Script 03 broken (NHSBSA SQL API returns HTTP 500)
- **Why it broke:** NHSBSA disabled the `datastore_search_sql` endpoint in 2024
- **Criticality:** 🟡 MEDIUM — demand volume is a useful leading indicator but the model already achieves 0.982 ROC-AUC without it
- **What we'd gain:** Detecting drugs with *rising demand* + *falling price* simultaneously (the classic shortage setup)
- **Alternatives:**
  1. ✅ **Script 07** (written): PCA monthly CSVs from NHSBSA CKAN — same data, different API. NHSBSA server is slow; run overnight.
  2. ✅ **Script 13** (written): OpenPrescribing.net API — 52 months of Rx volume per BNF code, free, reliable. Run: `python 13_openprescribing.py`
  3. Manual: Download EPD ZIP files from `https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd`

#### DSO-025: FRED Pharma PPI (US pharmaceutical producer prices)
- **Status:** Script 15 written but FRED blocks automated requests (connection reset / CAPTCHA)
- **Criticality:** 🟡 MEDIUM — pharma input cost inflation is a 6-12 month leading indicator for UK generic price rises
- **What we'd gain:** Macro cost-push signal independent of GBP/INR
- **Alternatives:**
  1. ✅ **Manual download** (5 minutes): Go to browser → https://fred.stlouisfed.org/series/PCU325412325412 → Download → Save as `data/fred/fred_pharma_ppi.csv`
  2. Use `pandas_datareader` library: `pip install pandas-datareader` then `pdr.get_data_fred('PCU325412325412')`
  3. OECD Producer Price Index (free API, less granular)

#### DSO-028: Polypropylene / Plastics PPI
- **Status:** Not yet scripted
- **Criticality:** 🟢 LOW — packaging cost, not drug API cost. Minor signal.
- **Alternatives:** FRED WPU0913 (same FRED block issue). Manual download same as above.

#### DSO-041: Freightos Freight Rates
- **Status:** Not scripted
- **Criticality:** 🟢 LOW — shipping cost matters more for devices than generics
- **Alternatives:** Freightos requires paid API. Use Baltic Dry Index (BDI) via Yahoo Finance (`yfinance`) as free proxy.

#### DSO-052/053: EIA Brent Crude / TTF Gas
- **Status:** Not scripted
- **Criticality:** 🟢 LOW for drug shortage prediction specifically
- **Alternatives:** `yfinance`: `yf.download("BZ=F")` for Brent, `yf.download("TTF=F")` for TTF gas. Free, instant.

#### DSO-062: India DGFT Export Controls
- **Status:** Not scripted
- **Criticality:** 🔴 HIGH — India supplies ~70% of UK generic APIs. Export bans (like 2020 paracetamol) are the #1 root cause of UK shortages.
- **What we'd gain:** 2-4 week early warning before UK prices move
- **Alternatives:**
  1. India DGFT website: https://www.dgft.gov.in/CP/ (manual check, no API)
  2. Monitor WHO/UNICEF supply alerts (https://www.who.int/medicines/regulation/ssffc/pharmacovigilance/en/)
  3. Reuters/Bloomberg commodity desks (paid)
  4. **Best free option:** Scrape DGFT notifications page weekly

#### DSO-074: FRED FX (USD/INR)
- **Status:** Covered by Frankfurter API (GBP/INR) ✅ — already in model

#### DSO-089: yfinance equity signals
- **Status:** Not scripted
- **Criticality:** 🟡 MEDIUM — pharma company stock drops can signal supply issues
- **Alternatives:** `pip install yfinance` — completely free. Watch: Sun Pharma (SUNPHARMA.NS), Dr Reddy's (DRREDDY.NS), Teva (TEVA)

#### CPE Historical PDFs (2019 and earlier)
- **Status:** Not machine-readable via scraping — CPE PDFs are image-based
- **Criticality:** 🟡 MEDIUM — more training history would help
- **What we have:** Archive XLSX covers Jan 2020 – Feb 2026 (74 months) ✅
- **Alternatives:** OCR via `pytesseract` or Adobe Extract API (paid). Not worth the effort given we have 74 months already.

#### molecule_master.csv BNF codes (all null)
- **Status:** All 24,465 rows have `bnf_code = null` from dm+d API
- **Criticality:** 🟡 MEDIUM — prevents joining drug tariff (VMPP codes) to prescribing data (BNF codes)
- **Alternatives:**
  1. Download BNF–VMPP mapping from NHSBSA SNOMED mapping file (free, manual)
  2. Use drug name fuzzy matching (already doing this for MHRA/US shortage matching)
  3. OpenPrescribing BNF-to-VMPP mapping (available in their API)

---

## 3. FEATURE IMPORTANCE ANALYSIS

From the trained panel model (12_ml_model_panel.py):

```
concession_streak         27.6%  ████████████▌   — Momentum: ongoing shortage continues
on_concession             25.8%  ████████████▉   — Currently in shortage
conc_last_6mo             18.9%  █████████▍      — Frequency: repeat shortages
price_mom_pct             16.1%  ████████        — Price falling = approaching floor
floor_proximity            5.2%  ██▌             — Structural: near unprofitable floor
boe_bank_rate              1.7%  ▊               — Macro: higher rates = tighter margins
within_15pct_of_floor      1.6%  ▊               — Binary floor proximity
price_yoy_pct              1.4%  ▋               — Long-run price trend
fx_stress_score            0.9%  ▍               — GBP/INR stress
mhra_mention_count         0.8%  ▍               — Regulatory flag
us_shortage_flag           0.1%  ▏               — US early warning (weak matching)
ssp_flag                   TBD                   — Just added
```

**Key insight:** 72% of predictive power comes from *current concession state*. The model is primarily a "persistence predictor" — drugs currently in shortage tend to stay in shortage. This is realistic (average concession streak = 3-4 months) but means the model is weaker at catching *new* shortages before they start.

**To improve early warning (new shortage detection):**
- Add OpenPrescribing Rx volume (rising demand + flat/falling price = risk)
- Add India DGFT export ban alerts
- Add FRED pharma PPI (input cost inflation)
- Extend price history back to 2014 (264 Cat M CSVs available on NHSBSA)

---

## 4. WHAT'S MISSING vs. ARCHITECTURE PLAN

| Architecture DSO | Description | Status | Priority |
|-----------------|-------------|--------|----------|
| DSO-001 | NHSBSA Drug Tariff | ✅ Done | CRITICAL |
| DSO-003 | OpenPrescribing Rx Volume | ⚠️ Script written, not run | CRITICAL |
| DSO-004 | CPE Concessions | ✅ Done (74 months) | CRITICAL |
| DSO-007 | MHRA Shortage Alerts | ✅ Done | CRITICAL |
| DSO-008 | NHS SSP Register | ✅ Done | CRITICAL |
| DSO-009 | SPS Medicines Shortages | ❌ Not scripted | HIGH |
| DSO-011 | NICE RSS Guidance | ❌ Not scripted | HIGH |
| DSO-017 | BoE FX + Inflation | ✅ Done | CRITICAL |
| DSO-025 | FRED Pharma PPI | ⚠️ Manual download needed | HIGH |
| DSO-028 | Polypropylene PPI | ❌ Manual download needed | MEDIUM |
| DSO-036 | LME Aluminium | ❌ Not scripted | MEDIUM |
| DSO-041 | Freightos Freight | ❌ Paid API | LOW |
| DSO-052 | EIA Brent Crude | ❌ Not scripted (yfinance easy) | LOW |
| DSO-053 | TTF Gas | ❌ Not scripted (yfinance easy) | LOW |
| DSO-062 | India DGFT Export Controls | ❌ No API | HIGH |
| DSO-066 | FDA Import Alerts | ❌ Not scripted | HIGH |
| DSO-067 | FDA Warning Letters | ❌ Not scripted | MEDIUM |
| DSO-074 | FRED FX | ✅ Covered by Frankfurter | CRITICAL |
| DSO-089 | yfinance Equity Signals | ❌ Easy (pip install) | MEDIUM |

---

## 5. NEXT STEPS (Priority Order)

### Run in Terminal (already written)
```bash
python 13_openprescribing.py   # ~10 min, adds Rx volume demand signal
python 07_nhsbsa_pca_demand.py # ~20 min, NHSBSA demand data
```

### Manual browser downloads needed
1. FRED Pharma PPI → `data/fred/fred_pharma_ppi.csv`
2. FRED Plastics PPI → `data/fred/fred_plastics_ppi.csv`

### Next Claude sessions (one per session)
1. **GitHub setup** — push code only, data to Google Drive
2. **Streamlit dashboard** — top 30 risk table, charts
3. **yfinance + EIA Brent** — 2 easy free signals, ~30 min scripting
4. **FDA Import Alerts** — US pharma supply chain signal
5. **Extend tariff history** — download 2014-2021 Cat M CSVs (264 files)
6. **India DGFT scraper** — weekly check, highest value missing signal

---

## 6. STORAGE PLAN

| Asset | Where | Notes |
|-------|-------|-------|
| Code (`scrapers/*.py`, `app.py`) | GitHub | No data files |
| Data CSVs | Google Drive or Kaggle Datasets | Share link in README |
| Model (`panel_model.pkl`) | GitHub | ~2MB, safe to commit |
| Dashboard | Streamlit Cloud | Free hosting |
| TensorBoard | ❌ Not using | Overkill for Random Forest |
| Visualization | Streamlit | Top 30 alerts, feature importance, trend charts |
