"""
RMS2 Data Downloader - GitHub Actions compatible
Downloads RCB_24months.xlsx and RCB_12months.xlsx from RMS2
Uses Playwright with proper two-step download process (Display → Export)
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
        """Login to RMS2 with credentials"""
        print(f"[{datetime.now()}] Logging in to RMS2...")
        
        await self.page.goto(self.login_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        
        # Fill username and password
        await self.page.fill("input[name='username']", self.username)
        await self.page.fill("input[name='password']", self.password)
        
        # Click login button - RMS2 uses button.ui.positive.button
        await self.page.click("button.ui.positive.button", timeout=10000)
        await self.page.wait_for_load_state("networkidle")
        
        print(f"[{datetime.now()}] Login submitted, checking success...")
        
        # Check if login succeeded
        if "login" in self.page.url.lower():
            raise Exception("Login failed - still on login page")
        
        print(f"[{datetime.now()}] ✓ Login successful!")
        return True

    async def navigate_to_rcb(self):
        """Navigate to RCB page"""
        print(f"[{datetime.now()}] Navigating to RCB page...")
        await self.page.goto(self.base_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        time.sleep(2)
        print(f"[{datetime.now()}] ✓ At RCB page")

    async def download_period(self, period_months, output_filename):
        """
        Download data for specified period using two-step process:
        1. Select period and click "Display" button
        2. Wait for data to load
        3. Click "Export to excel" button
        """
        print(f"[{datetime.now()}] Downloading {period_months}-month data...")
        
        # Step 1: Select period from dropdown
        await self.page.select_option("select", str(period_months))
        print(f"[{datetime.now()}]   Selected {period_months} months period")
        
        # Step 2: Click "Display" button to load data
        await self.page.click("button.ui.mini.button:has-text('Display')", timeout=10000)
        print(f"[{datetime.now()}]   Clicked 'Display' button")
        
        # Wait for data to load (3 seconds for table to refresh)
        await asyncio.sleep(3)
        
        # Step 3: Click "Export to excel" button and download
        async with self.page.context.expect_download() as download_info:
            await self.page.click("button.ui.mini.button:has-text('Export to excel')", timeout=10000)
            print(f"[{datetime.now()}]   Clicked 'Export to excel' button")
        
        # Save the downloaded file
        download = await download_info.value
        await download.save_as(output_filename)
        
        # Verify file was saved
        if Path(output_filename).exists():
            file_size = Path(output_filename).stat().st_size
            print(f"[{datetime.now()}] ✓ Downloaded: {output_filename} ({file_size:,} bytes)")
            return True
        else:
            raise Exception(f"Failed to save {output_filename}")

    async def download_24month_data(self):
        """Download 24-month data"""
        return await self.download_period(24, "data/RCB_24months.xlsx")

    async def download_12month_data(self):
        """Download 12-month data"""
        return await self.download_period(12, "data/RCB_12months.xlsx")

    async def run(self):
        """Main execution flow"""
        try:
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] Starting RMS2 Data Download")
            print(f"[{datetime.now()}] ========================================")
            
            # Create data directory if needed
            Path("data").mkdir(exist_ok=True)
            
            # Launch browser
            print(f"[{datetime.now()}] Launching Chromium browser...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage']  # For GitHub Actions
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            print(f"[{datetime.now()}] ✓ Browser ready")
            
            # Execute steps
            await self.login()
            await self.navigate_to_rcb()
            await self.download_24month_data()
            await self.download_12month_data()
            
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] ✓ ALL FILES DOWNLOADED SUCCESSFULLY!")
            print(f"[{datetime.now()}] ========================================")
            return True
            
        except Exception as e:
            print(f"[{datetime.now()}] ✗ ERROR: {str(e)}")
            
            # Take screenshot on error
            if self.page:
                screenshot_path = f"data/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=screenshot_path)
                print(f"[{datetime.now()}] Screenshot saved: {screenshot_path}")
            
            raise
            
        finally:
            # Clean up
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()


def main():
    """Entry point for GitHub Actions"""
    username = os.environ.get("RMS_USERNAME")
    password = os.environ.get("RMS_PASSWORD")
    login_url = os.environ.get("RMS_LOGIN_URL", "https://rms2.koenig-solutions.com")
    base_url = os.environ.get("RCB_BASE_URL", "https://rms2.koenig-solutions.com/RCB")
    
    if not username or not password:
        raise ValueError("RMS_USERNAME and RMS_PASSWORD environment variables must be set")
    
    # Run the async downloader (headless=True for GitHub Actions)
    downloader = RMS2Downloader(username, password, login_url, base_url, headless=True)
    success = asyncio.run(downloader.run())
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
