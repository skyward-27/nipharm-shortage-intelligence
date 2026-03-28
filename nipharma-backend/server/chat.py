"""
Groq chatbot integration for Nipharma backend
Uses direct HTTP requests (no groq SDK) to avoid pydantic v2 dependency
"""

import requests
import os
from typing import List, Dict

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are Nipharma, an expert AI assistant specializing in UK pharmaceutical supply chain intelligence,
    drug pricing trends, and market analysis. You provide insights on drug shortages, supply chain disruptions,
    medicine pricing factors, and pharmacy market trends. Be concise, data-driven, and helpful."""
}


def chat_with_groq(user_message: str, chat_history: List[Dict[str, str]] = None) -> str:
    """
    Send a message to Groq's API via direct HTTP and get a response.
    """
    if chat_history is None:
        chat_history = []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Groq API key not configured. Please set GROQ_API_KEY environment variable."

    messages = [SYSTEM_MESSAGE] + chat_history + [{"role": "user", "content": user_message}]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512
    }

    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error communicating with Groq: {str(e)}"


def get_chat_response(user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Wrapper function that returns chat response in API format.
    """
    response = chat_with_groq(user_message, chat_history)
    return {
        "response": response,
        "role": "assistant"
    }
