# Nipharma Tech Stock Intelligence — Claude Context File

> Paste this into a new Claude chat to give full project context.
> After reading, tell me what's in the Current Status section and ask what to work on.

---

## CRITICAL RULES — READ FIRST BEFORE DOING ANYTHING

1. **NEVER rebuild scrapers that already exist.** Check the file exists before writing any code.
2. **NEVER commit sessions/*.json, invoice PDFs, or any NPT_Invoice_Data/ contents to GitHub.** Only `.py` source files are safe to commit.
3. **NEVER run ML model scripts via Claude Code.** Claude uses ~46GB RAM → OS kills Python (exit code 144). Always run in Terminal manually.
4. **NEVER hardcode staff email addresses in frontend code.** Use Resend API with emails stored in Railway env vars.
5. **CI=false must always be in vercel.json buildCommand.** Without it, ESLint warnings fail Vercel builds silently.

---

## Project Summary

**Nipharma Tech Stock Intelligence** — live web platform for UK community pharmacies. Predicts NHS drug shortages before they become concession events so pharmacists can buy stock at NHS tariff price before prices rise.

- **Live frontend:** `https://nipharm-shortage-intelligence.vercel.app`
- **Live backend:** `https://npt-stock-intel-production.up.railway.app`
- **GitHub repo:** `https://github.com/skyward-27/nipharm-shortage-intelligence` (Private)
- **Local project root:** `/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/`
- **Invoice data root:** `/Users/chaitanyawarhade/Documents/NPT_Invoice_Data/` ← NEVER on GitHub

---

## Tech Stack

| Layer | Tech | Hosting |
|-------|------|---------|
| Frontend | React 18 + TypeScript (react-scripts 5, Node 20.x) | Vercel |
| Backend | Python FastAPI + Groq LLM + Tavily search | Railway |
| ML Model | Random Forest (scikit-learn) | Local / offline |
| Data store | CSV files in `scrapers/data/` | Local |

---

## Repository Structure

```
/nipharma-frontend/
  src/pages/
    Dashboard.tsx           5 KPI cards, news feed, Weekly Report banner
    MarketNews.tsx          Live pharma news from backend
    Chat.tsx                Groq LLM + Tavily chatbot
    Analytics.tsx           Supply chain charts, top 10 shortage table
    Calculator.tsx          NHS tariff calculator, bulk discount tiers
    DrugSearch.tsx          26 drugs, BUY NOW/BUFFER/MONITOR tags, BNF categories, alternatives
    Alerts.tsx              MHRA shortage alerts, severity filter
    WeeklyReport.tsx        Newspaper-style intelligence brief, Print button only
    Contact.tsx             Contact form
  src/App.tsx               Router, navbar logo = "Nipharma" only (dark #0d0d0d, no emoji)
  vercel.json               buildCommand: "CI=false npm run build", SPA rewrite catch-all
  package.json              engines: node 20.x, homepage: "."
  .env.local                REACT_APP_API_URL=https://npt-stock-intel-production.up.railway.app

/nipharma-backend/
  server/
    main.py                 FastAPI: /health, /chat, /news, /mhra-alerts, /weekly-report, /contact
    chat.py                 Groq llama-3.1-8b-instant + Tavily, system prompt: "Today's date is April 2026"
  Dockerfile                WORKDIR /app/server, uvicorn CMD

/scrapers/                  ← NOT on GitHub. Run all scripts manually in Terminal.
  17_cpni_concessions.py    ✅ EXISTS — BSO NI concession scraper
  25_download_aah_orders.py ✅ EXISTS — AAH Salesforce Aura API scraper
  26_download_alliance_documents.py ✅ EXISTS — Alliance Liferay REST scraper
  01–16 scraper scripts     ✅ EXIST (see Data Sources table below)
  data/                     All collected CSVs
  app.py                    Streamlit dashboard (local only)
```

---

## GitHub — What Is and Isn't Tracked

| Location | On GitHub? | Reason |
|----------|-----------|--------|
| `nipharma-frontend/` | ✅ Yes | React app |
| `nipharma-backend/` | ✅ Yes | FastAPI backend |
| `scrapers/*.py` | ❌ No | Never committed — run locally only |
| `scrapers/data/` | ❌ No | CSV data files, local only |
| `NPT_Invoice_Data/` | ❌ NEVER | Invoices, supplier prices, session cookies — commercially sensitive |
| `NPT_Invoice_Data/sessions/*.json` | ❌ NEVER | Login cookies for AAH + Alliance portals |
| `.env.local` | ❌ No | Backend URL — gitignored |

---

## Current Status (as of April 2026)

### What's Working ✅
- Live site at Vercel — all 8 pages load correctly
- Backend on Railway — health, chat, news, alerts, weekly-report endpoints all live
- Navbar shows "Nipharma" only (dark #0d0d0d, no emoji, no subtitle)
- Drug Search — 26 drugs, BUY NOW/BUFFER/MONITOR tags, BNF categories, alternative drugs
- Chat — Groq llama-3.1-8b-instant + Tavily, date set to April 2026
- Weekly Report — concise card layout, Print button only
- All navigation fixed — React Router Links (was broken anchor tags)
- Vercel builds fixed — CI=false in vercel.json, unused vars removed from WeeklyReport.tsx

### What's Working ✅ (updated April 2026)
- **ML Model v4** — DEPLOYED. Random Forest trained on 44,074 rows (758 drugs × 60 months), AUC 0.9983 (5-fold CV), 28 features (added 13 concession price features from CPE scraper)
- **/predict endpoint** — LIVE at https://npt-stock-intel-production.up.railway.app/predict. Hybrid scoring: 70% ML model + 30% real-time signals (MHRA, CPE, demand, price stress, stock shortage)
- **Model file on GitHub** — nipharma-backend/model/panel_model.pkl (5.0 MB) committed to repo. Fixed .gitignore precedence: *.pkl rule now before negations.
- **27_download_aah_invoices.py** — FULLY WORKING. Login → Invoice Portal → AAH popup → BlackLine SSO → CSV export (829KB) + ZIP download (2.8MB). Cookies saved to `aah_invoice_session.json`.
- **26_download_alliance_documents.py** — Login WORKING. Cookie saving working. Extended SPA wait timeout (120s) + reload fallback handles slow Angular loading. Downloads 56 invoices/month.
- **28_extract_chrome_cookies.py** — Multi-profile scanning works. Profile 13 has credentials for both AAH and Alliance.
- **Detailed Technical Report** — Generated: NIPHARMA_MODEL_DEPLOYMENT_DETAILED_REPORT.docx (195 paragraphs, 4 tables, saved to ~/Downloads). Covers: v4 training results, hybrid scoring logic, all 8 problems faced + solutions, why 5 alternatives rejected (RAG, LLM, ensemble, daily retraining, API-only), 27 scrapers reference, deployment architecture, monthly retraining schedule.

### Known Issues / Not Yet Done ❌
- **AAH scraper (25)** — Watchlist empty → getProductDetails returns error. Fix: add drugs to watchlist at https://www.aah.co.uk/s/aahhub manually first.
- **NI concession scraper (17)** — script exists. Output: 453 rows in scrapers/data/concessions/cpni_concessions.csv.
- **Special Watch Flags** — top 3 urgent drugs not yet on Dashboard/Weekly Report
- **Automated weekly email** — Resend.com not built yet
- **Prescribing demand data** — 13_openprescribing.py still downloading (60 files, slow NHSBSA server)
- **Seasonal pattern feature** — not in panel store (planned for model v5)
- **Manufacturer count signal** — MHRA marketing authorisation scraper not built (planned for model v5)
- **Frontend /predict integration** — DrugSearch.tsx not yet calling /predict endpoint (next phase)
- **Streamlit dashboard** — local only, jinja2 missing error, numpy<2 required
- **BNF code join** — molecule_master.csv all 24,465 rows have null bnf_code

---

## Scraper Scripts — Full Detail

### Public Data Scrapers (in `scrapers/`)

| Script | Source | Output | Status |
|--------|--------|--------|--------|
| 01_nhsbsa_drug_tariff.py | NHSBSA Part VIII Cat M (24mo) | `data/drug_tariff/drug_tariff_202603.csv` | ✅ |
| 02_ncso_price_concessions.py | CPE current month concessions | `data/concessions/cpe_current_month.csv` | ✅ |
| 04_mhra_alerts.py | MHRA shortage publications | `data/mhra/govuk_shortage_publications.csv` | ✅ |
| 05_market_signals.py | FX (Frankfurter API), BoE, OpenFDA | `data/market_signals/` | ✅ |
| 06_molecule_master.py | dm+d molecules (NHSBSA) | `data/molecule_master/molecule_master.csv` | ✅ |
| 08_cpe_historical_concessions.py | CPE archive Jan 2020–Feb 2026 | `data/concessions/cpe_archive_full.csv` | ✅ |
| 09_feature_store_builder.py | Flat 758-mol feature store | `data/features/feature_store.csv` | ✅ |
| 11_feature_store_panel.py | Time-series panel 15,378 rows | `data/features/panel_feature_store.csv` | ✅ |
| 12_ml_model_panel.py | RF model v3 | `data/model/panel_model.pkl` | ✅ — run in Terminal only |
| 13_openprescribing.py | NHSBSA PCA demand (60 files) | pending | ⏳ still downloading |
| 14_nhsbsa_ssp.py | SSP Register | `data/ssp/ssp_parsed.csv` | ✅ 87 SSPs, 6 active |
| 16_yfinance_signals.py | Brent crude + Sun Pharma daily | `data/market_signals/brent_crude.csv` | ✅ |
| **17_cpni_concessions.py** | BSO NI concessionary prices | `data/concessions/cpni_concessions.csv` | ✅ exists, not yet run successfully |

### Supplier Scrapers — SENSITIVE (in `scrapers/`, data in `NPT_Invoice_Data/`)

#### 25_download_aah_orders.py — AAH Hub Wholesale Price Scraper
- **Portal:** `https://www.aah.co.uk/s/aahhub` (Salesforce Community)
- **API:** `https://www.aah.co.uk/s/sfsites/aura` (Salesforce Aura JSON API)
- **Key API call:** `other.AAHHubDashboard.getProductDetails=1` (r=7) → returns live price + stock per product code
- **Account:** 18035270X | **Branch:** 405N | **Company:** J. MCGREGOR (CHEMIST) LTD
- **Session file:** `/Users/chaitanyawarhade/Documents/NPT_Invoice_Data/sessions/aah_session.json`
- **Output dir:** `/Users/chaitanyawarhade/Documents/NPT_Invoice_Data/aah_hub/api_data/`
- **Auth mechanism (FIXED April 2026):** `aura.token` must be the `__Host-ERIC_PROD-*` cookie value (NOT sid cookie). Script gets this by doing a GET to the portal page first, which causes Salesforce to set the ERIC cookie in the session, then uses it.
- **fwuid + loaded hash:** Both extracted dynamically from the portal page HTML on every run. Do NOT use cached values.
- **getProductDetails blocker:** Returns "Error fetching product details" if the AAH Hub watchlist is EMPTY. To fix: log into https://www.aah.co.uk/s/aahhub → search for your regular products → add them to watchlist. Then getProductDetails will return their live prices.
- **Invoice portal:** AAH invoices are NOT in AAH Hub. They're in a separate BlackLine portal. `hasInvoicePortalAccess: False` for this account in Salesforce. Need BlackLine scraper (see 27_extract_blackline.py task).
- **Monthly workflow:** Log in → run 28_extract_chrome_cookies.py → run 25_download_aah_orders.py
- **NEVER commit:** sessions/*.json or any downloaded data

#### 26_download_alliance_documents.py — Alliance Healthcare Document Downloader
- **Portal:** `https://my.alliance-healthcare.co.uk/group/pro/documents` (Liferay-based)
- **API:** `https://my.alliance-healthcare.co.uk/b2b-backend/api/` (REST endpoints)
- **Downloads:** Invoices, Credit Notes, Statements (all PDF)
- **Account:** 1025850 | **UserId:** 37105346 | **Company:** J MCGREGOR (CHEMIST) LIMITED
- **Session file:** `/Users/chaitanyawarhade/Documents/NPT_Invoice_Data/sessions/alliance_session.json`
- **Output dir:** `/Users/chaitanyawarhade/Documents/NPT_Invoice_Data/alliance/raw_pdfs/`
- **Auth mechanism:** Liferay + CAS SSO. Key cookies: `JSESSIONID`, `TGC` (CAS Ticket Granting Cookie), `SAML_SP_SESSION_KEY`. Sessions expire in ~30 minutes.
- **Monthly workflow:** Log into https://my.alliance-healthcare.co.uk in Chrome → run 28_extract_chrome_cookies.py WITHIN 30 MINUTES → run 26_download_alliance_documents.py immediately.
- **Document list API:** `/b2b-backend/api/documents?customerCode=1025850&documentType=INVOICE&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD&page=0&size=200`
- **NEVER commit:** sessions/*.json or any downloaded PDFs

#### 28_extract_chrome_cookies.py — Monthly Cookie Extractor
- **Purpose:** Reads session cookies from Chrome after manual login. No credentials stored.
- **Run monthly:** Log into both portals in Chrome → run immediately → then run 25 and 26
- **AAH:** Extracts `__Host-ERIC_PROD-*`, `sid`, `sid_Client`, `renderCtx` cookies
- **Alliance:** Extracts `JSESSIONID`, `TGC`, `SAML_SP_SESSION_KEY` cookies — must run within 30 min of login
- **Output:** `sessions/aah_session.json` and `sessions/alliance_session.json`

#### 17_cpni_concessions.py — Community Pharmacy NI Scraper
- **Source:** `https://bso.hscni.net/` (BSO — NI's equivalent of NHSBSA)
- **Concessions URL:** `https://bso.hscni.net/directorates/operations/family-practitioner-services/pharmacy/contractor-information/drug-tariff-and-related-materials/concessionary-prices/`
- **Key finding:** NI applies England's concessions exactly — this scraper confirms that and captures from BSO source
- **Output:** `scrapers/data/concessions/cpni_concessions.csv`
- **No login required** — public BSO page, safe to run anytime
- **Safe to commit:** script and output CSV are both fine for GitHub

---

## ML Model Details

### Feature Store: `scrapers/data/features/panel_feature_store.csv`
- 15,378 rows = 758 molecules × 24 months (Apr 2021 – Jan 2026)
- 2,266 positive labels (14.7%) — "on concession next month"

### All 15 Features (by importance)
| Feature | Importance | What It Is |
|---------|-----------|------------|
| on_concession | 28.2% | Is drug on concession THIS month? |
| concession_streak | 24.7% | Consecutive months on concession |
| conc_last_6mo | 18.9% | Times conceded in last 6 months |
| price_mom_pct | 13.7% | Month-on-month tariff price change % |
| floor_proximity | 5.8% | Distance from 24-month price floor |
| within_15pct_of_floor | 3.2% | Binary: within 15% of floor price |
| mhra_mention_count | 2.4% | MHRA shortage publications last 12mo |
| fx_stress_score | 1.8% | GBP/INR 30-day rolling z-score |
| boe_bank_rate | 1.5% | BoE base interest rate |
| brent_stress | 1.1% | Brent crude 30-day z-score (currently 3.53 — elevated) |
| brent_mom_pct | 0.9% | Brent crude month-on-month % change |
| sunpharma_stress | 0.9% | Sun Pharma stock 30-day z-score |
| ssp_flag | 0.6% | Active NHS Serious Shortage Protocol |
| price_yoy_pct | 0.2% | Year-on-year tariff price change % |
| us_shortage_flag | 0.1% | On FDA shortage list (weak — naming mismatch) |

### Model Version History
| Version | AUC | Training Rows | What Changed |
|---------|-----|--------------|-------------|
| v1 (flat) | 0.891 | 758 | One row per drug, no time dimension |
| v2 (panel) | 0.971 | 14,764 | Added streak, recent history, time series |
| v3 | 0.982 | 14,764 | Added Brent crude + Sun Pharma (yfinance) |
| v4 (current) | 0.9983 | 44,074 | Added CPE prices (13 features), hybrid /predict endpoint deployed |

### CRITICAL: Always Run ML in Terminal — Never via Claude
```bash
cd "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/scrapers"
python 12_ml_model_panel.py    # retrain model
streamlit run app.py           # local dashboard (needs numpy<2 and jinja2)
```

---

## Key Decisions Made

- **Perplexity vs historical training** — separate concerns. ML model stays on historical CSV data (core IP). Chatbot uses Groq+Tavily (free). Perplexity sonar-pro upgrade (~£5/mo) deferred until paying customers.
- **BNF copyright** — BNF-80.pdf is copyrighted BMJ/RPS. We use WHO ATC codes instead. Drug categories in Drug Search labelled CV/GI/CNS etc. not pulled from BNF directly.
- **Port import data** — HMRC Trade Info API has 3-month lag, quarterly data. Too slow for monthly shortage prediction. Brent crude (daily, yfinance) is a better proxy.
- **Email security** — Staff emails must NEVER be in frontend source code. Use Resend API with emails in Railway environment variables.
- **Node version** — Must be 20.x for Vercel (18.x discontinued, 24.x breaks react-scripts/ajv).
- **CI=false** — Must be in vercel.json buildCommand. Without it, ESLint warnings fail every Vercel build silently.
- **AAH/Alliance data** — Wholesale prices and invoice PDFs are under supplier agreements. Never on GitHub.

---

## Priority Next Steps (order matters)

1. **Frontend /predict integration** — DrugSearch.tsx to call /predict endpoint (medium effort, high value)
2. **AAH watchlist** — log into https://www.aah.co.uk/s/aahhub, search for regular drugs, add to watchlist so getProductDetails works
3. **Alliance + AAH monthly data run** — log in → run 28_extract_chrome_cookies.py within 30 min → run 25 and 26 scripts
4. **API response caching** — cache /predict results for 6 hrs to reduce compute
5. **Automated email** — Resend.com, every Monday, staff list in Railway env vars
6. **Model v5 (seasonal pattern)** — add month × BNF category feature (Q2 2026)
7. **Model v5 (manufacturer count)** — MHRA marketing authorisation database scraper (Q2 2026)
8. **Model v5 (demand trend)** — complete 13_openprescribing.py → join PCA demand features

---

## Comparison vs Pills Stock Intelligence (competitor, March 2026)

### Our Advantages
- Interactive 8-page web app (they are PDF only)
- AI chatbot with real-time web search (Groq + Tavily)
- Brent crude + Sun Pharma market signals
- Alternative drug recommendations

### Gaps We've Closed (April 2026)
- BUY NOW / BUFFER / MONITOR action tags ✅
- BNF therapeutic categories ✅

### Still Behind Pills
- Seasonal pattern signal (1.4% importance) — planned v4
- Manufacturer count signal (3.1% importance) — planned v4
- Prescribing demand trend (2.8% importance) — pending 13_openprescribing.py
- WhatsApp alerts (their Q3 2026 roadmap)
- PMR integration (their Q2 2026 roadmap)

---

## Bugs Fixed History (for reference — don't re-fix these)

1. Vercel CI=true treating ESLint warnings as errors → CI=false in vercel.json
2. Unused `emailBody`/`emailSubject` vars in WeeklyReport.tsx → removed
3. Navbar logo blue colour → fixed to `#0d0d0d`
4. Groq model llama3-8b-8192 decommissioned → switched to llama-3.1-8b-instant
5. Chat giving 2025 answers → system prompt specifies April 2026
6. Metformin 1g missing from Drug Search → added with alternative
7. Email Team button exposing staff emails → removed entirely
8. Backend Dockerfile WORKDIR wrong → fixed to /app/server
9. Navigation broken (anchor tags) → React Router Links throughout
10. Vercel 404 on direct URL → vercel.json SPA catch-all rewrite
11. Node 18.x discontinued on Vercel → pinned to 20.x
12. groq SDK pydantic v2 conflict → replaced with direct HTTP requests to Groq API
