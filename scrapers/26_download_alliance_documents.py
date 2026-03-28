"""
SCRIPT 26: Alliance Healthcare Document Downloader (Improved)
=============================================================
Downloads invoices, credit notes, and monthly statements from:
    https://my.alliance-healthcare.co.uk/group/pro/documents

Account: 1025850 — J MCGREGOR (CHEMIST) LIMITED
Portal:  Cencora / Alliance Healthcare My Account (Liferay-based portal)

Key improvements over script 22:
  - Navigates DIRECTLY to the /documents section (not the portal home)
  - Tries cookies for BOTH my.alliance-healthcare.co.uk AND .alliance-healthcare.co.uk
  - Clicks each document type tab: Invoices, Credit Notes, Monthly Statements
  - Uses context.expect_page() for pop-up downloads that open in a new window
  - Intercepts XHR/API calls to capture document metadata as structured JSON
  - Handles Liferay portal loading spinners via networkidle wait
  - Sets date range: 2021-03-01 to today (5 years)
  - Rotates through all document types systematically

Output:
    ~/Documents/NPT_Invoice_Data/alliance/raw_pdfs/      — PDF files
    ~/Documents/NPT_Invoice_Data/alliance/metadata.json  — document metadata
    ~/Documents/NPT_Invoice_Data/alliance/download_log.json

Usage:
    python 26_download_alliance_documents.py

First run: opens Chromium. Log in if prompted, press ENTER to continue.
Session saved to ~/Documents/NPT_Invoice_Data/sessions/alliance_session.json

IMPORTANT: Output is saved LOCALLY only — never committed to git.
"""

import asyncio
import json
import pathlib
import re
import struct
import sys
import time
from datetime import datetime, timedelta, date

# ── Paths ───────────────────────────────────────────────────────────────────────
BASE_DIR      = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data" / "alliance"
PDF_DIR       = BASE_DIR / "raw_pdfs"
SESSION_FILE  = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data" / "sessions" / "alliance_session.json"
LOG_FILE      = BASE_DIR / "download_log.json"
METADATA_FILE = BASE_DIR / "metadata.json"

for d in [PDF_DIR, SESSION_FILE.parent]:
    d.mkdir(parents=True, exist_ok=True)

# ── Portal URLs ─────────────────────────────────────────────────────────────────
PORTAL_HOME     = "https://my.alliance-healthcare.co.uk/group/pro"
DOCUMENTS_URL   = "https://my.alliance-healthcare.co.uk/group/pro/documents"

# Date range
DATE_FROM = date(2021, 3, 1)   # 5 years back
DATE_TO   = date.today()
DATE_FROM_STR = DATE_FROM.strftime("%Y-%m-%d")
DATE_TO_STR   = DATE_TO.strftime("%Y-%m-%d")
# Alliance portal may expect DD/MM/YYYY format
DATE_FROM_UK  = DATE_FROM.strftime("%d/%m/%Y")
DATE_TO_UK    = DATE_TO.strftime("%d/%m/%Y")

# Alliance domains to try for cookie extraction
ALLIANCE_DOMAINS = [
    "my.alliance-healthcare.co.uk",
    ".alliance-healthcare.co.uk",
    "alliance-healthcare.co.uk",
]

# Document type tabs to cycle through
DOCUMENT_TYPES = [
    {
        "name": "Invoices",
        "tab_selectors": [
            "a:has-text('Invoices')",
            "li:has-text('Invoices') a",
            "[data-tab='invoices']",
            "button:has-text('Invoices')",
            ".nav-tabs a:has-text('Invoice')",
            "#invoices-tab",
        ],
        "subfolder": "invoices",
    },
    {
        "name": "Credit Notes",
        "tab_selectors": [
            "a:has-text('Credit Notes')",
            "a:has-text('Credits')",
            "li:has-text('Credit') a",
            "[data-tab='credit']",
            "button:has-text('Credit')",
            ".nav-tabs a:has-text('Credit')",
            "#credit-notes-tab",
            "#credits-tab",
        ],
        "subfolder": "credit_notes",
    },
    {
        "name": "Monthly Statements",
        "tab_selectors": [
            "a:has-text('Monthly Statements')",
            "a:has-text('Statements')",
            "li:has-text('Statement') a",
            "[data-tab='statements']",
            "button:has-text('Statement')",
            ".nav-tabs a:has-text('Statement')",
            "#statements-tab",
            "#monthly-statements-tab",
        ],
        "subfolder": "statements",
    },
]


# ── Cookie helpers ──────────────────────────────────────────────────────────────
def get_safari_cookies_bc3(domain: str) -> list[dict]:
    """
    Use browser_cookie3 to read Safari cookies for a given domain.
    browser_cookie3 parses ~/Library/Cookies/Cookies.binarycookies.
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
    Parse Safari's binary cookie file (Cookies.binarycookies) directly.

    Format overview:
      - File header: 'cook' magic + big-endian page count + big-endian page sizes
      - Each page: little-endian cookie count + offsets + raw cookie structs
      - Cookie struct: flags, domain/name/path/value offsets, Mac-epoch expiry

    Mac epoch = seconds since 2001-01-01, differs from Unix epoch by 978307200.
    This direct parsing avoids browser_cookie3's decoding layer, which can
    garble cookie values when the binary format doesn't match expectations.
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
            if len(page_data) < 8 or struct.unpack("<I", page_data[0:4])[0] != 0x00000100:
                continue

            num_cookies = struct.unpack("<I", page_data[4:8])[0]
            offsets = [struct.unpack("<I", page_data[8 + i*4: 12 + i*4])[0] for i in range(num_cookies)]

            for coff in offsets:
                try:
                    c = page_data[coff:]
                    if len(c) < 56:
                        continue

                    flags      = struct.unpack("<I", c[8:12])[0]
                    domain_off = struct.unpack("<I", c[16:20])[0]
                    name_off   = struct.unpack("<I", c[20:24])[0]
                    path_off   = struct.unpack("<I", c[24:28])[0]
                    value_off  = struct.unpack("<I", c[28:32])[0]
                    expiry_mac = struct.unpack("<d", c[40:48])[0]

                    def cstr(buf, start):
                        end = buf.find(b"\x00", start)
                        return buf[start:end].decode("utf-8", errors="replace") if end != -1 else ""

                    domain = cstr(c, domain_off)
                    name   = cstr(c, name_off)
                    path   = cstr(c, path_off)
                    value  = cstr(c, value_off)

                    # Domain filter: check if target domain is contained in cookie domain or vice versa
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
    Gather cookies for all Alliance domain variants using both methods.
    Deduplicates by (name, domain), preferring binary parse.
    """
    print("  Collecting Safari cookies for Alliance Healthcare domains...")
    seen: dict[tuple, dict] = {}

    for domain in ALLIANCE_DOMAINS:
        for c in parse_safari_binary_cookies(domain):
            seen[(c["name"], c["domain"])] = c

    for domain in ALLIANCE_DOMAINS:
        for c in get_safari_cookies_bc3(domain):
            key = (c["name"], c["domain"])
            if key not in seen:
                seen[key] = c

    cookies = list(seen.values())
    print(f"  Total unique cookies: {len(cookies)}")
    return cookies


def normalise_cookies(cookies: list[dict]) -> list[dict]:
    """
    Sanitise cookie dicts for Playwright's add_cookies() which validates:
    - sameSite: must be 'Strict', 'Lax', or 'None' (case-sensitive)
    - expires: must be numeric
    - domain/name: must not be empty
    """
    valid_ss = {"Strict", "Lax", "None"}
    out = []
    for c in cookies:
        try:
            ss = str(c.get("sameSite", "None")).capitalize()
            if ss not in valid_ss:
                ss = "None"
            clean = {
                "name":     str(c.get("name", "")),
                "value":    str(c.get("value", "")),
                "domain":   str(c.get("domain", "")),
                "path":     str(c.get("path", "/")),
                "secure":   bool(c.get("secure", False)),
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
    Load persisted Playwright cookies. Sessions older than 8 hours are rejected
    because Alliance Healthcare's Liferay session tokens expire.
    """
    if not SESSION_FILE.exists():
        return []
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
        saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
        age_h    = (datetime.now() - saved_at).total_seconds() / 3600
        if age_h < 8:
            cookies = data.get("cookies", [])
            print(f"  Loaded saved session: {len(cookies)} cookies ({age_h:.1f}h old)")
            return cookies
        print(f"  Saved session is {age_h:.1f}h old — will refresh")
    except Exception as e:
        print(f"  Could not load session: {e}")
    return []


def save_session(cookies: list[dict]) -> None:
    """Persist Playwright context cookies to disk."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"saved_at": datetime.now().isoformat(), "cookies": cookies}, f, indent=2)
        print(f"  Session saved → {SESSION_FILE}")
    except Exception as e:
        print(f"  ⚠️  Session save failed: {e}")


# ── Metadata / API interceptor ─────────────────────────────────────────────────
class DocumentMetadataCapture:
    """
    Intercepts XHR/fetch responses from the Alliance portal's backend API.

    Alliance Healthcare's Cencora portal is Liferay-based and makes API calls to:
      /api/documents           — document list with metadata
      /api/invoices            — invoice-specific data
      /group/pro/documents/data — Liferay portlet data endpoint
      Any JSON response from alliance-healthcare.co.uk

    Capturing this metadata gives us structured data (invoice numbers, amounts,
    dates, document IDs) without having to parse PDFs — useful for the ML model.
    """

    def __init__(self):
        self.documents: list[dict] = []   # Structured document metadata records
        self.raw_responses: list[dict] = []  # All captured JSON responses
        self.pdf_urls: list[str] = []     # Direct PDF download URLs discovered

    def _is_document_api(self, url: str) -> bool:
        """Check if a URL looks like a document/invoice API endpoint."""
        patterns = [
            "/api/", "/documents", "/invoices", "/statements", "/credits",
            "json", "portal/data", "portlet", "/rest/",
        ]
        return any(p in url.lower() for p in patterns)

    def _extract_document_records(self, json_body) -> list[dict]:
        """
        Try to pull structured document records out of an API response.
        Alliance APIs return documents in various shapes — we try to normalise them
        into a consistent {id, type, date, amount, pdf_url, ...} schema.
        """
        records = []

        def walk(obj, depth=0):
            """Recursively walk the JSON tree looking for document-like objects."""
            if depth > 10:
                return
            if isinstance(obj, list):
                for item in obj:
                    walk(item, depth + 1)
            elif isinstance(obj, dict):
                # Heuristic: looks like a document record if it has date + (amount or number)
                has_date   = any(k in obj for k in ["date", "documentDate", "invoiceDate", "statementDate", "createdDate"])
                has_amount = any(k in obj for k in ["amount", "total", "value", "net", "gross", "invoiceTotal"])
                has_id     = any(k in obj for k in ["id", "documentId", "invoiceId", "reference", "invoiceNumber"])

                if (has_date or has_id) and (has_amount or has_id):
                    # Normalise to common schema
                    record = {
                        "source_keys": list(obj.keys()),
                        "id":       obj.get("id") or obj.get("documentId") or obj.get("invoiceId") or obj.get("reference"),
                        "type":     obj.get("type") or obj.get("documentType") or "unknown",
                        "date":     obj.get("date") or obj.get("documentDate") or obj.get("invoiceDate"),
                        "amount":   obj.get("amount") or obj.get("total") or obj.get("invoiceTotal"),
                        "currency": obj.get("currency", "GBP"),
                        "pdf_url":  obj.get("pdfUrl") or obj.get("downloadUrl") or obj.get("fileUrl"),
                        "raw":      obj,
                    }
                    records.append(record)

                    # If there's a PDF URL, capture it for download
                    if record["pdf_url"]:
                        self.pdf_urls.append(record["pdf_url"])
                else:
                    for v in obj.values():
                        walk(v, depth + 1)

        walk(json_body)
        return records

    async def handle_response(self, response) -> None:
        """Playwright response event handler — called for every network response."""
        try:
            url          = response.url
            status       = response.status
            content_type = response.headers.get("content-type", "")

            if status not in (200, 201):
                return

            # Intercept PDF responses
            if "pdf" in content_type.lower() or (
                "octet-stream" in content_type.lower() and ".pdf" in url.lower()
            ):
                self.pdf_urls.append(url)
                return

            # Intercept JSON API responses
            if not ("json" in content_type.lower() or self._is_document_api(url)):
                return

            try:
                body = await response.body()
                if len(body) < 5:
                    return
                text = body.decode("utf-8", errors="replace").strip()
                if not text.startswith(("{", "[")):
                    return

                json_body = json.loads(text)
                self.raw_responses.append({
                    "url":          url,
                    "status":       status,
                    "captured_at":  datetime.now().isoformat(),
                    "content_type": content_type,
                    "body":         json_body,
                })

                # Try to extract structured document records
                records = self._extract_document_records(json_body)
                if records:
                    self.documents.extend(records)
                    print(f"    API: captured {len(records)} document record(s) from {url[:70]}...")

            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Not valid JSON — skip

        except Exception:
            pass  # Ignore any handler errors to avoid breaking page navigation


# ── Date filter helpers ────────────────────────────────────────────────────────
async def apply_date_filter(page, date_from_str: str, date_to_str: str,
                             date_from_uk: str, date_to_uk: str) -> bool:
    """
    Attempt to set the date range filter on the documents page.
    Alliance Healthcare's portal may use:
      - ISO date inputs (yyyy-mm-dd)
      - UK date inputs (dd/mm/yyyy)
      - Date picker widgets
      - A dropdown for preset ranges
    Returns True if any date field was successfully set.
    """
    success = False

    # Attempt 1: HTML5 date inputs (most common modern approach)
    date_inputs = await page.query_selector_all("input[type='date']")
    if len(date_inputs) >= 1:
        try:
            await date_inputs[0].triple_click()
            await date_inputs[0].type(date_from_str)
            await page.keyboard.press("Tab")
            success = True
            print(f"    Set start date (ISO): {date_from_str}")
        except Exception:
            pass
    if len(date_inputs) >= 2:
        try:
            await date_inputs[1].triple_click()
            await date_inputs[1].type(date_to_str)
            await page.keyboard.press("Tab")
            print(f"    Set end date (ISO): {date_to_str}")
        except Exception:
            pass

    # Attempt 2: Text inputs that expect UK date format
    if not success:
        text_inputs = await page.query_selector_all(
            "input[placeholder*='dd/mm' i], "
            "input[placeholder*='date' i], "
            "input[name*='from' i], "
            "input[name*='start' i], "
            "input[id*='from' i], "
            "input[id*='start' i]"
        )
        if text_inputs:
            try:
                await text_inputs[0].triple_click()
                await text_inputs[0].type(date_from_uk)
                await page.keyboard.press("Tab")
                success = True
                print(f"    Set start date (UK): {date_from_uk}")
            except Exception:
                pass

    # Attempt 3: Look for a "5 years" or "All" preset in a date range dropdown
    if not success:
        for preset in ["5 Years", "Last 5 Years", "All", "All Time", "5Y", "Custom"]:
            try:
                el = await page.query_selector(
                    f"select option:has-text('{preset}'), "
                    f"button:has-text('{preset}'), "
                    f"a:has-text('{preset}'), "
                    f"li:has-text('{preset}')"
                )
                if el:
                    await el.click()
                    success = True
                    print(f"    Selected date preset: '{preset}'")
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                continue

    return success


async def click_filter_button(page) -> None:
    """Click the filter/search button to apply the date range."""
    for btn_text in ["Search", "Apply", "Filter", "Go", "Submit", "Retrieve", "Show"]:
        try:
            btn = await page.query_selector(
                f"button:has-text('{btn_text}'), "
                f"input[type='submit'][value='{btn_text}']"
            )
            if btn and await btn.is_visible() and not await btn.is_disabled():
                await btn.click()
                print(f"    Clicked filter button: '{btn_text}'")
                await page.wait_for_timeout(2000)
                return
        except Exception:
            continue


# ── Tab navigation ─────────────────────────────────────────────────────────────
async def click_document_tab(page, doc_type: dict) -> bool:
    """
    Click the tab for a given document type (Invoices, Credit Notes, Statements).
    Tries each selector in the tab_selectors list.
    Returns True if a tab was found and clicked.
    """
    print(f"\n  Switching to tab: {doc_type['name']}")
    for sel in doc_type["tab_selectors"]:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                print(f"    Clicked tab via selector: {sel}")
                # Wait for Liferay to update the content area
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    await page.wait_for_timeout(3000)
                return True
        except Exception:
            continue
    print(f"    ⚠️  Tab not found for: {doc_type['name']}")
    return False


# ── PDF download handlers ──────────────────────────────────────────────────────
async def download_single_element(page, context, el, pdf_dir: pathlib.Path,
                                   downloaded: list, skipped: list) -> bool:
    """
    Attempt to download the PDF associated with a single page element.

    Strategy 1: page.expect_download() — handles direct download triggers.
    Strategy 2: context.expect_page() — handles links that open a new tab/popup.
    Strategy 3: Direct href fetch — for <a href="...pdf"> links.

    Returns True if a new file was downloaded.
    """
    # Strategy 1: Standard download trigger
    try:
        async with page.expect_download(timeout=12000) as dl_info:
            await el.click()
        dl = await dl_info.value
        filename = dl.suggested_filename or f"alliance_{int(time.time())}.pdf"
        dest = pdf_dir / filename
        if not dest.exists():
            await dl.save_as(str(dest))
            downloaded.append(str(dest))
            print(f"    ✅ Downloaded: {filename}")
            return True
        else:
            skipped.append(filename)
            return False
    except Exception:
        pass

    # Strategy 2: Pop-up / new tab download
    try:
        async with context.expect_page(timeout=8000) as new_page_info:
            await el.click()
        new_page = await new_page_info.value
        try:
            await new_page.wait_for_load_state("domcontentloaded", timeout=15000)
            new_url  = new_page.url
            new_ct   = ""

            # Check the content type of the new page
            resp = await new_page.goto(new_url, timeout=15000)
            if resp:
                new_ct = resp.headers.get("content-type", "")
                if "pdf" in new_ct.lower() or "pdf" in new_url.lower():
                    body = await resp.body()
                    fname = new_url.split("/")[-1].split("?")[0]
                    if not fname.endswith(".pdf"):
                        fname = f"alliance_{int(time.time())}.pdf"
                    dest = pdf_dir / fname
                    if not dest.exists():
                        dest.write_bytes(body)
                        downloaded.append(str(dest))
                        print(f"    ✅ Downloaded (popup): {fname}")
                        await new_page.close()
                        return True
            await new_page.close()
        except Exception:
            try:
                await new_page.close()
            except Exception:
                pass
    except Exception:
        pass

    # Strategy 3: Read href and fetch directly (for static PDF links)
    try:
        href = await el.get_attribute("href")
        if href and (".pdf" in href.lower() or "download" in href.lower()):
            if href.startswith("/"):
                href = f"https://my.alliance-healthcare.co.uk{href}"
            resp = await page.goto(href, wait_until="domcontentloaded", timeout=20000)
            if resp and resp.ok:
                ct = resp.headers.get("content-type", "")
                if "pdf" in ct.lower() or "octet-stream" in ct.lower():
                    body = await resp.body()
                    fname = href.split("/")[-1].split("?")[0] or f"alliance_{int(time.time())}.pdf"
                    if not fname.endswith(".pdf"):
                        fname += ".pdf"
                    dest = pdf_dir / fname
                    if not dest.exists():
                        dest.write_bytes(body)
                        downloaded.append(str(dest))
                        print(f"    ✅ Downloaded (href): {fname}")
                        return True
                    else:
                        skipped.append(fname)
            # Go back to documents page after direct navigation
            await page.go_back()
            await page.wait_for_timeout(1500)
    except Exception:
        pass

    return False


async def download_all_on_page(page, context, pdf_dir: pathlib.Path,
                                 downloaded: list, skipped: list) -> int:
    """
    Find and download all PDF documents visible on the current page.
    Returns the count of new downloads.
    """
    count = 0
    download_selectors = [
        "a[href*='.pdf']",
        "a[href*='download']",
        "a[href*='/documents/']",
        "button:has-text('Download')",
        "a:has-text('Download')",
        "a:has-text('PDF')",
        "a:has-text('View PDF')",
        "a:has-text('Invoice')",
        "a[download]",
        "[data-type='pdf']",
        "[title*='Download' i]",
        "[title*='PDF' i]",
        "[aria-label*='Download' i]",
        "td a",    # Alliance portal tables often have download links in table cells
        "tr a[href]",
    ]

    seen_elements = set()  # Track by href to avoid clicking the same link twice

    for selector in download_selectors:
        try:
            elements = await page.query_selector_all(selector)
            if not elements:
                continue

            print(f"    Found {len(elements)} elements: {selector}")

            for el in elements:
                try:
                    # Avoid re-clicking elements we've already processed
                    el_href = await el.get_attribute("href") or ""
                    el_text = (await el.inner_text()).strip() if el_href == "" else el_href
                    el_key  = el_href or el_text
                    if el_key in seen_elements:
                        continue
                    seen_elements.add(el_key)

                    # Skip navigation links (they're not document downloads)
                    nav_texts = ["home", "menu", "login", "logout", "account", "profile", "help"]
                    if any(nav in el_text.lower() for nav in nav_texts):
                        continue

                    ok = await download_single_element(page, context, el, pdf_dir, downloaded, skipped)
                    if ok:
                        count += 1
                    await page.wait_for_timeout(600)

                except Exception:
                    continue

        except Exception:
            continue

    return count


async def paginate_and_download_tab(page, context, pdf_dir: pathlib.Path,
                                      downloaded: list, skipped: list) -> None:
    """
    Download all documents across all pages for the currently active tab.
    Handles Alliance's Liferay pagination patterns.
    """
    page_num  = 1
    max_pages = 500

    while page_num <= max_pages:
        print(f"\n    --- Tab page {page_num} ---")

        # Wait for content to fully load (Liferay uses JS-heavy rendering)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            await page.wait_for_timeout(2000)

        count = await download_all_on_page(page, context, pdf_dir, downloaded, skipped)
        if count == 0:
            print("    No new downloads on this page")

        # Navigate to next page
        next_clicked = False
        next_selectors = [
            "a:has-text('Next')",
            "button:has-text('Next')",
            "[aria-label='Next']",
            "[aria-label='Next page']",
            ".pagination-next a",
            ".next a",
            "li.next a",
            "a[rel='next']",
            ".portlet-pagination-next",
            "[class*='next'][href]",
        ]
        for sel in next_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    is_disabled = await btn.is_disabled()
                    is_visible  = await btn.is_visible()
                    if is_visible and not is_disabled:
                        await btn.click()
                        await page.wait_for_timeout(2500)
                        page_num += 1
                        next_clicked = True
                        break
            except Exception:
                continue

        if not next_clicked:
            print("    End of pages for this tab")
            break


# ── Main download coroutine ────────────────────────────────────────────────────
async def download_alliance_documents():
    """
    Main coroutine orchestrating the complete Alliance Healthcare document download.

    Flow:
      1. Load best available cookies
      2. Launch visible Chromium with cookies injected
      3. Navigate directly to /group/pro/documents
      4. Check login; prompt for manual login if needed
      5. Set date range filter (2021-03-01 to today)
      6. For each document type (Invoices, Credit Notes, Statements):
         a. Click the tab
         b. Set/reapply date filter
         c. Download all PDFs across all pages
      7. Download any additional PDFs discovered via API interception
      8. Save metadata JSON with all captured document records
      9. Save session and write download log
    """
    from playwright.async_api import async_playwright

    downloaded: list[str] = []
    skipped:    list[str] = []

    async with async_playwright() as p:

        # ── Load best available cookies ────────────────────────────────────────
        print("Loading session cookies...")
        saved = load_saved_session()
        if saved:
            best_cookies = normalise_cookies(saved)
        else:
            raw = collect_all_cookies()
            best_cookies = normalise_cookies(raw)
        print(f"  Best cookies to inject: {len(best_cookies)}")

        # ── Launch browser ────────────────────────────────────────────────────
        # headless=False is intentional — user needs to be able to log in manually
        # and also see that the scraper is working
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
            accept_downloads=True,
        )

        # Inject cookies before navigating — must be done on the context before
        # any page is opened so all pages in the context share the session
        if best_cookies:
            injected = 0
            for cookie in best_cookies:
                try:
                    await context.add_cookies([cookie])
                    injected += 1
                except Exception:
                    pass
            print(f"  Injected {injected}/{len(best_cookies)} cookies")

        # ── Set up metadata/API interception ─────────────────────────────────
        # Register this before creating any page so the first navigation is captured
        capture = DocumentMetadataCapture()

        page = await context.new_page()
        page.on("response", capture.handle_response)

        # ── Navigate directly to the documents section ─────────────────────────
        # This is the key improvement over script 22: we go straight to /documents
        # rather than the portal home, saving time and reducing risk of getting
        # redirected or lost in Liferay's navigation structure.
        print(f"\nNavigating directly to: {DOCUMENTS_URL}")
        try:
            await page.goto(DOCUMENTS_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"  ⚠️  Navigation error: {e}")
            # Fall back to portal home and navigate from there
            print(f"  Falling back to portal home: {PORTAL_HOME}")
            try:
                await page.goto(PORTAL_HOME, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
            except Exception as e2:
                print(f"  ⚠️  Fallback navigation also failed: {e2}")

        current_url = page.url
        page_title  = await page.title()
        print(f"  URL:   {current_url}")
        print(f"  Title: {page_title}")

        # ── Assess login status ───────────────────────────────────────────────
        url_l   = current_url.lower()
        title_l = page_title.lower()
        body_l  = ""
        try:
            body_l = (await page.inner_text("body")).lower()
        except Exception:
            pass

        login_kw     = ["login", "sign in", "signin", "username", "password", "c/portal/login"]
        logged_in_kw = ["pro", "1025850", "mcgregor", "logout", "sign out", "documents", "invoices"]

        is_login_page = any(kw in url_l or kw in title_l or kw in body_l for kw in login_kw)
        is_logged_in  = any(kw in url_l or kw in title_l or kw in body_l for kw in logged_in_kw)

        if is_login_page or not is_logged_in:
            print("\n⚠️  Not logged in — cookie transfer failed or session expired.")
            print("   The browser is open. Please log in to Alliance Healthcare.")
            print("   After login, navigate to: Documents (or Invoices)")
            print("   Then press ENTER here.")
            input("   Press ENTER when on the Documents page > ")
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"  URL after login: {current_url}")
        else:
            print("  ✅ Logged in via cookies")

        # Save session immediately so subsequent runs can reuse it
        fresh_cookies = await context.cookies()
        save_session(fresh_cookies)

        # ── Navigate to documents section if not already there ─────────────────
        if "documents" not in page.url.lower() and "invoice" not in page.url.lower():
            print("\nLooking for Documents navigation link...")
            for sel in [
                "a:has-text('Documents')",
                "a:has-text('My Documents')",
                "nav a:has-text('Document')",
                "[href*='/documents']",
                "[href*='documents']",
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await page.wait_for_timeout(3000)
                        print(f"  Clicked documents link: {sel}")
                        break
                except Exception:
                    continue

        # Try networkidle to let the Liferay portal finish loading its portlets
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            await page.wait_for_timeout(3000)

        print(f"\nOn page: {page.url}")

        # ── Iterate through each document type tab ─────────────────────────────
        all_tab_pdfs: dict[str, list[str]] = {}

        for doc_type in DOCUMENT_TYPES:
            print(f"\n{'─'*50}")
            print(f"DOCUMENT TYPE: {doc_type['name']}")
            print(f"{'─'*50}")

            # Create a subdirectory for this document type to keep things organised
            type_pdf_dir = PDF_DIR / doc_type["subfolder"]
            type_pdf_dir.mkdir(parents=True, exist_ok=True)

            tab_downloaded: list[str] = []
            tab_skipped:    list[str] = []

            # Click the tab for this document type
            tab_found = await click_document_tab(page, doc_type)

            if not tab_found:
                print(f"  ⚠️  Could not find '{doc_type['name']}' tab — trying to continue anyway")
                # Even if we couldn't find the specific tab, try downloading whatever is visible

            # ── Set date filter for this tab ──────────────────────────────────
            print(f"\n  Setting date filter: {DATE_FROM_STR} to {DATE_TO_STR}")
            date_set = await apply_date_filter(
                page, DATE_FROM_STR, DATE_TO_STR, DATE_FROM_UK, DATE_TO_UK
            )
            if date_set:
                await click_filter_button(page)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    await page.wait_for_timeout(3000)
            else:
                print("  ⚠️  Could not set date filter — all available documents will be downloaded")

            # ── Download with pagination ──────────────────────────────────────
            print(f"\n  Downloading {doc_type['name']} with pagination...")
            await paginate_and_download_tab(
                page, context, type_pdf_dir, tab_downloaded, tab_skipped
            )

            downloaded.extend(tab_downloaded)
            skipped.extend(tab_skipped)
            all_tab_pdfs[doc_type["name"]] = tab_downloaded

            print(f"\n  {doc_type['name']}: {len(tab_downloaded)} downloaded, {len(tab_skipped)} skipped")

        # ── Download PDFs discovered via API interception ──────────────────────
        # Some documents may only be accessible via URLs captured from XHR responses
        # rather than visible links on the page
        discovered_pdf_urls = list(set(capture.pdf_urls))
        if discovered_pdf_urls:
            print(f"\n{'─'*50}")
            print(f"Downloading {len(discovered_pdf_urls)} PDF(s) discovered via API interception...")
            for pdf_url in discovered_pdf_urls:
                try:
                    # Ensure the URL is absolute
                    if pdf_url.startswith("/"):
                        pdf_url = f"https://my.alliance-healthcare.co.uk{pdf_url}"

                    resp = await page.goto(pdf_url, wait_until="domcontentloaded", timeout=20000)
                    if resp and resp.ok:
                        ct = resp.headers.get("content-type", "")
                        if "pdf" in ct.lower() or "octet-stream" in ct.lower():
                            body = await resp.body()
                            fname = pdf_url.split("/")[-1].split("?")[0]
                            if not fname.endswith(".pdf"):
                                fname = f"alliance_api_{int(time.time())}.pdf"
                            dest = PDF_DIR / fname
                            if not dest.exists():
                                dest.write_bytes(body)
                                downloaded.append(str(dest))
                                print(f"  ✅ API PDF: {fname}")
                            else:
                                skipped.append(fname)
                except Exception as e:
                    print(f"  ⚠️  API PDF download failed: {e}")

        # ── Save metadata JSON ─────────────────────────────────────────────────
        # This structured metadata is what the ML model (script 10/12) will use
        # to build features without needing to re-parse PDFs
        metadata = {
            "extracted_at":      datetime.now().isoformat(),
            "date_from":         DATE_FROM_STR,
            "date_to":           DATE_TO_STR,
            "account":           "1025850 — J MCGREGOR (CHEMIST) LIMITED",
            "portal":            DOCUMENTS_URL,
            "document_records":  capture.documents,
            "api_responses":     [
                {k: v for k, v in r.items() if k != "body"}  # Exclude body for size
                for r in capture.raw_responses
            ],
            "total_api_responses":     len(capture.raw_responses),
            "total_document_records":  len(capture.documents),
        }
        try:
            with open(METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)
            print(f"\n  Metadata saved → {METADATA_FILE}")
            print(f"  Document records captured: {len(capture.documents)}")
            print(f"  API responses captured:    {len(capture.raw_responses)}")
        except Exception as e:
            print(f"\n  ⚠️  Metadata save failed: {e}")

        # ── Save download log ──────────────────────────────────────────────────
        log = {
            "run_at":         datetime.now().isoformat(),
            "date_from":      DATE_FROM_STR,
            "date_to":        DATE_TO_STR,
            "portal":         DOCUMENTS_URL,
            "account":        "1025850",
            "downloaded":     downloaded,
            "skipped":        skipped,
            "per_type":       {k: len(v) for k, v in all_tab_pdfs.items()},
            "total_downloaded": len(downloaded),
            "total_skipped":    len(skipped),
            "metadata_records": len(capture.documents),
        }
        try:
            with open(LOG_FILE, "w") as f:
                json.dump(log, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Log save failed: {e}")

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print("ALLIANCE HEALTHCARE DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"  Total PDFs downloaded:     {len(downloaded)}")
        print(f"  Skipped (already exist):   {len(skipped)}")
        print(f"  Metadata records captured: {len(capture.documents)}")
        for doc_type_name, files in all_tab_pdfs.items():
            print(f"    {doc_type_name}: {len(files)} files")
        print(f"  Output directory:          {BASE_DIR}")
        print(f"{'='*60}")

        print("\nKeeping browser open for 15 seconds...")
        await page.wait_for_timeout(15000)
        await browser.close()

    return downloaded


if __name__ == "__main__":
    print("=" * 60)
    print("ALLIANCE HEALTHCARE DOCUMENT DOWNLOADER (IMPROVED)")
    print(f"Portal:    {DOCUMENTS_URL}")
    print(f"Account:   1025850 — J MCGREGOR (CHEMIST) LIMITED")
    print(f"Output:    {BASE_DIR}")
    print(f"Date from: {DATE_FROM_STR}")
    print(f"Date to:   {DATE_TO_STR}")
    print("=" * 60)
    print()
    print("Document types: Invoices, Credit Notes, Monthly Statements")
    print("API interception: enabled (captures document metadata as JSON)")
    print()

    result = asyncio.run(download_alliance_documents())
    print(f"\nDone. {len(result)} documents saved to {PDF_DIR}")
    print("Next step: python 23_parse_invoice_pdfs.py")
