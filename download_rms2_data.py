"""
RMS2 Data Downloader - GitHub Actions Compatible
Downloads the 24-month RCB data from RMS2
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
        """Login to RMS2"""
        print(f"[{datetime.now()}] Logging in to RMS2...")
        
        await self.page.goto(self.login_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        
        # Fill username and password
        await self.page.fill("input[type='text']", self.username)
        await self.page.fill("input[type='password']", self.password)
        
        # Click login button
        await self.page.click("button:has-text('Login')", timeout=10000)
        
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        print(f"[{datetime.now()}] ✓ Login successful!")
        return True

    async def download_rcb_data(self):
        """Navigate to RCB page and download the Excel file"""
        print(f"[{datetime.now()}] Navigating to RCB page...")
        await self.page.goto(self.base_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        # Take screenshot for debugging
        screenshot_path = f"data/rcb_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"[{datetime.now()}] RCB page screenshot saved: {screenshot_path}")
        
        # Look for Export/Download button
        print(f"[{datetime.now()}] Looking for Export button...")
        
        export_selectors = [
            "button:has-text('Export')",
            "button:has-text('Excel')",
            "button:has-text('Download')",
            "button:has-text('Export to Excel')",
            "button:has-text('Export to excel')",
            "a:has-text('Export')",
            "a:has-text('Excel')",
            "button[title*='Export']",
            ".export-excel",
            ".excel-button",
            "button:has-text('CSV')",
            "a[download]",
        ]
        
        for selector in export_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    print(f"[{datetime.now()}] Found export button with selector: {selector}")
                    
                    # Expect download and save
                    async with self.page.context.expect_download(timeout=120000) as download_info:
                        await self.page.click(selector, timeout=5000)
                        print(f"[{datetime.now()}] Clicked export button, waiting for download...")
                        
                        download = await download_info.value
                        
                        # Determine filename (should be RCB_24months.xlsx)
                        suggested_filename = download.suggested_filename
                        print(f"[{datetime.now()}] Suggested filename: {suggested_filename}")
                        
                        # Save as RCB_24months.xlsx
                        output_filename = "data/RCB_24months.xlsx"
                        await download.save_as(output_filename)
                        
                        if Path(output_filename).exists():
                            file_size = Path(output_filename).stat().st_size
                            print(f"[{datetime.now()}] ✓ Downloaded: {output_filename} ({file_size:,} bytes)")
                            return True
                    break
            except Exception as e:
                print(f"  Export selector '{selector}' failed: {str(e)[:80]}")
                continue
        
        # If no export button found, look for any link that might download Excel
        print(f"[{datetime.now()}] Looking for download links...")
        links = await self.page.query_selector_all("a")
        for link in links:
            href = await link.get_attribute("href") or ""
            if ".xlsx" in href or ".xls" in href or "export" in href.lower():
                print(f"[{datetime.now()}] Found potential download link: {href}")
                try:
                    async with self.page.context.expect_download(timeout=120000) as download_info:
                        await link.click()
                        download = await download_info.value
                        await download.save_as("data/RCB_24months.xlsx")
                        
                        if Path("data/RCB_24months.xlsx").exists():
                            file_size = Path("data/RCB_24months.xlsx").stat().st_size
                            print(f"[{datetime.now()}] ✓ Downloaded via link: RCB_24months.xlsx ({file_size:,} bytes)")
                            return True
                except Exception as e:
                    print(f"  Link download failed: {str(e)[:50]}")
                    continue
        
        print(f"[{datetime.now()}] ⚠️ Could not find export button or download link!")
        
        # Save HTML for debugging
        html_path = f"data/rcb_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html_content = await self.page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[{datetime.now()}] Page HTML saved to: {html_path}")
        
        return False

    async def run(self):
        """Main execution flow"""
        try:
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] Starting RMS2 Data Download")
            print(f"[{datetime.now()}] ========================================")
            
            Path("data").mkdir(exist_ok=True)
            
            # Launch browser
            print(f"[{datetime.now()}] Launching Chromium browser...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            print(f"[{datetime.now()}] ✓ Browser ready")
            
            # Login and download
            await self.login()
            success = await self.download_rcb_data()
            
            if success:
                print(f"[{datetime.now()}] ========================================")
                print(f"[{datetime.now()}] ✓ RCB_24months.xlsx DOWNLOADED SUCCESSFULLY!")
                print(f"[{datetime.now()}] ========================================")
                return True
            else:
                print(f"[{datetime.now()}] ========================================")
                print(f"[{datetime.now()}] ✗ DOWNLOAD FAILED")
                print(f"[{datetime.now()}] ========================================")
                return False
            
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
