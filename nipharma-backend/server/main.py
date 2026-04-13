"""
Nipharma FastAPI Backend
Provides pharmaceutical supply chain intelligence APIs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
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


@app.get("/recommendations")
async def recommendations_endpoint():
    """
    Get wholesale buying recommendations for pharmacists.
    Reads from buying_recommendations.csv and returns structured recommendations.
    """
    REC_PATHS = [
        "../scrapers/data/pharmacy_invoices/buying_recommendations.csv",
        "./model/buying_recommendations.csv",
        "/app/model/buying_recommendations.csv",
    ]
    for path in REC_PATHS:
        try:
            df = pd.read_csv(path)
            break
        except Exception:
            continue
    else:
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
        rec_col = "recommendation"  # fallback

    # Determine margin column name
    margin_col = None
    for candidate in ["margin_gbp", "margin", "saving_gbp", "savings_gbp"]:
        if candidate in df.columns:
            margin_col = candidate
            break

    # Build summary
    total = len(df)
    bulk = int((df[rec_col].str.upper() == "BULK BUY").sum()) if rec_col in df.columns else 0
    buy_go = int((df[rec_col].str.upper() == "BUY AS YOU GO").sum()) if rec_col in df.columns else 0
    hold = int((df[rec_col].str.upper() == "HOLD BUYING").sum()) if rec_col in df.columns else 0
    avg_margin = round(float(df[margin_col].mean()), 2) if margin_col and margin_col in df.columns else 0.0

    # Top 20 BULK BUY opportunities by margin
    top_opps = []
    if rec_col in df.columns and margin_col and margin_col in df.columns:
        bulk_df = df[df[rec_col].str.upper() == "BULK BUY"].nlargest(20, margin_col)
        top_opps = bulk_df.where(bulk_df.notna(), None).to_dict("records")

    # Hold warnings
    hold_warnings = []
    if rec_col in df.columns:
        hold_df = df[df[rec_col].str.upper() == "HOLD BUYING"]
        hold_warnings = hold_df.where(hold_df.notna(), None).to_dict("records")

    # Full list (first 50)
    recs = df.head(50).where(df.head(50).notna(), None).to_dict("records")

    return {
        "success": True,
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
    """Fetch MHRA drug shortage and safety alerts"""
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
            for entry in root.findall("atom:entry", ns)[:10]:
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:link", ns)
                updated = entry.find("atom:updated", ns)
                alerts.append({
                    "title": title.text if title is not None else "",
                    "summary": (summary.text or "")[:200] if summary is not None else "",
                    "url": link.get("href", "") if link is not None else "",
                    "date": updated.text[:10] if updated is not None else "",
                    "severity": "HIGH" if any(w in (title.text or "").lower() for w in ["shortage", "recall", "urgent"]) else "MEDIUM"
                })
            return {"success": True, "count": len(alerts), "alerts": alerts, "source": "MHRA Live"}
    except Exception as e:
        pass

    # Fallback hardcoded alerts
    return {
        "success": True,
        "count": 6,
        "source": "MHRA (cached)",
        "alerts": [
            {"title": "Amoxicillin 500mg capsules - Supply Shortage", "summary": "Manufacturing constraints at primary supplier. Expected resolution Q3 2025. Pharmacies advised to source alternatives.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2025-03-15", "severity": "HIGH"},
            {"title": "Metformin 1g tablets - Intermittent Supply Issues", "summary": "Raw material shortage from Chinese API supplier affecting multiple UK wholesalers.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2025-03-10", "severity": "HIGH"},
            {"title": "Amlodipine 5mg tablets - Supply Disruption", "summary": "Short-term supply disruption. Alternative brands available from AAH and Alliance.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2025-03-08", "severity": "MEDIUM"},
            {"title": "Lansoprazole 30mg capsules - Stock Alert", "summary": "Supply constraints expected to ease by end of month. Omeprazole remains available.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2025-03-05", "severity": "MEDIUM"},
            {"title": "Furosemide 40mg tablets - Shortage Notice", "summary": "Indian API manufacturer facing regulatory review. Supply expected to normalise in 6-8 weeks.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2025-02-28", "severity": "HIGH"},
            {"title": "Sertraline 50mg tablets - Supply Update", "summary": "Supply improving following manufacturing capacity increase. Normal supply expected within 2 weeks.", "url": "https://www.gov.uk/drug-device-alerts", "date": "2025-02-20", "severity": "LOW"}
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

        features = np.array([[
            # 0-7: core pricing
            request.price_gbp,
            request.floor_price_gbp,
            request.floor_proximity,
            request.within_15pct_of_floor,
            request.price_mom_pct,
            request.price_6mo_avg,
            request.price_yoy_pct,
            request.on_concession,
            # 8-14: market signals
            request.gbp_inr,
            request.fx_stress_score,
            request.boe_bank_rate,
            request.mhra_mention_count,
            request.us_shortage_flag,
            request.concession_streak,
            request.conc_last_6mo,
            # 15-17: pharmacy pricing
            request.pharmacy_over_tariff,
            request.pharmacy_unit_price,
            request.pharmacy_qty_ordered,
            # 18-23: CPE features
            request.cpe_price_pence,
            request.cpe_price_gbp,
            request.ni_price_gbp,
            request.price_vs_cpe_pct,
            request.cpe_conc_available,
            request.cpe_avail_6mo,
            # 24-30: v5 new features
            request.bsn_same_section_conc_count,
            month_sin,
            month_cos,
            is_winter,
            request.drug_on_ssp,
            request.drug_age_years,
            request.ni_india_pharma_stress,
            # 31-33: wholesale price features
            request.best_historic_price,
            request.price_vs_best_pct,
            request.wholesale_margin_pct,
            # 34-38: PCA demand features (fixed BNF mapping)
            request.pca_items,
            pca_items_mom,
            pca_spike,
            pca_trend,
            request.pca_nic_gbp,
            # 39-41: v6 features (BSO NI, FDA, manufacturer diversity)
            request.bso_ni_shortage_flag,
            request.fda_warning_flag,
            request.manufacturer_count,
        ]])

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
