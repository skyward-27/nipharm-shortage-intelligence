"""
Groq chatbot integration for Nipharma backend
Provides chat completions using Groq's Mixtral model
"""

from groq import Groq
import os
from typing import List, Dict

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are Nipharma, an expert AI assistant specializing in UK pharmaceutical supply chain intelligence,
    drug pricing trends, and market analysis. You provide insights on drug shortages, supply chain disruptions,
    medicine pricing factors, and pharmacy market trends. Be concise, data-driven, and helpful."""
}


def chat_with_groq(user_message: str, chat_history: List[Dict[str, str]] = None) -> str:
    """Send a message to Groq's Mixtral model and get a response."""
    if chat_history is None:
        chat_history = []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Groq API key not configured. Please set GROQ_API_KEY environment variable."

    try:
        client = Groq(api_key=api_key)
        messages = [SYSTEM_MESSAGE] + chat_history + [{"role": "user", "content": user_message}]
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=messages,
            temperature=0.7,
            max_tokens=512
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error communicating with Groq: {str(e)}"


def get_chat_response(user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, str]:
    """Wrapper function that returns chat response in API format."""
    response = chat_with_groq(user_message, chat_history)
    return {
        "response": response,
        "role": "assistant"
    }
