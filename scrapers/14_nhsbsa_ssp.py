"""
SCRIPT 14: NHSBSA SSP Register — Serious Shortage Protocols
============================================================
Scrapes the active SSP register from NHSBSA. An SSP is issued when
a medicine is in such short supply that pharmacists are authorised
to dispense a therapeutic substitute. This is the STRONGEST shortage
signal available — it means a shortage is confirmed and severe enough
for NHS intervention.

Source: https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/serious-shortage-protocols-ssps

Outputs:
  data/ssp/ssp_active.csv     — currently active SSPs
  data/ssp/ssp_all.csv        — all SSPs including expired
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os, re
from datetime import datetime

OUT_DIR = "data/ssp"
os.makedirs(OUT_DIR, exist_ok=True)

SSP_URL = "https://www.nhsbsa.nhs.uk/pharmacies-gp-practices-and-appliance-contractors/serious-shortage-protocols-ssps"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NiPharm-Research/1.0)"}


def fetch_ssp_page() -> BeautifulSoup:
    r = requests.get(SSP_URL, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} from NHSBSA SSP page")
    return BeautifulSoup(r.text, "html.parser")


def parse_ssp_table(soup: BeautifulSoup) -> pd.DataFrame:
    """Parse SSP tables from the NHSBSA page."""
    records = []

    # Try to find tables
    tables = soup.find_all("table")
    if tables:
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            for row in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if cells:
                    record = dict(zip(headers, cells)) if headers else {"raw": " | ".join(cells)}
                    records.append(record)
        if records:
            return pd.DataFrame(records)

    # Fallback: parse list items / text blocks
    content = soup.find("main") or soup.find("article") or soup.body
    if not content:
        return pd.DataFrame()

    # Look for drug names in SSP context
    text_blocks = content.find_all(["li", "p", "td"])
    for block in text_blocks:
        text = block.get_text(strip=True)
        # SSP entries often mention drug name + SSP number
        ssp_match = re.search(r'SSP[\s\-]?(\d+)', text, re.IGNORECASE)
        if ssp_match or "shortage" in text.lower():
            records.append({
                "raw_text": text,
                "ssp_number": ssp_match.group(0) if ssp_match else "",
                "scraped_at": datetime.now().strftime("%Y-%m-%d"),
            })

    return pd.DataFrame(records) if records else pd.DataFrame()


def run():
    print("=" * 65)
    print("SCRIPT 14: NHSBSA SSP Register")
    print("=" * 65)

    try:
        soup = fetch_ssp_page()
        print(f"Page fetched: {len(soup.get_text()):,} chars")

        df = parse_ssp_table(soup)

        if df.empty:
            print("WARNING: No structured SSP data found — page may have changed format.")
            # Save raw HTML for manual inspection
            with open(f"{OUT_DIR}/ssp_page_raw.html", "w") as f:
                f.write(str(soup))
            print(f"Raw HTML saved: {OUT_DIR}/ssp_page_raw.html")

            # Try to find any CSV/Excel links on the page
            links = soup.find_all("a", href=True)
            data_links = [a["href"] for a in links if any(
                ext in a["href"].lower() for ext in [".csv", ".xlsx", ".xls", "download"]
            )]
            if data_links:
                print(f"Data download links found: {data_links[:5]}")
            return pd.DataFrame()

        df["scraped_at"] = datetime.now().strftime("%Y-%m-%d")

        # Try to identify active vs expired
        if "status" in df.columns:
            active = df[df["status"].str.lower().str.contains("active|current", na=False)]
        else:
            active = df

        active.to_csv(f"{OUT_DIR}/ssp_active.csv", index=False)
        df.to_csv(f"{OUT_DIR}/ssp_all.csv", index=False)

        print(f"Total SSPs found : {len(df)}")
        print(f"Active SSPs      : {len(active)}")
        print(f"Saved: {OUT_DIR}/ssp_active.csv")

        if len(active):
            print("\nActive SSPs:")
            print(active.head(20).to_string(index=False))

        return active

    except Exception as e:
        print(f"ERROR: {e}")
        print("The SSP page may have moved. Check: https://www.nhsbsa.nhs.uk and search 'SSP'")
        return pd.DataFrame()


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run()
