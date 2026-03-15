"""
SCRAPER 04: MHRA Drug Shortage Notices & Serious Shortage Protocols (SSPs)
===========================================================================
Sources:
  A) MHRA Serious Shortage Protocols — GOV.UK structured data
     https://www.gov.uk/government/publications/serious-shortage-protocols-ssps
  B) MHRA Drug Safety Updates — RSS feed
     https://www.gov.uk/drug-safety-update.atom
  C) GOV.UK API — drug shortage publications
     https://www.gov.uk/api/search.json?filter_organisations=medicines-and-healthcare-products-regulatory-agency&filter_topics=drug-shortages

Data:    Official shortage declarations, SSPs issued, expected resolutions
Use:     Ground-truth shortage labels + supply disruption signal
Freq:    Ad hoc (published when issued by MHRA)
"""

import requests
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

OUTPUT_DIR = "data/mhra"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NPTResearchBot/1.0)"}

# ── METHOD A: Scrape MHRA SSP page ───────────────────────────────────────────
def scrape_mhra_ssps() -> pd.DataFrame:
    """
    Scrape the GOV.UK Serious Shortage Protocols page.
    Returns: drug_name, bnf_code, ssp_number, issue_date, status, url
    """
    url = "https://www.gov.uk/government/publications/serious-shortage-protocols-ssps"
    print(f"  Fetching MHRA SSPs: {url}")

    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")

    records = []
    # GOV.UK SSP page lists each SSP as a document attachment
    for doc in soup.find_all("section", class_="attachment"):
        title_el = doc.find(["h2", "h3", "h4", "a"])
        title = title_el.get_text(strip=True) if title_el else ""

        # Extract drug name from title (pattern: "SSP XXX: Drug Name Strength Form")
        drug_match = re.search(r"SSP\s*\d+[A-Z]?:\s*(.+)", title)
        drug_name = drug_match.group(1).strip() if drug_match else title

        # Extract SSP number
        ssp_match = re.search(r"SSP\s*(\d+[A-Z]?)", title, re.IGNORECASE)
        ssp_number = ssp_match.group(1) if ssp_match else ""

        # Extract date if shown
        date_el = doc.find("time")
        issue_date = date_el.get("datetime", "") if date_el else ""

        # Get PDF link
        link_el = doc.find("a", href=True)
        link = link_el["href"] if link_el else ""
        if link and not link.startswith("http"):
            link = "https://www.gov.uk" + link

        if title:
            records.append({
                "ssp_number":    ssp_number,
                "drug_name":     drug_name,
                "issue_date":    issue_date,
                "status":        "ACTIVE",  # All listed SSPs are active
                "source_url":    link,
                "is_ssp":        1,
            })

    # Also try the attachments in a different format
    if not records:
        for link_el in soup.find_all("a", href=True):
            if "ssp" in link_el.get("href", "").lower() or "serious-shortage" in link_el.get("href", "").lower():
                records.append({
                    "drug_name":  link_el.get_text(strip=True),
                    "source_url": "https://www.gov.uk" + link_el["href"] if not link_el["href"].startswith("http") else link_el["href"],
                    "is_ssp": 1,
                })

    df = pd.DataFrame(records)
    print(f"  Found {len(df)} SSPs")
    return df

# ── METHOD B: MHRA Drug Safety Update Atom/RSS Feed ──────────────────────────
def fetch_mhra_rss_feed() -> pd.DataFrame:
    """
    Fetch MHRA Drug Safety Update RSS feed — catches shortage-related alerts
    before they become formal SSPs.
    """
    # Multiple RSS feeds to check
    feed_urls = [
        "https://www.gov.uk/drug-safety-update.atom",
        "https://www.gov.uk/drug-device-alerts.atom",
        "https://www.gov.uk/medicines-medical-devices-safety-updates.atom",
    ]

    records = []
    for feed_url in feed_urls:
        print(f"  Fetching RSS: {feed_url}")
        try:
            r = requests.get(feed_url, timeout=30, headers=HEADERS)
            if r.status_code != 200:
                continue

            # Parse Atom XML
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(r.content)

            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                published = entry.findtext("atom:published", "", ns)
                summary = entry.findtext("atom:summary", "", ns)

                # Flag shortage-related entries
                shortage_keywords = ["shortage", "supply", "unavailable", "concession", "SSP", "stock"]
                is_shortage = any(kw.lower() in title.lower() or kw.lower() in summary.lower()
                                  for kw in shortage_keywords)

                records.append({
                    "title":        title,
                    "url":          link,
                    "published":    published[:10] if published else "",
                    "summary":      summary[:300] if summary else "",
                    "is_shortage_related": int(is_shortage),
                    "feed":         feed_url,
                })

        except Exception as e:
            print(f"  ERROR parsing {feed_url}: {e}")

    df = pd.DataFrame(records)
    print(f"  Total MHRA alerts fetched: {len(df)}")
    shortage_alerts = df[df["is_shortage_related"] == 1]
    print(f"  Shortage-related alerts: {len(shortage_alerts)}")
    return df

# ── METHOD C: GOV.UK Content API ─────────────────────────────────────────────
def fetch_govuk_shortage_publications() -> pd.DataFrame:
    """
    Use GOV.UK content search API to find all MHRA shortage publications.
    No API key required. Returns paginated JSON.
    """
    base_url = "https://www.gov.uk/api/search.json"
    params = {
        "filter_organisations": "medicines-and-healthcare-products-regulatory-agency",
        "q": "medicine shortage supply",
        "fields[]": ["title", "link", "public_timestamp", "description"],
        "count": 100,
        "start": 0,
    }

    records = []
    page = 0
    while True:
        params["start"] = page * 100
        r = requests.get(base_url, params=params, timeout=30, headers=HEADERS)
        if r.status_code != 200:
            break

        data = r.json()
        results = data.get("results", [])
        if not results:
            break

        for item in results:
            records.append({
                "title":       item.get("title", ""),
                "url":         "https://www.gov.uk" + item.get("link", ""),
                "published":   item.get("public_timestamp", "")[:10],
                "description": item.get("description", ""),
            })

        if len(results) < 100:
            break
        page += 1

    df = pd.DataFrame(records)
    print(f"  GOV.UK API: found {len(df)} MHRA publications")
    return df

def run():
    print("=" * 60)
    print("MHRA Shortage Alerts & SSP Scraper")
    print("=" * 60)

    try:
        print("\n[METHOD A] Scraping MHRA SSP page:")
        df_ssp = scrape_mhra_ssps()
        if not df_ssp.empty:
            df_ssp.to_csv(f"{OUTPUT_DIR}/ssps.csv", index=False)
            print(f"  Saved {len(df_ssp)} SSPs to {OUTPUT_DIR}/ssps.csv")
    except Exception as e:
        print(f"  ERROR: {e}")
        df_ssp = pd.DataFrame()

    try:
        print("\n[METHOD B] Fetching MHRA RSS feeds:")
        df_rss = fetch_mhra_rss_feed()
        if not df_rss.empty:
            df_rss.to_csv(f"{OUTPUT_DIR}/mhra_rss_alerts.csv", index=False)
            # Show recent shortage alerts
            shortage = df_rss[df_rss["is_shortage_related"] == 1].sort_values("published", ascending=False)
            print(f"\n  Recent shortage-related MHRA alerts:")
            print(shortage[["published", "title"]].head(10).to_string(index=False))
    except Exception as e:
        print(f"  ERROR: {e}")
        df_rss = pd.DataFrame()

    try:
        print("\n[METHOD C] GOV.UK Content API:")
        df_gov = fetch_govuk_shortage_publications()
        if not df_gov.empty:
            df_gov.to_csv(f"{OUTPUT_DIR}/govuk_shortage_publications.csv", index=False)
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[DONE] MHRA data collection complete")

if __name__ == "__main__":
    run()
