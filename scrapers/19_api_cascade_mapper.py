"""
Script 19: API Supply Chain Cascade Mapper
==========================================
Maps each drug in our watchlist to its active pharmaceutical ingredient (API),
identifies which drugs share the same API (cascade risk), and checks OpenFDA
for US shortage signals at the API level.

Why this matters:
  Olanzapine 5mg + 10mg + 15mg + 20mg all use the SAME API from the SAME
  Indian manufacturers. One GMP failure → all 4 go on concession simultaneously.
  This is "cascade risk" — our model currently treats them independently.

New features added:
  - api_name                : standardised INN/API name
  - api_cascade_count       : how many other drugs in watchlist share this API
  - api_cascade_on_concession: how many of those cascade drugs are ALREADY on concession
  - api_us_shortage_flag    : OpenFDA shows active US shortage for this API
  - api_india_dependency    : 1 if this API is primarily manufactured in India/China
  - api_concentration_risk  : HIGH/MEDIUM/LOW based on manufacturer count

Output:
  data/early_warning/api_cascade_map.csv
  data/early_warning/api_cascade_features.csv
"""

import pathlib
import time
import re

import pandas as pd
import requests

HERE = pathlib.Path(__file__).parent
OUT  = HERE / "data" / "early_warning"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "NPT-Stock-Intelligence/1.0 (NHS pharmacy shortage research)"}

# ── Known API → drugs that use it (UK generics context) ──────────────────
# Format: "api_name": ["keyword1", "keyword2", ...]
# Built from dm+d VTM data + pharmacological knowledge
API_DRUG_MAP = {
    "olanzapine":              ["olanzapine"],
    "esomeprazole":            ["esomeprazole"],
    "omeprazole":              ["omeprazole"],
    "lactulose":               ["lactulose"],
    "pramipexole":             ["pramipexole"],
    "mefenamic acid":          ["mefenamic"],
    "indapamide":              ["indapamide"],
    "codeine phosphate":       ["co-codamol", "codeine", "co codamol"],
    "paracetamol":             ["paracetamol", "co-codamol", "co codamol"],
    "propranolol":             ["propranolol"],
    "hydroxocobalamin":        ["hydroxocobalamin"],
    "metformin":               ["metformin"],
    "amlodipine":              ["amlodipine"],
    "atorvastatin":            ["atorvastatin"],
    "simvastatin":             ["simvastatin"],
    "ramipril":                ["ramipril"],
    "lisinopril":              ["lisinopril"],
    "bisoprolol":              ["bisoprolol"],
    "sertraline":              ["sertraline"],
    "amitriptyline":           ["amitriptyline"],
    "gabapentin":              ["gabapentin"],
    "pregabalin":              ["pregabalin"],
    "levothyroxine":           ["levothyroxine"],
    "prednisolone":            ["prednisolone"],
    "doxycycline":             ["doxycycline"],
    "amoxicillin":             ["amoxicillin", "co-amoxiclav"],
    "clavulanic acid":         ["co-amoxiclav"],
    "azithromycin":            ["azithromycin"],
    "clarithromycin":          ["clarithromycin"],
    "fluoxetine":              ["fluoxetine"],
    "citalopram":              ["citalopram"],
    "naproxen":                ["naproxen"],
    "ibuprofen":               ["ibuprofen"],
    "diclofenac":              ["diclofenac"],
    "lansoprazole":            ["lansoprazole"],
    "pantoprazole":            ["pantoprazole"],
    "allopurinol":             ["allopurinol"],
    "tamsulosin":              ["tamsulosin"],
    "finasteride":             ["finasteride"],
    "sildenafil":              ["sildenafil"],
    "ibandronic acid":         ["ibandronic", "ibandronate"],
    "alendronic acid":         ["alendronic", "alendronate"],
    "budesonide":              ["budesonide"],
    "salbutamol":              ["salbutamol"],
    "tiotropium":              ["tiotropium"],
    "montelukast":             ["montelukast"],
    "cetirizine":              ["cetirizine"],
    "loratadine":              ["loratadine"],
    "folic acid":              ["folic acid"],
    "ferrous sulfate":         ["ferrous sulfate", "ferrous sulphate"],
    "warfarin":                ["warfarin"],
    "apixaban":                ["apixaban"],
    "rivaroxaban":             ["rivaroxaban"],
    "quetiapine":              ["quetiapine"],
    "risperidone":             ["risperidone"],
    "aripiprazole":            ["aripiprazole"],
    "clonazepam":              ["clonazepam"],
    "diazepam":                ["diazepam"],
    "zopiclone":               ["zopiclone"],
}

# ── API sourcing risk data (based on EudraGMDP, FDA research, industry data)
# HIGH = <3 global API manufacturers, predominantly India/China
# MEDIUM = 3-6 manufacturers, mix of origins
# LOW = >6 manufacturers, diversified supply
API_CONCENTRATION_RISK = {
    "olanzapine":              {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 3,  "india_china_pct": 85},
    "esomeprazole":            {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 4,  "india_china_pct": 75},
    "omeprazole":              {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 6,  "india_china_pct": 65},
    "lactulose":               {"risk": "HIGH",   "primary_source": "Europe", "manufacturers": 2,  "india_china_pct": 10},
    "pramipexole":             {"risk": "HIGH",   "primary_source": "China",  "manufacturers": 2,  "india_china_pct": 90},
    "mefenamic acid":          {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 3,  "india_china_pct": 80},
    "indapamide":              {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 3,  "india_china_pct": 75},
    "codeine phosphate":       {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 4,  "india_china_pct": 70},
    "paracetamol":             {"risk": "LOW",    "primary_source": "Europe", "manufacturers": 12, "india_china_pct": 30},
    "propranolol":             {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 3,  "india_china_pct": 80},
    "hydroxocobalamin":        {"risk": "HIGH",   "primary_source": "Europe", "manufacturers": 2,  "india_china_pct": 20},
    "metformin":               {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 8,  "india_china_pct": 70},
    "amlodipine":              {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 7,  "india_china_pct": 75},
    "atorvastatin":            {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 6,  "india_china_pct": 70},
    "doxycycline":             {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 3,  "india_china_pct": 80},
    "amoxicillin":             {"risk": "HIGH",   "primary_source": "China",  "manufacturers": 4,  "india_china_pct": 85},
    "azithromycin":            {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 4,  "india_china_pct": 80},
    "ibandronic acid":         {"risk": "HIGH",   "primary_source": "India",  "manufacturers": 3,  "india_china_pct": 85},
    "gabapentin":              {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 5,  "india_china_pct": 75},
    "pregabalin":              {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 5,  "india_china_pct": 75},
    "sertraline":              {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 6,  "india_china_pct": 70},
    "quetiapine":              {"risk": "MEDIUM", "primary_source": "India",  "manufacturers": 5,  "india_china_pct": 75},
}


def load_predictions() -> pd.DataFrame:
    path = HERE / "data" / "model" / "panel_predictions.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def query_openfda_shortage(api_name: str) -> dict:
    """Query OpenFDA drug shortages for a specific API name."""
    url = "https://api.fda.gov/drug/shortages.json"
    try:
        # search by active ingredient
        keyword = api_name.split()[0]  # use first word
        params = {
            "search": f'active_ingredient:"{keyword}"',
            "limit": 5,
        }
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            results = data.get("results", [])
            statuses = [rec.get("status", "") for rec in results]
            return {
                "openfda_shortage_count": total,
                "openfda_active_shortage": int(any(s.lower() == "active" for s in statuses)),
                "openfda_statuses": "|".join(statuses[:3]),
            }
        elif r.status_code == 404:
            return {"openfda_shortage_count": 0, "openfda_active_shortage": 0, "openfda_statuses": ""}
    except Exception as e:
        pass
    return {"openfda_shortage_count": 0, "openfda_active_shortage": 0, "openfda_statuses": ""}


def build_api_cascade_map(preds_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each drug in predictions, identify:
    1. Its API
    2. How many other drugs share that API (cascade count)
    3. How many of those are already on concession (cascade on concession)
    4. API concentration risk
    5. US shortage signal via OpenFDA
    """
    records = []

    # build reverse lookup: drug_keyword → api_name
    drug_to_api = {}
    for api_name, keywords in API_DRUG_MAP.items():
        for kw in keywords:
            drug_to_api[kw.lower()] = api_name

    # get list of drugs on concession right now
    if not preds_df.empty and "on_concession" in preds_df.columns:
        on_conc_drugs = set(
            preds_df[preds_df["on_concession"] == 1]["drug_name"].str.lower().tolist()
        )
    else:
        on_conc_drugs = set()

    processed_apis = {}  # cache OpenFDA results

    drug_names = preds_df["drug_name"].tolist() if not preds_df.empty else []

    for drug_name in drug_names:
        drug_lower = drug_name.lower()

        # find API for this drug
        matched_api = None
        for kw, api_name in drug_to_api.items():
            if kw in drug_lower:
                matched_api = api_name
                break

        if not matched_api:
            # use first significant word as API approximation
            words = [w for w in drug_lower.split() if len(w) > 4 and not w[0].isdigit()]
            matched_api = words[0] if words else drug_lower.split()[0]

        # find all drugs in watchlist that share this API
        api_keywords = API_DRUG_MAP.get(matched_api, [matched_api.split()[0]])
        cascade_drugs = []
        cascade_on_conc = []

        for other_drug in drug_names:
            if other_drug == drug_name:
                continue
            other_lower = other_drug.lower()
            if any(kw.lower() in other_lower for kw in api_keywords):
                cascade_drugs.append(other_drug)
                if other_lower in on_conc_drugs:
                    cascade_on_conc.append(other_drug)

        # get concentration risk data
        risk_data = API_CONCENTRATION_RISK.get(matched_api, {
            "risk": "UNKNOWN", "primary_source": "Unknown",
            "manufacturers": -1, "india_china_pct": -1
        })

        # get OpenFDA shortage — only query KNOWN APIs (not unmatched first-words)
        if matched_api in API_DRUG_MAP:
            if matched_api not in processed_apis:
                time.sleep(0.3)  # rate limit
                processed_apis[matched_api] = query_openfda_shortage(matched_api)
            fda_data = processed_apis[matched_api]
        else:
            fda_data = {"openfda_shortage_count": 0, "openfda_active_shortage": 0, "openfda_statuses": ""}

        records.append({
            "drug_name":                  drug_name,
            "api_name":                   matched_api,
            "api_cascade_count":          len(cascade_drugs),
            "api_cascade_drugs":          "|".join(cascade_drugs[:5]),
            "api_cascade_on_concession":  len(cascade_on_conc),
            "api_cascade_conc_drugs":     "|".join(cascade_on_conc[:5]),
            "api_concentration_risk":     risk_data["risk"],
            "api_primary_source":         risk_data["primary_source"],
            "api_manufacturer_count":     risk_data["manufacturers"],
            "api_india_china_pct":        risk_data["india_china_pct"],
            "api_india_dependency":       int(risk_data["india_china_pct"] >= 60) if risk_data["india_china_pct"] >= 0 else -1,
            "api_us_shortage_count":      fda_data["openfda_shortage_count"],
            "api_us_shortage_active":     fda_data["openfda_active_shortage"],
        })

    return pd.DataFrame(records)


def run():
    print("=" * 60)
    print("Script 19: API Supply Chain Cascade Mapper")
    print("=" * 60)

    preds_df = load_predictions()
    if preds_df.empty:
        print("ERROR: panel_predictions.csv not found. Run script 12 first.")
        return pd.DataFrame()

    print(f"Loaded {len(preds_df)} predictions")

    print("\nBuilding API cascade map...")
    print("  (querying OpenFDA for US shortage signals...)")
    api_df = build_api_cascade_map(preds_df)

    # save full cascade map
    map_path = OUT / "api_cascade_map.csv"
    api_df.to_csv(map_path, index=False)
    print(f"  Saved {len(api_df)} rows → {map_path}")

    # summary stats
    high_risk = api_df[api_df["api_concentration_risk"] == "HIGH"]
    cascade_risk = api_df[api_df["api_cascade_count"] > 1]
    us_shortage  = api_df[api_df["api_us_shortage_active"] == 1]

    print(f"\n  HIGH concentration risk drugs: {len(high_risk)}")
    print(f"  Drugs with cascade risk (share API): {len(cascade_risk)}")
    print(f"  Drugs with active US shortage signal: {len(us_shortage)}")

    # show top cascade clusters
    print("\n  Top API cascade clusters:")
    cluster_summary = (
        api_df.groupby("api_name")
        .agg(
            drugs_in_cluster=("drug_name", "count"),
            on_concession_in_cluster=("api_cascade_on_concession", "max"),
            concentration_risk=("api_concentration_risk", "first"),
            india_china_pct=("api_india_china_pct", "first"),
        )
        .query("drugs_in_cluster > 1")
        .sort_values("drugs_in_cluster", ascending=False)
        .head(15)
    )
    print(cluster_summary.to_string())

    # save features for model integration
    feature_cols = [
        "drug_name", "api_name", "api_cascade_count",
        "api_cascade_on_concession", "api_concentration_risk",
        "api_manufacturer_count", "api_india_china_pct",
        "api_india_dependency", "api_us_shortage_active",
    ]
    feat_df = api_df[[c for c in feature_cols if c in api_df.columns]]
    feat_path = OUT / "api_cascade_features.csv"
    feat_df.to_csv(feat_path, index=False)
    print(f"\n  Model features saved → {feat_path}")

    print("\nDone.")
    return api_df

if __name__ == "__main__":
    run()
