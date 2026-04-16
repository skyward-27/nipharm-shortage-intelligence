"""
Data Explorer — DuckDB in-process SQL + Groq NL→SQL
Allows plain English or direct SQL queries against historical drug data.
"""

import os
import re
import json
import requests
import pandas as pd
from typing import Optional

# ── DuckDB setup ─────────────────────────────────────────────────────────────
_conn = None

def _find(filename: str) -> Optional[str]:
    for p in [f"./model/{filename}", f"/app/model/{filename}", f"../scrapers/data/model/{filename}"]:
        if os.path.exists(p):
            return p
    return None

def get_conn():
    global _conn
    if _conn is not None:
        return _conn
    try:
        import duckdb
        _conn = duckdb.connect(database=":memory:")

        # Load available tables
        tables_loaded = []
        table_map = {
            "concessions": "drug_concessions.csv",
            "prices":      "drug_price_history.csv",
            "alerts":      "mhra_alerts.csv",
            "trends":      "concession_trends.csv",
        }
        for table, fname in table_map.items():
            path = _find(fname)
            if path:
                _conn.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{path}')")
                count = _conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                tables_loaded.append(f"{table} ({count:,} rows)")

        print(f"[Explorer] DuckDB ready. Tables: {', '.join(tables_loaded)}")
        return _conn
    except Exception as e:
        print(f"[Explorer] DuckDB init failed: {e}")
        return None


# ── Schema description for Groq prompt ───────────────────────────────────────
SCHEMA = """
You are a SQL expert for a UK pharmaceutical drug shortage intelligence platform.
The DuckDB database has these tables:

concessions(month VARCHAR, drug VARCHAR, concession_price DOUBLE)
  -- 7,742 rows. Each row = one drug on CPE concession that month.
  -- month format: 'YYYY-MM' e.g. '2022-12'
  -- drug: full drug name e.g. 'Amoxicillin 500mg capsules'

prices(drug VARCHAR, month VARCHAR, price_gbp DOUBLE)
  -- 15,122 rows. NHS Cat M tariff price per drug per month.
  -- month format: 'YYYY-MM'

alerts(title VARCHAR, date VARCHAR, description VARCHAR, url VARCHAR, source VARCHAR, published_at VARCHAR)
  -- 3,372 rows. MHRA shortage publications.
  -- Use LOWER(title) LIKE '%keyword%' for text search.

trends(month VARCHAR, count INTEGER)
  -- 74 rows. Total drugs on concession per month (Jan 2020 - Feb 2026).

Rules:
1. ONLY write SELECT statements. No INSERT/UPDATE/DELETE/DROP.
2. Always add LIMIT 200 if no LIMIT is specified.
3. Use LOWER(column) LIKE '%term%' for case-insensitive text search.
4. For "top N" requests, use ORDER BY ... DESC LIMIT N.
5. month columns are VARCHAR 'YYYY-MM' — use LIKE '2022%' for year filtering.
6. Return ONLY the SQL query, nothing else. No markdown, no explanation.
"""

def nl_to_sql(question: str) -> str:
    """Convert natural language question to SQL using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    examples = [
        {"role": "user",    "content": "which drugs had the most concession events?"},
        {"role": "assistant","content": "SELECT drug, COUNT(*) as events FROM concessions GROUP BY drug ORDER BY events DESC LIMIT 10"},
        {"role": "user",    "content": "show amoxicillin price history"},
        {"role": "assistant","content": "SELECT month, price_gbp FROM prices WHERE LOWER(drug) LIKE '%amoxicillin%' ORDER BY month"},
        {"role": "user",    "content": "how many drugs went on concession each year?"},
        {"role": "assistant","content": "SELECT LEFT(month, 4) as year, SUM(count) as total FROM trends GROUP BY year ORDER BY year"},
        {"role": "user",    "content": "most expensive concession prices in 2023"},
        {"role": "assistant","content": "SELECT drug, month, concession_price FROM concessions WHERE month LIKE '2023%' ORDER BY concession_price DESC LIMIT 20"},
        {"role": "user",    "content": "MHRA alerts about amoxicillin"},
        {"role": "assistant","content": "SELECT title, date, description FROM alerts WHERE LOWER(title) LIKE '%amoxicillin%' OR LOWER(description) LIKE '%amoxicillin%' ORDER BY date DESC LIMIT 20"},
    ]

    messages = [{"role": "system", "content": SCHEMA}] + examples + [{"role": "user", "content": question}]

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 300, "temperature": 0.1},
        timeout=15,
    )
    resp.raise_for_status()
    sql = resp.json()["choices"][0]["message"]["content"].strip()
    # Strip markdown code fences if present
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"```$", "", sql).strip()
    return sql


def safe_sql(sql: str) -> str:
    """Reject mutations; inject LIMIT if missing."""
    sql = sql.strip().rstrip(";")
    upper = sql.upper()
    for bad in ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "PRAGMA"]:
        if re.search(rf"\b{bad}\b", upper):
            raise ValueError(f"Only SELECT queries are allowed (found {bad})")
    if "LIMIT" not in upper:
        sql += " LIMIT 200"
    return sql


def guess_chart_hint(columns: list, rows: list) -> str:
    """Guess whether result is best shown as bar, line, or table."""
    if len(columns) == 2:
        col0, col1 = columns[0].lower(), columns[1].lower()
        if any(t in col0 for t in ["month", "year", "date"]):
            return "line"
        if any(t in col1 for t in ["count", "total", "events", "sum", "avg", "price"]):
            return "bar"
    return "table"


def run_query(question: str = "", sql: str = "") -> dict:
    """
    Main entry point. Either:
    - question (str): plain English → NL→SQL → execute
    - sql (str): direct SQL → execute
    Returns dict with sql, columns, rows, chart_hint, row_count, explanation.
    """
    conn = get_conn()
    if conn is None:
        return {"success": False, "error": "DuckDB not available — run: pip install duckdb", "sql": "", "rows": [], "columns": []}

    generated_sql = ""
    explanation = ""

    try:
        if sql:
            # Direct SQL mode
            generated_sql = safe_sql(sql)
            explanation = "Direct SQL query"
        elif question:
            # NL mode
            raw_sql = nl_to_sql(question)
            generated_sql = safe_sql(raw_sql)
            explanation = f"Translated from: \"{question}\""
        else:
            return {"success": False, "error": "Provide either 'question' or 'sql'", "sql": "", "rows": [], "columns": []}

        result = conn.execute(generated_sql).fetchdf()
        columns = list(result.columns)
        rows = result.to_dict(orient="records")

        # Serialise numpy/pandas types
        clean_rows = []
        for row in rows:
            clean = {}
            for k, v in row.items():
                try:
                    if pd.isna(v):
                        clean[k] = None
                    elif hasattr(v, "item"):
                        clean[k] = v.item()
                    else:
                        clean[k] = v
                except Exception:
                    clean[k] = str(v)
            clean_rows.append(clean)

        chart_hint = guess_chart_hint(columns, clean_rows)

        return {
            "success": True,
            "sql": generated_sql,
            "columns": columns,
            "rows": clean_rows,
            "row_count": len(clean_rows),
            "chart_hint": chart_hint,
            "explanation": explanation,
        }

    except ValueError as e:
        return {"success": False, "error": str(e), "sql": generated_sql, "rows": [], "columns": []}
    except Exception as e:
        return {"success": False, "error": f"Query failed: {str(e)}", "sql": generated_sql, "rows": [], "columns": []}
