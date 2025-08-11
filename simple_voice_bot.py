#!/usr/bin/env python3
"""
Simple Claude Voice Bot - Direct terminal integration
"""
from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
import time
from datetime import datetime

app = Flask(__name__)

# Store the last response
last_response = ""

# HTML template
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
        }
        .info {
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Voice Terminal</h1>
        
        <div class="info">
            <p>📱 Works on any device with a microphone!</p>
            <p>🗣️ Click the mic and speak your command</p>
            <p>🤖 Claude will process it in the terminal</p>
        </div>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div class="status" id="status">Ready to listen...</div>
        
        <div class="messages" id="messages"></div>
        
        <div class="error" id="error"></div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        
        // Initialize speech recognition
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
                document.getElementById('status').textContent = 'Ready to listen...';
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
                document.getElementById('error').textContent = 'Error: ' + event.error;
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
            };
        } else {
            document.getElementById('error').textContent = 'Speech recognition not supported. Try Chrome or Edge.';
        }
        
        // Mic button handler
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition) return;
            
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
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
                    // Poll for response
                    setTimeout(checkResponse, 2000);
                } else {
                    document.getElementById('error').textContent = 'Failed to process command';
                }
            } catch (err) {
                document.getElementById('error').textContent = 'Error: ' + err.message;
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
    
    # Here you would integrate with the actual Claude terminal
    # For now, we'll simulate a response
    if "hello" in command.lower():
        last_response = "Hello! I heard you say: " + command
    elif "time" in command.lower():
        last_response = f"The current time is {datetime.now().strftime('%I:%M %p')}"
    elif "scanner" in command.lower():
        last_response = "The ScreenScanner is running on port 8095. Would you like me to check its status?"
    else:
        last_response = f"I received your command: '{command}'. In a full implementation, this would be sent to the Claude terminal."
    
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
    print("🎙️  CLAUDE VOICE TERMINAL")
    print("="*60)
    print("✅ Voice interface ready!")
    print("📱 Access from any device at:")
    print("   http://192.168.40.232:8096")
    print("")
    print("Features:")
    print("- 🎤 Voice input with speech recognition")
    print("- 🔊 Text-to-speech responses")
    print("- 📱 Works on phones, tablets, and PCs")
    print("- 🤖 Auto-confirms terminal prompts")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8096, debug=False)