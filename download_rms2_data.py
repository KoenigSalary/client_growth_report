"""
Download RCB data files from RMS2 using Playwright
Optimized for GitHub Actions with correct two-step download process
"""

import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Install with: pip install playwright python-dotenv")
    sys.exit(1)


class RMS2DataDownloader:
    """Download RCB data files from RMS2 system"""
    
    def __init__(self, data_dir='data'):
        """Initialize downloader"""
        self.username = os.getenv('RMS_USERNAME')
        self.password = os.getenv('RMS_PASSWORD')
        self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
        self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        
        if not self.username or not self.password:
            raise ValueError("RMS_USERNAME and RMS_PASSWORD must be set in environment or .env file")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def log(self, message):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def setup_browser(self):
        """Setup Playwright browser"""
        self.log("Setting up browser...")
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = self.browser.new_context(accept_downloads=True)
            self.page = self.context.new_page()
            
            # Set longer default timeout
            self.page.set_default_timeout(60000)
            
            self.log("Browser ready")
            
        except Exception as e:
            raise Exception(f"Browser setup failed: {str(e)}")
    
    def login(self):
        """Login to RMS2"""
        self.log("Logging in to RMS2...")
        
        try:
            # Go to login page
            self.page.goto(self.login_url, wait_until='domcontentloaded')
            self.page.wait_for_timeout(3000)
            
            # Fill credentials
            self.page.fill("input[placeholder='Your Email']", self.username)
            self.page.fill("input[placeholder='Password']", self.password)
            self.page.wait_for_timeout(1000)
            
            # Click login button
            self.page.click("button.ui.positive.button")
            
            # Wait for navigation
            self.page.wait_for_load_state('domcontentloaded')
            self.page.wait_for_timeout(3000)
            
            self.log("Login successful")
            
        except Exception as e:
            screenshot_path = self.data_dir / 'login_error.png'
            self.page.screenshot(path=str(screenshot_path))
            self.log(f"Login error screenshot saved: {screenshot_path}")
            raise Exception(f"Login failed: {str(e)}")
    
    def download_file(self, period_months, target_filename):
        """
        Download RCB file using correct two-step process:
        1. Select period
        2. Click 'Display' button
        3. Click 'Export to excel' button
        """
        self.log(f"Downloading {period_months}-month data...")
        
        try:
            # Go to RCB page
            self.page.goto(self.rcb_url, wait_until='domcontentloaded')
            self.page.wait_for_timeout(3000)
            
            # Step 1: Select period from dropdown
            try:
                self.log(f"Selecting {period_months} months period...")
                self.page.select_option("select", str(period_months))
                self.page.wait_for_timeout(2000)
            except Exception as e:
                self.log(f"Warning: Could not select period - {e}")
            
            # Step 2: Click 'Display' button
            # Button HTML: <button class="ui mini button" style="float: right;"><i aria-hidden="true" class="teal filter icon"></i>Display</button>
            self.log("Clicking 'Display' button...")
            try:
                # Try specific selector first
                self.page.click("button.ui.mini.button:has-text('Display')")
            except:
                # Fallback: find button with filter icon
                self.page.click("button.ui.mini.button:has(i.filter.icon)")
            
            self.page.wait_for_timeout(3000)  # Wait for data to display
            
            # Step 3: Click 'Export to excel' button and expect download
            # Button HTML: <button class="ui mini button">Export to excel</button>
            self.log("Clicking 'Export to excel' button...")
            with self.page.expect_download(timeout=90000) as download_info:
                self.page.click("button.ui.mini.button:has-text('Export to excel')")
            
            download = download_info.value
            
            # Save file
            target_path = self.data_dir / target_filename
            download.save_as(target_path)
            
            # Verify file
            if not target_path.exists():
                raise Exception("Download failed - file not found")
            
            file_size = target_path.stat().st_size
            if file_size < 1000:
                raise Exception(f"Download failed - file too small ({file_size} bytes)")
            
            self.log(f"✓ Downloaded: {target_filename} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            screenshot_path = self.data_dir / f'download_{period_months}m_error.png'
            self.page.screenshot(path=str(screenshot_path))
            self.log(f"Download error screenshot saved: {screenshot_path}")
            raise Exception(f"Download {period_months}M failed: {str(e)}")
    
    def cleanup(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.log("Browser cleanup complete")
        except Exception as e:
            self.log(f"Cleanup warning: {e}")
    
    def download_both_files(self):
        """Download both 24M and 12M files"""
        try:
            self.setup_browser()
            self.login()
            
            # Download 24 months file
            self.download_file(24, 'RCB_24months.xlsx')
            
            # Download 12 months file
            self.download_file(12, 'RCB_12months.xlsx')
            
            self.log("✓ All files downloaded successfully!")
            return True
            
        except Exception as e:
            self.log(f"✗ Download failed: {str(e)}")
            return False
            
        finally:
            self.cleanup()


def main():
    """Main entry point"""
    print("=" * 60)
    print("RMS2 Data Downloader")
    print("=" * 60)
    
    try:
        downloader = RMS2DataDownloader()
        success = downloader.download_both_files()
        
        if success:
            print("\n" + "=" * 60)
            print("SUCCESS: All files downloaded")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("FAILED: Check logs above for details")
            print("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
