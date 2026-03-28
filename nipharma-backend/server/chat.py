"""
Groq chatbot integration - uses direct HTTP requests (no SDK)
"""
import requests
import os
from typing import List, Dict

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are Nipharma AI, an expert assistant specialising in UK pharmaceutical supply chain intelligence. "
        "You can answer questions about:\n"
        "- Which drugs are currently on NHS England concessions and their concessionary prices\n"
        "- Top drugs at risk of shortage in the UK (e.g. Amoxicillin, Metformin, Amlodipine)\n"
        "- Supply chain disruptions originating from India (generic APIs) and China (raw materials)\n"
        "- GBP/INR and GBP/CNY exchange rate impacts on import costs\n"
        "- Bulk buying opportunities and group purchasing strategies for UK independent pharmacies\n"
        "- MHRA alerts, parallel import risks, and regulatory updates\n"
        "- Price trend analysis and shortage probability scoring\n"
        "Be concise, data-driven and helpful. When unsure, give your best informed estimate and flag it as such."
    )
}


def chat_with_groq(user_message: str, chat_history: List[Dict] = None) -> str:
    if chat_history is None:
        chat_history = []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "The Groq API key is not configured on this server. "
            "Please set the GROQ_API_KEY environment variable to enable AI chat."
        )

    messages = [SYSTEM_MESSAGE] + chat_history + [{"role": "user", "content": user_message}]

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": "llama3-8b-8192",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 512
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
