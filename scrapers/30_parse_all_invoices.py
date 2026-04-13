#!/usr/bin/env python3
"""
30_parse_all_invoices.py
========================
Comprehensive PDF invoice parser for 152 pharmacy invoices.
Extracts drug line items from three supplier formats:
  1. Ethigen (i0189xxx.pdf / c000xxx.pdf) — clean text, "Description Qty Rate Amount"
  2. MedHub/Bestway (010-SINV-xxx.pdf) — spaced-out text, needs de-spacing
  3. PHD/PIN credit notes (Credits For Acc) — qty + drug + pip + price format

Skips non-drug PDFs: power bills, statements, waste invoices, surgical summaries,
packaging supply invoices (EMT Healthcare).

Outputs:
  - scrapers/data/pharmacy_invoices/all_pdf_drug_lines.csv
  - Merges with existing wholesale_price_history.csv
  - Recomputes best_historic_price.csv and buying_recommendations.csv

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
import pdfplumber

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent  # scrapers/
DATA_DIR = ROOT / "data"
INVOICE_DIR = DATA_DIR / "pharmacy_invoices"
INVOICE_DIR.mkdir(parents=True, exist_ok=True)

INVOICE_DATA_ROOT = Path.home() / "Documents" / "NPT_Invoice_Data" / "OneDrive_2026-04-12"
DRUG_TARIFF = DATA_DIR / "drug_tariff" / "drug_tariff_202603.csv"

PDF_PHARMACIES = {
    "Bessbrook Pharmacy": INVOICE_DATA_ROOT / "Bessbrook Pharmacy",
    "Lowwood Pharmacy": INVOICE_DATA_ROOT / "Lowwood Pharmacy",
    "McGregor Chemist": INVOICE_DATA_ROOT / "McGregor Chemist",
}

# Files/patterns to SKIP (not drug invoices)
SKIP_PATTERNS = [
    "power-invoice",
    "Statement",
    "Invoice_INV00054359",  # Belfast waste collection
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalise_drug_name(name: str) -> str:
    """Lowercase, strip trailing junk, extra whitespace."""
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    # Remove trailing (PO, (P), **UK PACK**, PILSCO, Licensed, FS, SF, etc.
    name = re.sub(r"\s*\(po\b.*$", "", name)
    name = re.sub(r"\s*\*+.*$", "", name)
    name = re.sub(r"\s+(pilsco|licensed|fs|sf)\s*$", "", name, flags=re.IGNORECASE)
    # Remove "pk: 28", "pk:112", "x 28" at end
    name = re.sub(r"\s*pk\s*:\s*\d+", "", name)
    name = re.sub(r"\s*x\s*\d+\s*$", "", name)
    name = name.strip()
    return name


def extract_base_molecule(name: str) -> str:
    """Extract base molecule name before strength. e.g. 'metformin 500mg' -> 'metformin'"""
    if not isinstance(name, str) or not name:
        return ""
    m = re.match(r"^([\w\-]+(?:\s[\w\-]+)?)\s+\d", name)
    if m:
        return m.group(1).strip()
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


def infer_month_from_folder(folder_name: str) -> pd.Timestamp:
    """Infer month from folder name like '2026-03 March' -> 2026-03-01."""
    m = re.match(r"(\d{4}-\d{2})", folder_name)
    if m:
        try:
            return pd.to_datetime(m.group(1) + "-01")
        except Exception:
            pass
    return pd.NaT


def should_skip_pdf(pdf_path: Path) -> bool:
    """Return True if this PDF is not a drug invoice."""
    name = pdf_path.name
    for pat in SKIP_PATTERNS:
        if pat.lower() in name.lower():
            return True
    return False


def despace_medhub(text: str) -> str:
    """Remove the character-level spacing in MedHub PDFs.
    E.g. 'A M I T R I P T Y L I N E T A B L E T S' -> 'AMITRIPTYLINE TABLETS'
    The pattern is: single chars separated by spaces, with word gaps as double+ spaces.
    """
    # Detect if text has the spaced pattern (majority of chars are single with space)
    # Replace sequences of "X " (single char + space) treating double+ space as word boundary
    # Split on 2+ spaces first (word boundaries), then de-space each word
    words = re.split(r'  +', text)
    result = []
    for word in words:
        # If word looks like spaced single chars: "A M I T R I P T Y L I N E"
        if len(word) > 2 and re.match(r'^[A-Za-z0-9/.%#\[\]áéí] (?:[A-Za-z0-9/.%#\[\]áéí] )*[A-Za-z0-9/.%#\[\]áéí]$', word):
            result.append(word.replace(' ', ''))
        else:
            result.append(word)
    return ' '.join(result)


# ══════════════════════════════════════════════════════════════════════════════
# PARSER: Ethigen format (i0189xxx.pdf, c000xxx.pdf)
# ══════════════════════════════════════════════════════════════════════════════

def parse_ethigen_pdf(pdf_path: Path, pharmacy: str, month: pd.Timestamp) -> list:
    """Parse Ethigen-format invoices. Lines: 'Drug Name Qty Rate Amount' then 'Commodity : ...'"""
    rows = []
    supplier = ""
    invoice_ref = ""
    invoice_date = month

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')

            # Extract header info from first page
            if page_idx == 0:
                # Supplier = first line
                if lines:
                    supplier = lines[0].strip().split(',')[0].strip()

                # Invoice ref
                for line in lines[:15]:
                    m = re.search(r'(I\d{9,}|C\d{9,})', line)
                    if m:
                        invoice_ref = m.group(1)
                        break

                # Tax Date
                for line in lines[:15]:
                    m = re.search(r'Tax Date:\s*(\d{2}/\d{2}/\d{2,4})', line)
                    if m:
                        try:
                            invoice_date = pd.to_datetime(m.group(1), dayfirst=True)
                        except Exception:
                            pass
                        break

            # Parse drug lines
            # Pattern: Description followed by numbers at end: Qty Rate Amount
            # Drug lines end with: int float float
            # But description is truncated so we can't rely on fixed columns
            for i, line in enumerate(lines):
                # Skip known non-drug lines
                if any(skip in line for skip in [
                    'Commodity :', 'Continued/', 'Description', 'Invoice to:',
                    'Total Number', 'VAT Summary', 'EORI', 'Incoterms',
                    'Net Weight', 'Gross Weight', 'Wholesale Dealers',
                    'Telephone:', 'INVOICE', 'CREDIT', 'Ref:', '(GBP)',
                    'Invoice Account', 'Tax Date:', 'Order Date:',
                    'BESSBROOK', 'LOWWOOD', 'MCGREGOR', 'FOY INC',
                    'CHARLEMONT', 'COUNTY DOWN', 'BT35', 'NEWRY',
                    'Ethigen', 'RRP', 'Sub Total', '@ 20.00', '@ 5.00', '@ 0.00',
                    'Total', 'am pm',
                ]):
                    continue

                # Match: Description ... Qty Rate Amount
                # Qty is integer, Rate and Amount are floats
                m = re.match(
                    r'^(.+?)\s+(\d+)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s*$',
                    line.strip()
                )
                if m:
                    drug_name = m.group(1).strip()
                    qty = int(m.group(2))
                    rate = float(m.group(3))
                    amount = float(m.group(4))

                    # Validate: amount should roughly equal qty * rate
                    expected = qty * rate
                    if abs(expected - amount) > 0.02:
                        # Sometimes the description eats into the numbers
                        # Try alternative: last 3 numbers
                        pass

                    if rate > 0 and qty > 0 and len(drug_name) > 3:
                        rows.append({
                            "drug_name": normalise_drug_name(drug_name),
                            "unit_price_gbp": rate,
                            "qty": qty,
                            "line_total": amount,
                            "pharmacy": pharmacy,
                            "supplier": supplier,
                            "invoice_date": invoice_date,
                            "month": month,
                            "invoice_ref": invoice_ref,
                            "source_pdf": pdf_path.name,
                        })

    return rows


# ══════════════════════════════════════════════════════════════════════════════
# PARSER: MedHub/Bestway format (010-SINV-xxx.pdf)
# Character-spaced text — collapse all spaces and parse numerics from the end
# using the constraint: supplied * price = total
# ══════════════════════════════════════════════════════════════════════════════

def _parse_medhub_numeric_tail(rest):
    """Parse (desc, supplied, price, total) from collapsed MedHub line tail.

    End structure: ...(pack)(supplied)(price)(disc)(A)(total)
    disc=0-9, A=1-9 (usually 0 and 1). Constraint: supplied * price ~= total.
    """
    candidates = []

    for tlen in range(4, min(9, len(rest) + 1)):
        ts = rest[-tlen:]
        parts = ts.split('.')
        if len(parts) != 2 or len(parts[1]) != 2 or not parts[0].isdigit():
            continue
        total = float(ts)
        if total <= 0:
            continue

        r1 = rest[:-tlen]
        if len(r1) < 4 or not r1[-1].isdigit() or not r1[-2].isdigit():
            continue
        r3 = r1[:-2]  # strip disc + A columns (2 digits)

        if len(r3) < 3:
            continue

        for plen in range(3, min(9, len(r3) + 1)):
            ps = r3[-plen:]
            if '.' not in ps:
                continue
            pp = ps.split('.')
            if len(pp) != 2 or len(pp[1]) not in (2, 3) or not pp[0].isdigit():
                continue
            price = float(ps)
            if price <= 0 or price > 500:
                continue

            r4 = r3[:-plen]
            if not r4:
                continue

            for slen in range(1, min(3, len(r4) + 1)):
                ss = r4[-slen:]
                if not ss.isdigit():
                    continue
                supplied = int(ss)
                if supplied < 1 or supplied > 50:
                    continue

                if abs(round(supplied * price, 2) - total) < 0.03:
                    desc = r4[:-slen]
                    candidates.append((desc, supplied, price, total))

    if not candidates:
        return None
    # Prefer highest total (consumes the most digits from numeric tail)
    candidates.sort(key=lambda x: x[3], reverse=True)
    return candidates[0]


def _clean_medhub_desc(collapsed_desc):
    """Clean a collapsed MedHub drug description back into readable form."""
    desc = collapsed_desc
    # Remove (A)/(B)/(C) order-key markers
    desc = re.sub(r'\([A-Z]\)', ' ', desc)
    # Remove [B] markers
    desc = re.sub(r'\[[A-Z]\]', '', desc)
    # Remove trailing lowercase manufacturer codes (acc, man, zen, tev, enn, fln, mec)
    desc = re.sub(r'[a-z]{2,3}$', '', desc).strip()
    # Remove trailing pack size (digits + optional unit letters like G, ML, MG)
    desc = re.sub(r'\d+[A-Z]{0,2}$', '', desc).strip()
    # Insert spaces at letter-digit and digit-letter transitions
    desc = re.sub(r'([A-Za-z])(\d)', r'\1 \2', desc)
    desc = re.sub(r'(\d)([A-Za-z])', r'\1 \2', desc)
    # Insert spaces before common dosage form words
    desc = re.sub(r'(TABLETS?|CAPS(?:ULES)?|CREAM|OINTM?(?:ENT)?|LOTION|SHAMPOO|GEL|SUSP(?:ENSION)?|SACHETS?|SOLUTION|DROPS|SPRAY|INHALER|FILM|SYRUP|INJECTION|TABS)', r' \1', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc


def parse_medhub_pdf(pdf_path: Path, pharmacy: str, month: pd.Timestamp) -> list:
    """Parse MedHub/Bestway invoices with character-spaced text."""
    rows = []
    supplier = "Bestway MedHub"
    invoice_ref = ""
    invoice_date = month

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')

            if not invoice_ref:
                m = re.search(r'SINV-(\d+)', pdf_path.name)
                if m:
                    invoice_ref = f"SINV-{m.group(1)}"

            if page_idx == 0:
                m = re.search(r'(\d{8})\.pdf', pdf_path.name)
                if m:
                    try:
                        invoice_date = pd.to_datetime(m.group(1), format='%Y%m%d')
                    except Exception:
                        pass

            for line in lines:
                # MedHub product lines start with 5-digit+letter code
                collapsed = line.replace(' ', '')
                m = re.match(r'^(\d{5}[A-Z])([A-Z]{1,2}\d+/\d+)(.*)', collapsed)
                if not m:
                    continue

                rest = m.group(3)
                if len(rest) < 8:  # too short to contain drug + price
                    continue

                result = _parse_medhub_numeric_tail(rest)
                if not result:
                    continue

                desc_raw, qty, unit_price, line_total = result
                drug_desc = _clean_medhub_desc(desc_raw)

                if unit_price > 0 and qty > 0 and len(drug_desc) > 3:
                    rows.append({
                        "drug_name": normalise_drug_name(drug_desc),
                        "unit_price_gbp": unit_price,
                        "qty": qty,
                        "line_total": line_total,
                        "pharmacy": pharmacy,
                        "supplier": supplier,
                        "invoice_date": invoice_date,
                        "month": month,
                        "invoice_ref": invoice_ref,
                        "source_pdf": pdf_path.name,
                    })

    return rows


# ══════════════════════════════════════════════════════════════════════════════
# PARSER: PHD/PIN credit notes (Credits For Acc - 0xxxx.pdf)
# ══════════════════════════════════════════════════════════════════════════════

def parse_phd_credit_pdf(pdf_path: Path, pharmacy: str, month: pd.Timestamp) -> list:
    """Parse PHD/PIN credit notes. Two line formats:

    Format A (EDN prefix):
      'EDN 8 RAMIPRIL CAPS 5MG PHD/EG 28 6611-354 0.00 0.690 1 M 5.52 59563641'
      Fields: EDN? qty DRUG_NAME PHD/EG pack PIP SRP TRADE 1 [key] TOTAL REF

    Format B (Mounjaro-style, PIP code prefix):
      '1 5402300 MOUNJARO 7.5MG 310326 - 05 0426 0000-000 0.00 206.550 1 206.55 W152...'
      Fields: qty PIP DRUG_NAME batch - expiry PIP2 SRP TRADE 1 TOTAL REF

    Format C (ABILIFY-style, no EDN, no PIP prefix):
      '1 ABILIFY MAINTENA INJ VIAL 400MG PI 1 6781-421* 0.00 219.290 1 219.29 59894975'
    """
    rows = []
    supplier = "PHD"
    invoice_ref = ""
    invoice_date = month

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')

            # Get date
            for line in lines[:20]:
                m = re.search(r'DATE\s+(\d{2}/\d{2}/\d{2,4})', line)
                if m:
                    try:
                        invoice_date = pd.to_datetime(m.group(1), dayfirst=True)
                    except Exception:
                        pass
                    break

            for line in lines:
                stripped = line.strip()

                # Skip non-product lines
                if any(skip in stripped for skip in [
                    'CREDIT NOTE', 'PRODUCT RECALL', 'PIP CODE',
                    'MULTIPLE BATCH', 'PLEASE SEE', 'GTIN',
                    'VAT Summary', 'Goods Total', 'VAT Total',
                    'Invoice Total', 'Please Remit', 'Registered Office',
                    'COMPANY REG', 'ORD QTY', 'PRODUCT DESCRIPTION',
                    'LOWWOOD', 'MCGREGOR', 'SHORE ROAD', 'BOTANIC',
                    'BELFAST', 'COUNTY ANTRIM', 'BT15', 'BT7', 'TEL:',
                    'ROUTE', 'SUPPLIED BY', 'DELIVERED BY', 'ORDER REF',
                    'HIBIWASH', '--------', '****',
                ]):
                    continue

                # Require a PIP-like code (digits-digits) somewhere in the line
                if not re.search(r'\d{4}-\d{3}', stripped):
                    continue

                # Format A: optional 'EDN' + qty + DRUG ... PHD/EG pack + PIP + 0.00 + price + 1 + [key] + total + ref
                m = re.match(
                    r'^(?:EDN\s+)?(\d+)\s+'           # qty
                    r'(?:\d{7}\s+)?'                    # optional 7-digit PIP prefix
                    r'(.+?)\s+'                         # drug name
                    r'\d{4}-\d{3}\*?\s+'                # PIP code (e.g. 6611-354)
                    r'\d+\.\d+\s+'                      # SRP (usually 0.00)
                    r'(\d+\.\d{2,3})\s+'                # TRADE price (unit price)
                    r'\d+\s+'                            # always 1
                    r'(?:[A-Z]\s+)?'                     # optional key letter (M, C, etc.)
                    r'(\d+\.\d{2})',                     # line total
                    stripped
                )
                if m:
                    qty = int(m.group(1))
                    drug_name = m.group(2).strip()
                    unit_price = float(m.group(3))
                    line_total = float(m.group(4))

                    # Clean drug name: remove PHD/EG + pack size at end
                    drug_name = re.sub(r'\s+PHD/\w+\s+\d+\w*\s*$', '', drug_name)
                    drug_name = re.sub(r'\s+PI\s+\d+\s*$', '', drug_name)
                    # Remove batch/expiry patterns
                    drug_name = re.sub(r'\s+\d{6}\s*-.*$', '', drug_name)

                    if unit_price > 0 and qty > 0 and len(drug_name) > 3:
                        rows.append({
                            "drug_name": normalise_drug_name(drug_name),
                            "unit_price_gbp": unit_price,
                            "qty": qty,
                            "line_total": line_total,
                            "pharmacy": pharmacy,
                            "supplier": supplier,
                            "invoice_date": invoice_date,
                            "month": month,
                            "invoice_ref": invoice_ref,
                            "source_pdf": pdf_path.name,
                        })
                    continue

                # Format B: Mounjaro-style with embedded date
                m2 = re.match(
                    r'^(\d+)\s+\d{7}\s+(.+?)\s+\d{6}\s*-.*?'
                    r'\d{4}-\d{3}\*?\s+'
                    r'\d+\.\d+\s+'
                    r'(\d+\.\d{2,3})\s+'
                    r'\d+\s+'
                    r'(\d+\.\d{2})',
                    stripped
                )
                if m2:
                    qty = int(m2.group(1))
                    drug_name = m2.group(2).strip()
                    unit_price = float(m2.group(3))
                    line_total = float(m2.group(4))

                    if unit_price > 0 and qty > 0 and len(drug_name) > 3:
                        rows.append({
                            "drug_name": normalise_drug_name(drug_name),
                            "unit_price_gbp": unit_price,
                            "qty": qty,
                            "line_total": line_total,
                            "pharmacy": pharmacy,
                            "supplier": supplier,
                            "invoice_date": invoice_date,
                            "month": month,
                            "invoice_ref": invoice_ref,
                            "source_pdf": pdf_path.name,
                        })

    return rows


# ══════════════════════════════════════════════════════════════════════════════
# PARSER: Abbott / specialty single-item invoices
# ══════════════════════════════════════════════════════════════════════════════

def parse_abbott_pdf(pdf_path: Path, pharmacy: str, month: pd.Timestamp) -> list:
    """Parse Abbott-style invoices with QUANTITY/DETAILS/UNIT PRICE/NET AMT format."""
    rows = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # Get supplier from first lines
            supplier = ""
            lines = text.split('\n')
            if lines:
                supplier = lines[0].strip()

            # Get invoice ref and date
            invoice_ref = ""
            invoice_date = month
            for line in lines[:20]:
                m = re.search(r'Invoice No[.\s]+(\d+)', line)
                if m:
                    invoice_ref = m.group(1)
                m = re.search(r'Invoice Date[.\s]+(\d{2}/\d{2}/\d{4})', line)
                if m:
                    try:
                        invoice_date = pd.to_datetime(m.group(1), dayfirst=True)
                    except Exception:
                        pass

            # Parse product lines: "QTY DESCRIPTION BATCH ORIGIN UNIT_PRICE NET_AMT VAT% VAT"
            # e.g. "12.00 FreeStyle Libre 2 Plus KTP014873 US 37.50 450.00 20 90.00"
            for line in lines:
                m = re.match(
                    r'^(\d+\.?\d*)\s+(.+?)\s+[A-Z0-9]{5,}\s+[A-Z]{2}\s+(\d+\.\d{2})\s+(\d+\.\d{2})',
                    line.strip()
                )
                if m:
                    qty = int(float(m.group(1)))
                    drug_name = m.group(2).strip()
                    unit_price = float(m.group(3))
                    net_amt = float(m.group(4))

                    # Remove " - Commodity Code:..." suffix
                    drug_name = re.sub(r'\s*-\s*Commodity.*$', '', drug_name)

                    if unit_price > 0 and qty > 0 and len(drug_name) > 3:
                        rows.append({
                            "drug_name": normalise_drug_name(drug_name),
                            "unit_price_gbp": unit_price,
                            "qty": qty,
                            "line_total": net_amt,
                            "pharmacy": pharmacy,
                            "supplier": supplier,
                            "invoice_date": invoice_date,
                            "month": month,
                            "invoice_ref": invoice_ref,
                            "source_pdf": pdf_path.name,
                        })

    return rows


# ══════════════════════════════════════════════════════════════════════════════
# PARSER: Sangers Surgical summary (just a delivery manifest, not line items)
# ══════════════════════════════════════════════════════════════════════════════

def is_sangers_surgical(pdf_path: Path) -> bool:
    """Detect Sangers Surgical delivery summaries (not parseable for drug lines)."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = pdf.pages[0].extract_text() or ""
            return "Sangers Surgical" in text or "Surgical Products" in text
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER: Detect format and dispatch to correct parser
# ══════════════════════════════════════════════════════════════════════════════

def detect_and_parse(pdf_path: Path, pharmacy: str, month: pd.Timestamp) -> list:
    """Detect invoice format and dispatch to appropriate parser."""
    name = pdf_path.name

    # Credit notes from PHD
    if name.lower().startswith("credits for acc"):
        return parse_phd_credit_pdf(pdf_path, pharmacy, month)

    # MedHub/Bestway invoices
    if name.startswith("010-SINV"):
        return parse_medhub_pdf(pdf_path, pharmacy, month)

    # Ethigen invoices (i0189xxx.pdf) or credit notes (c000xxx.pdf)
    if re.match(r'^[ic]\d{6,}', name):
        return parse_ethigen_pdf(pdf_path, pharmacy, month)

    # Abbott / specialty (numeric invoice number)
    if re.match(r'^\d{7}\.pdf$', name):
        # Could be Abbott or similar — try to detect
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = pdf.pages[0].extract_text() or ""
                if "ABBOTT" in text.upper():
                    return parse_abbott_pdf(pdf_path, pharmacy, month)
                # Other single-supplier invoices
                return parse_abbott_pdf(pdf_path, pharmacy, month)
        except Exception:
            return []

    # EMT Healthcare (packaging supplies — skip)
    if name.startswith("INV_"):
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = pdf.pages[0].extract_text() or ""
                if "EMT Healthcare" in text or "Prescriptions Bags" in text or "Counter Bags" in text:
                    return []  # Not drug invoices
        except Exception:
            pass

    # Sangers Surgical summaries — skip
    if is_sangers_surgical(pdf_path):
        return []

    # Fallback: try Ethigen parser (most common format)
    return parse_ethigen_pdf(pdf_path, pharmacy, month)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN: Parse all PDFs
# ══════════════════════════════════════════════════════════════════════════════

def parse_all_pdfs():
    """Walk all pharmacy folders and parse every PDF invoice."""
    print("=" * 70)
    print("  30_parse_all_invoices.py — Comprehensive PDF Invoice Parser")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    all_rows = []
    stats = {
        "pdfs_found": 0,
        "pdfs_parsed": 0,
        "pdfs_skipped": 0,
        "pdfs_empty": 0,
        "pdfs_error": 0,
        "lines_extracted": 0,
    }
    format_counts = {}

    for pharmacy_name, pharmacy_dir in PDF_PHARMACIES.items():
        if not pharmacy_dir.exists():
            print(f"\n  [WARN] Directory not found: {pharmacy_dir}")
            continue

        pdfs = sorted(pharmacy_dir.rglob("*.pdf"))
        print(f"\n  {pharmacy_name}: {len(pdfs)} PDFs found")
        stats["pdfs_found"] += len(pdfs)

        for pdf_path in pdfs:
            # Skip non-drug PDFs
            if should_skip_pdf(pdf_path):
                stats["pdfs_skipped"] += 1
                continue

            # Infer month from folder
            month = infer_month_from_folder(pdf_path.parent.name)

            try:
                rows = detect_and_parse(pdf_path, pharmacy_name, month)

                if rows:
                    all_rows.extend(rows)
                    stats["pdfs_parsed"] += 1
                    stats["lines_extracted"] += len(rows)

                    # Track format
                    fmt = rows[0].get("supplier", "unknown")
                    format_counts[fmt] = format_counts.get(fmt, 0) + len(rows)
                else:
                    stats["pdfs_empty"] += 1

            except Exception as e:
                stats["pdfs_error"] += 1
                if stats["pdfs_error"] <= 10:
                    print(f"    [ERROR] {pdf_path.name}: {e}")

    # Build DataFrame
    df = pd.DataFrame(all_rows)
    if df.empty:
        print("\n  [FATAL] No drug lines extracted from any PDF!")
        return df

    # Clean up
    df["drug_name"] = df["drug_name"].str.strip()
    df = df[df["drug_name"].str.len() > 2].copy()
    df = df[df["unit_price_gbp"] > 0].copy()

    # Save raw PDF extract
    out_path = INVOICE_DIR / "all_pdf_drug_lines.csv"
    df.to_csv(out_path, index=False)

    print(f"\n  {'─' * 50}")
    print(f"  EXTRACTION RESULTS")
    print(f"  {'─' * 50}")
    print(f"  PDFs found:      {stats['pdfs_found']}")
    print(f"  PDFs parsed:     {stats['pdfs_parsed']}")
    print(f"  PDFs skipped:    {stats['pdfs_skipped']} (non-drug)")
    print(f"  PDFs empty:      {stats['pdfs_empty']} (no lines found)")
    print(f"  PDFs errored:    {stats['pdfs_error']}")
    print(f"  Drug lines:      {stats['lines_extracted']}")
    print(f"  Unique drugs:    {df['drug_name'].nunique()}")
    print(f"  Pharmacies:      {df['pharmacy'].nunique()}")
    print(f"  Saved: {out_path}")

    print(f"\n  Lines by supplier:")
    for sup, count in sorted(format_counts.items(), key=lambda x: -x[1]):
        print(f"    {sup:30s}  {count:5d} lines")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# MERGE with existing wholesale_price_history.csv
# ══════════════════════════════════════════════════════════════════════════════

def merge_with_existing(pdf_df: pd.DataFrame):
    """Merge new PDF data with existing wholesale_price_history.csv."""
    print(f"\n{'=' * 70}")
    print("  MERGING WITH EXISTING WHOLESALE PRICE HISTORY")
    print("=" * 70)

    existing_path = INVOICE_DIR / "wholesale_price_history.csv"
    frames = []

    if existing_path.exists():
        existing = pd.read_csv(existing_path)
        # Remove old PDF-sourced rows (we're replacing them with better parsing)
        old_pdf = existing[existing["source"].str.startswith("pdf_")]
        non_pdf = existing[~existing["source"].str.startswith("pdf_")]
        print(f"  Existing non-PDF rows: {len(non_pdf)} (keeping)")
        print(f"  Existing old PDF rows: {len(old_pdf)} (replacing)")
        frames.append(non_pdf)
    else:
        print("  No existing wholesale_price_history.csv found")

    # Add new PDF data, mapping columns
    if not pdf_df.empty:
        new_rows = pd.DataFrame({
            "drug_name": pdf_df["drug_name"],
            "date": pdf_df["invoice_date"],
            "pharmacy": pdf_df["pharmacy"],
            "supplier": pdf_df["supplier"],
            "unit_price_gbp": pdf_df["unit_price_gbp"],
            "qty": pdf_df["qty"],
            "source": "pdf_parsed_v2",
        })
        frames.append(new_rows)
        print(f"  New PDF rows: {len(new_rows)}")

    if not frames:
        print("  [ERROR] No data to merge!")
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)
    merged = merged[merged["unit_price_gbp"] > 0].copy()
    merged["base_molecule"] = merged["drug_name"].apply(extract_base_molecule)
    merged = merged.sort_values(["drug_name", "date"]).reset_index(drop=True)

    merged.to_csv(existing_path, index=False)
    print(f"\n  MERGED TOTAL: {len(merged)} rows, {merged['drug_name'].nunique()} unique drugs")
    print(f"  Sources: {merged['source'].value_counts().to_dict()}")
    print(f"  Saved: {existing_path}")

    return merged


# ══════════════════════════════════════════════════════════════════════════════
# RECOMPUTE best_historic_price.csv (same logic as script 23 step5)
# ══════════════════════════════════════════════════════════════════════════════

def recompute_best_historic_price(price_history: pd.DataFrame):
    """Compute best, average, and current prices per drug."""
    print(f"\n{'=' * 70}")
    print("  RECOMPUTING BEST HISTORIC PRICE")
    print("=" * 70)

    if price_history.empty:
        return pd.DataFrame()

    # Ensure date column is proper datetime
    price_history["date"] = pd.to_datetime(price_history["date"], errors="coerce")

    drugs = price_history.groupby("drug_name").agg(
        best_historic_price=("unit_price_gbp", "min"),
        avg_historic_price=("unit_price_gbp", "mean"),
        max_historic_price=("unit_price_gbp", "max"),
        observation_count=("unit_price_gbp", "count"),
        first_seen=("date", "min"),
        last_seen=("date", "max"),
    ).reset_index()

    # Current price = most recent observation
    dated = price_history[price_history["date"].notna()].copy()
    recent = (dated
              .sort_values("date")
              .groupby("drug_name")
              .last()
              .reset_index()[["drug_name", "unit_price_gbp", "date", "supplier"]])
    recent.columns = ["drug_name", "current_price", "current_date", "current_supplier"]
    drugs = drugs.merge(recent, on="drug_name", how="left")

    # 3-month rolling average
    three_months_ago = pd.Timestamp.now() - pd.DateOffset(months=3)
    price_history["date"] = pd.to_datetime(price_history["date"], errors="coerce")
    recent_prices = (price_history[price_history["date"].notna() & (price_history["date"] >= three_months_ago)]
                     .groupby("drug_name")["unit_price_gbp"]
                     .mean()
                     .reset_index()
                     .rename(columns={"unit_price_gbp": "avg_price_3mo"}))
    drugs = drugs.merge(recent_prices, on="drug_name", how="left")

    # Price trend
    drugs["price_trend_pct"] = np.where(
        drugs["avg_price_3mo"].notna() & (drugs["avg_price_3mo"] > 0),
        ((drugs["current_price"] - drugs["avg_price_3mo"]) / drugs["avg_price_3mo"] * 100).round(1),
        np.nan
    )
    drugs["price_vs_best_pct"] = np.where(
        drugs["best_historic_price"] > 0,
        ((drugs["current_price"] - drugs["best_historic_price"]) / drugs["best_historic_price"] * 100).round(1),
        np.nan
    )
    drugs["base_molecule"] = drugs["drug_name"].apply(extract_base_molecule)

    out_path = INVOICE_DIR / "best_historic_price.csv"
    drugs.to_csv(out_path, index=False)
    print(f"  Drugs with pricing: {len(drugs)}")
    print(f"  Saved: {out_path}")
    return drugs


# ══════════════════════════════════════════════════════════════════════════════
# RECOMPUTE buying_recommendations.csv (same logic as script 23 step6)
# ══════════════════════════════════════════════════════════════════════════════

def recompute_buying_recommendations(best_prices: pd.DataFrame):
    """Generate buy/hold/bulk-buy recommendations."""
    print(f"\n{'=' * 70}")
    print("  RECOMPUTING BUYING RECOMMENDATIONS")
    print("=" * 70)

    if best_prices.empty:
        return pd.DataFrame()

    recs = best_prices.copy()

    # Recommendation logic (same as script 23)
    conditions = [
        recs["current_price"] <= recs["best_historic_price"] * 1.05,
        recs["current_price"] <= recs["avg_historic_price"],
        recs["current_price"] > recs["avg_historic_price"] * 1.20,
    ]
    choices = ["BULK BUY", "BUY AS YOU GO", "HOLD BUYING"]
    recs["recommendation"] = np.select(conditions, choices, default="BUY AS YOU GO")

    # Drug Tariff comparison
    recs["tariff_price_gbp"] = np.nan
    recs["price_vs_tariff_pct"] = np.nan
    recs["margin_gbp"] = np.nan

    if DRUG_TARIFF.exists():
        try:
            tariff = pd.read_csv(DRUG_TARIFF)
            tariff["tariff_gbp"] = tariff["Basic price"] / 100.0
            tariff["tariff_drug"] = tariff["Drug Name"].str.lower().str.strip()
            tariff["tariff_molecule"] = tariff["tariff_drug"].apply(extract_base_molecule)

            tariff_lookup = tariff.groupby("tariff_drug")["tariff_gbp"].first().to_dict()
            recs["tariff_price_gbp"] = recs["drug_name"].map(tariff_lookup)

            unmatched = recs["tariff_price_gbp"].isna()
            if unmatched.any():
                mol_tariff = tariff.groupby("tariff_molecule")["tariff_gbp"].median().to_dict()
                recs.loc[unmatched, "tariff_price_gbp"] = (
                    recs.loc[unmatched, "base_molecule"].map(mol_tariff)
                )

            has_tariff = recs["tariff_price_gbp"].notna() & (recs["tariff_price_gbp"] > 0)
            recs.loc[has_tariff, "price_vs_tariff_pct"] = (
                (recs.loc[has_tariff, "current_price"] / recs.loc[has_tariff, "tariff_price_gbp"] * 100 - 100).round(1)
            )
            recs.loc[has_tariff, "margin_gbp"] = (
                (recs.loc[has_tariff, "tariff_price_gbp"] - recs.loc[has_tariff, "current_price"]).round(2)
            )
            print(f"  Drug Tariff matches: {has_tariff.sum()}/{len(recs)}")
        except Exception as e:
            print(f"  [WARN] Drug Tariff comparison failed: {e}")

    # Sort
    rec_order = {"BULK BUY": 0, "HOLD BUYING": 1, "BUY AS YOU GO": 2}
    recs["_sort"] = recs["recommendation"].map(rec_order)
    recs = recs.sort_values(["_sort", "price_vs_best_pct"]).drop(columns="_sort")

    out_path = INVOICE_DIR / "buying_recommendations.csv"
    recs.to_csv(out_path, index=False)
    print(f"  Total recommendations: {len(recs)}")
    for rec_type in ["BULK BUY", "BUY AS YOU GO", "HOLD BUYING"]:
        count = (recs["recommendation"] == rec_type).sum()
        print(f"    {rec_type}: {count}")
    print(f"  Saved: {out_path}")
    return recs


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(pdf_df, merged_df, best_prices, recs):
    """Print coverage improvement summary."""
    print(f"\n{'=' * 70}")
    print("  FINAL SUMMARY")
    print("=" * 70)

    # Before vs after
    existing_path = INVOICE_DIR / "wholesale_price_history.csv"
    old_unique = 0
    if "source" in merged_df.columns:
        old_sources = merged_df[merged_df["source"] != "pdf_parsed_v2"]
        old_unique = old_sources["drug_name"].nunique()

    new_unique = merged_df["drug_name"].nunique() if not merged_df.empty else 0
    pdf_unique = pdf_df["drug_name"].nunique() if not pdf_df.empty else 0

    print(f"\n  COVERAGE IMPROVEMENT")
    print(f"  {'─' * 50}")
    print(f"  Old unique drugs (Victoria OS + training):  {old_unique}")
    print(f"  New PDF-parsed unique drugs:                {pdf_unique}")
    print(f"  TOTAL unique drugs now:                     {new_unique}")
    print(f"  Coverage increase:                          +{new_unique - old_unique} drugs")

    if not pdf_df.empty:
        print(f"\n  PDF PARSING BREAKDOWN")
        print(f"  {'─' * 50}")
        print(f"  Total drug lines from PDFs:    {len(pdf_df)}")
        print(f"  By pharmacy:")
        for pharm, count in pdf_df["pharmacy"].value_counts().items():
            n_drugs = pdf_df[pdf_df["pharmacy"] == pharm]["drug_name"].nunique()
            print(f"    {pharm:30s}  {count:5d} lines  ({n_drugs} unique drugs)")
        print(f"  By supplier:")
        for sup, count in pdf_df["supplier"].value_counts().items():
            print(f"    {sup:30s}  {count:5d} lines")

    if not recs.empty:
        print(f"\n  RECOMMENDATIONS")
        print(f"  {'─' * 50}")
        for rec_type in ["BULK BUY", "HOLD BUYING", "BUY AS YOU GO"]:
            count = (recs["recommendation"] == rec_type).sum()
            print(f"    {rec_type}: {count}")

    print(f"\n  OUTPUT FILES")
    print(f"  {'─' * 50}")
    for f in sorted(INVOICE_DIR.glob("*.csv")):
        size_kb = f.stat().st_size / 1024
        print(f"    {f.name:45s}  ({size_kb:.1f} KB)")

    print(f"\n{'=' * 70}")
    print("  Pipeline complete!")
    print("=" * 70)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Step 1: Parse all PDFs
    pdf_df = parse_all_pdfs()

    if pdf_df.empty:
        print("\n[FATAL] No data extracted. Exiting.")
        return

    # Step 2: Merge with existing price history
    merged_df = merge_with_existing(pdf_df)

    # Step 3: Recompute best historic price
    best_prices = recompute_best_historic_price(merged_df)

    # Step 4: Recompute buying recommendations
    recs = recompute_buying_recommendations(best_prices)

    # Step 5: Print summary
    print_summary(pdf_df, merged_df, best_prices, recs)


if __name__ == "__main__":
    main()
