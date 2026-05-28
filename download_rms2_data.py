"""
download_rms2_data.py

Purpose:
- Login to RMS2
- Download latest RCB data for:
  1. Last 24 months
  2. Last 12 months
- Save/overwrite:
  data/RCB_24months.xlsx
  data/RCB_12months.xlsx

Designed for GitHub Actions.

Required GitHub Secrets:
- RMS_USERNAME
- RMS_PASSWORD

Optional environment variables:
- RMS_LOGIN_URL
- RCB_BASE_URL

Important:
This script includes debug screenshots and flexible selectors.
If RMS2 page fields/buttons differ, check GitHub Actions artifact screenshots/logs,
then update the selector section below.
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import date, timedelta
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


def format_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def get_date_range(months: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=months * 30)
    return format_date(start), format_date(end)


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


def click_first_available(page: Page, selectors: list[str], label: str, timeout: int = 5000) -> bool:
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


def fill_first_available(page: Page, selectors: list[str], value: str, label: str, timeout: int = 5000) -> bool:
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.fill(value)
            print(f"Filled {label}: {selector}")
            return True
        except Exception:
            continue
    print(f"Could not fill {label}. Tried: {selectors}")
    return False


def wait_for_download_and_save(page: Page, click_selectors: list[str], output_path: Path, label: str) -> None:
    output_path.parent.mkdir(exist_ok=True)

    with page.expect_download(timeout=120000) as download_info:
        ok = click_first_available(page, click_selectors, f"{label} export/download", timeout=10000)
        if not ok:
            screenshot(page, f"{label}_export_button_not_found_error.png")
            raise RuntimeError(f"Could not find export/download button for {label}.")

    download = download_info.value
    temp_path = download.path()

    if not temp_path:
        raise RuntimeError(f"Download failed for {label}. Suggested filename: {download.suggested_filename}")

    shutil.copy(temp_path, output_path)
    print(f"Saved {label}: {output_path} ({output_path.stat().st_size} bytes)")


def select_or_fill_date(page: Page, selectors: list[str], value: str, label: str) -> None:
    ok = fill_first_available(page, selectors, value, label, timeout=5000)
    if not ok:
        screenshot(page, f"{label}_not_found_error.png")
        raise RuntimeError(f"Could not find date field: {label}")


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
        raise RuntimeError("Could not find username field on RMS login page.")

    if not fill_first_available(page, password_selectors, RMS_PASSWORD, "password"):
        raise RuntimeError("Could not find password field on RMS login page.")

    if not click_first_available(page, login_button_selectors, "login button"):
        screenshot(page, "login_button_not_found_error.png")
        raise RuntimeError("Could not find login button on RMS login page.")

    page.wait_for_load_state("networkidle", timeout=60000)
    screenshot(page, "02_after_login.png")

    body_text = page.locator("body").inner_text(timeout=10000)
    if re.search(r"invalid|incorrect|wrong|captcha|otp|verification|required", body_text, re.I):
        screenshot(page, "login_failed_or_extra_verification_error.png")
        raise RuntimeError("Login may have failed or RMS requires OTP/CAPTCHA. Check screenshot artifact.")


def open_rcb_page(page: Page) -> None:
    print(f"Opening RCB page: {RCB_BASE_URL}")
    page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    screenshot(page, "03_rcb_page.png")


def download_rcb_report(page: Page, months: int, output_path: Path, label: str) -> None:
    start_date, end_date = get_date_range(months)
    print(f"Downloading {label}: {start_date} to {end_date}")

    open_rcb_page(page)

    from_date_selectors = [
        "#txtDateFrom",
        "#txtFromDate",
        "#DateFrom",
        "#FromDate",
        "input[name='txtDateFrom']",
        "input[name='txtFromDate']",
        "input[name='DateFrom']",
        "input[name='FromDate']",
        "input[placeholder*='From' i]",
        "input[aria-label*='From' i]",
    ]

    to_date_selectors = [
        "#txtDateTo",
        "#txtToDate",
        "#DateTo",
        "#ToDate",
        "input[name='txtDateTo']",
        "input[name='txtToDate']",
        "input[name='DateTo']",
        "input[name='ToDate']",
        "input[placeholder*='To' i]",
        "input[aria-label*='To' i]",
    ]

    search_button_selectors = [
        "#btnSearch",
        "#Search",
        "button:has-text('Search')",
        "input[value='Search']",
        "text=Search",
    ]

    export_button_selectors = [
        "#btnExport",
        "#btnExportToExcel",
        "#ExportToExcel",
        "#lnkExport",
        "button:has-text('Export')",
        "button:has-text('Excel')",
        "input[value*='Export' i]",
        "input[value*='Excel' i]",
        "a:has-text('Export')",
        "a:has-text('Excel')",
        "text=Export",
        "text=Excel",
    ]

    select_or_fill_date(page, from_date_selectors, start_date, f"{label}_from_date")
    select_or_fill_date(page, to_date_selectors, end_date, f"{label}_to_date")
    screenshot(page, f"04_{label}_dates_filled.png")

    clicked_search = click_first_available(page, search_button_selectors, f"{label} search", timeout=5000)
    if clicked_search:
        page.wait_for_load_state("networkidle", timeout=60000)
        screenshot(page, f"05_{label}_after_search.png")
    else:
        print(f"No search button found for {label}; trying export directly.")

    wait_for_download_and_save(page, export_button_selectors, output_path, label)


def main() -> None:
    require_env()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            login(page)
            download_rcb_report(page, months=24, output_path=FILE_24M, label="RCB_24months")
            download_rcb_report(page, months=12, output_path=FILE_12M, label="RCB_12months")
        except Exception as exc:
            print(f"ERROR: {exc}")
            screenshot(page, "final_error.png")
            raise
        finally:
            context.close()
            browser.close()

    print("RMS2 download completed successfully.")
    print(f"24M file: {FILE_24M}")
    print(f"12M file: {FILE_12M}")


if __name__ == "__main__":
    main()
