#!/usr/bin/env python3
"""
Simple Direct Voice Bot - Minimal version that just works
"""
from flask import Flask, render_template_string, request, jsonify
import subprocess
import ssl
from datetime import datetime

app = Flask(__name__)

# Simple HTML with clear feedback
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Direct</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        h1 {
            color: #00ff00;
        }
        .mic-button {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: 3px solid #00ff00;
            background: #0f3460;
            color: #00ff00;
            font-size: 60px;
            cursor: pointer;
            margin: 30px auto;
            display: block;
        }
        .mic-button.listening {
            background: #ff0000;
            border-color: #ff0000;
        }
        #status {
            font-size: 20px;
            margin: 20px 0;
            padding: 20px;
            background: #0f3460;
            border-radius: 10px;
            min-height: 60px;
        }
        #log {
            text-align: left;
            background: #000;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 14px;
        }
        .log-entry {
            margin: 5px 0;
        }
        .success { color: #00ff00; }
        .error { color: #ff0000; }
        .info { color: #00ffff; }
        button {
            background: #27ae60;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Voice Direct</h1>
        
        <button onclick="testConnection()">Test Connection</button>
        <button onclick="clearLog()">Clear Log</button>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div id="status">Click microphone to start</div>
        
        <div id="log"></div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        
        function log(message, type = 'info') {
            const logDiv = document.getElementById('log');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            const time = new Date().toLocaleTimeString();
            entry.textContent = `[${time}] ${message}`;
            logDiv.appendChild(entry);
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function updateStatus(text) {
            document.getElementById('status').textContent = text;
        }
        
        // Test connection
        async function testConnection() {
            log('Testing connection...', 'info');
            try {
                const response = await fetch('/test', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    log('✅ Connection test successful!', 'success');
                    updateStatus('Test message sent - check your terminal!');
                } else {
                    log('❌ Test failed: ' + data.error, 'error');
                }
            } catch (err) {
                log('❌ Network error: ' + err.message, 'error');
            }
        }
        
        function clearLog() {
            document.getElementById('log').innerHTML = '';
            log('Log cleared', 'info');
        }
        
        // Initialize speech recognition
        function initSpeechRecognition() {
            log('Initializing speech recognition...', 'info');
            
            if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
                log('❌ Speech recognition not supported!', 'error');
                document.getElementById('micButton').disabled = true;
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                log('🎤 Listening...', 'success');
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                updateStatus('🔴 Listening - speak now!');
            };
            
            recognition.onend = () => {
                log('Stopped listening', 'info');
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                updateStatus('Click microphone to start');
            };
            
            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                log('Recognized: "' + text + '"', 'success');
                updateStatus('Sending: ' + text);
                sendCommand(text);
            };
            
            recognition.onerror = (event) => {
                log('❌ Error: ' + event.error, 'error');
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                
                if (event.error === 'not-allowed') {
                    updateStatus('❌ Microphone permission denied!');
                    alert('Please allow microphone access and refresh the page.');
                } else {
                    updateStatus('Error: ' + event.error);
                }
            };
            
            log('✅ Speech recognition ready', 'success');
        }
        
        // Send command
        async function sendCommand(text) {
            log('Sending command: "' + text + '"', 'info');
            try {
                const response = await fetch('/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    log('✅ Command sent successfully!', 'success');
                    updateStatus('✅ Sent: ' + text);
                } else {
                    log('❌ Failed: ' + data.error, 'error');
                    updateStatus('❌ Failed to send');
                }
            } catch (err) {
                log('❌ Network error: ' + err.message, 'error');
                updateStatus('❌ Network error');
            }
        }
        
        // Mic button
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition) return;
            
            if (isListening) {
                log('Stopping...', 'info');
                recognition.stop();
            } else {
                log('Starting microphone...', 'info');
                recognition.start();
            }
        });
        
        // Initialize
        window.onload = () => {
            log('Page loaded', 'info');
            initSpeechRecognition();
            log('Ready! Click test button or microphone.', 'success');
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/test', methods=['POST'])
def test():
    """Test tmux connection"""
    try:
        test_message = "VOICE BOT TEST: Connection working!"
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', test_message], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        print(f"[TEST] Sent: {test_message}")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/send', methods=['POST'])
def send():
    """Send voice command to tmux"""
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({'success': False, 'error': 'No command'})
    
    try:
        # Log it
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] VOICE: {command}")
        
        # Send to tmux
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', command], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR] Send failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  SIMPLE CLAUDE VOICE BOT")
    print("="*50)
    print("Access at: https://192.168.40.232:8099")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8099, debug=False, ssl_context=context)