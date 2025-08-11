#!/usr/bin/env python3
"""
GEICO Browser Controller - Captures screenshots while navigating GEICO quote site
"""

import os
import json
import time
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GEICOBrowserController:
    def __init__(self):
        self.driver = None
        self.screenshots_dir = "geico_screenshots"
        self.current_step = ""
        
        # Create screenshots directory
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    def setup_driver(self):
        """Setup Chrome driver with options for headless screenshot capture"""
        chrome_options = Options()
        
        # Run in headless mode but with screenshot capabilities
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--force-device-scale-factor=1')
        
        # Additional options for better rendering
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Additional anti-detection measures
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--no-default-browser-check')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-default-apps')
        
        # Modify navigator.webdriver flag
        chrome_options.add_argument("--disable-blink-features")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Detect Chrome binary
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
            '/usr/local/bin/chrome'
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                logger.info(f"Found Chrome at: {path}")
                break
        
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_window_size(1920, 1080)
            
            # Execute script to mask webdriver detection
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.navigator.chrome = {
                        runtime: {},
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                '''
            })
            
            logger.info("Chrome driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            # Try without specifying binary location as fallback
            try:
                chrome_options.binary_location = ""
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_window_size(1920, 1080)
                
                # Execute script to mask webdriver detection (same as above)
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        window.navigator.chrome = {
                            runtime: {},
                        };
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en'],
                        });
                    '''
                })
                
                logger.info("Chrome driver initialized successfully (using default binary)")
                return True
            except Exception as e2:
                logger.error(f"Failed to initialize Chrome driver with fallback: {e2}")
                return False
    
    def capture_screenshot(self, step_name):
        """Capture screenshot and save with timestamp"""
        if not self.driver:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{step_name}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            # Take screenshot
            self.driver.save_screenshot(filepath)
            
            # Also get screenshot as base64 for immediate display
            screenshot_base64 = self.driver.get_screenshot_as_base64()
            
            logger.info(f"Screenshot captured: {filename}")
            
            return {
                'filename': filename,
                'filepath': filepath,
                'base64': screenshot_base64,
                'timestamp': timestamp,
                'step': step_name
            }
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    def take_screenshot(self, step_name):
        """Alias for capture_screenshot to maintain compatibility"""
        return self.capture_screenshot(step_name)
    
    def navigate_to_geico(self):
        """Navigate to GEICO quote page"""
        try:
            logger.info("Navigating to GEICO quote page...")
            self.driver.get("https://gateway.geico.com/")
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Capture initial page
            self.capture_screenshot("geico_homepage")
            
            # Try to find and click on auto quote button
            try:
                auto_quote_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/auto/') or contains(text(), 'Auto') or contains(text(), 'Car Insurance')]"))
                )
                auto_quote_button.click()
                time.sleep(2)
                self.capture_screenshot("auto_quote_start")
            except:
                logger.info("Could not find auto quote button, staying on main page")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to GEICO: {e}")
            return False
    
    def fill_zip_code(self, zip_code):
        """Fill in zip code field"""
        try:
            # Look for zip code input field
            zip_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='tel' and (@placeholder='ZIP Code' or @name='zip' or @id='zip')]"))
            )
            
            zip_input.clear()
            zip_input.send_keys(str(zip_code))
            
            self.capture_screenshot("zip_code_entered")
            
            # Try to find and click continue/next button
            try:
                continue_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'Start') or contains(text(), 'Get a Quote')]")
                continue_button.click()
                time.sleep(2)
                self.capture_screenshot("after_zip_submit")
            except:
                logger.info("Could not find continue button after zip code")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill zip code: {e}")
            return False
    
    def fill_usdot(self, usdot_number="111111111"):
        """Fill in USDOT field using proven approach from element_scanner_browser.py"""
        try:
            logger.info(f"Looking for USDOT field to fill with: {usdot_number}")
            
            # Wait a bit for page to load
            time.sleep(2)
            
            usdot_input = None
            
            # Method 1: Look for label containing DOT and find associated input
            logger.info("Looking for DOT label...")
            try:
                labels = self.driver.find_elements(By.TAG_NAME, "label")
                for label in labels:
                    text = label.text.upper()
                    if "DOT" in text or "USDOT" in text or "US DOT" in text:
                        logger.info(f"Found label with text: {label.text}")
                        
                        # Try to find associated input by 'for' attribute
                        label_for = label.get_attribute("for")
                        if label_for:
                            try:
                                usdot_input = self.driver.find_element(By.ID, label_for)
                                logger.info(f"Found field by label 'for' attribute: {label_for}")
                                break
                            except:
                                pass
                        
                        # Try next input after label
                        try:
                            usdot_input = label.find_element(By.XPATH, "following::input[1]")
                            logger.info("Found field as next input after label")
                            break
                        except:
                            pass
                        
                        # Try input within parent
                        try:
                            parent = label.find_element(By.XPATH, "..")
                            usdot_input = parent.find_element(By.TAG_NAME, "input")
                            logger.info("Found field within label parent")
                            break
                        except:
                            pass
            except Exception as e:
                logger.info(f"Label search failed: {e}")
            
            # Method 2: Try common selectors
            if not usdot_input:
                logger.info("Trying common selectors...")
                usdot_selectors = [
                    "//input[@name='dot_number']",
                    "//input[@name='dotNumber']",
                    "//input[@name='usdot']",
                    "//input[@name='USDOT']",
                    "//input[@id='dot_number']",
                    "//input[@id='dotNumber']",
                    "//input[@id='usdot']",
                    "//input[@placeholder[contains(., 'DOT')]]",
                    "//input[@placeholder[contains(., 'USDOT')]]",
                    "//input[@name='usdot' or @id='usdot' or contains(@placeholder, 'USDOT') or contains(@placeholder, 'DOT')]",
                    "//input[@type='text' and (contains(@aria-label, 'USDOT') or contains(@aria-label, 'DOT'))]",
                    "//input[contains(@class, 'usdot')]",
                    "//input[@data-field='usdot']",
                    "//input[@type='number' and (contains(@placeholder, 'DOT') or contains(@aria-label, 'DOT'))]",
                    "//input[contains(@name, 'dot') or contains(@id, 'dot')]"
                ]
                
                for selector in usdot_selectors:
                    try:
                        usdot_input = self.driver.find_element(By.XPATH, selector)
                        logger.info(f"Found USDOT field with selector: {selector}")
                        break
                    except:
                        continue
            
            # Method 3: Use proven fallback - find second text input field
            if not usdot_input:
                logger.info("Using fallback method - looking for second text input")
                text_inputs = self.driver.find_elements(By.XPATH, "//input[@type='text' or @type='number' or not(@type)]")
                visible_inputs = [inp for inp in text_inputs if inp.is_displayed()]
                
                logger.info(f"Found {len(visible_inputs)} visible input fields")
                
                if len(visible_inputs) >= 2:
                    # Assume first is ZIP, second is DOT
                    usdot_input = visible_inputs[1]
                    logger.info("Using second visible input field as DOT field")
                elif len(visible_inputs) == 1:
                    # If only one visible, it might be the DOT field
                    usdot_input = visible_inputs[0]
                    logger.info("Only one visible input, using it as DOT field")
            
            if not usdot_input:
                logger.error("Could not find USDOT input field")
                self.capture_screenshot("no_usdot_field_found")
                return False
            
            # Now fill the field using proven JavaScript approach from element_scanner_browser.py
            logger.info("Field found, attempting to fill...")
            
            # Scroll into view and focus
            self.driver.execute_script("""
                arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                arguments[0].focus();
            """, usdot_input)
            
            time.sleep(0.5)
            
            # Click the field
            try:
                usdot_input.click()
                logger.info("Clicked on field")
            except:
                # Use JavaScript click as fallback
                self.driver.execute_script("arguments[0].click();", usdot_input)
                logger.info("Clicked on field using JavaScript")
            
            time.sleep(0.5)
            
            # Clear and fill using simple JavaScript - proven method from element_scanner_browser.py
            logger.info("Using JavaScript method to enter USDOT...")
            result = self.driver.execute_script("""
                var field = arguments[0];
                var value = arguments[1];
                
                // Clear the field
                field.value = '';
                field.focus();
                
                // Set the value
                field.value = value;
                
                // Trigger events
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
                field.dispatchEvent(new Event('blur', { bubbles: true }));
                
                return field.value;
            """, usdot_input, str(usdot_number))
            
            logger.info(f"JavaScript set value to: {result}")
            
            # Verify the value was set
            time.sleep(0.5)
            current_value = usdot_input.get_attribute("value")
            
            if current_value == str(usdot_number):
                logger.info(f"SUCCESS: Field value confirmed as {current_value}")
                self.capture_screenshot("usdot_filled_success")
                return True
            else:
                # Try one more time with send_keys as absolute fallback
                logger.warning(f"Value mismatch, trying send_keys method. Current: {current_value}, Expected: {usdot_number}")
                try:
                    usdot_input.clear()
                    time.sleep(0.2)
                    usdot_input.send_keys(str(usdot_number))
                    time.sleep(0.5)
                    
                    final_value = usdot_input.get_attribute("value")
                    if final_value == str(usdot_number):
                        logger.info(f"SUCCESS with send_keys: Field value is {final_value}")
                        self.capture_screenshot("usdot_filled_sendkeys_success")
                        return True
                    else:
                        logger.error(f"FAILED: Final value is {final_value}, expected {usdot_number}")
                        self.capture_screenshot("usdot_fill_failed")
                        return False
                except Exception as e:
                    logger.error(f"send_keys fallback failed: {e}")
                    self.capture_screenshot("usdot_fill_error")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to fill USDOT: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_latest_screenshot(self):
        """Get the most recent screenshot data"""
        try:
            screenshots = [f for f in os.listdir(self.screenshots_dir) if f.endswith('.png')]
            if not screenshots:
                return None
                
            latest = max(screenshots, key=lambda f: os.path.getctime(os.path.join(self.screenshots_dir, f)))
            filepath = os.path.join(self.screenshots_dir, latest)
            
            with open(filepath, 'rb') as f:
                image_data = f.read()
                
            return {
                'filename': latest,
                'base64': base64.b64encode(image_data).decode('utf-8')
            }
            
        except Exception as e:
            logger.error(f"Failed to get latest screenshot: {e}")
            return None
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def test_browser_controller():
    """Test the browser controller with mock data"""
    controller = GEICOBrowserController()
    
    # Load mock data
    with open('truck_quote_example.json', 'r') as f:
        mock_data = json.load(f)
    
    try:
        # Setup driver
        if not controller.setup_driver():
            logger.error("Failed to setup driver")
            return
        
        # Navigate to GEICO
        if controller.navigate_to_geico():
            logger.info("Successfully navigated to GEICO")
            
            # Try to fill zip code
            zip_code = mock_data.get('driver_info', {}).get('address', {}).get('zip', '30301')
            controller.fill_zip_code(zip_code)
            
            # Give time for any redirects
            time.sleep(3)
            
            # Fill USDOT field with DOT number from mock data
            dot_number = mock_data.get('driver_info', {}).get('dot_number', '3431557')
            logger.info(f"Filling USDOT field with DOT number: {dot_number}")
            controller.fill_usdot(dot_number)
            
            # Give time for the field to be filled
            time.sleep(2)
            
            # Take final screenshot
            controller.capture_screenshot("final_state")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
    
    finally:
        controller.cleanup()


if __name__ == "__main__":
    test_browser_controller()