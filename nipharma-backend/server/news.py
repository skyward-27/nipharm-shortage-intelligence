"""
News API integration for Nipharma backend
Fetches pharmaceutical and supply chain news articles
"""

import requests
import os
from typing import List, Dict
from datetime import datetime

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"


def get_pharma_news(limit: int = 10) -> List[Dict]:
    """
    Fetch pharmaceutical industry news from News API.

    Args:
        limit: Maximum number of articles to return

    Returns:
        List of news articles with title, description, url, image, source, and publishedAt
    """
    if not NEWS_API_KEY:
        return {
            "error": "NEWS_API_KEY not configured",
            "articles": []
        }

    try:
        response = requests.get(NEWS_API_URL, params={
            "q": "pharmaceutical shortage OR drug supply OR medicine price UK OR pharmacy UK",
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": limit,
            "apiKey": NEWS_API_KEY
        }, timeout=10)

        if response.status_code != 200:
            return {
                "error": f"News API returned status {response.status_code}",
                "articles": []
            }

        data = response.json()
        articles = data.get("articles", [])

        # Format articles
        formatted_articles = [
            {
                "title": article.get("title", "No title"),
                "description": article.get("description", "No description"),
                "url": article.get("url", ""),
                "image": article.get("urlToImage", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "publishedAt": article.get("publishedAt", ""),
                "author": article.get("author", "Unknown")
            }
            for article in articles
            if article.get("title") and article.get("url")
        ]

        return {
            "success": True,
            "count": len(formatted_articles),
            "articles": formatted_articles
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to fetch news: {str(e)}",
            "articles": []
        }


def get_supply_chain_news(limit: int = 10) -> List[Dict]:
    """
    Fetch supply chain and logistics news.

    Args:
        limit: Maximum number of articles to return

    Returns:
        List of supply chain news articles
    """
    if not NEWS_API_KEY:
        return {
            "error": "NEWS_API_KEY not configured",
            "articles": []
        }

    try:
        response = requests.get(NEWS_API_URL, params={
            "q": "supply chain UK OR logistics disruption OR freight costs",
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": limit,
            "apiKey": NEWS_API_KEY
        }, timeout=10)

        if response.status_code != 200:
            return {
                "error": f"News API returned status {response.status_code}",
                "articles": []
            }

        data = response.json()
        articles = data.get("articles", [])

        # Format articles
        formatted_articles = [
            {
                "title": article.get("title", "No title"),
                "description": article.get("description", "No description"),
                "url": article.get("url", ""),
                "image": article.get("urlToImage", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "publishedAt": article.get("publishedAt", ""),
                "author": article.get("author", "Unknown")
            }
            for article in articles
            if article.get("title") and article.get("url")
        ]

        return {
            "success": True,
            "count": len(formatted_articles),
            "articles": formatted_articles
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to fetch supply chain news: {str(e)}",
            "articles": []
        }


def search_news(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for news articles with custom query.

    Args:
        query: Search query string
        limit: Maximum number of articles to return

    Returns:
        List of search results
    """
    if not NEWS_API_KEY:
        return {
            "error": "NEWS_API_KEY not configured",
            "articles": []
        }

    try:
        response = requests.get(NEWS_API_URL, params={
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": limit,
            "apiKey": NEWS_API_KEY
        }, timeout=10)

        if response.status_code != 200:
            return {
                "error": f"News API returned status {response.status_code}",
                "articles": []
            }

        data = response.json()
        articles = data.get("articles", [])

        # Format articles
        formatted_articles = [
            {
                "title": article.get("title", "No title"),
                "description": article.get("description", "No description"),
                "url": article.get("url", ""),
                "image": article.get("urlToImage", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "publishedAt": article.get("publishedAt", ""),
                "author": article.get("author", "Unknown")
            }
            for article in articles
            if article.get("title") and article.get("url")
        ]

        return {
            "success": True,
            "count": len(formatted_articles),
            "articles": formatted_articles
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to search news: {str(e)}",
            "articles": []
        }
