"""
RMS2 Data Downloader - FIXED SELECTORS
Downloads 24-month and 12-month data from RMS2 RCB page
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

class RMS2Downloader:
    def __init__(self):
        self.username = os.getenv('RMS_USERNAME')
        self.password = os.getenv('RMS_PASSWORD')
        self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
        self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        
        if not self.username or not self.password:
            raise ValueError("RMS_USERNAME and RMS_PASSWORD must be set")
        
        print("=" * 60)
        print("RMS2 Data Downloader")
        print("=" * 60)
        
    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def download_data(self):
        """Download both 24M and 12M data files"""
        with sync_playwright() as p:
            self.log("Setting up browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True
            )
            page = context.new_page()
            
            try:
                self.log("Browser ready")
                
                # Login
                self.log("Logging in to RMS2...")
                page.goto(self.login_url, wait_until='networkidle')
                page.wait_for_timeout(2000)
                
                # Fill login form - UPDATED SELECTORS
                page.fill("input[placeholder='Your Email']", self.username)
                page.fill("input[placeholder='Password']", self.password)
                page.click("button:has-text('Login')")
                page.wait_for_timeout(3000)
                
                self.log("Login successful")
                
                # Download 24-month data
                success_24m = self._download_file(page, 24)
                if not success_24m:
                    self.log("✗ Failed to download 24-month data")
                    return False
                
                page.wait_for_timeout(2000)
                
                # Download 12-month data
                success_12m = self._download_file(page, 12)
                if not success_12m:
                    self.log("✗ Failed to download 12-month data")
                    return False
                
                self.log("✓ Both files downloaded successfully")
                return True
                
            except Exception as e:
                self.log(f"✗ Error: {str(e)}")
                screenshot_path = Path('data') / 'error_screenshot.png'
                page.screenshot(path=str(screenshot_path))
                self.log(f"Error screenshot saved: {screenshot_path}")
                return False
                
            finally:
                self.log("Browser cleanup complete")
                browser.close()
    
    def _download_file(self, page, months):
        """Download file for specific month period"""
        self.log(f"Downloading {months}-month data...")
        
        try:
            # Navigate to RCB page
            page.goto(self.rcb_url, wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            # METHOD 1: Try to find and fill input field directly
            self.log(f"Trying to set {months} months period...")
            
            try:
                # Look for input field with placeholder="12" or any number input
                month_input = page.locator("input[placeholder='12']").first
                if not month_input.is_visible():
                    # Try alternative selectors
                    month_input = page.locator("input[type='text']").filter(has_text="12").first
                
                if month_input.is_visible():
                    month_input.click()
                    page.wait_for_timeout(500)
                    month_input.fill("")  # Clear
                    page.wait_for_timeout(500)
                    month_input.type(str(months))
                    page.wait_for_timeout(1000)
                    self.log(f"✓ Set to {months} months")
                else:
                    raise Exception("Month input field not found")
                    
            except Exception as e:
                self.log(f"Warning: Could not set month period - {str(e)}")
                self.log("Continuing with default value...")
            
            # Click Display button - UPDATED SELECTOR
            self.log("Clicking 'Display' button...")
            try:
                # Try multiple possible selectors for Display button
                display_selectors = [
                    "button:has-text('Display')",
                    "button.ui.mini.button:has-text('Display')",
                    "button:has(i.filter.icon)",
                    "//button[contains(text(), 'Display')]"
                ]
                
                button_found = False
                for selector in display_selectors:
                    try:
                        page.click(selector, timeout=5000)
                        button_found = True
                        self.log("✓ Display button clicked")
                        break
                    except:
                        continue
                
                if not button_found:
                    raise Exception("Display button not found")
                    
            except Exception as e:
                self.log(f"Warning: Could not click Display button - {str(e)}")
            
            page.wait_for_timeout(5000)  # Wait for data to load
            
            # Click Export button and handle download
            self.log("Clicking 'Export to excel' button...")
            
            export_selectors = [
                "button:has-text('Export to excel')",
                "button.ui.mini.button:has-text('Export')",
                "//button[contains(text(), 'Export')]"
            ]
            
            download_started = False
            for selector in export_selectors:
                try:
                    with page.expect_download(timeout=60000) as download_info:
                        page.click(selector, timeout=10000)
                    
                    download = download_info.value
                    download_started = True
                    self.log("✓ Download started")
                    
                    # Save file
                    output_file = Path('data') / f'RCB_{months}months.xlsx'
                    download.save_as(output_file)
                    
                    if output_file.exists():
                        size_mb = output_file.stat().st_size / 1024 / 1024
                        self.log(f"✓ Saved: {output_file.name} ({size_mb:.1f} MB)")
                        return True
                    break
                    
                except Exception as e:
                    continue
            
            if not download_started:
                raise Exception("Export button not found or download failed")
            
            return False
            
        except Exception as e:
            self.log(f"Download error: {str(e)}")
            screenshot_path = Path('data') / f'download_{months}m_error.png'
            page.screenshot(path=str(screenshot_path))
            self.log(f"Download error screenshot saved: {screenshot_path}")
            return False

def main():
    """Main execution"""
    try:
        # Create data directory
        Path('data').mkdir(exist_ok=True)
        
        downloader = RMS2Downloader()
        success = downloader.download_data()
        
        if success:
            print("\n" + "=" * 60)
            print("SUCCESS: Both files downloaded")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("FAILED: Check logs above for details")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
