"""
Groq chatbot integration - uses direct HTTP requests (no SDK)
"""
import requests
import os
from typing import List, Dict

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_MESSAGE = {
    "role": "system",
    "content": "You are Nipharma, an expert AI assistant specializing in UK pharmaceutical supply chain intelligence, drug pricing trends, and market analysis. Be concise and helpful."
}


def chat_with_groq(user_message: str, chat_history: List[Dict] = None) -> str:
    if chat_history is None:
        chat_history = []
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Groq API key not configured."
    messages = [SYSTEM_MESSAGE] + chat_history + [{"role": "user", "content": user_message}]
    try:
        r = requests.post(
            GROQ_API_URL,
            json={"model": "mixtral-8x7b-32768", "messages": messages, "temperature": 0.7, "max_tokens": 512},
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"


def get_chat_response(user_message: str, chat_history: List[Dict] = None) -> Dict:
    return {"response": chat_with_groq(user_message, chat_history), "role": "assistant"}
