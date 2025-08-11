from flask import Flask, render_template, jsonify, request, send_file
import requests
import base64
import time
import os
import json

app = Flask(__name__)

# Load mock data
try:
    with open('truck_quote_example.json', 'r') as f:
        truck_data = json.load(f)
except FileNotFoundError:
    truck_data = {}

# Scanner state
scanner_active = False
current_field_index = 0
captured_screenshots = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scanner', methods=['POST'])
def start_scanner():
    global scanner_active, current_field_index, captured_screenshots
    scanner_active = True
    current_field_index = 0
    captured_screenshots = []
    return jsonify({'status': 'started', 'message': 'Auto scanner started'})

@app.route('/stop_scanner', methods=['POST'])
def stop_scanner():
    global scanner_active
    scanner_active = False
    return jsonify({'status': 'stopped'})

@app.route('/capture_screenshot', methods=['POST'])
def capture_screenshot():
    """Capture a mock screenshot of GEICO site"""
    try:
        # Create a mock HTML representation that looks like a screenshot
        mock_html = """
        <div style="width: 1200px; height: 800px; background: white; font-family: Arial;">
            <div style="background: #004B87; color: white; padding: 20px;">
                <h2>GEICO Auto Insurance Quote</h2>
            </div>
            <div style="padding: 40px;">
                <h3>Vehicle Information</h3>
                <input style="width: 500px; padding: 10px; margin: 10px 0;" value="2024 Ford F-150" readonly>
                <h3>Driver Information</h3>
                <input style="width: 500px; padding: 10px; margin: 10px 0;" value="John Doe" readonly>
            </div>
        </div>
        """
        
        # For now, we'll return a placeholder that indicates a screenshot was captured
        screenshot_data = {
            'type': 'mock_screenshot',
            'html': mock_html,
            'timestamp': time.time()
        }
        
        captured_screenshots.append(screenshot_data)
        
        return jsonify({
            'status': 'success',
            'screenshot': screenshot_data,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload_field', methods=['POST'])
def upload_field():
    """Process field upload from the scanner"""
    global current_field_index
    
    try:
        # Get the field being uploaded
        field_names = list(truck_data.keys())
        if current_field_index < len(field_names):
            field_name = field_names[current_field_index]
            field_value = truck_data[field_name]
            
            # Simulate processing delay
            time.sleep(0.5)
            
            # Generate a mock screenshot showing this field being filled
            mock_html = f"""
            <div style="width: 1200px; height: 800px; background: white; font-family: Arial;">
                <div style="background: #004B87; color: white; padding: 20px;">
                    <h2>GEICO Auto Insurance Quote</h2>
                </div>
                <div style="background: #FFF3CD; border: 2px solid #856404; padding: 20px; margin: 20px;">
                    <strong style="color: #856404;">Currently filling: {field_name}</strong><br>
                    <span>Value: {str(field_value)[:50]}...</span>
                </div>
                <div style="padding: 40px;">
                    <h3>Progress: {field_name}</h3>
                    <div style="background: #e0e0e0; height: 30px; border-radius: 15px;">
                        <div style="background: #28a745; height: 30px; width: {progress}%; border-radius: 15px;"></div>
                    </div>
                </div>
            </div>
            """
            
            screenshot_data = {
                'type': 'mock_screenshot',
                'html': mock_html,
                'timestamp': time.time()
            }
            
            current_field_index += 1
            progress = (current_field_index / len(field_names)) * 100
            
            return jsonify({
                'status': 'success',
                'field': field_name,
                'value': field_value,
                'progress': progress,
                'screenshot': screenshot_data
            })
        else:
            return jsonify({
                'status': 'complete',
                'message': 'All fields uploaded',
                'progress': 100
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/scanner_status')
def scanner_status():
    global scanner_active, current_field_index
    field_names = list(truck_data.keys())
    progress = (current_field_index / len(field_names)) * 100 if field_names else 0
    
    return jsonify({
        'active': scanner_active,
        'progress': progress,
        'current_field': current_field_index,
        'total_fields': len(field_names)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5557, debug=True)