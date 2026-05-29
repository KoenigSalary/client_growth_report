"""
rms2_downloader.py  --  OTP-aware RMS2 downloader

Designed to be driven INTERACTIVELY by the Streamlit app:
  1. Streamlit calls start_session()  -> returns immediately with an object
  2. Streamlit calls submit_otp(code)  -> resumes the script with the user's OTP
  3. Streamlit calls download_files()  -> performs the 24M / 12M downloads
  4. Streamlit calls close()           -> cleans up Playwright

This module does NOT block on input(). The OTP is provided via a thread-safe
queue so the Playwright loop can wait without blocking Streamlit's UI thread.
"""

from __future__ import annotations

import os
import threading
import queue
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, sync_playwright, TimeoutError as PWTimeout


RMS_LOGIN_URL = "https://rms2.koenig-solutions.com"
RCB_BASE_URL  = "https://rms2.koenig-solutions.com/RCB"


class RMS2Session:
    """
    A long-lived RMS2 session that runs Playwright in a background thread
    so the main (Streamlit) thread stays responsive.

    State machine:
        IDLE -> LOGGING_IN -> WAITING_FOR_OTP -> AUTHENTICATED ->
        DOWNLOADING -> DONE  (or ERROR at any point)
    """

    STATE_IDLE             = "idle"
    STATE_LOGGING_IN       = "logging_in"
    STATE_WAITING_FOR_OTP  = "waiting_for_otp"
    STATE_AUTHENTICATED    = "authenticated"
    STATE_DOWNLOADING      = "downloading"
    STATE_DONE             = "done"
    STATE_ERROR            = "error"

    def __init__(self, username: str, password: str, data_dir: str = "data",
                 headless: bool = True):
        self.username = username
        self.password = password
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.headless = headless

        self.state = self.STATE_IDLE
        self.message = ""
        self.error: Optional[str] = None

        # Thread-safe channels between Streamlit and the worker thread
        self._otp_queue: queue.Queue = queue.Queue(maxsize=1)
        self._command_queue: queue.Queue = queue.Queue()
        self._worker: Optional[threading.Thread] = None

        # File paths populated when downloads succeed
        self.file_24m: Optional[Path] = None
        self.file_12m: Optional[Path] = None

    # ---------------- Public API (called by Streamlit) ----------------

    def start(self) -> None:
        """Kick off login in a background thread."""
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def submit_otp(self, otp_code: str) -> None:
        """Streamlit pushes the OTP the user typed."""
        if self.state != self.STATE_WAITING_FOR_OTP:
            return
        try:
            self._otp_queue.put_nowait(otp_code.strip())
        except queue.Full:
            pass

    def request_download(self) -> None:
        """Streamlit asks the worker to perform the two downloads."""
        self._command_queue.put("download")

    def close(self) -> None:
        """Stop the worker and clean up."""
        self._command_queue.put("quit")
        if self._worker:
            self._worker.join(timeout=10)

    # ---------------- Worker thread ----------------

    def _run(self) -> None:
        """The background thread driving Playwright."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                page.set_default_timeout(30000)

                try:
                    self._login_flow(page)
                    # Wait for the Streamlit user to ask for downloads
                    while True:
                        cmd = self._command_queue.get()
                        if cmd == "quit":
                            break
                        if cmd == "download":
                            self._download_both(page)
                            self.state = self.STATE_DONE
                            self.message = "All downloads complete."
                            break
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            self.error = str(exc)
            self.state = self.STATE_ERROR
            self.message = f"ERROR: {exc}"

    # ---------------- Internal flow ----------------

    def _login_flow(self, page: Page) -> None:
        self.state = self.STATE_LOGGING_IN
        self.message = "Opening RMS2 login page..."

        page.goto(RMS_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        self._screenshot(page, "01_login_page.png")

        self.message = "Filling username & password..."
        self._fill_first(page, [
            "input[placeholder='Your Email']",
            "input[placeholder*='Email' i]",
            "input[type='text']",
        ], self.username, "username")
        self._fill_first(page, [
            "input[placeholder='Password']",
            "input[type='password']",
        ], self.password, "password")

        self._click_first(page, [
            "button.ui.positive.button:has-text('Login')",
            "button:has-text('Login')",
            "button[type='submit']",
        ], "Login")

        # Wait LONGER for OTP screen to render (it can take 5-10s)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        self._screenshot(page, "02_after_login.png")

        # Dump page state so we can see what's actually there
        self._dump_page_state(page, "after_login")

        # Aggressively check for OTP screen multiple times with retries
        # (the OTP page may take a few seconds to fully render)
        otp_detected = False
        for attempt in range(5):
            if self._is_otp_screen(page):
                otp_detected = True
                break
            page.wait_for_timeout(2000)

        # If we still have a password field visible, login failed outright
        if not otp_detected and self._has_password_input(page):
            self._screenshot(page, "login_failed.png")
            raise RuntimeError(
                "Login failed -- still seeing password field after submitting. "
                "Check RMS_USERNAME / RMS_PASSWORD in Streamlit secrets."
            )

        # Either we detected OTP screen, OR we're past it entirely (lucky session)
        # If unsure (no password but no OTP-text either), still offer OTP entry
        if otp_detected or self._looks_like_otp_screen_loosely(page):
            self.state = self.STATE_WAITING_FOR_OTP
            self.message = (
                "OTP required! Check your Outlook inbox for the 6-digit code "
                "sent by RMS2, then enter it below."
            )
            otp_code = self._otp_queue.get()   # blocks until Streamlit submits
            self._submit_otp(page, otp_code)
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            self._screenshot(page, "03_after_otp.png")

        # Final check -- are we through?
        if self._has_password_input(page) or self._is_otp_screen(page):
            self._screenshot(page, "auth_failed_final.png")
            raise RuntimeError(
                "Authentication failed -- still on login/OTP screen after submit. "
                "Possibly wrong OTP or expired code."
            )

        self.state = self.STATE_AUTHENTICATED
        self.message = f"Authenticated! Current URL: {page.url}"

    def _is_otp_screen(self, page: Page) -> bool:
        """Heuristic: an OTP screen typically has a single short input and
        body text mentioning 'OTP', 'code', 'verification'."""
        try:
            body = (page.locator("body").inner_text(timeout=3000) or "").lower()
            otp_hints = ("otp" in body or "verification code" in body
                         or "one-time password" in body or "6-digit" in body
                         or "enter the code" in body)
            if not otp_hints:
                return False
            # Look for a numeric / short-text input
            for sel in [
                "input[placeholder*='OTP' i]",
                "input[placeholder*='code' i]",
                "input[name*='otp' i]",
                "input[name*='code' i]",
                "input[type='tel']",
                "input[maxlength='6']",
                "input[maxlength='4']",
            ]:
                try:
                    if page.locator(sel).first.is_visible(timeout=500):
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _is_login_or_otp_screen(self, page: Page) -> bool:
        if self._is_otp_screen(page):
            return True
        try:
            url = (page.url or "").lower()
            if "login" in url:
                return True
            pw = page.locator("input[type='password']")
            if pw.count() > 0 and pw.first.is_visible(timeout=500):
                return True
            return False
        except Exception:
            return False

    def _submit_otp(self, page: Page, otp_code: str) -> None:
        self.message = "Submitting OTP..."
        otp_selectors = [
            "input[placeholder*='OTP' i]",
            "input[placeholder*='code' i]",
            "input[name*='otp' i]",
            "input[name*='code' i]",
            "input[maxlength='6']",
            "input[maxlength='4']",
            "input[type='tel']",
            "input[type='text']:not([type='password'])",
        ]
        self._fill_first(page, otp_selectors, otp_code, "OTP")

        # Submit -- try a button first, then Enter as last resort (safe here:
        # we're on the OTP screen, not a search box)
        submit_clicked = False
        for sel in [
            "button:has-text('Verify')",
            "button:has-text('Submit')",
            "button:has-text('Continue')",
            "button:has-text('Login')",
            "button.ui.positive.button",
            "button[type='submit']",
            "input[type='submit']",
        ]:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=1500):
                    loc.click()
                    submit_clicked = True
                    break
            except Exception:
                continue

        if not submit_clicked:
            try:
                page.keyboard.press("Enter")
            except Exception:
                pass


    # ---------------- RCB downloads ----------------

    def _download_both(self, page: Page) -> None:
        self.state = self.STATE_DOWNLOADING
        self.message = "Downloading 24-month data..."
        self.file_24m = self._download_one(page, 24, "RCB_24months.xlsx", "RCB_24months")

        self.message = "Downloading 12-month data..."
        self.file_12m = self._download_one(page, 12, "RCB_12months.xlsx", "RCB_12months")

    def _download_one(self, page: Page, months: int, filename: str, label: str) -> Path:
        # Navigate to RCB
        page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        self._screenshot(page, f"04_{label}_rcb_page.png")

        # Set Last Months (label-aware, never picks the search box)
        self._set_last_months(page, months, label)
        # Apply Filters
        self._click_first(page, [
            "button:has-text('Apply Filters')",
            "//button[normalize-space(.)='Apply Filters']",
            "input[value='Apply Filters']",
        ], f"{label} Apply Filters")
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        self._screenshot(page, f"05_{label}_after_apply_filters.png")

        # Export Excel
        with page.expect_download(timeout=180000) as dl_info:
            self._click_first(page, [
                "button:has-text('Export Excel')",
                "//button[normalize-space(.)='Export Excel']",
                "//button[contains(., 'Export Excel') and not(contains(., 'PPC'))]",
            ], f"{label} Export Excel")
        download = dl_info.value

        out = self.data_dir / filename
        download.save_as(str(out))
        size_mb = out.stat().st_size / 1024 / 1024
        self.message = f"Saved {filename} ({size_mb:.2f} MB)"
        return out

    def _set_last_months(self, page: Page, months: int, label: str) -> None:
        """Label-aware Last Months detection -- never grabs the search box."""
        xpath_candidates = [
            "//label[contains(normalize-space(.), 'Last Months')]/following::input[1]",
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
                    return
            except Exception:
                continue

        # Attribute fallback
        for sel in [
            "input[placeholder='Last Months']",
            "input[placeholder*='Months' i]",
            "input[name*='Month' i]",
            "input[id*='Month' i]",
        ]:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    loc.fill("")
                    loc.fill(str(months))
                    return
            except Exception:
                continue

        # Value-scan fallback (skip search/CCE/country/NR fields)
        inputs = page.locator("input[type='text'], input[type='number']")
        for i in range(inputs.count()):
            el = inputs.nth(i)
            try:
                if not el.is_visible():
                    continue
                if el.input_value().strip() != "12":
                    continue
                nm  = (el.get_attribute("name") or "").lower()
                ph  = (el.get_attribute("placeholder") or "").lower()
                ide = (el.get_attribute("id") or "").lower()
                if any(x in nm + ph + ide for x in
                       ["search", "cce", "country", "manager", "nr", "amount"]):
                    continue
                el.fill("")
                el.fill(str(months))
                return
            except Exception:
                continue

        raise RuntimeError(f"Could not find Last Months field for {label}.")

    # ---------------- Low-level helpers ----------------

    def _fill_first(self, page: Page, selectors, value: str, label: str) -> None:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=5000)
                loc.fill("")
                loc.fill(value)
                return
            except Exception:
                continue
        raise RuntimeError(f"Could not fill {label}. Tried: {selectors}")

    def _click_first(self, page: Page, selectors, label: str) -> None:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=5000)
                loc.click()
                return
            except Exception:
                continue
        raise RuntimeError(f"Could not click {label}. Tried: {selectors}")

    def _screenshot(self, page: Page, name: str) -> None:
        try:
            page.screenshot(path=str(self.data_dir / name), full_page=True)
        except Exception:
            pass
