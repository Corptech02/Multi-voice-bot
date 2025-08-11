#!/usr/bin/env python3
import os
import time
import logging
import json
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, send_file, jsonify, render_template_string, request
import threading
import queue
import base64
from PIL import Image
from io import BytesIO

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
            self.capture_screenshot()
            time.sleep(self.interval)
    
    def capture_screenshot(self):
        """Capture a screenshot and save it"""
        try:
            # Check if we have a display
            if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
                logger.warning("No display detected. Auto scanner is running in headless mode.")
                logger.warning("Screenshots can only be captured when running with a display.")
                logger.info("Please use the upload functionality or run the scanner on a system with a display.")
                return None
            
            import subprocess
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quarter_{timestamp}.png"
            filepath = SCAN_DIR / filename
            
            # Try different screenshot methods based on availability
            screenshot_captured = False
            error_messages = []
            
            # Method 1: Try gnome-screenshot
            try:
                result = subprocess.run(['gnome-screenshot', '-f', str(filepath)], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0 and filepath.exists():
                    screenshot_captured = True
                    logger.info("Screenshot captured using gnome-screenshot")
                else:
                    error_messages.append(f"gnome-screenshot failed: {result.stderr.decode('utf-8', errors='ignore')}")
            except FileNotFoundError:
                error_messages.append("gnome-screenshot not installed")
            except Exception as e:
                error_messages.append(f"gnome-screenshot error: {str(e)}")
            
            # Method 2: Try import (ImageMagick)
            if not screenshot_captured:
                try:
                    result = subprocess.run(['import', '-window', 'root', str(filepath)], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0 and filepath.exists():
                        screenshot_captured = True
                        logger.info("Screenshot captured using import (ImageMagick)")
                    else:
                        error_messages.append(f"import failed: {result.stderr.decode('utf-8', errors='ignore')}")
                except FileNotFoundError:
                    error_messages.append("ImageMagick (import) not installed")
                except Exception as e:
                    error_messages.append(f"import error: {str(e)}")
            
            # Method 3: Try scrot
            if not screenshot_captured:
                try:
                    result = subprocess.run(['scrot', str(filepath)], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0 and filepath.exists():
                        screenshot_captured = True
                        logger.info("Screenshot captured using scrot")
                    else:
                        error_messages.append(f"scrot failed: {result.stderr.decode('utf-8', errors='ignore')}")
                except FileNotFoundError:
                    error_messages.append("scrot not installed")
                except Exception as e:
                    error_messages.append(f"scrot error: {str(e)}")
            
            if not screenshot_captured:
                logger.error("No screenshot tool could capture the screen.")
                logger.error("Errors: %s", "; ".join(error_messages))
                logger.error("Please install one of: gnome-screenshot, scrot, or ImageMagick (import command)")
                logger.error("On Ubuntu/Debian: sudo apt-get install gnome-screenshot scrot imagemagick")
                return None
            
            # Process the captured screenshot to get quarter
            img = Image.open(filepath)
            width, height = img.size
            quarter_width = width // 2
            quarter_height = height // 2
            
            # Crop to upper-left quarter
            quarter_img = img.crop((0, 0, quarter_width, quarter_height))
            quarter_img.save(filepath)
            
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
    
    def process_uploaded_image(self, image_data, filename=None):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not filename:
                filename = f"quarter_{timestamp}.png"
            filepath = SCAN_DIR / filename
            
            # Decode base64 image if necessary
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
                image_data = base64.b64decode(image_data)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Get image dimensions
            img = Image.open(filepath)
            width, height = img.size
            
            scan_data = {
                'timestamp': timestamp,
                'filename': filename,
                'path': str(filepath),
                'size': os.path.getsize(filepath),
                'dimensions': f"{width}x{height}"
            }
            
            scan_history.append(scan_data)
            scan_queue.put(scan_data)
            
            logger.info("Processed uploaded image: %s", filename)
            return scan_data
            
        except Exception as e:
            logger.error("Error processing uploaded image: %s", str(e))
            return None

scanner = AutoQuarterScanner()

# Check if we're in headless mode
IS_HEADLESS = not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))

@app.route('/')
def index():
    headless_warning = ''
    if IS_HEADLESS:
        headless_warning = '<p style="font-size: 14px; color: #ffeb3b;">⚠️ Running in headless mode - Screenshot capture is not available. Please use the upload functionality.</p>'
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Auto Quarter Scanner</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .scan-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
            .scan-item {{ background: white; border: 1px solid #ddd; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .scan-item img {{ max-width: 100%; height: auto; border-radius: 5px; }}
            .controls {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .upload-area {{ border: 2px dashed #2196F3; padding: 40px; text-align: center; margin: 20px 0; border-radius: 8px; background-color: #e3f2fd; }}
            .upload-area.dragover {{ background-color: #bbdefb; }}
            button {{ padding: 10px 20px; margin: 5px; cursor: pointer; background-color: #2196F3; color: white; border: none; border-radius: 5px; font-size: 16px; }}
            button:hover {{ background-color: #1976D2; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .status.success {{ background-color: #c8e6c9; color: #2e7d32; }}
            .status.error {{ background-color: #ffcdd2; color: #c62828; }}
            input[type="file"] {{ display: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Auto Quarter Scanner</h1>
                <p>Upload images or use auto-scan functionality</p>
                {headless_warning}
            </div>
            
            <div class="controls">
                <h2>Scanner Controls</h2>
                <button onclick="startScanner()">Start Auto Scanner</button>
                <button onclick="stopScanner()">Stop Auto Scanner</button>
                <button onclick="manualScan()">Manual Scan</button>
                <button onclick="refreshScans()">Refresh</button>
                
                <div class="upload-area" id="uploadArea">
                    <h3>Upload Quarter Images</h3>
                    <p>Drag and drop images here or click to select</p>
                    <input type="file" id="fileInput" accept="image/*" multiple onchange="handleFileSelect(event)">
                    <button onclick="document.getElementById('fileInput').click()">Select Files</button>
                </div>
            </div>
            
            <div id="status"></div>
            
            <h2>Recent Scans</h2>
            <div id="scans" class="scan-grid"></div>
        </div>
        
        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            
            // Drag and drop functionality
            uploadArea.addEventListener('dragover', (e) => {{
                e.preventDefault();
                uploadArea.classList.add('dragover');
            }});
            
            uploadArea.addEventListener('dragleave', () => {{
                uploadArea.classList.remove('dragover');
            }});
            
            uploadArea.addEventListener('drop', (e) => {{
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            }});
            
            function handleFileSelect(event) {{
                handleFiles(event.target.files);
            }}
            
            function handleFiles(files) {{
                Array.from(files).forEach(file => {{
                    if (file.type.startsWith('image/')) {{
                        uploadImage(file);
                    }}
                }});
            }}
            
            function uploadImage(file) {{
                const reader = new FileReader();
                reader.onload = function(e) {{
                    fetch('/api/upload', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            image: e.target.result,
                            filename: file.name
                        }})
                    }})
                    .then(r => r.json())
                    .then(data => {{
                        showStatus('Image uploaded successfully', 'success');
                        refreshScans();
                    }})
                    .catch(err => {{
                        showStatus('Upload failed: ' + err, 'error');
                    }});
                }};
                reader.readAsDataURL(file);
            }}
            
            function showStatus(message, type) {{
                const status = document.getElementById('status');
                status.innerHTML = '<div class="status ' + type + '">' + message + '</div>';
                setTimeout(() => status.innerHTML = '', 5000);
            }}
            
            function startScanner() {{
                fetch('/api/start').then(r => r.json()).then(data => {{
                    showStatus(data.message, data.status === 'warning' ? 'error' : 'success');
                    if (data.status === 'success') {{
                        refreshScans();
                    }}
                }});
            }}
            
            function stopScanner() {{
                fetch('/api/stop').then(r => r.json()).then(data => {{
                    showStatus(data.message, 'success');
                }});
            }}
            
            function manualScan() {{
                showStatus('Capturing screenshot...', 'success');
                fetch('/api/scan').then(r => r.json()).then(data => {{
                    if (data.status === 'success') {{
                        showStatus('Screenshot captured successfully', 'success');
                        refreshScans();
                    }} else {{
                        showStatus('Failed to capture screenshot: ' + (data.message || 'Unknown error'), 'error');
                    }}
                }}).catch(err => {{
                    showStatus('Error capturing screenshot: ' + err, 'error');
                }});
            }}
            
            function refreshScans() {{
                fetch('/api/scans').then(r => r.json()).then(data => {{
                    const container = document.getElementById('scans');
                    container.innerHTML = data.scans.map(scan => 
                        '<div class="scan-item">' +
                            '<img src="/scan/' + scan.filename + '" alt="' + scan.filename + '">' +
                            '<p><strong>' + scan.filename + '</strong></p>' +
                            '<p>Time: ' + scan.timestamp + '</p>' +
                            '<p>Size: ' + scan.dimensions + '</p>' +
                            '<p>File size: ' + (scan.size / 1024).toFixed(2) + ' KB</p>' +
                        '</div>'
                    ).join('');
                }});
            }}
            
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
    if IS_HEADLESS:
        return jsonify({
            'status': 'warning', 
            'message': 'Scanner started in headless mode - screenshot capture not available. Use upload instead.'
        })
    return jsonify({'status': 'success', 'message': 'Scanner started'})

@app.route('/api/stop')
def api_stop():
    scanner.stop()
    return jsonify({'status': 'success', 'message': 'Scanner stopped'})

@app.route('/api/scan')
def api_manual_scan():
    """Manual scan endpoint"""
    scan_data = scanner.capture_screenshot()
    if scan_data:
        return jsonify({'status': 'success', 'scan': scan_data})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to capture screenshot'}), 500

@app.route('/api/upload', methods=['POST'])
def api_upload():
    try:
        data = request.json
        image_data = data.get('image')
        filename = data.get('filename')
        
        scan_data = scanner.process_uploaded_image(image_data, filename)
        if scan_data:
            return jsonify({'status': 'success', 'scan': scan_data})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process image'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
    logger.info("Starting Auto Quarter Scanner Server on http://0.0.0.0:5557")
    print("\n" + "="*60)
    print("Auto Quarter Scanner Web Server")
    print("="*60)
    print(f"Access from this computer: http://localhost:5557")
    print(f"Access from other computers on network: http://192.168.40.232:5557")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5557, debug=False)