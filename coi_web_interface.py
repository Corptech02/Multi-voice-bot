#!/usr/bin/env python3
from flask import Flask, render_template_string, jsonify, request
import requests
from datetime import datetime
import os

app = Flask(__name__)

# COI Backend URL
COI_BACKEND_URL = os.environ.get('COI_BACKEND_URL', 'http://localhost:8001')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>COI Request Tool</title>
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
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .status { 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 5px;
            background: #e8f5e9;
        }
        .request-card {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            background: #fafafa;
        }
        .monitoring-status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }
        .active { 
            background: #4CAF50; 
            color: white; 
        }
        .inactive { 
            background: #f44336; 
            color: white; 
        }
        button {
            background: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover {
            background: #1976D2;
        }
        .refresh-btn {
            background: #4CAF50;
        }
        .refresh-btn:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>COI Request Management Tool</h1>
        
        <div class="status">
            <h3>Email Monitoring Status: 
                <span id="monitoring-status" class="monitoring-status">Loading...</span>
            </h3>
            <button onclick="toggleMonitoring()">Toggle Monitoring</button>
            <button class="refresh-btn" onclick="loadRequests()">Refresh Requests</button>
        </div>
        
        <h2>COI Requests</h2>
        <div id="requests-container">
            Loading requests...
        </div>
    </div>

    <script>
        function loadRequests() {
            fetch('/api/requests')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('requests-container');
                    if (data.requests && data.requests.length > 0) {
                        container.innerHTML = data.requests.map(req => `
                            <div class="request-card">
                                <h4>Request ID: ${req.id}</h4>
                                <p><strong>Agency:</strong> ${req.agency_name}</p>
                                <p><strong>Insured:</strong> ${req.insured_name}</p>
                                <p><strong>Status:</strong> ${req.status}</p>
                                <p><strong>Received:</strong> ${req.timestamp}</p>
                                <p><strong>Email From:</strong> ${req.email_from || 'N/A'}</p>
                            </div>
                        `).join('');
                    } else {
                        container.innerHTML = '<p>No COI requests found.</p>';
                    }
                })
                .catch(err => {
                    document.getElementById('requests-container').innerHTML = 
                        '<p style="color: red;">Error loading requests: ' + err + '</p>';
                });
        }

        function checkMonitoringStatus() {
            fetch('/api/monitoring-status')
                .then(r => r.json())
                .then(data => {
                    const statusEl = document.getElementById('monitoring-status');
                    if (data.monitoring_active) {
                        statusEl.textContent = 'ACTIVE';
                        statusEl.className = 'monitoring-status active';
                    } else {
                        statusEl.textContent = 'INACTIVE';
                        statusEl.className = 'monitoring-status inactive';
                    }
                })
                .catch(() => {
                    document.getElementById('monitoring-status').textContent = 'ERROR';
                    document.getElementById('monitoring-status').className = 'monitoring-status inactive';
                });
        }

        function toggleMonitoring() {
            fetch('/api/toggle-monitoring', { method: 'POST' })
                .then(r => r.json())
                .then(() => {
                    checkMonitoringStatus();
                    loadRequests();
                })
                .catch(err => alert('Error toggling monitoring: ' + err));
        }

        // Initial load
        loadRequests();
        checkMonitoringStatus();

        // Auto-refresh every 10 seconds
        setInterval(() => {
            loadRequests();
            checkMonitoringStatus();
        }, 10000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/requests')
def get_requests():
    try:
        response = requests.get(f'{COI_BACKEND_URL}/requests', timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e), 'requests': []})

@app.route('/api/monitoring-status')
def monitoring_status():
    try:
        response = requests.get(f'{COI_BACKEND_URL}/monitoring-status', timeout=5)
        return jsonify(response.json())
    except:
        return jsonify({'monitoring_active': False})

@app.route('/api/toggle-monitoring', methods=['POST'])
def toggle_monitoring():
    try:
        response = requests.post(f'{COI_BACKEND_URL}/toggle-monitoring', timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print(f"Starting COI Web Interface on http://0.0.0.0:5000")
    print(f"Backend URL: {COI_BACKEND_URL}")
    app.run(host='0.0.0.0', port=5000, debug=True)