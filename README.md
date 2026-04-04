# Nipharma — Stock Intelligence Platform

A real-time pharmaceutical shortage prediction platform for UK community pharmacies. Uses Random Forest ML (AUC 0.9983) combined with live market signals to predict NHS drug concessions before they happen—enabling pharmacists to stock at tariff price before prices surge.

**Live Site:** https://nipharm-shortage-intelligence.vercel.app

---

## Key Features

- **Drug Search** — 26 essential medicines with BUY NOW/BUFFER/MONITOR recommendations
- **Shortage Intelligence** — ML predictions updated monthly + real-time signal boosting
- **Market News** — Curated pharmaceutical industry updates
- **Chatbot** — AI-powered Q&A with live web search (Groq + Tavily)
- **Analytics Dashboard** — Supply chain trends, MHRA alerts, top shortage risks
- **Weekly Report** — Newspaper-style intelligence brief (printable)
- **Tariff Calculator** — NHS price lookup + bulk discount estimator

---

## Architecture

| Component | Tech | Hosted |
|-----------|------|--------|
| Frontend | React 18 + TypeScript | Vercel |
| Backend | Python FastAPI + Groq LLM | Railway |
| ML Model | Random Forest (scikit-learn) | GitHub + Railway |
| Data Layer | CSV files + CPE/MHRA/Market APIs | Local + Railway |

### Key Endpoints

```
POST   /predict              # ML shortage prediction (28 features)
GET    /health               # Backend status
GET    /news                 # Pharmaceutical news feed
GET    /mhra-alerts          # MHRA shortage publications
POST   /chat                 # Groq LLM + Tavily search
GET    /weekly-report        # Intelligence summary
POST   /contact              # Contact form
```

---

## ML Model (v4)

**Random Forest Classification**
- Training data: 44,074 rows (758 drugs × 60 months historical)
- Performance: AUC 0.9983, 5-fold stratified cross-validation
- Features: 28 (pricing, concessions, FX/commodity signals, MHRA mentions, demand spikes)
- Retraining: Monthly (invoice data insufficient for daily patterns)

**Hybrid Prediction Scoring**
- 70% ML probability + 30% real-time signal boost
- Real-time signals: MHRA alerts, CPE availability, demand spikes, price stress, stock shortages

**Top Features by Importance**
1. On concession (28.2%)
2. Concession streak (24.7%)
3. History last 6mo (18.9%)
4. Price change MoM (13.7%)
5. Distance from floor (5.8%)

[Full model details](./nipharma-backend/README.md#ml-model-v4-specifications)

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

## Data Sources

| Source | Type | Frequency | Status |
|--------|------|-----------|--------|
| NHSBSA Drug Tariff | Pricing | Daily | ✅ Live |
| CPE (Concessions) | Concession events | Monthly | ✅ Live (archive + current) |
| MHRA Publications | Shortage alerts | Ad-hoc | ✅ Live |
| Brent Crude (yfinance) | Market stress | Daily | ✅ Live |
| FX Rates (Frankfurter) | GBP/INR | Daily | ✅ Live |
| BoE Bank Rate | Interest rates | Quarterly | ✅ Live |
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
  server/main.py            7 endpoints (health, predict, chat, news, alerts, report, contact)
  requirements.txt          FastAPI, Pydantic, scikit-learn, pandas, numpy
  README.md                 API & ML model documentation

scrapers/                   Data collection scripts (local only, ~27 scripts)
  12_ml_model_panel.py      Random Forest training
  data/                     Feature store + model artifacts
```

---

## Key Technologies

- **ML:** scikit-learn (Random Forest), pandas, numpy
- **Backend:** FastAPI, uvicorn, Pydantic
- **Frontend:** React 18, TypeScript, React Router
- **LLM:** Groq (llama-3.1-8b-instant), Tavily (web search)
- **Data:** CSV-based feature store (15,378 rows, 28 features)

---

## Roadmap

### v4 (Current) ✅
- ML model with 28 features (added CPE prices)
- Hybrid /predict endpoint (70% ML + 30% signals)
- Full frontend + backend integration
- Detailed model documentation

### v5 (Planned)
- Seasonal pattern signal (month × BNF category)
- Manufacturer count signal (MHRA marketing authorisations)
- Prescribing demand trends (NHSBSA PCA data)
- API response caching (6hr TTL)

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

**Last Updated:** April 2026 | **Model:** v4 (AUC 0.9983) | **Status:** Production ✅
