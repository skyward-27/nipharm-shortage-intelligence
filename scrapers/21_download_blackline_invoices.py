"""
SCRIPT 21: BlackLine EIPP Invoice Downloader
=============================================
Downloads all invoices from aah.eipp.blackline.com for the last 5 years.
Uses Playwright with your existing Safari session cookies.

Output: ~/Documents/NPT_Invoice_Data/blackline/raw_pdfs/
        ~/Documents/NPT_Invoice_Data/blackline/download_log.json

Usage:
    python 21_download_blackline_invoices.py

First run: opens a visible browser window. Log in manually if prompted,
then press ENTER in the terminal. Session is saved for future runs.

IMPORTANT: Output is saved LOCALLY only — never committed to git.
"""

import asyncio
import json
import os
import sys
import time
import pathlib
from datetime import datetime, timedelta

# ── Paths ──────────────────────────────────────────────────────────────────────
INVOICE_DIR   = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data" / "blackline"
PDF_DIR       = INVOICE_DIR / "raw_pdfs"
SESSION_FILE  = INVOICE_DIR / "session_cookies.json"
LOG_FILE      = INVOICE_DIR / "download_log.json"
PORTAL_URL    = "https://aah.eipp.blackline.com/app/customer/retrieved-documents"

PDF_DIR.mkdir(parents=True, exist_ok=True)

# ── Cookie helper: try to load from Safari first ───────────────────────────────
def get_safari_cookies(domain="aah.eipp.blackline.com"):
    """Try to extract existing Safari cookies for the BlackLine domain."""
    try:
        import browser_cookie3
        cookies = browser_cookie3.safari(domain_name=domain)
        cookie_list = [
            {"name": c.name, "value": c.value, "domain": c.domain or domain,
             "path": c.path or "/", "httpOnly": False, "secure": True}
            for c in cookies
        ]
        if cookie_list:
            print(f"  Found {len(cookie_list)} Safari cookies for {domain}")
        return cookie_list
    except Exception as e:
        print(f"  Could not read Safari cookies: {e}")
        return []


def load_saved_session():
    """Load previously saved session cookies."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE) as f:
                data = json.load(f)
            # Check if session is less than 8 hours old
            saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
            if (datetime.now() - saved_at).total_seconds() < 28800:
                print(f"  Using saved session from {saved_at.strftime('%H:%M on %d %b')}")
                return data.get("cookies", [])
        except Exception:
            pass
    return []


def save_session(cookies):
    """Save session cookies to disk."""
    with open(SESSION_FILE, "w") as f:
        json.dump({"saved_at": datetime.now().isoformat(), "cookies": cookies}, f, indent=2)
    print(f"  Session saved to {SESSION_FILE}")


async def download_blackline_invoices():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:

        # ── Try to reuse existing session ─────────────────────────────────────
        saved_cookies = load_saved_session()
        safari_cookies = get_safari_cookies() if not saved_cookies else []
        initial_cookies = saved_cookies or safari_cookies

        # ── Launch browser ────────────────────────────────────────────────────
        # Non-headless so user can see what's happening and log in if needed
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Inject any cookies we have
        if initial_cookies:
            try:
                await context.add_cookies(initial_cookies)
                print(f"  Injected {len(initial_cookies)} cookies")
            except Exception as e:
                print(f"  Cookie injection partial: {e}")

        page = await context.new_page()

        # ── Navigate to portal ────────────────────────────────────────────────
        print(f"\nNavigating to {PORTAL_URL} ...")
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Check if we're on a login page
        current_url = page.url
        page_title  = await page.title()
        print(f"  Current URL: {current_url}")
        print(f"  Page title:  {page_title}")

        needs_login = any(kw in current_url.lower() or kw in page_title.lower()
                         for kw in ["login", "signin", "sign-in", "auth", "sso"])

        if needs_login or "retrieved-documents" not in current_url:
            print("\n⚠️  Not logged in. Browser is open — please log in to BlackLine EIPP.")
            print("   Once you're on the 'Retrieved Documents' page, press ENTER here.")
            input("   Press ENTER when ready > ")
            await page.wait_for_timeout(2000)

        # Save session for next time
        all_cookies = await context.cookies()
        save_session(all_cookies)

        # ── Now we're on the documents page — intercept downloads ────────────
        print("\nSetting up download interception...")

        downloaded = []
        skipped    = []

        # Set download path
        await context.set_default_timeout(30000)

        # Intercept all PDF responses
        async def handle_response(response):
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type or "octet-stream" in content_type:
                url = response.url
                filename = url.split("/")[-1].split("?")[0] or f"invoice_{int(time.time())}.pdf"
                if not filename.endswith(".pdf"):
                    filename += ".pdf"
                dest = PDF_DIR / filename
                if not dest.exists():
                    try:
                        body = await response.body()
                        dest.write_bytes(body)
                        downloaded.append(str(dest))
                        print(f"  ✅ Downloaded: {filename}")
                    except Exception as e:
                        print(f"  ⚠️  Failed {filename}: {e}")
                else:
                    skipped.append(filename)

        page.on("response", handle_response)

        # ── Scroll and interact with the document list ────────────────────────
        print("\nAnalysing document list UI...")
        await page.wait_for_timeout(2000)

        # Try to find date filter / "5 years" option
        five_years_ago = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
        print(f"  Looking for date filters (target: {five_years_ago} to today)")

        # Try common date input patterns
        date_inputs = await page.query_selector_all("input[type='date'], input[placeholder*='date' i], input[placeholder*='from' i]")
        if date_inputs:
            print(f"  Found {len(date_inputs)} date input(s)")
            try:
                await date_inputs[0].fill(five_years_ago)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1000)
                print(f"  Set start date to {five_years_ago}")
            except Exception:
                pass

        # Look for "Apply", "Search", "Filter" buttons
        for btn_text in ["Apply", "Search", "Filter", "Go", "Retrieve"]:
            try:
                btn = await page.query_selector(f"button:has-text('{btn_text}')")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    print(f"  Clicked '{btn_text}' button")
                    break
            except Exception:
                pass

        # ── Page through ALL results ──────────────────────────────────────────
        page_num = 1
        max_pages = 500  # Safety limit

        while page_num <= max_pages:
            print(f"\n--- Page {page_num} ---")
            await page.wait_for_timeout(1500)

            # Find all download links/buttons on this page
            download_selectors = [
                "a[href*='.pdf']",
                "a[href*='download']",
                "button:has-text('Download')",
                "a:has-text('Download')",
                "a[download]",
                "button[title*='download' i]",
                "a[title*='download' i]",
            ]

            total_clicked = 0
            for selector in download_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  Found {len(elements)} elements matching '{selector}'")
                    for el in elements:
                        try:
                            async with page.expect_download(timeout=10000) as dl_info:
                                await el.click()
                            dl = await dl_info.value
                            filename = dl.suggested_filename or f"invoice_{int(time.time())}.pdf"
                            dest = PDF_DIR / filename
                            await dl.save_as(str(dest))
                            downloaded.append(str(dest))
                            print(f"  ✅ {filename}")
                            total_clicked += 1
                            await page.wait_for_timeout(500)
                        except Exception:
                            pass  # Not a download trigger or already downloaded

            if total_clicked == 0:
                print("  No new downloads on this page")

            # Try to go to next page
            next_clicked = False
            for next_sel in [
                "button:has-text('Next')",
                "a:has-text('Next')",
                "[aria-label*='next' i]",
                ".pagination-next",
                "button[aria-label='Next page']",
                "li.next a",
            ]:
                try:
                    btn = await page.query_selector(next_sel)
                    if btn:
                        is_disabled = await btn.is_disabled()
                        if not is_disabled:
                            await btn.click()
                            await page.wait_for_timeout(2000)
                            page_num += 1
                            next_clicked = True
                            break
                except Exception:
                    pass

            if not next_clicked:
                print("  No more pages (or pagination not found)")
                break

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"BlackLine EIPP Download Complete")
        print(f"  Downloaded: {len(downloaded)} invoices")
        print(f"  Skipped (already exist): {len(skipped)}")
        print(f"  Saved to: {PDF_DIR}")
        print(f"{'='*60}")

        # Write log
        log = {
            "run_at": datetime.now().isoformat(),
            "downloaded": downloaded,
            "skipped": skipped,
            "total": len(downloaded),
        }
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)

        print(f"\nKeeping browser open for 10 seconds so you can inspect...")
        await page.wait_for_timeout(10000)
        await browser.close()

        return downloaded


if __name__ == "__main__":
    print("=" * 60)
    print("BlackLine EIPP Invoice Downloader")
    print(f"Portal:  {PORTAL_URL}")
    print(f"Output:  {PDF_DIR}")
    print(f"Target:  Last 5 years of invoices")
    print("=" * 60)
    print()

    downloaded = asyncio.run(download_blackline_invoices())
    print(f"\nDone. {len(downloaded)} invoices saved to {PDF_DIR}")
    print("Next step: run python 23_parse_invoice_pdfs.py")
