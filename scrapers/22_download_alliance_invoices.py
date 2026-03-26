"""
SCRIPT 22: Alliance Healthcare Invoice Downloader
==================================================
Downloads all invoices from my.alliance-healthcare.co.uk for the last 5 years.
Uses Playwright with your existing Safari session cookies.

Output: ~/Documents/NPT_Invoice_Data/alliance/raw_pdfs/
        ~/Documents/NPT_Invoice_Data/alliance/download_log.json

Usage:
    python 22_download_alliance_invoices.py

IMPORTANT: Output is saved LOCALLY only — never committed to git.
"""

import asyncio
import json
import os
import time
import pathlib
from datetime import datetime, timedelta

# ── Paths ──────────────────────────────────────────────────────────────────────
INVOICE_DIR   = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data" / "alliance"
PDF_DIR       = INVOICE_DIR / "raw_pdfs"
SESSION_FILE  = INVOICE_DIR / "session_cookies.json"
LOG_FILE      = INVOICE_DIR / "download_log.json"
PORTAL_URL    = "https://my.alliance-healthcare.co.uk/group/pro"

PDF_DIR.mkdir(parents=True, exist_ok=True)


def get_safari_cookies(domain="my.alliance-healthcare.co.uk"):
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
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE) as f:
                data = json.load(f)
            saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
            if (datetime.now() - saved_at).total_seconds() < 28800:
                print(f"  Using saved session from {saved_at.strftime('%H:%M on %d %b')}")
                return data.get("cookies", [])
        except Exception:
            pass
    return []


def save_session(cookies):
    with open(SESSION_FILE, "w") as f:
        json.dump({"saved_at": datetime.now().isoformat(), "cookies": cookies}, f, indent=2)
    print(f"  Session saved to {SESSION_FILE}")


async def download_alliance_invoices():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        saved_cookies = load_saved_session()
        safari_cookies = get_safari_cookies() if not saved_cookies else []
        initial_cookies = saved_cookies or safari_cookies

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

        if initial_cookies:
            try:
                await context.add_cookies(initial_cookies)
                print(f"  Injected {len(initial_cookies)} cookies")
            except Exception as e:
                print(f"  Cookie injection note: {e}")

        page = await context.new_page()

        print(f"\nNavigating to {PORTAL_URL} ...")
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        current_url = page.url
        page_title  = await page.title()
        print(f"  URL: {current_url}")
        print(f"  Title: {page_title}")

        needs_login = any(kw in current_url.lower() or kw in page_title.lower()
                         for kw in ["login", "signin", "sign-in", "auth"])

        if needs_login:
            print("\n⚠️  Not logged in. Browser is open — please log in to Alliance Healthcare.")
            print("   Navigate to the invoices / account documents section.")
            print("   Press ENTER when you're on the invoices page.")
            input("   Press ENTER > ")
            await page.wait_for_timeout(2000)

        all_cookies = await context.cookies()
        save_session(all_cookies)

        # ── Explore the page for invoice navigation ──────────────────────────
        print("\nLooking for invoice/documents section...")

        # Common Alliance Healthcare portal navigation patterns
        invoice_nav_texts = [
            "Invoices", "Statements", "Documents", "My Documents",
            "Account Documents", "Invoice History", "Finance",
        ]
        for nav_text in invoice_nav_texts:
            try:
                link = await page.query_selector(f"a:has-text('{nav_text}'), button:has-text('{nav_text}')")
                if link:
                    print(f"  Found navigation: '{nav_text}' — clicking")
                    await link.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

        # ── Network interception for PDFs ────────────────────────────────────
        downloaded = []
        skipped    = []

        async def handle_response(response):
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type or "application/octet-stream" in content_type:
                url = response.url
                filename = url.split("/")[-1].split("?")[0] or f"invoice_{int(time.time())}.pdf"
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                dest = PDF_DIR / filename
                if not dest.exists():
                    try:
                        body = await response.body()
                        dest.write_bytes(body)
                        downloaded.append(str(dest))
                        print(f"  ✅ Intercepted: {filename}")
                    except Exception as e:
                        print(f"  ⚠️  Failed {filename}: {e}")

        page.on("response", handle_response)

        # ── Set date range filter ────────────────────────────────────────────
        five_years_ago = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
        date_inputs = await page.query_selector_all("input[type='date']")
        if date_inputs:
            try:
                await date_inputs[0].fill(five_years_ago)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1000)
                print(f"  Set date filter: {five_years_ago}")
            except Exception:
                pass

        for btn_text in ["Apply", "Search", "Filter", "Go"]:
            try:
                btn = await page.query_selector(f"button:has-text('{btn_text}')")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    print(f"  Clicked '{btn_text}'")
                    break
            except Exception:
                pass

        # ── Paginate and download ────────────────────────────────────────────
        page_num = 1
        max_pages = 500

        while page_num <= max_pages:
            print(f"\n--- Page {page_num} ---")
            await page.wait_for_timeout(1500)

            download_selectors = [
                "a[href*='.pdf']",
                "a[href*='download']",
                "button:has-text('Download')",
                "a:has-text('Download')",
                "a:has-text('PDF')",
                "a[download]",
                "button[title*='download' i]",
                "a[title*='PDF' i]",
                "a[title*='invoice' i]",
            ]

            total_clicked = 0
            for selector in download_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  {len(elements)} element(s) — '{selector}'")
                    for el in elements:
                        try:
                            async with page.expect_download(timeout=10000) as dl_info:
                                await el.click()
                            dl = await dl_info.value
                            filename = dl.suggested_filename or f"alliance_{int(time.time())}.pdf"
                            dest = PDF_DIR / filename
                            if not dest.exists():
                                await dl.save_as(str(dest))
                                downloaded.append(str(dest))
                                print(f"  ✅ {filename}")
                                total_clicked += 1
                            else:
                                skipped.append(filename)
                            await page.wait_for_timeout(300)
                        except Exception:
                            pass

            if total_clicked == 0:
                print("  No new downloads")

            next_clicked = False
            for next_sel in [
                "button:has-text('Next')", "a:has-text('Next')",
                "[aria-label*='next' i]", ".pagination-next",
                "button[aria-label='Next page']", "li.next a",
            ]:
                try:
                    btn = await page.query_selector(next_sel)
                    if btn and not await btn.is_disabled():
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        page_num += 1
                        next_clicked = True
                        break
                except Exception:
                    pass

            if not next_clicked:
                print("  End of pages")
                break

        print(f"\n{'='*60}")
        print(f"Alliance Healthcare Download Complete")
        print(f"  Downloaded: {len(downloaded)} invoices")
        print(f"  Skipped (exist): {len(skipped)}")
        print(f"  Saved to: {PDF_DIR}")
        print(f"{'='*60}")

        log = {
            "run_at": datetime.now().isoformat(),
            "downloaded": downloaded,
            "skipped": skipped,
            "total": len(downloaded),
        }
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)

        print("\nKeeping browser open for 10 seconds...")
        await page.wait_for_timeout(10000)
        await browser.close()
        return downloaded


if __name__ == "__main__":
    print("=" * 60)
    print("Alliance Healthcare Invoice Downloader")
    print(f"Portal:  {PORTAL_URL}")
    print(f"Output:  {PDF_DIR}")
    print("=" * 60)
    print()
    downloaded = asyncio.run(download_alliance_invoices())
    print(f"\nDone. {len(downloaded)} invoices in {PDF_DIR}")
    print("Next step: run python 23_parse_invoice_pdfs.py")
