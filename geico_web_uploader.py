#!/usr/bin/env python3
"""
GEICO Web-Based Visual Uploader
Creates a local web interface for auto-filling GEICO quotes
"""

from flask import Flask, render_template_string, jsonify, request
import json
import webbrowser
import threading
import time

app = Flask(__name__)

# HTML template with visual interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>GEICO Quote Auto-Uploader</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f0f0;
        }
        .header {
            background-color: #004B87;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .status-bar {
            background-color: #4CAF50;
            color: white;
            padding: 15px;
            text-align: center;
            font-size: 18px;
            font-weight: bold;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .section {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #004B87;
            margin-top: 0;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }
        .field-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .field-label {
            font-weight: bold;
            color: #333;
            width: 200px;
        }
        .field-value {
            flex-grow: 1;
            font-family: monospace;
            background-color: #f8f8f8;
            padding: 8px;
            border-radius: 4px;
            margin: 0 10px;
        }
        .copy-btn {
            background-color: #28a745;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        .copy-btn:hover {
            background-color: #218838;
        }
        .copy-btn.copied {
            background-color: #6c757d;
        }
        .action-buttons {
            text-align: center;
            margin: 30px 0;
        }
        .action-btn {
            background-color: #004B87;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin: 0 10px;
            transition: background-color 0.3s;
        }
        .action-btn:hover {
            background-color: #003366;
        }
        .progress-section {
            background-color: #e8f4f8;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
        }
        .progress-bar {
            background-color: #e0e0e0;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            background-color: #004B87;
            height: 100%;
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #28a745;
            color: white;
            padding: 15px 25px;
            border-radius: 5px;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚗 GEICO Quote Auto-Uploader</h1>
        <p>Automatically fill GEICO insurance quotes with test data</p>
    </div>
    
    <div class="status-bar">
        ✅ Quote Data Loaded Successfully! Ready to auto-fill.
    </div>
    
    <div class="container">
        <div class="action-buttons">
            <button class="action-btn" onclick="openGeico()">🌐 Open GEICO Website</button>
            <button class="action-btn" onclick="showInstructions()">📋 Instructions</button>
        </div>
        
        <div class="progress-section">
            <h3>Copy Progress</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <p id="progressText">0 / 0 fields copied</p>
        </div>
        
        <div class="section">
            <h2>🚛 Vehicle Information</h2>
            <div class="field-row">
                <span class="field-label">Year:</span>
                <span class="field-value">{{ data.vehicle.year }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.vehicle.year }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Make:</span>
                <span class="field-value">{{ data.vehicle.make }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.vehicle.make }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Model:</span>
                <span class="field-value">{{ data.vehicle.model }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.vehicle.model }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Trim:</span>
                <span class="field-value">{{ data.vehicle.trim }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.vehicle.trim }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">VIN:</span>
                <span class="field-value">{{ data.vehicle.vin }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.vehicle.vin }}', this)">📋 Copy</button>
            </div>
        </div>
        
        <div class="section">
            <h2>👤 Driver Information</h2>
            <div class="field-row">
                <span class="field-label">First Name:</span>
                <span class="field-value">{{ data.driver.first_name }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.first_name }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Last Name:</span>
                <span class="field-value">{{ data.driver.last_name }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.last_name }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Date of Birth:</span>
                <span class="field-value">{{ data.driver.date_of_birth }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.date_of_birth }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Email:</span>
                <span class="field-value">{{ data.driver.email }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.email }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">Phone:</span>
                <span class="field-value">{{ data.driver.phone }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.phone }}', this)">📋 Copy</button>
            </div>
        </div>
        
        <div class="section">
            <h2>🏠 Address</h2>
            <div class="field-row">
                <span class="field-label">Street:</span>
                <span class="field-value">{{ data.driver.address.street }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.address.street }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">City:</span>
                <span class="field-value">{{ data.driver.address.city }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.address.city }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">State:</span>
                <span class="field-value">{{ data.driver.address.state }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.address.state }}', this)">📋 Copy</button>
            </div>
            <div class="field-row">
                <span class="field-label">ZIP:</span>
                <span class="field-value">{{ data.driver.address.zip }}</span>
                <button class="copy-btn" onclick="copyToClipboard('{{ data.driver.address.zip }}', this)">📋 Copy</button>
            </div>
        </div>
    </div>
    
    <div class="notification" id="notification">
        Value copied to clipboard!
    </div>
    
    <script>
        let copiedCount = 0;
        const totalFields = document.querySelectorAll('.copy-btn').length;
        
        function copyToClipboard(text, button) {
            navigator.clipboard.writeText(text).then(function() {
                // Update button state
                if (!button.classList.contains('copied')) {
                    button.classList.add('copied');
                    button.textContent = '✅ Copied';
                    copiedCount++;
                    updateProgress();
                }
                
                // Show notification
                const notification = document.getElementById('notification');
                notification.style.display = 'block';
                notification.textContent = `'${text}' copied to clipboard!`;
                setTimeout(() => {
                    notification.style.display = 'none';
                }, 2000);
            });
        }
        
        function updateProgress() {
            const percentage = Math.round((copiedCount / totalFields) * 100);
            document.getElementById('progressFill').style.width = percentage + '%';
            document.getElementById('progressFill').textContent = percentage + '%';
            document.getElementById('progressText').textContent = `${copiedCount} / ${totalFields} fields copied`;
        }
        
        function openGeico() {
            window.open('https://www.geico.com/auto-insurance-quote/', '_blank');
        }
        
        function showInstructions() {
            alert(`How to use the GEICO Quote Auto-Uploader:

1. Click 'Open GEICO Website' to open the quote form
2. Click the 'Copy' button next to each field
3. Paste the value into the GEICO form field
4. The progress bar shows your completion status

All data is test data for a 2021 Ford F-150.`);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main page"""
    try:
        with open('truck_quote_example.json', 'r') as f:
            data = json.load(f)
        return render_template_string(HTML_TEMPLATE, data=data)
    except Exception as e:
        return f"Error loading data: {e}", 500

def open_browser():
    """Open the browser after server starts"""
    time.sleep(1)
    webbrowser.open('http://localhost:5556')

if __name__ == '__main__':
    print("Starting GEICO Web Uploader...")
    print("Opening browser at http://localhost:5556")
    
    # Start browser opening in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5556, debug=False)