"""
Groq chatbot integration - uses direct HTTP requests (no SDK)
Optionally augments responses with Tavily real-time web search context.
"""
import requests
import os
from typing import List, Dict

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are NPT Intel AI, an expert assistant specialising in UK pharmaceutical supply chain intelligence. "
    "Today's date is March 2026. Always refer to 2026 as the current year. "
    "You can answer questions about:\n"
    "- Which drugs are currently on NHS England concessions and their concessionary prices (2026)\n"
    "- Top drugs at risk of shortage in the UK (e.g. Amoxicillin, Metformin, Amlodipine)\n"
    "- Supply chain disruptions originating from India (generic APIs) and China (raw materials)\n"
    "- GBP/INR and GBP/CNY exchange rate impacts on import costs\n"
    "- Bulk buying opportunities and group purchasing strategies for UK independent pharmacies\n"
    "- MHRA alerts, parallel import risks, and regulatory updates\n"
    "- Price trend analysis and shortage probability scoring\n"
    "Be concise, data-driven and helpful. Always use 2026 as the reference year. "
    "If web search context is provided above, use it to give the most up-to-date accurate answer. "
    "When unsure, give your best informed estimate and flag it as such."
)


def search_web_context(query: str) -> str:
    """Use Tavily to get real-time web context for pharmaceutical queries"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return ""
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": f"UK pharmacy {query} NHS 2026",
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
    except:
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

    # Optionally enrich the system prompt with real-time Tavily web context
    web_context = search_web_context(user_message)
    if web_context:
        system_content = SYSTEM_PROMPT + f"\n\nREAL-TIME WEB CONTEXT (use this to give accurate current answers):\n{web_context}"
    else:
        system_content = SYSTEM_PROMPT

    system_message = {"role": "system", "content": system_content}

    messages = [system_message] + chat_history + [{"role": "user", "content": user_message}]

    try:
        r = requests.post(
            GROQ_API_URL,
            json={
                "model": "llama-3.1-8b-instant",
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
