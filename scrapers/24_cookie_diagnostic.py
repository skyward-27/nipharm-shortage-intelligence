"""
SCRIPT 24: Cookie & Session Diagnostic Tool
============================================
Standalone diagnostic that tests whether Safari cookies can be transferred
to a Playwright Chromium browser for both pharmacy portals.

The root problem: browser_cookie3 reads from Safari's binary cookie store
but Chromium often rejects the transferred cookies because:
  1. The cookie domain doesn't match exactly (www. vs .)
  2. The SameSite or Secure flags mismatch
  3. Safari stores cookies in a binary format that browser_cookie3 may partially misread

This script tests ALL approaches in sequence and reports exactly what works.

Output:
    ~/Documents/NPT_Invoice_Data/diagnostics/cookie_diagnostic_<timestamp>.json
    ~/Documents/NPT_Invoice_Data/sessions/aah_session.json
    ~/Documents/NPT_Invoice_Data/sessions/alliance_session.json

Usage:
    python 24_cookie_diagnostic.py

First run: opens two browser windows (one per portal). Log in manually if
cookies fail, then press ENTER. Saved sessions are used on future runs.

IMPORTANT: Output is saved LOCALLY only — never committed to git.
"""

import asyncio
import json
import os
import pathlib
import platform
import struct
import sys
import time
from datetime import datetime

# ── Paths ───────────────────────────────────────────────────────────────────────
BASE_DIR       = pathlib.Path.home() / "Documents" / "NPT_Invoice_Data"
DIAG_DIR       = BASE_DIR / "diagnostics"
SESSION_DIR    = BASE_DIR / "sessions"
DIAG_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Both portals under test
PORTALS = [
    {
        "name": "AAH Hub",
        "url": "https://www.aah.co.uk/s/aahhub",
        "domains": ["www.aah.co.uk", ".aah.co.uk", "aah.co.uk"],
        "logged_in_indicators": ["aahhub", "logout", "my account", "orders"],
        "login_indicators": ["login", "signin", "sign in", "username", "password"],
        "session_file": SESSION_DIR / "aah_session.json",
    },
    {
        "name": "Alliance Healthcare",
        "url": "https://my.alliance-healthcare.co.uk/group/pro",
        "domains": ["my.alliance-healthcare.co.uk", ".alliance-healthcare.co.uk", "alliance-healthcare.co.uk"],
        "logged_in_indicators": ["pro", "1025850", "mcgregor", "logout", "documents"],
        "login_indicators": ["login", "signin", "sign in", "username", "password"],
        "session_file": SESSION_DIR / "alliance_session.json",
    },
]


# ── Approach 1: browser_cookie3 (standard) ─────────────────────────────────────
def try_browser_cookie3(domain: str) -> list[dict]:
    """
    Use browser_cookie3 to read Safari's cookie database for a given domain.
    browser_cookie3 locates ~/Library/Cookies/Cookies.binarycookies and decodes it.
    Returns a list of Playwright-compatible cookie dicts.
    """
    try:
        import browser_cookie3
        jar = browser_cookie3.safari(domain_name=domain)
        cookies = []
        for c in jar:
            # Playwright requires 'sameSite' to be 'Strict', 'Lax', or 'None'
            same_site = "None"
            try:
                # browser_cookie3 may expose same_site attribute
                if hasattr(c, "same_site") and c.same_site:
                    raw = str(c.same_site).lower()
                    if "strict" in raw:
                        same_site = "Strict"
                    elif "lax" in raw:
                        same_site = "Lax"
            except Exception:
                pass

            cookie = {
                "name": c.name,
                "value": c.value,
                "domain": c.domain if c.domain else domain,
                "path": c.path if c.path else "/",
                "secure": bool(getattr(c, "secure", True)),
                "httpOnly": bool(getattr(c, "has_nonstandard_attr", lambda x: False)("HttpOnly")),
                "sameSite": same_site,
            }
            # Only include expiry if it exists and is in the future
            if c.expires and c.expires > time.time():
                cookie["expires"] = int(c.expires)
            cookies.append(cookie)
        return cookies
    except ImportError:
        print("  ⚠️  browser_cookie3 not installed — run: pip install browser_cookie3")
        return []
    except Exception as e:
        print(f"  ⚠️  browser_cookie3 failed for {domain}: {e}")
        return []


# ── Approach 2: Read Safari binary cookie file directly ─────────────────────────
def parse_safari_binary_cookies(domain_filter=None):  # type: (str | None) -> list[dict]  # noqa
    """
    Directly parse Safari's binary Cookies.binarycookies file.

    The binary format:
      - 4-byte magic: 'cook'
      - 4-byte big-endian int: number of pages
      - n * 4-byte big-endian ints: page sizes
      - page data blocks

    Each page:
      - 4-byte magic: 0x00000100
      - 4-byte little-endian int: number of cookies
      - n * 4-byte little-endian ints: cookie offsets
      - cookie records

    Each cookie record is a struct with fixed offsets for name, value, domain, path.

    This is more reliable than browser_cookie3 for macOS because it bypasses
    the Python library's own parsing layer which sometimes garbles values.
    """
    cookie_file = pathlib.Path.home() / "Library" / "Cookies" / "Cookies.binarycookies"
    if not cookie_file.exists():
        print(f"  ⚠️  Safari cookie file not found: {cookie_file}")
        return []

    cookies = []
    try:
        with open(cookie_file, "rb") as f:
            data = f.read()

        # Validate magic header 'cook'
        if data[:4] != b"cook":
            print("  ⚠️  Not a valid Safari binary cookie file (bad magic)")
            return []

        # Number of pages (big-endian)
        num_pages = struct.unpack(">I", data[4:8])[0]

        # Page sizes array — each is a big-endian uint32
        page_sizes = []
        offset = 8
        for _ in range(num_pages):
            page_size = struct.unpack(">I", data[offset:offset + 4])[0]
            page_sizes.append(page_size)
            offset += 4

        # Parse each page
        for page_size in page_sizes:
            page_data = data[offset:offset + page_size]
            offset += page_size

            if len(page_data) < 8:
                continue

            # Page magic (little-endian, should be 0x00000100)
            page_magic = struct.unpack("<I", page_data[0:4])[0]
            if page_magic != 0x00000100:
                continue

            num_cookies_in_page = struct.unpack("<I", page_data[4:8])[0]

            # Cookie offsets within this page
            cookie_offsets = []
            for i in range(num_cookies_in_page):
                coff = struct.unpack("<I", page_data[8 + i * 4: 12 + i * 4])[0]
                cookie_offsets.append(coff)

            # Parse each cookie
            for coff in cookie_offsets:
                try:
                    c_data = page_data[coff:]
                    if len(c_data) < 56:
                        continue

                    # Cookie struct layout (all little-endian):
                    # 0:  uint32 cookie_size
                    # 4:  uint32 unknown1
                    # 8:  uint32 flags (1=secure, 4=httponly)
                    # 12: uint32 unknown2
                    # 16: uint32 domain_offset
                    # 20: uint32 name_offset
                    # 24: uint32 path_offset
                    # 28: uint32 value_offset
                    # 32: uint32 comment_offset (often 0)
                    # 36: uint32 comment_url_offset (often 0)
                    # 40: float64 expiry (Mac epoch: Jan 1 2001)
                    # 48: float64 creation (Mac epoch)

                    cookie_size    = struct.unpack("<I", c_data[0:4])[0]
                    flags          = struct.unpack("<I", c_data[8:12])[0]
                    domain_off     = struct.unpack("<I", c_data[16:20])[0]
                    name_off       = struct.unpack("<I", c_data[20:24])[0]
                    path_off       = struct.unpack("<I", c_data[24:28])[0]
                    value_off      = struct.unpack("<I", c_data[28:32])[0]
                    expiry_mac     = struct.unpack("<d", c_data[40:48])[0]

                    # Convert Mac epoch (2001-01-01) to Unix epoch (1970-01-01)
                    # Difference = 978307200 seconds
                    expiry_unix = int(expiry_mac) + 978307200 if expiry_mac > 0 else 0

                    def read_cstr(buf, start):
                        """Read null-terminated string from byte buffer at position start."""
                        end = buf.find(b"\x00", start)
                        if end == -1:
                            return buf[start:].decode("utf-8", errors="replace")
                        return buf[start:end].decode("utf-8", errors="replace")

                    domain = read_cstr(c_data, domain_off)
                    name   = read_cstr(c_data, name_off)
                    path   = read_cstr(c_data, path_off)
                    value  = read_cstr(c_data, value_off)

                    # Apply domain filter
                    if domain_filter:
                        # Normalise: strip leading dot for comparison
                        filter_bare = domain_filter.lstrip(".")
                        domain_bare = domain.lstrip(".")
                        if filter_bare not in domain_bare and domain_bare not in filter_bare:
                            continue

                    is_secure   = bool(flags & 1)
                    is_httponly = bool(flags & 4)

                    cookie = {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path if path else "/",
                        "secure": is_secure,
                        "httpOnly": is_httponly,
                        "sameSite": "None",
                    }
                    if expiry_unix > time.time():
                        cookie["expires"] = expiry_unix

                    if name and domain:  # Skip blank/corrupt entries
                        cookies.append(cookie)

                except Exception:
                    # Individual cookie parse failure — skip and continue
                    continue

    except Exception as e:
        print(f"  ⚠️  Binary cookie parse error: {e}")

    return cookies


# ── Approach 3: keyring ────────────────────────────────────────────────────────
def try_keyring(service_hint: str) -> list[dict]:
    """
    Check macOS Keychain via the keyring library for stored credentials.
    Keychain doesn't store session cookies directly, but may have auth tokens
    or OAuth refresh tokens stored by the browser.
    Returns empty list (with a note) since keychain stores credentials not cookies.
    """
    try:
        import keyring
        # Keychain is for credentials (username/password), not browser session cookies.
        # We attempt a lookup but this almost never yields session cookies.
        result = keyring.get_password(service_hint, "")
        if result:
            print(f"  ℹ️  Keyring found something for '{service_hint}' (likely a credential, not a session cookie)")
        else:
            print(f"  ℹ️  Keyring: no entry for '{service_hint}' — expected, session cookies aren't stored here")
        return []
    except ImportError:
        print("  ℹ️  keyring not installed — install with: pip install keyring")
        return []
    except Exception as e:
        print(f"  ℹ️  keyring lookup failed: {e}")
        return []


# ── Saved session loader ────────────────────────────────────────────────────────
def load_saved_session(session_file: pathlib.Path, max_age_hours: int = 8) -> list[dict]:
    """
    Load a previously saved Playwright session (list of cookie dicts).
    Rejects sessions older than max_age_hours to avoid using expired cookies.
    """
    if not session_file.exists():
        return []
    try:
        with open(session_file) as f:
            data = json.load(f)
        saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
        age_seconds = (datetime.now() - saved_at).total_seconds()
        if age_seconds < max_age_hours * 3600:
            cookies = data.get("cookies", [])
            print(f"  Loaded saved session ({len(cookies)} cookies, {age_seconds/3600:.1f}h old)")
            return cookies
        else:
            print(f"  Saved session is {age_seconds/3600:.1f}h old — too stale, ignoring")
    except Exception as e:
        print(f"  ⚠️  Could not load saved session: {e}")
    return []


def save_session(session_file: pathlib.Path, cookies: list[dict]) -> None:
    """Persist Playwright cookies to disk for reuse across runs."""
    try:
        with open(session_file, "w") as f:
            json.dump({"saved_at": datetime.now().isoformat(), "cookies": cookies}, f, indent=2)
        print(f"  Session saved → {session_file}")
    except Exception as e:
        print(f"  ⚠️  Could not save session: {e}")


# ── Cookie normaliser ───────────────────────────────────────────────────────────
def normalise_cookies_for_playwright(cookies: list[dict]) -> list[dict]:
    """
    Playwright's add_cookies() is strict about cookie field values.
    This function sanitises each cookie dict to match what Playwright expects:
    - sameSite must be 'Strict', 'Lax', or 'None' (not None, not 'none')
    - expires must be a number (int or float), not a string
    - domain must not be empty
    - Removes any unknown keys that would cause validation errors
    """
    valid_same_site = {"Strict", "Lax", "None"}
    cleaned = []
    for c in cookies:
        try:
            same_site = str(c.get("sameSite", "None")).capitalize()
            if same_site not in valid_same_site:
                same_site = "None"

            clean = {
                "name": str(c.get("name", "")),
                "value": str(c.get("value", "")),
                "domain": str(c.get("domain", "")),
                "path": str(c.get("path", "/")),
                "secure": bool(c.get("secure", False)),
                "httpOnly": bool(c.get("httpOnly", False)),
                "sameSite": same_site,
            }
            # Only include expires if it's a valid future timestamp
            expires = c.get("expires")
            if expires is not None:
                try:
                    expires_int = int(float(expires))
                    if expires_int > time.time():
                        clean["expires"] = expires_int
                except (ValueError, TypeError):
                    pass

            # Skip cookies with no name or domain
            if clean["name"] and clean["domain"]:
                cleaned.append(clean)
        except Exception:
            continue
    return cleaned


# ── Core diagnostic per portal ─────────────────────────────────────────────────
async def diagnose_portal(playwright, portal: dict) -> dict:
    """
    Run all cookie-transfer approaches for one portal and return a structured
    diagnostic report dict.

    Steps:
      1. Collect cookies via each approach (saved session, browser_cookie3, binary parse)
      2. Launch Chromium, inject best available cookies
      3. Navigate to portal URL
      4. Check whether we're logged in
      5. If not logged in: keep browser open for manual login, then save the session
      6. Return full report
    """
    report = {
        "portal": portal["name"],
        "url": portal["url"],
        "tested_at": datetime.now().isoformat(),
        "approaches": {},
        "cookies_injected": 0,
        "login_status": "unknown",
        "final_url": "",
        "page_title": "",
        "cookie_names_found": [],
        "session_saved": False,
        "errors": [],
    }

    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {portal['name']}")
    print(f"URL: {portal['url']}")
    print(f"{'='*60}")

    # ── Step 1: Try saved session first (fastest, most reliable) ──────────────
    print("\n[1] Checking saved session...")
    saved_cookies = load_saved_session(portal["session_file"])
    report["approaches"]["saved_session"] = {
        "found": len(saved_cookies),
        "used": False,
    }

    # ── Step 2: browser_cookie3 for all domain variants ───────────────────────
    print("\n[2] Trying browser_cookie3 for each domain variant...")
    bc3_all = []
    for domain in portal["domains"]:
        print(f"  domain: {domain}")
        cookies = try_browser_cookie3(domain)
        bc3_all.extend(cookies)
        report["approaches"].setdefault("browser_cookie3", {})[domain] = len(cookies)

    # Deduplicate by (name, domain) keeping last seen
    seen = {}
    for c in bc3_all:
        seen[(c["name"], c["domain"])] = c
    bc3_deduped = list(seen.values())
    print(f"  Total unique cookies via browser_cookie3: {len(bc3_deduped)}")

    # ── Step 3: Binary parse for all domain variants ──────────────────────────
    print("\n[3] Parsing Safari binary cookie file directly...")
    binary_all = []
    for domain in portal["domains"]:
        cookies = parse_safari_binary_cookies(domain_filter=domain)
        binary_all.extend(cookies)
        report["approaches"].setdefault("binary_parse", {})[domain] = len(cookies)

    seen2 = {}
    for c in binary_all:
        seen2[(c["name"], c["domain"])] = c
    binary_deduped = list(seen2.values())
    print(f"  Total unique cookies via binary parse: {len(binary_deduped)}")

    # ── Step 4: keyring (informational only) ──────────────────────────────────
    print("\n[4] Checking keyring...")
    for domain in portal["domains"][:1]:  # Only check once per portal
        try_keyring(domain)

    # ── Step 5: Pick the best cookie set to inject ────────────────────────────
    # Priority: saved session > binary parse > browser_cookie3
    # Binary parse is preferred over browser_cookie3 because it bypasses
    # browser_cookie3's own decoding layer which can corrupt cookie values.
    if saved_cookies:
        best_cookies = saved_cookies
        best_source  = "saved_session"
        report["approaches"]["saved_session"]["used"] = True
    elif binary_deduped:
        best_cookies = binary_deduped
        best_source  = "binary_parse"
    elif bc3_deduped:
        best_cookies = bc3_deduped
        best_source  = "browser_cookie3"
    else:
        best_cookies = []
        best_source  = "none"

    best_cookies = normalise_cookies_for_playwright(best_cookies)
    report["cookie_source_used"] = best_source
    print(f"\n  Best cookie source: {best_source} ({len(best_cookies)} cookies)")

    # ── Step 6: Launch browser and test ───────────────────────────────────────
    print(f"\n[5] Launching Chromium browser...")
    try:
        browser = await playwright.chromium.launch(
            headless=False,  # Visible so user can see what's happening and log in if needed
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        # Inject cookies before navigating — this is the key transfer step
        injected_count = 0
        if best_cookies:
            print(f"  Injecting {len(best_cookies)} cookies...")
            for cookie in best_cookies:
                try:
                    await context.add_cookies([cookie])
                    injected_count += 1
                except Exception as e:
                    # Log individual cookie injection failures (often due to domain mismatch)
                    report["errors"].append(f"Cookie injection failed: {cookie.get('name')} — {e}")

            print(f"  Injected {injected_count}/{len(best_cookies)} cookies successfully")
            report["cookies_injected"] = injected_count
            report["cookie_names_found"] = [c["name"] for c in best_cookies]

        page = await context.new_page()

        # Navigate to portal
        print(f"\n  Navigating to {portal['url']} ...")
        try:
            await page.goto(portal["url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            report["errors"].append(f"Navigation error: {e}")
            print(f"  ⚠️  Navigation error: {e}")

        final_url   = page.url
        page_title  = await page.title()
        page_text   = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""

        report["final_url"]  = final_url
        report["page_title"] = page_title

        print(f"  Final URL:   {final_url}")
        print(f"  Page title:  {page_title}")

        # Determine login status
        url_lower  = final_url.lower()
        title_lower = page_title.lower()

        is_login_page = any(
            kw in url_lower or kw in title_lower or kw in page_text
            for kw in portal["login_indicators"]
        )
        is_logged_in = any(
            kw in url_lower or kw in title_lower or kw in page_text
            for kw in portal["logged_in_indicators"]
        )

        if is_logged_in and not is_login_page:
            report["login_status"] = "logged_in"
            print(f"\n  ✅ SUCCESS — Logged in to {portal['name']}!")
        else:
            report["login_status"] = "not_logged_in"
            print(f"\n  ❌ NOT logged in — cookies did not transfer (or session expired)")
            print(f"\n  MANUAL LOGIN: The browser is open for {portal['name']}.")
            print(f"  Please log in now, navigate to the main portal page, then")
            print(f"  press ENTER here to save your session for future runs.")
            input(f"  Press ENTER when logged in to {portal['name']} > ")
            await page.wait_for_timeout(2000)

            # Re-check status after manual login
            final_url  = page.url
            page_title = await page.title()
            report["final_url"]  = final_url
            report["page_title"] = page_title
            report["login_status"] = "logged_in_manually"
            print(f"  URL after login: {final_url}")

        # Save session regardless of how we got in
        all_cookies = await context.cookies()
        save_session(portal["session_file"], all_cookies)
        report["session_saved"] = True
        report["session_file"]  = str(portal["session_file"])

        print(f"\n  Closing browser in 3 seconds...")
        await page.wait_for_timeout(3000)
        await browser.close()

    except Exception as e:
        report["errors"].append(f"Browser error: {e}")
        print(f"  ❌ Browser error: {e}")

    return report


# ── Main entry point ───────────────────────────────────────────────────────────
async def run_diagnostics():
    """
    Run full diagnostic for both portals sequentially (not parallel, so the
    user can focus on one browser at a time for manual login if needed).
    """
    from playwright.async_api import async_playwright

    print("=" * 60)
    print("COOKIE & SESSION DIAGNOSTIC TOOL")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python:   {sys.version.split()[0]}")
    print(f"Run at:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    print("This tool tests whether Safari session cookies can be transferred")
    print("to Playwright Chromium for your pharmacy portals.")
    print()

    all_reports = []

    async with async_playwright() as playwright:
        for portal in PORTALS:
            report = await diagnose_portal(playwright, portal)
            all_reports.append(report)

    # ── Print summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("DIAGNOSTIC SUMMARY")
    print(f"{'='*60}")

    for report in all_reports:
        status_icon = "✅" if "logged_in" in report["login_status"] else "❌"
        print(f"\n{status_icon} {report['portal']}")
        print(f"   Status:        {report['login_status']}")
        print(f"   Cookie source: {report.get('cookie_source_used', 'none')}")
        print(f"   Injected:      {report['cookies_injected']} cookies")
        print(f"   Cookie names:  {', '.join(report['cookie_names_found'][:5]) or 'none'}"
              + (" ..." if len(report['cookie_names_found']) > 5 else ""))
        print(f"   Final URL:     {report['final_url']}")
        print(f"   Session saved: {'Yes → ' + report.get('session_file', '') if report['session_saved'] else 'No'}")
        if report["errors"]:
            print(f"   Errors ({len(report['errors'])}):")
            for err in report["errors"][:3]:
                print(f"     - {err}")

    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")

    any_failed = any("not_logged_in" in r["login_status"] for r in all_reports)
    if any_failed:
        print("""
  Cookie transfer from Safari to Chromium failed for one or more portals.

  Common causes & fixes:

  1. Safari doesn't share cookies with Chromium natively.
     FIX: Use the manual login path (script keeps browser open) — session
          is then saved to JSON and reused automatically.

  2. browser_cookie3 needs Full Disk Access.
     FIX: System Settings → Privacy & Security → Full Disk Access → add Terminal.

  3. Cookies use domain '.aah.co.uk' but injection uses 'www.aah.co.uk'.
     FIX: The binary parser tries both — check diagnostic JSON for which worked.

  4. Session cookies have expired.
     FIX: Log in via Safari, then immediately re-run this diagnostic.

  Next step: scripts 25 and 26 will prompt for manual login automatically.
""")
    else:
        print("""
  ✅ All portals reachable. Session files saved.

  Next steps:
    python 25_download_aah_orders.py     — download AAH Hub invoices/orders
    python 26_download_alliance_documents.py — download Alliance docs
""")

    # ── Save full report to JSON ───────────────────────────────────────────────
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = DIAG_DIR / f"cookie_diagnostic_{timestamp}.json"
    try:
        with open(report_path, "w") as f:
            json.dump(all_reports, f, indent=2, default=str)
        print(f"  Full report saved → {report_path}")
    except Exception as e:
        print(f"  ⚠️  Could not save report: {e}")

    return all_reports


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
