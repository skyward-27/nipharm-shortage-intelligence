#!/usr/bin/env python3
"""
23_invoice_price_pipeline.py
============================
Processes client pharmacy invoice data to build:
  1. Wholesale price history (unified timeseries)
  2. Best historic price per drug
  3. Buy / Hold / Bulk Buy recommendations
  4. Merge new pricing features into the panel feature store

Data sources (PRIVATE — never on GitHub):
  - Victoria_OS_Pricing_Data.xlsx (ordered items + price summary)
  - Medication_Invoice_Index.xlsx (invoice metadata)
  - PDF invoices from Bessbrook / Lowwood / McGregor pharmacies
  - Existing pharmacy_training_features.csv

Outputs (scrapers/data/pharmacy_invoices/ — .gitignored):
  - wholesale_price_history.csv
  - best_historic_price.csv
  - buying_recommendations.csv
  - Updated panel_feature_store_train.csv (new pricing columns)

Author: NPT Stock Intelligence Unit
Date:   2026-04-12
"""

import os
import re
import warnings
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent  # scrapers/
DATA_DIR = ROOT / "data"
INVOICE_DIR = DATA_DIR / "pharmacy_invoices"
INVOICE_DIR.mkdir(parents=True, exist_ok=True)

INVOICE_DATA_ROOT = Path.home() / "Documents" / "NPT_Invoice_Data" / "OneDrive_2026-04-12"
VICTORIA_XLSX = INVOICE_DATA_ROOT / "Victoria_OS_Pricing_Data.xlsx"
INDEX_XLSX = INVOICE_DATA_ROOT / "Medication_Invoice_Index.xlsx"

EXISTING_FEATURES = INVOICE_DIR / "pharmacy_training_features.csv"
DRUG_TARIFF = DATA_DIR / "drug_tariff" / "drug_tariff_202603.csv"
PANEL_STORE = DATA_DIR / "features" / "panel_feature_store_train.csv"

# PDF invoice folders
PDF_PHARMACIES = {
    "Bessbrook Pharmacy": INVOICE_DATA_ROOT / "Bessbrook Pharmacy",
    "Lowwood Pharmacy": INVOICE_DATA_ROOT / "Lowwood Pharmacy",
    "McGregor Chemist": INVOICE_DATA_ROOT / "McGregor Chemist",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def normalise_drug_name(name: str) -> str:
    """Lowercase, strip pack size info, extra whitespace."""
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    # Remove "pk: 28", "pk:112", "x 28", etc.
    name = re.sub(r"\s*pk\s*:\s*\d+", "", name)
    name = re.sub(r"\s*x\s*\d+\s*$", "", name)
    # Remove trailing whitespace
    name = name.strip()
    return name


def extract_base_molecule(name) -> str:
    """Extract the base molecule name (first word or two before strength).
    e.g. 'metformin 500mg tablets' -> 'metformin'
    e.g. 'co-codamol 30mg/500mg' -> 'co-codamol'
    """
    if not isinstance(name, str) or not name:
        return ""
    # Match up to the first numeric strength pattern
    m = re.match(r"^([\w\-]+(?:\s[\w\-]+)?)\s+\d", name)
    if m:
        return m.group(1).strip()
    # Fallback: first word
    return name.split()[0] if name.split() else ""


def parse_price(val) -> float:
    """Safely parse a price value to float."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace("£", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return np.nan


def parse_date(val) -> pd.Timestamp:
    """Safely parse a date value."""
    if pd.isna(val):
        return pd.NaT
    try:
        return pd.to_datetime(val, dayfirst=True)
    except Exception:
        return pd.NaT


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: Parse Victoria OS xlsx
# ══════════════════════════════════════════════════════════════════════════════
def step1_parse_victoria_os():
    """Load Victoria OS Ordered Items and Price Summary sheets."""
    print("\n" + "=" * 70)
    print("STEP 1: Parsing Victoria OS Pricing Data")
    print("=" * 70)

    ordered_items = pd.DataFrame()
    price_summary = pd.DataFrame()

    if not VICTORIA_XLSX.exists():
        print(f"  [WARN] Victoria OS file not found: {VICTORIA_XLSX}")
        return ordered_items, price_summary

    try:
        # Ordered Items sheet
        oi = pd.read_excel(VICTORIA_XLSX, sheet_name="Ordered Items")
        print(f"  Loaded 'Ordered Items': {len(oi)} rows")

        ordered_items = pd.DataFrame({
            "drug_name": oi["Description"].apply(normalise_drug_name),
            "date": oi["Order Date"].apply(parse_date),
            "pharmacy": oi["Pharmacy"].str.strip(),
            "supplier": oi["Supplier"].str.strip(),
            "unit_price_gbp": oi["Unit Price (£)"].apply(parse_price),
            "qty": pd.to_numeric(oi["Ordered Qty"], errors="coerce"),
            "product_code": oi["Product Code"].astype(str),
            "source": "victoria_os",
        })
        ordered_items = ordered_items.dropna(subset=["drug_name", "unit_price_gbp"])
        print(f"  Valid ordered items: {len(ordered_items)}")

    except Exception as e:
        print(f"  [ERROR] Ordered Items: {e}")

    try:
        # Price Summary sheet
        ps = pd.read_excel(VICTORIA_XLSX, sheet_name="Price Summary")
        print(f"  Loaded 'Price Summary': {len(ps)} rows")

        price_summary = pd.DataFrame({
            "drug_name": ps["Description"].apply(normalise_drug_name),
            "product_code": ps["Product Code"].astype(str),
            "avg_price": ps["Avg Price (£)"].apply(parse_price),
            "min_price": ps["Min Price (£)"].apply(parse_price),
            "max_price": ps["Max Price (£)"].apply(parse_price),
            "total_qty": pd.to_numeric(ps["Total Qty Ordered"], errors="coerce"),
            "num_suppliers": pd.to_numeric(ps["# Suppliers"], errors="coerce"),
            "suppliers": ps["Suppliers"].astype(str),
        })
        price_summary = price_summary.dropna(subset=["drug_name"])
        print(f"  Valid price summary rows: {len(price_summary)}")

    except Exception as e:
        print(f"  [ERROR] Price Summary: {e}")

    return ordered_items, price_summary


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: Parse Invoice Index xlsx
# ══════════════════════════════════════════════════════════════════════════════
def step2_parse_invoice_index():
    """Load invoice metadata from Medication Invoice Index."""
    print("\n" + "=" * 70)
    print("STEP 2: Parsing Medication Invoice Index")
    print("=" * 70)

    if not INDEX_XLSX.exists():
        print(f"  [WARN] Invoice index not found: {INDEX_XLSX}")
        return pd.DataFrame()

    try:
        inv = pd.read_excel(INDEX_XLSX, sheet_name="All Invoices")
        print(f"  Loaded 'All Invoices': {len(inv)} rows")

        invoice_index = pd.DataFrame({
            "pharmacy": inv["Pharmacy"].str.strip(),
            "supplier": inv["Supplier"].str.strip(),
            "subject": inv["Subject"].astype(str),
            "date_received": inv["Date Received"].apply(parse_date),
            "month": inv["Month"].astype(str),
            "has_attachment": inv["Has Attachment"].astype(str),
            "amount": inv["Amount (if visible)"].apply(parse_price),
        })
        print(f"  Pharmacies: {invoice_index['pharmacy'].nunique()}")
        print(f"  Suppliers:  {invoice_index['supplier'].nunique()}")
        print(f"  Date range: {invoice_index['date_received'].min()} to "
              f"{invoice_index['date_received'].max()}")
        return invoice_index

    except Exception as e:
        print(f"  [ERROR] Invoice index: {e}")
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: Try to parse PDF invoices (optional)
# ══════════════════════════════════════════════════════════════════════════════
def step3_parse_pdf_invoices():
    """Attempt to extract drug prices from PDF invoices using pdfplumber."""
    print("\n" + "=" * 70)
    print("STEP 3: Parsing PDF Invoices (optional)")
    print("=" * 70)

    try:
        import pdfplumber
        print("  pdfplumber available — attempting PDF extraction")
    except ImportError:
        print("  [WARN] pdfplumber not installed — skipping PDF parsing")
        print("         Install with: pip install pdfplumber")
        return pd.DataFrame()

    all_rows = []
    pdf_count = 0
    error_count = 0

    for pharmacy_name, pharmacy_dir in PDF_PHARMACIES.items():
        if not pharmacy_dir.exists():
            print(f"  [WARN] Directory not found: {pharmacy_dir}")
            continue

        # Find all PDFs recursively
        pdfs = sorted(pharmacy_dir.rglob("*.pdf"))
        print(f"  {pharmacy_name}: {len(pdfs)} PDFs found")

        for pdf_path in pdfs:
            try:
                # Try to infer date from folder name (e.g. "2026-03 March")
                invoice_date = pd.NaT
                parent_name = pdf_path.parent.name
                date_match = re.match(r"(\d{4}-\d{2})", parent_name)
                if date_match:
                    invoice_date = pd.to_datetime(date_match.group(1) + "-01")

                with pdfplumber.open(str(pdf_path)) as pdf:
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        if not tables:
                            continue

                        for table in tables:
                            if len(table) < 2:
                                continue

                            # Try to identify columns from header row
                            header = [str(c).lower().strip() if c else "" for c in table[0]]

                            # Look for price-like and description-like columns
                            desc_idx = None
                            price_idx = None
                            qty_idx = None

                            for i, h in enumerate(header):
                                if any(k in h for k in ["description", "product", "item", "drug", "name"]):
                                    desc_idx = i
                                if any(k in h for k in ["unit price", "price", "unit", "rate"]):
                                    price_idx = i
                                if any(k in h for k in ["qty", "quantity", "ordered", "supplied"]):
                                    qty_idx = i

                            if desc_idx is None or price_idx is None:
                                continue

                            # Extract data rows
                            for row in table[1:]:
                                if len(row) <= max(desc_idx, price_idx):
                                    continue
                                desc = row[desc_idx]
                                price = row[price_idx]
                                qty = row[qty_idx] if qty_idx is not None and qty_idx < len(row) else None

                                if not desc or not price:
                                    continue

                                parsed_price = parse_price(price)
                                if pd.isna(parsed_price) or parsed_price <= 0:
                                    continue

                                all_rows.append({
                                    "drug_name": normalise_drug_name(str(desc)),
                                    "date": invoice_date,
                                    "pharmacy": pharmacy_name,
                                    "supplier": "unknown_pdf",
                                    "unit_price_gbp": parsed_price,
                                    "qty": parse_price(qty) if qty else np.nan,
                                    "product_code": "",
                                    "source": f"pdf_{pharmacy_name.lower().replace(' ', '_')}",
                                })

                pdf_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  [WARN] Error parsing {pdf_path.name}: {e}")

    pdf_df = pd.DataFrame(all_rows)
    print(f"  PDFs processed: {pdf_count} | Errors: {error_count}")
    print(f"  Line items extracted: {len(pdf_df)}")
    return pdf_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: Merge all price data
# ══════════════════════════════════════════════════════════════════════════════
def step4_merge_price_data(victoria_items, pdf_items):
    """Combine all price sources into one unified timeseries."""
    print("\n" + "=" * 70)
    print("STEP 4: Merging All Price Data")
    print("=" * 70)

    frames = []

    # Victoria OS items
    if len(victoria_items) > 0:
        frames.append(victoria_items[["drug_name", "date", "pharmacy", "supplier",
                                       "unit_price_gbp", "qty", "source"]])
        print(f"  Victoria OS items:       {len(victoria_items)}")

    # PDF items
    if len(pdf_items) > 0:
        frames.append(pdf_items[["drug_name", "date", "pharmacy", "supplier",
                                  "unit_price_gbp", "qty", "source"]])
        print(f"  PDF-extracted items:     {len(pdf_items)}")

    # Existing pharmacy training features
    if EXISTING_FEATURES.exists():
        try:
            existing = pd.read_csv(EXISTING_FEATURES)
            mapped = pd.DataFrame({
                "drug_name": existing["description"].apply(normalise_drug_name),
                "date": existing["date"].apply(parse_date),
                "pharmacy": existing["branch"].str.strip(),
                "supplier": existing["supplier"].str.strip() if "supplier" in existing.columns else "unknown",
                "unit_price_gbp": existing["unit_price_gbp"].apply(parse_price),
                "qty": pd.to_numeric(existing.get("qty_ordered", np.nan), errors="coerce"),
                "source": "pharmacy_training_features",
            })
            mapped = mapped.dropna(subset=["drug_name", "unit_price_gbp"])
            frames.append(mapped)
            print(f"  Existing training data:  {len(mapped)}")
        except Exception as e:
            print(f"  [WARN] Could not load existing features: {e}")

    if not frames:
        print("  [ERROR] No price data available!")
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)

    # Remove rows with zero or negative prices
    merged = merged[merged["unit_price_gbp"] > 0].copy()

    # Add base molecule for matching
    merged["base_molecule"] = merged["drug_name"].apply(extract_base_molecule)

    # Sort by drug and date
    merged = merged.sort_values(["drug_name", "date"]).reset_index(drop=True)

    # Save
    out_path = INVOICE_DIR / "wholesale_price_history.csv"
    merged.to_csv(out_path, index=False)
    print(f"\n  TOTAL merged rows: {len(merged)}")
    print(f"  Unique drugs:      {merged['drug_name'].nunique()}")
    print(f"  Date range:        {merged['date'].min()} to {merged['date'].max()}")
    print(f"  Saved: {out_path}")

    return merged


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: Compute Best Historic Price per drug
# ══════════════════════════════════════════════════════════════════════════════
def step5_best_historic_price(price_history):
    """Compute best, average, and current prices per drug."""
    print("\n" + "=" * 70)
    print("STEP 5: Computing Best Historic Price")
    print("=" * 70)

    if price_history.empty:
        print("  [ERROR] No price history available!")
        return pd.DataFrame()

    drugs = price_history.groupby("drug_name").agg(
        best_historic_price=("unit_price_gbp", "min"),
        avg_historic_price=("unit_price_gbp", "mean"),
        max_historic_price=("unit_price_gbp", "max"),
        observation_count=("unit_price_gbp", "count"),
        first_seen=("date", "min"),
        last_seen=("date", "max"),
    ).reset_index()

    # Current price = most recent observation per drug
    recent = (price_history
              .sort_values("date")
              .groupby("drug_name")
              .last()
              .reset_index()[["drug_name", "unit_price_gbp", "date", "supplier"]])
    recent.columns = ["drug_name", "current_price", "current_date", "current_supplier"]

    drugs = drugs.merge(recent, on="drug_name", how="left")

    # 3-month rolling average (where we have dates)
    three_months_ago = pd.Timestamp.now() - pd.DateOffset(months=3)
    recent_prices = (price_history[price_history["date"] >= three_months_ago]
                     .groupby("drug_name")["unit_price_gbp"]
                     .mean()
                     .reset_index()
                     .rename(columns={"unit_price_gbp": "avg_price_3mo"}))
    drugs = drugs.merge(recent_prices, on="drug_name", how="left")

    # Price trend: current vs 3-month avg
    drugs["price_trend_pct"] = np.where(
        drugs["avg_price_3mo"].notna() & (drugs["avg_price_3mo"] > 0),
        ((drugs["current_price"] - drugs["avg_price_3mo"]) / drugs["avg_price_3mo"] * 100).round(1),
        np.nan
    )

    # Price vs best historic
    drugs["price_vs_best_pct"] = np.where(
        drugs["best_historic_price"] > 0,
        ((drugs["current_price"] - drugs["best_historic_price"]) / drugs["best_historic_price"] * 100).round(1),
        np.nan
    )

    # Add base molecule
    drugs["base_molecule"] = drugs["drug_name"].apply(extract_base_molecule)

    # Save
    out_path = INVOICE_DIR / "best_historic_price.csv"
    drugs.to_csv(out_path, index=False)
    print(f"  Drugs with pricing: {len(drugs)}")
    print(f"  Saved: {out_path}")

    return drugs


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: Generate Buy/Hold/BulkBuy recommendations
# ══════════════════════════════════════════════════════════════════════════════
def step6_buying_recommendations(best_prices):
    """Generate actionable buying recommendations per drug."""
    print("\n" + "=" * 70)
    print("STEP 6: Generating Buying Recommendations")
    print("=" * 70)

    if best_prices.empty:
        print("  [ERROR] No pricing data for recommendations!")
        return pd.DataFrame()

    recs = best_prices.copy()

    # ── Recommendation logic ──
    conditions = [
        recs["current_price"] <= recs["best_historic_price"] * 1.05,
        recs["current_price"] <= recs["avg_historic_price"],
        recs["current_price"] > recs["avg_historic_price"] * 1.20,
    ]
    choices = ["BULK BUY", "BUY AS YOU GO", "HOLD BUYING"]
    recs["recommendation"] = np.select(conditions, choices, default="BUY AS YOU GO")

    # ── Drug Tariff comparison ──
    recs["tariff_price_gbp"] = np.nan
    recs["price_vs_tariff_pct"] = np.nan
    recs["margin_gbp"] = np.nan

    if DRUG_TARIFF.exists():
        try:
            tariff = pd.read_csv(DRUG_TARIFF)
            # Tariff 'Basic price' is in pence, convert to GBP
            tariff["tariff_gbp"] = tariff["Basic price"] / 100.0
            tariff["tariff_drug"] = tariff["Drug Name"].str.lower().str.strip()
            tariff["tariff_molecule"] = tariff["tariff_drug"].apply(extract_base_molecule)

            # Try exact drug name match first
            tariff_lookup = tariff.groupby("tariff_drug")["tariff_gbp"].first().to_dict()
            recs["tariff_price_gbp"] = recs["drug_name"].map(tariff_lookup)

            # For unmatched, try base molecule match (take the median tariff)
            unmatched = recs["tariff_price_gbp"].isna()
            if unmatched.any():
                mol_tariff = tariff.groupby("tariff_molecule")["tariff_gbp"].median().to_dict()
                recs.loc[unmatched, "tariff_price_gbp"] = (
                    recs.loc[unmatched, "base_molecule"].map(mol_tariff)
                )

            # Compute margins
            has_tariff = recs["tariff_price_gbp"].notna() & (recs["tariff_price_gbp"] > 0)
            recs.loc[has_tariff, "price_vs_tariff_pct"] = (
                (recs.loc[has_tariff, "current_price"] / recs.loc[has_tariff, "tariff_price_gbp"] * 100 - 100).round(1)
            )
            recs.loc[has_tariff, "margin_gbp"] = (
                (recs.loc[has_tariff, "tariff_price_gbp"] - recs.loc[has_tariff, "current_price"]).round(2)
            )

            tariff_matched = has_tariff.sum()
            print(f"  Drug Tariff matches: {tariff_matched}/{len(recs)}")

        except Exception as e:
            print(f"  [WARN] Drug Tariff comparison failed: {e}")
    else:
        print(f"  [WARN] Drug Tariff file not found: {DRUG_TARIFF}")

    # Sort: BULK BUY first, then HOLD BUYING, then rest
    rec_order = {"BULK BUY": 0, "HOLD BUYING": 1, "BUY AS YOU GO": 2}
    recs["_sort"] = recs["recommendation"].map(rec_order)
    recs = recs.sort_values(["_sort", "price_vs_best_pct"]).drop(columns="_sort")

    # Save
    out_path = INVOICE_DIR / "buying_recommendations.csv"
    recs.to_csv(out_path, index=False)
    print(f"  Total recommendations: {len(recs)}")
    for rec_type in ["BULK BUY", "BUY AS YOU GO", "HOLD BUYING"]:
        count = (recs["recommendation"] == rec_type).sum()
        print(f"    {rec_type}: {count}")
    print(f"  Saved: {out_path}")

    return recs


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7: Merge new features into panel feature store
# ══════════════════════════════════════════════════════════════════════════════
def step7_merge_panel_features(best_prices):
    """Add wholesale price features to the panel feature store."""
    print("\n" + "=" * 70)
    print("STEP 7: Merging Features into Panel Feature Store")
    print("=" * 70)

    if not PANEL_STORE.exists():
        print(f"  [WARN] Panel feature store not found: {PANEL_STORE}")
        return

    if best_prices.empty:
        print("  [WARN] No pricing data to merge")
        return

    try:
        panel = pd.read_csv(PANEL_STORE)
        print(f"  Loaded panel store: {panel.shape[0]} rows x {panel.shape[1]} cols")

        # Build lookup: base_molecule -> features
        price_features = best_prices.groupby("base_molecule").agg(
            best_historic_price=("best_historic_price", "min"),
            price_vs_best_pct=("price_vs_best_pct", "median"),
            wholesale_margin_pct=("price_vs_tariff_pct", "median"),
        ).reset_index()

        # Extract base molecule from panel drug names
        panel["_match_mol"] = panel["drug_name"].str.lower().str.strip().apply(extract_base_molecule)

        # Check for existing columns and drop them before merge
        for col in ["best_historic_price", "price_vs_best_pct", "wholesale_margin_pct"]:
            if col in panel.columns:
                panel = panel.drop(columns=col)

        # Merge
        before_cols = panel.shape[1]
        panel = panel.merge(
            price_features,
            left_on="_match_mol",
            right_on="base_molecule",
            how="left"
        ).drop(columns=["_match_mol", "base_molecule"])

        matched = panel["best_historic_price"].notna().sum()
        print(f"  Panel rows matched: {matched}/{len(panel)} "
              f"({matched / len(panel) * 100:.1f}%)")
        print(f"  New columns added: {panel.shape[1] - before_cols + 1}")

        # Save (overwrite)
        panel.to_csv(PANEL_STORE, index=False)
        print(f"  Saved updated panel store: {panel.shape[0]} rows x {panel.shape[1]} cols")
        print(f"  Path: {PANEL_STORE}")

    except Exception as e:
        print(f"  [ERROR] Panel merge failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8: Print summary
# ══════════════════════════════════════════════════════════════════════════════
def step8_summary(price_history, best_prices, recommendations):
    """Print a human-readable summary of all results."""
    print("\n" + "=" * 70)
    print("STEP 8: Summary")
    print("=" * 70)

    if price_history.empty:
        print("  No data to summarise.")
        return

    print(f"\n  Price History")
    print(f"  {'─' * 40}")
    print(f"  Total price observations: {len(price_history)}")
    print(f"  Unique drugs:             {price_history['drug_name'].nunique()}")
    print(f"  Unique pharmacies:        {price_history['pharmacy'].nunique()}")
    print(f"  Unique suppliers:         {price_history['supplier'].nunique()}")
    print(f"  Date range:               {price_history['date'].min()} to {price_history['date'].max()}")
    print(f"  Sources:                  {price_history['source'].value_counts().to_dict()}")

    if not best_prices.empty:
        print(f"\n  Price Statistics")
        print(f"  {'─' * 40}")
        print(f"  Avg best historic price:  £{best_prices['best_historic_price'].mean():.2f}")
        print(f"  Avg current price:        £{best_prices['current_price'].mean():.2f}")
        print(f"  Median price trend:       {best_prices['price_trend_pct'].median():.1f}%")

    if not recommendations.empty:
        print(f"\n  Buying Recommendations")
        print(f"  {'─' * 40}")
        for rec_type in ["BULK BUY", "HOLD BUYING", "BUY AS YOU GO"]:
            subset = recommendations[recommendations["recommendation"] == rec_type]
            if len(subset) > 0:
                print(f"\n  >>> {rec_type} ({len(subset)} drugs) <<<")
                # Show top 10
                display_cols = ["drug_name", "current_price", "best_historic_price",
                                "price_vs_best_pct", "margin_gbp"]
                display_cols = [c for c in display_cols if c in subset.columns]
                top = subset.head(10)[display_cols]
                for _, row in top.iterrows():
                    name = row["drug_name"][:45].ljust(45)
                    curr = f"£{row['current_price']:.2f}" if pd.notna(row.get("current_price")) else "N/A"
                    best = f"£{row['best_historic_price']:.2f}" if pd.notna(row.get("best_historic_price")) else "N/A"
                    margin = f"£{row['margin_gbp']:.2f}" if pd.notna(row.get("margin_gbp")) else "N/A"
                    print(f"    {name}  curr={curr}  best={best}  margin={margin}")

    print(f"\n  Output Files")
    print(f"  {'─' * 40}")
    for f in INVOICE_DIR.glob("*.csv"):
        size_kb = f.stat().st_size / 1024
        print(f"    {f.name:45s} ({size_kb:.1f} KB)")

    print("\n" + "=" * 70)
    print("  Pipeline complete!")
    print("=" * 70)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  NPT Invoice Price Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Step 1
    victoria_items, price_summary = step1_parse_victoria_os()

    # Step 2
    invoice_index = step2_parse_invoice_index()

    # Step 3
    pdf_items = step3_parse_pdf_invoices()

    # Step 4
    price_history = step4_merge_price_data(victoria_items, pdf_items)

    if price_history.empty:
        print("\n[FATAL] No price data collected. Exiting.")
        return

    # Step 5
    best_prices = step5_best_historic_price(price_history)

    # Step 6
    recommendations = step6_buying_recommendations(best_prices)

    # Step 7 — use recommendations (has tariff columns from step 6)
    step7_merge_panel_features(recommendations)

    # Step 8
    step8_summary(price_history, best_prices, recommendations)


if __name__ == "__main__":
    main()
