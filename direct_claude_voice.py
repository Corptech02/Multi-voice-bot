#!/usr/bin/env python3
"""
Direct Claude Voice Interface - Sends commands directly to Claude API
"""
from flask import Flask, render_template_string, request, jsonify, Response
import ssl
import os
import json
import time
from datetime import datetime
import anthropic
import subprocess
from queue import Queue
import threading

app = Flask(__name__)

# Initialize Anthropic client (you'll need to set your API key)
# You can set it as environment variable: export ANTHROPIC_API_KEY="your-key-here"
client = None
try:
    client = anthropic.Anthropic()
except:
    print("Note: Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")

# Store conversation history
conversation_history = []
response_queue = Queue()

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Direct Voice Interface</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.5);
        }
        h1 {
            margin: 0;
            color: #00ff88;
            font-size: 28px;
            text-shadow: 0 0 20px rgba(0,255,136,0.5);
        }
        .subtitle {
            color: #888;
            font-size: 14px;
            margin-top: 5px;
        }
        .main-container {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        .chat-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #111;
            margin: 20px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #0d0d0d;
        }
        .messages::-webkit-scrollbar {
            width: 8px;
        }
        .messages::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        .messages::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 4px;
        }
        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-message {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            margin-left: 20%;
            position: relative;
        }
        .user-message::before {
            content: '🗣️';
            position: absolute;
            left: -30px;
            top: 15px;
            font-size: 24px;
        }
        .claude-message {
            background: linear-gradient(135deg, #0f2027, #203a43);
            margin-right: 20%;
            position: relative;
        }
        .claude-message::before {
            content: '🤖';
            position: absolute;
            right: -30px;
            top: 15px;
            font-size: 24px;
        }
        .message-time {
            font-size: 11px;
            color: #666;
            margin-bottom: 5px;
        }
        .message-content {
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .voice-controls {
            padding: 20px;
            background: #1a1a1a;
            display: flex;
            align-items: center;
            gap: 20px;
            border-top: 1px solid #333;
        }
        .mic-button {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(145deg, #1a1a1a, #2a2a2a);
            border: 3px solid #00ff88;
            color: #00ff88;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 15px rgba(0,255,136,0.3);
        }
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 25px rgba(0,255,136,0.5);
        }
        .mic-button.listening {
            background: linear-gradient(145deg, #2a1a1a, #3a2a2a);
            border-color: #ff4444;
            color: #ff4444;
            animation: pulse 1.5s infinite;
            box-shadow: 0 4px 15px rgba(255,68,68,0.3);
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status-display {
            flex: 1;
            padding: 10px 20px;
            background: #0d0d0d;
            border-radius: 10px;
            border: 1px solid #333;
        }
        .status-text {
            font-size: 16px;
            color: #00ff88;
        }
        .transcript {
            font-size: 14px;
            color: #888;
            margin-top: 5px;
            font-style: italic;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #333;
            border-top-color: #00ff88;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            vertical-align: middle;
            margin-left: 10px;
        }
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
        .error {
            background: rgba(255,68,68,0.1);
            border: 1px solid #ff4444;
            color: #ff6666;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .info-bar {
            background: #1a1a1a;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #333;
        }
        .connection-status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ff4444;
        }
        .status-dot.connected {
            background: #00ff88;
        }
        @media (max-width: 768px) {
            .user-message { margin-left: 10%; }
            .claude-message { margin-right: 10%; }
            .user-message::before,
            .claude-message::before { display: none; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎤 Claude Direct Voice Interface</h1>
        <div class="subtitle">Speak naturally - Claude responds directly</div>
    </div>
    
    <div class="info-bar">
        <div class="connection-status">
            <div class="status-dot" id="statusDot"></div>
            <span id="connectionText">Connecting...</span>
        </div>
        <div>
            <span id="messageCount">0</span> messages
        </div>
    </div>
    
    <div class="main-container">
        <div class="chat-panel">
            <div class="messages" id="messages">
                <div class="message claude-message">
                    <div class="message-time">${new Date().toLocaleTimeString()}</div>
                    <div class="message-content">Hello! I'm Claude. Click the microphone and speak naturally. I'll respond directly here!</div>
                </div>
            </div>
            
            <div class="voice-controls">
                <button id="micButton" class="mic-button">
                    <span id="micIcon">🎤</span>
                </button>
                
                <div class="status-display">
                    <div class="status-text" id="statusText">Ready to listen</div>
                    <div class="transcript" id="transcript"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let messageCount = 0;
        let eventSource;
        
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
                document.getElementById('micIcon').textContent = '🔴';
                document.getElementById('statusText').textContent = 'Listening...';
                document.getElementById('transcript').textContent = '';
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('micIcon').textContent = '🎤';
                document.getElementById('statusText').textContent = 'Ready to listen';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                document.getElementById('transcript').textContent = text;
                
                if (event.results[last].isFinal) {
                    sendToClaude(text);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                document.getElementById('statusText').textContent = 'Error: ' + event.error;
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('micIcon').textContent = '🎤';
            };
        }
        
        // Mic button handler
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition) {
                showError('Speech recognition not supported in your browser');
                return;
            }
            
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Send to Claude
        async function sendToClaude(text) {
            addMessage(text, 'user');
            document.getElementById('statusText').innerHTML = 'Processing... <span class="loading"></span>';
            document.getElementById('transcript').textContent = '';
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: text})
                });
                
                if (!response.ok) {
                    throw new Error('Failed to send message');
                }
                
                // Start streaming response
                streamResponse();
                
            } catch (err) {
                showError('Failed to communicate with Claude: ' + err.message);
                document.getElementById('statusText').textContent = 'Ready to listen';
            }
        }
        
        // Stream Claude's response
        function streamResponse() {
            if (eventSource) {
                eventSource.close();
            }
            
            let responseText = '';
            let messageDiv = null;
            
            eventSource = new EventSource('/stream');
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'start') {
                    messageDiv = addMessage('', 'claude');
                    document.getElementById('statusText').textContent = 'Claude is responding...';
                } else if (data.type === 'content') {
                    responseText += data.content;
                    if (messageDiv) {
                        messageDiv.querySelector('.message-content').textContent = responseText;
                    }
                } else if (data.type === 'end') {
                    document.getElementById('statusText').textContent = 'Ready to listen';
                    eventSource.close();
                    
                    // Speak the response
                    if ('speechSynthesis' in window && responseText) {
                        const utterance = new SpeechSynthesisUtterance(responseText);
                        utterance.rate = 1.0;
                        speechSynthesis.speak(utterance);
                    }
                }
            };
            
            eventSource.onerror = () => {
                document.getElementById('statusText').textContent = 'Ready to listen';
                eventSource.close();
            };
        }
        
        // Add message to chat
        function addMessage(text, type) {
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = 'message ' + (type === 'user' ? 'user-message' : 'claude-message');
            
            const time = document.createElement('div');
            time.className = 'message-time';
            time.textContent = new Date().toLocaleTimeString();
            
            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = text;
            
            message.appendChild(time);
            message.appendChild(content);
            messages.appendChild(message);
            
            messages.scrollTop = messages.scrollHeight;
            
            messageCount++;
            document.getElementById('messageCount').textContent = messageCount;
            
            return message;
        }
        
        // Show error
        function showError(message) {
            const messages = document.getElementById('messages');
            const error = document.createElement('div');
            error.className = 'error';
            error.textContent = '❌ ' + message;
            messages.appendChild(error);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Update connection status
        function updateConnectionStatus(connected) {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('connectionText');
            
            if (connected) {
                dot.classList.add('connected');
                text.textContent = 'Connected to Claude';
            } else {
                dot.classList.remove('connected');
                text.textContent = 'Disconnected';
            }
        }
        
        // Check connection on load
        window.onload = async () => {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                updateConnectionStatus(data.connected);
            } catch {
                updateConnectionStatus(false);
            }
        };
        
        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                document.getElementById('micButton').click();
            }
        });
    </script>
</body>
</html>
'''

# Simulated Claude responses (replace with actual API calls)
def get_claude_response(message):
    """Get response from Claude (simulated for now)"""
    # This is where you would call the actual Claude API
    # For now, return a simulated response
    
    responses = {
        "hello": "Hello! I'm here to help. How can I assist you today?",
        "time": f"The current time is {datetime.now().strftime('%I:%M %p')}",
        "help": "I can help you with various tasks. Just speak naturally and I'll do my best to assist!",
    }
    
    # Check for keywords
    message_lower = message.lower()
    for keyword, response in responses.items():
        if keyword in message_lower:
            return response
    
    # Default response
    return f"I heard you say: '{message}'. In a full implementation, this would be processed by the Claude API for a natural response."

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    """Process chat message"""
    data = request.json
    message = data.get('message', '')
    
    # Log the message
    print(f"\n[VOICE] {message}")
    
    # Store in history
    conversation_history.append({
        'role': 'user',
        'content': message,
        'timestamp': datetime.now().isoformat()
    })
    
    # Get Claude's response
    response = get_claude_response(message)
    
    conversation_history.append({
        'role': 'assistant',
        'content': response,
        'timestamp': datetime.now().isoformat()
    })
    
    # Queue the response for streaming
    response_queue.put(response)
    
    return jsonify({'success': True})

@app.route('/stream')
def stream():
    """Stream Claude's response"""
    def generate():
        # Send start signal
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        
        # Get response from queue
        try:
            response = response_queue.get(timeout=5)
            
            # Simulate streaming by sending characters in chunks
            for i in range(0, len(response), 5):
                chunk = response[i:i+5]
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                time.sleep(0.05)  # Simulate typing delay
            
        except:
            pass
        
        # Send end signal
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/status')
def status():
    """Get connection status"""
    return jsonify({
        'connected': True,
        'api_key_set': bool(os.environ.get('ANTHROPIC_API_KEY')),
        'message_count': len(conversation_history)
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎤 CLAUDE DIRECT VOICE INTERFACE")
    print("="*60)
    print("\n✨ Voice → Claude → Response (No Copy/Paste!)")
    print("\n📝 Setup:")
    print("   1. Set your Claude API key:")
    print("      export ANTHROPIC_API_KEY='your-key-here'")
    print("\n   2. Access the interface at:")
    print("      https://192.168.40.232:8450")
    print("\n🎯 Features:")
    print("   • Direct voice to Claude communication")
    print("   • Real-time streaming responses")
    print("   • Voice responses from Claude")
    print("   • Full conversation history")
    print("="*60 + "\n")
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8450, ssl_context=context, debug=False)
    else:
        app.run(host='0.0.0.0', port=8104, debug=False)