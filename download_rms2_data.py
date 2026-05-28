"""
download_rms2_data.py

Downloads latest RMS2 RCB reports for:
- Last 24 months -> data/RCB_24months.xlsx
- Last 12 months -> data/RCB_12months.xlsx

This version is based on the current RMS2 RCB page:
- No From Date / To Date fields
- Uses "Last Months" filter
- Clicks Apply Filters
- Clicks Export Excel

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


RMS_USERNAME = os.getenv("RMS_USERNAME", "").strip()
RMS_PASSWORD = os.getenv("RMS_PASSWORD", "").strip()

RMS_LOGIN_URL = os.getenv("RMS_LOGIN_URL", "https://rms2.koenig-solutions.com").strip()
RCB_BASE_URL = os.getenv("RCB_BASE_URL", "https://rms2.koenig-solutions.com/RCB").strip()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FILE_24M = DATA_DIR / "RCB_24months.xlsx"
FILE_12M = DATA_DIR / "RCB_12months.xlsx"

HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))


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


def fill_first_available(page: Page, selectors: list[str], value: str, label: str, timeout: int = 7000) -> bool:
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


def click_first_available(page: Page, selectors: list[str], label: str, timeout: int = 7000) -> bool:
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


def login(page: Page) -> None:
    print(f"Opening RMS login URL: {RMS_LOGIN_URL}")
    page.goto(RMS_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    screenshot(page, "01_login_page.png")

    username_selectors = [
        "input[name='UserName']",
        "input[name='username']",
        "input[name='Email']",
        "input[name='email']",
        "input[type='email']",
        "input[type='text']",
        "#UserName",
        "#username",
        "#Email",
        "#email",
    ]

    password_selectors = [
        "input[name='Password']",
        "input[name='password']",
        "input[type='password']",
        "#Password",
        "#password",
    ]

    login_button_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Login')",
        "button:has-text('Sign in')",
        "input[value='Login']",
        "input[value='Sign in']",
        "text=Login",
        "text=Sign in",
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
    if re.search(r"invalid|incorrect|wrong|captcha|otp|verification|required", body_text, re.I):
        screenshot(page, "login_failed_or_extra_verification_error.png")
        raise RuntimeError("Login may have failed or RMS requires OTP/CAPTCHA.")


def open_rcb_page(page: Page) -> None:
    print(f"Opening RCB page: {RCB_BASE_URL}")
    page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    screenshot(page, "03_rcb_page.png")

def set_last_months(page, months, label):
    print(f"Setting Last Months = {months}")

    selectors = [
        # Most likely based on screenshot position
        "input[type='text']",

        # Fallback numeric fields
        "input[type='number']",

        # Generic filter area inputs
        ".filters input",
        ".filter input",
        "form input",
    ]

    success = False

    for selector in selectors:
        try:
            elements = page.locator(selector)
            count = elements.count()

            for i in range(count):
                try:
                    el = elements.nth(i)

                    # Visible only
                    if not el.is_visible():
                        continue

                    value = el.input_value()

                    # Your screenshot shows current value = 12
                    if value.strip() in ["12", "24", ""]:
                        el.fill("")
                        el.fill(str(months))
                        print(f"Updated Last Months field using {selector} index {i}")
                        success = True
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

def apply_filters(page: Page, label: str) -> None:
    apply_selectors = [
        "button:has-text('Apply Filters')",
        "button:has-text('Apply')",
        "input[value='Apply Filters']",
        "input[value='Apply']",
        "text=Apply Filters",
        "#btnApplyFilters",
        "#ApplyFilters",
        "#btnSearch",
        "#Search",
    ]

    if not click_first_available(page, apply_selectors, f"{label} Apply Filters"):
        screenshot(page, f"{label}_apply_filters_not_found_error.png")
        raise RuntimeError(f"Could not find Apply Filters button for {label}.")

    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    screenshot(page, f"05_{label}_after_apply_filters.png")


def export_excel(page: Page, output_path: Path, label: str) -> None:
    export_selectors = [
        "button:has-text('Export Excel')",
        "button:has-text('Excel (PPC)')",
        "button:has-text('Excel')",
        "button:has-text('Export')",
        "a:has-text('Export Excel')",
        "a:has-text('Excel')",
        "input[value*='Export' i]",
        "input[value*='Excel' i]",
        "#ExportExcel",
        "#btnExportExcel",
        "#ExportToExcel",
        "#btnExportToExcel",
    ]

    with page.expect_download(timeout=120000) as download_info:
        if not click_first_available(page, export_selectors, f"{label} Export Excel", timeout=10000):
            screenshot(page, f"{label}_export_excel_not_found_error.png")
            raise RuntimeError(f"Could not find Export Excel button for {label}.")

    download = download_info.value
    temp_path = download.path()

    if not temp_path:
        raise RuntimeError(f"Download failed for {label}. Suggested filename: {download.suggested_filename}")

    output_path.parent.mkdir(exist_ok=True)
    shutil.copy(temp_path, output_path)

    print(f"Saved {label}: {output_path} ({output_path.stat().st_size} bytes)")


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
