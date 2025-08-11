#!/usr/bin/env python3
import os
import time
import logging
import json
from datetime import datetime
from pathlib import Path
import pyautogui
from flask import Flask, jsonify, render_template_string, request
import threading
import queue
import webbrowser

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCAN_DIR = Path("movie_scans")
SCAN_DIR.mkdir(exist_ok=True)

movie_queue = queue.Queue()
scan_results = []

class MovieQuarterScanner:
    def __init__(self):
        self.processing = False
        self.process_thread = None
        
    def start_processing(self):
        if not self.processing:
            self.processing = True
            self.process_thread = threading.Thread(target=self._process_queue)
            self.process_thread.daemon = True
            self.process_thread.start()
            logger.info("Movie scanner processing started")
    
    def stop_processing(self):
        self.processing = False
        if self.process_thread:
            self.process_thread.join()
        logger.info("Movie scanner processing stopped")
    
    def _process_queue(self):
        while self.processing:
            try:
                if not movie_queue.empty():
                    movie_data = movie_queue.get(timeout=1)
                    self._process_movie(movie_data)
                else:
                    time.sleep(1)
            except queue.Empty:
                time.sleep(1)
            except Exception as e:
                logger.error("Error in processing queue: %s", str(e))
    
    def _process_movie(self, movie_data):
        try:
            url = movie_data['url']
            logger.info("Opening movie URL: %s", url)
            
            # Open the URL in default browser
            webbrowser.open(url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Capture quarter screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"movie_{timestamp}.png"
            filepath = SCAN_DIR / filename
            
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size
            quarter_width = width // 2
            quarter_height = height // 2
            
            # Capture top-left quarter
            quarter_screenshot = screenshot.crop((0, 0, quarter_width, quarter_height))
            quarter_screenshot.save(filepath)
            
            result = {
                'id': movie_data['id'],
                'url': url,
                'timestamp': timestamp,
                'filename': filename,
                'path': str(filepath),
                'size': os.path.getsize(filepath),
                'dimensions': f"{quarter_width}x{quarter_height}",
                'status': 'completed'
            }
            
            scan_results.append(result)
            logger.info("Captured movie screenshot: %s", filename)
            
        except Exception as e:
            logger.error("Error processing movie URL %s: %s", movie_data['url'], str(e))
            result = {
                'id': movie_data['id'],
                'url': movie_data['url'],
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'status': 'error',
                'error': str(e)
            }
            scan_results.append(result)

scanner = MovieQuarterScanner()

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Movie URL Quarter Scanner</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            .url-input-section {
                background: #f0f0f0;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            input[type="url"] {
                width: 70%;
                padding: 10px;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            button {
                padding: 10px 20px;
                margin: 5px;
                cursor: pointer;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            button:hover {
                background: #0056b3;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                display: none;
            }
            .status.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
                display: block;
            }
            .status.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
                display: block;
            }
            .scan-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .scan-item {
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 5px;
                background: #fff;
            }
            .scan-item img {
                max-width: 100%;
                height: auto;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            .scan-item.error {
                background: #fee;
            }
            .info-panel {
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .network-info {
                font-family: monospace;
                background: #333;
                color: #0f0;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Movie URL Quarter Scanner</h1>
            
            <div class="info-panel">
                <h3>Network Access Information</h3>
                <p>To access this scanner from another computer on your network:</p>
                <div class="network-info" id="network-info">
                    Loading network information...
                </div>
            </div>
            
            <div class="url-input-section">
                <h2>Submit Movie URL</h2>
                <input type="url" id="movieUrl" placeholder="Enter movie URL (e.g., https://example.com/movie)" />
                <button onclick="submitUrl()">Scan URL</button>
                <button onclick="startScanner()">Start Processing</button>
                <button onclick="stopScanner()">Stop Processing</button>
                <div id="status" class="status"></div>
            </div>
            
            <h2>Scan Results</h2>
            <button onclick="refreshScans()">Refresh Results</button>
            <div id="scans" class="scan-grid"></div>
        </div>
        
        <script>
            // Get network info on load
            fetch('/api/network-info').then(r => r.json()).then(data => {
                document.getElementById('network-info').innerHTML = 
                    `Access this scanner from: http://${data.ip}:5556`;
            });
            
            function submitUrl() {
                const url = document.getElementById('movieUrl').value;
                if (!url) {
                    showStatus('Please enter a URL', 'error');
                    return;
                }
                
                fetch('/api/submit-url', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                }).then(r => r.json()).then(data => {
                    if (data.status === 'success') {
                        showStatus('URL submitted successfully!', 'success');
                        document.getElementById('movieUrl').value = '';
                        refreshScans();
                    } else {
                        showStatus('Error: ' + data.message, 'error');
                    }
                });
            }
            
            function startScanner() {
                fetch('/api/start').then(r => r.json()).then(data => {
                    showStatus(data.message, 'success');
                });
            }
            
            function stopScanner() {
                fetch('/api/stop').then(r => r.json()).then(data => {
                    showStatus(data.message, 'success');
                });
            }
            
            function showStatus(message, type) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = 'status ' + type;
                setTimeout(() => {
                    status.style.display = 'none';
                }, 5000);
            }
            
            function refreshScans() {
                fetch('/api/scans').then(r => r.json()).then(data => {
                    const container = document.getElementById('scans');
                    container.innerHTML = data.scans.map(scan => {
                        if (scan.status === 'error') {
                            return `
                                <div class="scan-item error">
                                    <h4>Error Processing URL</h4>
                                    <p><strong>URL:</strong> ${scan.url}</p>
                                    <p><strong>Error:</strong> ${scan.error}</p>
                                    <p><strong>Time:</strong> ${scan.timestamp}</p>
                                </div>
                            `;
                        } else {
                            return `
                                <div class="scan-item">
                                    <img src="/scan/${scan.filename}" alt="${scan.filename}">
                                    <p><strong>URL:</strong> ${scan.url}</p>
                                    <p><strong>Time:</strong> ${scan.timestamp}</p>
                                    <p><strong>Size:</strong> ${scan.dimensions}</p>
                                </div>
                            `;
                        }
                    }).join('');
                });
            }
            
            // Auto-refresh every 5 seconds
            setInterval(refreshScans, 5000);
            refreshScans();
            
            // Enter key submits URL
            document.getElementById('movieUrl').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    submitUrl();
                }
            });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/network-info')
def api_network_info():
    import socket
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return jsonify({'hostname': hostname, 'ip': ip})

@app.route('/api/submit-url', methods=['POST'])
def api_submit_url():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'status': 'error', 'message': 'URL is required'})
        
        movie_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        movie_data = {
            'id': movie_id,
            'url': url,
            'submitted_at': datetime.now().isoformat()
        }
        
        movie_queue.put(movie_data)
        logger.info("URL submitted to queue: %s", url)
        
        return jsonify({'status': 'success', 'message': 'URL queued for processing', 'id': movie_id})
        
    except Exception as e:
        logger.error("Error submitting URL: %s", str(e))
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/start')
def api_start():
    scanner.start_processing()
    return jsonify({'status': 'success', 'message': 'Scanner started'})

@app.route('/api/stop')
def api_stop():
    scanner.stop_processing()
    return jsonify({'status': 'success', 'message': 'Scanner stopped'})

@app.route('/api/scans')
def api_get_scans():
    recent_scans = scan_results[-20:][::-1]  # Last 20 scans, newest first
    return jsonify({'scans': recent_scans})

@app.route('/scan/<filename>')
def serve_scan(filename):
    filepath = SCAN_DIR / filename
    if filepath.exists():
        from flask import send_file
        return send_file(filepath, mimetype='image/png')
    return "Not found", 404

if __name__ == '__main__':
    logger.info("Starting Movie URL Scanner Server on http://0.0.0.0:5556")
    print("\n" + "="*60)
    print("Movie URL Quarter Scanner")
    print("="*60)
    print("Server starting on: http://0.0.0.0:5556")
    print("Access from other computers on network using your IP address")
    print("="*60 + "\n")
    
    # Start the processing thread
    scanner.start_processing()
    
    # Run the web server
    app.run(host='0.0.0.0', port=5556, debug=False)