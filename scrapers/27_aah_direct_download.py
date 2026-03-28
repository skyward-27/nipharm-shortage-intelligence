"""
27_aah_direct_download.py
─────────────────────────
Simple direct downloader for AAH Retrieved Documents
(assumes you're already logged in and on the page)

Just downloads all documents from the current Retrieved Documents page.
"""

import pathlib, json, datetime, time, shutil, tempfile
from playwright.sync_api import sync_playwright

OUT_DIR = pathlib.Path.home() / "Documents/NPT_Invoice_Data/aah_hub/pdfs"
META_FILE = pathlib.Path.home() / "Documents/NPT_Invoice_Data/aah_hub/metadata.json"
CHROME_PROFILE = pathlib.Path.home() / "Library/Application Support/Google/Chrome/Default"
SESSION_COPY_DIR = pathlib.Path(tempfile.gettempdir()) / "npt_chrome_aah_direct"

URL = "https://aah.eipp.blackline.com/app/customer/retrieved-documents"


def copy_profile():
    print("📋  Copying Chrome profile…", flush=True)
    if SESSION_COPY_DIR.exists():
        shutil.rmtree(SESSION_COPY_DIR, ignore_errors=True)
    SESSION_COPY_DIR.mkdir(parents=True)

    for item in ["Cookies", "Local Storage", "Session Storage", "IndexedDB", "Web Data"]:
        src = CHROME_PROFILE / item
        if src.exists():
            dst = SESSION_COPY_DIR / item
            try:
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            except:
                pass
    print(f"   ✅  Ready\n", flush=True)


def download_all():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copy_profile()

    records = []
    total = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_COPY_DIR),
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,  # VISIBLE WINDOW
            accept_downloads=True,
            viewport={"width": 1400, "height": 900},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        # Navigate to the page (or it might already be open)
        print(f"🌐  Going to Retrieved Documents page…\n", flush=True)
        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(3000)

        page_num = 1
        while True:
            print(f"📄  Page {page_num}…", flush=True)

            # Wait for table rows
            try:
                page.wait_for_selector("table tbody tr, table tr", timeout=8_000)
            except:
                print("   ⚠️  Couldn't find table. Is the page loaded? Retrying…")
                page.wait_for_timeout(5000)
                continue

            # Get all rows
            rows = page.query_selector_all("table tbody tr") or page.query_selector_all("table tr")
            # Filter out header rows
            rows = [r for r in rows if r.query_selector("td")]

            print(f"   Found {len(rows)} documents", flush=True)

            if not rows:
                print("   No documents on this page. Done!")
                break

            # Download each document on this page
            for idx, row in enumerate(rows):
                try:
                    cells = row.query_selector_all("td")
                    if len(cells) < 2:
                        continue

                    # Extract info from cells
                    doc_type = (cells[0].inner_text() or "").strip()
                    doc_ref = (cells[1].inner_text() or "").strip()
                    doc_date = (cells[2].inner_text() or "").strip() if len(cells) > 2 else ""

                    # Create filename
                    filename = f"{doc_type}_{doc_ref}_{doc_date}".replace("/", "-").replace(" ", "_")
                    if not filename.endswith(".pdf"):
                        filename += ".pdf"
                    filename = filename[:120]

                    out_path = OUT_DIR / filename
                    if out_path.exists():
                        print(f"   ⏭️  {idx+1}. {filename[:50]} (already have)")
                        total += 1
                        continue

                    # Find the download button/icon in this row
                    # Usually the rightmost button/link
                    buttons = row.query_selector_all("button, a[role='button'], [class*='download']")

                    if not buttons:
                        # Try looking for any clickable element in the last cell
                        last_cell = cells[-1]
                        buttons = last_cell.query_selector_all("button, a, [role='button']")

                    if not buttons:
                        print(f"   ❌ {idx+1}. No download button for {doc_ref[:30]}")
                        continue

                    # Click the last (rightmost) button
                    download_btn = buttons[-1]

                    try:
                        with page.expect_download(timeout=30_000) as dl_info:
                            download_btn.click()
                        dl = dl_info.value
                        dl.save_as(str(out_path))

                        size = out_path.stat().st_size // 1024
                        print(f"   ✅ {idx+1}. {filename[:50]} ({size} KB)")

                        records.append({
                            "doc_type": doc_type,
                            "doc_ref": doc_ref,
                            "doc_date": doc_date,
                            "filename": filename,
                            "path": str(out_path),
                            "size_kb": size,
                            "downloaded_at": datetime.datetime.now().isoformat()
                        })
                        total += 1
                        time.sleep(0.3)

                    except Exception as e:
                        print(f"   ❌ {idx+1}. Download failed: {e}")

                except Exception as e:
                    print(f"   ❌ Row {idx+1} error: {e}")

            # Go to next page
            try:
                # Look for next button
                next_buttons = page.query_selector_all(
                    "a[aria-label*='next' i], button[aria-label*='next' i], "
                    ".pagination-next, [class*='next']"
                )

                next_btn = None
                for btn in next_buttons:
                    if btn.is_enabled():
                        next_btn = btn
                        break

                if next_btn:
                    print(f"   ➡️  Next page…\n", flush=True)
                    next_btn.click()
                    page.wait_for_timeout(3000)
                    page_num += 1
                else:
                    print(f"   🏁  No more pages\n", flush=True)
                    break

            except Exception as e:
                print(f"   🏁  Pagination done: {e}\n", flush=True)
                break

        browser.close()

    # Save metadata
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(records, indent=2, default=str))

    print("=" * 60)
    print(f"✅  Downloaded {total} documents")
    print(f"📂  Location: {OUT_DIR}")
    print(f"💾  Metadata: {META_FILE}")
    print("=" * 60)

    # Cleanup
    shutil.rmtree(SESSION_COPY_DIR, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 60)
    print("  AAH Retrieved Documents Downloader")
    print("  (Direct download - assumes you're already on the page)")
    print("=" * 60)
    print()
    download_all()
