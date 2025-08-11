#!/usr/bin/env python3
"""
Mock GEICO Browser Controller - Simulates screenshots without requiring Chrome
"""

import os
import json
import time
import base64
from datetime import datetime
import logging
from PIL import Image, ImageDraw, ImageFont
import io

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GEICOBrowserController:
    def __init__(self):
        self.driver = "mock_driver"  # Mock driver
        self.screenshots_dir = "geico_screenshots"
        self.current_step = ""
        self.mock_data = None
        
        # Create screenshots directory
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
        
        # Load mock data
        try:
            with open('truck_quote_example.json', 'r') as f:
                self.mock_data = json.load(f)
        except:
            self.mock_data = {}
    
    def setup_driver(self):
        """Mock setup - always returns True"""
        logger.info("Mock Chrome driver initialized successfully")
        return True
    
    def create_mock_screenshot(self, title, content):
        """Create a mock screenshot image"""
        # Create a white image
        width, height = 1200, 800
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw header
        header_height = 100
        draw.rectangle([(0, 0), (width, header_height)], fill='#002c5f')
        
        # Try to use a font, fallback to default if not available
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            content_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
        
        # Draw GEICO logo text
        draw.text((50, 30), "GEICO", font=title_font, fill='white')
        
        # Draw title
        draw.text((50, 120), title, font=title_font, fill='#002c5f')
        
        # Draw content
        y_offset = 200
        for line in content:
            draw.text((50, y_offset), line, font=content_font, fill='#333333')
            y_offset += 40
        
        # Draw form fields
        y_offset += 20
        for i in range(3):
            # Field label
            draw.rectangle([(50, y_offset), (width-50, y_offset+35)], outline='#cccccc', width=2)
            y_offset += 50
        
        # Draw button
        button_y = height - 100
        draw.rectangle([(width//2-100, button_y), (width//2+100, button_y+50)], fill='#007ac2')
        draw.text((width//2-50, button_y+15), "Continue", font=content_font, fill='white')
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str
    
    def capture_screenshot(self, step_name):
        """Create and save a mock screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{step_name}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            # Generate content based on step
            if step_name == "geico_homepage":
                title = "Get a Free Auto Quote"
                content = [
                    "Save up to 15% or more on car insurance",
                    "Get your quote in minutes",
                    "Join millions of satisfied customers"
                ]
            elif step_name == "auto_quote_start":
                title = "Start Your Auto Quote"
                content = [
                    "Enter your ZIP code to begin",
                    f"ZIP Code: {self.mock_data.get('driver', {}).get('address', {}).get('zip_code', '10001')}",
                    "We'll guide you through the process"
                ]
            elif step_name == "zip_code_entered":
                title = "Location Confirmed"
                content = [
                    f"Quote for ZIP: {self.mock_data.get('driver', {}).get('address', {}).get('zip_code', '10001')}",
                    "Next: Vehicle Information",
                    "Tell us about your vehicle"
                ]
            else:
                title = f"Step: {step_name}"
                content = [
                    "Processing your information...",
                    "Please wait while we load the next section",
                    f"Current step: {step_name}"
                ]
            
            # Create mock screenshot
            screenshot_base64 = self.create_mock_screenshot(title, content)
            
            # Save to file
            img_data = base64.b64decode(screenshot_base64)
            with open(filepath, 'wb') as f:
                f.write(img_data)
            
            logger.info(f"Mock screenshot captured: {filename}")
            
            return {
                'filename': filename,
                'filepath': filepath,
                'base64': screenshot_base64,
                'timestamp': timestamp,
                'step': step_name
            }
            
        except Exception as e:
            logger.error(f"Failed to capture mock screenshot: {e}")
            return None
    
    def navigate_to_geico(self):
        """Simulate navigation to GEICO"""
        try:
            logger.info("Simulating navigation to GEICO quote page...")
            time.sleep(1)  # Simulate loading time
            
            # Capture initial page
            self.capture_screenshot("geico_homepage")
            
            # Simulate clicking auto quote
            time.sleep(1)
            self.capture_screenshot("auto_quote_start")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to simulate navigation: {e}")
            return False
    
    def fill_zip_code(self, zip_code):
        """Simulate filling zip code"""
        try:
            logger.info(f"Simulating zip code entry: {zip_code}")
            time.sleep(1)
            
            self.capture_screenshot("zip_code_entered")
            
            # Simulate form submission
            time.sleep(1)
            self.capture_screenshot("after_zip_submit")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to simulate zip code entry: {e}")
            return False
    
    def get_latest_screenshot(self):
        """Get the most recent screenshot data"""
        try:
            screenshots = [f for f in os.listdir(self.screenshots_dir) if f.endswith('.png')]
            if not screenshots:
                # Create a default screenshot if none exist
                self.capture_screenshot("default")
                screenshots = [f for f in os.listdir(self.screenshots_dir) if f.endswith('.png')]
                
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
        """Mock cleanup"""
        logger.info("Mock browser closed")