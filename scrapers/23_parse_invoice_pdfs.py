"""
SCRIPT 23: Invoice PDF Parser
==============================
Parses downloaded AAH/Alliance Healthcare invoice PDFs and extracts:
  - Invoice date
  - Drug name
  - Pack size / quantity
  - Unit price paid (actual cost)
  - NHS Drug Tariff price (joined from tariff data)
  - Over/under tariff signal

Output: ~/Documents/NPT_Invoice_Data/combined/invoice_line_items.csv
        scrapers/data/pharmacy_invoices/pharmacy_training_features.csv  ← for ML model

Usage:
    python 23_parse_invoice_pdfs.py

IMPORTANT: Raw PDFs and line-item CSV stay LOCAL — never committed to git.
Only the aggregated ML features CSV is used by the model.
"""

import os
import re
import json
import pathlib
import pandas as pd
import pdfplumber
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
INVOICE_BASE   = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data"
BLACKLINE_PDFS = INVOICE_BASE / "blackline" / "raw_pdfs"
ALLIANCE_PDFS  = INVOICE_BASE / "alliance" / "raw_pdfs"
COMBINED_DIR   = INVOICE_BASE / "combined"
LINE_ITEMS_CSV = COMBINED_DIR / "invoice_line_items.csv"
FEATURES_CSV   = pathlib.Path(__file__).parent / "data" / "pharmacy_invoices" / "pharmacy_training_features.csv"

COMBINED_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_CSV.parent.mkdir(parents=True, exist_ok=True)


# ── Date patterns ──────────────────────────────────────────────────────────────
DATE_PATTERNS = [
    r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4})\b",
    r"\bInvoice\s+Date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",
    r"\bDate[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",
]

# ── Price patterns ─────────────────────────────────────────────────────────────
PRICE_PATTERN = re.compile(
    r"£\s*([\d,]+\.?\d{0,4})|"    # £12.34 or £ 12.34
    r"\b([\d,]+\.\d{2,4})\b"      # 12.3456 (pack price)
)

# ── Drug name patterns — NHS generic names ─────────────────────────────────────
# Matches "Amoxicillin 500mg capsules", "Co-codamol 8/500mg tablets" etc.
DRUG_PATTERN = re.compile(
    r"\b([A-Z][a-z]+(?:[\s\-][a-z]+)*(?:\s+\d+(?:\.\d+)?(?:mg|mcg|microgram|g|ml|%|unit|IU)[\s/]*)+"
    r"(?:tablet|capsule|injection|solution|suspension|cream|gel|patch|inhaler|spray|drop|syrup|liquid|"
    r"powder|granule|sachet|suppository|pessary|lozenge|film|modified|gastro|oro|dispersible|"
    r"effervescent|chewable)s?\b)",
    re.IGNORECASE,
)


def parse_date(text):
    """Extract first recognisable date from text."""
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
                        "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y",
                        "%B %d, %Y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m")
                except ValueError:
                    continue
    return None


def parse_pdf_blackline(pdf_path):
    """
    Parse a BlackLine EIPP invoice PDF.
    BlackLine invoices typically have a table structure:
      Description | Quantity | Unit Price | Total
    """
    rows = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            # Extract invoice date
            inv_date = parse_date(full_text)

            # Extract tables
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    # Find header row to identify columns
                    headers = [str(c).lower().strip() if c else "" for c in (table[0] or [])]

                    desc_col  = next((i for i, h in enumerate(headers) if any(k in h for k in ["desc", "product", "drug", "item", "name"])), None)
                    qty_col   = next((i for i, h in enumerate(headers) if any(k in h for k in ["qty", "quant", "pack", "units"])), None)
                    price_col = next((i for i, h in enumerate(headers) if any(k in h for k in ["unit price", "price", "cost", "each", "net"])), None)
                    total_col = next((i for i, h in enumerate(headers) if any(k in h for k in ["total", "amount", "value", "ext"])), None)

                    for data_row in table[1:]:
                        if not data_row:
                            continue
                        cells = [str(c).strip() if c else "" for c in data_row]

                        # Skip blank or header-repeat rows
                        if not any(cells) or cells == headers:
                            continue

                        drug_name = cells[desc_col].strip() if desc_col is not None and desc_col < len(cells) else ""
                        qty_raw   = cells[qty_col].strip()  if qty_col   is not None and qty_col   < len(cells) else ""
                        price_raw = cells[price_col].strip() if price_col is not None and price_col < len(cells) else ""

                        # Try to extract number from price cell
                        price_val = None
                        if price_raw:
                            price_clean = re.sub(r"[£,\s]", "", price_raw)
                            try:
                                price_val = float(price_clean)
                            except ValueError:
                                pass

                        qty_val = None
                        if qty_raw:
                            qty_clean = re.sub(r"[,\s]", "", qty_raw)
                            try:
                                qty_val = float(qty_clean)
                            except ValueError:
                                pass

                        # Skip rows without a drug name or price
                        if not drug_name or price_val is None:
                            continue
                        # Skip header rows that slipped through
                        if any(kw in drug_name.lower() for kw in ["description", "product", "item", "drug"]):
                            continue

                        rows.append({
                            "source":       "blackline",
                            "invoice_date": inv_date,
                            "drug_name_raw": drug_name,
                            "quantity":     qty_val,
                            "unit_price":   price_val,
                            "pdf_file":     pdf_path.name,
                        })

    except Exception as e:
        print(f"  ⚠️  Error parsing {pdf_path.name}: {e}")

    return rows


def parse_pdf_alliance(pdf_path):
    """
    Parse an Alliance Healthcare invoice PDF.
    Alliance typically shows: PIP code | Drug name | Qty | Price | Total
    """
    rows = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            inv_date = parse_date(full_text)

            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    headers = [str(c).lower().strip() if c else "" for c in (table[0] or [])]

                    desc_col  = next((i for i, h in enumerate(headers) if any(k in h for k in ["desc", "product", "drug", "item", "name"])), None)
                    qty_col   = next((i for i, h in enumerate(headers) if any(k in h for k in ["qty", "quant", "pack", "units"])), None)
                    price_col = next((i for i, h in enumerate(headers) if any(k in h for k in ["price", "cost", "each", "net", "unit"])), None)

                    for data_row in table[1:]:
                        if not data_row:
                            continue
                        cells = [str(c).strip() if c else "" for c in data_row]
                        if not any(cells):
                            continue

                        drug_name = cells[desc_col].strip() if desc_col is not None and desc_col < len(cells) else ""
                        qty_raw   = cells[qty_col].strip()  if qty_col   is not None and qty_col   < len(cells) else ""
                        price_raw = cells[price_col].strip() if price_col is not None and price_col < len(cells) else ""

                        price_val = None
                        if price_raw:
                            price_clean = re.sub(r"[£,\s]", "", price_raw)
                            try:
                                price_val = float(price_clean)
                            except ValueError:
                                pass

                        qty_val = None
                        if qty_raw:
                            try:
                                qty_val = float(re.sub(r"[,\s]", "", qty_raw))
                            except ValueError:
                                pass

                        if not drug_name or price_val is None:
                            continue
                        if any(kw in drug_name.lower() for kw in ["description", "product"]):
                            continue

                        rows.append({
                            "source":       "alliance",
                            "invoice_date": inv_date,
                            "drug_name_raw": drug_name,
                            "quantity":     qty_val,
                            "unit_price":   price_val,
                            "pdf_file":     pdf_path.name,
                        })

    except Exception as e:
        print(f"  ⚠️  Error parsing {pdf_path.name}: {e}")

    return rows


def normalise_drug_name(name):
    """Basic normalisation: lowercase, strip trailing whitespace/punctuation."""
    if not name:
        return ""
    n = str(name).lower().strip()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^\w\s\-\/\.%]", "", n)
    return n


def build_ml_features(line_items_df):
    """
    Aggregate invoice line items into drug-level ML features.
    Joins with Drug Tariff to compute over/under tariff signal.
    """
    if line_items_df.empty:
        print("  No line items to aggregate.")
        return pd.DataFrame()

    df = line_items_df.copy()
    df["drug_name_norm"] = df["drug_name_raw"].apply(normalise_drug_name)
    df["invoice_date"]   = pd.to_datetime(df["invoice_date"], errors="coerce")

    # Aggregate: median unit price per drug per month
    agg = (
        df.dropna(subset=["invoice_date"])
        .groupby(["drug_name_norm", df["invoice_date"].dt.to_period("M")])
        .agg(
            invoice_price_median  = ("unit_price", "median"),
            invoice_price_mean    = ("unit_price", "mean"),
            invoice_price_min     = ("unit_price", "min"),
            invoice_price_max     = ("unit_price", "max"),
            invoice_qty_total     = ("quantity",   "sum"),
            invoice_line_count    = ("unit_price", "count"),
        )
        .reset_index()
    )
    agg.rename(columns={"invoice_date": "month"}, inplace=True)
    agg["month"] = agg["month"].astype(str)

    # Try to join with Drug Tariff for over-tariff calculation
    tariff_path = pathlib.Path(__file__).parent / "data" / "drug_tariff" / "drug_tariff_202603.csv"
    if tariff_path.exists():
        tariff = pd.read_csv(tariff_path)
        tariff_col = next((c for c in tariff.columns if "price" in c.lower()), None)
        name_col   = next((c for c in tariff.columns if "name" in c.lower() or "drug" in c.lower()), None)

        if tariff_col and name_col:
            tariff["drug_name_norm"] = tariff[name_col].apply(normalise_drug_name)
            tariff_agg = tariff.groupby("drug_name_norm")[tariff_col].median().reset_index()
            tariff_agg.columns = ["drug_name_norm", "tariff_price_median"]
            agg = agg.merge(tariff_agg, on="drug_name_norm", how="left")
            agg["over_tariff_pct"] = (
                (agg["invoice_price_median"] / agg["tariff_price_median"] - 1) * 100
            ).round(2)
            agg["pharmacy_over_tariff"] = (agg["over_tariff_pct"] > 10).astype(int)
            print(f"  Joined with Drug Tariff: {agg['pharmacy_over_tariff'].sum()} over-tariff instances")
    else:
        print(f"  Drug Tariff not found at {tariff_path} — skipping over-tariff calculation")

    return agg


def main():
    print("=" * 60)
    print("Invoice PDF Parser")
    print("=" * 60)

    all_rows = []

    # ── Parse BlackLine PDFs ──────────────────────────────────────────────────
    blackline_pdfs = list(BLACKLINE_PDFS.glob("*.pdf"))
    print(f"\nBlackLine PDFs: {len(blackline_pdfs)} files in {BLACKLINE_PDFS}")
    for i, pdf_path in enumerate(blackline_pdfs, 1):
        print(f"  [{i}/{len(blackline_pdfs)}] {pdf_path.name}", end=" ", flush=True)
        rows = parse_pdf_blackline(pdf_path)
        print(f"→ {len(rows)} line items")
        all_rows.extend(rows)

    # ── Parse Alliance PDFs ───────────────────────────────────────────────────
    alliance_pdfs = list(ALLIANCE_PDFS.glob("*.pdf"))
    print(f"\nAlliance PDFs: {len(alliance_pdfs)} files in {ALLIANCE_PDFS}")
    for i, pdf_path in enumerate(alliance_pdfs, 1):
        print(f"  [{i}/{len(alliance_pdfs)}] {pdf_path.name}", end=" ", flush=True)
        rows = parse_pdf_alliance(pdf_path)
        print(f"→ {len(rows)} line items")
        all_rows.extend(rows)

    if not all_rows:
        print("\n⚠️  No line items extracted. Check that PDFs were downloaded first.")
        print("   Run: python 21_download_blackline_invoices.py")
        print("   Run: python 22_download_alliance_invoices.py")
        return

    # ── Save line items (LOCAL ONLY) ──────────────────────────────────────────
    line_df = pd.DataFrame(all_rows)
    line_df.to_csv(LINE_ITEMS_CSV, index=False)
    print(f"\n✅ {len(line_df)} total line items → {LINE_ITEMS_CSV}")

    # ── Build ML features ─────────────────────────────────────────────────────
    print("\nBuilding ML features...")
    features_df = build_ml_features(line_df)
    if not features_df.empty:
        features_df.to_csv(FEATURES_CSV, index=False)
        print(f"✅ {len(features_df)} drug-month features → {FEATURES_CSV}")
        print(f"   Columns: {list(features_df.columns)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"  Total invoices parsed: {len(blackline_pdfs) + len(alliance_pdfs)}")
    print(f"  Total line items:      {len(line_df)}")
    print(f"  Unique drugs:          {line_df['drug_name_raw'].nunique()}")
    date_range = f"{line_df['invoice_date'].min()} to {line_df['invoice_date'].max()}" if "invoice_date" in line_df else "unknown"
    print(f"  Date range:            {date_range}")
    print(f"{'='*60}")
    print("\nNext step: retrain ML model with invoice features:")
    print("  python 11_feature_store_panel.py")
    print("  python 12_ml_model_panel.py")


if __name__ == "__main__":
    main()
