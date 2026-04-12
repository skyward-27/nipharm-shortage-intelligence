"""
Groq chatbot integration - uses direct HTTP requests (no SDK)
Optionally augments responses with Tavily real-time web search context,
local CPE concession data, and MHRA shortage alerts.
"""
import requests
import os
import re
from typing import List, Dict
from datetime import datetime

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Dynamic current month (e.g. "April 2026")
current_month = datetime.now().strftime("%B %Y")

SYSTEM_PROMPT = (
    f"You are NPT Intel AI, an expert assistant specialising in UK pharmaceutical supply chain intelligence. "
    f"Today's date is {current_month}. Always refer to the current year when discussing prices and shortages. "
    "You can answer questions about:\n"
    "- Which drugs are currently on NHS England concessions and their concessionary prices\n"
    "- Top drugs at risk of shortage in the UK (e.g. Amoxicillin, Metformin, Amlodipine, Furosemide, Sertraline)\n"
    "- Supply chain disruptions originating from India (generic APIs) and China (raw materials)\n"
    "  - Key Indian manufacturers supplying the UK: Sun Pharma, Cipla, Aurobindo (AUROPHARMA), Dr Reddy's, Lupin\n"
    "  - India accounts for ~40% of UK generic drug supply; China supplies ~80% of global API raw materials\n"
    "- GBP/INR and GBP/CNY exchange rate impacts: weaker GBP vs INR raises import costs for Indian generics\n"
    "- Bulk buying opportunities and group purchasing strategies for UK independent pharmacies\n"
    "- MHRA alerts, parallel import risks, NICE guidance, and regulatory updates\n"
    "- Price trend analysis and shortage probability scoring\n"
    "- Northern Ireland context: NI pharmacies are reimbursed under HSCNI/BSO NI framework. "
    "  NI applies the same CPE England concession prices, confirmed monthly by BSO NI from DH England/CPE.\n"
    "- When asked about therapeutic alternatives, group drugs by BNF class "
    "  (e.g. ACE inhibitors, SSRIs, PPIs, beta-blockers, biguanides) and name available alternatives.\n"
    "- When asked about manufacturer count or market concentration, note that single-source drugs "
    "  (one manufacturer) carry far higher shortage risk than multi-source drugs.\n"
    "Be concise, data-driven and helpful. "
    "If local data is provided above (CPE concession or MHRA context), use it as your primary source — "
    "it is the most accurate current data available. "
    "If web search context is provided, use it to give up-to-date answers. "
    "When unsure, give your best informed estimate and flag it as such."
)

# Paths to local data files — try local dev paths then Railway deployment paths
CPE_PATHS = [
    "../scrapers/data/concessions/cpe_current_month.csv",
    "./model/cpe_current_month.csv",
    "/app/model/cpe_current_month.csv",
    # Fallback: NI concessions share same CPE prices
    "../scrapers/data/concessions/cpni_concessions.csv",
    "./model/cpni_concessions.csv",
]

MHRA_PATHS = [
    "../scrapers/data/mhra/govuk_shortage_publications.csv",
    "./model/govuk_shortage_publications.csv",
    "/app/model/govuk_shortage_publications.csv",
]

# Concession-related keywords that trigger local CSV lookup
CONCESSION_KEYWORDS = [
    "concession", "price", "how much", "cpe", "cost", "concessionary",
    "tariff", "reimburse", "reimbursement", "dispensing"
]

# Shortage / alert keywords that trigger MHRA lookup
MHRA_KEYWORDS = [
    "shortage", "alert", "mhra", "supply", "disruption", "recall",
    "unavailable", "out of stock", "discontinued", "risk"
]


def _load_cpe_data() -> "pd.DataFrame | None":
    """Load CPE concession CSV from the first available path."""
    try:
        import pandas as pd
        for path in CPE_PATHS:
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    return df
            except Exception:
                continue
    except ImportError:
        pass
    return None


def _load_mhra_data() -> "pd.DataFrame | None":
    """Load MHRA shortage publications CSV from the first available path."""
    try:
        import pandas as pd
        for path in MHRA_PATHS:
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    return df
            except Exception:
                continue
    except ImportError:
        pass
    return None


def _extract_drug_name(text: str) -> str:
    """
    Heuristic: extract a likely drug name from the user message.
    Returns a lower-case string for fuzzy matching.
    """
    # Strip common question words and punctuation
    clean = re.sub(
        r"\b(what|is|the|price|of|for|concession|cost|how|much|does|do|"
        r"current|month|on|nhs|england|northern|ireland|in|a|an|please|"
        r"tell|me|about|show|get|find|check|lookup)\b",
        " ",
        text.lower()
    )
    clean = re.sub(r"[^\w\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def lookup_cpe_concession(user_message: str) -> str:
    """
    If the user seems to be asking about concession price(s), look up the local CPE CSV.
    Returns a formatted string with the result, or empty string if nothing found.
    """
    msg_lower = user_message.lower()

    # Check if this looks like a concession/price question
    if not any(kw in msg_lower for kw in CONCESSION_KEYWORDS):
        return ""

    df = _load_cpe_data()
    if df is None:
        return ""

    # Normalise column names (different CSVs may use slightly different names)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    drug_col = next((c for c in df.columns if "drug" in c or "name" in c), None)
    price_col = next((c for c in df.columns if "pence" in c or "price" in c), None)

    if drug_col is None:
        return ""

    drug_query = _extract_drug_name(user_message)
    if not drug_query or len(drug_query) < 3:
        return ""

    # Fuzzy match: find rows where drug name contains any word from the query
    query_words = [w for w in drug_query.split() if len(w) > 3]
    if not query_words:
        return ""

    mask = df[drug_col].str.lower().str.contains("|".join(query_words), na=False)
    matches = df[mask]

    if matches.empty:
        return ""

    lines = [f"LOCAL CPE CONCESSION DATA ({current_month}):"]
    for _, row in matches.head(5).iterrows():
        drug = row[drug_col]
        if price_col and price_col in row:
            price_pence = row[price_col]
            try:
                price_gbp = float(price_pence) / 100
                lines.append(f"  - {drug}: {price_pence}p (£{price_gbp:.2f})")
            except (ValueError, TypeError):
                lines.append(f"  - {drug}: {price_pence}")
        else:
            lines.append(f"  - {drug}: (price unavailable)")

    return "\n".join(lines)


def lookup_mhra_alerts(user_message: str) -> str:
    """
    If the user mentions a drug name and shortage-related keywords, look up MHRA data.
    Returns a formatted string with matching alerts, or empty string if nothing found.
    """
    msg_lower = user_message.lower()

    # Check if this looks like a shortage/alert question
    if not any(kw in msg_lower for kw in MHRA_KEYWORDS):
        return ""

    df = _load_mhra_data()
    if df is None:
        return ""

    df.columns = [c.strip().lower() for c in df.columns]
    title_col = next((c for c in df.columns if "title" in c), None)
    desc_col = next((c for c in df.columns if "desc" in c or "summary" in c), None)
    date_col = next((c for c in df.columns if "date" in c or "published" in c), None)

    if title_col is None:
        return ""

    drug_query = _extract_drug_name(user_message)
    query_words = [w for w in drug_query.split() if len(w) > 3]
    if not query_words:
        return ""

    mask = df[title_col].str.lower().str.contains("|".join(query_words), na=False)
    matches = df[mask]

    if matches.empty:
        return ""

    lines = ["MHRA SHORTAGE ALERT DATA (from local database):"]
    for _, row in matches.head(3).iterrows():
        title = row[title_col]
        date = row[date_col] if date_col and date_col in row else "unknown date"
        desc = ""
        if desc_col and desc_col in row and isinstance(row[desc_col], str):
            desc = row[desc_col][:150]
        lines.append(f"  - [{date}] {title}")
        if desc:
            lines.append(f"    {desc}...")

    return "\n".join(lines)


def search_web_context(query: str) -> str:
    """Use Tavily to get real-time web context for pharmaceutical queries."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return ""
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": f"UK pharmacy {query} NHS {current_month}",
                "search_depth": "basic",
                "max_results": 3,
                "include_answer": True
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            context_parts = []
            if data.get("answer"):
                context_parts.append(f"Web search summary: {data['answer']}")
            for r in data.get("results", [])[:3]:
                context_parts.append(f"- {r.get('title', '')}: {r.get('content', '')[:200]}")
            return "\n".join(context_parts)
    except Exception:
        pass
    return ""


def chat_with_groq(user_message: str, chat_history: List[Dict] = None) -> str:
    if chat_history is None:
        chat_history = []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "The Groq API key is not configured on this server. "
            "Please set the GROQ_API_KEY environment variable to enable AI chat."
        )

    # ── STEP 1: Local data lookups (fast, no API cost) ──────────────────────
    local_context_parts = []

    cpe_context = lookup_cpe_concession(user_message)
    if cpe_context:
        local_context_parts.append(cpe_context)

    mhra_context = lookup_mhra_alerts(user_message)
    if mhra_context:
        local_context_parts.append(mhra_context)

    # ── STEP 2: Optionally enrich with Tavily web search ────────────────────
    web_context = search_web_context(user_message)

    # ── STEP 3: Build enriched system prompt ────────────────────────────────
    system_content = SYSTEM_PROMPT

    if local_context_parts:
        system_content += (
            "\n\nLOCAL DATABASE CONTEXT (authoritative — use this first):\n"
            + "\n\n".join(local_context_parts)
        )

    if web_context:
        system_content += (
            "\n\nREAL-TIME WEB CONTEXT (use this to give accurate current answers):\n"
            + web_context
        )

    system_message = {"role": "system", "content": system_content}
    messages = [system_message] + chat_history + [{"role": "user", "content": user_message}]

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        data = r.json()

        # Check for API-level errors returned in the response body
        if "error" in data:
            err_msg = data["error"].get("message", "Unknown API error")
            err_type = data["error"].get("type", "")
            return (
                f"The AI service returned an error ({err_type}): {err_msg}. "
                "Please try again shortly or contact support."
            )

        # Validate expected response structure
        choices = data.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            return (
                "The AI service returned an unexpected response format. "
                "Please try again or contact support."
            )

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            return "The AI returned an empty response. Please rephrase your question and try again."

        return content

    except requests.exceptions.Timeout:
        return "The request to the AI service timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "Could not connect to the AI service. Please check your internet connection and try again."
    except Exception as e:
        return (
            f"An unexpected error occurred while contacting the AI service: {str(e)}. "
            "Please try again."
        )


def get_chat_response(user_message: str, chat_history: List[Dict] = None) -> Dict:
    return {"response": chat_with_groq(user_message, chat_history), "role": "assistant"}
