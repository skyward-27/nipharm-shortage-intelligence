"""
Nipharma FastAPI Backend
Provides pharmaceutical supply chain intelligence APIs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# Import our modules
from chat import chat_with_groq, get_chat_response
from news import get_pharma_news, get_supply_chain_news, search_news

# Load environment variables
load_dotenv()

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
        "news_api_configured": bool(os.getenv("NEWS_API_KEY"))
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
    Get concession trends and market intelligence.
    Future: Load concession trends data and return analysis.
    """
    return {
        "message": "Concessions endpoint - coming soon",
        "status": "under_development"
    }


@app.get("/signals")
async def signals_endpoint():
    """
    Get market signals including GBP/INR, Brent crude, and BoE rate.
    Future: Return real-time market signals.
    """
    return {
        "message": "Market signals endpoint - coming soon",
        "signals": {
            "gbp_inr": "TBD",
            "brent_crude": "TBD",
            "boe_rate": "TBD"
        },
        "status": "under_development"
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
