"""
Download RCB data files from RMS2 using Playwright (Cloud-friendly)
Works on Streamlit Cloud and local environments
"""

import os
import time
from pathlib import Path
from datetime import datetime

# Try to import streamlit for secrets (cloud deployment)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class RMS2DataDownloader:
    """Download RCB data files from RMS2 system using Playwright"""
    
    def __init__(self, data_dir='data', progress_callback=None):
        """Initialize downloader with credentials from .env or Streamlit secrets"""
        # Try Streamlit secrets first (for cloud deployment), then .env file (for local)
        if HAS_STREAMLIT and hasattr(st, 'secrets'):
            try:
                self.username = st.secrets.get('RMS_USERNAME', os.getenv('RMS_USERNAME'))
                self.password = st.secrets.get('RMS_PASSWORD', os.getenv('RMS_PASSWORD'))
                self.login_url = st.secrets.get('RMS_LOGIN_URL', os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com'))
                self.rcb_url = st.secrets.get('RCB_BASE_URL', os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB'))
            except Exception:
                # Fallback to environment variables
                self.username = os.getenv('RMS_USERNAME')
                self.password = os.getenv('RMS_PASSWORD')
                self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
                self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        else:
            # Use environment variables from .env file
            self.username = os.getenv('RMS_USERNAME')
            self.password = os.getenv('RMS_PASSWORD')
            self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
            self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        
        if not self.username or not self.password:
            raise ValueError("RMS_USERNAME and RMS_PASSWORD must be set in Streamlit secrets or .env file")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.download_temp = self.data_dir / 'temp_downloads'
        self.download_temp.mkdir(exist_ok=True)
        
        self.browser = None
        self.page = None
        self.progress_callback = progress_callback
        
    def update_progress(self, message, percentage):
        """Update progress callback"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        print(f"[{percentage}%] {message}")
    
    def setup_browser(self):
        """Configure Playwright browser"""
        self.update_progress("Setting up browser...", 5)
        
        try:
            from playwright.sync_api import sync_playwright
            import subprocess
            
            self.playwright = sync_playwright().start()
            
            # Try to launch, if fails, install browser first
            try:
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            except Exception as launch_error:
                # Browser not installed, install it now
                self.update_progress("Installing browser (first time only)...", 7)
                try:
                    subprocess.run(['playwright', 'install', 'chromium'], check=True, capture_output=True)
                    # Try launching again
                    self.browser = self.playwright.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage']
                    )
                except Exception as install_error:
                    raise Exception(f"Failed to install/launch browser: {str(install_error)}")
            
            # Create context with download path
            self.context = self.browser.new_context(
                accept_downloads=True
            )
            
            self.page = self.context.new_page()
            self.update_progress("Browser ready", 10)
            
        except Exception as e:
            raise Exception(f"Failed to initialize Playwright: {str(e)}. Try restarting the app.")
    
    def login(self):
        """Login to RMS2 system"""
        self.update_progress("Logging in to RMS2...", 15)
        
        try:
            self.page.goto(self.login_url, wait_until='networkidle')
            
            # Wait for email field and enter email
            self.page.fill("input[placeholder='Your Email']", self.username)
            
            # Enter password
            self.page.fill("input[placeholder='Password']", self.password)
            
            # Click login button
            self.page.click("button[type='submit']")
            
            # Wait for navigation
            self.page.wait_for_load_state('networkidle')
            
            self.update_progress("Login successful", 20)
            
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def download_file(self, period_months, target_filename):
        """Download RCB file for specified period"""
        self.update_progress(f"Downloading {period_months}-month data...", 30 if period_months == 24 else 60)
        
        try:
            # Go to RCB page
            self.page.goto(self.rcb_url, wait_until='networkidle')
            time.sleep(2)
            
            # Select the period from dropdown
            self.page.select_option("select[name='period']", str(period_months))
            time.sleep(1)
            
            # Wait for download to trigger
            with self.page.expect_download() as download_info:
                # Click download button
                self.page.click("button:has-text('Download')")
            
            download = download_info.value
            
            # Save to target location
            target_path = self.data_dir / target_filename
            download.save_as(target_path)
            
            self.update_progress(f"{period_months}-month data downloaded", 50 if period_months == 24 else 80)
            
            return True
            
        except Exception as e:
            raise Exception(f"Download failed for {period_months}-month data: {str(e)}")
    
    def cleanup(self):
        """Close browser and cleanup"""
        self.update_progress("Cleaning up...", 90)
        
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def download_both_files(self):
        """Download both 24-month and 12-month files"""
        try:
            self.setup_browser()
            self.login()
            
            # Download 24-month file
            self.download_file(24, 'RCB_24months.xlsx')
            
            # Download 12-month file
            self.download_file(12, 'RCB_12months.xlsx')
            
            self.update_progress("Download complete!", 100)
            
            return True, "Both files downloaded successfully"
            
        except Exception as e:
            return False, f"Download failed: {str(e)}"
        finally:
            self.cleanup()


def download_rcb_files(data_dir='data', progress_callback=None):
    """
    Main function to download RCB files
    
    Args:
        data_dir: Directory to save files
        progress_callback: Optional callback for progress updates
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        downloader = RMS2DataDownloader(data_dir, progress_callback)
        return downloader.download_both_files()
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    # Test the downloader
    print("Starting RMS2 data download...")
    success, message = download_rcb_files()
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
