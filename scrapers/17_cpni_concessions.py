"""
17_cpni_concessions.py — Community Pharmacy NI Concessionary Prices
====================================================================
NI applies the same concession prices as England (set by DH England / CPE).
The BSO (Business Services Organisation) publishes them at:
  https://bso.hscni.net/.../concessionary-prices/

This scraper:
1. Scrapes the BSO concessionary prices page for the current month's data
2. Also checks the archive page for historical months
3. Saves to scrapers/data/concessions/cpni_concessions.csv

Output columns: month, drug_name, pack_size, concessionary_price_pence, source_url

NOTE: This script is safe to commit to GitHub. The output CSV is also fine to commit.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
from datetime import datetime
from urllib.parse import urljoin
from typing import Optional, List, Dict

BASE_URL = "https://bso.hscni.net"
CONCESSIONS_URL = (
    "https://bso.hscni.net/directorates/operations/family-practitioner-services/"
    "pharmacy/contractor-information/drug-tariff-and-related-materials/concessionary-prices/"
)
ARCHIVE_URL = (
    "https://bso.hscni.net/directorates/operations/family-practitioner-services/"
    "pharmacy/contractor-information/drug-tariff-and-related-materials/concessionary-prices/"
    "concessionary-prices-archive/"
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "concessions")
OUT_FILE = os.path.join(OUT_DIR, "cpni_concessions.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def parse_month_label(text: str) -> str:
    """Convert 'March 2026' or 'March-2026' → '2026-03'."""
    text = text.strip().replace("-", " ")
    for fmt in ("%B %Y", "%b %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return text


def scrape_inline_table(soup: BeautifulSoup, month_label: str, source_url: str) -> List[Dict]:
    """Extract rows from an HTML table of concession prices."""
    records = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        # Expect columns like: drug name, pack size, price
        if not any(k in " ".join(headers) for k in ["drug", "product", "price", "pack"]):
            continue
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            record = {
                "month": month_label,
                "source": "BSO NI",
                "source_url": source_url,
            }
            # Map cells to fields based on header position
            for i, h in enumerate(headers):
                if i >= len(cells):
                    break
                if any(k in h for k in ["drug", "product", "medicine", "name"]):
                    record["drug_name"] = cells[i]
                elif any(k in h for k in ["pack", "size", "quantity"]):
                    record["pack_size"] = cells[i]
                elif any(k in h for k in ["price", "concession", "£", "pence", "p"]):
                    # Normalise to pence
                    raw = cells[i].replace("£", "").replace("p", "").strip()
                    try:
                        val = float(raw)
                        # If it looks like pounds (< 500), convert to pence
                        record["concessionary_price_pence"] = int(val * 100) if val < 500 else int(val)
                    except ValueError:
                        record["concessionary_price_pence"] = None
                        record["price_raw"] = cells[i]
            if "drug_name" in record and record.get("drug_name"):
                records.append(record)
    return records


def find_pdf_links(soup: BeautifulSoup, base_url: str) -> List[tuple]:
    """Return (label, absolute_url) for all PDF links on page."""
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            label = a.get_text(strip=True) or href.split("/")[-1]
            pdfs.append((label, urljoin(base_url, href)))
    return pdfs


def download_pdf_as_text(pdf_url: str) -> Optional[str]:
    """Download a PDF and extract text using pdfplumber if available."""
    try:
        import pdfplumber
        import io
        r = requests.get(pdf_url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        print("  pdfplumber not installed — PDF text extraction skipped")
        return None
    except Exception as e:
        print(f"  ERROR reading PDF {pdf_url}: {e}")
        return None


def parse_pdf_text(text: str, month_label: str, source_url: str) -> List[Dict]:
    """Parse concession price rows from extracted PDF text."""
    records = []
    lines = text.splitlines()
    # Look for lines matching: DRUG NAME  PACK_SIZE  PRICE pattern
    price_re = re.compile(r"(.+?)\s{2,}(\d+\s*(?:tab|cap|ml|g|mg|mcg)[^\s]*)\s{2,}([£\d][\d.]+p?)", re.IGNORECASE)
    simple_re = re.compile(r"(.+?)\s{2,}([£\d][\d.]+(?:p)?)\s*$")

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        m = price_re.match(line)
        if m:
            drug, pack, price_raw = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        else:
            m = simple_re.match(line)
            if m:
                drug, pack, price_raw = m.group(1).strip(), "", m.group(2).strip()
            else:
                continue

        # Parse price
        raw = price_raw.replace("£", "").replace("p", "").strip()
        try:
            val = float(raw)
            price_pence = int(val * 100) if val < 500 else int(val)
        except ValueError:
            price_pence = None

        records.append({
            "month": month_label,
            "drug_name": drug,
            "pack_size": pack,
            "concessionary_price_pence": price_pence,
            "price_raw": price_raw,
            "source": "BSO NI",
            "source_url": source_url,
        })
    return records


def scrape_bso_page(url: str, is_archive: bool = False) -> List[Dict]:
    print(f"Fetching: {url}")
    soup = fetch_page(url)
    if not soup:
        return []

    all_records = []

    # First try inline HTML tables (BSO sometimes uses these)
    month_label = datetime.now().strftime("%Y-%m") if not is_archive else "archive"
    records = scrape_inline_table(soup, month_label, url)
    if records:
        print(f"  Found {len(records)} rows in HTML table")
        all_records.extend(records)

    # Find PDF links
    pdfs = find_pdf_links(soup, url)
    print(f"  Found {len(pdfs)} PDF links")

    for label, pdf_url in pdfs:
        # Infer month from label or URL
        month_match = re.search(
            r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
            r"[\s\-_]*(20\d\d)",
            label + " " + pdf_url, re.IGNORECASE
        )
        if month_match:
            month_label = parse_month_label(f"{month_match.group(1)} {month_match.group(2)}")
        else:
            month_label = datetime.now().strftime("%Y-%m")

        print(f"  PDF [{month_label}]: {label} → {pdf_url}")
        text = download_pdf_as_text(pdf_url)
        if text:
            rows = parse_pdf_text(text, month_label, pdf_url)
            print(f"    Parsed {len(rows)} rows from PDF")
            all_records.extend(rows)
        else:
            # Save a placeholder so we know the PDF exists
            all_records.append({
                "month": month_label,
                "drug_name": f"[PDF not parsed — {label}]",
                "pack_size": "",
                "concessionary_price_pence": None,
                "price_raw": "",
                "source": "BSO NI",
                "source_url": pdf_url,
            })

    # Also look for embedded links to sub-pages (archive months)
    if is_archive:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if not href.lower().endswith(".pdf") and "concessionary" in href.lower():
                sub_url = urljoin(BASE_URL, href)
                if sub_url != url:
                    print(f"  Sub-page: {text} → {sub_url}")
                    sub_records = scrape_bso_page(sub_url, is_archive=False)
                    # Try to infer month from anchor text
                    month_match = re.search(
                        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
                        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
                        r"[\s\-_]*(20\d\d)",
                        text, re.IGNORECASE
                    )
                    if month_match:
                        inferred = parse_month_label(f"{month_match.group(1)} {month_match.group(2)}")
                        for rec in sub_records:
                            if rec.get("month") == datetime.now().strftime("%Y-%m"):
                                rec["month"] = inferred
                    all_records.extend(sub_records)

    return all_records


def run():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    print("17_cpni_concessions.py — BSO NI Concessionary Prices")
    print("=" * 60)
    print()
    print("NOTE: NI applies the same concessions as England (CPE/DH England).")
    print("This script scrapes the BSO publication for NI confirmation + archive.")
    print()

    all_records = []

    # Current month
    print("--- Current month ---")
    all_records.extend(scrape_bso_page(CONCESSIONS_URL, is_archive=False))

    # Archive
    print()
    print("--- Archive ---")
    all_records.extend(scrape_bso_page(ARCHIVE_URL, is_archive=True))

    if not all_records:
        print("\nNo records extracted. BSO may have changed page structure.")
        print("Manual check: https://bso.hscni.net → Drug Tariff → Concessionary Prices")
        return

    df = pd.DataFrame(all_records)
    # Deduplicate
    df = df.drop_duplicates(subset=["month", "drug_name", "pack_size"])
    df = df.sort_values(["month", "drug_name"])

    df.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(df)} rows → {OUT_FILE}")

    # Cross-reference with CPE England data
    cpe_file = os.path.join(OUT_DIR, "cpe_archive_full.xlsx")
    if os.path.exists(cpe_file):
        try:
            cpe = pd.read_excel(cpe_file)
            ni_drugs = set(df["drug_name"].str.upper().str.strip())
            cpe_drugs = set(cpe.iloc[:, 0].astype(str).str.upper().str.strip())
            ni_only = ni_drugs - cpe_drugs
            print(f"\nCross-reference: {len(ni_only)} drugs in BSO NI not matched in CPE England")
            if ni_only:
                print("  NI-only drugs:", list(ni_only)[:10])
        except Exception as e:
            print(f"  (Cross-reference skipped: {e})")

    print("\nDone.")


if __name__ == "__main__":
    run()
