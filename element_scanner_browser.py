#!/usr/bin/env python3
"""
Element Scanner Browser Controller - Opens Chrome and highlights form elements with red overlays
"""

import os
import time
import base64
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import logging
import subprocess

# Try to import pyautogui for fallback typing
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElementScannerBrowser:
    def __init__(self):
        self.driver = None
        self.screenshots_dir = "scanner_screenshots"
        self.user_data_dir = None
        self.current_url = None
        self.monitoring_active = False
        
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    def setup_driver(self, headless=True):
        """Setup Chrome driver with proper path detection - default to headless to avoid conflicts"""
        chrome_options = Options()
        
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
        
        # Add basic options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Always use headless mode to avoid user-data-dir conflicts
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--force-device-scale-factor=1')
        
        # Additional options for better rendering
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_window_size(1920, 1080)
            logger.info("Chrome driver initialized successfully in headless mode")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            # Try without specifying binary location as fallback
            try:
                chrome_options.binary_location = ""
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_window_size(1920, 1080)
                logger.info("Chrome driver initialized successfully (using default binary)")
                return True
            except Exception as e2:
                logger.error(f"Failed to initialize Chrome driver with fallback: {e2}")
                return False
    
    def _old_setup_driver_chrome_detection(self):
        """Old Chrome detection code - kept for reference"""
        # Check if Chrome is available
        chrome_bin = None
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable', 
            'google-chrome-stable', 
            'google-chrome', 
            'chromium-browser', 
            'chromium',
            '/opt/google/chrome/google-chrome'
        ]
        
        for path in chrome_paths:
            try:
                # First check if the file exists
                if not os.path.isabs(path):
                    # For non-absolute paths, try to find it in PATH
                    full_path = shutil.which(path)
                    if full_path:
                        path = full_path
                    else:
                        logger.info(f"Path {path} not found in PATH")
                        continue
                
                if not os.path.exists(path):
                    logger.info(f"Path does not exist: {path}")
                    continue
                
                # Check if it's executable
                if not os.access(path, os.X_OK):
                    logger.info(f"Path is not executable: {path}")
                    continue
                
                logger.info(f"Checking Chrome version at: {path}")
                # Add timeout and environment to avoid hanging
                result = subprocess.run([path, '--version'], 
                                     capture_output=True, 
                                     text=True,
                                     timeout=5,
                                     env=os.environ.copy())
                if result.returncode == 0:
                    chrome_bin = path
                    logger.info(f"Found Chrome at: {chrome_bin} - {result.stdout.strip()}")
                    break
                else:
                    logger.info(f"Failed to run {path}: return code {result.returncode}, stderr: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout checking {path} - might be hanging")
                continue
            except Exception as e:
                logger.warning(f"Exception checking {path}: {type(e).__name__}: {e}")
                continue
        
        if not chrome_bin:
            logger.error("Chrome browser not found in any expected location")
            return False
        
        chrome_options = Options()
        chrome_options.binary_location = chrome_bin
        logger.info(f"Using Chrome binary: {chrome_bin}")
        # This is just reference code - not used in the simple setup_driver method
    
    def inject_element_scanner(self):
        """Inject JavaScript to highlight form elements with red overlays and labels"""
        scanner_script = """
        // Remove any existing overlays
        document.querySelectorAll('.element-scanner-overlay').forEach(el => el.remove());
        
        // Create style for overlays if not already exists
        if (!document.getElementById('element-scanner-styles')) {
            const style = document.createElement('style');
            style.id = 'element-scanner-styles';
            style.textContent = `
                .element-scanner-overlay {
                    position: absolute;
                    border: 3px solid red;
                    background-color: rgba(255, 0, 0, 0.1);
                    pointer-events: none;
                    z-index: 9999;
                    box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
                }
                .element-scanner-label {
                    position: absolute;
                    background-color: red;
                    color: white;
                    padding: 2px 8px;
                    font-size: 12px;
                    font-weight: bold;
                    font-family: Arial, sans-serif;
                    top: -25px;
                    left: 0;
                    white-space: nowrap;
                    z-index: 10000;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Find ALL clickable elements - comprehensive selector
        const formElements = document.querySelectorAll(`
            input, textarea, select, button, a, 
            [role="button"], [role="link"], [role="tab"], [role="menuitem"],
            [onclick], [ng-click], [data-click], [data-action],
            [href], [type="submit"], [type="button"], [type="reset"],
            .btn, .button, .link, .clickable,
            *[tabindex]:not([tabindex="-1"]),
            label[for], summary, 
            div[contenteditable="true"], span[contenteditable="true"],
            [data-testid*="button"], [data-testid*="link"],
            [class*="btn"], [class*="button"], [class*="link"],
            [id*="btn"], [id*="button"], [id*="link"],
            img[onclick], img[style*="cursor: pointer"],
            li[onclick], div[onclick], span[onclick], p[onclick],
            td[onclick], tr[onclick],
            [style*="cursor: pointer"]
        `);
        
        // Remove duplicates and filter out non-visible elements
        const processedElements = new Set();
        const visibleElements = Array.from(formElements).filter(element => {
            // Skip if already processed
            if (processedElements.has(element)) return false;
            processedElements.add(element);
            
            // Skip hidden elements
            if (!element.offsetParent) return false;
            
            // Skip elements with no size
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return false;
            
            // Skip elements outside viewport (too far)
            if (rect.bottom < -1000 || rect.top > window.innerHeight + 1000) return false;
            
            return true;
        });
        
        // Get current zoom level
        const zoomLevel = parseFloat(getComputedStyle(document.body).zoom || 1);
        console.log('Current zoom level:', zoomLevel);
        
        visibleElements.forEach((element, index) => {
            
            // Get element position and size
            const rect = element.getBoundingClientRect();
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
            
            // Create overlay div
            const overlay = document.createElement('div');
            overlay.className = 'element-scanner-overlay';
            
            // Apply zoom correction to positions
            // When zoom is applied, getBoundingClientRect returns the visual position
            // but we need to set the actual position which needs to be divided by zoom
            overlay.style.top = ((rect.top + scrollTop) / zoomLevel) + 'px';
            overlay.style.left = ((rect.left + scrollLeft) / zoomLevel) + 'px';
            overlay.style.width = (rect.width / zoomLevel) + 'px';
            overlay.style.height = (rect.height / zoomLevel) + 'px';
            
            // Create label
            const label = document.createElement('div');
            label.className = 'element-scanner-label';
            
            // Generate comprehensive label text
            let labelText = element.tagName.toLowerCase();
            
            // Add type for form elements
            if (element.type) labelText += `[${element.type}]`;
            
            // Try to get meaningful identifier
            if (element.name) {
                labelText += `: ${element.name}`;
            } else if (element.id) {
                labelText += `: #${element.id}`;
            } else if (element.getAttribute('aria-label')) {
                labelText += `: ${element.getAttribute('aria-label')}`;
            } else if (element.getAttribute('data-testid')) {
                labelText += `: ${element.getAttribute('data-testid')}`;
            } else if (element.className && typeof element.className === 'string') {
                const firstClass = element.className.split(' ')[0];
                if (firstClass) labelText += `: .${firstClass}`;
            }
            
            // Add text content for buttons and links
            const textContent = element.textContent?.trim();
            if ((element.tagName === 'BUTTON' || element.tagName === 'A' || element.getAttribute('role') === 'button') && textContent && textContent.length < 30) {
                labelText += ` "${textContent}"`;
            }
            
            // Add placeholder for inputs
            if (element.placeholder) labelText += ` (${element.placeholder})`;
            
            // Add href preview for links
            if (element.href && element.tagName === 'A') {
                const hrefPreview = element.href.split('/').pop() || element.href;
                if (hrefPreview.length < 20) labelText += ` [${hrefPreview}]`;
            }
            
            label.textContent = labelText;
            overlay.appendChild(label);
            
            // Add overlay to page
            document.body.appendChild(overlay);
        });
        
        // Return count of visible elements highlighted
        return visibleElements.length;
        """
        
        try:
            count = self.driver.execute_script(scanner_script)
            logger.info(f"Highlighted {count} form elements")
            return count
        except Exception as e:
            logger.error(f"Failed to inject scanner script: {e}")
            return 0
    
    def monitor_page_changes(self):
        """Monitor for page changes and re-inject scanner when needed"""
        try:
            current_url = self.driver.current_url
            if current_url != self.current_url:
                logger.info(f"Page changed from {self.current_url} to {current_url}")
                self.current_url = current_url
                time.sleep(1)  # Brief wait for page to stabilize
                self.inject_element_scanner()
                return True
            return False
        except Exception as e:
            logger.error(f"Error monitoring page changes: {e}")
            return False
    
    def scan_page(self, url):
        """Navigate to URL and scan for form elements"""
        try:
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            self.current_url = url
            
            # Wait for page to load
            time.sleep(3)
            
            # Inject scanner
            element_count = self.inject_element_scanner()
            
            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            self.driver.save_screenshot(filepath)
            screenshot_base64 = self.driver.get_screenshot_as_base64()
            
            return {
                'success': True,
                'element_count': element_count,
                'screenshot': {
                    'filename': filename,
                    'base64': screenshot_base64
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to scan page: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_and_click_element(self, selectors):
        """Find and click an element using multiple selector strategies"""
        # First try to find using the scanned labels
        try:
            script = """
            // Get current zoom level
            const zoomLevel = parseFloat(getComputedStyle(document.body).zoom || 1);
            const labels = document.querySelectorAll('.element-scanner-label');
            for (let label of labels) {
                const labelText = label.textContent.toLowerCase();
                if (labelText.includes('input[text]') || 
                    labelText.includes('input[email]') ||
                    labelText.includes('#username') ||
                    labelText.includes(': username') ||
                    labelText.includes('email') ||
                    labelText.includes('user id') ||
                    labelText.includes('user name') ||
                    labelText.includes('login')) {
                    // Get the parent overlay
                    const overlay = label.parentElement;
                    // Find the actual input element at this position
                    const rect = overlay.getBoundingClientRect();
                    // Account for zoom when using elementFromPoint
                    const x = rect.left + rect.width/2;
                    const y = rect.top + rect.height/2;
                    const element = document.elementFromPoint(x, y);
                    if (element && (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA')) {
                        element.scrollIntoView(true);
                        element.click();
                        element.focus();
                        console.log('Clicked username field via label:', labelText);
                        return true;
                    }
                }
            }
            return false;
            """
            if self.driver.execute_script(script):
                logger.info("Clicked element using scanned label")
                return True
        except Exception as e:
            logger.debug(f"Failed to click using labels: {e}")
        
        # Fallback to original selector methods
        for selector_type, selector_value in selectors:
            try:
                if selector_type == "id":
                    element = self.driver.find_element(By.ID, selector_value)
                elif selector_type == "name":
                    element = self.driver.find_element(By.NAME, selector_value)
                elif selector_type == "xpath":
                    element = self.driver.find_element(By.XPATH, selector_value)
                elif selector_type == "css":
                    element = self.driver.find_element(By.CSS_SELECTOR, selector_value)
                elif selector_type == "placeholder":
                    element = self.driver.find_element(By.XPATH, f"//input[@placeholder='{selector_value}']")
                
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Click the element
                element.click()
                logger.info(f"Clicked element with {selector_type}='{selector_value}'")
                return True
            except Exception as e:
                logger.debug(f"Failed to find element with {selector_type}='{selector_value}': {e}")
                continue
        
        logger.error(f"Could not find element with any of the provided selectors")
        return False
    
    def click_password_field(self):
        """Special method to click password field using labels"""
        try:
            script = """
            // Get current zoom level
            const zoomLevel = parseFloat(getComputedStyle(document.body).zoom || 1);
            const labels = document.querySelectorAll('.element-scanner-label');
            for (let label of labels) {
                const labelText = label.textContent.toLowerCase();
                if (labelText.includes('password') || labelText.includes('input[password]')) {
                    // Get the parent overlay
                    const overlay = label.parentElement;
                    // Find the actual input element at this position
                    const rect = overlay.getBoundingClientRect();
                    const x = rect.left + rect.width/2;
                    const y = rect.top + rect.height/2;
                    const element = document.elementFromPoint(x, y);
                    if (element && element.tagName === 'INPUT') {
                        element.scrollIntoView(true);
                        element.click();
                        element.focus();
                        console.log('Clicked password field via label:', labelText);
                        return true;
                    }
                }
            }
            // Fallback: try direct password field selector
            const passwordField = document.querySelector('input[type="password"]');
            if (passwordField) {
                passwordField.scrollIntoView(true);
                passwordField.click();
                passwordField.focus();
                return true;
            }
            return false;
            """
            if self.driver.execute_script(script):
                logger.info("Clicked password field")
                return True
            else:
                logger.error("Could not find password field")
                return False
        except Exception as e:
            logger.error(f"Failed to click password field: {e}")
            return False
    
    def click_login_button(self):
        """Special method to click login/sign in button using labels"""
        try:
            script = """
            // Get current zoom level
            const zoomLevel = parseFloat(getComputedStyle(document.body).zoom || 1);
            const labels = document.querySelectorAll('.element-scanner-label');
            for (let label of labels) {
                const labelText = label.textContent.toLowerCase();
                // Check for various login button patterns
                if (labelText.includes('"log in"') || 
                    labelText.includes('"login"') ||
                    labelText.includes('"sign in"') ||
                    labelText.includes('"signin"') ||
                    labelText.includes('button') && (labelText.includes('log') || labelText.includes('sign')) ||
                    labelText.includes('submit') ||
                    labelText.includes('[submit]')) {
                    // Get the parent overlay
                    const overlay = label.parentElement;
                    // Find the actual button element at this position
                    const rect = overlay.getBoundingClientRect();
                    const x = rect.left + rect.width/2;
                    const y = rect.top + rect.height/2;
                    const element = document.elementFromPoint(x, y);
                    if (element && (element.tagName === 'BUTTON' || element.tagName === 'INPUT' || element.getAttribute('role') === 'button')) {
                        element.scrollIntoView(true);
                        element.click();
                        console.log('Clicked login button via label:', labelText);
                        return true;
                    }
                }
            }
            
            // Fallback: try various selectors for login button
            const selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:contains("Log In")',
                'button:contains("Sign In")',
                'button:contains("Login")',
                '[role="button"]:contains("Log")',
                '[role="button"]:contains("Sign")'
            ];
            
            for (let selector of selectors) {
                try {
                    let elements;
                    if (selector.includes(':contains')) {
                        // Handle :contains selector manually
                        const [tag, text] = selector.split(':contains');
                        const searchText = text.replace(/[()'"]/g, '').toLowerCase();
                        elements = Array.from(document.querySelectorAll(tag)).filter(el => 
                            el.textContent.toLowerCase().includes(searchText)
                        );
                    } else {
                        elements = document.querySelectorAll(selector);
                    }
                    
                    for (let element of elements) {
                        if (element && element.offsetParent !== null) { // Check if visible
                            element.scrollIntoView(true);
                            element.click();
                            console.log('Clicked login button with selector:', selector);
                            return true;
                        }
                    }
                } catch (e) {
                    console.log('Error with selector:', selector, e);
                }
            }
            
            return false;
            """
            if self.driver.execute_script(script):
                logger.info("Clicked login button")
                return True
            else:
                logger.error("Could not find login button")
                return False
        except Exception as e:
            logger.error(f"Failed to click login button: {e}")
            return False
    
    def enter_zip_code(self, zip_code="44256"):
        """Enter ZIP code in the ZIP code field"""
        try:
            script = f"""
            // Get current zoom level
            const zoomLevel = parseFloat(getComputedStyle(document.body).zoom || 1);
            // First try to find using scanned labels
            const labels = document.querySelectorAll('.element-scanner-label');
            for (let label of labels) {{
                const labelText = label.textContent.toLowerCase();
                // Check for ZIP code field patterns
                if (labelText.includes('zip') || 
                    labelText.includes('postal') ||
                    labelText.includes('zipcode') ||
                    labelText.includes('zip code') ||
                    labelText.includes('input[text]') && label.textContent.includes('ZIP') ||
                    labelText.includes('input[number]') && label.textContent.includes('ZIP')) {{
                    // Get the parent overlay
                    const overlay = label.parentElement;
                    // Find the actual input element at this position
                    const rect = overlay.getBoundingClientRect();
                    const x = rect.left + rect.width/2;
                    const y = rect.top + rect.height/2;
                    const element = document.elementFromPoint(x, y);
                    if (element && (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA')) {{
                        element.scrollIntoView(true);
                        element.click();
                        element.focus();
                        // Clear any existing value
                        element.value = '';
                        // Type the ZIP code
                        element.value = '{zip_code}';
                        // Trigger input and change events
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('Entered ZIP code via label:', labelText);
                        return true;
                    }}
                }}
            }}
            
            // Fallback: try various selectors for ZIP code field
            const selectors = [
                'input[name*="zip"]',
                'input[id*="zip"]',
                'input[placeholder*="ZIP"]',
                'input[placeholder*="Zip"]',
                'input[aria-label*="ZIP"]',
                'input[type="text"][maxlength="5"]',
                'input[type="number"][maxlength="5"]',
                'input[data-testid*="zip"]',
                '[class*="zip"] input',
                '[id*="postal"] input'
            ];
            
            for (let selector of selectors) {{
                try {{
                    const elements = document.querySelectorAll(selector);
                    for (let element of elements) {{
                        if (element && element.offsetParent !== null) {{ // Check if visible
                            element.scrollIntoView(true);
                            element.click();
                            element.focus();
                            // Clear and enter ZIP
                            element.value = '';
                            element.value = '{zip_code}';
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            console.log('Entered ZIP code with selector:', selector);
                            return true;
                        }}
                    }}
                }} catch (e) {{
                    console.log('Error with selector:', selector, e);
                }}
            }}
            
            return false;
            """
            if self.driver.execute_script(script):
                logger.info(f"Successfully entered ZIP code: {zip_code}")
                return True
            else:
                logger.error("Could not find ZIP code field")
                return False
        except Exception as e:
            logger.error(f"Failed to enter ZIP code: {e}")
            return False
    
    def enter_dot_number(self, dot_number="3431557"):
        """Enter DOT number in the DOT field"""
        try:
            logger.info(f"Attempting to enter DOT number: {dot_number}")
            
            # Import the helper script
            try:
                from geico_dot_helper import get_geico_dot_entry_script, get_force_type_script
                
                # First try the targeted GEICO approach
                logger.info("Trying GEICO-specific DOT entry method...")
                result = self.driver.execute_script(get_geico_dot_entry_script(dot_number))
                
                if result and result.get('success'):
                    logger.info(f"Successfully entered DOT number using GEICO method: {result.get('value')}")
                    logger.info(f"Field info: {result.get('fieldInfo')}")
                    return True
                else:
                    logger.warning(f"GEICO method failed: {result}")
                    
                    # Try the force type method
                    logger.info("Trying force type method...")
                    force_result = self.driver.execute_script(get_force_type_script(dot_number))
                    
                    if force_result and force_result.get('success'):
                        logger.info(f"Successfully entered DOT number using force type: {force_result.get('value')}")
                        return True
            except ImportError:
                logger.warning("Could not import geico_dot_helper, using fallback method")
            
            # Continue with original JavaScript approach as fallback
            logger.info("Using standard JavaScript method...")
            script = f"""
            console.log('Starting DOT number entry script...');
            
            // Helper function to simulate real typing
            function simulateTyping(element, text) {{
                element.focus();
                element.click();
                
                // Clear the field first
                element.value = '';
                
                // Type each character with proper events
                for (let i = 0; i < text.length; i++) {{
                    const char = text[i];
                    element.value += char;
                    
                    // Dispatch keyboard events
                    element.dispatchEvent(new KeyboardEvent('keydown', {{
                        key: char,
                        code: 'Digit' + char,
                        which: char.charCodeAt(0),
                        keyCode: char.charCodeAt(0),
                        bubbles: true
                    }}));
                    
                    element.dispatchEvent(new KeyboardEvent('keypress', {{
                        key: char,
                        code: 'Digit' + char,
                        which: char.charCodeAt(0),
                        keyCode: char.charCodeAt(0),
                        bubbles: true
                    }}));
                    
                    element.dispatchEvent(new InputEvent('input', {{
                        data: char,
                        inputType: 'insertText',
                        bubbles: true
                    }}));
                    
                    element.dispatchEvent(new KeyboardEvent('keyup', {{
                        key: char,
                        code: 'Digit' + char,
                        which: char.charCodeAt(0),
                        keyCode: char.charCodeAt(0),
                        bubbles: true
                    }}));
                }}
                
                // Final change event
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                element.blur();
                element.focus();
            }}
            
            // Find DOT field using multiple strategies
            let dotField = null;
            
            // Strategy 1: Look for field with DOT-related attributes
            const dotSelectors = [
                'input[name*="dot" i]',
                'input[id*="dot" i]',
                'input[placeholder*="dot" i]',
                'input[placeholder*="USDOT" i]',
                'input[placeholder*="US DOT" i]',
                'input[aria-label*="dot" i]',
                'input[data-testid*="dot" i]'
            ];
            
            for (let selector of dotSelectors) {{
                const elements = document.querySelectorAll(selector);
                for (let element of elements) {{
                    if (element.offsetParent !== null && 
                        (element.type === 'text' || element.type === 'number' || !element.type)) {{
                        dotField = element;
                        console.log('Found DOT field with selector:', selector);
                        break;
                    }}
                }}
                if (dotField) break;
            }}
            
            // Strategy 2: If not found, look for the second visible text input
            if (!dotField) {{
                const visibleInputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])'))
                    .filter(el => {{
                        if (!el.offsetParent) return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && rect.top >= 0;
                    }});
                
                console.log('Found', visibleInputs.length, 'visible input fields');
                
                // Usually ZIP is first, DOT is second
                if (visibleInputs.length >= 2) {{
                    dotField = visibleInputs[1];
                    console.log('Using second visible input as DOT field');
                }}
            }}
            
            // Strategy 3: Look for any empty text field that's not ZIP
            if (!dotField) {{
                const emptyFields = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])'))
                    .filter(el => {{
                        if (!el.offsetParent) return false;
                        const text = (el.placeholder + el.name + el.id + (el.getAttribute('aria-label') || '')).toLowerCase();
                        return !text.includes('zip') && !text.includes('postal') && el.value === '';
                    }});
                
                if (emptyFields.length > 0) {{
                    dotField = emptyFields[0];
                    console.log('Found empty non-ZIP field for DOT');
                }}
            }}
            
            if (dotField) {{
                console.log('DOT field found, attempting to enter value...');
                dotField.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                
                // Try simple value setting first
                dotField.focus();
                dotField.click();
                dotField.value = '{dot_number}';
                dotField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                dotField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                // Verify the value was set
                if (dotField.value !== '{dot_number}') {{
                    console.log('Simple value setting failed, trying simulated typing...');
                    simulateTyping(dotField, '{dot_number}');
                }}
                
                console.log('DOT number entry complete. Field value:', dotField.value);
                return dotField.value === '{dot_number}';
            }}
            
            console.error('Could not find DOT field');
            return false;
            """
            
            js_result = self.driver.execute_script(script)
            
            if js_result:
                logger.info(f"Successfully entered DOT number via JavaScript: {dot_number}")
                return True
            else:
                logger.warning("JavaScript method failed, trying Selenium approach...")
                
                # Fallback: Try using Selenium WebDriver methods
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Try to find DOT field using Selenium
                dot_selectors = [
                    (By.XPATH, "//input[contains(@name, 'dot') or contains(@id, 'dot') or contains(@placeholder, 'DOT')]"),
                    (By.XPATH, "//input[@type='text' or @type='number'][position()=2]"),  # Second input field
                    (By.XPATH, "//input[@type='text' and @value='']")  # Any empty text field
                ]
                
                for by_type, selector in dot_selectors:
                    try:
                        elements = self.driver.find_elements(by_type, selector)
                        for element in elements:
                            if element.is_displayed():
                                # Check if it's not the ZIP field
                                elem_text = (element.get_attribute('placeholder') or '') + \
                                          (element.get_attribute('name') or '') + \
                                          (element.get_attribute('id') or '')
                                
                                if 'zip' not in elem_text.lower():
                                    logger.info(f"Found potential DOT field with Selenium: {selector}")
                                    
                                    # Scroll to element
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    time.sleep(0.5)
                                    
                                    # Try multiple methods to enter the value
                                    try:
                                        # Method 1: Direct click and type
                                        element.click()
                                        element.clear()
                                        element.send_keys(dot_number)
                                        logger.info("Entered DOT via direct send_keys")
                                        return True
                                    except:
                                        try:
                                            # Method 2: ActionChains
                                            actions = ActionChains(self.driver)
                                            actions.move_to_element(element)
                                            actions.click()
                                            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                                            actions.send_keys(Keys.DELETE)
                                            actions.send_keys(dot_number)
                                            actions.perform()
                                            logger.info("Entered DOT via ActionChains")
                                            return True
                                        except:
                                            pass
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {e}")
                        continue
                
                # Last resort: Try pyautogui if available and not headless
                if PYAUTOGUI_AVAILABLE and hasattr(self.driver, 'get_window_rect'):
                    try:
                        logger.warning("Trying PyAutoGUI as last resort...")
                        
                        # Get window position
                        window_rect = self.driver.get_window_rect()
                        
                        # Find the DOT field position using JavaScript
                        field_pos_script = """
                        // Find second visible text input (assuming first is ZIP)
                        const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])'))
                            .filter(el => el.offsetParent !== null);
                        
                        if (inputs.length >= 2) {
                            const dotField = inputs[1];
                            const rect = dotField.getBoundingClientRect();
                            dotField.style.border = '5px solid red';  // Highlight it
                            return {
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2
                            };
                        }
                        return null;
                        """
                        
                        field_pos = self.driver.execute_script(field_pos_script)
                        
                        if field_pos:
                            # Calculate absolute screen position
                            abs_x = window_rect['x'] + field_pos['x']
                            abs_y = window_rect['y'] + field_pos['y']
                            
                            logger.info(f"Clicking at position: {abs_x}, {abs_y}")
                            
                            # Click on the field
                            pyautogui.click(abs_x, abs_y)
                            time.sleep(0.5)
                            
                            # Triple-click to select all (in case there's existing text)
                            pyautogui.tripleClick()
                            time.sleep(0.2)
                            
                            # Type the DOT number
                            pyautogui.typewrite(dot_number, interval=0.1)
                            
                            logger.info("Entered DOT via PyAutoGUI")
                            return True
                    except Exception as e:
                        logger.error(f"PyAutoGUI method failed: {e}")
                
                logger.error("Could not find or enter DOT number with any method")
                
                # Log current page state for debugging
                try:
                    page_info_script = """
                    const inputs = document.querySelectorAll('input');
                    const info = [];
                    inputs.forEach((input, i) => {
                        if (input.offsetParent) {
                            info.push({
                                index: i,
                                type: input.type,
                                name: input.name,
                                id: input.id, 
                                placeholder: input.placeholder,
                                value: input.value,
                                className: input.className
                            });
                        }
                    });
                    return info;
                    """
                    
                    page_info = self.driver.execute_script(page_info_script)
                    logger.error(f"Current page inputs: {page_info}")
                except:
                    pass
                    
                return False
                
        except Exception as e:
            logger.error(f"Failed to enter DOT number: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def click_commercial_auto_button(self):
        """Special method to click Commercial Auto / Trucking button using labels"""
        try:
            script = """
            // Get current zoom level
            const zoomLevel = parseFloat(getComputedStyle(document.body).zoom || 1);
            // First try to find using scanned labels
            const labels = document.querySelectorAll('.element-scanner-label');
            for (let label of labels) {
                const labelText = label.textContent.toLowerCase();
                // Check for commercial auto / trucking patterns
                if (labelText.includes('commercial auto') || 
                    labelText.includes('trucking') ||
                    labelText.includes('commercial') && labelText.includes('auto') ||
                    labelText.includes('commercial vehicle') ||
                    labelText.includes('truck')) {
                    // Get the parent overlay
                    const overlay = label.parentElement;
                    // Find the actual element at this position
                    const rect = overlay.getBoundingClientRect();
                    const x = rect.left + rect.width/2;
                    const y = rect.top + rect.height/2;
                    const element = document.elementFromPoint(x, y);
                    if (element) {
                        element.scrollIntoView(true);
                        element.click();
                        console.log('Clicked Commercial Auto button via label:', labelText);
                        return true;
                    }
                }
            }
            
            // Fallback: try various selectors for Commercial Auto button
            const selectors = [
                // Text content selectors
                '*:contains("Commercial Auto")',
                '*:contains("Commercial Autos")',
                '*:contains("Trucking")',
                '*:contains("Commercial Autos / Trucking")',
                '*:contains("Commercial Vehicle")',
                // Specific element types
                'button:contains("Commercial")',
                'a:contains("Commercial")',
                'div:contains("Commercial Auto")',
                'span:contains("Commercial Auto")',
                'li:contains("Commercial Auto")',
                '[role="button"]:contains("Commercial")',
                '[role="link"]:contains("Commercial")',
                '[role="menuitem"]:contains("Commercial")',
                // Class/ID based
                '[class*="commercial"]',
                '[id*="commercial"]',
                '[data-testid*="commercial"]'
            ];
            
            for (let selector of selectors) {
                try {
                    let elements;
                    if (selector.includes(':contains')) {
                        // Handle :contains selector manually
                        const parts = selector.split(':contains');
                        const tag = parts[0] || '*';
                        const searchText = parts[1].replace(/[()'"]/g, '');
                        elements = Array.from(document.querySelectorAll(tag)).filter(el => {
                            const text = el.textContent || '';
                            return text.includes(searchText) && 
                                   // Make sure it's not a parent container with too much text
                                   text.length < 200 &&
                                   // Check if element is clickable
                                   (el.tagName === 'BUTTON' || el.tagName === 'A' || 
                                    el.style.cursor === 'pointer' || 
                                    el.onclick || el.getAttribute('onclick') ||
                                    el.getAttribute('role') === 'button' ||
                                    el.getAttribute('role') === 'link' ||
                                    el.getAttribute('role') === 'menuitem');
                        });
                    } else {
                        elements = document.querySelectorAll(selector);
                    }
                    
                    for (let element of elements) {
                        if (element && element.offsetParent !== null) { // Check if visible
                            // Double-check text content
                            const text = element.textContent || '';
                            if (text.toLowerCase().includes('commercial') && 
                                (text.toLowerCase().includes('auto') || text.toLowerCase().includes('truck'))) {
                                element.scrollIntoView(true);
                                element.click();
                                console.log('Clicked Commercial Auto button with selector:', selector);
                                return true;
                            }
                        }
                    }
                } catch (e) {
                    console.log('Error with selector:', selector, e);
                }
            }
            
            return false;
            """
            if self.driver.execute_script(script):
                logger.info("Clicked Commercial Auto / Trucking button")
                return True
            else:
                logger.error("Could not find Commercial Auto / Trucking button")
                return False
        except Exception as e:
            logger.error(f"Failed to click Commercial Auto button: {e}")
            return False
    
    def type_text(self, text):
        """Type text into the currently focused element"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.send_keys(text).perform()
            logger.info(f"Typed text: '{text}'")
            return True
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def verify_text_in_field(self, selectors):
        """Verify that a field contains text"""
        for selector_type, selector_value in selectors:
            try:
                if selector_type == "id":
                    element = self.driver.find_element(By.ID, selector_value)
                elif selector_type == "name":
                    element = self.driver.find_element(By.NAME, selector_value)
                elif selector_type == "xpath":
                    element = self.driver.find_element(By.XPATH, selector_value)
                elif selector_type == "css":
                    element = self.driver.find_element(By.CSS_SELECTOR, selector_value)
                elif selector_type == "placeholder":
                    element = self.driver.find_element(By.XPATH, f"//input[@placeholder='{selector_value}']")
                
                # Get the value
                value = element.get_attribute('value')
                if value and len(value) > 0:
                    logger.info(f"Field {selector_type}='{selector_value}' contains text: '{value}'")
                    return True
                else:
                    logger.info(f"Field {selector_type}='{selector_value}' is empty")
                    return False
            except Exception as e:
                logger.debug(f"Failed to check field with {selector_type}='{selector_value}': {e}")
                continue
        
        logger.error(f"Could not verify text in any of the provided selectors")
        return False
    
    def wait_for_page_load(self, timeout=10):
        """Wait for page to finish loading"""
        try:
            # Wait for document ready state
            self.driver.execute_script("""
                return new Promise((resolve) => {
                    if (document.readyState === 'complete') {
                        resolve();
                    } else {
                        window.addEventListener('load', resolve);
                        setTimeout(resolve, %d);
                    }
                });
            """ % (timeout * 1000))
            return True
        except Exception as e:
            logger.error(f"Error waiting for page load: {e}")
            return False
    
    def wait_for_element_to_appear(self, text_to_find, timeout=10):
        """Wait for an element with specific text to appear in the scanned elements"""
        start_time = time.time()
        logger.info(f"Waiting for element containing text: '{text_to_find}'")
        
        while time.time() - start_time < timeout:
            try:
                # Check if element exists in the page - look for username in various formats
                script = f"""
                const elements = document.querySelectorAll('.element-scanner-label');
                for (let el of elements) {{
                    const labelText = el.textContent.toLowerCase();
                    // Check for various username field formats
                    if (labelText.includes('{text_to_find.lower()}') ||
                        labelText.includes('input[text]') ||
                        labelText.includes('input[email]') ||
                        labelText.includes('#username') ||
                        labelText.includes(': username') ||
                        labelText.includes('email') ||
                        labelText.includes('user id') ||
                        labelText.includes('user name') ||
                        labelText.includes('login') ||
                        labelText.includes('userId')) {{
                        console.log('Found username field:', el.textContent);
                        return true;
                    }}
                }}
                return false;
                """
                if self.driver.execute_script(script):
                    logger.info(f"Found element with text: '{text_to_find}'")
                    return True
            except Exception as e:
                logger.debug(f"Error checking for element: {e}")
            
            time.sleep(0.5)
        
        logger.warning(f"Timeout waiting for element with text: '{text_to_find}'")
        return False
    
    def perform_login_automation(self):
        """Perform the login automation sequence"""
        try:
            logger.info("Starting login automation...")
            
            # Re-inject scanner to see current form elements
            logger.info("Injecting scanner and waiting for login fields...")
            self.inject_element_scanner()
            
            # Wait for username field to be detected
            if not self.wait_for_element_to_appear("username"):
                logger.warning("Username field not detected by scanner, will try anyway...")
            time.sleep(0.5)
            
            # Define possible selectors for username field
            username_selectors = [
                ("id", "username"),
                ("name", "username"),
                ("id", "email"),
                ("name", "email"),
                ("xpath", "//input[@type='text' or @type='email'][1]"),
                ("placeholder", "Username"),
                ("placeholder", "Email")
            ]
            
            # Click on username field
            logger.info("Step 1: Clicking on username field...")
            if not self.find_and_click_element(username_selectors):
                return {"success": False, "error": "Could not find username field"}
            
            time.sleep(0.5)
            
            # Type username
            logger.info("Step 2: Typing username...")
            if not self.type_text("I017346"):
                return {"success": False, "error": "Failed to type username"}
            
            time.sleep(0.5)
            
            # Verify username was typed
            logger.info("Step 3: Verifying username field has text...")
            if not self.verify_text_in_field(username_selectors):
                return {"success": False, "error": "Username field does not contain text"}
            
            # Define possible selectors for password field
            password_selectors = [
                ("id", "password"),
                ("name", "password"),
                ("xpath", "//input[@type='password'][1]"),
                ("placeholder", "Password")
            ]
            
            # Click on password field - use special method for password
            logger.info("Step 4: Clicking on password field...")
            if not self.click_password_field():
                return {"success": False, "error": "Could not find password field"}
            
            time.sleep(0.5)
            
            # Type password
            logger.info("Step 5: Typing password...")
            if not self.type_text("25Nickc124"):
                return {"success": False, "error": "Failed to type password"}
            
            time.sleep(0.5)
            
            # Verify password was typed
            logger.info("Step 6: Verifying password field has text...")
            if not self.verify_text_in_field(password_selectors):
                return {"success": False, "error": "Password field does not contain text"}
            
            # Click login button using special method
            logger.info("Step 7: Clicking login button...")
            if not self.click_login_button():
                return {"success": False, "error": "Could not find login button"}
            
            logger.info("Login automation completed successfully!")
            
            # Wait for page navigation after login
            logger.info("Waiting for page to load after login...")
            time.sleep(3)  # Initial wait
            self.wait_for_page_load()
            
            # Re-inject scanner on the new page
            logger.info("Re-injecting scanner on post-login page...")
            element_count = self.inject_element_scanner()
            logger.info(f"Found {element_count} elements on new page")
            
            # Take a screenshot after login and scanning
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"login_result_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            self.driver.save_screenshot(filepath)
            screenshot_base64 = self.driver.get_screenshot_as_base64()
            
            # Start continuous monitoring
            logger.info("Starting continuous page monitoring...")
            self.monitoring_active = True
            self.start_continuous_monitoring()
            
            # Wait for dashboard to fully load
            logger.info("Waiting for dashboard to load...")
            time.sleep(5)  # Give dashboard time to load
            self.wait_for_page_load()
            
            # Re-inject scanner to see dashboard elements
            logger.info("Re-injecting scanner to find dashboard elements...")
            element_count = self.inject_element_scanner()
            logger.info(f"Found {element_count} elements on dashboard")
            
            # Take screenshot of dashboard
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            self.driver.save_screenshot(filepath)
            
            # Wait for Commercial Autos / Trucking button to appear
            logger.info("Looking for 'Commercial Autos / Trucking' button...")
            time.sleep(2)  # Brief pause to ensure all elements are rendered
            
            # Try to click Commercial Auto / Trucking button
            if self.click_commercial_auto_button():
                logger.info("Successfully clicked Commercial Autos / Trucking button!")
                
                # Wait for navigation after clicking
                time.sleep(3)
                self.wait_for_page_load()
                
                # Zoom out to 25% to see more of the page
                logger.info("Zooming out to 50% for better visibility...")
                self.driver.execute_script("document.body.style.zoom = '0.5'")
                time.sleep(1)  # Brief pause to let zoom take effect
                
                # Take screenshot after clicking
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"commercial_auto_selected_{timestamp}.png"
                filepath = os.path.join(self.screenshots_dir, filename)
                self.driver.save_screenshot(filepath)
                
                # Re-inject scanner on new page
                self.inject_element_scanner()
                
                logger.info("Commercial Auto / Trucking selection completed!")
                
                # Wait for page to load after clicking Commercial Auto
                logger.info("Waiting for ZIP code field to appear...")
                time.sleep(3)
                self.wait_for_page_load()
                
                # Re-inject scanner to see ZIP code field
                logger.info("Re-injecting scanner to find ZIP code field...")
                element_count = self.inject_element_scanner()
                logger.info(f"Found {element_count} elements on ZIP code page")
                
                # Enter ZIP code
                logger.info("Entering ZIP code 44256...")
                if self.enter_zip_code("44256"):
                    logger.info("Successfully entered ZIP code!")
                    
                    # Take screenshot after entering ZIP
                    time.sleep(1)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"zip_code_entered_{timestamp}.png"
                    filepath = os.path.join(self.screenshots_dir, filename)
                    self.driver.save_screenshot(filepath)
                    logger.info(f"Screenshot saved: {filename}")
                    
                    # Now look for and enter DOT number
                    logger.info("Looking for DOT number field...")
                    time.sleep(2)  # Wait for page to update after ZIP entry
                    
                    # Re-inject scanner to find DOT field
                    element_count = self.inject_element_scanner()
                    logger.info(f"Found {element_count} elements after ZIP entry")
                    
                    # Enter DOT number - use the one from mock data
                    dot_number = "3431557"  # This is from the mock data
                    logger.info(f"Entering DOT number {dot_number}...")
                    
                    # Add a delay and take screenshot before attempting
                    time.sleep(1)
                    pre_dot_screenshot = f"pre_dot_entry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(os.path.join(self.screenshots_dir, pre_dot_screenshot))
                    logger.info(f"Pre-DOT screenshot: {pre_dot_screenshot}")
                    
                    if self.enter_dot_number(dot_number):
                        logger.info("Successfully entered DOT number!")
                        
                        # Take screenshot after entering DOT
                        time.sleep(1)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"dot_number_entered_{timestamp}.png"
                        filepath = os.path.join(self.screenshots_dir, filename)
                        self.driver.save_screenshot(filepath)
                        logger.info(f"Screenshot saved: {filename}")
                    else:
                        logger.warning("Could not find or enter DOT number")
                else:
                    logger.warning("Could not find or enter ZIP code")
            else:
                logger.warning("Could not find or click Commercial Autos / Trucking button")
                logger.info("The button may be on a different page or have different text")
            
            return {
                "success": True,
                "message": "Login automation completed",
                "element_count": element_count,
                "screenshot": {
                    "filename": filename,
                    "base64": screenshot_base64
                }
            }
            
        except Exception as e:
            logger.error(f"Login automation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def start_continuous_monitoring(self):
        """Start a background thread to continuously monitor for page changes"""
        import threading
        
        def monitor_loop():
            while self.monitoring_active and self.driver:
                try:
                    # Check for page changes every 2 seconds
                    time.sleep(2)
                    if self.monitor_page_changes():
                        logger.info("Page change detected, scanner re-injected")
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    if "invalid session id" in str(e).lower():
                        self.monitoring_active = False
                        break
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Continuous monitoring thread started")
    
    def cleanup(self):
        """Close browser and clean up temporary files"""
        self.monitoring_active = False
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")
        
        # Clean up temporary user data directory
        if hasattr(self, 'user_data_dir') and self.user_data_dir and os.path.exists(self.user_data_dir):
            import shutil
            try:
                shutil.rmtree(self.user_data_dir)
                logger.info(f"Cleaned up temporary directory: {self.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")


if __name__ == "__main__":
    # Test the scanner
    scanner = ElementScannerBrowser()
    
    if scanner.setup_driver(headless=False):
        result = scanner.scan_page("https://www.geico.com")
        
        if result['success']:
            print(f"Found {result['element_count']} elements")
            print(f"Screenshot saved: {result['screenshot']['filename']}")
        
        time.sleep(5)  # Keep browser open to see the overlays
        scanner.cleanup()