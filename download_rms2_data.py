"""
RMS2 Data Downloader - GitHub Actions compatible
Downloads RCB_24months.xlsx and RCB_12months.xlsx from RMS2
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
        print(f"[{datetime.now()}] Logging in to RMS2...")
        
        await self.page.goto(self.login_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        
        await self.page.fill("input[name='username']", self.username)
        await self.page.fill("input[name='password']", self.password)
        await self.page.click("button.ui.positive.button", timeout=10000)
        await self.page.wait_for_load_state("networkidle")
        
        if "login" in self.page.url.lower():
            raise Exception("Login failed - still on login page")
        
        print(f"[{datetime.now()}] ✓ Login successful!")

    async def navigate_to_rcb(self):
        print(f"[{datetime.now()}] Navigating to RCB page...")
        await self.page.goto(self.base_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        time.sleep(2)

    async def download_period(self, period_months, output_filename):
        print(f"[{datetime.now()}] Downloading {period_months}-month data...")
        
        await self.page.select_option("select", str(period_months))
        await self.page.click("button.ui.mini.button:has-text('Display')", timeout=10000)
        await asyncio.sleep(3)
        
        async with self.page.context.expect_download() as download_info:
            await self.page.click("button.ui.mini.button:has-text('Export to excel')", timeout=10000)
        
        download = await download_info.value
        await download.save_as(output_filename)
        
        file_size = Path(output_filename).stat().st_size
        print(f"[{datetime.now()}] ✓ Downloaded: {output_filename} ({file_size:,} bytes)")

    async def run(self):
        try:
            print(f"[{datetime.now()}] Starting RMS2 Data Download...")
            Path("data").mkdir(exist_ok=True)
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            
            await self.login()
            await self.navigate_to_rcb()
            await self.download_period(24, "data/RCB_24months.xlsx")
            await self.download_period(12, "data/RCB_12months.xlsx")
            
            print(f"[{datetime.now()}] ✓ ALL FILES DOWNLOADED SUCCESSFULLY!")
            return True
            
        except Exception as e:
            print(f"[{datetime.now()}] ✗ ERROR: {str(e)}")
            if self.page:
                await self.page.screenshot(path=f"data/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
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
        raise ValueError("RMS_USERNAME and RMS_PASSWORD must be set")
    
    success = asyncio.run(RMS2Downloader(username, password, login_url, base_url, headless=True).run())
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
