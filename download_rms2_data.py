"""
download_rms2_data.py  —  FIXED VERSION

Downloads latest RMS2 RCB reports for:
- Last 24 months -> data/RCB_24months.xlsx
- Last 12 months -> data/RCB_12months.xlsx

FIX vs previous version:
  The RMS2 RCB page button is labeled "Display" (Semantic-UI mini button with
  a filter icon), NOT "Apply Filters". Searching for "Apply Filters" caused:
      RuntimeError: Could not find Apply Filters button for RCB_24months
  This version tries Display + Apply Filters + several Semantic-UI / icon
  fallbacks, and as a last resort presses Enter inside the Last Months field
  (which on most server-rendered pages also submits the filter form).

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


# ─── Config ──────────────────────────────────────────────────────────────────
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


# ─── Helpers ─────────────────────────────────────────────────────────────────
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


# ─── Login ───────────────────────────────────────────────────────────────────
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
    screenshot(page, "03_rcb_page.png")


# ─── Last Months field ───────────────────────────────────────────────────────
def set_last_months(page: Page, months: int, label: str) -> None:
    print(f"Setting Last Months = {months}")

    selectors = [
        "input[type='text']",
        "input[type='number']",
        ".filters input",
        ".filter input",
        "form input",
    ]

    success = False
    target_field = None

    for selector in selectors:
        try:
            elements = page.locator(selector)
            count = elements.count()
            for i in range(count):
                try:
                    el = elements.nth(i)
                    if not el.is_visible():
                        continue
                    value = el.input_value()
                    if value.strip() in ["12", "24", ""]:
                        el.fill("")
                        el.fill(str(months))
                        print(f"Updated Last Months field using {selector} index {i}")
                        success = True
                        target_field = el
                        break
                except Exception:
                    continue
            if success:
                break
        except Exception:
            continue

    if not success:
        screenshot(page, f"{label}_last_months_not_found_error.png")
        raise RuntimeError(f"Could not find Last Months field for {label}.")

    screenshot(page, f"04_{label}_last_months_filled.png")

    # Stash the field for the Apply-Filters fallback (press Enter)
    setattr(page, "_last_months_field", target_field)


# ─── Apply / Display button  (THE KEY FIX) ───────────────────────────────────
def apply_filters(page: Page, label: str) -> None:
    """
    The RMS2 RCB page uses a Semantic-UI 'Display' button (not 'Apply Filters').
    Try a wide range of selectors so this keeps working even if the label changes.
    """
    apply_selectors = [
        # Most likely (confirmed by earlier working script): 'Display'
        "button:has-text('Display')",
        "button.ui.mini.button:has-text('Display')",
        "button:has(i.filter.icon)",                          # filter-icon button
        "//button[normalize-space(text())='Display']",
        "//button[contains(., 'Display')]",

        # Possible variants
        "button:has-text('Apply Filters')",
        "button:has-text('Apply')",
        "button:has-text('Search')",
        "button:has-text('Show')",
        "button:has-text('View')",
        "button:has-text('Submit')",

        # Inputs styled as buttons
        "input[value='Display']",
        "input[value='Apply Filters']",
        "input[value='Apply']",
        "input[value='Search']",
        "input[type='submit']",

        # IDs commonly used
        "#btnDisplay", "#Display",
        "#btnApplyFilters", "#ApplyFilters",
        "#btnSearch", "#Search",

        # Semantic-UI generic mini buttons (last resort)
        "button.ui.mini.primary.button",
        "button.ui.primary.button",
        "button.ui.button",
    ]

    if click_first_available(page, apply_selectors, f"{label} Display/Apply", timeout=5000):
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        screenshot(page, f"05_{label}_after_apply_filters.png")
        return

    # ── Fallback 1: press Enter inside the Last Months field ────────────────
    print(f"[{label}] No button matched. Falling back to pressing Enter in Last Months field.")
    try:
        field = getattr(page, "_last_months_field", None)
        if field is not None:
            field.press("Enter")
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            screenshot(page, f"05_{label}_after_enter_submit.png")
            print(f"[{label}] Enter-key submit succeeded.")
            return
    except Exception as e:
        print(f"[{label}] Enter-key fallback failed: {e}")

    # ── Fallback 2: dump every visible button so we can debug from the screenshot
    try:
        buttons = page.locator("button, input[type='button'], input[type='submit']")
        n = buttons.count()
        print(f"[{label}] Buttons present on page ({n}):")
        for i in range(min(n, 25)):
            try:
                b = buttons.nth(i)
                if b.is_visible():
                    txt = (b.inner_text() or "").strip()
                    val = (b.get_attribute("value") or "").strip()
                    cls = (b.get_attribute("class") or "").strip()
                    print(f"  [{i}] text='{txt[:40]}'  value='{val[:40]}'  class='{cls[:60]}'")
            except Exception:
                pass
    except Exception:
        pass

    screenshot(page, f"{label}_apply_filters_not_found_error.png")
    raise RuntimeError(f"Could not find Display/Apply button for {label}.")


# ─── Export ──────────────────────────────────────────────────────────────────
def export_excel(page: Page, output_path: Path, label: str) -> None:
    export_selectors = [
        # Most likely on RMS2 RCB
        "button:has-text('Export to excel')",
        "button:has-text('Export to Excel')",
        "button.ui.mini.button:has-text('Export')",
        "button:has-text('Export Excel')",
        "button:has-text('Excel (PPC)')",
        "button:has-text('Excel')",
        "button:has-text('Export')",
        "a:has-text('Export to excel')",
        "a:has-text('Export Excel')",
        "a:has-text('Excel')",
        "input[value*='Export' i]",
        "input[value*='Excel' i]",
        "#ExportExcel", "#btnExportExcel",
        "#ExportToExcel", "#btnExportToExcel",
        "//button[contains(., 'Export')]",
        "//a[contains(., 'Export')]",
    ]

    try:
        with page.expect_download(timeout=120000) as download_info:
            if not click_first_available(page, export_selectors,
                                         f"{label} Export Excel", timeout=10000):
                screenshot(page, f"{label}_export_excel_not_found_error.png")
                raise RuntimeError(f"Could not find Export Excel button for {label}.")
        download = download_info.value
    except Exception as e:
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


# ─── Orchestration ───────────────────────────────────────────────────────────
def download_rcb_report(page: Page, months: int, output_path: Path, label: str) -> None:
    print(f"Starting {label} download for Last Months = {months}")
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

    print("RMS2 RCB downloads completed successfully.")
    print(f"24M file: {FILE_24M}")
    print(f"12M file: {FILE_12M}")


if __name__ == "__main__":
    main()
