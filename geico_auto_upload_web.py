#!/usr/bin/env python3
from flask import Flask, render_template_string, jsonify, request
import json
import os
import time
from pathlib import Path
import webbrowser
from threading import Thread

app = Flask(__name__)

# Global state
upload_state = {
    'is_uploading': False,
    'is_paused': False,
    'progress': 0,
    'current_field': '',
    'uploaded_fields': [],
    'total_fields': 0,
    'log': []
}

# Load quote data
def load_quote_data():
    quote_file = Path("truck_quote_example.json")
    if quote_file.exists():
        with open(quote_file, 'r') as f:
            return json.load(f)
    return {}

quote_data = load_quote_data()

# Count total fields
def count_total_fields(data):
    count = 0
    for section in data.values():
        if isinstance(section, dict):
            count += len(section)
    return count

upload_state['total_fields'] = count_total_fields(quote_data)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GEICO Auto Quote Uploader</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #f0f4f8;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .status-panel {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        
        .progress-container {
            margin: 2rem 0;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50 0%, #2e7d32 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .controls {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin: 2rem 0;
        }
        
        .btn {
            padding: 0.75rem 2rem;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: #4CAF50;
            color: white;
        }
        
        .btn-primary:hover { background: #45a049; }
        
        .btn-stop {
            background: #f44336;
            color: white;
        }
        
        .btn-stop:hover { background: #da190b; }
        
        .btn-secondary {
            background: #2196F3;
            color: white;
        }
        
        .btn-secondary:hover { background: #0b7dda; }
        
        .btn-warning {
            background: #FF9800;
            color: white;
        }
        
        .btn-warning:hover { background: #e68900; }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .indicators {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        .indicator {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .indicator:hover {
            transform: translateY(-2px);
        }
        
        .indicator-light {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            margin: 0 auto 1rem;
            transition: all 0.3s ease;
        }
        
        .indicator-light.gray { background: #9e9e9e; }
        .indicator-light.yellow { 
            background: #FFEB3B; 
            box-shadow: 0 0 20px rgba(255, 235, 59, 0.5);
            animation: pulse 1s infinite;
        }
        .indicator-light.green { 
            background: #4CAF50; 
            box-shadow: 0 0 20px rgba(76, 175, 80, 0.5);
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .log-container {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-height: 400px;
            overflow-y: auto;
        }
        
        .log-entry {
            padding: 0.5rem;
            border-bottom: 1px solid #eee;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }
        
        .log-entry.success { color: #4CAF50; }
        .log-entry.info { color: #2196F3; }
        .log-entry.warning { color: #FF9800; }
        
        .status-text {
            font-size: 1.2rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1rem;
        }
        
        .field-display {
            background: #f5f5f5;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
            font-family: 'Courier New', monospace;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 2rem;
            background: #4CAF50;
            color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease;
            z-index: 1000;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚛 GEICO Auto Quote Uploader</h1>
        <p>Automatic form filling assistant</p>
    </div>
    
    <div class="container">
        <div class="status-panel">
            <div class="status-text" id="status">Status: Ready to Upload</div>
            
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress" style="width: 0%">0%</div>
                </div>
            </div>
            
            <div class="field-display" id="currentField">
                Current field: <span id="fieldName">None</span>
            </div>
            
            <div class="controls">
                <button class="btn btn-primary" id="startBtn" onclick="toggleUpload()">
                    Start Auto Upload
                </button>
                <button class="btn btn-warning" id="pauseBtn" onclick="togglePause()" disabled>
                    Pause
                </button>
                <a href="https://www.geico.com/auto-insurance-quote/" target="_blank" 
                   class="btn btn-secondary">
                    Open GEICO Site
                </a>
            </div>
        </div>
        
        <div class="indicators" id="indicators">
            <div class="indicator">
                <div class="indicator-light gray" id="driver-indicator"></div>
                <div>Driver Info</div>
            </div>
            <div class="indicator">
                <div class="indicator-light gray" id="vehicle-indicator"></div>
                <div>Vehicle Info</div>
            </div>
            <div class="indicator">
                <div class="indicator-light gray" id="coverage-indicator"></div>
                <div>Coverage</div>
            </div>
            <div class="indicator">
                <div class="indicator-light gray" id="address-indicator"></div>
                <div>Address</div>
            </div>
        </div>
        
        <div class="log-container">
            <h3>Upload Log</h3>
            <div id="log"></div>
        </div>
    </div>
    
    <div id="notification" style="display: none;" class="notification"></div>
    
    <script>
        let isUploading = false;
        let updateInterval;
        
        function showNotification(message) {
            const notif = document.getElementById('notification');
            notif.textContent = message;
            notif.style.display = 'block';
            setTimeout(() => {
                notif.style.display = 'none';
            }, 3000);
        }
        
        function updateUI(data) {
            // Update progress
            document.getElementById('progress').style.width = data.progress + '%';
            document.getElementById('progress').textContent = Math.round(data.progress) + '%';
            
            // Update status
            if (data.is_uploading) {
                document.getElementById('status').textContent = 'Status: Uploading...';
            } else if (data.progress >= 100) {
                document.getElementById('status').textContent = 'Status: Upload Complete!';
            } else {
                document.getElementById('status').textContent = 'Status: Ready to Upload';
            }
            
            // Update current field
            document.getElementById('fieldName').textContent = data.current_field || 'None';
            
            // Update buttons
            const startBtn = document.getElementById('startBtn');
            const pauseBtn = document.getElementById('pauseBtn');
            
            if (data.is_uploading) {
                startBtn.textContent = 'Stop Upload';
                startBtn.classList.remove('btn-primary');
                startBtn.classList.add('btn-stop');
                pauseBtn.disabled = false;
            } else {
                startBtn.textContent = 'Start Auto Upload';
                startBtn.classList.remove('btn-stop');
                startBtn.classList.add('btn-primary');
                pauseBtn.disabled = true;
            }
            
            if (data.is_paused) {
                pauseBtn.textContent = 'Resume';
            } else {
                pauseBtn.textContent = 'Pause';
            }
            
            // Update log
            const logDiv = document.getElementById('log');
            logDiv.innerHTML = '';
            data.log.slice(-20).reverse().forEach(entry => {
                const div = document.createElement('div');
                div.className = 'log-entry ' + entry.type;
                div.textContent = '[' + entry.time + '] ' + entry.message;
                logDiv.appendChild(div);
            });
            
            // Update indicators
            if (data.current_section) {
                document.querySelectorAll('.indicator-light').forEach(light => {
                    light.className = 'indicator-light gray';
                });
                const currentIndicator = document.getElementById(data.current_section + '-indicator');
                if (currentIndicator) {
                    currentIndicator.className = 'indicator-light yellow';
                }
            }
            
            // Update completed indicators
            data.completed_sections?.forEach(section => {
                const indicator = document.getElementById(section + '-indicator');
                if (indicator) {
                    indicator.className = 'indicator-light green';
                }
            });
        }
        
        function toggleUpload() {
            if (isUploading) {
                fetch('/stop_upload', { method: 'POST' })
                    .then(() => {
                        isUploading = false;
                        showNotification('Upload stopped');
                    });
            } else {
                fetch('/start_upload', { method: 'POST' })
                    .then(() => {
                        isUploading = true;
                        showNotification('Upload started');
                    });
            }
        }
        
        function togglePause() {
            fetch('/toggle_pause', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    showNotification(data.is_paused ? 'Upload paused' : 'Upload resumed');
                });
        }
        
        // Update UI every 500ms
        function startUpdates() {
            updateInterval = setInterval(() => {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => updateUI(data));
            }, 500);
        }
        
        // Start updates when page loads
        window.onload = () => {
            startUpdates();
            fetch('/status')
                .then(response => response.json())
                .then(data => updateUI(data));
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    return jsonify(upload_state)

@app.route('/start_upload', methods=['POST'])
def start_upload():
    if not upload_state['is_uploading']:
        upload_state['is_uploading'] = True
        upload_state['progress'] = 0
        upload_state['uploaded_fields'] = []
        upload_state['log'] = []
        
        # Start upload in background thread
        thread = Thread(target=upload_process)
        thread.daemon = True
        thread.start()
        
        add_log('Upload started', 'success')
    return jsonify({'success': True})

@app.route('/stop_upload', methods=['POST'])
def stop_upload():
    upload_state['is_uploading'] = False
    add_log('Upload stopped', 'warning')
    return jsonify({'success': True})

@app.route('/toggle_pause', methods=['POST'])
def toggle_pause():
    upload_state['is_paused'] = not upload_state['is_paused']
    add_log('Upload paused' if upload_state['is_paused'] else 'Upload resumed', 'info')
    return jsonify({'is_paused': upload_state['is_paused']})

def add_log(message, log_type='info'):
    timestamp = time.strftime('%H:%M:%S')
    upload_state['log'].append({
        'time': timestamp,
        'message': message,
        'type': log_type
    })

def upload_process():
    """Background upload process"""
    sections = [
        ('driver_info', 'driver'),
        ('vehicle_info', 'vehicle'),
        ('coverage_preferences', 'coverage'),
        ('address_info', 'address')
    ]
    
    field_count = 0
    upload_state['completed_sections'] = []
    
    for section_name, indicator_name in sections:
        if not upload_state['is_uploading']:
            break
            
        upload_state['current_section'] = indicator_name
        section_data = quote_data.get(section_name, {})
        
        for field_name, field_value in section_data.items():
            if not upload_state['is_uploading']:
                break
                
            # Wait if paused
            while upload_state['is_paused'] and upload_state['is_uploading']:
                time.sleep(0.1)
            
            # Update current field
            upload_state['current_field'] = f"{field_name}: {field_value}"
            field_count += 1
            
            # Update progress
            upload_state['progress'] = (field_count / upload_state['total_fields']) * 100
            
            # Log upload
            add_log(f"Uploaded: {field_name} = {field_value}", 'success')
            upload_state['uploaded_fields'].append({
                'field': field_name,
                'value': field_value
            })
            
            # Simulate upload delay
            time.sleep(0.5)
        
        # Mark section as complete
        upload_state['completed_sections'].append(indicator_name)
    
    if upload_state['is_uploading'] and upload_state['progress'] >= 100:
        add_log('Upload completed successfully!', 'success')
        upload_state['current_field'] = 'Upload Complete!'
    
    upload_state['is_uploading'] = False
    upload_state['current_section'] = None

if __name__ == '__main__':
    print("\n" + "="*50)
    print("GEICO Auto Upload Web Interface")
    print("="*50)
    print(f"Starting server at http://localhost:5557")
    print("Opening browser...")
    print("="*50 + "\n")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(1)
        webbrowser.open('http://localhost:5557')
    
    browser_thread = Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    app.run(host='0.0.0.0', port=5557, debug=False)