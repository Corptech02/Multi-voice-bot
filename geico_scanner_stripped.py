#!/usr/bin/env python3
"""
GEICO Scanner - Stripped Down Version with Full Functionality
Combines simple UI with browser automation capabilities
"""

from flask import Flask, render_template_string, jsonify, send_file
import threading
import time
import json
import os
from datetime import datetime
from geico_browser_controller import GEICOBrowserController
import base64

app = Flask(__name__)

# Global variables
scanner_thread = None
browser_controller = None
scan_status = {
    'running': False,
    'paused': False,
    'current_step': 'Idle',
    'screenshots': [],
    'log': []
}

# Simple HTML template - stripped down UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GEICO Scanner - Stripped Down</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
        }
        .status.running {
            border-left-color: #28a745;
        }
        .status.paused {
            border-left-color: #ffc107;
        }
        .status.stopped {
            border-left-color: #dc3545;
        }
        .controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 30px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-start {
            background-color: #28a745;
            color: white;
        }
        .btn-start:hover:not(:disabled) {
            background-color: #218838;
        }
        .btn-pause {
            background-color: #ffc107;
            color: #212529;
        }
        .btn-pause:hover:not(:disabled) {
            background-color: #e0a800;
        }
        .btn-stop {
            background-color: #dc3545;
            color: white;
        }
        .btn-stop:hover:not(:disabled) {
            background-color: #c82333;
        }
        .log-container {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 10px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 3px 0;
        }
        .screenshot-container {
            margin-top: 20px;
            text-align: center;
        }
        .screenshot {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 10px;
        }
        .info {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 10px;
            margin-bottom: 20px;
        }
    </style>
    <script>
        let updateInterval;
        
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    // Update status display
                    const statusDiv = document.getElementById('status');
                    const statusText = document.getElementById('status-text');
                    
                    statusText.textContent = `Status: ${data.current_step}`;
                    
                    statusDiv.className = 'status';
                    if (data.running && !data.paused) {
                        statusDiv.classList.add('running');
                    } else if (data.paused) {
                        statusDiv.classList.add('paused');
                    } else {
                        statusDiv.classList.add('stopped');
                    }
                    
                    // Update buttons
                    document.getElementById('btn-start').disabled = data.running;
                    document.getElementById('btn-pause').disabled = !data.running || data.paused;
                    document.getElementById('btn-resume').disabled = !data.paused;
                    document.getElementById('btn-stop').disabled = !data.running;
                    
                    // Update log
                    const logContainer = document.getElementById('log');
                    logContainer.innerHTML = data.log.map(entry => 
                        `<div class="log-entry">${entry}</div>`
                    ).join('');
                    logContainer.scrollTop = logContainer.scrollHeight;
                    
                    // Update latest screenshot
                    if (data.screenshots.length > 0) {
                        const latestScreenshot = data.screenshots[data.screenshots.length - 1];
                        document.getElementById('screenshot').src = latestScreenshot;
                        document.getElementById('screenshot').style.display = 'block';
                    }
                });
        }
        
        function startScan() {
            fetch('/start', { method: 'POST' })
                .then(() => updateStatus());
        }
        
        function pauseScan() {
            fetch('/pause', { method: 'POST' })
                .then(() => updateStatus());
        }
        
        function resumeScan() {
            fetch('/resume', { method: 'POST' })
                .then(() => updateStatus());
        }
        
        function stopScan() {
            fetch('/stop', { method: 'POST' })
                .then(() => updateStatus());
        }
        
        // Start periodic updates
        updateInterval = setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</head>
<body>
    <div class="container">
        <h1>GEICO Scanner - Stripped Down</h1>
        
        <div class="info">
            <strong>Simple UI with Full Browser Automation</strong><br>
            Click "Start Quote" to begin automated GEICO form scanning and filling.
        </div>
        
        <div id="status" class="status stopped">
            <span id="status-text">Status: Idle</span>
        </div>
        
        <div class="controls">
            <button id="btn-start" class="btn-start" onclick="startScan()">Start Quote</button>
            <button id="btn-pause" class="btn-pause" onclick="pauseScan()" disabled>Pause</button>
            <button id="btn-resume" class="btn-pause" onclick="resumeScan()" disabled>Resume</button>
            <button id="btn-stop" class="btn-stop" onclick="stopScan()" disabled>Stop</button>
        </div>
        
        <div class="log-container" id="log"></div>
        
        <div class="screenshot-container">
            <img id="screenshot" class="screenshot" style="display:none;">
        </div>
    </div>
</body>
</html>
'''

def add_log(message):
    """Add a message to the log"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    scan_status['log'].append(log_entry)
    # Keep only last 50 log entries
    if len(scan_status['log']) > 50:
        scan_status['log'] = scan_status['log'][-50:]
    print(log_entry)

def run_scanner():
    """Main scanner function with browser automation"""
    global browser_controller, scan_status
    
    try:
        add_log("Starting GEICO scanner...")
        scan_status['current_step'] = 'Initializing browser'
        
        # Initialize browser controller
        browser_controller = GEICOBrowserController()
        browser_controller.setup_driver()
        add_log("Browser initialized successfully")
        
        # Load mock data
        mock_data_path = 'truck_quote_example.json'
        if os.path.exists(mock_data_path):
            with open(mock_data_path, 'r') as f:
                mock_data = json.load(f)
            add_log(f"Loaded mock data from {mock_data_path}")
        else:
            add_log("Warning: Mock data file not found, using defaults")
            mock_data = {
                "location": {"zip_code": "30301"},
                "driver_info": {"dot_number": "3431557"}
            }
        
        # Navigate to GEICO
        scan_status['current_step'] = 'Navigating to GEICO'
        add_log("Navigating to GEICO commercial auto page...")
        browser_controller.navigate_to_geico()
        
        # Take initial screenshot
        screenshot = browser_controller.take_screenshot("initial")
        if screenshot:
            scan_status['screenshots'].append(f"data:image/png;base64,{screenshot}")
            add_log("Initial screenshot captured")
        
        if scan_status['paused']:
            add_log("Scan paused")
            return
        
        # Fill ZIP code
        scan_status['current_step'] = 'Filling ZIP code'
        zip_code = mock_data.get('location', {}).get('zip_code', '30301')
        add_log(f"Filling ZIP code: {zip_code}")
        browser_controller.fill_zip_code(zip_code)
        time.sleep(2)
        
        # Take screenshot after ZIP
        screenshot = browser_controller.take_screenshot("after_zip")
        if screenshot:
            scan_status['screenshots'].append(f"data:image/png;base64,{screenshot}")
            add_log("Screenshot after ZIP captured")
        
        if scan_status['paused']:
            add_log("Scan paused")
            return
        
        # Fill DOT number
        scan_status['current_step'] = 'Filling DOT number'
        dot_number = mock_data.get('driver_info', {}).get('dot_number', '3431557')
        add_log(f"Filling DOT number: {dot_number}")
        browser_controller.fill_usdot(dot_number)
        time.sleep(2)
        
        # Take screenshot after DOT
        screenshot = browser_controller.take_screenshot("after_dot")
        if screenshot:
            scan_status['screenshots'].append(f"data:image/png;base64,{screenshot}")
            add_log("Screenshot after DOT captured")
        
        # Continue with other fields...
        scan_status['current_step'] = 'Scan complete'
        add_log("GEICO scan completed successfully!")
        
    except Exception as e:
        add_log(f"Error during scan: {str(e)}")
        scan_status['current_step'] = f'Error: {str(e)}'
    finally:
        scan_status['running'] = False
        if browser_controller:
            try:
                browser_controller.close()
                add_log("Browser closed")
            except:
                pass

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    return jsonify(scan_status)

@app.route('/start', methods=['POST'])
def start():
    global scanner_thread, scan_status
    
    if not scan_status['running']:
        scan_status['running'] = True
        scan_status['paused'] = False
        scan_status['log'] = []
        scan_status['screenshots'] = []
        scanner_thread = threading.Thread(target=run_scanner)
        scanner_thread.start()
        add_log("Scanner started")
    
    return jsonify({'status': 'started'})

@app.route('/pause', methods=['POST'])
def pause():
    global scan_status
    if scan_status['running'] and not scan_status['paused']:
        scan_status['paused'] = True
        add_log("Scanner paused")
    return jsonify({'status': 'paused'})

@app.route('/resume', methods=['POST'])
def resume():
    global scan_status
    if scan_status['running'] and scan_status['paused']:
        scan_status['paused'] = False
        add_log("Scanner resumed")
    return jsonify({'status': 'resumed'})

@app.route('/stop', methods=['POST'])
def stop():
    global scan_status, browser_controller
    scan_status['running'] = False
    scan_status['paused'] = False
    if browser_controller:
        try:
            browser_controller.close()
        except:
            pass
    add_log("Scanner stopped")
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    print("Starting GEICO Scanner - Stripped Down Version")
    print("Access at http://localhost:5557")
    app.run(debug=True, host='0.0.0.0', port=5557)