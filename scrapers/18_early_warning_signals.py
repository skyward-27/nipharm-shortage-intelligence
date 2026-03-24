"""
Script 18: Early Warning Signals — Multi-Source Lead Indicator Scraper
=======================================================================
Sources (all free, no auth required):
  1. GOV.UK MHRA Atom feed       → 4-6 week lead time before concession
  2. FDA Warning Letters RSS      → 6-8 week lead time (API manufacturer GMP)
  3. CPE shortage news feed       → 1-2 week lead time
  4. MIMS drug shortages page     → 2-4 week lead time

Output:
  data/early_warning/govuk_mhra_alerts.csv
  data/early_warning/fda_warning_letters.csv
  data/early_warning/cpe_shortage_news.csv
  data/early_warning/early_warning_features.csv  ← joined drug-level features
"""

import pathlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

HERE = pathlib.Path(__file__).parent
OUT  = HERE / "data" / "early_warning"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "NPT-Stock-Intelligence/1.0 (NHS pharmacy shortage research)"}

# ── Load molecule master for drug name matching ────────────────────────────
MOL_PATH = HERE / "data" / "molecule_master" / "molecule_master.csv"
PRED_PATH = HERE / "data" / "model" / "panel_predictions.csv"

def load_drug_names() -> list[str]:
    names = []
    if PRED_PATH.exists():
        df = pd.read_csv(PRED_PATH)
        names = df["drug_name"].dropna().str.lower().tolist()
    return names

def drug_name_in_text(text: str, drug_names: list[str]) -> list[str]:
    """Return drug names that appear in text (fuzzy word-boundary match)."""
    text_lower = text.lower()
    matched = []
    for name in drug_names:
        # match on first word of drug name (e.g. "olanzapine" in "olanzapine 10mg")
        keyword = name.split()[0] if name else ""
        if keyword and len(keyword) > 4 and keyword in text_lower:
            matched.append(name)
    return list(set(matched))


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 1: GOV.UK MHRA Atom Feed
# ══════════════════════════════════════════════════════════════════════════

def scrape_govuk_mhra_alerts(drug_names: list[str]) -> pd.DataFrame:
    """
    Parse GOV.UK MHRA Atom feeds for medicine supply shortage publications.
    Lead time: 4-6 weeks before CPE concession.
    """
    feeds = [
        "https://www.gov.uk/drug-device-alerts.atom",
        "https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency.atom",
        "https://mhrainspectorate.blog.gov.uk/feed/",   # GMP inspection failures (4-16wk lead)
        "https://cpe.org.uk/feed/",                     # CPE concession announcements (RSS)
    ]
    records = []
    shortage_keywords = [
        "shortage", "supply", "discontinu", "withdrawn", "unavailable",
        "recall", "concession", "stock", "out of stock"
    ]

    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)
            print(f"  {feed_url.split('/')[-1]}: {len(entries)} entries")

            for entry in entries:
                title   = (entry.findtext("atom:title",   "", ns) or "").strip()
                summary = (entry.findtext("atom:summary", "", ns) or "").strip()
                updated = (entry.findtext("atom:updated", "", ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link    = link_el.get("href", "") if link_el is not None else ""

                combined = (title + " " + summary).lower()

                # filter: must mention a shortage/supply keyword
                if not any(kw in combined for kw in shortage_keywords):
                    continue

                # match against our drug watchlist
                matched = drug_name_in_text(combined, drug_names)

                records.append({
                    "source":        "govuk_mhra",
                    "title":         title,
                    "summary":       summary[:300],
                    "published":     updated[:10] if updated else "",
                    "url":           link,
                    "matched_drugs": "|".join(matched) if matched else "",
                    "drug_count":    len(matched),
                })

            time.sleep(1)

        except Exception as e:
            print(f"  WARNING: {feed_url} failed: {e}")

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["title", "published"])
        df = df.sort_values("published", ascending=False)
    return df


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 2: FDA Warning Letters RSS (API Manufacturer GMP Failures)
# ══════════════════════════════════════════════════════════════════════════

FDA_API_COMPANIES = [
    # Major Indian API suppliers to UK generics market
    "aurobindo", "dr reddy", "sun pharma", "cipla", "lupin", "ipca",
    "laurus", "divi", "granules", "sequent", "strides", "alembic",
    "zydus", "cadila", "intas", "torrent", "glenmark", "wockhardt",
    "jubilant", "natco", "hetero", "mylan", "viatris",
    # Chinese API suppliers
    "sichuan", "zhejiang", "hubei", "jiangxi", "anhui", "shandong",
    "shanghai", "beijing", "chongqing",
    # Other key suppliers
    "sandoz", "teva", "hikma", "accord",
]

def scrape_fda_warning_letters(drug_names: list[str]) -> pd.DataFrame:
    """
    Parse FDA Warning Letters RSS for GMP failures at Indian/Chinese API
    manufacturers. Lead time: 6-8 weeks before UK concession.
    """
    rss_url = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/warning-letters/rss.xml"
    records = []

    try:
        r = requests.get(rss_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        print(f"  FDA Warning Letters RSS: {len(items)} items")

        for item in items:
            title   = (item.findtext("title")       or "").strip()
            desc    = (item.findtext("description") or "").strip()
            pubdate = (item.findtext("pubDate")      or "").strip()
            link    = (item.findtext("link")         or "").strip()
            combined = (title + " " + desc).lower()

            # filter: must be pharma/API/GMP related
            gmp_keywords = ["pharmaceutical", "drug", "api", "gmp", "manufacturing",
                            "tablet", "capsule", "injection", "sterile", "active ingredient"]
            if not any(kw in combined for kw in gmp_keywords):
                continue

            # check if it mentions known API supplier countries or companies
            is_api_manufacturer = any(co in combined for co in FDA_API_COMPANIES)
            is_india_china = any(c in combined for c in ["india", "china", "chinese", "indian"])

            # match drug names mentioned
            matched_drugs = drug_name_in_text(combined, drug_names)

            records.append({
                "source":              "fda_warning_letter",
                "title":               title,
                "description":         desc[:300],
                "published":           pubdate[:16] if pubdate else "",
                "url":                 link,
                "is_api_manufacturer": int(is_api_manufacturer),
                "is_india_china":      int(is_india_china),
                "matched_drugs":       "|".join(matched_drugs) if matched_drugs else "",
                "drug_count":          len(matched_drugs),
            })

    except Exception as e:
        print(f"  WARNING: FDA Warning Letters RSS failed: {e}")

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("published", ascending=False)
    return df


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 3: CPE Shortage News Feed
# ══════════════════════════════════════════════════════════════════════════

def scrape_cpe_shortage_news(drug_names: list[str]) -> pd.DataFrame:
    """
    Scrape CPE shortage news page for NCSO applications and concession updates.
    Lead time: 1-2 weeks before formal concession announcement.
    """
    url = "https://cpe.org.uk/our-latest-news-category/shortage/"
    records = []

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")

        articles = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"post|article|news"))
        print(f"  CPE shortage news: {len(articles)} articles found")

        for art in articles[:50]:
            title_el = art.find(["h1", "h2", "h3", "h4"])
            title    = title_el.get_text(strip=True) if title_el else ""
            body_el  = art.find("p")
            body     = body_el.get_text(strip=True) if body_el else ""
            date_el  = art.find(["time", "span"], class_=re.compile(r"date|time|publish"))
            date_str = date_el.get_text(strip=True) if date_el else ""
            link_el  = art.find("a", href=True)
            link     = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://cpe.org.uk" + link

            if not title:
                continue

            combined     = (title + " " + body).lower()
            matched      = drug_name_in_text(combined, drug_names)
            is_concession = any(k in combined for k in ["concession", "ncso", "price", "shortage"])

            records.append({
                "source":         "cpe_news",
                "title":          title,
                "body":           body[:300],
                "published":      date_str[:20],
                "url":            link,
                "is_concession":  int(is_concession),
                "matched_drugs":  "|".join(matched) if matched else "",
                "drug_count":     len(matched),
            })

    except Exception as e:
        print(f"  WARNING: CPE shortage news failed: {e}")

    return pd.DataFrame(records)


# ══════════════════════════════════════════════════════════════════════════
# SOURCE 4: MIMS Drug Shortages Page
# ══════════════════════════════════════════════════════════════════════════

def scrape_mims_shortages(drug_names: list[str]) -> pd.DataFrame:
    """
    Scrape MIMS UK drug shortages page. Lead time: 2-4 weeks.
    MIMS updates more frequently than CPE.
    """
    url = "https://www.mims.co.uk/drug-shortages"
    records = []

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")

        # MIMS uses a table or list for shortages
        rows = soup.find_all("tr") or soup.find_all("li", class_=re.compile(r"shortage|drug"))
        print(f"  MIMS drug shortages: {len(rows)} rows found")

        for row in rows:
            text = row.get_text(separator=" ", strip=True)
            if not text or len(text) < 10:
                continue

            matched = drug_name_in_text(text.lower(), drug_names)
            # Extract any date-like pattern
            date_match = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}", text)
            date_str = date_match.group() if date_match else ""

            records.append({
                "source":        "mims_shortages",
                "text":          text[:400],
                "published":     date_str,
                "matched_drugs": "|".join(matched) if matched else "",
                "drug_count":    len(matched),
                "scraped_date":  datetime.today().strftime("%Y-%m-%d"),
            })

    except Exception as e:
        print(f"  WARNING: MIMS shortages failed: {e}")

    df = pd.DataFrame(records)
    if not df.empty:
        df = df[df["drug_count"] > 0]  # only rows matching our drugs
    return df


# ══════════════════════════════════════════════════════════════════════════
# BUILD DRUG-LEVEL FEATURE STORE
# ══════════════════════════════════════════════════════════════════════════

def build_early_warning_features(
    govuk_df: pd.DataFrame,
    fda_df: pd.DataFrame,
    cpe_df: pd.DataFrame,
    mims_df: pd.DataFrame,
    drug_names: list[str],
) -> pd.DataFrame:
    """
    Aggregate all early warning signals into per-drug features.
    Returns DataFrame with one row per drug in our watchlist.
    """
    today = pd.Timestamp.today()
    cutoff_30d = today - timedelta(days=30)
    cutoff_90d = today - timedelta(days=90)

    rows = []
    unique_drugs = list(set(drug_names))

    for drug in unique_drugs:
        kw = drug.split()[0].lower() if drug else ""
        if not kw or len(kw) < 4:
            continue

        def count_mentions(df: pd.DataFrame, col: str = "matched_drugs") -> int:
            if df.empty or col not in df.columns:
                return 0
            return int(df[col].fillna("").str.lower().str.contains(kw).sum())

        def count_recent(df: pd.DataFrame, days: int = 30, col: str = "matched_drugs") -> int:
            if df.empty or col not in df.columns:
                return 0
            date_col = "published"
            if date_col not in df.columns:
                return count_mentions(df, col)
            mask_drug = df[col].fillna("").str.lower().str.contains(kw)
            # try to parse dates
            try:
                dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
                cutoff = today.tz_localize("UTC") - timedelta(days=days)
                mask_date = dates >= cutoff
                return int((mask_drug & mask_date).sum())
            except Exception:
                return int(mask_drug.sum())

        govuk_total    = count_mentions(govuk_df)
        govuk_30d      = count_recent(govuk_df, 30)
        fda_total      = count_mentions(fda_df)
        fda_api        = int(fda_df[fda_df["matched_drugs"].fillna("").str.lower().str.contains(kw)]["is_api_manufacturer"].sum()) if not fda_df.empty and "is_api_manufacturer" in fda_df.columns else 0
        fda_india_china= int(fda_df[fda_df["matched_drugs"].fillna("").str.lower().str.contains(kw)]["is_india_china"].sum()) if not fda_df.empty and "is_india_china" in fda_df.columns else 0
        cpe_total      = count_mentions(cpe_df)
        cpe_concession = int(cpe_df[cpe_df["matched_drugs"].fillna("").str.lower().str.contains(kw)]["is_concession"].sum()) if not cpe_df.empty and "is_concession" in cpe_df.columns else 0
        mims_total     = count_mentions(mims_df)

        # composite early warning score (0-10 scale)
        ew_score = min(10, (
            govuk_total    * 1.5 +
            govuk_30d      * 2.0 +
            fda_total      * 1.0 +
            fda_india_china* 1.5 +
            cpe_total      * 2.0 +
            cpe_concession * 3.0 +
            mims_total     * 2.5
        ))

        rows.append({
            "drug_name":                    drug,
            "govuk_mhra_mentions":          govuk_total,
            "govuk_mhra_mentions_30d":      govuk_30d,
            "fda_warning_mentions":         fda_total,
            "fda_api_manufacturer_flag":    int(fda_api > 0),
            "fda_india_china_flag":         int(fda_india_china > 0),
            "cpe_news_mentions":            cpe_total,
            "cpe_concession_flag":          int(cpe_concession > 0),
            "mims_shortage_flag":           int(mims_total > 0),
            "early_warning_score":          round(ew_score, 2),
            "scraped_date":                 today.strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(rows)
    df = df[df["early_warning_score"] > 0].sort_values("early_warning_score", ascending=False)
    return df


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def run():
    print("=" * 60)
    print("Script 18: Early Warning Signals Scraper")
    print("=" * 60)

    drug_names = load_drug_names()
    print(f"Loaded {len(drug_names)} drugs from predictions")

    print("\n[1/4] GOV.UK MHRA Atom feeds...")
    govuk_df = scrape_govuk_mhra_alerts(drug_names)
    govuk_path = OUT / "govuk_mhra_alerts.csv"
    govuk_df.to_csv(govuk_path, index=False)
    print(f"  Saved {len(govuk_df)} alerts → {govuk_path}")

    print("\n[2/4] FDA Warning Letters RSS...")
    fda_df = scrape_fda_warning_letters(drug_names)
    fda_path = OUT / "fda_warning_letters.csv"
    fda_df.to_csv(fda_path, index=False)
    print(f"  Saved {len(fda_df)} letters → {fda_path}")

    print("\n[3/4] CPE shortage news...")
    cpe_df = scrape_cpe_shortage_news(drug_names)
    cpe_path = OUT / "cpe_shortage_news.csv"
    cpe_df.to_csv(cpe_path, index=False)
    print(f"  Saved {len(cpe_df)} news items → {cpe_path}")

    print("\n[4/4] MIMS drug shortages...")
    mims_df = scrape_mims_shortages(drug_names)
    mims_path = OUT / "mims_shortages.csv"
    mims_df.to_csv(mims_path, index=False)
    print(f"  Saved {len(mims_df)} shortage rows → {mims_path}")

    print("\n[FEATURES] Building drug-level feature store...")
    features_df = build_early_warning_features(govuk_df, fda_df, cpe_df, mims_df, drug_names)
    feat_path = OUT / "early_warning_features.csv"
    features_df.to_csv(feat_path, index=False)
    print(f"  Saved {len(features_df)} drug features → {feat_path}")

    if not features_df.empty:
        print("\n  Top 10 drugs by early warning score:")
        top = features_df.head(10)[["drug_name", "early_warning_score",
                                     "govuk_mhra_mentions", "cpe_concession_flag",
                                     "fda_india_china_flag", "mims_shortage_flag"]]
        print(top.to_string(index=False))

    print("\nDone.")
    return features_df

if __name__ == "__main__":
    run()
