"""
download_rms2_data.py  --  v3 PAGE-SPECIFIC FIX

Downloads latest RMS2 RCB reports for:
- Last 24 months -> data/RCB_24months.xlsx
- Last 12 months -> data/RCB_12months.xlsx

PAGE LAYOUT (verified from actual screenshots of rms2.koenig-solutions.com/RCB):

  +---------------------------------------------------------------+
  | Regular Corporate Business  [Add Corporate][FAQ][Export Excel]|
  |                                       [Excel (PPC)][Median]   |
  +---------------------------------------------------------------+
  | FILTERS                                                       |
  | [Select Country][All CCE][All Manager]                        |
  | [NR more than][NR less than][Last Months: 24]                 |
  | [ ] W/O any CCE   [ ] List Of Corporate SCs                   |
  |                                          [Apply Filters]      |
  +---------------------------------------------------------------+

KEY BUTTON LABELS (confirmed):
  - Filter trigger : 'Apply Filters' (dark button, bottom-right of filter card)
  - Export trigger : 'Export Excel'  (header, top-right)
  - Last Months input has current value '12' or '24'

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


# Config
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
            print(f"Filled {label}: {selector} = {value}")
            return True
        except Exception:
            continue
    print(f"Could not fill {label}. Tried: {selectors}")
    return False


def click_first_available(page: Page, selectors, label: str,
                          timeout: int = 7000) -> bool:
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
            print(f"Clicked {label}: {selector}")
            return True
        except Exception:
            continue
    print(f"Could not click {label}. Tried: {selectors}")
    return False


def dump_all_buttons(page: Page, label: str) -> None:
    """Print every visible clickable element on the page for debugging."""
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


def login(page: Page) -> None:
    print(f"Opening RMS login URL: {RMS_LOGIN_URL}")
    page.goto(RMS_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    screenshot(page, "01_login_page.png")

    username_selectors = [
        "input[name='UserName']", "input[name='username']",
        "input[name='Email']",    "input[name='email']",
        "input[type='email']",    "input[type='text']",
        "#UserName", "#username", "#Email", "#email",
    ]
    password_selectors = [
        "input[name='Password']", "input[name='password']",
        "input[type='password']", "#Password", "#password",
    ]
    login_button_selectors = [
        "button[type='submit']", "input[type='submit']",
        "button:has-text('Login')", "button:has-text('Sign in')",
        "input[value='Login']",     "input[value='Sign in']",
        "text=Login", "text=Sign in",
    ]

    if not fill_first_available(page, username_selectors, RMS_USERNAME, "username"):
        raise RuntimeError("Could not find username field.")
    if not fill_first_available(page, password_selectors, RMS_PASSWORD, "password"):
        raise RuntimeError("Could not find password field.")
    if not click_first_available(page, login_button_selectors, "login button"):
        screenshot(page, "login_button_not_found_error.png")
        raise RuntimeError("Could not find login button.")

    page.wait_for_load_state("networkidle", timeout=60000)
    screenshot(page, "02_after_login.png")

    body_text = page.locator("body").inner_text(timeout=15000)
    if re.search(r"invalid|incorrect|wrong|captcha|otp|verification|required",
                 body_text, re.I):
        screenshot(page, "login_failed_or_extra_verification_error.png")
        raise RuntimeError("Login may have failed or RMS requires OTP/CAPTCHA.")


def open_rcb_page(page: Page) -> None:
    print(f"Opening RCB page: {RCB_BASE_URL}")
    page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(2000)
    screenshot(page, "03_rcb_page.png")


def set_last_months(page: Page, months: int, label: str) -> None:
    print(f"Setting Last Months = {months}")

    precise_selectors = [
        "input[placeholder='Last Months']",
        "input[placeholder*='Last Months' i]",
        "input[placeholder*='Months' i]",
        "input[name*='Month' i]",
        "input[id*='Month' i]",
    ]

    target_field = None
    for sel in precise_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                loc.fill("")
                loc.fill(str(months))
                target_field = loc
                print(f"Filled Last Months via precise selector: {sel}")
                break
        except Exception:
            continue

    if target_field is None:
        print("Precise selectors failed; scanning visible inputs containing '12' or '24'...")
        for sel in ["input[type='text']", "input[type='number']", "input"]:
            try:
                elements = page.locator(sel)
                for i in range(elements.count()):
                    el = elements.nth(i)
                    try:
                        if not el.is_visible():
                            continue
                        if el.input_value().strip() in ["12", "24", ""]:
                            el.fill("")
                            el.fill(str(months))
                            target_field = el
                            print(f"Filled Last Months via fallback: {sel} index {i}")
                            break
                    except Exception:
                        continue
                if target_field is not None:
                    break
            except Exception:
                continue

    if target_field is None:
        screenshot(page, f"{label}_last_months_not_found_error.png")
        raise RuntimeError(f"Could not find Last Months field for {label}.")

    screenshot(page, f"04_{label}_last_months_filled.png")
    setattr(page, "_last_months_field", target_field)


def apply_filters(page: Page, label: str) -> None:
    """
    Confirmed from screenshot: filter trigger is a DARK button labeled
    'Apply Filters' at the bottom-right of the filter card.
    """
    apply_selectors = [
        "button:has-text('Apply Filters')",
        "//button[normalize-space(.)='Apply Filters']",
        "//button[contains(normalize-space(.), 'Apply Filters')]",
        "input[value='Apply Filters']",
        "a:has-text('Apply Filters')",
        "[role='button']:has-text('Apply Filters')",
        "button:has-text('Apply')",
        "button:has-text('Display')",
        "button:has-text('Search')",
    ]

    if click_first_available(page, apply_selectors, f"{label} Apply Filters", timeout=8000):
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        screenshot(page, f"05_{label}_after_apply_filters.png")
        return

    print(f"[{label}] Apply Filters button not found. Pressing Enter in Last Months field.")
    try:
        field = getattr(page, "_last_months_field", None)
        if field is not None:
            field.press("Enter")
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(4000)
            screenshot(page, f"05_{label}_after_enter_submit.png")
            return
    except Exception as e:
        print(f"[{label}] Enter-key fallback failed: {e}")

    dump_all_buttons(page, label)
    screenshot(page, f"{label}_apply_filters_not_found_error.png")
    raise RuntimeError(f"Could not find Apply Filters button for {label}.")


def export_excel(page: Page, output_path: Path, label: str) -> None:
    """
    Confirmed from screenshot: export trigger is a WHITE button labeled
    'Export Excel' in the top-right header area of the page.
    NOTE: 'Excel (PPC)' and 'Median Data' are SEPARATE buttons -- avoid them.
    """
    export_selectors = [
        "button:has-text('Export Excel')",
        "//button[normalize-space(.)='Export Excel']",
        "//button[normalize-space(text())='Export Excel']",
        "a:has-text('Export Excel')",
        "[role='button']:has-text('Export Excel')",
        "input[value='Export Excel']",
        "//button[contains(., 'Export Excel') and not(contains(., 'PPC'))]",
        "//button[contains(., 'Export') and not(contains(., 'PPC')) and not(contains(., 'Median'))]",
        "button:has-text('Export to excel')",
        "button:has-text('Export to Excel')",
    ]

    print(f"[{label}] Attempting Export Excel download...")
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
    print(f"Saved {label}: {output_path} ({output_path.stat().st_size} bytes)")


def download_rcb_report(page: Page, months: int, output_path: Path, label: str) -> None:
    print(f"\n{'='*70}\nStarting {label} download for Last Months = {months}\n{'='*70}")
    open_rcb_page(page)
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
            print(f"ERROR: {exc}")
            screenshot(page, "final_error.png")
            raise
        finally:
            context.close()
            browser.close()

    print("\n" + "="*70)
    print("RMS2 RCB downloads completed successfully!")
    print(f"  24M file: {FILE_24M}")
    print(f"  12M file: {FILE_12M}")
    print("="*70)


if __name__ == "__main__":
    main()
