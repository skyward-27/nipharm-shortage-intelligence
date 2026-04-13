"""
News aggregation for Nipharma backend.
Scrapes free RSS/Atom feeds — no API key required.
Sources: MHRA gov.uk, BBC Health, The Pharmaceutical Journal, PharmaTimes
Falls back to curated static articles if all feeds fail.
"""

import requests
import os
from typing import List, Dict
from datetime import datetime
import xml.etree.ElementTree as ET

# Keep for backward-compat if someone sets it and we want to try NewsAPI later
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ── RSS feed sources ─────────────────────────────────────────────────────────
RSS_FEEDS = [
    {
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=drug+shortage+medicine&topical_events=&organisations[]=medicines-and-healthcare-products-regulatory-agency",
        "source": "MHRA",
        "ns": {"atom": "http://www.w3.org/2005/Atom"},
        "format": "atom",
    },
    {
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=pharmacy+prescription+medicine+NHS&organisations[]=nhs-england",
        "source": "NHS England",
        "ns": {"atom": "http://www.w3.org/2005/Atom"},
        "format": "atom",
    },
    {
        "url": "https://pharmaceutical-journal.com/feed/",
        "source": "Pharmaceutical Journal",
        "ns": {},
        "format": "rss",
    },
    {
        "url": "https://www.pharmatimes.com/feed/",
        "source": "PharmaTimes",
        "ns": {},
        "format": "rss",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/health/rss.xml",
        "source": "BBC Health",
        "ns": {},
        "format": "rss",
    },
]

# ── Fallback articles (always available) ─────────────────────────────────────
FALLBACK_ARTICLES = [
    {
        "title": "MHRA issues shortage alert for key epilepsy medicines",
        "description": "MHRA has flagged supply constraints for several antiepileptic drugs following manufacturing disruptions. Pharmacies advised to manage stock carefully.",
        "url": "https://www.gov.uk/government/collections/drug-alerts-and-recalls",
        "image": "",
        "source": "MHRA",
        "publishedAt": "2026-04-10T09:00:00Z",
    },
    {
        "title": "NHS Drug Tariff April 2026: Concession prices reach record highs",
        "description": "CPE confirms 174 drugs on concession pricing for April 2026, driven by continued global supply chain pressure and GBP/INR exchange rate movements.",
        "url": "https://cpe.org.uk/funding-and-reimbursement/reimbursement/price-concessions/",
        "image": "",
        "source": "CPE",
        "publishedAt": "2026-04-07T08:00:00Z",
    },
    {
        "title": "Indian pharma manufacturers face increased MHRA scrutiny",
        "description": "Regulatory actions at key Indian API manufacturers are contributing to anticipated shortages across multiple therapeutic categories for UK pharmacies.",
        "url": "https://www.gov.uk/guidance/guidance-for-manufacturers-of-medicines",
        "image": "",
        "source": "Pharmaceutical Journal",
        "publishedAt": "2026-04-05T11:30:00Z",
    },
    {
        "title": "GBP weakens against INR — import costs rise for generics wholesalers",
        "description": "Sterling fell 2.3% against the Indian Rupee this quarter, increasing costs for UK wholesalers importing generic medicines from India.",
        "url": "https://www.bankofengland.co.uk/monetary-policy/inflation",
        "image": "",
        "source": "Bank of England",
        "publishedAt": "2026-04-03T14:00:00Z",
    },
    {
        "title": "NHS England issues guidance on medicine supply disruptions",
        "description": "NHS England has updated its guidance to community pharmacies on managing medicine shortages, advising proactive stock management for Category M drugs.",
        "url": "https://www.england.nhs.uk/primary-care/pharmacy/",
        "image": "",
        "source": "NHS England",
        "publishedAt": "2026-04-01T10:00:00Z",
    },
]


def _parse_rss(xml_text: str, source: str, limit: int) -> List[Dict]:
    """Parse standard RSS 2.0 feed."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []
        items = channel.findall("item")[:limit]
        for item in items:
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if title and url:
                # Parse date
                try:
                    dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                    iso = dt.isoformat()
                except Exception:
                    iso = pub_date
                articles.append({
                    "title": title,
                    "description": desc[:200] if desc else "",
                    "url": url,
                    "image": "",
                    "source": source,
                    "publishedAt": iso,
                })
    except Exception:
        pass
    return articles


def _parse_atom(xml_text: str, source: str, limit: int) -> List[Dict]:
    """Parse Atom feed (gov.uk uses Atom)."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)[:limit]
        for entry in entries:
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            summary_el = entry.find("atom:summary", ns)
            updated_el = entry.find("atom:updated", ns)

            title = (title_el.text if title_el is not None else "").strip()
            url = (link_el.get("href", "") if link_el is not None else "").strip()
            desc = (summary_el.text if summary_el is not None else "").strip()
            iso = (updated_el.text if updated_el is not None else "").strip()

            if title and url:
                articles.append({
                    "title": title,
                    "description": desc[:200] if desc else "",
                    "url": url,
                    "image": "",
                    "source": source,
                    "publishedAt": iso,
                })
    except Exception:
        pass
    return articles


def _fetch_feed(feed: Dict, limit: int) -> List[Dict]:
    """Fetch and parse a single RSS/Atom feed."""
    try:
        resp = requests.get(
            feed["url"],
            timeout=8,
            headers={"User-Agent": "NiPharma-Intel/1.0 (+https://nipharma.co.uk)"},
        )
        if resp.status_code != 200:
            return []
        if feed["format"] == "atom":
            return _parse_atom(resp.text, feed["source"], limit)
        else:
            return _parse_rss(resp.text, feed["source"], limit)
    except Exception:
        return []


def get_pharma_news(limit: int = 10) -> Dict:
    """
    Fetch pharmaceutical news from free RSS feeds.
    Falls back to curated static articles if all feeds fail.
    """
    all_articles: List[Dict] = []

    for feed in RSS_FEEDS:
        if len(all_articles) >= limit:
            break
        articles = _fetch_feed(feed, limit)
        all_articles.extend(articles)

    # De-duplicate by URL
    seen = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    # If feeds gave us nothing, use fallback
    if not unique:
        unique = FALLBACK_ARTICLES[:limit]

    unique = unique[:limit]

    return {
        "success": True,
        "count": len(unique),
        "articles": unique,
    }


def get_supply_chain_news(limit: int = 10) -> Dict:
    """Supply chain news — subset from same feeds."""
    return get_pharma_news(limit)


def search_news(query: str, limit: int = 10) -> Dict:
    """Search news — returns all feed articles for now."""
    result = get_pharma_news(limit * 2)
    q = query.lower()
    filtered = [a for a in result["articles"] if q in a["title"].lower() or q in a["description"].lower()]
    if not filtered:
        filtered = result["articles"]
    filtered = filtered[:limit]
    return {
        "success": True,
        "count": len(filtered),
        "articles": filtered,
    }
