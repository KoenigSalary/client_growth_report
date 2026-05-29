"""
download_rms2_data.py  --  v5 FINAL

Downloads RMS2 RCB reports for analysis:
  - Last 24 months -> data/RCB_24months.xlsx
  - Last 12 months -> data/RCB_12months.xlsx

Flow (each download):
  1. Login to RMS2
  2. Navigate to RCB page
  3. Set 'Last Months' input to 24 (or 12)
  4. Click 'Apply Filters' (dark button, bottom-right of filter card)
  5. Click 'Export Excel' (white button, top-right of header)
  6. Save the downloaded .xlsx

KEY ROBUSTNESS FEATURES:
  - LABEL-aware Last Months detection (won't pick the search box by accident)
  - Session-validity check before every step (fast-fail if redirected to login)
  - Diagnostic dumps of all buttons + inputs on any failure
  - Re-login between 24M and 12M downloads (in case session expires)
  - NO Enter-key fallback (caused logouts in earlier versions)

Required GitHub Secrets:
  - RMS_USERNAME
  - RMS_PASSWORD
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


# ----------- Config -----------
RMS_USERNAME  = os.getenv("RMS_USERNAME", "").strip()
RMS_PASSWORD  = os.getenv("RMS_PASSWORD", "").strip()
RMS_LOGIN_URL = os.getenv("RMS_LOGIN_URL", "https://rms2.koenig-solutions.com").strip()
RCB_BASE_URL  = os.getenv("RCB_BASE_URL", "https://rms2.koenig-solutions.com/RCB").strip()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FILE_24M = DATA_DIR / "RCB_24months.xlsx"
FILE_12M = DATA_DIR / "RCB_12months.xlsx"

HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"
SLOW_MO  = int(os.getenv("SLOW_MO", "0"))


# ----------- Helpers -----------
def require_env() -> None:
    if not RMS_USERNAME:
        raise ValueError("RMS_USERNAME secret is missing.")
    if not RMS_PASSWORD:
        raise ValueError("RMS_PASSWORD secret is missing.")


def screenshot(page: Page, name: str) -> None:
    path = DATA_DIR / name
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"Saved screenshot: {path}")
    except Exception as exc:
        print(f"Could not save screenshot {path}: {exc}")


def fill_first_available(page: Page, selectors, value: str, label: str,
                         timeout: int = 7000) -> bool:
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.fill("")
            loc.fill(value)
            print(f"Filled {label} via: {selector}")
            return True
        except Exception:
            continue
    print(f"Could NOT fill {label}. Tried: {selectors}")
    return False


def click_first_available(page: Page, selectors, label: str,
                          timeout: int = 7000) -> bool:
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
            print(f"Clicked {label} via: {selector}")
            return True
        except Exception:
            continue
    print(f"Could NOT click {label}. Tried: {selectors}")
    return False


def dump_all_buttons(page: Page, label: str) -> None:
    try:
        clickables = page.locator(
            "button, a, input[type='button'], input[type='submit'], [role='button']"
        )
        n = clickables.count()
        print(f"\n[{label}] DIAGNOSTIC -- Visible clickable elements ({n} total):")
        shown = 0
        for i in range(n):
            try:
                el = clickables.nth(i)
                if not el.is_visible():
                    continue
                txt = (el.inner_text() or "").strip().replace("\n", " ")[:50]
                val = (el.get_attribute("value") or "").strip()[:30]
                cls = (el.get_attribute("class") or "").strip()[:60]
                ide = (el.get_attribute("id") or "").strip()[:30]
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                print(f"  [{i}] <{tag}> text='{txt}'  value='{val}'  id='{ide}'  class='{cls}'")
                shown += 1
                if shown >= 40:
                    print(f"  ... ({n - i - 1} more not shown)")
                    break
            except Exception:
                continue
        print("")
    except Exception as e:
        print(f"[{label}] Could not dump buttons: {e}")


def dump_all_inputs(page: Page, label: str) -> None:
    try:
        inputs = page.locator("input")
        n = inputs.count()
        print(f"\n[{label}] DIAGNOSTIC -- Visible input elements ({n} total):")
        shown = 0
        for i in range(n):
            try:
                el = inputs.nth(i)
                if not el.is_visible():
                    continue
                typ = (el.get_attribute("type") or "").strip()[:15]
                nm  = (el.get_attribute("name") or "").strip()[:30]
                ide = (el.get_attribute("id") or "").strip()[:30]
                ph  = (el.get_attribute("placeholder") or "").strip()[:30]
                val = (el.input_value() or "").strip()[:30]
                cls = (el.get_attribute("class") or "").strip()[:50]
                print(f"  [{i}] type='{typ}' name='{nm}' id='{ide}' placeholder='{ph}' value='{val}' class='{cls}'")
                shown += 1
                if shown >= 30:
                    break
            except Exception:
                continue
        print("")
    except Exception as e:
        print(f"[{label}] Could not dump inputs: {e}")


def is_on_login_page(page: Page) -> bool:
    """Detect if we're currently on (or got redirected to) the login page."""
    try:
        url = (page.url or "").lower()
        if "login" in url or url.rstrip("/") == RMS_LOGIN_URL.rstrip("/").lower():
            return True
        # Login-page hallmark: password input visible AND only ~3 buttons
        pw = page.locator("input[type='password']")
        if pw.count() > 0:
            try:
                if pw.first.is_visible(timeout=500):
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def ensure_logged_in(page: Page, label: str) -> None:
    """If we're on the login page mid-workflow, log in again."""
    if is_on_login_page(page):
        print(f"[{label}] Session lost or expired -- attempting re-login...")
        login(page)


# ----------- Login -----------
def login(page: Page) -> None:
    print(f"Opening RMS login URL: {RMS_LOGIN_URL}")
    page.goto(RMS_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    screenshot(page, "01_login_page.png")

    username_selectors = [
        "input[placeholder='Your Email']",
        "input[placeholder*='Email' i]",
        "input[name='UserName']", "input[name='username']",
        "input[name='Email']",    "input[name='email']",
        "input[type='email']",
        "input[type='text']",
        "#UserName", "#username", "#Email", "#email",
    ]
    password_selectors = [
        "input[placeholder='Password']",
        "input[name='Password']", "input[name='password']",
        "input[type='password']",
        "#Password", "#password",
    ]
    login_button_selectors = [
        "button.ui.positive.button:has-text('Login')",
        "button:has-text('Login')",
        "button:has-text('Sign in')",
        "button[type='submit']",
        "input[type='submit']",
        "input[value='Login']",
    ]

    if not fill_first_available(page, username_selectors, RMS_USERNAME, "username"):
        dump_all_inputs(page, "login")
        raise RuntimeError("Could not find username field on login page.")

    if not fill_first_available(page, password_selectors, RMS_PASSWORD, "password"):
        dump_all_inputs(page, "login")
        raise RuntimeError("Could not find password field on login page.")

    if not click_first_available(page, login_button_selectors, "Login button"):
        dump_all_buttons(page, "login")
        screenshot(page, "login_button_not_found_error.png")
        raise RuntimeError("Could not find Login button on login page.")

    # Wait for login to complete & session to settle
    try:
        page.wait_for_url(lambda u: "login" not in u.lower(), timeout=15000)
    except Exception:
        # Some apps don't redirect URL but do change content -- check below
        pass

    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    screenshot(page, "02_after_login.png")

    if is_on_login_page(page):
        screenshot(page, "login_failed_still_on_login_page.png")
        raise RuntimeError(
            "Login failed -- still on login page after submitting credentials. "
            "Check RMS_USERNAME / RMS_PASSWORD secrets."
        )

    print(f"Login successful. Current URL: {page.url}")


# ----------- Navigation -----------
def open_rcb_page(page: Page, label: str) -> None:
    print(f"\nOpening RCB page: {RCB_BASE_URL}")
    page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    screenshot(page, f"03_{label}_rcb_page.png")

    # If RMS2 redirected us back to login, re-authenticate and retry
    if is_on_login_page(page):
        print(f"[{label}] RCB page redirected to login. Re-logging in...")
        login(page)
        page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        screenshot(page, f"03_{label}_rcb_page_retry.png")

    if is_on_login_page(page):
        raise RuntimeError(
            "Cannot reach RCB page -- session keeps getting redirected to login. "
            "User may lack RCB access or RMS2 requires extra verification."
        )


# ----------- Last Months input -----------
def set_last_months(page: Page, months: int, label: str) -> None:
    """
    Find the 'Last Months' input via label-aware strategies.
    DO NOT just pick input[type='text'] index 0 -- that's the search box.
    """
    print(f"\nSetting Last Months = {months}")
    target_field = None

    # Strategy 1: XPath using nearby 'Last Months' text/label
    xpath_candidates = [
        "//label[contains(normalize-space(.), 'Last Months')]/following::input[1]",
        "//label[contains(normalize-space(.), 'Last Months')]/..//input",
        "//*[contains(normalize-space(text()), 'Last Months')]/following::input[1]",
        "//*[contains(normalize-space(text()), 'Last Months')]/..//input",
        "//div[contains(normalize-space(.), 'Last Months')]//input[@type='text' or @type='number']",
    ]
    for xp in xpath_candidates:
        try:
            loc = page.locator(xp).first
            if loc.is_visible(timeout=2000):
                loc.fill("")
                loc.fill(str(months))
                target_field = loc
                print(f"Filled Last Months via label-XPath: {xp}")
                break
        except Exception:
            continue

    # Strategy 2: Attribute selectors
    if target_field is None:
        attr_selectors = [
            "input[placeholder='Last Months']",
            "input[placeholder*='Last Months' i]",
            "input[placeholder*='Months' i]",
            "input[name*='Month' i]",
            "input[name*='LastMonth' i]",
            "input[id*='Month' i]",
            "input[id*='LastMonth' i]",
        ]
        for sel in attr_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    loc.fill("")
                    loc.fill(str(months))
                    target_field = loc
                    print(f"Filled Last Months via attribute: {sel}")
                    break
            except Exception:
                continue

    # Strategy 3: Scan inputs whose current value is EXACTLY '12' (RCB default)
    # while excluding search/CCE/country/NR-amount fields
    if target_field is None:
        print("Falling back to value-scan for input containing exactly '12'...")
        try:
            inputs = page.locator("input[type='text'], input[type='number']")
            n = inputs.count()
            for i in range(n):
                el = inputs.nth(i)
                try:
                    if not el.is_visible():
                        continue
                    v = el.input_value().strip()
                    if v != "12":
                        continue
                    nm  = (el.get_attribute("name") or "").lower()
                    ph  = (el.get_attribute("placeholder") or "").lower()
                    ide = (el.get_attribute("id") or "").lower()
                    haystack = nm + " " + ph + " " + ide
                    if any(x in haystack for x in ["search", "cce", "country", "manager", "nr ", "amount"]):
                        continue
                    el.fill("")
                    el.fill(str(months))
                    target_field = el
                    print(f"Filled Last Months via value-scan at input index {i} (name='{nm}', placeholder='{ph}', id='{ide}')")
                    break
                except Exception:
                    continue
        except Exception:
            pass

    if target_field is None:
        print(f"[{label}] CRITICAL: could not find Last Months field. Dumping all inputs:")
        dump_all_inputs(page, label)
        screenshot(page, f"{label}_last_months_not_found_error.png")
        raise RuntimeError(f"Could not find Last Months field for {label}.")

    page.wait_for_timeout(800)
    screenshot(page, f"04_{label}_last_months_filled.png")


# ----------- Apply Filters -----------
def apply_filters(page: Page, label: str) -> None:
    """The filter trigger is a DARK button labeled 'Apply Filters'."""
    apply_selectors = [
        "button:has-text('Apply Filters')",
        "//button[normalize-space(.)='Apply Filters']",
        "//button[contains(normalize-space(.), 'Apply Filters')]",
        "input[value='Apply Filters']",
        "a:has-text('Apply Filters')",
        "[role='button']:has-text('Apply Filters')",
    ]

    if click_first_available(page, apply_selectors, f"{label} Apply Filters", timeout=10000):
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        screenshot(page, f"05_{label}_after_apply_filters.png")
        ensure_logged_in(page, label)
        return

    print(f"[{label}] Apply Filters button not found. Dumping diagnostics:")
    dump_all_buttons(page, label)
    dump_all_inputs(page, label)
    screenshot(page, f"{label}_apply_filters_not_found_error.png")
    raise RuntimeError(f"Could not find Apply Filters button for {label}.")


# ----------- Export Excel -----------
def export_excel(page: Page, output_path: Path, label: str) -> None:
    """The export trigger is a WHITE button labeled 'Export Excel' in the header."""
    ensure_logged_in(page, label)

    export_selectors = [
        "button:has-text('Export Excel')",
        "//button[normalize-space(.)='Export Excel']",
        "//button[normalize-space(text())='Export Excel']",
        "a:has-text('Export Excel')",
        "[role='button']:has-text('Export Excel')",
        "input[value='Export Excel']",
        "//button[contains(., 'Export Excel') and not(contains(., 'PPC'))]",
        "//button[contains(., 'Export') and not(contains(., 'PPC')) and not(contains(., 'Median'))]",
    ]

    print(f"\n[{label}] Attempting Export Excel download...")
    try:
        with page.expect_download(timeout=180000) as download_info:
            if not click_first_available(page, export_selectors,
                                         f"{label} Export Excel", timeout=10000):
                dump_all_buttons(page, label)
                screenshot(page, f"{label}_export_excel_not_found_error.png")
                raise RuntimeError(f"Could not find Export Excel button for {label}.")
        download = download_info.value
    except Exception as e:
        dump_all_buttons(page, label)
        screenshot(page, f"{label}_export_download_error.png")
        raise RuntimeError(f"Export download failed for {label}: {e}")

    temp_path = download.path()
    if not temp_path:
        raise RuntimeError(
            f"Download failed for {label}. Suggested filename: {download.suggested_filename}"
        )

    output_path.parent.mkdir(exist_ok=True)
    shutil.copy(temp_path, output_path)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Saved {label}: {output_path} ({size_mb:.2f} MB)")


# ----------- Orchestration -----------
def download_rcb_report(page: Page, months: int, output_path: Path, label: str) -> None:
    print(f"\n{'='*70}\nStarting {label} download (Last Months = {months})\n{'='*70}")
    open_rcb_page(page, label)
    set_last_months(page, months, label)
    apply_filters(page, label)
    export_excel(page, output_path, label)


def main() -> None:
    require_env()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(30000)
        try:
            login(page)
            download_rcb_report(page, 24, FILE_24M, "RCB_24months")
            download_rcb_report(page, 12, FILE_12M, "RCB_12months")
        except Exception as exc:
            print(f"\nFATAL ERROR: {exc}")
            screenshot(page, "final_error.png")
            raise
        finally:
            context.close()
            browser.close()

    print("\n" + "=" * 70)
    print("RMS2 RCB downloads completed successfully!")
    print(f"  24M file: {FILE_24M}")
    print(f"  12M file: {FILE_12M}")
    print("=" * 70)


if __name__ == "__main__":
    main()
