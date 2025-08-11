#!/usr/bin/env python3
"""
Integrated Claude Voice Bot - Full terminal integration
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
import sys
from datetime import datetime
from claude_terminal_connector import initialize_connector, claude_connector

app = Flask(__name__)

# Initialize Claude connector on startup
connector = None

# HTML template (same beautiful UI as before)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude AI Voice Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .stars {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
        }
        
        .star {
            position: absolute;
            width: 2px;
            height: 2px;
            background: white;
            border-radius: 50%;
            animation: twinkle 3s infinite;
        }
        
        @keyframes twinkle {
            0%, 100% { opacity: 0; }
            50% { opacity: 1; }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }
        
        header {
            text-align: center;
            padding: 40px 0;
        }
        
        h1 {
            font-size: 3em;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00ff88, #00bbff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px rgba(0, 255, 136, 0.5);
        }
        
        .subtitle {
            font-size: 1.2em;
            color: #a0a0a0;
            margin-bottom: 20px;
        }
        
        .status-bar {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 15px 25px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ff3366;
            animation: pulse-dot 2s infinite;
        }
        
        .status-dot.connected {
            background: #00ff88;
        }
        
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 40px;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .voice-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .mic-container {
            display: flex;
            justify-content: center;
            margin: 40px 0;
            position: relative;
        }
        
        .mic-button {
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(145deg, #00ff88, #00bbff);
            color: white;
            font-size: 80px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 40px rgba(0, 255, 136, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .mic-button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.3s, height 0.3s;
        }
        
        .mic-button:hover::before {
            width: 100%;
            height: 100%;
        }
        
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 15px 50px rgba(0, 255, 136, 0.4);
        }
        
        .mic-button.listening {
            animation: pulse-mic 1.5s infinite;
            background: linear-gradient(145deg, #ff3366, #ff6b6b);
        }
        
        @keyframes pulse-mic {
            0% { transform: scale(1); box-shadow: 0 10px 40px rgba(255, 51, 102, 0.3); }
            50% { transform: scale(1.1); box-shadow: 0 15px 60px rgba(255, 51, 102, 0.5); }
            100% { transform: scale(1); box-shadow: 0 10px 40px rgba(255, 51, 102, 0.3); }
        }
        
        .status {
            text-align: center;
            font-size: 1.2em;
            margin: 20px 0;
            min-height: 40px;
            color: #00ff88;
        }
        
        .chat-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chat-container {
            height: 500px;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .chat-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .chat-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }
        
        .chat-container::-webkit-scrollbar-thumb {
            background: rgba(0, 255, 136, 0.5);
            border-radius: 4px;
        }
        
        .message {
            margin: 20px 0;
            padding: 20px;
            border-radius: 15px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { 
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .user-message {
            background: linear-gradient(145deg, #2a2a4e, #1a1a3e);
            border: 1px solid rgba(0, 255, 136, 0.3);
            margin-left: 20%;
        }
        
        .claude-message {
            background: linear-gradient(145deg, #1a1a3e, #0f0f23);
            border: 1px solid rgba(0, 187, 255, 0.3);
            margin-right: 20%;
        }
        
        .message-header {
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .message-icon {
            font-size: 1.5em;
        }
        
        .message-time {
            font-size: 0.8em;
            color: #666;
            margin-left: auto;
        }
        
        .error-message {
            background: rgba(255, 51, 102, 0.1);
            border: 1px solid rgba(255, 51, 102, 0.5);
            color: #ff6b6b;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            display: none;
        }
        
        .controls {
            margin-top: 30px;
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        
        .control-button {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .control-button:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }
        
        .pulse-ring {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: 3px solid rgba(0, 255, 136, 0.5);
            transform: translate(-50%, -50%);
            animation: pulse-ring 2s infinite;
            pointer-events: none;
        }
        
        @keyframes pulse-ring {
            0% {
                transform: translate(-50%, -50%) scale(1);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.5);
                opacity: 0;
            }
        }
        
        footer {
            text-align: center;
            padding: 40px 0;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="stars"></div>
    
    <div class="container">
        <header>
            <h1>Claude AI Voice Terminal</h1>
            <p class="subtitle">Direct voice control for your Claude terminal session</p>
        </header>
        
        <div class="status-bar">
            <div class="status-indicator">
                <div class="status-dot" id="statusDot"></div>
                <span id="connectionStatus">Connecting to Claude...</span>
            </div>
            <div>
                <span id="commandCount">0</span> commands sent
            </div>
        </div>
        
        <div class="main-content">
            <div class="voice-section">
                <h2 style="text-align: center; margin-bottom: 30px;">🎙️ Voice Control</h2>
                
                <div class="mic-container">
                    <button id="micButton" class="mic-button">
                        <span id="micIcon">🎤</span>
                    </button>
                    <div class="pulse-ring" id="pulseRing" style="display: none;"></div>
                </div>
                
                <div class="status" id="status">Click the microphone to start</div>
                
                <div class="error-message" id="error"></div>
                
                <div class="controls">
                    <button class="control-button" onclick="clearChat()">Clear Chat</button>
                    <button class="control-button" onclick="restartClaude()">Restart Claude</button>
                    <button class="control-button" onclick="checkStatus()">Check Status</button>
                </div>
            </div>
            
            <div class="chat-section">
                <h2 style="text-align: center; margin-bottom: 30px;">💬 Terminal Session</h2>
                <div class="chat-container" id="chatContainer">
                    <div class="message claude-message">
                        <div class="message-header">
                            <span class="message-icon">🤖</span>
                            <span>Claude</span>
                            <span class="message-time">${new Date().toLocaleTimeString()}</span>
                        </div>
                        <p>Terminal session ready. Click the microphone and speak your command!</p>
                    </div>
                </div>
            </div>
        </div>
        
        <footer>
            <p>Claude Voice Terminal • Direct terminal integration • Auto-confirms prompts</p>
        </footer>
    </div>
    
    <script>
        // Create stars background
        function createStars() {
            const starsContainer = document.querySelector('.stars');
            for (let i = 0; i < 100; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.animationDelay = Math.random() * 3 + 's';
                starsContainer.appendChild(star);
            }
        }
        createStars();
        
        let recognition;
        let isListening = false;
        let synthesis = window.speechSynthesis;
        let commandCount = 0;
        
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
                document.getElementById('status').textContent = 'Listening...';
                document.getElementById('pulseRing').style.display = 'block';
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('micIcon').textContent = '🎤';
                document.getElementById('status').textContent = 'Click the microphone to start';
                document.getElementById('pulseRing').style.display = 'none';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').textContent = '💭 ' + text;
                } else {
                    sendToClaude(text);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                showError('Microphone error: ' + event.error);
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('micIcon').textContent = '🎤';
                document.getElementById('pulseRing').style.display = 'none';
            };
        }
        
        // Microphone button handler
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
        
        // Send to Claude terminal
        async function sendToClaude(text) {
            addMessage(text, 'user');
            document.getElementById('status').textContent = 'Sending to Claude terminal...';
            
            try {
                const response = await fetch('/api/terminal/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    commandCount++;
                    document.getElementById('commandCount').textContent = commandCount;
                    
                    if (data.response) {
                        addMessage(data.response, 'claude');
                        speakResponse(data.response);
                    }
                } else {
                    showError(data.error || 'Failed to send command');
                }
            } catch (err) {
                showError('Connection error: ' + err.message);
            }
        }
        
        // Add message to chat
        function addMessage(text, sender) {
            const container = document.getElementById('chatContainer');
            const message = document.createElement('div');
            message.className = 'message ' + (sender === 'user' ? 'user-message' : 'claude-message');
            
            const header = document.createElement('div');
            header.className = 'message-header';
            header.innerHTML = `
                <span class="message-icon">${sender === 'user' ? '🗣️' : '🤖'}</span>
                <span>${sender === 'user' ? 'You' : 'Claude'}</span>
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
            `;
            
            const content = document.createElement('p');
            content.textContent = text;
            
            message.appendChild(header);
            message.appendChild(content);
            container.appendChild(message);
            
            container.scrollTop = container.scrollHeight;
        }
        
        // Text to speech
        function speakResponse(text) {
            if ('speechSynthesis' in window) {
                // Cancel any ongoing speech
                synthesis.cancel();
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                
                // Select a good voice if available
                const voices = synthesis.getVoices();
                const englishVoice = voices.find(voice => voice.lang.startsWith('en-'));
                if (englishVoice) {
                    utterance.voice = englishVoice;
                }
                
                synthesis.speak(utterance);
            }
        }
        
        // Show error
        function showError(message) {
            const error = document.getElementById('error');
            error.textContent = message;
            error.style.display = 'block';
            setTimeout(() => {
                error.style.display = 'none';
            }, 5000);
        }
        
        // Control functions
        function clearChat() {
            const container = document.getElementById('chatContainer');
            container.innerHTML = `
                <div class="message claude-message">
                    <div class="message-header">
                        <span class="message-icon">🤖</span>
                        <span>Claude</span>
                        <span class="message-time">${new Date().toLocaleTimeString()}</span>
                    </div>
                    <p>Chat cleared. Ready for new commands!</p>
                </div>
            `;
        }
        
        async function restartClaude() {
            try {
                const response = await fetch('/api/terminal/restart', {method: 'POST'});
                const data = await response.json();
                
                if (data.success) {
                    addMessage('Claude terminal restarted successfully', 'claude');
                    updateStatus(true);
                } else {
                    showError('Failed to restart Claude');
                }
            } catch (err) {
                showError('Error restarting: ' + err.message);
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/terminal/status');
                const data = await response.json();
                
                updateStatus(data.connected);
                
                const statusMsg = `Status: ${data.connected ? 'Connected' : 'Disconnected'}, Commands: ${data.command_count}`;
                addMessage(statusMsg, 'claude');
            } catch (err) {
                showError('Error checking status: ' + err.message);
            }
        }
        
        function updateStatus(connected) {
            const dot = document.getElementById('statusDot');
            const status = document.getElementById('connectionStatus');
            
            if (connected) {
                dot.classList.add('connected');
                status.textContent = 'Connected to Claude';
            } else {
                dot.classList.remove('connected');
                status.textContent = 'Disconnected';
            }
        }
        
        // Check status on load
        window.onload = () => {
            checkStatus();
        };
        
        // Periodic status check
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/terminal/send', methods=['POST'])
def send_to_terminal():
    """Send voice command to Claude terminal"""
    global connector
    
    data = request.json
    command = data.get('command', '')
    
    if not connector:
        return jsonify({'success': False, 'error': 'Claude not initialized'})
    
    # Log the command
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] Voice command: {command}")
    
    # Send to Claude terminal
    response = connector.send_voice_command(command)
    
    return jsonify({
        'success': True,
        'response': response,
        'timestamp': timestamp
    })

@app.route('/api/terminal/status')
def get_status():
    """Get Claude terminal status"""
    global connector
    
    if not connector:
        return jsonify({
            'connected': False,
            'command_count': 0
        })
    
    status = connector.get_status()
    
    return jsonify({
        'connected': status['ready'] and status['process_alive'],
        'command_count': status['command_count']
    })

@app.route('/api/terminal/restart', methods=['POST'])
def restart_terminal():
    """Restart Claude terminal"""
    global connector
    
    if connector:
        success = connector.restart()
        return jsonify({'success': success})
    
    return jsonify({'success': False, 'error': 'No connector initialized'})

def initialize_app():
    """Initialize the application"""
    global connector
    
    print("\n" + "="*60)
    print("🎙️  CLAUDE VOICE TERMINAL - INITIALIZING")
    print("="*60)
    
    # Try to initialize Claude connector
    try:
        print("\n📡 Attempting to connect to Claude terminal...")
        connector = initialize_connector()
        
        if connector and connector.is_ready:
            print("✅ Claude terminal connected successfully!")
        else:
            print("⚠️  Running in demo mode (Claude not found)")
            print("   Voice commands will be logged but not executed")
            
            # Create a demo connector
            from claude_terminal_connector import ClaudeTerminalConnector
            connector = ClaudeTerminalConnector()
            connector.is_ready = True
            
            # Override send_voice_command for demo
            def demo_send(text):
                return f"Demo mode: Received '{text}'. In production, this would be sent to Claude."
            
            connector.send_voice_command = demo_send
            
    except Exception as e:
        print(f"❌ Error initializing Claude: {e}")
        print("   Continuing in demo mode...")

if __name__ == '__main__':
    # Initialize on startup
    initialize_app()
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        print("\n" + "="*60)
        print("🎙️  CLAUDE VOICE TERMINAL - READY")
        print("="*60)
        print("✅ Secure terminal interface ready!")
        print("")
        print("🌐 Access at:")
        print("   https://192.168.40.232:8443")
        print("")
        print("Features:")
        print("- 🎤 Voice commands sent directly to Claude terminal")
        print("- 🤖 Auto-confirms terminal prompts")
        print("- 💬 Full conversation history")
        print("- 🔊 Voice responses from Claude")
        print("- 📊 Real-time status monitoring")
        print("="*60 + "\n")
        
        # Run with HTTPS
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8443, ssl_context=context, debug=False)
    else:
        print("\n⚠️  No SSL certificates found")
        print("Running on HTTP (microphone may not work from remote devices)")
        app.run(host='0.0.0.0', port=8097, debug=False)