"""
RMS2 Data Downloader - GitHub Actions Compatible
Downloads both 24-month and 12-month data from RMS2
Workflow: Type period → Apply Filters → Export Excel
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

    async def navigate_to_rcb(self):
        """Navigate to RCB page"""
        print(f"[{datetime.now()}] Navigating to RCB page...")
        await self.page.goto(self.base_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        # Take screenshot of RCB page for debugging
        screenshot_path = f"data/rcb_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"[{datetime.now()}] RCB page screenshot saved: {screenshot_path}")
        
        print(f"[{datetime.now()}] ✓ At RCB page")

    async def download_period_data(self, period_value, output_filename):
        """
        Download data for a specific period
        Steps:
        1. Clear and type the period value (12 or 24) into the input field
        2. Click "Apply Filters" button
        3. Click "Export Excel" button and download
        """
        print(f"\n[{datetime.now()}] {'='*50}")
        print(f"[{datetime.now()}] DOWNLOADING {period_value}-MONTH DATA")
        print(f"[{datetime.now()}] Saving to: {output_filename}")
        print(f"[{datetime.now()}] {'='*50}")
        
        # Step 1: Find and clear the period input field
        # The input has placeholder="12" and type="text"
        print(f"[{datetime.now()}] Step 1: Finding period input field...")
        
        period_input_selectors = [
            "input[placeholder='12']",
            "input[placeholder='24']",
            "input[type='text'][class*='MuiOutlinedInput-input']",
            ".MuiOutlinedInput-input",
            "input[class*='MuiInputBase-input']",
        ]
        
        period_input = None
        for selector in period_input_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    period_input = element
                    print(f"[{datetime.now()}] ✓ Found period input with selector: {selector}")
                    break
            except:
                continue
        
        if not period_input:
            # Try to find by placeholder text
            print(f"[{datetime.now()}] Looking for input with placeholder containing number...")
            all_inputs = await self.page.query_selector_all("input[type='text']")
            for inp in all_inputs:
                placeholder = await inp.get_attribute("placeholder") or ""
                if placeholder.isdigit() or placeholder in ["12", "24"]:
                    period_input = inp
                    print(f"[{datetime.now()}] ✓ Found period input with placeholder='{placeholder}'")
                    break
        
        if not period_input:
            print(f"[{datetime.now()}] ❌ Could not find period input field!")
            # Dump all inputs for debugging
            all_inputs = await self.page.query_selector_all("input")
            print(f"[{datetime.now()}] All input fields found:")
            for i, inp in enumerate(all_inputs):
                inp_type = await inp.get_attribute("type") or ""
                inp_placeholder = await inp.get_attribute("placeholder") or ""
                inp_class = await inp.get_attribute("class") or ""
                print(f"  Input {i}: type='{inp_type}', placeholder='{inp_placeholder}', class='{inp_class[:50]}'")
            return False
        
        # Clear and fill the period input
        try:
            await period_input.fill("")
            await asyncio.sleep(0.5)
            await period_input.fill(str(period_value))
            print(f"[{datetime.now()}] ✓ Set period to: {period_value}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Failed to set period value: {e}")
            return False
        
        # Step 2: Click "Apply Filters" button
        print(f"[{datetime.now()}] Step 2: Clicking 'Apply Filters' button...")
        
        apply_filters_selectors = [
            "button:has-text('Apply Filters')",
            "button.rcb-apply-btn",
            "button:has-text('Apply')",
            "button:has-text('Filter')",
            ".rcb-apply-btn",
            "button[class*='apply']",
        ]
        
        apply_clicked = False
        for selector in apply_filters_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    await self.page.click(selector, timeout=5000)
                    print(f"[{datetime.now()}] ✓ Clicked 'Apply Filters' using: {selector}")
                    apply_clicked = True
                    break
            except:
                continue
        
        if not apply_clicked:
            print(f"[{datetime.now()}] ❌ Could not find 'Apply Filters' button!")
            # Dump all buttons for debugging
            all_buttons = await self.page.query_selector_all("button")
            print(f"[{datetime.now()}] All buttons found:")
            for i, btn in enumerate(all_buttons):
                btn_text = await btn.text_content() or ""
                btn_class = await btn.get_attribute("class") or ""
                print(f"  Button {i}: text='{btn_text[:30]}', class='{btn_class[:50]}'")
            return False
        
        # Wait for data to load after applying filters
        print(f"[{datetime.now()}] Waiting for data to load...")
        await asyncio.sleep(5)
        
        # Step 3: Click "Export Excel" button and download
        print(f"[{datetime.now()}] Step 3: Clicking 'Export Excel' button...")
        
        export_selectors = [
            "button:has-text('Export Excel')",
            "button:has-text('Export')",
            ".rcb-header-btn",
            "button[class*='rcb-header-btn']",
            "button:has-text('Excel')",
            "button i.file.excel.outline.icon",
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
                        suggested_filename = download.suggested_filename
                        print(f"[{datetime.now()}] Suggested filename: {suggested_filename}")
                        
                        # Save with the specified output filename
                        await download.save_as(output_filename)
                        
                        if Path(output_filename).exists():
                            file_size = Path(output_filename).stat().st_size
                            print(f"[{datetime.now()}] ✓ Downloaded: {output_filename} ({file_size:,} bytes)")
                            return True
                    break
            except Exception as e:
                print(f"  Export selector '{selector}' failed: {str(e)[:80]}")
                continue
        
        print(f"[{datetime.now()}] ❌ Could not find 'Export Excel' button!")
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
            
            # Login and navigate
            await self.login()
            await self.navigate_to_rcb()
            
            # Download 24-month data first
            success_24 = await self.download_period_data(24, "data/RCB_24months.xlsx")
            
            if not success_24:
                print(f"[{datetime.now()}] ⚠️ Failed to download 24-month data")
            
            # Wait between downloads
            await asyncio.sleep(3)
            
            # Download 12-month data
            success_12 = await self.download_period_data(12, "data/RCB_12months.xlsx")
            
            if not success_12:
                print(f"[{datetime.now()}] ⚠️ Failed to download 12-month data")
            
            # Final summary
            print(f"\n[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] DOWNLOAD SUMMARY")
            print(f"[{datetime.now()}] ========================================")
            print(f"  24-month data: {'✅ SUCCESS' if success_24 else '❌ FAILED'}")
            print(f"  12-month data: {'✅ SUCCESS' if success_12 else '❌ FAILED'}")
            
            # Verify files exist
            print(f"\n[{datetime.now()}] Verifying downloaded files...")
            for file in ["data/RCB_24months.xlsx", "data/RCB_12months.xlsx"]:
                if Path(file).exists():
                    size = Path(file).stat().st_size
                    print(f"  ✅ {file} ({size:,} bytes)")
                else:
                    print(f"  ❌ {file} not found")
            
            if success_24 and success_12:
                print(f"\n[{datetime.now()}] 🎉 ALL FILES DOWNLOADED SUCCESSFULLY!")
                return True
            else:
                print(f"\n[{datetime.now()}] ⚠️ Some downloads failed. Check logs above.")
                return False
            
        except Exception as e:
            print(f"[{datetime.now()}] ❌ ERROR: {str(e)}")
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
