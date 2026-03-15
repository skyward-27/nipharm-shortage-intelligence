"""
SCRAPER 08: CPE Historical Price Concessions Archive
=====================================================
Source:  https://cpe.org.uk/funding-and-reimbursement/reimbursement/price-concessions/
         (current month + links to all previous months)
Data:    All price concessions back to ~2019 — one table per month
Use:     ML training labels — every concession event = is_shortage=1
Freq:    Run once to build history; then run monthly (scraper 02 gets current month)

Note:    The CPE page lists the current month's concessions plus a dropdown/links
         to previous months. This scraper crawls all available archive months.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime

OUTPUT_DIR = "data/concessions"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NPTResearchBot/1.0)"}
BASE_URL = "https://cpe.org.uk"
CONCESSIONS_URL = f"{BASE_URL}/funding-and-reimbursement/reimbursement/price-concessions/"


def get_archive_month_links() -> list:
    """
    Scrape the CPE price concessions page for links to all historical months.
    Returns list of dicts: {month_label, url}
    """
    r = requests.get(CONCESSIONS_URL, timeout=30, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")

    links = []

    # Method 1: Look for select/option dropdowns (common on CPE)
    for sel in soup.find_all("select"):
        for opt in sel.find_all("option"):
            val = opt.get("value", "")
            label = opt.get_text(strip=True)
            if val and val != "#" and ("concession" in val.lower() or "price" in val.lower() or
                                        re.search(r'\d{4}', label)):
                full = val if val.startswith("http") else BASE_URL + val
                links.append({"month_label": label, "url": full})

    # Method 2: Look for explicit month links in page body
    month_pattern = re.compile(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}', re.IGNORECASE)
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if month_pattern.search(text) and ("concession" in href.lower() or "concession" in text.lower() or
                                            "price" in text.lower()):
            full = href if href.startswith("http") else BASE_URL + href
            if full not in [l["url"] for l in links]:
                links.append({"month_label": text, "url": full})

    # Method 3: Look for accordion/tab sections with month headings
    for heading in soup.find_all(["h2", "h3", "h4", "button", "summary"]):
        text = heading.get_text(strip=True)
        if month_pattern.search(text):
            # Find nearest link
            parent = heading.find_parent()
            if parent:
                a = parent.find("a", href=True)
                if a:
                    full = a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
                    if full not in [l["url"] for l in links]:
                        links.append({"month_label": text, "url": full})

    # Always include current page as current month
    links.insert(0, {"month_label": f"Current ({datetime.now().strftime('%B %Y')})", "url": CONCESSIONS_URL})

    print(f"  Found {len(links)} month archive links")
    return links


def scrape_concessions_page(url: str, month_label: str) -> pd.DataFrame:
    """
    Scrape a single CPE concessions page for the drug table.
    Returns DataFrame with: drug_name, pack_size, concession_price_p, month
    """
    r = requests.get(url, timeout=30, headers=HEADERS)
    if r.status_code != 200:
        return pd.DataFrame()

    soup = BeautifulSoup(r.content, "lxml")
    tables = soup.find_all("table")

    if not tables:
        return pd.DataFrame()

    # Take the table with most rows
    table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = table.find_all("tr")
    if not rows:
        return pd.DataFrame()

    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    data = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if cells:
            data.append(dict(zip(headers, cells)))

    df = pd.DataFrame(data)
    if df.empty:
        return df

    # Standardise columns
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rename_map = {
        "drug":             "drug_name",
        "pack_size":        "pack_size",
        "price_concession": "concession_price_p",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Parse month from label (e.g. "March 2026" → "2026-03")
    month_match = re.search(
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
        month_label, re.IGNORECASE
    )
    if month_match:
        month_str = datetime.strptime(f"{month_match.group(1)} {month_match.group(2)}", "%B %Y").strftime("%Y-%m")
    else:
        month_str = datetime.now().strftime("%Y-%m")

    df["month"]      = month_str
    df["source"]     = "CPE_archive"
    df["is_shortage"] = 1

    return df


def run():
    print("=" * 60)
    print("CPE Historical Price Concessions Scraper")
    print("=" * 60)

    print("\n[1] Finding archive month links on CPE page...")
    try:
        month_links = get_archive_month_links()
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    all_dfs = []
    print(f"\n[2] Scraping {len(month_links)} months...")

    for link in month_links:
        label = link["month_label"]
        url   = link["url"]
        try:
            df = scrape_concessions_page(url, label)
            if not df.empty:
                all_dfs.append(df)
                print(f"  ✅ {label:40s} — {len(df):3d} concessions")
            else:
                print(f"  ⚠️  {label:40s} — no table found")
        except Exception as e:
            print(f"  ❌ {label:40s} — {e}")

    if not all_dfs:
        print("\nERROR: No historical concession data found.")
        print("Tip: CPE may use JavaScript to load archive data.")
        print("     If so, download PDFs manually from CPE or use NHSBSA OpenPrescribing as backup.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["drug_name", "pack_size", "month"])
    combined = combined.sort_values(["month", "drug_name"])

    out_path = f"{OUTPUT_DIR}/cpe_historical_concessions.csv"
    combined.to_csv(out_path, index=False)

    print(f"\n[3] Saved {len(combined):,} concession records to: {out_path}")
    print(f"    Date range: {combined['month'].min()} → {combined['month'].max()}")
    print(f"    Unique drugs: {combined['drug_name'].nunique()}")
    print(f"    Months covered: {combined['month'].nunique()}")


if __name__ == "__main__":
    run()
