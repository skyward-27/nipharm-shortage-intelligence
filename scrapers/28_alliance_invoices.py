"""
28_alliance_invoices.py
───────────────────────
Alliance Healthcare (my.alliance-healthcare.co.uk)
→ Documents → Invoices + Credit Notes
→ Date range: March 2025 – March 2026
→ Download all PDFs → ~/Documents/NPT_Invoice_Data/alliance/

Flow:
  1. Launch Chromium with a COPY of your Chrome Default profile
  2. Navigate to https://my.alliance-healthcare.co.uk/group/pro
  3. Click Documents → Invoices (then repeat for Credit Notes)
  4. Set From=01/03/2025  To=31/03/2026
  5. Download every document found

Usage:
  python 28_alliance_invoices.py
  python 28_alliance_invoices.py --headless
  python 28_alliance_invoices.py --from-date 2024-01-01   # custom start
"""

import argparse, shutil, time, pathlib, json, sys, datetime, tempfile
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── paths ──────────────────────────────────────────────────────────────────
CHROME_PROFILE    = pathlib.Path.home() / "Library/Application Support/Google/Chrome/Default"
OUT_INVOICES      = pathlib.Path.home() / "Documents/NPT_Invoice_Data/alliance/invoices"
OUT_CREDIT_NOTES  = pathlib.Path.home() / "Documents/NPT_Invoice_Data/alliance/credit_notes"
META_FILE         = pathlib.Path.home() / "Documents/NPT_Invoice_Data/alliance/metadata.json"
SESSION_COPY_DIR  = pathlib.Path(tempfile.gettempdir()) / "npt_chrome_profile_alliance"

ALLIANCE_URL = "https://my.alliance-healthcare.co.uk/group/pro"
DOCS_URL     = "https://my.alliance-healthcare.co.uk/documents"

DEFAULT_FROM = "01/03/2025"
DEFAULT_TO   = "31/03/2026"


# ── helpers ────────────────────────────────────────────────────────────────
def copy_chrome_profile():
    print("📋  Copying Chrome profile…", flush=True)
    if SESSION_COPY_DIR.exists():
        shutil.rmtree(SESSION_COPY_DIR, ignore_errors=True)
    SESSION_COPY_DIR.mkdir(parents=True)

    needed = [
        "Cookies", "Cookies-journal",
        "Local Storage", "Session Storage",
        "IndexedDB", "Web Data", "Login Data",
        "Preferences", "Secure Preferences",
        "Extension Cookies",
    ]
    for item in needed:
        src = CHROME_PROFILE / item
        if src.exists():
            dst = SESSION_COPY_DIR / item
            try:
                if src.is_dir():
                    try:
                        shutil.copytree(src, dst)
                    except Exception:
                        pass
                else:
                    try:
                        shutil.copy2(src, dst)
                    except Exception:
                        pass
            except Exception:
                pass
    print(f"   ✅  Profile copied → {SESSION_COPY_DIR}", flush=True)


def save_metadata(records: list):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(records, indent=2, default=str))
    print(f"\n💾  Metadata saved → {META_FILE}  ({len(records)} records)")


# ── document downloader ────────────────────────────────────────────────────
def download_section(page, section_name: str, out_dir: pathlib.Path,
                     records: list, from_date: str, to_date: str) -> int:
    """Handle one document section (Invoices or Credit Notes)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    page_num = 1

    print(f"\n{'='*55}", flush=True)
    print(f"  📂  Section: {section_name}", flush=True)
    print(f"  📅  Date range: {from_date} → {to_date}", flush=True)
    print(f"{'='*55}", flush=True)

    # ── Navigate to Documents page ─────────────────────────────────────────
    try:
        # Click Documents menu
        docs_selectors = [
            "nav >> text=Documents",
            "a:has-text('Documents')",
            "[href*='document']",
            "text=Documents",
        ]
        for sel in docs_selectors:
            try:
                page.click(sel, timeout=5000)
                print(f"   ✅  Clicked Documents nav", flush=True)
                page.wait_for_timeout(2000)
                break
            except Exception:
                continue
    except Exception:
        pass

    # ── Click the specific section (Invoices / Credit Notes) ───────────────
    print(f"🖱️   Clicking '{section_name}'…", flush=True)
    section_selectors = [
        f"text={section_name}",
        f"a:has-text('{section_name}')",
        f"button:has-text('{section_name}')",
        f"[href*='{section_name.lower().replace(' ', '-')}']",
        f"[href*='{section_name.lower().replace(' ', '_')}']",
    ]
    found_section = False
    for sel in section_selectors:
        try:
            page.click(sel, timeout=5000)
            found_section = True
            print(f"   ✅  Clicked: {sel}", flush=True)
            page.wait_for_timeout(3000)
            break
        except Exception:
            continue

    if not found_section:
        print(f"\n⚠️  Could not auto-click '{section_name}'.")
        print(f"    Please click '{section_name}' in the browser, then press ENTER…")
        input("   > ")
        page.wait_for_timeout(2000)

    # ── Set date filters ────────────────────────────────────────────────────
    print(f"📅  Setting date range…", flush=True)
    _set_date_filters(page, from_date, to_date)

    # ── Screenshot for confirmation ─────────────────────────────────────────
    ss_name = f"alliance_{section_name.lower().replace(' ','_')}.png"
    page.screenshot(path=str(out_dir.parent / ss_name))
    print(f"   📸  Screenshot → {out_dir.parent / ss_name}", flush=True)

    # ── Download loop ───────────────────────────────────────────────────────
    while True:
        print(f"\n   📄  Page {page_num}…", flush=True)

        # Wait for content
        try:
            page.wait_for_selector(
                "table tr td, [class*='document'], [class*='invoice'], a[href*='.pdf']",
                timeout=10_000
            )
        except PWTimeout:
            print("   ⚠️  Waiting for documents…")
            page.screenshot(path=str(out_dir.parent / f"debug_{section_name}_{page_num}.png"))
            resp = input("   Documents visible? Press ENTER to retry or type 'skip': ").strip().lower()
            if resp == "skip":
                break
            page.wait_for_timeout(3000)
            continue

        # ── Strategy 1: Find direct PDF links ──────────────────────────────
        pdf_links = page.eval_on_selector_all(
            "a[href*='.pdf'], a[href*='download'], a[href*='/document'], a[href*='invoice']",
            """els => els.map(el => ({
                href: el.href,
                text: el.innerText.trim(),
                title: el.title || el.getAttribute('aria-label') || ''
            }))"""
        )

        # ── Strategy 2: Download icons / buttons ───────────────────────────
        dl_buttons = page.query_selector_all(
            "button[aria-label*='download' i], button[title*='download' i], "
            "[class*='download']:not(a), a[aria-label*='download' i], "
            "button:has-text('Download'), svg[aria-label*='download' i]"
        )

        # ── Strategy 3: Row-by-row click and download ──────────────────────
        # Alliance often has a download icon per row
        row_dl_icons = page.query_selector_all(
            "td a[download], td button, td [role='button'], "
            "tr td:last-child a, tr td:last-child button"
        )

        print(f"   Found: {len(pdf_links)} PDF links | "
              f"{len(dl_buttons)} DL buttons | {len(row_dl_icons)} row icons", flush=True)

        # Download via direct links
        for link in pdf_links:
            href = link.get("href", "")
            text = link.get("text", "")
            title = link.get("title", "")
            if not href or href.startswith("javascript"):
                continue
            filename = href.split("/")[-1].split("?")[0] or f"doc_{downloaded+1}"
            if not filename.endswith(".pdf"):
                filename = (title or text or f"doc_{downloaded+1}").replace("/", "-") + ".pdf"

            out_path = out_dir / filename
            if out_path.exists():
                downloaded += 1
                continue
            try:
                with page.expect_download(timeout=30_000) as dl_info:
                    page.evaluate(f"window.open('{href}', '_blank')")
                dl = dl_info.value
                dl.save_as(str(out_path))
                sz = out_path.stat().st_size // 1024
                print(f"   ✅  {filename} ({sz} KB)")
                records.append({
                    "source": "Alliance", "section": section_name,
                    "filename": filename, "url": href, "label": text,
                    "path": str(out_path),
                    "downloaded_at": datetime.datetime.now().isoformat()
                })
                downloaded += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"   ❌  {filename}: {e}")

        # Download via buttons (avoid duplicates by tracking filenames)
        seen = {r["filename"] for r in records}
        for btn in dl_buttons:
            try:
                with page.expect_download(timeout=30_000) as dl_info:
                    btn.click()
                dl = dl_info.value
                filename = dl.suggested_filename or f"doc_{downloaded+1}.pdf"
                if filename in seen:
                    continue
                out_path = out_dir / filename
                dl.save_as(str(out_path))
                sz = out_path.stat().st_size // 1024
                print(f"   ✅  {filename} ({sz} KB)")
                records.append({
                    "source": "Alliance", "section": section_name,
                    "filename": filename, "path": str(out_path),
                    "downloaded_at": datetime.datetime.now().isoformat()
                })
                seen.add(filename)
                downloaded += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"   ❌  Row DL button: {e}")

        # Pagination
        next_btn = page.query_selector(
            "a:has-text('Next'), button:has-text('Next'), "
            "[aria-label='Next page'], [aria-label='Next'], "
            "li.next a, .pagination-next"
        )
        if next_btn and next_btn.is_enabled():
            print("   ➡️   Next page…")
            next_btn.click()
            page.wait_for_timeout(3000)
            page_num += 1
        else:
            print("   🏁  No more pages.")
            break

    return downloaded


def _set_date_filters(page, from_date: str, to_date: str):
    """Try to find and fill date input fields."""
    date_from_selectors = [
        "input[name*='from' i]", "input[placeholder*='from' i]",
        "input[id*='from' i]", "input[aria-label*='from' i]",
        "input[type='date']:first-of-type",
        "input[placeholder*='dd/mm/yyyy']:first-of-type",
        "input[placeholder*='start' i]",
    ]
    date_to_selectors = [
        "input[name*='to' i]", "input[placeholder*='to' i]",
        "input[id*='to' i]", "input[aria-label*='to' i]",
        "input[type='date']:last-of-type",
        "input[placeholder*='dd/mm/yyyy']:last-of-type",
        "input[placeholder*='end' i]",
    ]

    # Fill FROM date
    for sel in date_from_selectors:
        try:
            el = page.query_selector(sel)
            if el:
                el.triple_click()
                el.type(from_date, delay=50)
                print(f"   ✅  From date set: {from_date}")
                break
        except Exception:
            continue

    # Fill TO date
    for sel in date_to_selectors:
        try:
            el = page.query_selector(sel)
            if el:
                el.triple_click()
                el.type(to_date, delay=50)
                print(f"   ✅  To date set: {to_date}")
                break
        except Exception:
            continue

    # Submit / Search
    search_selectors = [
        "button:has-text('Search')", "button:has-text('Filter')",
        "button:has-text('Apply')", "button[type='submit']",
        "input[type='submit']", "button:has-text('Go')",
        "button:has-text('Show')",
    ]
    for sel in search_selectors:
        try:
            page.click(sel, timeout=3000)
            print(f"   ✅  Clicked search/filter button")
            page.wait_for_timeout(3000)
            break
        except Exception:
            continue


# ── main ───────────────────────────────────────────────────────────────────
def scrape(headless: bool, from_date: str, to_date: str):
    copy_chrome_profile()
    records = []
    total = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_COPY_DIR),
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=headless,
            accept_downloads=True,
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled",
                  "--no-first-run", "--no-default-browser-check"],
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        # ── Navigate to Alliance Healthcare ───────────────────────────────
        print(f"\n🌐  Navigating to {ALLIANCE_URL} …", flush=True)
        page.goto(ALLIANCE_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(4000)

        # Check login
        if "login" in page.url.lower() or "sso" in page.url.lower():
            print("\n⚠️  Login required — please log in in the browser window.")
            print("    Press ENTER once you're on the Alliance Healthcare homepage…")
            input()
            page.wait_for_timeout(2000)

        print(f"   ✅  Page: {page.url}", flush=True)

        # ── Section 1: Invoices ────────────────────────────────────────────
        n = download_section(page, "Invoices", OUT_INVOICES, records, from_date, to_date)
        total += n
        print(f"\n   📊  Invoices downloaded: {n}")

        # Navigate back to Documents for Credit Notes
        page.goto(ALLIANCE_URL, wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(3000)

        # ── Section 2: Credit Notes ────────────────────────────────────────
        n = download_section(page, "Credit notes", OUT_CREDIT_NOTES, records, from_date, to_date)
        total += n
        print(f"\n   📊  Credit notes downloaded: {n}")

        browser.close()

    save_metadata(records)
    shutil.rmtree(SESSION_COPY_DIR, ignore_errors=True)
    print(f"\n🏁  Alliance Healthcare scraper complete.  Total files: {total}")


# ── entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download Alliance Healthcare invoices & credit notes")
    ap.add_argument("--headless", action="store_true", help="Run without a visible browser")
    ap.add_argument("--from-date", default=DEFAULT_FROM, help=f"Start date DD/MM/YYYY (default: {DEFAULT_FROM})")
    ap.add_argument("--to-date",   default=DEFAULT_TO,   help=f"End date DD/MM/YYYY (default: {DEFAULT_TO})")
    args = ap.parse_args()

    print("=" * 60)
    print("  Alliance Healthcare Document Downloader")
    print(f"  Target: {ALLIANCE_URL}")
    print(f"  Output: ~/Documents/NPT_Invoice_Data/alliance/")
    print(f"  Range:  {args.from_date}  →  {args.to_date}")
    print("=" * 60)
    scrape(args.headless, args.from_date, args.to_date)
