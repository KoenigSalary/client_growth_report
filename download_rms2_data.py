"""
RMS2 Data Downloader - GitHub Actions Compatible
Analyzes page structure to find 12 and 24 month data export options
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
        print(f"[{datetime.now()}] Navigating to login page...")
        
        await self.page.goto(self.login_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        
        # Fill username and password
        await self.page.fill("input[type='text']", self.username)
        await self.page.fill("input[type='password']", self.password)
        
        # Click login button
        await self.page.click("button:has-text('Login')", timeout=10000)
        
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        
        print(f"[{datetime.now()}] ✓ Login successful!")
        return True

    async def explore_rcb_page(self):
        """Explore the RCB page to find data export options"""
        print(f"[{datetime.now()}] Exploring RCB page: {self.base_url}")
        await self.page.goto(self.base_url, timeout=60000)
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        # Take screenshot
        screenshot_path = f"data/rcb_main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"[{datetime.now()}] Screenshot saved: {screenshot_path}")
        
        # Find all links on the page
        print(f"\n[{datetime.now()}] ========== LINKS ON RCB PAGE ==========")
        links = await self.page.query_selector_all("a")
        for i, link in enumerate(links):
            href = await link.get_attribute("href") or ""
            text = await link.text_content() or ""
            text = text.strip()[:50]
            if href and not href.startswith("#"):
                print(f"  Link {i}: '{text}' -> {href}")
        
        # Find all tabs/menu items
        print(f"\n[{datetime.now()}] ========== POSSIBLE TABS/MENUS ==========")
        tab_selectors = [
            ".tab", ".nav-link", ".menu-item", "[role='tab']", 
            ".ui.tab", ".tab-pane", "button:has-text('History')",
            "button:has-text('Report')", "button:has-text('Export')"
        ]
        for selector in tab_selectors:
            elements = await self.page.query_selector_all(selector)
            for elem in elements:
                text = await elem.text_content() or ""
                text = text.strip()[:50]
                if text:
                    print(f"  Tab/menu: '{text}'")
        
        # Try to find period/duration selector
        print(f"\n[{datetime.now()}] ========== SEARCHING FOR PERIOD SELECTORS ==========")
        
        # Look for dropdowns that might contain period options
        selects = await self.page.query_selector_all("select")
        for sel in selects:
            sel_id = await sel.get_attribute("id") or ""
            sel_name = await sel.get_attribute("name") or ""
            sel_class = await sel.get_attribute("class") or ""
            print(f"  Select: id='{sel_id}', name='{sel_name}', class='{sel_class}'")
            
            # Get options
            options = await sel.query_selector_all("option")
            for opt in options:
                opt_value = await opt.get_attribute("value") or ""
                opt_text = await opt.text_content() or ""
                print(f"    Option: value='{opt_value}', text='{opt_text}'")
        
        # Look for any element with "12" or "24" in text
        print(f"\n[{datetime.now()}] ========== ELEMENTS WITH '12' or '24' ==========")
        elements_with_numbers = await self.page.query_selector_all("*:has-text('12'), *:has-text('24')")
        for elem in elements_with_numbers[:20]:  # Limit to 20
            text = await elem.text_content() or ""
            tag = await elem.evaluate("el => el.tagName")
            if text.strip() and len(text.strip()) < 100:
                print(f"  {tag}: '{text.strip()[:80]}'")
        
        return True

    async def try_alternative_urls(self):
        """Try alternative RCB URLs that might have historical data"""
        alternative_urls = [
            f"{self.base_url}/History",
            f"{self.base_url}/Report",
            f"{self.base_url}/Export",
            f"{self.base_url}/Data",
            f"{self.base_url}/Monthly",
            f"{self.base_url}/Historical",
            f"{self.base_url}/12months",
            f"{self.base_url}/24months",
            "https://rms2.koenig-solutions.com/Reports/RCB",
            "https://rms2.koenig-solutions.com/Reports/RCB/Export",
        ]
        
        print(f"\n[{datetime.now()}] ========== TRYING ALTERNATIVE URLs ==========")
        
        for url in alternative_urls:
            print(f"[{datetime.now()}] Trying: {url}")
            try:
                await self.page.goto(url, timeout=30000)
                await self.page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                # Check if this page has export functionality
                export_buttons = await self.page.query_selector_all("button:has-text('Export'), a:has-text('Export')")
                if export_buttons:
                    print(f"  ✓ Found {len(export_buttons)} export buttons on this page!")
                    # Take screenshot
                    screenshot_path = f"data/export_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=screenshot_path)
                    print(f"  Screenshot saved: {screenshot_path}")
                    return url
                else:
                    print(f"  No export buttons found")
            except Exception as e:
                print(f"  Failed: {str(e)[:50]}")
                continue
        
        return None

    async def try_direct_export_with_parameters(self):
        """Try to trigger export by manipulating URL parameters or form data"""
        print(f"\n[{datetime.now()}] ========== TRYING DIRECT EXPORT ==========")
        
        # Look for any "Export to Excel" button on the current page
        export_selectors = [
            "button:has-text('Export')",
            "button:has-text('Excel')",
            "button:has-text('Download')",
            "a:has-text('Export')",
            "a:has-text('Excel')",
            ".export-excel",
            ".excel-export",
            "button[title*='Excel']",
            "a[download*='xlsx']",
            "button:has-text('CSV')",
        ]
        
        for selector in export_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    print(f"[{datetime.now()}] Found export button with selector: {selector}")
                    async with self.page.context.expect_download(timeout=60000) as download_info:
                        await self.page.click(selector, timeout=5000)
                        download = await download_info.value
                        
                        # Determine which period this is (we'll need to do two separate exports)
                        filename = f"data/RCB_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        await download.save_as(filename)
                        print(f"[{datetime.now()}] ✓ Downloaded: {filename}")
                        return filename
            except Exception as e:
                print(f"  Selector '{selector}' failed: {str(e)[:50]}")
                continue
        
        return None

    async def try_different_rcb_endpoints(self):
        """Try different RCB endpoints that might have period parameters"""
        # These are common patterns for period-based data
        endpoints = [
            "/RCB/GetData?period=12",
            "/RCB/GetData?period=24",
            "/RCB/Export?months=12",
            "/RCB/Export?months=24",
            "/RCB/Download?type=excel&months=12",
            "/RCB/Download?type=excel&months=24",
            "/RCB/Report?duration=12",
            "/RCB/Report?duration=24",
        ]
        
        print(f"\n[{datetime.now()}] ========== TRYING PERIOD ENDPOINTS ==========")
        
        for endpoint in endpoints:
            url = f"https://rms2.koenig-solutions.com{endpoint}"
            print(f"[{datetime.now()}] Trying: {url}")
            try:
                response = await self.page.goto(url, timeout=30000)
                if response and response.ok:
                    # Check if we got an Excel file
                    content_type = response.headers.get("content-type", "")
                    if "excel" in content_type or "spreadsheet" in content_type:
                        # Save the response as file
                        body = await response.body()
                        if endpoint.find("12") > -1:
                            filename = "data/RCB_12months.xlsx"
                        else:
                            filename = "data/RCB_24months.xlsx"
                        
                        with open(filename, "wb") as f:
                            f.write(body)
                        print(f"[{datetime.now()}] ✓ Downloaded directly: {filename}")
                        return True
            except Exception as e:
                print(f"  Failed: {str(e)[:50]}")
                continue
        
        return False

    async def manual_period_selection_guide(self):
        """Print guide for manual period selection - user needs to help identify where period is"""
        print(f"\n[{datetime.now()}] ========================================")
        print(f"[{datetime.now()}] CANNOT FIND PERIOD SELECTOR AUTOMATICALLY")
        print(f"[{datetime.now()}] ========================================")
        print(f"""
Please manually check the RMS2 RCB page at: {self.base_url}

Look for where you select "12 months" and "24 months" data. 
Common locations:
1. A dropdown at the top of the page
2. A sidebar menu with "Reports" or "History"
3. A "From Date" and "To Date" date picker
4. A separate tab for "Monthly Report" or "Periodic Report"
5. A filter section that says "Last 12 months" or "Last 24 months"

Once you identify where the period selection is, please describe:
- What the element looks like (dropdown, radio button, tabs)
- Any labels or text near it
- The URL when you select different periods

This will help me create the correct selectors.
""")
        
        # Save full page HTML for debugging
        html_path = f"data/rcb_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html_content = await self.page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[{datetime.now()}] Full page HTML saved to: {html_path}")

    async def run(self):
        """Main execution flow"""
        try:
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] Starting RMS2 Data Download (Discovery Mode)")
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
            
            # Login
            await self.login()
            
            # Explore RCB page to find structure
            await self.explore_rcb_page()
            
            # Try alternative URLs
            export_url = await self.try_alternative_urls()
            
            # Try direct export from current page
            downloaded_file = await self.try_direct_export_with_parameters()
            
            if downloaded_file:
                print(f"[{datetime.now()}] Successfully downloaded: {downloaded_file}")
                # We need to find both 12 and 24 month exports
                # This might require two separate actions
            else:
                # Try period endpoints
                success = await self.try_different_rcb_endpoints()
                if not success:
                    await self.manual_period_selection_guide()
            
            print(f"[{datetime.now()}] ========================================")
            print(f"[{datetime.now()}] Discovery complete. Check data/ folder for:")
            print(f"[{datetime.now()}] - Screenshots of the RCB page")
            print(f"[{datetime.now()}] - HTML dump of the page")
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
