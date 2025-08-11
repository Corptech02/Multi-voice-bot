#!/usr/bin/env python3
import os
import time
import logging
import json
from datetime import datetime
from pathlib import Path
import pyautogui
from flask import Flask, send_file, jsonify, render_template_string
import threading
import queue

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCAN_DIR = Path("scanned_quarters")
SCAN_DIR.mkdir(exist_ok=True)

scan_queue = queue.Queue()
scan_history = []

class AutoQuarterScanner:
    def __init__(self, interval=15):
        self.interval = interval
        self.running = False
        self.scan_thread = None
        
    def start(self):
        if not self.running:
            self.running = True
            self.scan_thread = threading.Thread(target=self._scan_loop)
            self.scan_thread.daemon = True
            self.scan_thread.start()
            logger.info("Auto scanner started with %d second interval", self.interval)
    
    def stop(self):
        self.running = False
        if self.scan_thread:
            self.scan_thread.join()
        logger.info("Auto scanner stopped")
    
    def _scan_loop(self):
        while self.running:
            self.capture_quarter()
            time.sleep(self.interval)
    
    def capture_quarter(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quarter_{timestamp}.png"
            filepath = SCAN_DIR / filename
            
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size
            quarter_width = width // 2
            quarter_height = height // 2
            
            quarter_screenshot = screenshot.crop((0, 0, quarter_width, quarter_height))
            quarter_screenshot.save(filepath)
            
            scan_data = {
                'timestamp': timestamp,
                'filename': filename,
                'path': str(filepath),
                'size': os.path.getsize(filepath),
                'dimensions': f"{quarter_width}x{quarter_height}"
            }
            
            scan_history.append(scan_data)
            scan_queue.put(scan_data)
            
            logger.info("Captured quarter screenshot: %s", filename)
            return scan_data
            
        except Exception as e:
            logger.error("Error capturing screenshot: %s", str(e))
            return None

scanner = AutoQuarterScanner()

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Auto Quarter Scanner</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .scan-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .scan-item { border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
            .scan-item img { max-width: 100%; height: auto; }
            .controls { margin-bottom: 20px; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>Auto Quarter Scanner</h1>
        <div class="controls">
            <button onclick="startScanner()">Start Scanner</button>
            <button onclick="stopScanner()">Stop Scanner</button>
            <button onclick="manualScan()">Manual Scan</button>
            <button onclick="refreshScans()">Refresh</button>
        </div>
        <div id="status"></div>
        <h2>Recent Scans</h2>
        <div id="scans" class="scan-grid"></div>
        
        <script>
            function startScanner() {
                fetch('/api/start').then(r => r.json()).then(data => {
                    document.getElementById('status').innerHTML = data.message;
                    refreshScans();
                });
            }
            
            function stopScanner() {
                fetch('/api/stop').then(r => r.json()).then(data => {
                    document.getElementById('status').innerHTML = data.message;
                });
            }
            
            function manualScan() {
                fetch('/api/scan').then(r => r.json()).then(data => {
                    document.getElementById('status').innerHTML = 'Manual scan completed';
                    refreshScans();
                });
            }
            
            function refreshScans() {
                fetch('/api/scans').then(r => r.json()).then(data => {
                    const container = document.getElementById('scans');
                    container.innerHTML = data.scans.map(scan => `
                        <div class="scan-item">
                            <img src="/scan/${scan.filename}" alt="${scan.filename}">
                            <p><strong>${scan.filename}</strong></p>
                            <p>Time: ${scan.timestamp}</p>
                            <p>Size: ${scan.dimensions}</p>
                        </div>
                    `).join('');
                });
            }
            
            refreshScans();
            setInterval(refreshScans, 5000);
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/start')
def api_start():
    scanner.start()
    return jsonify({'status': 'success', 'message': 'Scanner started'})

@app.route('/api/stop')
def api_stop():
    scanner.stop()
    return jsonify({'status': 'success', 'message': 'Scanner stopped'})

@app.route('/api/scan')
def api_manual_scan():
    scan_data = scanner.capture_quarter()
    return jsonify({'status': 'success', 'scan': scan_data})

@app.route('/api/scans')
def api_get_scans():
    recent_scans = scan_history[-20:][::-1]
    return jsonify({'scans': recent_scans})

@app.route('/scan/<filename>')
def serve_scan(filename):
    filepath = SCAN_DIR / filename
    if filepath.exists():
        return send_file(filepath, mimetype='image/png')
    return "Not found", 404

@app.route('/api/scan/<filename>')
def api_scan_info(filename):
    for scan in scan_history:
        if scan['filename'] == filename:
            return jsonify(scan)
    return jsonify({'error': 'Scan not found'}), 404

if __name__ == '__main__':
    logger.info("Starting Auto Quarter Scanner Server on http://localhost:5555")
    app.run(host='0.0.0.0', port=5555, debug=False)