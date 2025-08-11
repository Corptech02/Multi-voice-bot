#!/usr/bin/env python3
"""
Claude Voice Bot - Web-based voice interface for Claude AI
Allows voice conversations that get typed into the terminal
"""
from flask import Flask, render_template_string, request, jsonify, Response
import subprocess
import threading
import queue
import time
import os
import json
from datetime import datetime

app = Flask(__name__)

# Queue for managing commands to send to terminal
command_queue = queue.Queue()
response_queue = queue.Queue()

# HTML template with voice interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .voice-button {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(145deg, #667eea, #764ba2);
            color: white;
            font-size: 60px;
            cursor: pointer;
            margin: 0 auto;
            display: block;
            transition: all 0.3s;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .voice-button:hover {
            transform: scale(1.05);
        }
        .voice-button.listening {
            animation: pulse 1.5s infinite;
            background: linear-gradient(145deg, #e74c3c, #c0392b);
        }
        .voice-button.speaking {
            background: linear-gradient(145deg, #27ae60, #229954);
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
            70% { box-shadow: 0 0 0 30px rgba(231, 76, 60, 0); }
            100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
        }
        .status {
            text-align: center;
            margin-top: 30px;
            font-size: 1.2em;
            color: #555;
            min-height: 30px;
        }
        .transcript {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 30px;
            max-height: 300px;
            overflow-y: auto;
        }
        .transcript-item {
            margin: 10px 0;
            padding: 10px;
            border-radius: 8px;
        }
        .user-message {
            background: #e3f2fd;
            text-align: right;
        }
        .claude-message {
            background: #f3e5f5;
            text-align: left;
        }
        .settings {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .setting-item {
            margin: 15px 0;
        }
        .setting-item label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .setting-item select, .setting-item input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        .error {
            color: #e74c3c;
            text-align: center;
            margin-top: 20px;
        }
        .info {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Voice Assistant</h1>
        
        <div class="info">
            Click the microphone to start talking to Claude
        </div>
        
        <button id="voiceButton" class="voice-button">
            <span id="micIcon">🎤</span>
        </button>
        
        <div class="status" id="status">Ready to listen...</div>
        
        <div class="transcript" id="transcript">
            <div class="transcript-item claude-message">
                👋 Hi! I'm Claude. Click the microphone and start talking!
            </div>
        </div>
        
        <div class="settings">
            <h3>Settings</h3>
            <div class="setting-item">
                <label for="voice">Voice:</label>
                <select id="voice">
                    <option value="default">Default</option>
                </select>
            </div>
            <div class="setting-item">
                <label for="rate">Speech Rate:</label>
                <input type="range" id="rate" min="0.5" max="2" value="1" step="0.1">
                <span id="rateValue">1.0</span>
            </div>
            <div class="setting-item">
                <label>
                    <input type="checkbox" id="autoSpeak" checked>
                    Automatically speak Claude's responses
                </label>
            </div>
        </div>
        
        <div class="error" id="error" style="display: none;"></div>
    </div>
    
    <script>
        let recognition;
        let synthesis = window.speechSynthesis;
        let isListening = false;
        let voices = [];
        
        const voiceButton = document.getElementById('voiceButton');
        const micIcon = document.getElementById('micIcon');
        const status = document.getElementById('status');
        const transcript = document.getElementById('transcript');
        const error = document.getElementById('error');
        const voiceSelect = document.getElementById('voice');
        const rateSlider = document.getElementById('rate');
        const rateValue = document.getElementById('rateValue');
        const autoSpeak = document.getElementById('autoSpeak');
        
        // Initialize speech recognition
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
        } else if ('SpeechRecognition' in window) {
            recognition = new SpeechRecognition();
        } else {
            showError('Speech recognition not supported in this browser. Try Chrome or Edge.');
        }
        
        if (recognition) {
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                isListening = true;
                voiceButton.classList.add('listening');
                micIcon.textContent = '🔴';
                status.textContent = 'Listening...';
            };
            
            recognition.onend = () => {
                isListening = false;
                voiceButton.classList.remove('listening');
                micIcon.textContent = '🎤';
                status.textContent = 'Ready to listen...';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (event.results[last].isFinal) {
                    addTranscript(text, 'user');
                    status.textContent = 'Sending to Claude...';
                    sendToClaude(text);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                showError('Error: ' + event.error);
                isListening = false;
                voiceButton.classList.remove('listening');
                micIcon.textContent = '🎤';
            };
        }
        
        // Load available voices
        function loadVoices() {
            voices = synthesis.getVoices();
            voiceSelect.innerHTML = '';
            
            voices.forEach((voice, i) => {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = voice.name + ' (' + voice.lang + ')';
                if (voice.default) {
                    option.selected = true;
                }
                voiceSelect.appendChild(option);
            });
        }
        
        synthesis.onvoiceschanged = loadVoices;
        loadVoices();
        
        // Voice button click handler
        voiceButton.addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Settings handlers
        rateSlider.addEventListener('input', (e) => {
            rateValue.textContent = e.target.value;
        });
        
        // Send text to Claude
        async function sendToClaude(text) {
            try {
                const response = await fetch('/send-to-claude', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ text: text })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to send to Claude');
                }
                
                // Start polling for response
                pollForResponse();
                
            } catch (err) {
                showError('Failed to send message: ' + err.message);
                status.textContent = 'Ready to listen...';
            }
        }
        
        // Poll for Claude's response
        async function pollForResponse() {
            status.textContent = 'Waiting for Claude...';
            
            const pollInterval = setInterval(async () => {
                try {
                    const response = await fetch('/get-response');
                    const data = await response.json();
                    
                    if (data.response) {
                        clearInterval(pollInterval);
                        addTranscript(data.response, 'claude');
                        status.textContent = 'Claude responded';
                        
                        if (autoSpeak.checked) {
                            speak(data.response);
                        }
                        
                        setTimeout(() => {
                            status.textContent = 'Ready to listen...';
                        }, 2000);
                    }
                } catch (err) {
                    console.error('Polling error:', err);
                }
            }, 1000);
            
            // Stop polling after 30 seconds
            setTimeout(() => {
                clearInterval(pollInterval);
            }, 30000);
        }
        
        // Text-to-speech
        function speak(text) {
            // Cancel any ongoing speech
            synthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.voice = voices[voiceSelect.value];
            utterance.rate = parseFloat(rateSlider.value);
            
            utterance.onstart = () => {
                voiceButton.classList.add('speaking');
                status.textContent = 'Claude is speaking...';
            };
            
            utterance.onend = () => {
                voiceButton.classList.remove('speaking');
                status.textContent = 'Ready to listen...';
            };
            
            synthesis.speak(utterance);
        }
        
        // Add message to transcript
        function addTranscript(text, sender) {
            const item = document.createElement('div');
            item.className = 'transcript-item ' + (sender === 'user' ? 'user-message' : 'claude-message');
            item.textContent = (sender === 'user' ? '🗣️ You: ' : '🤖 Claude: ') + text;
            transcript.appendChild(item);
            transcript.scrollTop = transcript.scrollHeight;
        }
        
        // Show error
        function showError(message) {
            error.textContent = message;
            error.style.display = 'block';
            setTimeout(() => {
                error.style.display = 'none';
            }, 5000);
        }
        
        // Handle page visibility for speech synthesis
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                synthesis.cancel();
            }
        });
    </script>
</body>
</html>
'''

# Terminal interface class
class TerminalInterface:
    def __init__(self):
        self.process = None
        self.response_buffer = []
        self.last_response = ""
        
    def send_command(self, command):
        """Send command to Claude terminal and auto-accept confirmations"""
        try:
            # For now, just echo the command - in real implementation,
            # this would interface with the actual Claude terminal
            print(f"[VOICE COMMAND]: {command}")
            
            # Simulate Claude's response
            # In real implementation, this would capture terminal output
            response = f"I heard you say: '{command}'. This is a simulated response."
            
            self.last_response = response
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def get_response(self):
        """Get the last response from Claude"""
        return self.last_response

terminal = TerminalInterface()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send-to-claude', methods=['POST'])
def send_to_claude():
    data = request.json
    text = data.get('text', '')
    
    # Send to terminal
    success = terminal.send_command(text)
    
    return jsonify({'success': success})

@app.route('/get-response')
def get_response():
    response = terminal.get_response()
    if response:
        # Clear the response after sending
        terminal.last_response = ""
        return jsonify({'response': response})
    return jsonify({'response': None})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  Claude Voice Assistant")
    print("="*50)
    print("Access from any device at:")
    print("http://192.168.40.232:8096")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=8096, debug=False)