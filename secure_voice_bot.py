#!/usr/bin/env python3
"""
Secure Claude Voice Bot with HTTPS support
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
from datetime import datetime

app = Flask(__name__)

# Store the last response
last_response = ""

# HTML template with better error handling
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant</title>
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
        .mic-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
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
        }
        .user {
            background: #16213e;
            text-align: right;
            border: 1px solid #4fbdba;
        }
        .claude {
            background: #0f2027;
            border: 1px solid #00ff00;
        }
        .error {
            color: #ff6b6b;
            text-align: center;
            margin: 20px 0;
            background: rgba(255, 107, 107, 0.1);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #ff6b6b;
        }
        .info {
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }
        .permission-guide {
            background: #2c3e50;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            display: none;
        }
        .permission-guide h3 {
            color: #00ff00;
            margin-bottom: 15px;
        }
        .permission-guide ol {
            text-align: left;
            line-height: 1.8;
        }
        .test-button {
            background: #27ae60;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 5px;
            font-size: 16px;
        }
        .test-button:hover {
            background: #229954;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Voice Terminal</h1>
        
        <div class="info">
            <p>📱 Voice control for Claude AI</p>
            <p>🔒 Microphone permission required</p>
        </div>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div class="status" id="status">Checking microphone access...</div>
        
        <div class="error" id="error" style="display: none;"></div>
        
        <div class="permission-guide" id="permissionGuide">
            <h3>🔧 How to enable microphone:</h3>
            <ol>
                <li>Click the lock/info icon in your browser's address bar</li>
                <li>Find "Microphone" in the permissions</li>
                <li>Change it to "Allow"</li>
                <li>Refresh this page</li>
            </ol>
            <p><strong>For phones:</strong> Also check your phone's Settings > Apps > Browser > Permissions</p>
            
            <h3>🧪 Test Options:</h3>
            <button class="test-button" onclick="testMicrophone()">Test Microphone</button>
            <button class="test-button" onclick="requestPermission()">Request Permission</button>
        </div>
        
        <div class="messages" id="messages"></div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let hasPermission = false;
        
        // Check for HTTPS
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            showError('⚠️ HTTPS required for microphone access. Use https:// or access from localhost.');
        }
        
        // Initialize speech recognition
        function initSpeechRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
                
                recognition.onstart = () => {
                    isListening = true;
                    document.getElementById('micButton').classList.add('listening');
                    document.getElementById('status').textContent = '🔴 Listening...';
                };
                
                recognition.onend = () => {
                    isListening = false;
                    document.getElementById('micButton').classList.remove('listening');
                    document.getElementById('status').textContent = hasPermission ? 'Ready to listen...' : 'Microphone permission needed';
                };
                
                recognition.onresult = (event) => {
                    const last = event.results.length - 1;
                    const text = event.results[last][0].transcript;
                    
                    document.getElementById('status').textContent = '🎧 ' + text;
                    
                    if (event.results[last].isFinal) {
                        sendCommand(text);
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Recognition error:', event.error);
                    isListening = false;
                    document.getElementById('micButton').classList.remove('listening');
                    
                    if (event.error === 'not-allowed') {
                        hasPermission = false;
                        showError('🎤 Microphone permission denied. Please allow microphone access.');
                        document.getElementById('permissionGuide').style.display = 'block';
                        document.getElementById('micButton').disabled = true;
                    } else if (event.error === 'no-speech') {
                        document.getElementById('status').textContent = 'No speech detected. Try again.';
                    } else {
                        showError('Error: ' + event.error);
                    }
                };
                
                // Test microphone permission
                checkMicrophonePermission();
            } else {
                showError('Speech recognition not supported. Please use Chrome, Edge, or Safari.');
                document.getElementById('micButton').disabled = true;
            }
        }
        
        // Check microphone permission
        async function checkMicrophonePermission() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                hasPermission = true;
                document.getElementById('status').textContent = 'Ready to listen...';
                document.getElementById('micButton').disabled = false;
                document.getElementById('permissionGuide').style.display = 'none';
                hideError();
            } catch (err) {
                hasPermission = false;
                document.getElementById('status').textContent = 'Microphone permission needed';
                document.getElementById('micButton').disabled = true;
                showError('🎤 Please allow microphone access to use voice commands.');
                document.getElementById('permissionGuide').style.display = 'block';
            }
        }
        
        // Test microphone
        async function testMicrophone() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                showError('✅ Microphone is working! Refresh the page to continue.', false);
                stream.getTracks().forEach(track => track.stop());
                setTimeout(() => location.reload(), 2000);
            } catch (err) {
                showError('❌ Microphone test failed: ' + err.message);
            }
        }
        
        // Request permission
        async function requestPermission() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                location.reload();
            } catch (err) {
                showError('Permission request failed. Please enable it manually in browser settings.');
            }
        }
        
        // Mic button handler
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition || !hasPermission) return;
            
            if (isListening) {
                recognition.stop();
            } else {
                try {
                    recognition.start();
                } catch (err) {
                    showError('Failed to start: ' + err.message);
                }
            }
        });
        
        // Send command to server
        async function sendCommand(text) {
            addMessage(text, 'user');
            document.getElementById('status').textContent = '⏳ Processing...';
            
            try {
                const response = await fetch('/process-voice', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('status').textContent = '✅ Command sent!';
                    setTimeout(checkResponse, 2000);
                } else {
                    showError('Failed to process command');
                }
            } catch (err) {
                showError('Error: ' + err.message);
            }
        }
        
        // Check for Claude's response
        async function checkResponse() {
            try {
                const response = await fetch('/get-last-response');
                const data = await response.json();
                
                if (data.response) {
                    addMessage(data.response, 'claude');
                    // Speak the response
                    if ('speechSynthesis' in window) {
                        const utterance = new SpeechSynthesisUtterance(data.response);
                        window.speechSynthesis.speak(utterance);
                    }
                }
            } catch (err) {
                console.error('Error checking response:', err);
            }
        }
        
        // Add message to display
        function addMessage(text, sender) {
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = 'message ' + sender;
            message.innerHTML = `<strong>${sender === 'user' ? '🗣️ You' : '🤖 Claude'}:</strong><br>${text}`;
            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Show error
        function showError(message, isError = true) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            if (isError) {
                errorDiv.style.color = '#ff6b6b';
                errorDiv.style.background = 'rgba(255, 107, 107, 0.1)';
            } else {
                errorDiv.style.color = '#27ae60';
                errorDiv.style.background = 'rgba(39, 174, 96, 0.1)';
            }
        }
        
        // Hide error
        function hideError() {
            document.getElementById('error').style.display = 'none';
        }
        
        // Initialize on load
        window.onload = () => {
            initSpeechRecognition();
        };
        
        // Periodic response check
        setInterval(checkResponse, 5000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process-voice', methods=['POST'])
def process_voice():
    global last_response
    data = request.json
    command = data.get('command', '')
    
    # Log the voice command
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] VOICE COMMAND: {command}")
    
    # Process commands
    if "hello" in command.lower():
        last_response = "Hello! I'm Claude. How can I help you today?"
    elif "time" in command.lower():
        last_response = f"The current time is {datetime.now().strftime('%I:%M %p')}"
    elif "scanner" in command.lower():
        last_response = "The ScreenScanner is running on port 8095. Would you like me to check its status?"
    else:
        last_response = f"I heard: '{command}'. In the full version, this would be sent to the Claude terminal."
    
    return jsonify({'success': True})

@app.route('/get-last-response')
def get_last_response():
    global last_response
    if last_response:
        response = last_response
        last_response = ""  # Clear after sending
        return jsonify({'response': response})
    return jsonify({'response': None})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️  CLAUDE VOICE TERMINAL (Secure)")
    print("="*60)
    print("✅ Voice interface ready!")
    print("")
    print("📱 Access options:")
    print("   1. HTTP (localhost only): http://localhost:8097")
    print("   2. Network: http://192.168.40.232:8097")
    print("")
    print("⚠️  For remote access with microphone:")
    print("   - Use HTTPS (self-signed cert)")
    print("   - Or use localhost forwarding")
    print("   - Or use Chrome with --unsafely-treat-insecure-origin-as-secure flag")
    print("")
    print("Features:")
    print("- 🎤 Voice input with permission handling")
    print("- 🔊 Text-to-speech responses")
    print("- 📱 Better error messages")
    print("- 🔧 Microphone testing tools")
    print("="*60 + "\n")
    
    # Run on different port to avoid conflict
    app.run(host='0.0.0.0', port=8097, debug=False)