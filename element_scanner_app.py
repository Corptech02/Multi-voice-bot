#!/usr/bin/env python3
"""
Element Scanner Web App - Simple interface to launch browser with element detection
"""

from flask import Flask, render_template, request, jsonify
from element_scanner_browser import ElementScannerBrowser
import os
import json
import logging
import time
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scanner instance
scanner = None


@app.route('/')
def index():
    """Main page with simple UI"""
    return render_template('element_scanner.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload (optional)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # If it's a JSON file, try to parse it
            data = None
            if filename.endswith('.json'):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                except:
                    pass
            
            return jsonify({
                'success': True,
                'filename': filename,
                'data': data
            })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/start_scan', methods=['POST'])
def start_scan():
    """Start the browser and element scanning"""
    global scanner
    
    try:
        data = request.get_json()
        url = data.get('url', 'https://gateway.geico.com')
        headless = data.get('headless', False)
        
        # Clean up any existing scanner
        if scanner:
            scanner.cleanup()
        
        # Create new scanner
        scanner = ElementScannerBrowser()
        
        if not scanner.setup_driver(headless=headless):
            return jsonify({
                'success': False,
                'error': 'Failed to initialize Chrome browser. This may be due to Chrome processes already running or permission issues. Please check the logs for more details.'
            })
        
        # Scan the page
        result = scanner.scan_page(url)
        
        # Automatically start login process
        if result.get('success'):
            login_result = scanner.perform_login_automation()
            result['login_automation'] = login_result
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Scan error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/capture_screenshot', methods=['POST'])
def capture_screenshot():
    """Capture a screenshot using the working scanner"""
    global scanner
    
    try:
        # Start scanner if not already running
        if not scanner or not scanner.driver:
            scanner = ElementScannerBrowser()
            if not scanner.setup_driver(headless=False):
                return jsonify({
                    'success': False,
                    'error': 'Failed to initialize Chrome browser'
                })
            
            # Navigate to GEICO
            scanner.driver.get('https://gateway.geico.com')
            time.sleep(2)
        
        # Take screenshot
        screenshot_base64 = scanner.driver.get_screenshot_as_base64()
        
        # Save screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"geico_screenshot_{timestamp}.png"
        filepath = os.path.join(scanner.screenshots_dir, filename)
        scanner.driver.save_screenshot(filepath)
        
        return jsonify({
            'success': True,
            'screenshot': screenshot_base64,
            'filename': filename
        })
    
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    """Stop the browser"""
    global scanner
    
    try:
        if scanner:
            scanner.cleanup()
            scanner = None
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/rescan', methods=['POST'])
def rescan():
    """Re-run the element detection on current page"""
    global scanner
    
    try:
        if not scanner or not scanner.driver:
            return jsonify({
                'success': False,
                'error': 'No active browser session'
            })
        
        # Wait for page to stabilize
        time.sleep(1)
        scanner.wait_for_page_load()
        
        # Force re-injection of scanner
        logger.info(f"Rescanning page: {scanner.driver.current_url}")
        element_count = scanner.inject_element_scanner()
        
        # Take new screenshot
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rescan_{timestamp}.png"
        filepath = os.path.join(scanner.screenshots_dir, filename)
        
        scanner.driver.save_screenshot(filepath)
        screenshot_base64 = scanner.driver.get_screenshot_as_base64()
        
        logger.info(f"Rescan complete: {element_count} elements found")
        
        return jsonify({
            'success': True,
            'element_count': element_count,
            'screenshot': {
                'filename': filename,
                'base64': screenshot_base64
            },
            'current_url': scanner.driver.current_url
        })
    
    except Exception as e:
        logger.error(f"Rescan error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/automate_login', methods=['POST'])
def automate_login():
    """Perform automated login sequence"""
    global scanner
    
    try:
        # Start scanner if not already running
        if not scanner or not scanner.driver:
            scanner = ElementScannerBrowser()
            if not scanner.setup_driver(headless=False):
                return jsonify({
                    'success': False,
                    'error': 'Failed to initialize Chrome browser'
                })
            
            # Navigate to GEICO
            scanner.driver.get('https://gateway.geico.com')
            time.sleep(2)
        
        # Perform login automation
        result = scanner.perform_login_automation()
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Login automation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5557)