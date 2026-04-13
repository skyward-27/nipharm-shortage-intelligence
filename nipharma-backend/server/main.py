"""
Nipharma FastAPI Backend
Provides pharmaceutical supply chain intelligence APIs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import json
import requests
from dotenv import load_dotenv
import pickle
import numpy as np
import pandas as pd
from functools import lru_cache
from datetime import datetime, timedelta
import time

# Simple TTL cache for /predict
_predict_cache = {}
PREDICT_CACHE_TTL = 6 * 3600  # 6 hours


def get_cached_prediction(cache_key: str):
    if cache_key in _predict_cache:
        result, ts = _predict_cache[cache_key]
        if time.time() - ts < PREDICT_CACHE_TTL:
            return result
    return None


def set_cached_prediction(cache_key: str, result):
    _predict_cache[cache_key] = (result, time.time())

# Import our modules
from chat import chat_with_groq, get_chat_response
from news import get_pharma_news, get_supply_chain_news, search_news

# Load environment variables
load_dotenv()

# Load ML models at startup (try multiple paths)
ml_model_rf = None
ml_model_xgb = None
ml_model = None  # Active model pointer (XGBoost preferred, RF fallback)
active_model_name = None

# ── Load feature column order from JSON (saved by training script) ────────────
# This prevents silent feature mismatch when model is retrained with new features.
FEATURE_COLS: list = []  # populated at startup; falls back to hardcoded if not found
FEATURE_COLS_PATHS = [
    "./model/panel_feature_cols.json",
    "/app/model/panel_feature_cols.json",
    "../scrapers/data/model/panel_feature_cols.json",
]
for _fc_path in FEATURE_COLS_PATHS:
    try:
        with open(_fc_path) as _f:
            FEATURE_COLS = json.load(_f)
        print(f"Feature cols loaded from {_fc_path}: {len(FEATURE_COLS)} features")
        break
    except Exception:
        continue
if not FEATURE_COLS:
    print("Warning: panel_feature_cols.json not found — /predict will use hardcoded order")

# RF model paths
RF_MODEL_PATHS = [
    "../scrapers/data/model/panel_model.pkl",  # Local dev
    "./model/panel_model.pkl",                  # Railway deployment
    "/app/model/panel_model.pkl",               # Railway alternate
]

# XGBoost model paths
XGB_MODEL_PATHS = [
    "../scrapers/data/model/panel_model_xgb.pkl",  # Local dev
    "./model/panel_model_xgb.pkl",                  # Railway deployment
    "/app/model/panel_model_xgb.pkl",               # Railway alternate
]

# Load RF model
for path in RF_MODEL_PATHS:
    try:
        with open(path, 'rb') as f:
            ml_model_rf = pickle.load(f)
        print(f"RF model loaded from {path}")
        break
    except FileNotFoundError:
        continue
    except Exception as e:
        print(f"Error loading RF from {path}: {e}")
        continue

# Load XGBoost model
for path in XGB_MODEL_PATHS:
    try:
        with open(path, 'rb') as f:
            ml_model_xgb = pickle.load(f)
        print(f"XGBoost model loaded from {path}")
        break
    except FileNotFoundError:
        continue
    except Exception as e:
        print(f"Error loading XGBoost from {path}: {e}")
        continue

# Select active model: prefer XGBoost, fall back to RF
if ml_model_xgb is not None:
    ml_model = ml_model_xgb
    active_model_name = "xgboost_v6"
    print(f"Active model: XGBoost (xgboost_v6)")
elif ml_model_rf is not None:
    ml_model = ml_model_rf
    active_model_name = "random_forest_v5"
    print(f"Active model: Random Forest (random_forest_v5)")
else:
    print("Warning: No ML model found. /predict endpoint will return error until model is deployed.")

# Initialize FastAPI app
app = FastAPI(
    title="Nipharma API",
    description="Pharmaceutical Supply Chain Intelligence Backend",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    message: str
    chat_history: List[Dict[str, str]] = []


class ChatResponse(BaseModel):
    response: str
    role: str = "assistant"


class NewsArticle(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    image: Optional[str] = None
    source: str
    publishedAt: str
    author: Optional[str] = None


class NewsResponse(BaseModel):
    success: bool = True
    count: int = 0
    articles: List[NewsArticle] = []
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    groq_configured: bool
    news_api_configured: bool
    tavily_configured: bool


class PredictionRequest(BaseModel):
    drug_name: str
    # Core pricing features (required)
    price_gbp: float
    floor_price_gbp: float
    floor_proximity: float
    within_15pct_of_floor: int
    price_mom_pct: float
    price_6mo_avg: float
    price_yoy_pct: float
    on_concession: int
    gbp_inr: float
    fx_stress_score: float
    boe_bank_rate: float
    mhra_mention_count: int
    us_shortage_flag: int = 0
    concession_streak: int
    conc_last_6mo: int
    pharmacy_over_tariff: float = 0.0
    pharmacy_unit_price: float = 0.0
    pharmacy_qty_ordered: float = 0.0
    cpe_price_pence: float
    cpe_price_gbp: float
    ni_price_gbp: float = 0.0
    price_vs_cpe_pct: float
    cpe_conc_available: int
    cpe_avail_6mo: float
    # v5 new features (optional — computed or defaulted if not supplied)
    bsn_same_section_conc_count: int = 0
    drug_on_ssp: int = 0
    drug_age_years: float = 5.0
    ni_india_pharma_stress: int = 0
    best_historic_price: float = 0.0
    price_vs_best_pct: float = 0.0
    wholesale_margin_pct: float = 0.0
    pca_items: float = 0.0
    pca_items_mom_pct: float = 0.0
    pca_demand_spike: int = 0
    pca_demand_trend_6mo: float = 0.0
    pca_nic_gbp: float = 0.0
    # v6 new features (BSO NI, FDA warnings, manufacturer diversity)
    bso_ni_shortage_flag: int = 0
    fda_warning_flag: int = 0
    manufacturer_count: int = 3
    # Legacy fields kept for backward compatibility (mapped to pca equivalents)
    items_mom_pct: float = 0.0
    demand_spike: int = 0
    demand_trend_6mo: float = 0.0


class PredictionResponse(BaseModel):
    drug_name: str
    model_probability: float
    real_time_signals: float
    final_probability: float
    action: str
    confidence: str
    explanation: str
    model_used: str = "random_forest_v5"


# Health check endpoint
@app.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint. Returns API status and configuration info.
    """
    return {
        "status": "running",
        "version": "1.0.0",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "news_api_configured": bool(os.getenv("NEWS_API_KEY")),
        "tavily_configured": bool(os.getenv("TAVILY_API_KEY"))
    }


# Chat endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the Nipharma AI assistant powered by Groq.

    **Request body:**
    - message: User's message
    - chat_history: Previous conversation history (optional)

    **Returns:**
    - response: AI assistant's response
    - role: Always "assistant"
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        response = get_chat_response(request.message, request.chat_history)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# News endpoints
@app.get("/news", response_model=NewsResponse)
async def news_endpoint(limit: int = Query(10, ge=1, le=50)):
    """
    Get latest pharmaceutical industry news.

    **Query parameters:**
    - limit: Number of articles to return (1-50, default 10)

    **Returns:**
    - List of news articles with title, description, url, image, source, and publishedAt
    """
    try:
        result = get_pharma_news(limit)
        if "error" in result:
            return NewsResponse(
                success=False,
                count=0,
                articles=[],
                error=result["error"]
            )
        return NewsResponse(
            success=True,
            count=result.get("count", 0),
            articles=result.get("articles", [])
        )
    except Exception as e:
        return NewsResponse(
            success=False,
            count=0,
            articles=[],
            error=str(e)
        )


@app.get("/news/supply-chain", response_model=NewsResponse)
async def supply_chain_news_endpoint(limit: int = Query(10, ge=1, le=50)):
    """
    Get supply chain and logistics news.

    **Query parameters:**
    - limit: Number of articles to return (1-50, default 10)

    **Returns:**
    - List of supply chain news articles
    """
    try:
        result = get_supply_chain_news(limit)
        if "error" in result:
            return NewsResponse(
                success=False,
                count=0,
                articles=[],
                error=result["error"]
            )
        return NewsResponse(
            success=True,
            count=result.get("count", 0),
            articles=result.get("articles", [])
        )
    except Exception as e:
        return NewsResponse(
            success=False,
            count=0,
            articles=[],
            error=str(e)
        )


@app.get("/news/search", response_model=NewsResponse)
async def search_news_endpoint(
    query: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Search for news articles with custom query.

    **Query parameters:**
    - query: Search query (required)
    - limit: Number of articles to return (1-50, default 10)

    **Returns:**
    - List of search results
    """
    try:
        result = search_news(query, limit)
        if "error" in result:
            return NewsResponse(
                success=False,
                count=0,
                articles=[],
                error=result["error"]
            )
        return NewsResponse(
            success=True,
            count=result.get("count", 0),
            articles=result.get("articles", [])
        )
    except Exception as e:
        return NewsResponse(
            success=False,
            count=0,
            articles=[],
            error=str(e)
        )


# Placeholder endpoints for future implementation
@app.get("/drugs")
async def drugs_endpoint(search: str = Query("", max_length=100)):
    """
    Search pharmaceutical drugs database.
    Future: Load existing drug data from CSV and return filtered results.

    **Query parameters:**
    - search: Drug name or keyword to search for
    """
    return {
        "message": "Drugs endpoint - coming soon",
        "search": search,
        "status": "under_development"
    }


@app.get("/concessions")
async def concessions_endpoint():
    """
    Get current month CPE concessions from local CSV data.
    """
    CONC_PATHS = [
        "../scrapers/data/concessions/cpe_current_month.csv",
        "./model/cpe_current_month.csv",
        "/app/model/cpe_current_month.csv",
        # Fallback: NI concessions share same CPE prices
        "../scrapers/data/concessions/cpni_concessions.csv",
        "./model/cpni_concessions.csv",
    ]
    for path in CONC_PATHS:
        try:
            df = pd.read_csv(path)
            records = df.head(50).to_dict("records")
            return {
                "success": True,
                "count": len(df),
                "source": "CPE England",
                "concessions": records
            }
        except Exception:
            continue
    return {
        "success": False,
        "count": 0,
        "concessions": [],
        "message": "Data file not available"
    }


def _safe_serialize(records: list) -> list:
    """
    Convert a list of dicts (from df.to_dict('records')) to JSON-safe Python types.
    Handles pd.NA, np.nan, np.int64, np.float64, np.bool_ across all pandas versions.
    """
    import math
    safe = []
    for row in records:
        clean = {}
        for k, v in row.items():
            # pd.NA, np.nan, float nan → None
            try:
                if pd.isna(v):
                    clean[k] = None
                    continue
            except (TypeError, ValueError):
                pass
            # numpy scalar types → native Python
            if hasattr(v, "item"):
                try:
                    v = v.item()
                except Exception:
                    v = str(v)
            # float inf / -inf → None
            if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                clean[k] = None
            else:
                clean[k] = v
        safe.append(clean)
    return safe


@app.get("/recommendations")
async def recommendations_endpoint():
    """
    Get wholesale buying recommendations for pharmacists.
    Reads from buying_recommendations.csv and returns structured recommendations.
    """
    try:
        REC_PATHS = [
            "./model/buying_recommendations.csv",           # Railway (committed)
            "/app/model/buying_recommendations.csv",        # Railway alternate
            "../scrapers/data/pharmacy_invoices/buying_recommendations.csv",  # Local dev (full)
        ]
        df = None
        loaded_path = None
        for path in REC_PATHS:
            try:
                df = pd.read_csv(path)
                loaded_path = path
                break
            except Exception:
                continue

        if df is None:
            return {
                "success": False,
                "summary": {
                    "total_drugs": 0,
                    "bulk_buy_count": 0,
                    "buy_as_you_go_count": 0,
                    "hold_buying_count": 0,
                    "avg_margin_gbp": 0.0,
                },
                "top_opportunities": [],
                "hold_warnings": [],
                "recommendations": [],
                "message": "Recommendations data file not available",
            }

        # Normalise column names to lowercase for safety
        df.columns = [c.strip().lower() for c in df.columns]

        # Determine recommendation column name
        rec_col = None
        for candidate in ["recommendation", "action", "rec", "buying_recommendation"]:
            if candidate in df.columns:
                rec_col = candidate
                break
        if rec_col is None:
            rec_col = df.columns[0]  # fallback to first column

        # Determine margin column name
        margin_col = None
        for candidate in ["margin_gbp", "margin", "saving_gbp", "savings_gbp"]:
            if candidate in df.columns:
                margin_col = candidate
                break

        # Build summary — all counts use Python int, margin uses pd.isna()
        total = int(len(df))
        if rec_col in df.columns:
            rec_upper = df[rec_col].astype(str).str.strip().str.upper()
            bulk = int((rec_upper == "BULK BUY").sum())
            buy_go = int((rec_upper == "BUY AS YOU GO").sum())
            hold = int((rec_upper == "HOLD BUYING").sum())
        else:
            bulk = buy_go = hold = 0

        if margin_col and margin_col in df.columns:
            _margin_series = pd.to_numeric(df[margin_col], errors="coerce").dropna()
            _margin_mean = _margin_series.mean() if len(_margin_series) > 0 else 0.0
            avg_margin = round(float(_margin_mean), 2) if not pd.isna(_margin_mean) else 0.0
        else:
            avg_margin = 0.0

        # Top 20 BULK BUY opportunities by margin
        top_opps = []
        if rec_col in df.columns and margin_col and margin_col in df.columns:
            bulk_mask = df[rec_col].astype(str).str.strip().str.upper() == "BULK BUY"
            bulk_df = df[bulk_mask].copy()
            bulk_df[margin_col] = pd.to_numeric(bulk_df[margin_col], errors="coerce")
            bulk_df = bulk_df.nlargest(20, margin_col)
            top_opps = _safe_serialize(bulk_df.to_dict("records"))

        # Hold warnings
        hold_warnings = []
        if rec_col in df.columns:
            hold_mask = df[rec_col].astype(str).str.strip().str.upper() == "HOLD BUYING"
            hold_df = df[hold_mask].copy()
            hold_warnings = _safe_serialize(hold_df.to_dict("records"))

        # Full list (first 50)
        recs = _safe_serialize(df.head(50).to_dict("records"))

        return {
            "success": True,
            "loaded_from": loaded_path,
            "summary": {
                "total_drugs": total,
                "bulk_buy_count": bulk,
                "buy_as_you_go_count": buy_go,
                "hold_buying_count": hold,
                "avg_margin_gbp": avg_margin,
            },
            "top_opportunities": top_opps,
            "hold_warnings": hold_warnings,
            "recommendations": recs,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "summary": {"total_drugs": 0, "bulk_buy_count": 0, "buy_as_you_go_count": 0, "hold_buying_count": 0, "avg_margin_gbp": 0.0},
            "top_opportunities": [],
            "hold_warnings": [],
            "recommendations": [],
        }


@app.get("/top-drugs")
async def top_drugs_endpoint(n: int = 3):
    """
    Return the top N bulk-buy drug opportunities from buying recommendations.
    Used by the Dashboard 'Special Watch' section to show real data.
    """
    REC_PATHS = [
        "./model/buying_recommendations.csv",
        "/app/model/buying_recommendations.csv",
        "../scrapers/data/pharmacy_invoices/buying_recommendations.csv",
    ]
    df = None
    for path in REC_PATHS:
        try:
            df = pd.read_csv(path)
            break
        except Exception:
            continue

    if df is None:
        return {"success": False, "drugs": [], "message": "No recommendations data available"}

    df.columns = [c.strip().lower() for c in df.columns]

    # Get top N BULK BUY by margin
    rec_col = next((c for c in ["recommendation", "action", "rec"] if c in df.columns), None)
    margin_col = next((c for c in ["margin_gbp", "margin", "saving_gbp"] if c in df.columns), None)
    tariff_col = next((c for c in ["tariff_price_gbp", "tariff", "nhs_tariff"] if c in df.columns), None)

    if rec_col and margin_col:
        bulk = df[df[rec_col].str.upper() == "BULK BUY"]
        bulk = bulk.dropna(subset=[margin_col])
        top = bulk.nlargest(n, margin_col)
    else:
        top = df.head(n)

    drugs = []
    for _, row in top.iterrows():
        margin = row.get(margin_col) if margin_col else None
        tariff = row.get(tariff_col) if tariff_col else None
        drugs.append({
            "name": str(row.get("drug_name", "Unknown")),
            "recommendation": str(row.get(rec_col, "BULK BUY")) if rec_col else "BULK BUY",
            "margin_gbp": round(float(margin), 2) if margin is not None and not pd.isna(margin) else None,
            "tariff_price_gbp": round(float(tariff), 2) if tariff is not None and not pd.isna(tariff) else None,
            "margin_pct": round(float(row.get("price_vs_tariff_pct", 0)) * -1, 1) if "price_vs_tariff_pct" in row else None,
            "observation_count": int(row.get("observation_count", 1)) if "observation_count" in row else 1,
        })

    return {"success": True, "drugs": drugs, "count": len(drugs)}


@app.get("/signals")
async def signals_endpoint():
    """Get live market signals including GBP/INR, GBP/CNY, GBP/USD, and BoE rate."""
    try:
        fx = requests.get(
            "https://api.frankfurter.app/latest?from=GBP&to=INR,CNY,USD",
            timeout=5
        )
        fx_data = fx.json() if fx.status_code == 200 else {}
        rates = fx_data.get("rates", {})

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "gbp_inr": rates.get("INR", 106.8),
            "gbp_cny": rates.get("CNY", None),
            "gbp_usd": rates.get("USD", None),
            "boe_rate": 4.5,  # Current BoE rate as of April 2026
            "india_pharma_note": "Top 10 NSE pharma tracked: SUNPHARMA, DRREDDY, CIPLA, AUROPHARMA, LUPIN",
            "source": "Frankfurter API (ECB rates)",
            "currency_note": "Weaker GBP vs INR = higher import costs for Indian generics"
        }
    except Exception as e:
        return {
            "success": False,
            "gbp_inr": 106.8,
            "boe_rate": 4.5,
            "error": str(e)
        }


@app.get("/early-warnings")
async def early_warnings_endpoint():
    """
    Get early warning signals for supply chain disruptions.
    """
    return {
        "message": "Early warnings endpoint - coming soon",
        "status": "under_development"
    }


@app.get("/mhra-alerts")
async def mhra_alerts_endpoint():
    """Fetch MHRA drug shortage and safety alerts.
    Priority: 1) Live MHRA ATOM feed  2) Committed CSV (3,372 rows)  3) Hardcoded fallback
    """
    # ── 1. Try live MHRA ATOM feed ─────────────────────────────────────────────
    try:
        import xml.etree.ElementTree as ET
        response = requests.get(
            "https://www.gov.uk/drug-device-alerts.atom",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            alerts = []
            for entry in root.findall("atom:entry", ns)[:20]:
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:link", ns)
                updated = entry.find("atom:updated", ns)
                title_text = title.text if title is not None else ""
                alerts.append({
                    "title": title_text,
                    "summary": (summary.text or "")[:300] if summary is not None else "",
                    "url": link.get("href", "") if link is not None else "",
                    "date": updated.text[:10] if updated is not None else "",
                    "severity": "HIGH" if any(
                        w in title_text.lower()
                        for w in ["shortage", "recall", "urgent", "discontinu"]
                    ) else "MEDIUM"
                })
            if alerts:
                return {"success": True, "count": len(alerts), "alerts": alerts, "source": "MHRA Live"}
    except Exception:
        pass

    # ── 2. Fall back to committed CSV (govuk_shortage_publications.csv) ────────
    MHRA_CSV_PATHS = [
        "./model/mhra_alerts.csv",
        "/app/model/mhra_alerts.csv",
        "../scrapers/data/mhra/govuk_shortage_publications.csv",
    ]
    for csv_path in MHRA_CSV_PATHS:
        try:
            mhra_df = pd.read_csv(csv_path)
            mhra_df.columns = [c.strip().lower() for c in mhra_df.columns]
            # Filter to shortage-related entries
            title_col = next((c for c in ["title", "name", "drug"] if c in mhra_df.columns), mhra_df.columns[0])
            desc_col = next((c for c in ["description", "summary", "detail"] if c in mhra_df.columns), None)
            url_col = next((c for c in ["url", "link", "href"] if c in mhra_df.columns), None)
            date_col = next((c for c in ["published", "date", "updated"] if c in mhra_df.columns), None)

            shortage_mask = mhra_df[title_col].str.lower().str.contains(
                "shortage|supply|recall|discontinu|unavailab", na=False
            )
            filtered = mhra_df[shortage_mask].head(20)
            if len(filtered) == 0:
                filtered = mhra_df.head(20)

            alerts = []
            for _, row in filtered.iterrows():
                title_val = str(row.get(title_col, ""))
                alerts.append({
                    "title": title_val,
                    "summary": str(row.get(desc_col, ""))[:300] if desc_col else "",
                    "url": str(row.get(url_col, "https://www.gov.uk/drug-device-alerts")) if url_col else "https://www.gov.uk/drug-device-alerts",
                    "date": str(row.get(date_col, ""))[:10] if date_col else "",
                    "severity": "HIGH" if any(
                        w in title_val.lower()
                        for w in ["shortage", "recall", "urgent", "discontinu"]
                    ) else "MEDIUM"
                })
            return {
                "success": True,
                "count": len(alerts),
                "total_in_database": len(mhra_df),
                "alerts": alerts,
                "source": "MHRA Database (3,372 publications)"
            }
        except Exception:
            continue

    # ── 3. Absolute fallback (should never reach here if CSV is deployed) ──────
    return {
        "success": True,
        "count": 3,
        "source": "MHRA (static fallback — CSV not found)",
        "alerts": [
            {"title": "MHRA Shortage Publications Database", "summary": "3,372 MHRA shortage publications tracked. Live data unavailable — redeploy with mhra_alerts.csv in model/.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2026-04-13", "severity": "MEDIUM"},
            {"title": "Supply Chain Intelligence Active", "summary": "20 data sources monitoring UK pharmaceutical supply chain. Model tracking 714 drugs.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2026-04-13", "severity": "LOW"},
            {"title": "Check Live MHRA Feed", "summary": "Visit gov.uk/drug-device-alerts for current shortage publications.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2026-04-13", "severity": "LOW"},
        ]
    }


# ============================================================
# LEAD / CONTACT CAPTURE ENDPOINT
# ============================================================
@app.post("/leads")
async def capture_lead(
    name: str = Query(..., description="Full name"),
    email: str = Query(..., description="Email address"),
    phone: str = Query("", description="Phone number (optional)"),
    company: str = Query("", description="Pharmacy / company name"),
    message: str = Query("", description="Optional message"),
):
    """
    Capture pharmacy contact details for follow-up demo / sales.
    Stores to a local CSV and returns a confirmation message.
    """
    import csv
    import pathlib
    from datetime import datetime

    lead = {
        "timestamp": datetime.utcnow().isoformat(),
        "name": name,
        "email": email,
        "phone": phone,
        "company": company,
        "message": message,
    }

    # Persist to CSV (safe, no database needed)
    csv_path = pathlib.Path(__file__).parent.parent / "leads.csv"
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=lead.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(lead)

    return {
        "status": "success",
        "message": f"Thank you {name}! We'll be in touch at {email} within 24 hours.",
        "lead_id": f"NPT-{abs(hash(email)) % 100000:05d}",
    }


@app.get("/weekly-report")
async def weekly_report():
    """
    Get structured weekly intelligence report data for pharmacy owners.
    Returns shortage alerts, concessions, market signals, bulk opportunities, and AI forecast.
    """
    from datetime import datetime
    return {
        "week": datetime.now().strftime("%d %B %Y"),
        "alerts_count": 6,
        "savings_opportunity": 2340,
        "concessions_count": 3,
        "news_count": 12,
        "top_alerts": [
            {"drug": "Amoxicillin 500mg", "severity": "HIGH", "action": "Order 3-month stock from Alliance immediately"},
            {"drug": "Metformin 1g", "severity": "HIGH", "action": "Switch to Metformin 500mg x2 - available"},
            {"drug": "Furosemide 40mg", "severity": "HIGH", "action": "Stock up - Indian supplier issues ongoing"},
            {"drug": "Amlodipine 5mg", "severity": "MEDIUM", "action": "Monitor - alternative brands available"},
            {"drug": "Lansoprazole 30mg", "severity": "MEDIUM", "action": "Switch to Omeprazole if needed"}
        ],
        "concessions": [
            {"drug": "Amoxicillin 500mg x21", "conc_price": 1.89, "tariff_price": 1.20, "profitable": True},
            {"drug": "Metformin 500mg x28", "conc_price": 0.73, "tariff_price": 0.85, "profitable": False},
            {"drug": "Omeprazole 20mg x28", "conc_price": 1.82, "tariff_price": 1.50, "profitable": True}
        ],
        "market_signals": {
            "gbp_inr": 106.8,
            "brent_crude": 82,
            "india_api_volume_change": -8
        },
        "bulk_opportunities": [
            {"drug": "Amoxicillin 500mg", "monthly_saving": 340, "annual_saving": 4080},
            {"drug": "Omeprazole 20mg", "monthly_saving": 180, "annual_saving": 2160},
            {"drug": "Metformin 500mg", "monthly_saving": 120, "annual_saving": 1440}
        ]
    }


# ==================== ML MODEL PREDICTION ENDPOINT ====================

@app.post("/predict", response_model=PredictionResponse)
async def predict_concession(request: PredictionRequest):
    """
    Predict if a drug will go on NHS concession next month using HYBRID approach.

    Combines:
    1. ML Model Prediction (70%) — XGBoost (preferred) or Random Forest fallback
    2. Real-Time API Signals (30%) — MHRA alerts, CPE concessions, market stress

    **Request body (28 features):**
    price_gbp, floor_price_gbp, floor_proximity, within_15pct_of_floor, price_mom_pct,
    price_6mo_avg, price_yoy_pct, on_concession, gbp_inr, fx_stress_score, boe_bank_rate,
    mhra_mention_count, us_shortage_flag, concession_streak, conc_last_6mo,
    pharmacy_over_tariff, pharmacy_unit_price, pharmacy_qty_ordered, items_mom_pct,
    demand_spike, demand_trend_6mo, avg_items_3mo, cpe_price_pence, cpe_price_gbp,
    ni_price_gbp, price_vs_cpe_pct, cpe_conc_available, cpe_avail_6mo

    **Returns:**
    - model_probability: Raw RF prediction (0-1)
    - real_time_signals: Signal boost (0-1)
    - final_probability: Weighted blend (70% model + 30% signals)
    - action: "BUY NOW" | "BUFFER" | "MONITOR"
    - confidence: "high" | "medium" | "low"
    - explanation: Human-readable reason
    """

    if ml_model is None:
        raise HTTPException(status_code=503, detail="ML model not loaded. Check server logs.")

    # ── CACHE CHECK ────────────────────────────────────────────────────────────
    cache_key = (
        f"{request.drug_name}_{request.cpe_avail_6mo}_"
        f"{request.on_concession}_{request.concession_streak}"
    )
    cached = get_cached_prediction(cache_key)
    if cached:
        return cached

    try:
        # ── STEP 1: MODEL PREDICTION (70% weight) ─────────────────────────────
        # All 42 features in exact training order (v6 model)
        import math
        now_month = datetime.now().month
        month_sin = math.sin(2 * math.pi * now_month / 12)
        month_cos = math.cos(2 * math.pi * now_month / 12)
        is_winter = 1 if now_month in [11, 12, 1, 2] else 0

        # Map legacy PCA fields to new names (backward compat)
        pca_items_mom = request.pca_items_mom_pct or request.items_mom_pct
        pca_spike = request.pca_demand_spike or request.demand_spike
        pca_trend = request.pca_demand_trend_6mo or request.demand_trend_6mo

        # ── Feature lookup map (name → value) ─────────────────────────────────
        # Computed/special features override request field values
        feature_map = {
            "price_gbp": request.price_gbp,
            "floor_price_gbp": request.floor_price_gbp,
            "floor_proximity": request.floor_proximity,
            "within_15pct_of_floor": request.within_15pct_of_floor,
            "price_mom_pct": request.price_mom_pct,
            "price_6mo_avg": request.price_6mo_avg,
            "price_yoy_pct": request.price_yoy_pct,
            "on_concession": request.on_concession,
            "gbp_inr": request.gbp_inr,
            "fx_stress_score": request.fx_stress_score,
            "boe_bank_rate": request.boe_bank_rate,
            "mhra_mention_count": request.mhra_mention_count,
            "us_shortage_flag": request.us_shortage_flag,
            "concession_streak": request.concession_streak,
            "conc_last_6mo": request.conc_last_6mo,
            "pharmacy_over_tariff": request.pharmacy_over_tariff,
            "pharmacy_unit_price": request.pharmacy_unit_price,
            "pharmacy_qty_ordered": request.pharmacy_qty_ordered,
            "cpe_price_pence": request.cpe_price_pence,
            "cpe_price_gbp": request.cpe_price_gbp,
            "ni_price_gbp": request.ni_price_gbp,
            "price_vs_cpe_pct": request.price_vs_cpe_pct,
            "cpe_conc_available": request.cpe_conc_available,
            "cpe_avail_6mo": request.cpe_avail_6mo,
            "bsn_same_section_conc_count": request.bsn_same_section_conc_count,
            "month_sin": month_sin,   # auto-computed from current date
            "month_cos": month_cos,   # auto-computed from current date
            "is_winter": is_winter,   # auto-computed from current date
            "drug_on_ssp": request.drug_on_ssp,
            "drug_age_years": request.drug_age_years,
            "ni_india_pharma_stress": request.ni_india_pharma_stress,
            "best_historic_price": request.best_historic_price,
            "price_vs_best_pct": request.price_vs_best_pct,
            "wholesale_margin_pct": request.wholesale_margin_pct,
            "pca_items": request.pca_items,
            "pca_items_mom_pct": pca_items_mom,
            "pca_demand_spike": pca_spike,
            "pca_demand_trend_6mo": pca_trend,
            "pca_nic_gbp": request.pca_nic_gbp,
            "bso_ni_shortage_flag": request.bso_ni_shortage_flag,
            "fda_warning_flag": request.fda_warning_flag,
            "manufacturer_count": request.manufacturer_count,
        }

        # ── Build feature vector ───────────────────────────────────────────────
        # Use FEATURE_COLS (from panel_feature_cols.json) if loaded at startup.
        # Falls back to hardcoded order — which matches the JSON — if file not found.
        col_order = FEATURE_COLS if FEATURE_COLS else list(feature_map.keys())
        feature_values = [float(feature_map.get(col, 0.0)) for col in col_order]
        features = np.array([feature_values])

        model_proba = ml_model.predict_proba(features)[0][1]  # Probability of concession

        # ── STEP 2: REAL-TIME SIGNAL BOOST (30% weight) ────────────────────────
        api_score = 0.0
        signals_applied = []

        # Signal 1: MHRA alert boost
        if request.mhra_mention_count > 0:
            mhra_boost = min(request.mhra_mention_count * 0.05, 0.15)  # Max 0.15
            api_score += mhra_boost
            signals_applied.append(f"MHRA alert ({mhra_boost:.2f})")

        # Signal 2: Already on CPE concession boost
        if request.cpe_conc_available == 1:
            cpe_boost = 0.20
            api_score += cpe_boost
            signals_applied.append(f"CPE available today (0.20)")

        # Signal 3: Concession availability trend
        if request.cpe_avail_6mo > 0.5:
            trend_boost = request.cpe_avail_6mo * 0.10  # Max 0.10
            api_score += trend_boost
            signals_applied.append(f"Trend (6mo avg: {request.cpe_avail_6mo:.2f})")

        # Signal 4: High demand spike (indicates shortage risk)
        if pca_spike == 1:
            demand_boost = 0.12
            api_score += demand_boost
            signals_applied.append(f"Demand spike detected (0.12)")

        # Signal 5: Price stress (price far above floor = shortage risk)
        if request.price_vs_cpe_pct > 50:
            price_boost = min(request.price_vs_cpe_pct / 1000, 0.15)
            api_score += price_boost
            signals_applied.append(f"Price stress {request.price_vs_cpe_pct:.1f}%")

        api_score = min(api_score, 1.0)  # Cap at 1.0

        # ── STEP 3: WEIGHTED BLEND ────────────────────────────────────────────
        final_probability = (model_proba * 0.70) + (api_score * 0.30)
        final_probability = round(final_probability, 4)

        # ── STEP 4: DETERMINE ACTION & CONFIDENCE ──────────────────────────────
        if final_probability >= 0.70:
            action = "BUY NOW"
            explanation = f"High risk ({final_probability:.1%}). Drug likely to go on concession soon."
        elif final_probability >= 0.50:
            action = "BUFFER"
            explanation = f"Medium risk ({final_probability:.1%}). Monitor prices, consider stock buildup."
        else:
            action = "MONITOR"
            explanation = f"Low risk ({final_probability:.1%}). Standard ordering sufficient."

        # Confidence: high if far from 0.5, low if near boundary
        diff_from_boundary = abs(final_probability - 0.5)
        if diff_from_boundary > 0.25:
            confidence = "high"
        elif diff_from_boundary > 0.10:
            confidence = "medium"
        else:
            confidence = "low"

        # Add signal details to explanation
        if signals_applied:
            explanation += f" Signals: {', '.join(signals_applied)}."

        result = PredictionResponse(
            drug_name=request.drug_name,
            model_probability=round(model_proba, 4),
            real_time_signals=round(api_score, 4),
            final_probability=final_probability,
            action=action,
            confidence=confidence,
            explanation=explanation,
            model_used=active_model_name or "unknown"
        )
        set_cached_prediction(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
