"""
Groq chatbot integration for Nipharma backend
Provides chat completions using Groq's Mixtral model
"""

from groq import Groq
import os
from typing import List, Dict

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def chat_with_groq(user_message: str, chat_history: List[Dict[str, str]] = None) -> str:
    """
    Send a message to Groq's Mixtral model and get a response.

    Args:
        user_message: The user's message
        chat_history: List of previous messages in format [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        The assistant's response
    """
    if chat_history is None:
        chat_history = []

    # Build messages list
    messages = chat_history + [{"role": "user", "content": user_message}]

    # Create system message for pharmaceutical domain
    system_message = {
        "role": "system",
        "content": """You are Nipharma, an expert AI assistant specializing in UK pharmaceutical supply chain intelligence,
        drug pricing trends, and market analysis. You provide insights on drug shortages, supply chain disruptions,
        medicine pricing factors, and pharmacy market trends. Be concise, data-driven, and helpful."""
    }

    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[system_message] + messages,
            temperature=0.7,
            max_tokens=512
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error communicating with Groq: {str(e)}"


def get_chat_response(user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Wrapper function that returns chat response in API format.

    Args:
        user_message: The user's message
        chat_history: Previous conversation history

    Returns:
        Dictionary with response and updated history
    """
    response = chat_with_groq(user_message, chat_history)
    return {
        "response": response,
        "role": "assistant"
    }
