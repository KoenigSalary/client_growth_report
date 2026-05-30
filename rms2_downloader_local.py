"""
rms2_downloader_local.py  --  Visible-browser RMS2 downloader

Designed to be run on the user's OWN COMPUTER (not Streamlit Cloud).
A real Chromium window opens so the user can see what is happening and
type the OTP directly into RMS2 when prompted.

Flow:
  1. Streamlit starts a background thread
  2. Thread launches a VISIBLE Chromium window
  3. Auto-fills email + password, clicks Login
  4. RMS2 shows the OTP screen
  5. User types OTP into the visible browser window (in RMS2 itself)
  6. Script polls every 1.5s waiting for the password field to disappear
     (meaning the user has authenticated)
  7. Once authenticated, navigates to RCB, downloads 24M + 12M
  8. Closes the browser, reports back to Streamlit
"""

from __future__ import annotations

import threading
import queue
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, sync_playwright


RMS_LOGIN_URL = "https://rms2.koenig-solutions.com"
RCB_BASE_URL  = "https://rms2.koenig-solutions.com/RCB"


class RMS2LocalSession:
    """
    Runs Playwright in non-headless mode so the user can interact with
    the RMS2 login (specifically for entering the OTP).
    """

    STATE_IDLE                  = "idle"
    STATE_OPENING_BROWSER       = "opening_browser"
    STATE_FILLING_CREDENTIALS   = "filling_credentials"
    STATE_WAITING_FOR_USER_OTP  = "waiting_for_user_otp"
    STATE_AUTHENTICATED         = "authenticated"
    STATE_DOWNLOADING_24M       = "downloading_24m"
    STATE_DOWNLOADING_12M       = "downloading_12m"
    STATE_DONE                  = "done"
    STATE_ERROR                 = "error"

    # How long to wait for the user to enter the OTP (seconds)
    OTP_WAIT_TIMEOUT = 600          # 10 minutes

    def __init__(self, username: str, password: str, data_dir: str = "data"):
        self.username = username
        self.password = password
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.state = self.STATE_IDLE
        self.message = ""
        self.error: Optional[str] = None
        self.file_24m: Optional[Path] = None
        self.file_12m: Optional[Path] = None

        self._command_queue: queue.Queue = queue.Queue()
        self._worker: Optional[threading.Thread] = None

    # ---------- Public API ----------

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def cancel(self) -> None:
        self._command_queue.put("cancel")

    # ---------- Worker thread ----------

    def _run(self) -> None:
        try:
            with sync_playwright() as p:
                self.state = self.STATE_OPENING_BROWSER
                self.message = "Opening Chromium browser window..."
                browser = p.chromium.launch(headless=False, slow_mo=200)
                context = browser.new_context(
                    viewport={"width": 1400, "height": 900},
                    accept_downloads=True,
                )
                page = context.new_page()
                page.set_default_timeout(30000)

                try:
                    self._login_with_user_otp(page)
                    self._download_both(page)
                    self.state = self.STATE_DONE
                    self.message = "All downloads complete. Closing browser..."
                finally:
                    try:
                        page.wait_for_timeout(1500)
                        context.close()
                        browser.close()
                    except Exception:
                        pass
        except Exception as exc:
            self.error = str(exc)
            self.state = self.STATE_ERROR
            self.message = f"ERROR: {exc}"

    # ---------- Login with user-typed OTP ----------

    def _login_with_user_otp(self, page: Page) -> None:
        self.state = self.STATE_FILLING_CREDENTIALS
        self.message = "Loading RMS2 login page..."
        page.goto(RMS_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        self._screenshot(page, "01_login_page.png")

        self.message = "Filling email and password..."
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

        # Wait for navigation away from the password field
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        # Now we are either on the RCB dashboard already OR on the OTP screen.
        # If the OTP screen is up, wait for the USER to type the OTP into the
        # visible browser and submit it. We detect success by watching the URL
        # / DOM until no password/OTP-style input is visible AND we reach a
        # post-login URL.
        self.state = self.STATE_WAITING_FOR_USER_OTP
        self.message = (
            "🔑 Please complete login in the Chromium window!\n\n"
            "Check your Outlook for the 6-digit OTP, type it into the RMS2 "
            "browser window that just opened, and click the Submit/Verify "
            "button in that window.\n\n"
            "This Streamlit page will continue automatically once you are "
            "logged in."
        )

        # Poll up to OTP_WAIT_TIMEOUT seconds for authentication
        import time as _time
        start = _time.time()
        while _time.time() - start < self.OTP_WAIT_TIMEOUT:
            # Check for cancel
            try:
                cmd = self._command_queue.get_nowait()
                if cmd == "cancel":
                    raise RuntimeError("Cancelled by user")
            except queue.Empty:
                pass

            # If we are clearly authenticated (no password OR OTP-input, and
            # the URL is not the login root), break out.
            if self._appears_authenticated(page):
                break
            page.wait_for_timeout(1500)
        else:
            raise RuntimeError(
                f"OTP not entered within {self.OTP_WAIT_TIMEOUT // 60} minutes. "
                "Aborting."
            )

        self.state = self.STATE_AUTHENTICATED
        self.message = f"Authenticated. URL: {page.url}"
        self._screenshot(page, "02_after_user_otp.png")

    def _appears_authenticated(self, page: Page) -> bool:
        """STRICT v5.1 check: ALL conditions must hold.
        Prevents the bug where the script raced ahead before OTP entry."""
        try:
            url = (page.url or "").lower().rstrip("/")
            login_root = RMS_LOGIN_URL.lower().rstrip("/")
            # 1. URL must NOT be login root or contain login/otp/verify/auth
            if url == login_root:
                return False
            if any(token in url for token in
                   ("login", "otp", "verify", "verification", "auth", "2fa", "mfa")):
                return False
            # 2. No visible password input
            if self._has_visible(page, "input[type='password']"):
                return False
            # 3. No visible OTP-style input
            for sel in [
                "input[maxlength='6']", "input[maxlength='4']",
                "input[type='tel']",
                "input[placeholder*='OTP' i]",
                "input[placeholder*='code' i]",
                "input[placeholder*='verification' i]",
                "input[name*='otp' i]",
                "input[name*='code' i]",
                "input[id*='otp' i]",
                "input[id*='code' i]",
            ]:
                if self._has_visible(page, sel):
                    return False
            # 4. Require a "logged-in hallmark" to be visible
            for sel in [
                "a:has-text('Logout')", "button:has-text('Logout')",
                "text=Logout", "text=Log Out",
                "text=Dashboard", "text=RCB",
                "a[href*='/RCB']", "a[href*='/Dashboard']",
                "[class*='user-menu']", "[class*='userMenu']",
                "[class*='avatar']",
            ]:
                if self._has_visible(page, sel):
                    return True
            return False
        except Exception:
            return False


    def _has_visible(self, page: Page, selector: str) -> bool:
        try:
            loc = page.locator(selector)
            return loc.count() > 0 and loc.first.is_visible(timeout=400)
        except Exception:
            return False

    # ---------- RCB downloads ----------

    def _download_both(self, page: Page) -> None:
        self.state = self.STATE_DOWNLOADING_24M
        self.message = "Downloading 24-month data..."
        self.file_24m = self._download_one(page, 24, "RCB_24months.xlsx", "RCB_24months")

        self.state = self.STATE_DOWNLOADING_12M
        self.message = "Downloading 12-month data..."
        self.file_12m = self._download_one(page, 12, "RCB_12months.xlsx", "RCB_12months")

    def _download_one(self, page: Page, months: int, filename: str, label: str) -> Path:
        page.goto(RCB_BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        self._screenshot(page, f"03_{label}_rcb_page.png")

        self._set_last_months(page, months, label)
        self._click_first(page, [
            "button:has-text('Apply Filters')",
            "//button[normalize-space(.)='Apply Filters']",
            "input[value='Apply Filters']",
        ], f"{label} Apply Filters")
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        self._screenshot(page, f"04_{label}_after_apply_filters.png")

        with page.expect_download(timeout=180000) as dl_info:
            self._click_first(page, [
                "button:has-text('Export Excel')",
                "//button[normalize-space(.)='Export Excel']",
                "//button[contains(., 'Export Excel') and not(contains(., 'PPC'))]",
            ], f"{label} Export Excel")
        download = dl_info.value

        out = self.data_dir / filename
        download.save_as(str(out))
        return out

    def _set_last_months(self, page: Page, months: int, label: str) -> None:
        # Label-aware -- never grabs the search box
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
        # Value-scan
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

    # ---------- Low-level helpers ----------

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
        raise RuntimeError(f"Could not fill {label}.")

    def _click_first(self, page: Page, selectors, label: str) -> None:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=5000)
                loc.click()
                return
            except Exception:
                continue
        raise RuntimeError(f"Could not click {label}.")

    def _screenshot(self, page: Page, name: str) -> None:
        try:
            page.screenshot(path=str(self.data_dir / name), full_page=True)
        except Exception:
            pass
