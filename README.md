# Nipharma — Stock Intelligence Platform

A real-time pharmaceutical shortage prediction platform for UK & NI community pharmacies. Uses Random Forest + XGBoost ML with 46 features, combined with live market signals and wholesale price intelligence, to predict NHS drug concessions before they happen — enabling pharmacists to stock at tariff price before prices surge.

**Live Site:** https://nipharm-shortage-intelligence.vercel.app

---

## Key Features

- **Drug Search** — 26 essential medicines with BUY NOW/BUFFER/MONITOR recommendations + ML predictions
- **Shortage Intelligence** — ML predictions with real-time signal boosting (MHRA, CPE, demand, price stress)
- **Market News** — Curated pharmaceutical industry updates
- **AI Chatbot** — Groq LLM (llama-3.3-70b) with CPE concession lookup, MHRA cross-reference, live web search
- **Analytics Dashboard** — Supply chain trends, MHRA alerts, top shortage risks
- **Weekly Report** — Newspaper-style intelligence brief (printable)
- **Tariff Calculator** — NHS price lookup + bulk discount estimator
- **Wholesale Price Intelligence** — Best historic price tracking, Buy/Hold/Bulk Buy recommendations across 3 NI pharmacies

---

## Architecture

| Component | Tech | Hosted |
|-----------|------|--------|
| Frontend | React 18 + TypeScript | Vercel |
| Backend | Python FastAPI + Groq LLM | Railway |
| ML Model | Random Forest + XGBoost (scikit-learn) | GitHub + Railway |
| Data Layer | CSV feature store + CPE/MHRA/Market APIs | Local + Railway |
| Price Intelligence | Victoria OS + invoice pipeline | Local (private) |

### Key Endpoints

```
POST   /predict              # ML shortage prediction (46 features, 6hr TTL cache)
GET    /health               # Backend status
GET    /news                 # Pharmaceutical news feed
GET    /mhra-alerts          # MHRA shortage publications
POST   /chat                 # Groq LLM + CPE lookup + MHRA cross-ref + Tavily search
GET    /weekly-report        # Intelligence summary
POST   /contact              # Contact form
GET    /signals              # Live market signals (FX, BoE, commodity)
GET    /concessions          # Current CPE concession prices
```

---

## ML Model

### v4 (Deployed)
- **Random Forest** — AUC 0.9983*, 44,074 rows, 28 features
- *Note: AUC inflated by temporal leakage in StratifiedKFold(shuffle=True). True AUC likely 0.92-0.96

### v5 (Ready to Train)
- **Temporal validation fixed** — TimeSeriesSplit with 1-month gap (no future leakage)
- **XGBoost benchmark** added alongside Random Forest
- **SHAP explainability** — per-drug feature importance
- **Isotonic calibration** — trustworthy probability outputs
- **46 features** (18 new): neighbouring drug cascade, seasonal encoding, SSP status, drug age, Indian pharma stress, wholesale price vs tariff, manufacturer count
- **Hold-out test set** — last 6 months reserved for unbiased evaluation

**Hybrid Prediction Scoring**
- 70% ML probability + 30% real-time signal boost
- Real-time signals: MHRA alerts, CPE availability, demand spikes, price stress, stock shortages
- 6-hour TTL cache for repeated queries

**Top Features (v4)**
1. CPE availability 6mo (29.6%)
2. Concessions last 6mo (18.7%)
3. Concession streak (12.1%)
4. On concession (9.9%)
5. Price change MoM (5.8%)

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

**Environment Variables** (`.env`)
```
# Backend URL for frontend
REACT_APP_API_URL=https://npt-stock-intel-production.up.railway.app

# Railway vars (auto-set)
GROQ_API_KEY=xxx
TAVILY_API_KEY=xxx
```

---

## Data Sources (27 Scrapers)

| Source | Type | Frequency | Status |
|--------|------|-----------|--------|
| NHSBSA Drug Tariff | Cat M prices (24mo) | Monthly | ✅ Live |
| CPE Concessions | Current + archive (7,742 rows) | Monthly | ✅ Live |
| MHRA Publications | Shortage alerts (3,372 pubs) | Ad-hoc | ✅ Live |
| BSO NI Concessions | NI-specific concessions (453 rows) | Monthly | ✅ Live |
| BSO NI Shortages | NI shortage notices (113 rows) | Ad-hoc | ✅ Live |
| Indian Pharma Stocks | 10 NSE tickers via yfinance | Monthly | ✅ Live |
| Shipping Stress | ZIM + SBLK freight proxies | Monthly | ✅ Live |
| Brent Crude | Commodity stress signal | Daily | ✅ Live |
| FX Rates (Frankfurter) | GBP/INR, GBP/CNY, GBP/USD | Daily | ✅ Live |
| BoE Bank Rate | Interest rates + PPI | Quarterly | ✅ Live |
| MHRA Manufacturer Count | Marketing authorisations per drug | Ad-hoc | ✅ Live |
| OpenDataNI | NI GP prescribing (CKAN API) | Monthly | ⚠️ Manual |
| FDA Warning Letters | India/China supplier actions | Ad-hoc | ✅ Live |
| NHSBSA PCA Data | Prescribing demand (348,611 rows) | Monthly | ✅ Collected |
| NHSBSA SSP Register | Serious shortage protocols | Ad-hoc | ✅ Live |
| dm+d Molecules | 24,465 molecule master list | Static | ✅ Live |
| Victoria OS | Wholesale ordering prices | Manual | ✅ Pipeline |
| PDF Invoices | 152 supplier invoices (3 pharmacies) | Manual | ✅ Pipeline |
| AAH Hub API | Wholesale prices | Manual monthly | ✅ Configured |
| Alliance Healthcare | Invoices | Manual monthly | ✅ Configured |

---

## Deployment Status

✅ **Frontend** — Live on Vercel
✅ **Backend** — Live on Railway
✅ **ML Model** — Committed to repo (5.0 MB `panel_model.pkl`)
✅ **CI/CD** — Vercel auto-deploys on GitHub push

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
    Chat.tsx                Groq LLM + Tavily search
    Alerts.tsx              MHRA shortage publications
    MarketNews.tsx          Pharmaceutical news aggregator
    WeeklyReport.tsx        Intelligence brief (printable)
    Contact.tsx             Contact form
  vercel.json               SPA rewrite catch-all

nipharma-backend/           FastAPI backend
  server/main.py            9 endpoints + 6hr TTL cache
  server/chat.py            Groq LLM + CPE lookup + MHRA cross-ref
  requirements.txt          FastAPI, Pydantic, scikit-learn, pandas, numpy
  README.md                 API & ML model documentation

scrapers/                   Data collection scripts (local only, 27 scripts)
  12_ml_model_panel.py      RF + XGBoost + SHAP training (v5)
  11_feature_store_builder.py  46-feature panel builder
  23_invoice_price_pipeline.py Wholesale price intelligence
  data/                     Feature store + model artifacts
```

---

## Key Technologies

- **ML:** scikit-learn (Random Forest), pandas, numpy
- **Backend:** FastAPI, uvicorn, Pydantic
- **Frontend:** React 18, TypeScript, React Router
- **LLM:** Groq (llama-3.3-70b-versatile), Tavily (web search)
- **Data:** CSV-based feature store (44,074 rows, 46 features)

---

## Roadmap

### v4 (Deployed) ✅
- ML model with 28 features (added CPE prices)
- Hybrid /predict endpoint (70% ML + 30% signals)
- Full frontend + backend integration

### v5 (Ready to Train) ✅
- Temporal validation fix (TimeSeriesSplit, no future leakage)
- XGBoost + SHAP + isotonic calibration
- 18 new features (46 total): Indian pharma stocks, NI data, manufacturer count, seasonal, wholesale margins
- 6hr TTL cache on /predict
- 2 new endpoints: /signals, /concessions
- Chatbot upgraded: CPE lookup, MHRA cross-ref, llama-3.3-70b
- Wholesale price intelligence pipeline (302 drugs, 3 pharmacies)
- 6 new data scrapers (NI, Indian pharma, FDA, manufacturer count)

### v6 (Planned)
- Fix vmpp-to-BNF mapping (Bennett Institute CSV) for better PCA signal
- AAH Hub wholesale price integration
- XGBoost model deployment (after v5 training)
- Dashboard: wholesale price trends + buying recommendations page

---

## Documentation

- **[Backend README](./nipharma-backend/README.md)** — API endpoints, model specs, retraining schedule
- **[Detailed Model Report](./NIPHARMA_MODEL_DEPLOYMENT_DETAILED_REPORT.docx)** — 9-page technical report (all 8 problems + solutions, 5 alternatives analyzed)
- **[Local Setup Guide](./CLAUDE.md)** — Critical rules, GitHub strategy, scraper details (private, local only)

---

## GitHub Policy

✅ **Tracked:**
- `nipharma-frontend/` — React source code
- `nipharma-backend/` — FastAPI + ML model (`panel_model.pkl`)
- `scrapers/*.py` — Data collection scripts

❌ **Never Committed:**
- `scrapers/data/` — CSV data files
- `NPT_Invoice_Data/` — Invoice PDFs, supplier prices, session cookies
- `.env` files — Local API keys

---

## Support & Contact

- **Issues:** GitHub Issues (private repo)
- **Live Site:** https://nipharm-shortage-intelligence.vercel.app
- **Backend Status:** https://npt-stock-intel-production.up.railway.app/health

---

**Last Updated:** April 2026 | **Model:** v4 deployed, v5 ready | **Status:** Production ✅
