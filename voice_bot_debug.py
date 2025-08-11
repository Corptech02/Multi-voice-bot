#!/usr/bin/env python3
"""
Direct Tmux Voice Bot with Enhanced Debugging and Feedback
"""
from flask import Flask, render_template_string, request, jsonify
import subprocess
import ssl
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML template with better feedback
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Direct Voice Control - Debug Mode</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00ff00;
            text-shadow: 0 0 20px #00ff00;
        }
        .mic-button {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            border: 3px solid #00ff00;
            background: #0f3460;
            color: #00ff00;
            font-size: 80px;
            cursor: pointer;
            margin: 50px auto;
            display: block;
            transition: all 0.3s;
        }
        .mic-button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 40px #00ff00;
        }
        .mic-button.listening {
            background: #ff0000;
            border-color: #ff0000;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        .status {
            text-align: center;
            font-size: 24px;
            margin: 20px 0;
            min-height: 40px;
            padding: 10px;
            background: #0f3460;
            border-radius: 10px;
            border: 1px solid #00ff00;
        }
        .interim-text {
            text-align: center;
            font-size: 18px;
            color: #ffc107;
            min-height: 30px;
            margin: 10px 0;
            padding: 10px;
            background: rgba(255, 193, 7, 0.1);
            border-radius: 10px;
        }
        .messages {
            background: #0f3460;
            border: 1px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            margin-top: 30px;
            max-height: 400px;
            overflow-y: auto;
        }
        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            background: #16213e;
            border: 1px solid #4fbdba;
        }
        .message.sent {
            border-color: #00ff00;
            background: rgba(0, 255, 0, 0.1);
        }
        .message.error {
            border-color: #ff0000;
            background: rgba(255, 0, 0, 0.1);
        }
        .debug-panel {
            background: #0f2027;
            border: 1px solid #666;
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            font-family: monospace;
            font-size: 12px;
        }
        .debug-line {
            margin: 5px 0;
            color: #00ff00;
        }
        .test-button {
            background: #27ae60;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px;
            font-size: 16px;
        }
        .test-button:hover {
            background: #229954;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Direct Voice Control - Debug Mode</h1>
        
        <div class="debug-panel">
            <div class="debug-line">🔧 Debug Mode Active</div>
            <div class="debug-line" id="micStatus">🎤 Microphone: Checking...</div>
            <div class="debug-line" id="apiStatus">🔌 API: Ready</div>
            <div class="debug-line" id="tmuxStatus">📟 Tmux: Connected to session 'claude'</div>
        </div>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div class="status" id="status">Initializing...</div>
        <div class="interim-text" id="interimText"></div>
        
        <div style="text-align: center;">
            <button class="test-button" onclick="testTmux()">Test Tmux Send</button>
            <button class="test-button" onclick="testMicrophone()">Test Microphone</button>
        </div>
        
        <div class="messages" id="messages"></div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let messageCount = 0;
        
        // Initialize speech recognition
        function initSpeechRecognition() {
            updateStatus('Initializing speech recognition...');
            
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
                
                recognition.onstart = () => {
                    console.log('Recognition started');
                    isListening = true;
                    document.getElementById('micButton').classList.add('listening');
                    updateStatus('🔴 Listening... Speak now!');
                    document.getElementById('micStatus').textContent = '🎤 Microphone: Active';
                };
                
                recognition.onend = () => {
                    console.log('Recognition ended');
                    isListening = false;
                    document.getElementById('micButton').classList.remove('listening');
                    updateStatus('Ready to listen...');
                    document.getElementById('interimText').textContent = '';
                    document.getElementById('micStatus').textContent = '🎤 Microphone: Ready';
                };
                
                recognition.onresult = (event) => {
                    console.log('Recognition result:', event);
                    const last = event.results.length - 1;
                    const text = event.results[last][0].transcript;
                    const isFinal = event.results[last].isFinal;
                    
                    if (isFinal) {
                        document.getElementById('interimText').textContent = '';
                        updateStatus('📝 Final text: ' + text);
                        sendToTmux(text);
                    } else {
                        document.getElementById('interimText').textContent = '💬 ' + text;
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Recognition error:', event);
                    isListening = false;
                    document.getElementById('micButton').classList.remove('listening');
                    document.getElementById('micStatus').textContent = '🎤 Microphone: Error - ' + event.error;
                    
                    if (event.error === 'not-allowed') {
                        updateStatus('❌ Microphone permission denied!');
                        addMessage('Microphone permission denied. Please allow access and refresh.', 'error');
                    } else if (event.error === 'no-speech') {
                        updateStatus('No speech detected. Try again.');
                    } else {
                        updateStatus('Error: ' + event.error);
                        addMessage('Recognition error: ' + event.error, 'error');
                    }
                };
                
                updateStatus('Speech recognition initialized. Click the mic to start!');
                document.getElementById('micStatus').textContent = '🎤 Microphone: Ready';
                
            } else {
                updateStatus('❌ Speech recognition not supported!');
                document.getElementById('micButton').disabled = true;
                addMessage('Your browser doesn\'t support speech recognition. Try Chrome or Edge.', 'error');
            }
        }
        
        // Update status
        function updateStatus(text) {
            document.getElementById('status').textContent = text;
            console.log('Status:', text);
        }
        
        // Test microphone
        async function testMicrophone() {
            try {
                updateStatus('Testing microphone access...');
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                updateStatus('✅ Microphone test successful!');
                addMessage('Microphone is working correctly!', 'sent');
                document.getElementById('micStatus').textContent = '🎤 Microphone: Tested OK';
            } catch (err) {
                updateStatus('❌ Microphone test failed!');
                addMessage('Microphone test failed: ' + err.message, 'error');
                document.getElementById('micStatus').textContent = '🎤 Microphone: Test Failed';
            }
        }
        
        // Test tmux
        async function testTmux() {
            updateStatus('Testing tmux connection...');
            try {
                const response = await fetch('/test-tmux', {
                    method: 'POST'
                });
                const data = await response.json();
                if (data.success) {
                    updateStatus('✅ Tmux test successful!');
                    addMessage('Test message sent to tmux!', 'sent');
                } else {
                    updateStatus('❌ Tmux test failed!');
                    addMessage('Tmux test failed: ' + data.error, 'error');
                }
            } catch (err) {
                updateStatus('❌ API Error!');
                addMessage('API Error: ' + err.message, 'error');
            }
        }
        
        // Mic button handler
        document.getElementById('micButton').addEventListener('click', async () => {
            if (!recognition) {
                updateStatus('Speech recognition not initialized!');
                return;
            }
            
            if (isListening) {
                console.log('Stopping recognition...');
                recognition.stop();
            } else {
                try {
                    console.log('Starting recognition...');
                    updateStatus('Starting microphone...');
                    recognition.start();
                } catch (err) {
                    console.error('Start error:', err);
                    updateStatus('Failed to start: ' + err.message);
                    addMessage('Failed to start recognition: ' + err.message, 'error');
                }
            }
        });
        
        // Send command to tmux via server
        async function sendToTmux(text) {
            messageCount++;
            const msgId = messageCount;
            
            addMessage(`[${msgId}] Sending: "${text}"`, 'pending');
            updateStatus('⏳ Sending to Claude...');
            document.getElementById('apiStatus').textContent = '🔌 API: Sending...';
            
            try {
                const response = await fetch('/send-to-tmux', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text, id: msgId})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStatus('✅ Command sent successfully!');
                    updateMessage(msgId, `[${msgId}] Sent: "${text}"`, 'sent');
                    document.getElementById('apiStatus').textContent = '🔌 API: Success';
                } else {
                    updateStatus('❌ Failed to send command!');
                    updateMessage(msgId, `[${msgId}] Failed: "${text}" - ${data.error}`, 'error');
                    document.getElementById('apiStatus').textContent = '🔌 API: Error';
                }
            } catch (err) {
                updateStatus('❌ Network error!');
                updateMessage(msgId, `[${msgId}] Network error: ${err.message}`, 'error');
                document.getElementById('apiStatus').textContent = '🔌 API: Network Error';
            }
        }
        
        // Add message to display
        function addMessage(text, type = 'pending') {
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = 'message ' + type;
            message.id = 'msg-' + messageCount;
            const timestamp = new Date().toLocaleTimeString();
            message.innerHTML = `<strong>[${timestamp}]</strong> ${text}`;
            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Update existing message
        function updateMessage(id, text, type) {
            const msg = document.getElementById('msg-' + id);
            if (msg) {
                msg.className = 'message ' + type;
                const timestamp = new Date().toLocaleTimeString();
                msg.innerHTML = `<strong>[${timestamp}]</strong> ${text}`;
            }
        }
        
        // Initialize on load
        window.onload = () => {
            initSpeechRecognition();
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send-to-tmux', methods=['POST'])
def send_to_tmux():
    data = request.json
    command = data.get('command', '')
    msg_id = data.get('id', 0)
    
    logger.info(f"Received command [{msg_id}]: {command}")
    
    if not command:
        logger.error("No command provided")
        return jsonify({'success': False, 'error': 'No command provided'})
    
    try:
        # Send text to tmux session "claude"
        logger.info("Clearing tmux line...")
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        
        logger.info("Sending command to tmux...")
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', command], check=True)
        
        logger.info("Pressing Enter...")
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        logger.info(f"✅ Command [{msg_id}] sent successfully!")
        
        return jsonify({'success': True, 'id': msg_id})
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to send to tmux: {str(e)}"
        logger.error(f"❌ [{msg_id}] {error_msg}")
        return jsonify({'success': False, 'error': error_msg, 'id': msg_id})
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"❌ [{msg_id}] {error_msg}")
        return jsonify({'success': False, 'error': error_msg, 'id': msg_id})

@app.route('/test-tmux', methods=['POST'])
def test_tmux():
    test_msg = "TEST: Voice bot tmux connection test"
    logger.info("Running tmux test...")
    
    try:
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', test_msg], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        logger.info("✅ Tmux test successful!")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"❌ Tmux test failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️  CLAUDE VOICE BOT - DEBUG MODE")
    print("="*60)
    print("✅ Enhanced debugging and feedback enabled!")
    print("")
    print("📱 Access at: https://192.168.40.232:8098")
    print("")
    print("🔧 Debug Features:")
    print("   - Real-time status updates")
    print("   - Interim speech recognition display")
    print("   - Test buttons for tmux and microphone")
    print("   - Detailed logging")
    print("   - Message tracking with IDs")
    print("")
    print("📋 Instructions:")
    print("   1. Accept the certificate warning")
    print("   2. Test microphone first")
    print("   3. Test tmux connection")
    print("   4. Click mic and speak!")
    print("="*60 + "\n")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8098, debug=False, ssl_context=context)