"""
SCRIPT 13: NHSBSA PCA — Monthly Rx Demand Signal
=================================================
Downloads PCA monthly CSVs from NHSBSA CKAN and aggregates to
England-wide ITEMS per generic BNF code. Adds demand features to
the panel feature store.

OpenPrescribing.net now blocks automated access (Cloudflare JS challenge).
PCA is the same underlying data, directly from NHSBSA.

Key columns used:
  GENERIC_BNF_EQUIVALENT_CODE  — BNF code for generic (joins to concessions)
  SNOMED_CODE                  — dm+d VMPP code (joins to drug tariff)
  ITEMS                        — prescription item count (demand signal)
  NIC                          — Net Ingredient Cost (value signal)
  YEAR_MONTH                   — yyyymm

Outputs:
  data/openprescribing/pca_demand_monthly.csv   — England totals per BNF per month
  data/openprescribing/pca_demand_features.csv  — demand features (MoM, spike, trend)
"""

import requests
import pandas as pd
import numpy as np
import os, re, io, time

OUT_DIR = "data/openprescribing"
os.makedirs(OUT_DIR, exist_ok=True)

BASE = "https://opendata.nhsbsa.net"
PACKAGE_ID = "prescription-cost-analysis-pca-monthly-data"

# BNF chapter prefixes to keep (generics most at risk of shortage)
KEEP_CHAPTERS = {"01","02","03","04","05","06","07","08","09","10","11","12","13"}


def get_resource_list() -> list[dict]:
    """Return list of {name, url} for all PCA monthly CSVs."""
    resp = requests.get(
        f"{BASE}/api/3/action/package_show",
        params={"id": PACKAGE_ID}, timeout=30
    )
    raw = resp.text

    # Extract resource IDs + names (response is truncated JSON, use regex)
    names = re.findall(r'"name":\s*"(PCA_\d+)"', raw)
    ids   = re.findall(r'/resource/([a-f0-9\-]{36})/download', raw)

    resources = []
    for name, rid in zip(names, ids):
        ym = name.replace("PCA_", "")
        url = f"{BASE}/dataset/358e443c-b299-4370-aed4-eca63ce3ba68/resource/{rid}/download/pca_{ym.lower()}.csv"
        resources.append({"name": name, "year_month": ym, "url": url})

    resources.sort(key=lambda x: x["year_month"])
    print(f"PCA resources found: {len(resources)}  ({resources[0]['year_month']} → {resources[-1]['year_month']})")
    return resources


def download_and_aggregate(resource: dict) -> pd.DataFrame:
    """Download one PCA month, aggregate to England totals by generic BNF."""
    try:
        r = requests.get(resource["url"], timeout=60)
        if r.status_code != 200:
            return pd.DataFrame()

        df = pd.read_csv(io.StringIO(r.text), dtype=str)
        df.columns = [c.upper() for c in df.columns]

        # Keep only generic equivalents
        required = {"GENERIC_BNF_EQUIVALENT_CODE", "ITEMS", "NIC", "SNOMED_CODE"}
        if not required.issubset(df.columns):
            return pd.DataFrame()

        # Filter to target BNF chapters
        df["chapter"] = df["GENERIC_BNF_EQUIVALENT_CODE"].str[:2]
        df = df[df["chapter"].isin(KEEP_CHAPTERS)]

        df["ITEMS"] = pd.to_numeric(df["ITEMS"], errors="coerce").fillna(0)
        df["NIC"]   = pd.to_numeric(df["NIC"],   errors="coerce").fillna(0)

        # Aggregate England-wide per generic BNF code
        agg = df.groupby(
            ["GENERIC_BNF_EQUIVALENT_CODE", "GENERIC_BNF_EQUIVALENT_NAME"],
            as_index=False
        ).agg(items=("ITEMS", "sum"), nic_gbp=("NIC", "sum"))

        agg["year_month"] = resource["year_month"]
        agg["month"] = str(pd.Period(resource["year_month"], freq="M"))

        return agg

    except Exception as e:
        print(f"    Error {resource['name']}: {e}")
        return pd.DataFrame()


def compute_demand_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per BNF code × month:
      items_mom_pct   — month-on-month items change %
      items_yoy_pct   — year-on-year items change %
      demand_spike    — MoM > +20% (sudden surge = supply pressure)
      demand_trend_6mo— 6-month linear trend slope (rising demand = risk)
      avg_items_3mo   — 3-month rolling average
    """
    df = df.sort_values(["GENERIC_BNF_EQUIVALENT_CODE", "month"])
    records = []

    for bnf_code, grp in df.groupby("GENERIC_BNF_EQUIVALENT_CODE"):
        grp = grp.reset_index(drop=True)
        items = grp["items"].values

        for i in range(len(grp)):
            p    = items[i]
            avg3 = np.mean(items[max(0, i-2):i+1])
            mom  = (p - items[i-1]) / items[i-1] * 100 if i > 0 and items[i-1] > 0 else 0.0
            yoy  = (p - items[i-12]) / items[i-12] * 100 if i >= 12 and items[i-12] > 0 else 0.0
            slope = float(np.polyfit(np.arange(6), items[max(0,i-5):i+1], 1)[0]) if i >= 5 else 0.0

            records.append({
                "bnf_code":          bnf_code,
                "bnf_name":          grp["GENERIC_BNF_EQUIVALENT_NAME"].iloc[i],
                "month":             grp["month"].iloc[i],
                "year_month":        grp["year_month"].iloc[i],
                "items":             int(p),
                "nic_gbp":           round(grp["nic_gbp"].iloc[i], 2),
                "avg_items_3mo":     round(avg3, 0),
                "items_mom_pct":     round(mom, 2),
                "items_yoy_pct":     round(yoy, 2),
                "demand_spike":      int(mom > 20),
                "demand_trend_6mo":  round(slope, 2),
            })

    return pd.DataFrame(records)


def run():
    print("=" * 65)
    print("SCRIPT 13: NHSBSA PCA — Monthly Rx Demand Signal")
    print("=" * 65)

    resources = get_resource_list()

    # Resume support: load already-downloaded months and skip them
    monthly_path = f"{OUT_DIR}/pca_demand_monthly.csv"
    already_done = set()
    existing = []
    if os.path.exists(monthly_path):
        prev = pd.read_csv(monthly_path)
        already_done = set(prev["year_month"].astype(str).unique())
        existing.append(prev)
        print(f"Resuming — {len(already_done)} months already downloaded: "
              f"{min(already_done)} → {max(already_done)}")

    all_months = list(existing)
    for i, res in enumerate(resources):
        if res["year_month"] in already_done:
            print(f"  [{i+1:02d}/{len(resources)}] {res['name']}... already done, skipping")
            continue
        print(f"  [{i+1:02d}/{len(resources)}] {res['name']}...", end=" ", flush=True)
        df = download_and_aggregate(res)
        if len(df):
            all_months.append(df)
            print(f"{len(df):,} BNF codes")
            # Save incrementally so progress survives Ctrl-C
            partial = pd.concat(all_months, ignore_index=True)
            partial.to_csv(monthly_path, index=False)
        else:
            print("skipped")
        time.sleep(0.3)

    if not all_months:
        print("No data downloaded.")
        return

    raw = pd.concat(all_months, ignore_index=True)
    raw = raw.drop_duplicates(subset=["GENERIC_BNF_EQUIVALENT_CODE", "year_month"]
                              if "GENERIC_BNF_EQUIVALENT_CODE" in raw.columns
                              else ["bnf_code", "year_month"] if "bnf_code" in raw.columns
                              else raw.columns[:2])
    raw.to_csv(f"{OUT_DIR}/pca_demand_monthly.csv", index=False)
    print(f"\nRaw monthly aggregates: {len(raw):,} rows → {OUT_DIR}/pca_demand_monthly.csv")

    # Compute demand features
    print("Computing demand features...")
    features = compute_demand_features(raw)
    features.to_csv(f"{OUT_DIR}/pca_demand_features.csv", index=False)
    print(f"Demand features: {len(features):,} rows → {OUT_DIR}/pca_demand_features.csv")

    # Summary
    latest_month = features["month"].max()
    latest = features[features["month"] == latest_month]
    spikes = latest[latest["demand_spike"] == 1].sort_values("items_mom_pct", ascending=False)

    print(f"\nBNF codes covered : {features['bnf_code'].nunique():,}")
    print(f"Months covered    : {features['month'].nunique()}")
    print(f"Demand spikes     : {features['demand_spike'].sum():,} total, {len(spikes)} in latest month ({latest_month})")

    if len(spikes):
        print(f"\nTop 10 demand spikes ({latest_month}):")
        cols = ["bnf_code", "bnf_name", "items", "items_mom_pct", "items_yoy_pct"]
        print(spikes[cols].head(10).to_string(index=False))

    return features


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
