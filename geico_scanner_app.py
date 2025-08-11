#!/usr/bin/env python3
"""
GEICO Quote Scanner - Web Interface with Browser Automation
"""

import os
import json
import base64
import threading
import time
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
try:
    from geico_browser_controller import GEICOBrowserController
except ImportError:
    # Fallback to mock controller if selenium is not available
    from geico_browser_controller_mock import GEICOBrowserController

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
SCREENSHOTS_FOLDER = 'geico_screenshots'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create folders if they don't exist
for folder in [UPLOAD_FOLDER, SCREENSHOTS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Global browser controller instance
browser_controller = None
browser_lock = threading.Lock()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main scanner page"""
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GEICO Quote Scanner</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #002c5f;
            text-align: center;
        }
        .main-content {
            display: flex;
            gap: 20px;
        }
        .left-panel {
            flex: 1;
        }
        .right-panel {
            flex: 1;
            max-width: 600px;
        }
        .control-panel {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        .primary-btn {
            background-color: #007ac2;
            color: white;
        }
        .primary-btn:hover {
            background-color: #005a92;
        }
        .secondary-btn {
            background-color: #6c757d;
            color: white;
        }
        .secondary-btn:hover {
            background-color: #545b62;
        }
        .success-btn {
            background-color: #28a745;
            color: white;
        }
        .danger-btn {
            background-color: #dc3545;
            color: white;
        }
        .danger-btn:hover {
            background-color: #c82333;
        }
        .screenshot-display {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            margin: 20px 0;
            min-height: 400px;
            background-color: #f8f9fa;
            text-align: center;
        }
        .screenshot-display img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .screenshot-placeholder {
            padding: 100px 20px;
            color: #6c757d;
        }
        .upload-section {
            margin: 20px 0;
            padding: 20px;
            border: 2px dashed #ccc;
            border-radius: 8px;
            text-align: center;
        }
        .progress-section {
            margin: 20px 0;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background-color: #007ac2;
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .status-lights {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-light {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: #ddd;
            transition: background-color 0.3s;
        }
        .status-light.active {
            background-color: #ffc107;
        }
        .status-light.complete {
            background-color: #28a745;
        }
        .log-section {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
        }
        .log-entry {
            padding: 5px 0;
            font-family: monospace;
            font-size: 14px;
        }
        .log-entry.success {
            color: #28a745;
        }
        .log-entry.info {
            color: #007ac2;
        }
        .log-entry.error {
            color: #dc3545;
        }
        #uploadStatus {
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
            display: none;
        }
        #uploadStatus.success {
            background-color: #d4edda;
            color: #155724;
            display: block;
        }
        #uploadStatus.error {
            background-color: #f8d7da;
            color: #721c24;
            display: block;
        }
        .geico-link {
            display: inline-block;
            padding: 10px 20px;
            background-color: #002c5f;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        .geico-link:hover {
            background-color: #001a3a;
        }
        @media (max-width: 768px) {
            .main-content {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 GEICO Quote Scanner</h1>
        
        <div class="control-panel">
            <button id="startAutoBtn" class="primary-btn">▶️ Start Auto Scanner</button>
            <button id="captureBtn" class="success-btn">📸 Capture GEICO Site</button>
            <button id="pauseBtn" class="secondary-btn" disabled>⏸️ Pause</button>
            <button id="resumeBtn" class="secondary-btn" disabled>▶️ Resume</button>
            <button id="stopBtn" class="danger-btn" disabled>⏹️ Stop</button>
            <a href="https://gateway.geico.com/" target="_blank" class="geico-link">🔗 Open GEICO Quote</a>
        </div>

        <div class="main-content">
            <div class="left-panel">
                <div class="progress-section">
                    <h3>Upload Progress</h3>
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill">0%</div>
                    </div>
                </div>

                <div class="status-lights">
                    <div class="status-item">
                        <div id="driverLight" class="status-light"></div>
                        <span>Driver Info</span>
                    </div>
                    <div class="status-item">
                        <div id="vehicleLight" class="status-light"></div>
                        <span>Vehicle Info</span>
                    </div>
                    <div class="status-item">
                        <div id="coverageLight" class="status-light"></div>
                        <span>Coverage</span>
                    </div>
                    <div class="status-item">
                        <div id="historyLight" class="status-light"></div>
                        <span>Driving History</span>
                    </div>
                    <div class="status-item">
                        <div id="discountsLight" class="status-light"></div>
                        <span>Discounts</span>
                    </div>
                </div>

                <div class="upload-section">
                    <h3>📸 Manual Screenshot Upload</h3>
                    <p>Upload screenshots from GEICO quote pages</p>
                    <input type="file" id="fileInput" accept="image/*" multiple style="display: none;">
                    <button onclick="document.getElementById('fileInput').click()" class="primary-btn">
                        Choose Screenshots
                    </button>
                    <div id="uploadStatus"></div>
                </div>

                <div class="log-section">
                    <h3>📋 Upload Log</h3>
                    <div id="logContainer"></div>
                </div>
            </div>

            <div class="right-panel">
                <h3>🖼️ Live Screenshot</h3>
                <div class="screenshot-display" id="screenshotDisplay">
                    <div class="screenshot-placeholder">
                        No screenshot yet. Click "Capture GEICO Site" to start.
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isScanning = false;
        let isPaused = false;
        let uploadQueue = [];
        let currentIndex = 0;
        let uploadInterval;
        let screenshotInterval;

        // Status light mapping
        const statusLights = {
            'driver': ['first_name', 'last_name', 'birth_date', 'gender', 'marital_status', 'email', 'phone'],
            'vehicle': ['year', 'make', 'model', 'vin', 'ownership', 'primary_use', 'annual_mileage'],
            'coverage': ['liability_limit', 'bodily_injury', 'property_damage', 'comprehensive_deductible', 'collision_deductible'],
            'history': ['accidents_violations', 'claims', 'license_status', 'years_licensed'],
            'discounts': ['good_driver', 'multi_vehicle', 'home_owner', 'anti_theft']
        };

        // Load mock data
        let mockData = {};
        fetch('/api/mock-data')
            .then(response => response.json())
            .then(data => {
                mockData = data;
                console.log('Mock data loaded:', mockData);
            })
            .catch(error => {
                console.error('Error loading mock data:', error);
            });

        function addLog(message, type = 'info') {
            const logContainer = document.getElementById('logContainer');
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logContainer.appendChild(entry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function updateProgress(percentage) {
            const progressFill = document.getElementById('progressFill');
            progressFill.style.width = percentage + '%';
            progressFill.textContent = percentage + '%';
        }

        function updateStatusLight(section, status) {
            const light = document.getElementById(section + 'Light');
            if (status === 'active') {
                light.classList.add('active');
                light.classList.remove('complete');
            } else if (status === 'complete') {
                light.classList.remove('active');
                light.classList.add('complete');
            } else {
                light.classList.remove('active', 'complete');
            }
        }

        function displayScreenshot(imageData) {
            const displayDiv = document.getElementById('screenshotDisplay');
            if (imageData) {
                displayDiv.innerHTML = `<img src="data:image/png;base64,${imageData}" alt="GEICO Screenshot">`;
            } else {
                displayDiv.innerHTML = '<div class="screenshot-placeholder">No screenshot available</div>';
            }
        }

        function captureGEICOSite() {
            addLog('Capturing GEICO site...', 'info');
            document.getElementById('captureBtn').disabled = true;
            
            fetch('/api/capture-geico', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addLog('GEICO site captured successfully', 'success');
                        if (data.screenshot) {
                            displayScreenshot(data.screenshot);
                        }
                        // Start periodic screenshot updates
                        startScreenshotUpdates();
                    } else {
                        throw new Error(data.error || 'Capture failed');
                    }
                })
                .catch(error => {
                    addLog(`Capture error: ${error.message}`, 'error');
                })
                .finally(() => {
                    document.getElementById('captureBtn').disabled = false;
                });
        }

        function startScreenshotUpdates() {
            // Update screenshot every 3 seconds
            screenshotInterval = setInterval(() => {
                fetch('/api/latest-screenshot')
                    .then(response => response.json())
                    .then(data => {
                        if (data.screenshot) {
                            displayScreenshot(data.screenshot);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching screenshot:', error);
                    });
            }, 3000);
        }

        function stopScreenshotUpdates() {
            if (screenshotInterval) {
                clearInterval(screenshotInterval);
                screenshotInterval = null;
            }
        }

        function prepareUploadQueue() {
            uploadQueue = [];
            
            // Flatten all data into upload queue
            if (mockData.driver) {
                Object.entries(mockData.driver).forEach(([key, value]) => {
                    if (typeof value === 'object') {
                        Object.entries(value).forEach(([subKey, subValue]) => {
                            uploadQueue.push({
                                section: 'driver',
                                field: `${key}_${subKey}`,
                                value: subValue
                            });
                        });
                    } else {
                        uploadQueue.push({
                            section: 'driver',
                            field: key,
                            value: value
                        });
                    }
                });
            }

            if (mockData.vehicle) {
                Object.entries(mockData.vehicle).forEach(([key, value]) => {
                    uploadQueue.push({
                        section: 'vehicle',
                        field: key,
                        value: value
                    });
                });
            }

            if (mockData.coverage_preferences) {
                Object.entries(mockData.coverage_preferences).forEach(([key, value]) => {
                    uploadQueue.push({
                        section: 'coverage',
                        field: key,
                        value: value
                    });
                });
            }

            if (mockData.driving_history) {
                Object.entries(mockData.driving_history).forEach(([key, value]) => {
                    uploadQueue.push({
                        section: 'history',
                        field: key,
                        value: value
                    });
                });
            }

            if (mockData.discounts) {
                Object.entries(mockData.discounts).forEach(([key, value]) => {
                    uploadQueue.push({
                        section: 'discounts',
                        field: key,
                        value: value
                    });
                });
            }
        }

        function processNextUpload() {
            if (!isScanning || isPaused || currentIndex >= uploadQueue.length) {
                if (currentIndex >= uploadQueue.length) {
                    completeScanning();
                }
                return;
            }

            const item = uploadQueue[currentIndex];
            const currentSection = item.section;
            
            // Update status lights
            Object.keys(statusLights).forEach(section => {
                if (section === currentSection) {
                    updateStatusLight(section, 'active');
                } else if (uploadQueue.slice(0, currentIndex).some(i => i.section === section)) {
                    updateStatusLight(section, 'complete');
                }
            });

            // Log the upload
            addLog(`Uploading ${item.field}: ${item.value}`, 'info');

            // Update progress
            const progress = Math.round((currentIndex + 1) / uploadQueue.length * 100);
            updateProgress(progress);

            currentIndex++;
        }

        function startAutoScanner() {
            if (!mockData || Object.keys(mockData).length === 0) {
                addLog('Error: Mock data not loaded', 'error');
                alert('Mock data not loaded. Please refresh the page.');
                return;
            }

            isScanning = true;
            isPaused = false;
            currentIndex = 0;
            
            prepareUploadQueue();
            
            document.getElementById('startAutoBtn').disabled = true;
            document.getElementById('pauseBtn').disabled = false;
            document.getElementById('stopBtn').disabled = false;
            
            addLog('Auto scanner started', 'success');
            addLog(`Found ${uploadQueue.length} fields to upload`, 'info');
            
            // Start capturing GEICO site
            captureGEICOSite();
            
            // Start processing uploads
            uploadInterval = setInterval(processNextUpload, 1000);
        }

        function pauseScanner() {
            isPaused = true;
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('resumeBtn').disabled = false;
            addLog('Scanner paused', 'info');
        }

        function resumeScanner() {
            isPaused = false;
            document.getElementById('pauseBtn').disabled = false;
            document.getElementById('resumeBtn').disabled = true;
            addLog('Scanner resumed', 'info');
        }

        function stopScanner() {
            isScanning = false;
            isPaused = false;
            clearInterval(uploadInterval);
            stopScreenshotUpdates();
            
            document.getElementById('startAutoBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('resumeBtn').disabled = true;
            document.getElementById('stopBtn').disabled = true;
            
            addLog('Scanner stopped', 'error');
            updateProgress(0);
            
            // Reset status lights
            Object.keys(statusLights).forEach(section => {
                updateStatusLight(section, '');
            });
        }

        function completeScanning() {
            clearInterval(uploadInterval);
            
            document.getElementById('startAutoBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('resumeBtn').disabled = true;
            document.getElementById('stopBtn').disabled = true;
            
            addLog('All fields uploaded successfully!', 'success');
            
            // Mark all sections as complete
            Object.keys(statusLights).forEach(section => {
                updateStatusLight(section, 'complete');
            });
        }

        // Event listeners
        document.getElementById('startAutoBtn').addEventListener('click', startAutoScanner);
        document.getElementById('captureBtn').addEventListener('click', captureGEICOSite);
        document.getElementById('pauseBtn').addEventListener('click', pauseScanner);
        document.getElementById('resumeBtn').addEventListener('click', resumeScanner);
        document.getElementById('stopBtn').addEventListener('click', stopScanner);

        // File upload handling
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                const formData = new FormData();
                for (let i = 0; i < files.length; i++) {
                    formData.append('screenshots', files[i]);
                }
                
                fetch('/api/upload-screenshots', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('uploadStatus').className = 'success';
                        document.getElementById('uploadStatus').textContent = 
                            `Successfully uploaded ${data.count} screenshot(s)`;
                        addLog(`Uploaded ${data.count} screenshot(s)`, 'success');
                    } else {
                        throw new Error(data.error || 'Upload failed');
                    }
                })
                .catch(error => {
                    document.getElementById('uploadStatus').className = 'error';
                    document.getElementById('uploadStatus').textContent = 
                        `Error: ${error.message}`;
                    addLog(`Upload error: ${error.message}`, 'error');
                });
            }
        });

        // Initialize
        addLog('Scanner ready', 'info');
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            stopScreenshotUpdates();
        });
    </script>
</body>
</html>''')

@app.route('/api/mock-data')
def api_mock_data():
    """Serve the mock quote data"""
    try:
        with open('truck_quote_example.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading mock data: {e}")
        return jsonify({'error': 'Failed to load mock data'}), 500

@app.route('/api/check-display')
def api_check_display():
    """Check if running in headless mode"""
    # Chrome can capture screenshots in headless mode, so always return true
    return jsonify({'has_display': True})

@app.route('/api/capture-geico', methods=['POST'])
def api_capture_geico():
    """Start capturing GEICO site with browser controller"""
    global browser_controller
    
    try:
        with browser_lock:
            # Initialize browser controller if needed
            if browser_controller is None:
                browser_controller = GEICOBrowserController()
            
            # Setup the browser
            if not browser_controller.setup_driver():
                return jsonify({
                    'success': False,
                    'error': 'Failed to initialize browser driver. Make sure Chrome/Chromium is installed.'
                }), 500
            
            # Navigate to GEICO
            if browser_controller.navigate_to_geico():
                # Load mock data to get zip code
                with open('truck_quote_example.json', 'r') as f:
                    mock_data = json.load(f)
                
                # Fill zip code
                zip_code = mock_data.get('driver_info', {}).get('address', {}).get('zip', '30301')
                browser_controller.fill_zip_code(zip_code)
                
                # Wait a bit for page transition after zip code
                time.sleep(2)
                
                # Fill USDOT field with DOT number from mock data
                dot_number = mock_data.get('driver_info', {}).get('dot_number', '3431557')
                logger.info(f"Filling USDOT field with DOT number: {dot_number}")
                browser_controller.fill_usdot(dot_number)
                
                # Get the latest screenshot
                screenshot_data = browser_controller.get_latest_screenshot()
                if screenshot_data:
                    return jsonify({
                        'success': True,
                        'message': 'GEICO site captured successfully with USDOT filled',
                        'screenshot': screenshot_data['base64']
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': 'Navigation successful but no screenshot available'
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to navigate to GEICO site'
                }), 500
                
    except Exception as e:
        logger.error(f"Error capturing GEICO site: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/latest-screenshot')
def api_latest_screenshot():
    """Get the latest screenshot from the browser controller"""
    global browser_controller
    
    if browser_controller is None:
        return jsonify({'screenshot': None})
    
    try:
        screenshot_data = browser_controller.get_latest_screenshot()
        if screenshot_data:
            return jsonify({'screenshot': screenshot_data['base64']})
        else:
            return jsonify({'screenshot': None})
    except Exception as e:
        logger.error(f"Error getting latest screenshot: {e}")
        return jsonify({'screenshot': None})

@app.route('/api/upload-screenshots', methods=['POST'])
def api_upload_screenshots():
    """Handle manual screenshot uploads"""
    try:
        if 'screenshots' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        files = request.files.getlist('screenshots')
        uploaded_count = 0
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_count += 1
                logger.info(f"Uploaded screenshot: {filename}")
        
        return jsonify({
            'success': True,
            'count': uploaded_count,
            'message': f'Successfully uploaded {uploaded_count} screenshot(s)'
        })
        
    except Exception as e:
        logger.error(f"Error uploading screenshots: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/screenshots/<filename>')
def serve_screenshot(filename):
    """Serve uploaded screenshots"""
    return send_from_directory(SCREENSHOTS_FOLDER, filename)

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def cleanup_browser():
    """Cleanup browser on shutdown"""
    global browser_controller
    if browser_controller:
        browser_controller.cleanup()
        browser_controller = None

if __name__ == '__main__':
    # Register cleanup
    import atexit
    atexit.register(cleanup_browser)
    
    # Get the local IP address
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*60)
    print("GEICO Quote Scanner with Browser Automation")
    print("="*60)
    print(f"Access from this computer: http://localhost:5557")
    print(f"Access from network: http://{local_ip}:5557")
    print("="*60)
    print("Features:")
    print("- Automatic GEICO site navigation and screenshot capture")
    print("- Visual progress tracking with status lights")
    print("- Mock data auto-upload simulation")
    print("- Manual screenshot upload support")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5557, debug=False)