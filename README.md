# Nipharma — Stock Intelligence Platform

A real-time pharmaceutical shortage prediction platform for UK community pharmacies. Uses ensemble ML (Random Forest + XGBoost, AUC 0.9983) combined with live market signals to predict NHS drug concessions before they happen — enabling pharmacists to stock at tariff price before prices surge.

**Live Site:** https://nipharm-shortage-intelligence.vercel.app

---

## Key Features

- **Drug Search** — 26 essential medicines with BUY NOW/BUFFER/MONITOR recommendations
- **Shortage Intelligence** — ML predictions updated monthly + real-time signal boosting
- **Market News** — Curated pharmaceutical industry updates
- **Chatbot** — AI-powered Q&A with local CPE concession lookup, MHRA cross-reference, NI context, and live web search (Groq llama-3.3-70b-versatile + Tavily)
- **Analytics Dashboard** — Supply chain trends, MHRA alerts, top shortage risks
- **Weekly Report** — Newspaper-style intelligence brief (printable)
- **Tariff Calculator** — NHS price lookup + bulk discount estimator

---

## Architecture

| Component | Tech | Hosted |
|-----------|------|--------|
| Frontend | React 18 + TypeScript | Vercel |
| Backend | Python FastAPI + Groq LLM | Railway |
| ML Model | Random Forest + XGBoost (scikit-learn) | GitHub + Railway |
| Data Layer | CSV files + CPE/MHRA/Market/NI APIs | Local + Railway |

### Key Endpoints

```
POST   /predict              # ML shortage prediction (43 features, 6hr TTL cache)
GET    /health               # Backend status
GET    /news                 # Pharmaceutical news feed
GET    /mhra-alerts          # MHRA shortage publications
GET    /signals              # Real-time GBP/INR, GBP/CNY, GBP/USD from ECB
GET    /concessions          # Current CPE concession data
POST   /chat                 # Groq LLM + Tavily search + local CPE/MHRA lookup
GET    /weekly-report        # Intelligence summary
POST   /contact              # Contact form
```

---

## ML Model

### v4 (Deployed)

**Random Forest Classification**
- Training data: 44,074 rows (758 drugs x 60 months historical)
- Performance: AUC 0.9983, 5-fold stratified cross-validation
- Features: 28 (pricing, concessions, FX/commodity signals, MHRA mentions, demand spikes)
- Note: v4 uses StratifiedKFold with shuffle, which introduces temporal data leakage. True AUC is likely 0.92-0.96.

### v5 (Ready to Train)

**Key upgrades over v4:**

| Improvement | v4 | v5 |
|-------------|----|----|
| Cross-validation | StratifiedKFold (shuffle=True, data leakage) | **TimeSeriesSplit** (no leakage) |
| Algorithms | Random Forest only | **Random Forest + XGBoost** benchmark |
| Explainability | Feature importance only | **SHAP** per-drug explainability |
| Calibration | Raw probabilities | **Isotonic calibration** (trustworthy confidence scores) |
| Test set | None (all data in CV) | **Hold-out test set** (last 6 months) |
| Features | 28 | **43** (15 new features) |

**7 New Feature Groups (v5):**

1. **Neighbouring drug cascade** (`bsn_same_section_conc_count`) — If drugs in the same BNF class go on concession, risk rises for related drugs
2. **Seasonal encoding** (`month_sin`, `month_cos`) — Cyclical month features capturing winter shortage patterns
3. **Winter flag** (`is_winter`) — Nov-Feb respiratory drug demand spike signal
4. **SSP integration** (`drug_on_ssp`) — Serious Shortage Protocol status from NHSBSA SSP register
5. **Drug age** (`drug_age_years`) — Older generics carry higher shortage risk
6. **Indian pharma stress** (`ni_india_pharma_stress`) — Composite stress score from 10 NSE pharma stock tickers
7. **Wholesale price intelligence** (`best_historic_price`, `price_vs_best_pct`, `wholesale_margin_pct`) — Real pharmacy invoice-derived price signals

**Hybrid Prediction Scoring**
- 70% ML probability + 30% real-time signal boost
- Real-time signals: MHRA alerts, CPE availability, demand spikes, price stress, stock shortages

**Top Features by Importance (v4)**
1. CPE availability 6mo (29.6%)
2. Concession history last 6mo (18.7%)
3. Concession streak (12.1%)
4. On concession (9.9%)
5. Price change MoM (5.8%)

### Model Version History

| Version | AUC | Rows | Key Change |
|---------|-----|------|------------|
| v1 (flat) | 0.891 | 758 | One row per drug |
| v2 (panel) | 0.971 | 14,764 | Added streak + time series |
| v3 | 0.982 | 14,764 | Added Brent crude + Sun Pharma |
| v4 (deployed) | 0.9983* | 44,074 | Added CPE price features + hybrid /predict |
| **v5 (ready)** | **TBD** | **44,074+** | **Temporal CV fix + XGBoost + SHAP + 15 new features** |

*v4 AUC inflated by temporal leakage in StratifiedKFold

---

## Data Sources

| Source | Type | Frequency | Status |
|--------|------|-----------|--------|
| NHSBSA Drug Tariff | Cat M pricing (24 months) | Monthly | ✅ Live |
| CPE Concessions | Concession events (archive + current) | Monthly | ✅ Live |
| BSO NI Concessions | Northern Ireland concessions | Monthly | ✅ Live |
| MHRA Publications | Shortage alerts | Ad-hoc | ✅ Live |
| MHRA Marketing Authorisations | Licensed manufacturer counts per drug | On-demand | ✅ Live |
| Indian Pharma NSE Stocks | 10 tickers: SUNPHARMA, DRREDDY, CIPLA, AUROPHARMA, LUPIN, DIVISLAB, BIOCON, TORNTPHARM, GLENMARK, ALKEM | Monthly | ✅ Live |
| Shipping Stress (ZIM, SBLK) | Freight rate proxy for API supply chain | Monthly | ✅ Live |
| Brent Crude (yfinance) | Commodity stress | Daily | ✅ Live |
| FX Rates (Frankfurter/ECB) | GBP/INR, GBP/CNY, GBP/USD | Daily | ✅ Live |
| BoE Bank Rate | Interest rates + PPI | Quarterly | ✅ Live |
| NHSBSA SSP Register | Serious Shortage Protocols | On-demand | ✅ Live |
| OpenPrescribing (PCA) | England GP prescribing demand | Monthly | ✅ Live |
| OpenDataNI | NI GP prescribing data | Manual | ✅ Live |
| BSO NI Shortage Notices | NI-specific shortage signals | Ad-hoc | ✅ Live |
| FDA Warning Letters | Regulatory actions on Indian/Chinese API manufacturers | On-demand | ✅ Live |
| dm+d Molecule Master | Drug dictionary (24,465 molecules) | On-demand | ✅ Live |
| Wholesale Invoices | Real pharmacy purchase prices | Manual monthly | ✅ Configured |

---

## Data Scrapers

All scraper scripts live in `scrapers/` and output to `scrapers/data/` (not committed to GitHub).

| Script | Purpose | Status |
|--------|---------|--------|
| `01_nhsbsa_drug_tariff.py` | Cat M prices (24 months) | ✅ Working |
| `02_ncso_price_concessions.py` | CPE current month concessions | ✅ Working |
| `04_mhra_alerts.py` | MHRA shortage publications | ✅ Working |
| `05_market_signals.py` | FX/BoE/OpenFDA signals | ✅ Working |
| `06_molecule_master.py` | dm+d molecule dictionary | ✅ Working |
| `08_cpe_historical_concessions.py` | CPE archive crawl (Jan 2020 onwards) | ✅ Working |
| `09_feature_store_builder.py` | Flat 758-molecule feature store | ✅ Working |
| `11_feature_store_builder.py` | v5 panel feature store (43 features) | ✅ New |
| `12_ml_model_panel.py` | RF + XGBoost + SHAP training (v5) | ✅ Upgraded |
| `13_openprescribing.py` | NHSBSA PCA demand data | ✅ Working |
| `14_nhsbsa_ssp.py` | Serious Shortage Protocol register | ✅ Working |
| `16_yfinance_signals.py` | 10 Indian pharma NSE tickers + 2 shipping proxies | ✅ Upgraded |
| `17_cpni_concessions.py` | BSO NI concessions | ✅ Working |
| `19_mhra_manufacturer_count.py` | Licensed manufacturer count per drug | ✅ New |
| `20_opendatani_prescribing.py` | NI GP prescribing (OpenDataNI CKAN) | ✅ New |
| `21_bso_ni_shortages.py` | BSO NI shortage notices | ✅ New |
| `22_fda_warning_letters.py` | FDA warning letters (India/China manufacturers) | ✅ New |
| `23_invoice_price_pipeline.py` | Wholesale price intelligence pipeline | ✅ New |

---

## Chatbot Improvements

The AI chatbot (Groq + Tavily) received significant upgrades:

- **Smarter model:** Upgraded from llama-3.1-8b-instant to **llama-3.3-70b-versatile**
- **Local CPE lookup:** Concession price questions answered instantly from local data before calling LLM
- **MHRA cross-reference:** Automatically alerts pharmacists about relevant MHRA shortage notices
- **Northern Ireland context:** Includes BSO NI and HSCNI data in responses
- **Dynamic date awareness:** No more hardcoded dates — always uses current month
- **Longer responses:** Max tokens doubled from 512 to 1024 for more detailed answers

---

## Backend Improvements

- **`/signals` endpoint** — Returns real-time GBP/INR, GBP/CNY, GBP/USD exchange rates from ECB via Frankfurter API
- **`/concessions` endpoint** — Returns current CPE concession data from the local CSV
- **6-hour TTL cache on `/predict`** — Faster responses, reduced Railway compute usage
- **Version bump to v5** in API docstrings and metadata

---

## Quick Start

### Frontend (Vercel)
```bash
cd nipharma-frontend
npm install
npm start                    # Local dev at :3000
REACT_APP_API_URL=http://localhost:8000 npm start   # Use local backend
```

### Backend (Railway)
```bash
cd nipharma-backend
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

### Retrain ML Model (run in Terminal, not via Claude Code)
```bash
cd scrapers
python 16_yfinance_signals.py       # Refresh market data
python 11_feature_store_builder.py  # Build v5 feature store (43 features)
python 12_ml_model_panel.py         # Train RF + XGBoost + SHAP
# Then copy model to backend:
cp data/model/panel_model.pkl ../nipharma-backend/model/
```

**Environment Variables** (`.env`)
```
REACT_APP_API_URL=https://npt-stock-intel-production.up.railway.app
GROQ_API_KEY=xxx
TAVILY_API_KEY=xxx
```

---

## Deployment Status

- **Frontend** — Live on Vercel (auto-deploys on push)
- **Backend** — Live on Railway
- **ML Model** — Committed to repo (5.0 MB `panel_model.pkl`)
- **CI/CD** — Vercel auto-deploys on GitHub push

### Environment

- **Node.js:** 20.x (Vercel)
- **Python:** 3.10+
- **Build:** Vercel buildCommand: `CI=false npm run build` (ESLint warnings ignored)

---

## Project Structure

```
nipharma-frontend/          React app (8 pages, TypeScript)
  src/pages/
    Dashboard.tsx           5 KPI cards + news feed
    DrugSearch.tsx          26 drugs + ML predictions
    Analytics.tsx           Supply chain charts + top 10 risks
    Chat.tsx                Groq LLM + Tavily search + local CPE/MHRA lookup
    Alerts.tsx              MHRA shortage publications
    MarketNews.tsx          Pharmaceutical news aggregator
    WeeklyReport.tsx        Intelligence brief (printable)
    Contact.tsx             Contact form
  vercel.json               SPA rewrite catch-all

nipharma-backend/           FastAPI backend (v5)
  server/main.py            9 endpoints (health, predict, signals, concessions, chat, news, alerts, report, contact)
  requirements.txt          FastAPI, Pydantic, scikit-learn, pandas, numpy
  model/panel_model.pkl     Trained ML model (5.0 MB)

scrapers/                   Data collection scripts (local only, 20+ scripts)
  11_feature_store_builder.py  v5 feature store (43 features)
  12_ml_model_panel.py         RF + XGBoost + SHAP training
  data/                        Feature store + model artifacts (not on GitHub)
```

---

## Key Technologies

- **ML:** scikit-learn (Random Forest), XGBoost, SHAP, isotonic calibration, pandas, numpy
- **Backend:** FastAPI, uvicorn, Pydantic, cachetools (6hr TTL)
- **Frontend:** React 18, TypeScript, React Router
- **LLM:** Groq (llama-3.3-70b-versatile), Tavily (web search)
- **Data:** CSV-based feature store (44,074+ rows, 43 features)
- **Market Data:** yfinance (10 NSE pharma tickers + 2 shipping proxies)

---

## Roadmap

### v4 (Deployed)
- ML model with 28 features (added CPE prices)
- Hybrid /predict endpoint (70% ML + 30% signals)
- Full frontend + backend integration

### v5 (Ready to Train)
- TimeSeriesSplit cross-validation (fixes temporal data leakage)
- XGBoost benchmark alongside Random Forest
- SHAP per-drug explainability
- Isotonic probability calibration
- 15 new features (43 total): seasonal patterns, drug cascade, SSP, manufacturer count, Indian pharma stress, wholesale price intelligence
- 6 new data scrapers: MHRA manufacturers, NI prescribing, NI shortages, FDA warning letters, wholesale prices, expanded Indian pharma tickers
- Chatbot upgrade: llama-3.3-70b-versatile + local CPE/MHRA lookup + NI context
- New endpoints: /signals (FX rates), /concessions (CPE data)
- 6-hour TTL caching on /predict

### v6 (Planned)
- Deploy v5 model to Railway
- Fix vmpp-to-BNF mapping (improve PCA demand signal quality)
- Real-time AAH Hub wholesale price integration
- Automated monthly retraining pipeline

---

## Documentation

- **[Backend README](./nipharma-backend/README.md)** — API endpoints, model specs, retraining schedule
- **[Detailed Model Report](./NIPHARMA_MODEL_DEPLOYMENT_DETAILED_REPORT.docx)** — 9-page technical report (all 8 problems + solutions, 5 alternatives analyzed)

---

## GitHub Policy

**Tracked:**
- `nipharma-frontend/` — React source code
- `nipharma-backend/` — FastAPI + ML model (`panel_model.pkl`)
- `scrapers/*.py` — Data collection scripts

**Never Committed:**
- `scrapers/data/` — CSV data files
- `.env` files — API keys and secrets
- Session cookies and browser data

---

## Support and Contact

- **Issues:** GitHub Issues (private repo)
- **Live Site:** https://nipharm-shortage-intelligence.vercel.app
- **Backend Status:** https://npt-stock-intel-production.up.railway.app/health

---

**Last Updated:** April 2026 | **Model:** v4 deployed (AUC 0.9983), v5 ready to train | **Status:** Production
