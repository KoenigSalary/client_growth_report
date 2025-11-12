"""
Download RCB data files from RMS2 using Playwright
Simplified version with correct selectors for RMS2
"""

import os
import time
from pathlib import Path
from datetime import datetime

# Try to import streamlit for secrets
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from dotenv import load_dotenv
load_dotenv()


class RMS2DataDownloader:
    """Download RCB data files from RMS2 system"""
    
    def __init__(self, data_dir='data', progress_callback=None):
        """Initialize downloader"""
        # Get credentials from Streamlit secrets or .env
        if HAS_STREAMLIT and hasattr(st, 'secrets'):
            try:
                self.username = st.secrets.get('RMS_USERNAME', os.getenv('RMS_USERNAME'))
                self.password = st.secrets.get('RMS_PASSWORD', os.getenv('RMS_PASSWORD'))
                self.login_url = st.secrets.get('RMS_LOGIN_URL', os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com'))
                self.rcb_url = st.secrets.get('RCB_BASE_URL', os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB'))
            except:
                self.username = os.getenv('RMS_USERNAME')
                self.password = os.getenv('RMS_PASSWORD')
                self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
                self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        else:
            self.username = os.getenv('RMS_USERNAME')
            self.password = os.getenv('RMS_PASSWORD')
            self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
            self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        
        if not self.username or not self.password:
            raise ValueError("RMS_USERNAME and RMS_PASSWORD must be set")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.browser = None
        self.page = None
        self.progress_callback = progress_callback
        
    def update_progress(self, message, percentage):
        """Update progress"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        print(f"[{percentage}%] {message}")
    
    def setup_browser(self):
        """Setup Playwright browser"""
        self.update_progress("Setting up browser...", 5)
        
        try:
            from playwright.sync_api import sync_playwright
            import subprocess
            
            self.playwright = sync_playwright().start()
            
            # Try to launch browser
            try:
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            except:
                # Install browser if missing
                self.update_progress("Installing browser (first time)...", 7)
                subprocess.run(['playwright', 'install', 'chromium'], check=True, capture_output=True)
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            
            self.context = self.browser.new_context(accept_downloads=True)
            self.page = self.context.new_page()
            self.update_progress("Browser ready", 10)
            
        except Exception as e:
            raise Exception(f"Browser setup failed: {str(e)}")
    
    def login(self):
        """Login to RMS2"""
        self.update_progress("Logging in...", 15)
        
        try:
            # Go to login page
            self.page.goto(self.login_url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_timeout(3000)
            
            # Fill email - try different selectors
            try:
                self.page.fill("input[placeholder='Your Email']", self.username, timeout=10000)
            except:
                try:
                    self.page.fill("input[type='email']", self.username, timeout=10000)
                except:
                    self.page.fill("input[name='email']", self.username, timeout=10000)
            
            # Fill password
            try:
                self.page.fill("input[placeholder='Password']", self.password, timeout=10000)
            except:
                self.page.fill("input[type='password']", self.password, timeout=10000)
            
            self.page.wait_for_timeout(1000)
            
            # Click login button - use very specific selector for RMS2 button
            # This ensures we don't click Streamlit's login button
            self.page.click("button.ui.positive.button", timeout=10000)
            # Alternative: wait for the button to be visible and clickable
            # self.page.locator("button.ui.positive.button").click()
            
            # Wait for navigation
            self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            self.page.wait_for_timeout(3000)
            
            self.update_progress("Login successful", 20)
            
        except Exception as e:
            # Save screenshot
            try:
                self.page.screenshot(path=str(self.data_dir / 'login_error.png'))
            except:
                pass
            raise Exception(f"Login failed: {str(e)}")
    
    def download_file(self, period_months, target_filename):
        """Download RCB file"""
        self.update_progress(f"Downloading {period_months}-month data...", 30 if period_months == 24 else 60)
        
        try:
            # Go to RCB page
            self.page.goto(self.rcb_url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_timeout(3000)
            
            # Select period if dropdown exists
            try:
                self.page.select_option("select", str(period_months), timeout=5000)
                self.page.wait_for_timeout(2000)
            except:
                pass  # No dropdown, maybe direct download
            
            # Click download button
            with self.page.expect_download(timeout=60000) as download_info:
                try:
                    self.page.click("button:has-text('Download')", timeout=10000)
                except:
                    try:
                        self.page.click("a:has-text('Download')", timeout=10000)
                    except:
                        self.page.click("button", timeout=10000)  # Click any button as fallback
            
            download = download_info.value
            
            # Save file
            target_path = self.data_dir / target_filename
            download.save_as(target_path)
            
            # Verify
            if not target_path.exists() or target_path.stat().st_size < 1000:
                raise Exception("Download failed or file corrupted")
            
            self.update_progress(f"{period_months}M downloaded", 50 if period_months == 24 else 80)
            return True
            
        except Exception as e:
            try:
                self.page.screenshot(path=str(self.data_dir / f'download_{period_months}m_error.png'))
            except:
                pass
            raise Exception(f"Download failed: {str(e)}")
    
    def cleanup(self):
        """Cleanup"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except:
            pass
    
    def download_both_files(self):
        """Download both files"""
        try:
            self.setup_browser()
            self.login()
            self.download_file(24, 'RCB_24months.xlsx')
            self.download_file(12, 'RCB_12months.xlsx')
            self.update_progress("Complete!", 100)
            return True, "Files downloaded successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
        finally:
            self.cleanup()


def download_rcb_files(data_dir='data', progress_callback=None):
    """Main download function"""
    try:
        downloader = RMS2DataDownloader(data_dir, progress_callback)
        return downloader.download_both_files()
    except Exception as e:
        return False, str(e)
