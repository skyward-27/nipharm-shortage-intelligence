"""
NPT Stock Intelligence — Claude AI Analyst Agent
Answers buying questions, validates orders, sends bi-weekly reports.

Usage:
    python agent.py                    # interactive chat
    python agent.py --report           # generate + email bi-weekly report
    python agent.py --validate order.csv  # validate a CSV order file

Setup:
    pip install anthropic pandas python-dotenv
    export ANTHROPIC_API_KEY=your_key_here
"""

import os
import sys
import json
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PREDICTIONS_FILE = BASE_DIR / "data/model/panel_predictions.csv"
CONCESSIONS_FILE = BASE_DIR / "data/concessions/cpe_current_month.csv"
MODEL = "claude-haiku-4-5"   # fast + cheap for POC; swap to claude-sonnet-4-6 for richer analysis

# ── Load data once ─────────────────────────────────────────────────────────────
def load_predictions() -> pd.DataFrame:
    df = pd.read_csv(PREDICTIONS_FILE)
    df["shortage_probability"] = df["shortage_probability"].round(4)
    return df

def load_concessions() -> pd.DataFrame:
    if CONCESSIONS_FILE.exists():
        return pd.read_csv(CONCESSIONS_FILE)
    return pd.DataFrame()

# ── Tool functions (called by Claude) ─────────────────────────────────────────

def get_top_risk_drugs(n: int = 20, min_prob: float = 0.7) -> str:
    """Return top N high-risk drugs as JSON for Claude to analyse."""
    df = load_predictions()
    top = (
        df[df["shortage_probability"] >= min_prob]
        .sort_values("shortage_probability", ascending=False)
        .head(n)
    )
    cols = ["drug_name", "shortage_probability", "on_concession",
            "concession_streak", "floor_proximity", "pharmacy_over_tariff"]
    available = [c for c in cols if c in top.columns]
    records = top[available].to_dict(orient="records")
    return json.dumps(records, default=str)


def get_drug_details(drug_name: str) -> str:
    """Return full prediction details for a specific drug (fuzzy match)."""
    df = load_predictions()
    mask = df["drug_name"].str.lower().str.contains(drug_name.lower(), na=False)
    matches = df[mask]
    if matches.empty:
        return json.dumps({"error": f"No drug found matching '{drug_name}'"})
    best = matches.sort_values("shortage_probability", ascending=False).head(3)
    return best.to_json(orient="records", default_handler=str)


def validate_order(drug_names: list) -> str:
    """Cross-validate a list of drug names against model predictions."""
    df = load_predictions()
    results = []
    for drug in drug_names:
        keywords = drug.lower().split()[:2]
        mask = df["drug_name"].str.lower().str.contains(keywords[0], na=False)
        if len(keywords) > 1:
            mask2 = df["drug_name"].str.lower().str.contains(
                keywords[1].replace("mg", "").strip(), na=False)
            mask = mask & mask2
        matches = df[mask]
        if matches.empty:
            mask = df["drug_name"].str.lower().str.contains(keywords[0], na=False)
            matches = df[mask]
        if not matches.empty:
            row = matches.sort_values("shortage_probability", ascending=False).iloc[0]
            results.append({
                "ordered": drug,
                "matched": row["drug_name"],
                "risk_pct": round(row["shortage_probability"] * 100, 1),
                "on_concession": bool(row.get("on_concession", 0)),
                "streak_months": int(row.get("concession_streak", 0)),
                "over_tariff": bool(row.get("pharmacy_over_tariff", 0)),
                "floor_proximity": round(float(row.get("floor_proximity", 1)), 3),
            })
        else:
            results.append({"ordered": drug, "matched": None, "risk_pct": None})
    return json.dumps(results)


def get_market_summary() -> str:
    """Return current market stress signals."""
    signals_file = BASE_DIR / "data/market_signals/yfinance_monthly.csv"
    boe_file = BASE_DIR / "data/market_signals/boe_inflation.csv"
    out = {}
    if signals_file.exists():
        s = pd.read_csv(signals_file).tail(1)
        if not s.empty:
            out["brent_crude_price"] = s.get("brent_close", [None]).iloc[0]
            out["brent_mom_pct"] = s.get("brent_mom_pct", [None]).iloc[0]
    if boe_file.exists():
        b = pd.read_csv(boe_file).tail(1)
        if not b.empty:
            out["boe_rate"] = b.get("rate", [None]).iloc[0]
    return json.dumps(out, default=str)


def get_portfolio_summary() -> str:
    """High-level stats: how many drugs scored, how many high risk, on concession."""
    df = load_predictions()
    summary = {
        "total_drugs_scored": len(df),
        "high_risk_gte70pct": int((df["shortage_probability"] >= 0.7).sum()),
        "critical_risk_gte90pct": int((df["shortage_probability"] >= 0.9).sum()),
        "on_concession_now": int(df.get("on_concession", pd.Series([0])).sum()),
        "paying_over_tariff": int(df.get("pharmacy_over_tariff", pd.Series([0])).sum()),
        "model_version": "v5",
        "model_roc_auc": 0.998,
        "data_date": "March 2026",
    }
    return json.dumps(summary)


# ── Tool definitions for Claude ────────────────────────────────────────────────
TOOLS = [
    {
        "name": "get_top_risk_drugs",
        "description": (
            "Get the top N drugs most likely to go on price concession next month, "
            "ranked by shortage probability. Use this when asked 'what should we buy' "
            "or 'what are the highest risk drugs'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number of drugs to return (default 20, max 50)", "default": 20},
                "min_prob": {"type": "number", "description": "Minimum shortage probability 0-1 (default 0.7)", "default": 0.7},
            },
            "required": [],
        },
    },
    {
        "name": "get_drug_details",
        "description": (
            "Get full prediction details for a specific drug. "
            "Use when asked about a specific drug name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "Drug name or partial name to search for"},
            },
            "required": ["drug_name"],
        },
    },
    {
        "name": "validate_order",
        "description": (
            "Cross-validate a list of ordered drugs against the shortage model. "
            "Returns risk scores for each drug in the order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of drug names from the order",
                },
            },
            "required": ["drug_names"],
        },
    },
    {
        "name": "get_market_summary",
        "description": "Get current macro market signals: Brent crude price, GBP stress, BoE rate.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_portfolio_summary",
        "description": "Get high-level portfolio stats: total drugs scored, how many are high risk, on concession.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

# ── Tool executor ──────────────────────────────────────────────────────────────
def execute_tool(name: str, inputs: dict) -> str:
    if name == "get_top_risk_drugs":
        return get_top_risk_drugs(inputs.get("n", 20), inputs.get("min_prob", 0.7))
    elif name == "get_drug_details":
        return get_drug_details(inputs["drug_name"])
    elif name == "validate_order":
        return validate_order(inputs["drug_names"])
    elif name == "get_market_summary":
        return get_market_summary()
    elif name == "get_portfolio_summary":
        return get_portfolio_summary()
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the NPT Stock Intelligence Analyst — an AI assistant built for NPT's buying team.

Your job is to help the buying team make smarter purchasing decisions for generic pharmaceuticals by:
- Identifying which drugs are most likely to go on NHS price concession next month
- Validating purchase orders against shortage risk predictions
- Flagging drugs where NPT is paying above tariff on low-risk items
- Summarising market signals (Brent crude, FX stress, BoE rate) that affect drug costs

The model behind you is a Random Forest trained on 44,363 drug-month rows with ROC-AUC 0.998.
A drug with shortage_probability >= 0.9 is CRITICAL — recommend buying additional stock immediately.
A drug with shortage_probability >= 0.7 is HIGH RISK — recommend buying more than usual.
A drug already on concession with a long streak is likely to stay on concession — keep stocking.

Always be concise and actionable. Give clear BUY / WATCH / NORMAL recommendations.
When validating orders, highlight anything that looks wrong (paying over tariff on low-risk drugs,
not buying enough of high-risk drugs).

Format your responses clearly with drug names, percentages, and recommendations.
"""

# ── Agent loop ─────────────────────────────────────────────────────────────────
def run_agent(user_message: str, conversation_history: list) -> tuple[str, list]:
    """Run one turn of the agent. Returns (response_text, updated_history)."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    conversation_history.append({"role": "user", "content": user_message})
    messages = conversation_history.copy()

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # If Claude wants to call tools
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # Final response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            conversation_history.append({"role": "assistant", "content": final_text})
            return final_text, conversation_history


# ── Bi-weekly report generator ─────────────────────────────────────────────────
def generate_report() -> str:
    """Generate the bi-weekly buying report text."""
    print("Generating bi-weekly report...")
    report_prompt = (
        f"Generate a bi-weekly NPT Stock Intelligence Report for the buying team. "
        f"Date: {datetime.now().strftime('%d %B %Y')}.\n\n"
        "The report should include:\n"
        "1. Portfolio summary (total drugs scored, how many are high risk)\n"
        "2. Top 10 CRITICAL/HIGH risk drugs to prioritise this week with buying recommendations\n"
        "3. Any drugs currently on concession that need restocking\n"
        "4. Market signals summary (Brent crude, FX, BoE)\n"
        "5. Any drugs where we are paying over tariff on low-risk items (waste to fix)\n\n"
        "Keep it concise and actionable. Format with clear sections and bullet points."
    )
    text, _ = run_agent(report_prompt, [])
    return text


def send_email_report(report_text: str, recipients: list[str]):
    """Send the report via Gmail SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")  # Gmail App Password (not your main password)

    if not gmail_user or not gmail_pass:
        print("⚠️  Set GMAIL_USER and GMAIL_APP_PASSWORD env vars to send emails.")
        print("\n--- REPORT (printed instead) ---\n")
        print(report_text)
        return

    subject = f"NPT Stock Intelligence — Bi-Weekly Report {datetime.now().strftime('%d %b %Y')}"
    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
    <div style="background: #1f3864; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="margin:0">📊 NPT Stock Intelligence Report</h2>
        <p style="margin:4px 0; opacity:0.8">{datetime.now().strftime('%d %B %Y')} · Model v5 · ROC-AUC 0.998</p>
    </div>
    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; white-space: pre-wrap; font-size: 14px; line-height: 1.6;">
{report_text}
    </div>
    <p style="font-size: 11px; color: #999; margin-top: 10px;">
        NPT Stock Intelligence Unit · Automated report generated by Claude AI
    </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, recipients, msg.as_string())

    print(f"✅ Report sent to {', '.join(recipients)}")


# ── Interactive chat ───────────────────────────────────────────────────────────
def interactive_chat():
    print("\n" + "="*60)
    print("  NPT Stock Intelligence — AI Analyst")
    print("  Model: Claude · Data: March 2026 · v5 (ROC-AUC 0.998)")
    print("="*60)
    print("\nAsk me anything about drug shortage risk or buying decisions.")
    print("Examples:")
    print("  • What should we buy this week?")
    print("  • Is Omeprazole 20mg high risk?")
    print("  • Validate this order: Amoxicillin, Metformin, Sertraline")
    print("  • What are the top 5 critical drugs right now?")
    print("\nType 'quit' to exit.\n")

    history = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        print("\nAnalyst: ", end="", flush=True)
        response, history = run_agent(user_input, history)
        print(response)
        print()


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NPT Stock Intelligence AI Analyst")
    parser.add_argument("--report", action="store_true", help="Generate and email bi-weekly report")
    parser.add_argument("--email", nargs="+", help="Email recipients for report")
    parser.add_argument("--validate", type=str, help="Path to order CSV to validate")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Set ANTHROPIC_API_KEY environment variable first:")
        print("   export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    if args.report:
        report = generate_report()
        recipients = args.email or ["lowwood@nipharm.co.uk"]
        send_email_report(report, recipients)

    elif args.validate:
        order_df = pd.read_csv(args.validate)
        drug_col = next((c for c in order_df.columns if "drug" in c.lower() or "desc" in c.lower()), order_df.columns[0])
        drug_names = order_df[drug_col].dropna().tolist()
        prompt = f"Validate this order of {len(drug_names)} drugs: {', '.join(drug_names[:20])}"
        response, _ = run_agent(prompt, [])
        print(response)

    else:
        interactive_chat()
