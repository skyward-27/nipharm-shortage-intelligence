"""
SCRIPT 16: yfinance Market Signals
====================================
Fetches two supply-chain proxy signals via yfinance:

  1. Brent Crude Oil (BZ=F)
     Pharmaceutical packaging (plastics) and logistics costs track crude.
     Rising crude = rising cost pressure on manufacturers.

  2. Sun Pharmaceutical Industries (SUNPHARMA.NS)
     India's largest generic drug manufacturer. Stock price reflects
     sentiment about Indian pharma supply capacity — a proxy for
     GBP/INR API supply risk beyond FX rates alone.

Outputs:
  data/market_signals/brent_crude.csv
  data/market_signals/sun_pharma.csv
  data/market_signals/yfinance_monthly.csv   — monthly aggregates for panel join
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

OUT_DIR = "data/market_signals"
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_ticker(symbol: str, name: str, start: str, end: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        print("Installing yfinance...")
        os.system("pip install yfinance --quiet")
        import yfinance as yf

    print(f"Fetching {name} ({symbol})...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval="1d")
    if df.empty:
        print(f"  WARNING: No data for {symbol}")
        return pd.DataFrame()
    df = df.reset_index()[["Date", "Close", "Volume"]].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.rename(columns={"Close": "close", "Volume": "volume", "Date": "date"})
    df["symbol"] = symbol
    df["name"] = name
    print(f"  {len(df):,} daily rows ({df['date'].min()} to {df['date'].max()})")
    return df


def compute_stress_score(df: pd.DataFrame, price_col: str, window: int = 90) -> pd.DataFrame:
    """Z-score of price relative to rolling window — positive = elevated stress."""
    df = df.copy().sort_values("date")
    roll_mean = df[price_col].rolling(window, min_periods=10).mean()
    roll_std  = df[price_col].rolling(window, min_periods=10).std()
    df["stress_zscore"] = ((df[price_col] - roll_mean) / roll_std).round(3)
    df["mom_pct"] = df[price_col].pct_change(21).mul(100).round(2)  # ~1mo
    return df


def to_monthly(df: pd.DataFrame, value_col: str, prefix: str) -> pd.DataFrame:
    """Aggregate daily to monthly mean for panel join."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        **{f"{prefix}_close":      (value_col, "mean"),
           f"{prefix}_stress":     ("stress_zscore", "mean"),
           f"{prefix}_mom_pct":    ("mom_pct", "last"),}
    ).reset_index()
    return monthly


def run():
    print("=" * 60)
    print("SCRIPT 16: yfinance Market Signals")
    print("=" * 60)

    end   = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")  # 5 years

    # ── Brent Crude
    brent = fetch_ticker("BZ=F", "Brent Crude Oil", start, end)
    if not brent.empty:
        brent = compute_stress_score(brent, "close")
        brent.to_csv(f"{OUT_DIR}/brent_crude.csv", index=False)
        print(f"  Saved: {OUT_DIR}/brent_crude.csv")
        latest_brent = brent.sort_values("date").tail(1)
        print(f"  Latest: ${latest_brent['close'].values[0]:.2f}  |  stress z-score: {latest_brent['stress_zscore'].values[0]:.2f}")

    # ── Sun Pharma
    sun = fetch_ticker("SUNPHARMA.NS", "Sun Pharmaceutical Industries", start, end)
    if not sun.empty:
        sun = compute_stress_score(sun, "close")
        sun.to_csv(f"{OUT_DIR}/sun_pharma.csv", index=False)
        print(f"  Saved: {OUT_DIR}/sun_pharma.csv")
        latest_sun = sun.sort_values("date").tail(1)
        print(f"  Latest: ₹{latest_sun['close'].values[0]:.2f}  |  stress z-score: {latest_sun['stress_zscore'].values[0]:.2f}")

    # ── Monthly aggregates for panel join
    monthly_parts = []
    if not brent.empty:
        monthly_parts.append(to_monthly(brent, "close", "brent"))
    if not sun.empty:
        monthly_parts.append(to_monthly(sun, "close", "sunpharma"))

    if monthly_parts:
        from functools import reduce
        monthly = reduce(lambda a, b: a.merge(b, on="month", how="outer"), monthly_parts)
        monthly.to_csv(f"{OUT_DIR}/yfinance_monthly.csv", index=False)
        print(f"\nMonthly aggregates saved: {OUT_DIR}/yfinance_monthly.csv")
        print(f"  {len(monthly)} months")
        print(monthly.tail(5).to_string(index=False))
    else:
        print("WARNING: No data fetched — check internet connection or ticker symbols")

    print("\nDone.")


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
