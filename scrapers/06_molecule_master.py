"""
SCRAPER 06: Molecule Master — BNF → dm+d → Product Name Normaliser
===================================================================
Sources:
  A) NHSBSA TRUD (Technology Reference Update Distribution)
     https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/6
     dm+d (Dictionary of Medicines and Devices) XML — weekly update
  B) OpenPrescribing BNF API
     https://openprescribing.net/api/1.0/bnf_code/?format=json
  C) NHS SNOMED CT browser
     https://ontology.nhs.uk/production1/fhir/ValueSet/$expand?url=...
  D) BNF codes from NHSBSA Drug Tariff directly

Purpose:
  The Molecule Master is the identity resolution layer — the single most
  critical infrastructure component. Every JOIN across data sources runs
  through this table. Without it, you will silently conflate:
  - Metformin 500mg and Metformin 850mg (different shortage patterns)
  - Branded and generic equivalents
  - Different pack sizes of the same drug
  - Parallel imports vs domestic supply

Schema: bnf_code | bnf_name | snomed_id | product_name_clean |
        strength | formulation | route | manufacturer_count |
        is_generic | api_country (India/China/EU) | dmd_id
"""

import requests
import pandas as pd
import re
import os
import json
from bs4 import BeautifulSoup

OUTPUT_DIR = "data/molecule_master"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NPTResearchBot/1.0)"}

# ── METHOD A: Parse dm+d XML from TRUD ───────────────────────────────────────
def parse_dmd_xml(xml_file_path: str) -> pd.DataFrame:
    """
    Parse the NHSBSA dm+d XML file (downloaded from TRUD — requires free registration).
    Download from: https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/6
    File: nhsbsa_dmd_YYYYMMDD.zip → extract → parse VTM.xml, VMP.xml, VMPP.xml, AMP.xml

    dm+d hierarchy:
      VTM  — Virtual Therapeutic Moiety (e.g. "Metformin")
      VMP  — Virtual Medicinal Product (e.g. "Metformin 500mg tablets")
      VMPP — VMP Pack (e.g. "Metformin 500mg tablets 28 tablet")
      AMP  — Actual Medicinal Product (e.g. branded/generic specific products)
    """
    import xml.etree.ElementTree as ET

    if not os.path.exists(xml_file_path):
        print(f"  dm+d XML not found at {xml_file_path}")
        print("  Download from: https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/6")
        print("  (Free registration required)")
        return pd.DataFrame()

    print(f"  Parsing dm+d XML: {xml_file_path}")
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    records = []
    for vmp in root.findall(".//VMP"):
        vtm_id = vmp.findtext("VTMID", "")
        vmp_id = vmp.findtext("VPID", "")
        name   = vmp.findtext("NM", "")
        abbr   = vmp.findtext("ABBREVNM", "")

        # Extract strength and formulation from name
        # Pattern: "Drug Name strength form" e.g. "Metformin 500mg tablets"
        strength_match = re.search(r"(\d+(?:\.\d+)?(?:mg|mcg|g|ml|unit|micrograms?))", name, re.IGNORECASE)
        strength = strength_match.group(1) if strength_match else ""

        form_keywords = ["tablet", "capsule", "solution", "suspension", "injection",
                         "cream", "ointment", "patch", "inhaler", "drops", "syrup"]
        formulation = next((f for f in form_keywords if f in name.lower()), "")

        records.append({
            "dmd_vmp_id":      vmp_id,
            "dmd_vtm_id":      vtm_id,
            "product_name":    name,
            "product_abbr":    abbr,
            "strength":        strength,
            "formulation":     formulation,
        })

    df = pd.DataFrame(records)
    print(f"  Parsed {len(df):,} VMP records from dm+d")
    return df

# ── METHOD B: OpenPrescribing BNF mapping ────────────────────────────────────
def fetch_openprescribing_bnf_codes() -> pd.DataFrame:
    """
    OpenPrescribing exposes a full BNF code list with names.
    No registration required. Returns all BNF codes used in NHS prescribing.
    """
    url = "https://openprescribing.net/api/1.0/bnf_code/?format=json&is_generic=true"
    print(f"  Fetching BNF codes from OpenPrescribing...")

    try:
        r = requests.get(url, timeout=60, headers=HEADERS)
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and "results" in data:
            df = pd.DataFrame(data["results"])
        else:
            df = pd.json_normalize(data)

        print(f"  Retrieved {len(df):,} BNF codes")
        return df

    except Exception as e:
        print(f"  OpenPrescribing BNF API error: {e}")
        return pd.DataFrame()

# ── METHOD C: Build from NHSBSA Drug Tariff CSV ───────────────────────────────
def build_master_from_tariff(tariff_csv_path: str) -> pd.DataFrame:
    """
    Build a basic molecule master from the NHSBSA Drug Tariff Part VIIIA CSV.
    This is the fallback when dm+d XML is not available.
    Creates: bnf_code | drug_name_raw | strength | formulation | pack_size
    """
    if not os.path.exists(tariff_csv_path):
        print(f"  Drug Tariff CSV not found: {tariff_csv_path}")
        print("  Run scraper 01 first to download it.")
        return pd.DataFrame()

    df = pd.read_csv(tariff_csv_path, encoding="latin-1")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Standardise column names
    if "bnf_code" not in df.columns and "drug" in df.columns:
        df = df.rename(columns={"drug": "drug_name_raw"})

    # Extract components from drug name
    def parse_drug_name(name: str) -> dict:
        name = str(name).strip()
        # Extract strength
        strength_match = re.search(
            r"(\d+(?:\.\d+)?(?:mg|mcg|g|ml|micrograms?|units?|%|iu|mmol))",
            name, re.IGNORECASE
        )
        strength = strength_match.group(1) if strength_match else ""

        # Extract formulation
        forms = {
            "tablet": r"\btablet|\btab\b",
            "capsule": r"\bcapsule|\bcap\b",
            "injection": r"\binjection|\binj\b",
            "solution": r"\bsolution|\bsoln\b",
            "suspension": r"\bsuspension|\bsusp\b",
            "cream": r"\bcream\b",
            "ointment": r"\bointment\b",
            "patch": r"\bpatch|\bpatches\b",
            "inhaler": r"\binhaler\b",
            "oral": r"\boral\b",
            "modified_release": r"\bmodified.release|\bMR\b|\bm/r\b",
        }
        formulation = next((f for f, pat in forms.items() if re.search(pat, name, re.IGNORECASE)), "other")

        # Extract base drug name (everything before the strength)
        base_name = re.split(r"\d+(?:\.\d+)?(?:mg|mcg|g|ml|micrograms?)", name, flags=re.IGNORECASE)[0].strip()

        return {
            "drug_name_clean": base_name,
            "strength":        strength,
            "formulation":     formulation,
        }

    parsed = df["drug_name_raw"].apply(parse_drug_name)
    df = pd.concat([df, pd.DataFrame(list(parsed))], axis=1)

    # Flag as generic (Drug Tariff Part VIIIA = all generics)
    df["is_generic"] = 1

    print(f"  Built molecule master from Tariff: {len(df):,} products")
    return df

# ── ENRICH: Add manufacturer count from Companies House API ───────────────────
def enrich_with_manufacturer_data(df: pd.DataFrame, drug_names: list) -> pd.DataFrame:
    """
    Use Companies House API to estimate manufacturer count for each molecule.
    Free API key required: https://developer.company-information.service.gov.uk/
    """
    API_KEY = os.environ.get("COMPANIES_HOUSE_API_KEY", "")
    if not API_KEY:
        print("  Set COMPANIES_HOUSE_API_KEY environment variable for manufacturer enrichment")
        return df

    base_url = "https://api.company-information.service.gov.uk/search/companies"
    pharma_terms = ["pharmaceutical", "pharma", "generics", "medicines"]

    manufacturers = {}
    for drug in drug_names[:50]:  # Rate limit: first 50
        try:
            r = requests.get(
                base_url,
                params={"q": f"{drug} pharmaceutical manufacturing"},
                auth=(API_KEY, ""),
                timeout=10,
            )
            if r.status_code == 200:
                count = len(r.json().get("items", []))
                manufacturers[drug] = count
        except Exception:
            pass

    if manufacturers:
        mfr_df = pd.DataFrame(list(manufacturers.items()), columns=["drug_name_clean", "manufacturer_count_proxy"])
        df = df.merge(mfr_df, on="drug_name_clean", how="left")

    return df

# ── BUILD FINAL MASTER ────────────────────────────────────────────────────────
def build_molecule_master(
    tariff_csv: str = "data/drug_tariff/tariff_with_floors.csv",
    dmd_xml:    str = "data/dmd/VMP.xml"
) -> pd.DataFrame:
    """
    Build the unified Molecule Master table.
    Priority: dm+d XML > OpenPrescribing BNF > Drug Tariff CSV
    """
    print("Building Molecule Master...")

    # Try dm+d first
    df_dmd = parse_dmd_xml(dmd_xml)

    # Supplement with OpenPrescribing BNF codes (BNF ↔ drug name mapping)
    df_bnf = fetch_openprescribing_bnf_codes()

    # Build from tariff as foundation
    df_tariff = build_master_from_tariff(tariff_csv)

    # Merge available sources — use dm+d as foundation if tariff not yet available
    if not df_tariff.empty:
        master = df_tariff.copy()
    elif not df_dmd.empty:
        # dm+d as standalone foundation (tariff not yet downloaded)
        master = df_dmd.rename(columns={
            "product_name": "drug_name",
            "dmd_vmp_id":   "dmd_id",
        }).copy()
        master["drug_name_clean"] = master["drug_name"]
        master["bnf_code"] = ""   # populated once tariff runs
        print(f"  Using dm+d as foundation: {len(master):,} VMP records")
    else:
        master = pd.DataFrame()

    if not df_bnf.empty and "id" in df_bnf.columns:
        df_bnf = df_bnf.rename(columns={"id": "bnf_code", "name": "bnf_name_op"})
        if "bnf_code" in master.columns:
            master = master.merge(df_bnf[["bnf_code", "bnf_name_op"]], on="bnf_code", how="left")

    if not df_dmd.empty and not df_tariff.empty and "bnf_code" in master.columns:
        master = master.merge(
            df_dmd[["product_name", "strength", "formulation", "dmd_vmp_id"]],
            left_on="drug_name_clean",
            right_on="product_name",
            how="left",
            suffixes=("", "_dmd")
        )

    # Add API country (heuristic — India/China supply ~70%/15% of UK generic APIs)
    # In production this would come from manufacturer licensing data
    master["api_country_primary"] = "India"  # Default; enrich with real data

    # Save
    out_path = f"{OUTPUT_DIR}/molecule_master.csv"
    master.to_csv(out_path, index=False)
    print(f"\nMolecule Master saved: {len(master):,} products → {out_path}")

    return master

if __name__ == "__main__":
    build_molecule_master()
