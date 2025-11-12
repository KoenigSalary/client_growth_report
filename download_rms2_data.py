"""
Download RCB data files from RMS2 using Selenium
Based on the working client_growth_report_FINAL.py script
"""

import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

class RMS2DataDownloader:
    """Download RCB data files from RMS2 system"""
    
    def __init__(self, data_dir='data', progress_callback=None):
        """Initialize downloader with credentials from .env"""
        self.username = os.getenv('RMS_USERNAME')
        self.password = os.getenv('RMS_PASSWORD')
        self.login_url = os.getenv('RMS_LOGIN_URL', 'https://rms2.koenig-solutions.com')
        self.rcb_url = os.getenv('RCB_BASE_URL', 'https://rms2.koenig-solutions.com/RCB')
        
        if not self.username or not self.password:
            raise ValueError("RMS_USERNAME and RMS_PASSWORD must be set in .env file")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.download_temp = self.data_dir / 'temp_downloads'
        self.download_temp.mkdir(exist_ok=True)
        
        self.driver = None
        self.progress_callback = progress_callback
        
    def update_progress(self, message, percentage):
        """Update progress callback"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        print(f"[{percentage}%] {message}")
    
    def setup_driver(self):
        """Configure Chrome WebDriver with download preferences"""
        self.update_progress("Setting up browser...", 5)
        
        chrome_options = Options()
        
        # Download preferences
        prefs = {
            "download.default_directory": str(self.download_temp.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Headless mode for server deployment
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.maximize_window()
            self.update_progress("Browser ready", 10)
        except Exception as e:
            raise Exception(f"Failed to initialize Chrome WebDriver: {str(e)}. Make sure Chrome and ChromeDriver are installed.")
    
    def login(self):
        """Login to RMS2 system"""
        self.update_progress("Logging in to RMS2...", 15)
        
        try:
            self.driver.get(self.login_url)
            wait = WebDriverWait(self.driver, 30)
            
            time.sleep(3)
            
            # Enter email
            email_field = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Your Email']"))
            )
            email_field.clear()
            email_field.send_keys(self.username)
            
            # Enter password
            password_field = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Password']"))
            )
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
            )
            login_button.click()
            
            time.sleep(5)
            self.update_progress("Login successful", 25)
            
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def navigate_to_rcb(self):
        """Navigate to RCB page"""
        self.update_progress("Opening RCB page...", 30)
        self.driver.get(self.rcb_url)
        time.sleep(5)
    
    def export_data(self, months):
        """Export data for specified number of months
        
        Args:
            months: Number of months (12 or 24)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        self.update_progress(f"Exporting {months}-month data...", 35 if months == 24 else 55)
        
        wait = WebDriverWait(self.driver, 30)
        
        try:
            # Find and clear month input field
            try:
                month_input = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='12']"))
                )
            except:
                month_input = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='text' and contains(@class, 'MuiInputBase-input')]"))
                )
            
            month_input.clear()
            time.sleep(0.5)
            month_input.send_keys(str(months))
            time.sleep(1)
            
            # Click Display button
            display_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'ui mini button') and contains(., 'Display')]"))
            )
            display_button.click()
            time.sleep(10)
            
            # Click Export to Excel button
            export_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'ui mini button') and contains(., 'Export to excel')]"))
            )
            
            # Track files before download
            files_before = set(os.listdir(self.download_temp))
            
            export_button.click()
            self.update_progress(f"Downloading {months}-month file...", 40 if months == 24 else 60)
            
            # Wait for download to complete
            downloaded_file = None
            for i in range(60):
                time.sleep(1)
                files_after = set(os.listdir(self.download_temp))
                new_files = files_after - files_before
                
                if new_files:
                    for new_file in new_files:
                        if not new_file.endswith(('.crdownload', '.tmp')):
                            file_path = self.download_temp / new_file
                            if file_path.exists():
                                time.sleep(2)  # Wait for file to finish writing
                                
                                # Rename to standard name
                                target_name = f"RCB_{months}months.xlsx"
                                target_path = self.data_dir / target_name
                                
                                # Remove old file if exists
                                if target_path.exists():
                                    target_path.unlink()
                                
                                # Move to data directory
                                file_path.rename(target_path)
                                downloaded_file = target_path
                                break
                
                if downloaded_file:
                    break
                    
                if i % 10 == 0 and i > 0:
                    self.update_progress(f"Still waiting for {months}-month download... ({i}/60s)", 
                                       42 + i//10 if months == 24 else 62 + i//10)
            
            if downloaded_file:
                file_size = downloaded_file.stat().st_size / (1024 * 1024)
                self.update_progress(f"{months}-month file downloaded ({file_size:.1f}MB)", 
                                   50 if months == 24 else 70)
                return downloaded_file
            else:
                raise Exception(f"Download timeout for {months}-month file")
                
        except Exception as e:
            raise Exception(f"Failed to export {months}-month data: {str(e)}")
    
    def download_all(self):
        """Main method to download both files
        
        Returns:
            tuple: (success: bool, message: str, files: dict)
        """
        try:
            self.setup_driver()
            self.login()
            self.navigate_to_rcb()
            
            # Download 24-month file
            file_24 = self.export_data(24)
            if not file_24:
                raise Exception("Failed to download 24-month file")
            
            time.sleep(3)
            
            # Download 12-month file
            file_12 = self.export_data(12)
            if not file_12:
                raise Exception("Failed to download 12-month file")
            
            self.update_progress("All files downloaded successfully!", 80)
            
            files = {
                '24_months': str(file_24),
                '12_months': str(file_12)
            }
            
            return True, "Successfully downloaded both RCB files", files
            
        except Exception as e:
            return False, f"Download failed: {str(e)}", {}
            
        finally:
            if self.driver:
                self.update_progress("Closing browser...", 90)
                self.driver.quit()
                self.update_progress("Download complete", 100)
            
            # Clean up temp directory
            if self.download_temp.exists():
                for file in self.download_temp.iterdir():
                    try:
                        file.unlink()
                    except:
                        pass


def download_rcb_files(data_dir='data', progress_callback=None):
    """
    Convenience function to download RCB files
    
    Args:
        data_dir: Directory to save files
        progress_callback: Function to call with progress updates (message, percentage)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    downloader = RMS2DataDownloader(data_dir, progress_callback)
    success, message, files = downloader.download_all()
    return success, message


if __name__ == '__main__':
    """Test the download function"""
    print("Testing RMS2 data download with Selenium...")
    print(f"Username: {os.getenv('RMS_USERNAME')}")
    print(f"Login URL: {os.getenv('RMS_LOGIN_URL')}")
    print("-" * 60)
    
    success, message = download_rcb_files()
    
    if success:
        print(f"\n✅ SUCCESS: {message}")
    else:
        print(f"\n❌ FAILURE: {message}")
