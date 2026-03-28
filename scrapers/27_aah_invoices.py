"""
27_aah_invoices.py
──────────────────
AAH Hub → Invoice Portal → AAH → Retrieve Documents → Download all PDFs

Flow:
  1. Launch Chromium using a COPY of your Chrome Default profile
     (so it inherits all your login cookies without touching live Chrome)
  2. Navigate  https://www.aah.co.uk/s/aahhub
  3. Click "Invoice Portal" tile
  4. In the pop-up choose "AAH" (not Enterprise/Trident)
  5. Sidebar → "Retrieve Documents"
  6. Download every PDF found → ~/Documents/NPT_Invoice_Data/aah_hub/pdfs/

Usage:
  python 27_aah_invoices.py
  python 27_aah_invoices.py --headless     # run without a visible window
  python 27_aah_invoices.py --years 3      # how many years back (default 5)
"""

import argparse, shutil, time, pathlib, json, re, sys, datetime, tempfile
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── paths ──────────────────────────────────────────────────────────────────
CHROME_PROFILE   = pathlib.Path.home() / "Library/Application Support/Google/Chrome/Default"
OUT_DIR          = pathlib.Path.home() / "Documents/NPT_Invoice_Data/aah_hub/pdfs"
META_FILE        = pathlib.Path.home() / "Documents/NPT_Invoice_Data/aah_hub/metadata.json"
SESSION_COPY_DIR = pathlib.Path(tempfile.gettempdir()) / "npt_chrome_profile_aah"

AAH_HUB_URL = "https://www.aah.co.uk/s/aahhub"

# ── helpers ────────────────────────────────────────────────────────────────
def copy_chrome_profile():
    """Copy only the essential Chrome files to avoid locking the live profile."""
    print("📋  Copying Chrome profile (cookies + local storage)…", flush=True)
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
    print(f"   ✅  Profile copied → {SESSION_COPY_DIR}", flush=True)


def save_metadata(records: list):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(records, indent=2, default=str))
    print(f"\n💾  Metadata saved → {META_FILE}  ({len(records)} records)")


# ── main scraper ───────────────────────────────────────────────────────────
def scrape(headless: bool, years: int):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copy_chrome_profile()

    records = []

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

        # ── 1. Go to AAH Hub ──────────────────────────────────────────────
        print(f"\n🌐  Navigating to {AAH_HUB_URL} …", flush=True)
        page.goto(AAH_HUB_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(3000)

        # Check login
        if "login" in page.url.lower() or "sign" in page.url.lower():
            print("\n⚠️  Login required — please log in in the browser window.")
            print("    Press ENTER here once you're on the AAH Hub homepage…")
            input()
            page.wait_for_timeout(2000)

        print(f"   ✅  Page: {page.url}", flush=True)

        # ── 2. Click Invoice Portal ───────────────────────────────────────
        print("🖱️   Looking for Invoice Portal tile…", flush=True)
        try:
            # Try multiple selectors for the invoice portal link
            invoice_selectors = [
                "text=Invoice Portal",
                "text=invoice portal",
                "a[href*='invoice']",
                "[class*='invoice']",
                "text=Invoices",
            ]
            clicked = False
            for sel in invoice_selectors:
                try:
                    page.click(sel, timeout=4000)
                    clicked = True
                    print(f"   ✅  Clicked: {sel}", flush=True)
                    break
                except Exception:
                    continue

            if not clicked:
                print("\n⚠️  Could not auto-click Invoice Portal.")
                print("    Please click 'Invoice Portal' in the browser, then press ENTER…")
                input()

            page.wait_for_timeout(3000)

        except Exception as e:
            print(f"   ⚠️  {e}")
            print("    Please navigate to the Invoice Portal manually, then press ENTER…")
            input()

        # ── 3. Choose AAH in pop-up ───────────────────────────────────────
        print("🖱️   Selecting 'AAH' in portal chooser…", flush=True)
        try:
            aah_selectors = [
                "text=AAH",
                "button:has-text('AAH')",
                "a:has-text('AAH')",
                "[data-label='AAH']",
            ]
            selected = False
            for sel in aah_selectors:
                try:
                    # Make sure we don't accidentally click Enterprise/Trident
                    elems = page.query_selector_all(sel)
                    for el in elems:
                        txt = (el.inner_text() or "").strip()
                        if txt == "AAH":
                            el.click()
                            selected = True
                            print(f"   ✅  Selected AAH tile", flush=True)
                            break
                    if selected:
                        break
                except Exception:
                    continue

            if not selected:
                print("\n⚠️  Could not auto-select AAH.")
                print("    Please click 'AAH' (not Enterprise/Trident) in the browser, then press ENTER…")
                input()

            page.wait_for_timeout(3000)

        except Exception as e:
            print(f"   ⚠️  {e}")
            input("    Select AAH manually, then press ENTER…")

        # ── 4. Click Retrieve Documents in sidebar ────────────────────────
        print("🖱️   Looking for 'Retrieve Documents' in sidebar…", flush=True)
        try:
            retrieve_selectors = [
                "text=Retrieve Documents",
                "text=Retrieve documents",
                "a:has-text('Retrieve')",
                "[href*='retrieve']",
                "[href*='documents']",
                "text=Documents",
            ]
            found = False
            for sel in retrieve_selectors:
                try:
                    page.click(sel, timeout=5000)
                    found = True
                    print(f"   ✅  Clicked: {sel}", flush=True)
                    break
                except Exception:
                    continue

            if not found:
                print("\n⚠️  Could not find 'Retrieve Documents'.")
                print("    Please click it in the sidebar, then press ENTER…")
                input()
                print("    ⏳  Waiting for page to load (10 seconds)…")

            page.wait_for_timeout(10_000)  # LONGER WAIT for dynamic content

        except Exception as e:
            print(f"   ⚠️  {e}")
            input("    Navigate to Retrieve Documents, then press ENTER…")
            print("    ⏳  Waiting for page to load (10 seconds)…")
            page.wait_for_timeout(10_000)

        # ── 5. Screenshot to confirm we're on the right page ──────────────
        ss_path = OUT_DIR.parent / "retrieve_docs_page.png"
        page.screenshot(path=str(ss_path))
        print(f"   📸  Screenshot saved → {ss_path}", flush=True)

        # ── 6. Set date range (5 years back) & download ──────────────────
        cutoff = datetime.date.today() - datetime.timedelta(days=365 * years)
        print(f"\n📅  Will download documents from {cutoff} onwards…", flush=True)

        downloaded = _download_documents(page, OUT_DIR, records, cutoff)
        print(f"\n✅  Downloaded {downloaded} document(s) total.")

        browser.close()

    save_metadata(records)
    shutil.rmtree(SESSION_COPY_DIR, ignore_errors=True)
    print("🏁  AAH scraper complete.")


def _download_documents(page, out_dir: pathlib.Path, records: list, cutoff) -> int:
    """Download all documents from BlackLine Retrieve Documents table."""
    downloaded = 0
    page_num = 1

    while True:
        print(f"\n📄  Processing page {page_num}…", flush=True)

        # Wait for table rows to load (with multiple attempts)
        found_rows = False
        for attempt in range(3):
            try:
                page.wait_for_selector("table tr, [role='row'], [class*='document-row']", timeout=5_000)
                found_rows = True
                break
            except PWTimeout:
                if attempt < 2:
                    print(f"   ⏳  Retry {attempt+1}/3, waiting more…")
                    page.wait_for_timeout(3000)

        if not found_rows:
            print("   ⚠️  No document table found on this page.")
            page.screenshot(path=str(out_dir.parent / f"debug_page{page_num}.png"))
            print(f"   📸  Debug screenshot → {out_dir.parent}/debug_page{page_num}.png")
            print("   ℹ️  If you can see documents in the browser, press ENTER to retry")
            print("       or type 'skip' to finish.")
            resp = input("   > ").strip().lower()
            if resp == "skip":
                break
            page.wait_for_timeout(2000)
            continue

        # ── Strategy: Click download icon in each table row ──────────────
        # Try multiple selectors for rows
        rows = page.query_selector_all("table tbody tr") or page.query_selector_all("table tr") or \
               page.query_selector_all("tr[class*='row']") or page.query_selector_all("[role='row']")
        print(f"   Found {len(rows)} documents on page {page_num}", flush=True)

        for idx, row in enumerate(rows):
            try:
                # Get document info from the row
                cells = row.query_selector_all("td")
                if len(cells) < 2:
                    continue

                doc_type = (cells[0].inner_text() or "").strip()
                doc_ref = (cells[1].inner_text() or "").strip()
                doc_date = (cells[2].inner_text() or "").strip() if len(cells) > 2 else ""

                # Create filename
                filename = f"{doc_type}_{doc_ref}_{doc_date}".replace("/", "-")
                if not filename.endswith(".pdf"):
                    filename += ".pdf"
                filename = filename[:100]  # Cap length

                out_path = out_dir / filename
                if out_path.exists():
                    print(f"   ⏭️   {idx+1}. Already have: {filename}")
                    downloaded += 1
                    continue

                # ── Find and click download icon in this row ──────────────
                # Look for the rightmost action button (download icon)
                action_buttons = row.query_selector_all("button, a[role='button'], [class*='action']")
                if not action_buttons:
                    print(f"   ⚠️  {idx+1}. No download button found for {doc_ref}")
                    continue

                # Try the rightmost button first (usually the download icon)
                download_btn = action_buttons[-1] if action_buttons else None
                if not download_btn:
                    print(f"   ⚠️  {idx+1}. No button to click for {doc_ref}")
                    continue

                # Try to download by clicking the button
                try:
                    with page.expect_download(timeout=30_000) as dl_info:
                        download_btn.click()
                    dl = dl_info.value
                    dl.save_as(str(out_path))
                    sz = out_path.stat().st_size // 1024
                    print(f"   ✅  {idx+1}. {filename} ({sz} KB)")
                    records.append({
                        "source": "AAH",
                        "doc_type": doc_type,
                        "doc_ref": doc_ref,
                        "doc_date": doc_date,
                        "filename": filename,
                        "path": str(out_path),
                        "downloaded_at": datetime.datetime.now().isoformat()
                    })
                    downloaded += 1
                    time.sleep(0.5)
                except Exception as e:
                    print(f"   ❌  {idx+1}. Download failed for {doc_ref}: {e}")

            except Exception as e:
                print(f"   ❌  Row {idx+1} error: {e}")

        # ── Check pagination ────────────────────────────────────────────
        try:
            next_btn = page.query_selector("a[aria-label='Next'], button[aria-label='Next'], .pagination-next")
            if next_btn and next_btn.is_enabled():
                print("   ➡️   Going to next page…", flush=True)
                next_btn.click()
                page.wait_for_timeout(3000)
                page_num += 1
            else:
                print("   🏁  No more pages.", flush=True)
                break
        except Exception:
            print("   🏁  End of pagination.", flush=True)
            break

    return downloaded


# ── entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download AAH Hub invoices")
    ap.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    ap.add_argument("--years", type=int, default=5, help="Years of data to fetch (default: 5)")
    args = ap.parse_args()

    print("=" * 60)
    print("  AAH Hub Invoice Downloader")
    print(f"  Target: {AAH_HUB_URL}")
    print(f"  Output: {OUT_DIR}")
    print(f"  Years:  {args.years}")
    print("=" * 60)
    scrape(args.headless, args.years)
