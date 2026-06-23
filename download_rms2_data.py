"""
download_rms2_data.py  --  Headless RMS2 downloader for GitHub Actions CI

Runs Playwright in HEADLESS mode (no visible browser window).
Designed for fully automated environments where no human is present.

Requirements:
  - RMS_USERNAME / RMS_PASSWORD env vars (set as GitHub Secrets)
  - RMS2 account must NOT require OTP, OR OTP must be pre-approved for
    the IP range used by GitHub Actions runners.

Downloads:
  - data/RCB_24months.xlsx
  - data/RCB_12months.xlsx

Exit codes:
  0 = success
  1 = login failed / OTP required / download failed
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

RMS_LOGIN_URL = os.environ.get("RMS_LOGIN_URL", "https://rms2.koenig-solutions.com")
RCB_BASE_URL  = os.environ.get("RCB_BASE_URL",  "https://rms2.koenig-solutions.com/RCB")
DATA_DIR      = Path("data")

DOWNLOAD_TIMEOUT_MS = 120_000   # 2 minutes per file
PAGE_TIMEOUT_MS     = 30_000    # 30 s for navigation


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def fail(msg: str, code: int = 1):
    print(f"\n❌ ERROR: {msg}\n", file=sys.stderr, flush=True)
    sys.exit(code)


def run_download():
    username = os.environ.get("RMS_USERNAME", "").strip()
    password = os.environ.get("RMS_PASSWORD", "").strip()

    if not username or not password:
        fail("RMS_USERNAME and RMS_PASSWORD must be set as environment variables / GitHub Secrets.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT_MS)

        # ── Step 1: Login ──────────────────────────────────────────────────
        log(f"Navigating to {RMS_LOGIN_URL}")
        page.goto(RMS_LOGIN_URL, wait_until="networkidle")

        log("Filling credentials...")
        try:
            page.fill('input[type="email"], input[name="email"], input[name="username"], input[id*="email"], input[id*="user"]', username)
            page.fill('input[type="password"]', password)
            page.click('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
        except Exception as e:
            # Take screenshot for debugging
            page.screenshot(path=str(DATA_DIR / "login_error.png"))
            fail(f"Could not fill login form: {e}\nScreenshot saved to data/login_error.png")

        log("Waiting for post-login redirect...")
        try:
            # Wait for URL to change away from the login page
            page.wait_for_url(lambda url: RMS_LOGIN_URL.rstrip("/") not in url or "/dashboard" in url or "/home" in url or "/RCB" in url,
                               timeout=30_000)
        except PWTimeout:
            # Check if we're stuck on OTP page
            content = page.content().lower()
            if "otp" in content or "one-time" in content or "verification code" in content:
                page.screenshot(path=str(DATA_DIR / "otp_required.png"))
                fail(
                    "RMS2 is asking for an OTP (one-time password).\n"
                    "  GitHub Actions cannot enter OTP automatically.\n"
                    "  Options:\n"
                    "    1) Ask your IT/RMS2 admin to whitelist GitHub Actions IPs for this account.\n"
                    "    2) Use a service account with OTP disabled.\n"
                    "    3) Run the report locally using run_monthly.py instead.\n"
                    "  Screenshot saved to data/otp_required.png"
                )
            page.screenshot(path=str(DATA_DIR / "login_timeout.png"))
            fail("Login timed out. Screenshot saved to data/login_timeout.png")

        log(f"Logged in. Current URL: {page.url}")

        # ── Step 2: Navigate to RCB and download 24M ──────────────────────
        log("Navigating to RCB page for 24-month download...")
        try:
            page.goto(RCB_BASE_URL, wait_until="networkidle")
        except Exception as e:
            page.screenshot(path=str(DATA_DIR / "rcb_nav_error.png"))
            fail(f"Could not navigate to RCB: {e}")

        file_24m = _download_rcb_file(page, months=24, label="24M")
        file_12m = _download_rcb_file(page, months=12, label="12M")

        browser.close()

    # ── Step 3: Verify files ───────────────────────────────────────────────
    for label, path in [("24M", file_24m), ("12M", file_12m)]:
        if not path or not Path(path).exists():
            fail(f"{label} file not found after download.")
        size_kb = Path(path).stat().st_size / 1024
        log(f"✅ {label}: {path} ({size_kb:.1f} KB)")

    log("🎉 Both files downloaded successfully.")


def _download_rcb_file(page, months: int, label: str) -> str | None:
    """
    Trigger the RCB export for `months` and save to data/RCB_{label}.xlsx.
    Returns the saved file path on success.
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    dest = DATA_DIR / f"RCB_{label}.xlsx"
    log(f"Downloading {label} export...")

    try:
        # Try to set the month range selector if it exists
        selectors_to_try = [
            f'select[name*="month"], select[id*="month"]',
            f'input[name*="month"], input[id*="month"]',
        ]

        # Look for a months dropdown and set it
        for sel in selectors_to_try:
            try:
                if page.locator(sel).count() > 0:
                    page.select_option(sel, str(months))
                    log(f"  Set month range to {months}")
                    break
            except Exception:
                pass

        # Click the export / download button
        export_selectors = [
            f'button:has-text("{months}"), a:has-text("{months} month")',
            'button:has-text("Export"), button:has-text("Download"), a:has-text("Export"), a:has-text("Download")',
            'button:has-text("Excel"), a:has-text("Excel")',
        ]

        downloaded = False
        for sel in export_selectors:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0 or btn.is_visible():
                    with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl_info:
                        btn.click()
                    dl = dl_info.value
                    dl.save_as(str(dest))
                    downloaded = True
                    break
            except PWTimeout:
                log(f"  Timeout waiting for download via '{sel}'")
            except Exception:
                pass

        if not downloaded:
            # Last resort: look for any download link
            with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl_info:
                page.evaluate("""
                    const links = [...document.querySelectorAll('a, button')];
                    const dl = links.find(el => /download|export|excel|xlsx/i.test(el.textContent));
                    if (dl) dl.click();
                """)
            dl = dl_info.value
            dl.save_as(str(dest))

        return str(dest)

    except Exception as e:
        page.screenshot(path=str(DATA_DIR / f"download_{label}_error.png"))
        fail(f"Failed to download {label} export: {e}\nScreenshot: data/download_{label}_error.png")
        return None


if __name__ == "__main__":
    run_download()
