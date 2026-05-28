"""
RMS2 Data Downloader - GitHub Actions compatible (DEBUG VERSION)
First, let's see what's on the login page
"""

import os
import time
import asyncio
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


class RMS2Downloader:
    def __init__(self, username, password, login_url, base_url, headless=True):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.base_url = base_url
        self.headless = headless
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    async def login(self):
        """Login to RMS2 with debugging to find correct selectors"""
        print(f"[{datetime.now()}] Navigating to login page: {self.login_url}")
        
        await self.page.goto(self.login_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        
        # Take screenshot of login page for debugging
        screenshot_path = f"data/login_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"[{datetime.now()}] Login page screenshot saved: {screenshot_path}")
        
        # Print page title and URL to verify we're on the right page
        title = await self.page.title()
        url = self.page.url
        print(f"[{datetime.now()}] Page title: {title}")
        print(f"[{datetime.now()}] Page URL: {url}")
        
        # Try different selector patterns for username field
        selectors_to_try = [
            "input[name='username']",
            "input[name='userName']",
            "input[name='email']",
            "input[name='user']",
            "input[type='text']",
            "input[placeholder*='username' i]",
            "input[placeholder*='email' i]",
            "#username",
            "#userName",
            ".username-input",
            "input.form-control",
        ]
        
        username_field = None
        for selector in selectors_to_try:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    username_field = selector
                    print(f"[{datetime.now()}] ✓ Found username field with selector: {selector}")
                    break
            except:
                continue
        
        if not username_field:
            # Dump all input fields for debugging
            print(f"[{datetime.now()}] Could not find username field. Dumping all inputs...")
            inputs = await self.page.query_selector_all("input")
            for i, inp in enumerate(inputs):
                input_type = await inp.get_attribute("type") or "unknown"
                input_name = await inp.get_attribute("name") or "no-name"
                input_id = await inp.get_attribute("id") or "no-id"
                input_placeholder = await inp.get_attribute("placeholder") or ""
                print(f"  Input {i}: type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}")
            raise Exception("Could not find username input field")
        
        # Fill username
        await self.page.fill(username_field, self.username)
        print(f"[{datetime.now()}] Filled username: {self.username[:3]}***")
        
        # Try different selectors for password field
        password_selectors = [
            "input[name='password']",
            "input[name='pass']",
            "input[type='password']",
            "#password",
            "#pass",
            ".password-input",
        ]
        
        password_field = None
        for selector in password_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    password_field = selector
                    print(f"[{datetime.now()}] ✓ Found password field with selector: {selector}")
                    break
            except:
                continue
        
        if not password_field:
            raise Exception("Could not find password input field")
        
        await self.page.fill(password_field, self.password)
        print(f"[{datetime.now()}] Filled password")
        
        # Try different selectors for login button
        button_selectors = [
            "button[type='submit']",
            "button:has-text('Login')",
            "button:has-text('Sign In')",
            "button:has-text('Submit')",
            "input[type='submit']",
            "button.ui.positive.button",
            "button.btn-primary",
            ".login-button",
            "#loginButton",
        ]
        
        login_button = None
        for selector in button_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    login_button = selector
                    print(f"[{datetime.now()}] ✓ Found login button with selector: {selector}")
                    break
            except:
                continue
        
        if not login_button:
            # Dump all buttons for debugging
            print(f"[{datetime.now()}] Could not find login button. Dumping all buttons...")
            buttons = await self.page.query_selector_all("button")
            for i, btn in enumerate(buttons):
                btn_text = await btn.text_content() or ""
                btn_class = await btn.get_attribute("class") or ""
                print(f"  Button {i}: text='{btn_text[:50]}', class='{btn_class}'")
            raise Exception("Could not find login button")
        
        # Click login button
        await self.page.click(login_button, timeout=10000)
        print(f"[{datetime.now()}] Clicked login button")
        
        # Wait for navigation
        await self.page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # Check if login succeeded
        current_url = self.page.url
        print(f"[{datetime.now()}] After login URL: {current_url}")
        
        if "login" in current_url.lower() or "auth" in current_url.lower():
            # Take screenshot of failure
            fail_screenshot = f"data/login_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=fail_screenshot)
            print(f"[{datetime.now()}] Login failed screenshot: {fail_screenshot}")
            raise Exception("Login failed - still on login/auth page")
        
        print(f"[{datetime.now()}] ✓ Login successful!")
        return True

    async def navigate_to_rcb(self):
        """Navigate to RCB page"""
        print(f"[{datetime.now()}] Navigating to RCB page: {self.base_url}")
        await self.page.goto(self.base_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        time.sleep(2)
        print(f"[{datetime.now()}] ✓ At RCB page")

    async def download_period(self, period_months, output_filename):
        """Download data for specified period"""
        print(f"[{datetime.now()}] Downloading {period_months}-month data...")
        
        # Find and select the dropdown
        dropdown_selectors = ["select", "select.form-control", ".ui.dropdown"]
        for selector in dropdown_selectors:
            try:
                await self.page.select_option(selector, str(period_months))
                print(f"[{datetime.now()}]   Selected {period_months} months using selector: {selector}")
                break
            except:
                continue
        
        await asyncio.sleep(1)
        
        # Click Display button
        display_selectors = [
            "button:has-text('Display')",
            "button:has-text('Show')",
            "button:has-text('Submit')",
            "button.ui.mini.button",
        ]
        for selector in display_selectors:
            try:
                await self.page.click(selector, timeout=5000)
                print(f"[{datetime.now()}]   Clicked 'Display' using selector: {selector}")
                break
            except:
                continue
        
        await asyncio.sleep(3)
        
        # Click Export button and download
        export_selectors = [
            "button:has-text('Export')",
            "button:has-text('Excel')",
            "button:has-text('Download')",
            "button.ui.mini.button:has-text('Export to excel')",
        ]
        
        for selector in export_selectors:
            try:
                async with self.page.context.expect_download(timeout=30000) as download_info:
                    await self.page.click(selector, timeout=5000)
                    print(f"[{datetime.now()}]   Clicked 'Export' using selector: {selector}")
                    
                    download = await download_info.value
                    await download.save_as(output_filename)
                    
                    if Path(output_filename).exists():
                        file_size = Path(output_filename).stat().st_size
                        print(f"[{datetime.now()}] ✓ Downloaded: {output_filename} ({file_size:,} bytes)")
                        return True
                    break
            except:
                continue
        
        raise Exception(f"Failed to download {period_months}-month data")

    async def run(self):
        """Main execution flow"""
        try:
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] Starting RMS2 Data Download (DEBUG MODE)")
            print(f"[{datetime.now()}] ========================================")
            
            Path("data").mkdir(exist_ok=True)
            
            print(f"[{datetime.now()}] Launching Chromium browser...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            print(f"[{datetime.now()}] ✓ Browser ready")
            
            await self.login()
            await self.navigate_to_rcb()
            await self.download_period(24, "data/RCB_24months.xlsx")
            await self.download_period(12, "data/RCB_12months.xlsx")
            
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] ✓ ALL FILES DOWNLOADED SUCCESSFULLY!")
            print(f"[{datetime.now()}] ========================================")
            return True
            
        except Exception as e:
            print(f"[{datetime.now()}] ✗ ERROR: {str(e)}")
            if self.page:
                screenshot_path = f"data/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=screenshot_path)
                print(f"[{datetime.now()}] Screenshot saved: {screenshot_path}")
            raise
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()


def main():
    username = os.environ.get("RMS_USERNAME")
    password = os.environ.get("RMS_PASSWORD")
    login_url = os.environ.get("RMS_LOGIN_URL", "https://rms2.koenig-solutions.com")
    base_url = os.environ.get("RCB_BASE_URL", "https://rms2.koenig-solutions.com/RCB")
    
    if not username or not password:
        raise ValueError("RMS_USERNAME and RMS_PASSWORD environment variables must be set")
    
    success = asyncio.run(RMS2Downloader(username, password, login_url, base_url, headless=True).run())
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
