"""
SCRIPT 25: AAH Hub Order & Invoice Downloader
=============================================
Scrapes order history and invoice data from AAH Hub (Salesforce Experience Cloud)
at https://www.aah.co.uk/s/aahhub

AAH Hub is built on Salesforce Experience Cloud. Key characteristics:
  - URL pattern: aah.co.uk/s/<page-name>
  - Data is loaded via XHR calls to Salesforce APIs:
      /services/apexrest/...
      /services/data/vXX.X/...
      /aura?r=X&...  (Aura/LWC component data)
  - Pagination uses offset-based cursors, not page numbers
  - PDFs are served from a separate document storage URL

Output:
    ~/Documents/NPT_Invoice_Data/aah_hub/raw_pdfs/     — downloaded PDFs
    ~/Documents/NPT_Invoice_Data/aah_hub/api_data/     — intercepted JSON API responses
    ~/Documents/NPT_Invoice_Data/aah_hub/order_data.csv — tabular order summary
    ~/Documents/NPT_Invoice_Data/aah_hub/download_log.json

Usage:
    python 25_download_aah_orders.py

First run: opens a visible Chromium window. If cookies don't transfer from
Safari, log in manually when prompted, then press ENTER.
Session is saved to ~/Documents/NPT_Invoice_Data/sessions/aah_session.json
for automatic reuse on subsequent runs (valid for 8 hours).

IMPORTANT: Output is saved LOCALLY only — never committed to git.
           ~/Documents/NPT_Invoice_Data/ is in .gitignore.
"""

import asyncio
import csv
import json
import os
import pathlib
import re
import struct
import sys
import time
from datetime import datetime, timedelta

# ── Paths ───────────────────────────────────────────────────────────────────────
BASE_DIR     = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data" / "aah_hub"
PDF_DIR      = BASE_DIR / "raw_pdfs"
API_DIR      = BASE_DIR / "api_data"
SESSION_FILE = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data" / "sessions" / "aah_session.json"
LOG_FILE     = BASE_DIR / "download_log.json"
CSV_FILE     = BASE_DIR / "order_data.csv"

for d in [PDF_DIR, API_DIR, SESSION_FILE.parent]:
    d.mkdir(parents=True, exist_ok=True)

# ── Portal URLs ─────────────────────────────────────────────────────────────────
PORTAL_BASE = "https://www.aah.co.uk"
PORTAL_HOME = "https://www.aah.co.uk/s/aahhub"

# Salesforce Experience Cloud page candidates for orders/invoices
CANDIDATE_PAGES = [
    "https://www.aah.co.uk/s/orders",
    "https://www.aah.co.uk/s/invoices",
    "https://www.aah.co.uk/s/account-documents",
    "https://www.aah.co.uk/s/invoice-history",
    "https://www.aah.co.uk/s/my-invoices",
    "https://www.aah.co.uk/s/statements",
]

# Date range: last 5 years
DATE_FROM = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
DATE_TO   = datetime.now().strftime("%Y-%m-%d")

# AAH domains to try for cookie extraction
AAH_DOMAINS = ["www.aah.co.uk", ".aah.co.uk", "aah.co.uk"]


# ── Cookie helpers ──────────────────────────────────────────────────────────────
def get_safari_cookies_bc3(domain: str) -> list[dict]:
    """
    Extract Safari cookies for a given domain using browser_cookie3.
    browser_cookie3 reads ~/Library/Cookies/Cookies.binarycookies.
    """
    try:
        import browser_cookie3
        jar = browser_cookie3.safari(domain_name=domain)
        cookies = []
        for c in jar:
            cookies.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain if c.domain else domain,
                "path": c.path if c.path else "/",
                "secure": bool(getattr(c, "secure", True)),
                "httpOnly": False,
                "sameSite": "None",
            })
        if cookies:
            print(f"    browser_cookie3: {len(cookies)} cookies for {domain}")
        return cookies
    except ImportError:
        return []
    except Exception as e:
        print(f"    browser_cookie3 error ({domain}): {e}")
        return []


def parse_safari_binary_cookies(domain_filter: str) -> list[dict]:
    """
    Parse Safari's Cookies.binarycookies file directly using struct unpacking.
    More reliable than browser_cookie3 for macOS Ventura and later because it
    reads the raw file format rather than going through a Python abstraction layer.

    Safari binary cookie format: big-endian page headers, little-endian cookie structs.
    Cookie expiry uses Mac epoch (seconds since 2001-01-01).
    """
    cookie_file = pathlib.Path.home() / "Library" / "Cookies" / "Cookies.binarycookies"
    if not cookie_file.exists():
        return []

    cookies = []
    try:
        data = cookie_file.read_bytes()
        if data[:4] != b"cook":
            return []

        num_pages = struct.unpack(">I", data[4:8])[0]
        page_sizes = [struct.unpack(">I", data[8 + i * 4: 12 + i * 4])[0] for i in range(num_pages)]

        file_offset = 8 + num_pages * 4
        for page_size in page_sizes:
            page_data = data[file_offset: file_offset + page_size]
            file_offset += page_size
            if len(page_data) < 8:
                continue

            page_magic = struct.unpack("<I", page_data[0:4])[0]
            if page_magic != 0x00000100:
                continue

            num_cookies = struct.unpack("<I", page_data[4:8])[0]
            offsets = [struct.unpack("<I", page_data[8 + i*4: 12 + i*4])[0] for i in range(num_cookies)]

            for coff in offsets:
                try:
                    c_data = page_data[coff:]
                    if len(c_data) < 56:
                        continue

                    flags      = struct.unpack("<I", c_data[8:12])[0]
                    domain_off = struct.unpack("<I", c_data[16:20])[0]
                    name_off   = struct.unpack("<I", c_data[20:24])[0]
                    path_off   = struct.unpack("<I", c_data[24:28])[0]
                    value_off  = struct.unpack("<I", c_data[28:32])[0]
                    expiry_mac = struct.unpack("<d", c_data[40:48])[0]

                    def cstr(buf, start):
                        end = buf.find(b"\x00", start)
                        return buf[start:end].decode("utf-8", errors="replace") if end != -1 else ""

                    domain = cstr(c_data, domain_off)
                    name   = cstr(c_data, name_off)
                    path   = cstr(c_data, path_off)
                    value  = cstr(c_data, value_off)

                    # Filter to requested domain (strip leading dot for comparison)
                    bare_filter = domain_filter.lstrip(".")
                    bare_domain = domain.lstrip(".")
                    if bare_filter not in bare_domain and bare_domain not in bare_filter:
                        continue

                    expiry_unix = int(expiry_mac) + 978307200 if expiry_mac > 0 else 0
                    cookie = {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path or "/",
                        "secure": bool(flags & 1),
                        "httpOnly": bool(flags & 4),
                        "sameSite": "None",
                    }
                    if expiry_unix > time.time():
                        cookie["expires"] = expiry_unix
                    if name and domain:
                        cookies.append(cookie)
                except Exception:
                    continue
    except Exception as e:
        print(f"    Binary cookie parse error: {e}")
    return cookies


def collect_all_cookies() -> list[dict]:
    """
    Collect cookies for all AAH domain variants using both extraction methods.
    Deduplicates by (name, domain), preferring binary parse over browser_cookie3.
    """
    print("  Collecting Safari cookies for AAH domains...")
    all_cookies = {}

    # Try binary parse first (more reliable)
    for domain in AAH_DOMAINS:
        for c in parse_safari_binary_cookies(domain):
            key = (c["name"], c["domain"])
            all_cookies[key] = c

    # Supplement with browser_cookie3 for any gaps
    for domain in AAH_DOMAINS:
        for c in get_safari_cookies_bc3(domain):
            key = (c["name"], c["domain"])
            if key not in all_cookies:
                all_cookies[key] = c

    cookies = list(all_cookies.values())
    print(f"  Total unique cookies collected: {len(cookies)}")
    return cookies


def normalise_cookies(cookies: list[dict]) -> list[dict]:
    """
    Sanitise cookie dicts so Playwright's add_cookies() accepts them.
    Playwright rejects cookies where sameSite is not 'Strict'/'Lax'/'None',
    or where expires is not a number.
    """
    valid_ss = {"Strict", "Lax", "None"}
    out = []
    for c in cookies:
        try:
            ss = str(c.get("sameSite", "None")).capitalize()
            if ss not in valid_ss:
                ss = "None"
            clean = {
                "name": str(c.get("name", "")),
                "value": str(c.get("value", "")),
                "domain": str(c.get("domain", "")),
                "path": str(c.get("path", "/")),
                "secure": bool(c.get("secure", False)),
                "httpOnly": bool(c.get("httpOnly", False)),
                "sameSite": ss,
            }
            exp = c.get("expires")
            if exp is not None:
                try:
                    exp_int = int(float(exp))
                    if exp_int > time.time():
                        clean["expires"] = exp_int
                except (ValueError, TypeError):
                    pass
            if clean["name"] and clean["domain"]:
                out.append(clean)
        except Exception:
            continue
    return out


def load_saved_session() -> list[dict]:
    """
    Load persisted session cookies from disk. Sessions are valid for 8 hours
    (Salesforce sessions typically last longer, but we refresh conservatively).
    """
    if not SESSION_FILE.exists():
        return []
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
        saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
        age_h = (datetime.now() - saved_at).total_seconds() / 3600
        if age_h < 8:
            cookies = data.get("cookies", [])
            print(f"  Loaded saved session: {len(cookies)} cookies ({age_h:.1f}h old)")
            return cookies
        print(f"  Saved session is {age_h:.1f}h old — will refresh")
    except Exception as e:
        print(f"  Could not load session: {e}")
    return []


def save_session(cookies: list[dict]) -> None:
    """Write Playwright context cookies to disk for reuse."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"saved_at": datetime.now().isoformat(), "cookies": cookies}, f, indent=2)
        print(f"  Session saved → {SESSION_FILE}")
    except Exception as e:
        print(f"  ⚠️  Session save failed: {e}")


# ── API response interceptor ────────────────────────────────────────────────────
class APIInterceptor:
    """
    Captures Salesforce API responses (Aura, Apex REST, standard REST)
    as the page loads, extracting order/invoice data without needing to
    reverse-engineer the UI interaction sequence.

    Salesforce Experience Cloud makes calls to endpoints like:
      /aura?r=...               — Lightning Aura framework data calls
      /services/apexrest/...    — Custom Apex REST endpoints
      /services/data/vXX/...    — Standard Salesforce REST API
    """

    def __init__(self):
        self.captured: list[dict] = []
        self.pdf_urls: list[str] = []

    def is_api_response(self, url: str, content_type: str) -> bool:
        """Detect whether a response looks like an API data response."""
        url_lower = url.lower()
        api_patterns = [
            "/aura", "/services/apexrest", "/services/data/",
            "/api/", "/rest/", "json",
        ]
        return (
            any(p in url_lower for p in api_patterns)
            or "json" in content_type
        )

    def is_pdf_url(self, url: str, content_type: str) -> bool:
        """Detect whether a response is a PDF document."""
        return "pdf" in content_type.lower() or "pdf" in url.lower()

    async def handle_response(self, response) -> None:
        """
        Playwright response handler. Runs for every network response.
        Captures JSON API data and intercepts PDF responses.
        """
        try:
            url          = response.url
            status       = response.status
            content_type = response.headers.get("content-type", "")

            # Skip failed/redirect responses
            if status not in (200, 201):
                return

            if self.is_pdf_url(url, content_type):
                self.pdf_urls.append(url)
                print(f"    Found PDF URL: {url[:80]}...")
                return

            if self.is_api_response(url, content_type):
                try:
                    body = await response.body()
                    if len(body) < 10:  # Skip tiny/empty responses
                        return
                    text = body.decode("utf-8", errors="replace")
                    # Only record if it looks like JSON with real data
                    if text.strip().startswith(("{", "[")):
                        self.captured.append({
                            "url": url,
                            "status": status,
                            "content_type": content_type,
                            "captured_at": datetime.now().isoformat(),
                            "body": text,
                        })
                except Exception:
                    pass  # Body may not be readable for all responses
        except Exception:
            pass


# ── UI navigation helpers ────────────────────────────────────────────────────────
async def find_and_click(page, selectors: list[str], description: str) -> bool:
    """
    Try a list of CSS selectors in order, clicking the first visible match.
    Returns True if something was clicked, False if nothing found.
    Used to navigate menus whose exact selectors vary between deployments.
    """
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                print(f"    Clicked: {description} (selector: {sel})")
                await page.wait_for_timeout(2000)
                return True
        except Exception:
            continue
    return False


async def set_date_filter(page, date_from: str, date_to: str) -> bool:
    """
    Attempt to set a date range filter on the current page.
    Tries multiple input patterns used by Salesforce Experience Cloud pages.
    Returns True if at least one date field was set.
    """
    success = False

    # Pattern 1: standard HTML date inputs
    date_inputs = await page.query_selector_all("input[type='date']")
    if len(date_inputs) >= 1:
        try:
            await date_inputs[0].fill(date_from)
            await page.keyboard.press("Tab")
            success = True
            print(f"    Set start date: {date_from}")
        except Exception:
            pass
    if len(date_inputs) >= 2:
        try:
            await date_inputs[1].fill(date_to)
            await page.keyboard.press("Tab")
            print(f"    Set end date: {date_to}")
        except Exception:
            pass

    # Pattern 2: text inputs with date placeholders (Salesforce often uses these)
    if not success:
        text_inputs = await page.query_selector_all(
            "input[placeholder*='date' i], input[placeholder*='from' i], "
            "input[placeholder*='start' i], lightning-input[type='date']"
        )
        for inp in text_inputs[:2]:
            try:
                await inp.fill(date_from)
                await page.keyboard.press("Tab")
                success = True
                break
            except Exception:
                continue

    # Pattern 3: look for a "Last 5 years" or similar dropdown preset
    for preset_text in ["5 Years", "Last 5 Years", "All Time", "All", "5Y"]:
        try:
            el = await page.query_selector(
                f"option:has-text('{preset_text}'), "
                f"button:has-text('{preset_text}'), "
                f"a:has-text('{preset_text}')"
            )
            if el:
                await el.click()
                success = True
                print(f"    Selected preset: '{preset_text}'")
                await page.wait_for_timeout(1000)
                break
        except Exception:
            continue

    return success


async def click_apply_filter(page) -> None:
    """Click Search/Apply/Filter button after setting date range."""
    for btn_text in ["Search", "Apply", "Filter", "Go", "Retrieve", "Submit"]:
        try:
            btn = await page.query_selector(
                f"button:has-text('{btn_text}'), "
                f"input[type='submit'][value='{btn_text}']"
            )
            if btn and await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(3000)
                print(f"    Clicked filter button: '{btn_text}'")
                return
        except Exception:
            continue


# ── PDF downloader ──────────────────────────────────────────────────────────────
async def download_pdfs_from_page(page, context, downloaded: list, skipped: list) -> int:
    """
    Find and download all PDF links visible on the current page.
    Uses both the expect_download() approach (for triggered downloads) and
    direct URL fetch (for links pointing directly to PDF files).
    Returns count of new downloads.
    """
    count = 0

    # Selectors targeting download links and buttons on Salesforce pages
    download_selectors = [
        "a[href*='.pdf']",
        "a[href*='download']",
        "a[href*='ContentDocument']",
        "a[href*='sfc/servlet']",          # Salesforce file servlet
        "a[href*='/servlet/servlet.FileDownload']",
        "button:has-text('Download')",
        "a:has-text('Download')",
        "a:has-text('PDF')",
        "a:has-text('View')",
        "a:has-text('Invoice')",
        "a[download]",
        "[data-doctype*='pdf' i]",
        "[title*='download' i]",
        "[title*='PDF' i]",
        "[title*='invoice' i]",
    ]

    for selector in download_selectors:
        try:
            elements = await page.query_selector_all(selector)
            if not elements:
                continue

            print(f"    Found {len(elements)} elements matching: {selector}")

            for el in elements:
                try:
                    # Try Playwright's download interception first (covers all download methods)
                    async with page.expect_download(timeout=12000) as dl_info:
                        await el.click()
                    dl = await dl_info.value
                    filename = dl.suggested_filename or f"aah_{int(time.time())}.pdf"
                    dest = PDF_DIR / filename
                    if not dest.exists():
                        await dl.save_as(str(dest))
                        downloaded.append(str(dest))
                        print(f"    ✅ Downloaded: {filename}")
                        count += 1
                    else:
                        skipped.append(filename)
                    await page.wait_for_timeout(800)
                except Exception:
                    # If expect_download times out, the link might open a new tab with the PDF
                    try:
                        async with context.expect_page() as new_page_info:
                            await el.click()
                        new_page = await new_page_info.value
                        await new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                        pdf_url = new_page.url
                        if ".pdf" in pdf_url.lower() or "ContentDocument" in pdf_url:
                            # Download the PDF from the new page's URL
                            pdf_bytes = await new_page.pdf() if "pdf" in pdf_url.lower() else None
                            if not pdf_bytes:
                                # Try fetching via response body
                                resp = await new_page.goto(pdf_url)
                                if resp:
                                    pdf_bytes = await resp.body()
                            if pdf_bytes:
                                fname = pdf_url.split("/")[-1].split("?")[0] or f"aah_{int(time.time())}.pdf"
                                if not fname.endswith(".pdf"):
                                    fname += ".pdf"
                                dest = PDF_DIR / fname
                                if not dest.exists():
                                    dest.write_bytes(pdf_bytes)
                                    downloaded.append(str(dest))
                                    print(f"    ✅ Downloaded (new tab): {fname}")
                                    count += 1
                        await new_page.close()
                    except Exception:
                        pass  # Link didn't trigger a download or new page

        except Exception:
            continue

    return count


async def paginate_and_download(page, context, downloaded: list, skipped: list) -> None:
    """
    Iterate through all pages of results, downloading PDFs on each page.
    Salesforce Experience Cloud uses both offset-based and cursor-based pagination.
    We handle the most common UI patterns: Next button, Load More, infinite scroll.
    """
    page_num = 1
    max_pages = 500  # Safety limit — a 5-year history shouldn't exceed this

    while page_num <= max_pages:
        print(f"\n  --- Page {page_num} ---")
        await page.wait_for_timeout(1500)

        count = await download_pdfs_from_page(page, context, downloaded, skipped)
        if count == 0:
            print("    No new downloads on this page")

        # Look for Next/Load More controls
        next_clicked = False

        # Standard Next button patterns
        next_selectors = [
            "button:has-text('Next')",
            "a:has-text('Next')",
            "[aria-label*='Next' i]",
            "[aria-label*='next page' i]",
            ".pagination-next",
            ".next-page",
            "li.next > a",
            "button[title='Next Page']",
            # Salesforce-specific pagination
            "lightning-button-icon[icon-name='utility:chevronright']",
            "button.slds-button[name='next']",
        ]
        for sel in next_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and not await btn.is_disabled() and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(2500)
                    page_num += 1
                    next_clicked = True
                    break
            except Exception:
                continue

        if not next_clicked:
            # Try "Load More" pattern (infinite scroll / lazy load)
            for load_sel in ["button:has-text('Load More')", "a:has-text('Load More')",
                             "button:has-text('Show More')", ".load-more"]:
                try:
                    btn = await page.query_selector(load_sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(2500)
                        page_num += 1
                        next_clicked = True
                        break
                except Exception:
                    continue

        if not next_clicked:
            print("    End of results (no more pages)")
            break


# ── Extract tabular data ────────────────────────────────────────────────────────
async def extract_table_data(page) -> list[dict]:
    """
    Extract any tabular order/invoice data from the current page.
    Reads table headers and rows, converting to a list of dicts.
    This data is saved to CSV for the ML model's training pipeline.
    """
    rows = []
    try:
        # Salesforce tables: standard HTML <table> or lightning-datatable
        tables = await page.query_selector_all("table")
        for table in tables:
            try:
                headers = []
                header_els = await table.query_selector_all("th")
                for th in header_els:
                    headers.append((await th.inner_text()).strip())

                if not headers:
                    continue

                row_els = await table.query_selector_all("tbody tr")
                for row_el in row_els:
                    cells = await row_el.query_selector_all("td")
                    if len(cells) == len(headers):
                        row = {}
                        for i, cell in enumerate(cells):
                            row[headers[i]] = (await cell.inner_text()).strip()
                        rows.append(row)
            except Exception:
                continue

        print(f"    Extracted {len(rows)} table rows")
    except Exception as e:
        print(f"    Table extraction error: {e}")
    return rows


# ── Main download function ──────────────────────────────────────────────────────
async def download_aah_orders():
    """
    Main coroutine. Orchestrates the full download flow:
    1. Load cookies (saved session → binary parse → browser_cookie3)
    2. Launch Chromium with injected cookies
    3. Check login status; prompt for manual login if needed
    4. Navigate to order/invoice pages, trying multiple URL candidates
    5. Intercept Salesforce API responses for structured data
    6. Download all PDFs with pagination
    7. Save structured data as CSV and JSON
    8. Save session for next run
    """
    from playwright.async_api import async_playwright

    downloaded: list[str] = []
    skipped:    list[str] = []
    all_table_rows: list[dict] = []
    api_captures: list[dict] = []

    async with async_playwright() as p:

        # ── Load best available cookies ────────────────────────────────────────
        print("Loading session cookies...")
        saved = load_saved_session()
        if saved:
            best_cookies = normalise_cookies(saved)
            print(f"  Using saved session ({len(best_cookies)} cookies)")
        else:
            raw = collect_all_cookies()
            best_cookies = normalise_cookies(raw)

        # ── Launch Chromium ────────────────────────────────────────────────────
        # headless=False so user can see the browser and intervene if needed
        print("\nLaunching Chromium...")
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            # Accept downloads automatically to the output directory
            accept_downloads=True,
        )

        # Inject cookies before any navigation so the session is active immediately
        if best_cookies:
            injected = 0
            for cookie in best_cookies:
                try:
                    await context.add_cookies([cookie])
                    injected += 1
                except Exception:
                    pass
            print(f"  Injected {injected}/{len(best_cookies)} cookies")

        # ── Set up API response interception ──────────────────────────────────
        # Do this before any navigation so we don't miss early API calls
        interceptor = APIInterceptor()

        # ── Open page and navigate to portal ─────────────────────────────────
        page = await context.new_page()
        page.on("response", interceptor.handle_response)

        print(f"\nNavigating to {PORTAL_HOME} ...")
        try:
            await page.goto(PORTAL_HOME, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"  ⚠️  Navigation error: {e}")

        current_url = page.url
        page_title  = await page.title()
        print(f"  URL:   {current_url}")
        print(f"  Title: {page_title}")

        # ── Check login status ─────────────────────────────────────────────────
        url_l   = current_url.lower()
        title_l = page_title.lower()
        body_l  = ""
        try:
            body_l = (await page.inner_text("body")).lower()
        except Exception:
            pass

        login_keywords   = ["login", "signin", "sign in", "password", "username"]
        logged_in_keywords = ["aahhub", "logout", "sign out", "my account", "welcome", "orders"]

        is_login_page = any(kw in url_l or kw in title_l or kw in body_l for kw in login_keywords)
        is_logged_in  = any(kw in url_l or kw in title_l or kw in body_l for kw in logged_in_keywords)

        if is_login_page or not is_logged_in:
            print("\n⚠️  Cookies did not transfer — not logged in.")
            print("   The browser is open. Please log in to AAH Hub manually.")
            print("   Once you're on the main AAH Hub page (after login), press ENTER here.")
            input("   Press ENTER when logged in > ")
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"  URL after login: {current_url}")
        else:
            print("  ✅ Logged in successfully via cookies")

        # Save session immediately after confirming login
        fresh_cookies = await context.cookies()
        save_session(fresh_cookies)

        # ── Navigate to invoice/order section ─────────────────────────────────
        print("\nSearching for invoice/order navigation...")

        # Try clicking navigation links first (more reliable than guessing URLs)
        nav_found = await find_and_click(page, [
            "a:has-text('Invoice History')",
            "a:has-text('Invoices')",
            "a:has-text('Invoice Delivery')",
            "a:has-text('Orders')",
            "a:has-text('Order History')",
            "a:has-text('Account Documents')",
            "a:has-text('Documents')",
            "nav a:has-text('Invoice')",
            "nav a:has-text('Order')",
            ".slds-nav a:has-text('Invoice')",
            "[role='navigation'] a:has-text('Invoice')",
        ], "invoice/orders navigation")

        if not nav_found:
            print("  Navigation link not found — trying candidate URLs...")
            # Try each candidate URL and stay on the first that looks like orders/invoices
            for url in CANDIDATE_PAGES:
                print(f"  Trying: {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2500)
                    final_url  = page.url
                    page_title = await page.title()
                    # Accept page if it loaded without redirecting to login
                    if not any(kw in final_url.lower() for kw in ["login", "error", "404"]):
                        print(f"    Landed on: {final_url}")
                        nav_found = True
                        break
                except Exception as e:
                    print(f"    ⚠️  {url}: {e}")

        if not nav_found:
            print("  ⚠️  Could not find orders/invoices page automatically.")
            print("  Please navigate to the invoices or orders section manually.")
            input("  Press ENTER when you're on the orders/invoices page > ")

        # Wait for Salesforce LWC components to finish loading
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            await page.wait_for_timeout(3000)

        print(f"  On page: {page.url}")

        # ── Set date filter ────────────────────────────────────────────────────
        print(f"\nSetting date filter: {DATE_FROM} to {DATE_TO}")
        date_set = await set_date_filter(page, DATE_FROM, DATE_TO)
        if date_set:
            await click_apply_filter(page)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                await page.wait_for_timeout(3000)
        else:
            print("  ⚠️  Could not set date filter — downloading all available documents")

        # ── Also check Invoice Delivery Settings section ───────────────────────
        # AAH Hub has a specific "Invoice Delivery Settings" feature that may list invoices
        print("\nChecking Invoice Delivery Settings section...")
        try:
            inv_settings = await page.query_selector(
                "a:has-text('Invoice Delivery Settings'), "
                "a:has-text('Invoice Settings'), "
                "[href*='invoice-delivery']"
            )
            if inv_settings:
                await inv_settings.click()
                await page.wait_for_timeout(3000)
                print("  Opened Invoice Delivery Settings")
                table_rows = await extract_table_data(page)
                all_table_rows.extend(table_rows)
                # Go back to main invoice list
                await page.go_back()
                await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  Invoice Delivery Settings: {e}")

        # ── Extract tabular data from current page ────────────────────────────
        print("\nExtracting tabular data...")
        table_rows = await extract_table_data(page)
        all_table_rows.extend(table_rows)

        # ── Download PDFs with pagination ─────────────────────────────────────
        print("\nStarting PDF download with pagination...")
        await paginate_and_download(page, context, downloaded, skipped)

        # ── Also download any PDF URLs captured via response interception ──────
        # These are PDFs that loaded in the background via XHR (not triggered by clicks)
        api_captures = interceptor.captured
        pdf_urls = list(set(interceptor.pdf_urls))  # Deduplicate

        if pdf_urls:
            print(f"\nDownloading {len(pdf_urls)} intercepted PDF URLs...")
            for pdf_url in pdf_urls:
                try:
                    resp = await page.goto(pdf_url, wait_until="domcontentloaded", timeout=20000)
                    if resp and resp.ok:
                        body = await resp.body()
                        fname = pdf_url.split("/")[-1].split("?")[0] or f"aah_intercepted_{int(time.time())}.pdf"
                        if not fname.endswith(".pdf"):
                            fname += ".pdf"
                        dest = PDF_DIR / fname
                        if not dest.exists():
                            dest.write_bytes(body)
                            downloaded.append(str(dest))
                            print(f"  ✅ Intercepted PDF: {fname}")
                        else:
                            skipped.append(fname)
                except Exception as e:
                    print(f"  ⚠️  Failed to download intercepted PDF: {e}")

        # ── Save API JSON data ────────────────────────────────────────────────
        if api_captures:
            timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
            api_outfile = API_DIR / f"api_responses_{timestamp}.json"
            try:
                with open(api_outfile, "w") as f:
                    json.dump(api_captures, f, indent=2, default=str)
                print(f"\n  Saved {len(api_captures)} API responses → {api_outfile}")
            except Exception as e:
                print(f"  ⚠️  API data save failed: {e}")

        # ── Save tabular data as CSV ──────────────────────────────────────────
        if all_table_rows:
            try:
                fieldnames = list(all_table_rows[0].keys())
                with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(all_table_rows)
                print(f"  Saved {len(all_table_rows)} rows → {CSV_FILE}")
            except Exception as e:
                print(f"  ⚠️  CSV save failed: {e}")

        # ── Save download log ─────────────────────────────────────────────────
        log = {
            "run_at":     datetime.now().isoformat(),
            "date_from":  DATE_FROM,
            "date_to":    DATE_TO,
            "portal":     PORTAL_HOME,
            "downloaded": downloaded,
            "skipped":    skipped,
            "total_downloaded": len(downloaded),
            "total_skipped":    len(skipped),
            "api_responses_captured": len(api_captures),
            "table_rows_extracted":   len(all_table_rows),
        }
        try:
            with open(LOG_FILE, "w") as f:
                json.dump(log, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Log save failed: {e}")

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print("AAH HUB DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"  PDFs downloaded:          {len(downloaded)}")
        print(f"  PDFs skipped (existing):  {len(skipped)}")
        print(f"  API responses captured:   {len(api_captures)}")
        print(f"  Table rows extracted:     {len(all_table_rows)}")
        print(f"  Output directory:         {BASE_DIR}")
        print(f"{'='*60}")

        print("\nKeeping browser open for 15 seconds for inspection...")
        await page.wait_for_timeout(15000)
        await browser.close()

    return downloaded


if __name__ == "__main__":
    print("=" * 60)
    print("AAH HUB ORDER & INVOICE DOWNLOADER")
    print(f"Portal:    {PORTAL_HOME}")
    print(f"Output:    {BASE_DIR}")
    print(f"Date from: {DATE_FROM}")
    print(f"Date to:   {DATE_TO}")
    print("=" * 60)
    print()
    print("NOTE: This is a Salesforce Experience Cloud portal.")
    print("      Data may load via XHR — API responses will be captured.")
    print()

    result = asyncio.run(download_aah_orders())
    print(f"\nDone. {len(result)} PDFs saved to {PDF_DIR}")
    print("Next step: python 23_parse_invoice_pdfs.py")
