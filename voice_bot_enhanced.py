#!/usr/bin/env python3
"""
Enhanced Voice Bot with Response Capability and Message Log
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
from datetime import datetime
import subprocess
import time
import threading
import queue
import json

app = Flask(__name__)

# Message history
message_history = []
response_queue = queue.Queue()

# HTML template with enhanced UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #0f0;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #0f0;
            text-shadow: 0 0 30px #0f0;
            font-size: 32px;
            margin-bottom: 30px;
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
        .section {
            background: #0a0a0a;
            border: 2px solid #0f0;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }
        .mic-container {
            text-align: center;
            padding: 40px 0;
        }
        .mic-button {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, #003300, #000000);
            border: 4px solid #0f0;
            color: #0f0;
            font-size: 60px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 
                0 0 50px rgba(0, 255, 0, 0.5),
                inset 0 0 50px rgba(0, 255, 0, 0.1);
            position: relative;
            overflow: hidden;
        }
        .mic-button::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(transparent, rgba(0, 255, 0, 0.1), transparent);
            animation: rotate 3s linear infinite;
        }
        @keyframes rotate {
            100% { transform: rotate(360deg); }
        }
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 
                0 0 80px rgba(0, 255, 0, 0.8),
                inset 0 0 50px rgba(0, 255, 0, 0.2);
        }
        .mic-button.listening {
            animation: pulse 1.5s infinite;
            background: radial-gradient(circle at 30% 30%, #ff0033, #330000);
            border-color: #ff0033;
            box-shadow: 
                0 0 80px rgba(255, 0, 51, 0.8),
                inset 0 0 50px rgba(255, 0, 51, 0.2);
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status {
            text-align: center;
            margin: 20px 0;
            font-size: 16px;
            color: #0f0;
            min-height: 24px;
        }
        .message-log {
            background: #000;
            border: 1px solid #0f0;
            border-radius: 5px;
            padding: 20px;
            max-height: 500px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-message {
            background: rgba(0, 255, 0, 0.1);
            border-left: 3px solid #0f0;
            margin-right: 20%;
        }
        .bot-message {
            background: rgba(0, 100, 255, 0.1);
            border-left: 3px solid #0064ff;
            margin-left: 20%;
        }
        .message-label {
            font-weight: bold;
            color: #0f0;
            margin-bottom: 5px;
        }
        .bot-message .message-label {
            color: #0064ff;
        }
        .message-text {
            color: #fff;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .message-time {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            justify-content: center;
        }
        .control-btn {
            background: #001100;
            border: 2px solid #0f0;
            color: #0f0;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .control-btn:hover {
            background: #003300;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        }
        .instructions {
            background: rgba(0, 255, 0, 0.05);
            border: 1px solid #0f0;
            border-radius: 5px;
            padding: 15px;
            margin-top: 20px;
            font-size: 14px;
            line-height: 1.6;
        }
        .shortcut {
            background: #003300;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
        }
        .speaking-indicator {
            display: none;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
            color: #0064ff;
        }
        .speaking-indicator.active {
            display: flex;
        }
        .speaking-dot {
            width: 10px;
            height: 10px;
            background: #0064ff;
            border-radius: 50%;
            animation: speaking 1.4s infinite ease-in-out both;
        }
        .speaking-dot:nth-child(1) { animation-delay: -0.32s; }
        .speaking-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes speaking {
            0%, 80%, 100% {
                transform: scale(0);
                opacity: 0.5;
            }
            40% {
                transform: scale(1);
                opacity: 1;
            }
        }
        /* Custom scrollbar */
        .message-log::-webkit-scrollbar {
            width: 10px;
        }
        .message-log::-webkit-scrollbar-track {
            background: #001100;
            border-radius: 5px;
        }
        .message-log::-webkit-scrollbar-thumb {
            background: #0f0;
            border-radius: 5px;
        }
        .message-log::-webkit-scrollbar-thumb:hover {
            background: #00ff00;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 CLAUDE VOICE ASSISTANT</h1>
        
        <div class="main-grid">
            <div class="section">
                <h2 style="text-align: center; color: #0f0; margin-top: 0;">Voice Control</h2>
                
                <div class="mic-container">
                    <button id="micButton" class="mic-button">
                        <span style="position: relative; z-index: 1;">🎤</span>
                    </button>
                </div>
                
                <div class="status" id="status">Ready for voice command</div>
                
                <div class="speaking-indicator" id="speakingIndicator">
                    <div class="speaking-dot"></div>
                    <div class="speaking-dot"></div>
                    <div class="speaking-dot"></div>
                    <span>Claude is speaking...</span>
                </div>
                
                <div class="controls">
                    <button class="control-btn" onclick="clearMessages()">Clear Chat</button>
                    <button class="control-btn" onclick="toggleTTS()">
                        <span id="ttsStatus">🔊 TTS: ON</span>
                    </button>
                </div>
                
                <div class="instructions">
                    <strong>Quick Tips:</strong><br>
                    • <span class="shortcut">Space</span> Push to talk<br>
                    • <span class="shortcut">Ctrl+Space</span> Toggle listening<br>
                    • <span class="shortcut">Esc</span> Stop listening<br>
                    • Claude will respond with voice<br>
                    • All conversations are logged
                </div>
            </div>
            
            <div class="section">
                <h2 style="text-align: center; color: #0f0; margin-top: 0;">Conversation Log</h2>
                
                <div class="message-log" id="messageLog">
                    <div class="message bot-message">
                        <div class="message-label">🤖 Claude</div>
                        <div class="message-text">Hello! I'm Claude, your voice assistant. How can I help you today?</div>
                        <div class="message-time">${new Date().toLocaleTimeString()}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let ttsEnabled = true;
        let isSpeaking = false;
        
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
                document.getElementById('status').textContent = 'Ready for voice command';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').innerHTML = '💭 <em>' + text + '</em>';
                } else {
                    processCommand(text);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('status').textContent = 'Error: ' + event.error;
            };
        }
        
        // Process command
        async function processCommand(text) {
            // Add user message to log
            addMessage(text, 'user');
            
            // Show processing status
            document.getElementById('status').textContent = '🤔 Processing...';
            
            // Send to server
            try {
                const response = await fetch('/process-voice', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.response) {
                    // Add bot response to log
                    addMessage(data.response, 'bot');
                    
                    // Speak response if TTS enabled
                    if (ttsEnabled) {
                        speakText(data.response);
                    }
                }
                
                document.getElementById('status').textContent = 'Ready for voice command';
            } catch (err) {
                console.error('Failed to process command:', err);
                document.getElementById('status').textContent = 'Error processing command';
                addMessage('Sorry, I encountered an error processing your request.', 'bot');
            }
        }
        
        // Add message to log
        function addMessage(text, sender) {
            const log = document.getElementById('messageLog');
            const message = document.createElement('div');
            message.className = 'message ' + (sender === 'user' ? 'user-message' : 'bot-message');
            
            const label = document.createElement('div');
            label.className = 'message-label';
            label.textContent = sender === 'user' ? '🎤 You' : '🤖 Claude';
            
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.textContent = text;
            
            const time = document.createElement('div');
            time.className = 'message-time';
            time.textContent = new Date().toLocaleTimeString();
            
            message.appendChild(label);
            message.appendChild(textDiv);
            message.appendChild(time);
            
            log.appendChild(message);
            log.scrollTop = log.scrollHeight;
        }
        
        // Text to speech
        function speakText(text) {
            if ('speechSynthesis' in window) {
                // Cancel any ongoing speech
                window.speechSynthesis.cancel();
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                utterance.volume = 1.0;
                
                // Try to use a better voice if available
                const voices = window.speechSynthesis.getVoices();
                const preferredVoice = voices.find(voice => 
                    voice.name.includes('Google') || 
                    voice.name.includes('Microsoft') ||
                    voice.name.includes('Alex')
                );
                if (preferredVoice) {
                    utterance.voice = preferredVoice;
                }
                
                utterance.onstart = () => {
                    isSpeaking = true;
                    document.getElementById('speakingIndicator').classList.add('active');
                };
                
                utterance.onend = () => {
                    isSpeaking = false;
                    document.getElementById('speakingIndicator').classList.remove('active');
                };
                
                window.speechSynthesis.speak(utterance);
            }
        }
        
        // Clear messages
        function clearMessages() {
            const log = document.getElementById('messageLog');
            log.innerHTML = '';
            addMessage('Conversation cleared. How can I help you?', 'bot');
        }
        
        // Toggle TTS
        function toggleTTS() {
            ttsEnabled = !ttsEnabled;
            document.getElementById('ttsStatus').textContent = ttsEnabled ? '🔊 TTS: ON' : '🔇 TTS: OFF';
        }
        
        // Mic button click
        document.getElementById('micButton').addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                if (isSpeaking) {
                    window.speechSynthesis.cancel();
                }
                recognition.start();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.ctrlKey && !e.metaKey && e.target.tagName !== 'INPUT') {
                e.preventDefault();
                if (!isListening) {
                    document.getElementById('micButton').click();
                }
            } else if (e.code === 'Space' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                document.getElementById('micButton').click();
            } else if (e.code === 'Escape' && isListening) {
                recognition.stop();
            }
        });
        
        // Release space to stop
        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && !e.ctrlKey && !e.metaKey && isListening) {
                recognition.stop();
            }
        });
        
        // Load voices
        if ('speechSynthesis' in window) {
            window.speechSynthesis.onvoiceschanged = () => {
                window.speechSynthesis.getVoices();
            };
        }
        
        // Poll for messages from server
        setInterval(async () => {
            try {
                const response = await fetch('/get-messages');
                const data = await response.json();
                
                if (data.new_messages) {
                    data.new_messages.forEach(msg => {
                        if (msg.role === 'assistant' && !document.querySelector('.message-text').textContent.includes(msg.content)) {
                            addMessage(msg.content, 'bot');
                            if (ttsEnabled) {
                                speakText(msg.content);
                            }
                        }
                    });
                }
            } catch (err) {
                // Silently fail polling
            }
        }, 2000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process-voice', methods=['POST'])
def process_voice():
    """Process voice command and generate response"""
    try:
        data = request.json
        command = data.get('command', '')
        
        # Add to message history
        message_history.append({
            'role': 'user',
            'content': command,
            'timestamp': datetime.now().isoformat()
        })
        
        # Send command to tmux session (if needed for terminal interaction)
        try:
            subprocess.run(['tmux', 'send-keys', '-t', 'claude', command, 'C-m'], check=False)
        except:
            pass
        
        # Generate a response based on the command
        response = generate_response(command)
        
        # Add response to history
        message_history.append({
            'role': 'assistant', 
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'status': 'success',
            'response': response
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/get-messages')
def get_messages():
    """Get recent messages"""
    # Return last 10 messages
    recent = message_history[-10:] if len(message_history) > 10 else message_history
    return jsonify({
        'messages': recent,
        'new_messages': []  # Could implement tracking of new messages
    })

def generate_response(command):
    """Generate appropriate response based on command"""
    command_lower = command.lower()
    
    # Basic responses for common queries
    if any(greeting in command_lower for greeting in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm Claude, your AI assistant. How can I help you today?"
    
    elif any(q in command_lower for q in ['how are you', 'how do you do', "how's it going"]):
        return "I'm doing well, thank you for asking! I'm here and ready to help you with any questions or tasks you might have."
    
    elif 'time' in command_lower and ('what' in command_lower or 'tell' in command_lower):
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."
    
    elif 'date' in command_lower and ('what' in command_lower or 'tell' in command_lower):
        current_date = datetime.now().strftime("%B %d, %Y")
        return f"Today's date is {current_date}."
    
    elif any(q in command_lower for q in ['help', 'what can you do', 'capabilities']):
        return ("I can help you with a variety of tasks including:\n"
                "• Answering questions\n"
                "• Running terminal commands\n" 
                "• Writing and editing code\n"
                "• Explaining technical concepts\n"
                "• Problem-solving and debugging\n"
                "Just speak your request and I'll do my best to assist!")
    
    elif 'thank' in command_lower:
        return "You're welcome! I'm happy to help. Is there anything else you'd like to know?"
    
    elif any(q in command_lower for q in ['goodbye', 'bye', 'see you', 'quit', 'exit']):
        return "Goodbye! Feel free to come back anytime you need assistance. Have a great day!"
    
    else:
        # For other commands, acknowledge and indicate processing
        return f"I understood: '{command}'. Let me process that for you. If this is a terminal command, I've sent it to the terminal. For other requests, please give me a moment to think about the best way to help you."

if __name__ == '__main__':
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Check if certificates exist
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("Generating self-signed certificate...")
        os.system('openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=localhost"')
    
    context.load_cert_chain(cert_path, key_path)
    
    print("\n" + "="*50)
    print("🎤 CLAUDE VOICE ASSISTANT")
    print("="*50)
    print(f"✅ Server starting on https://0.0.0.0:8104")
    print(f"📱 Access from any device: https://192.168.40.232:8104")
    print("="*50 + "\n")
    
    # Run the server on port 8104 as requested
    app.run(host='0.0.0.0', port=8104, ssl_context=context, debug=False)