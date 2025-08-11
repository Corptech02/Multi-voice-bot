#!/usr/bin/env python3
"""
Auto Voice Terminal - Automatically sends voice commands to Claude terminal
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
import subprocess
from datetime import datetime
import time

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Auto Voice Terminal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #000;
            color: #00ff00;
            padding: 20px;
            margin: 0;
            font-family: monospace;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00ff00;
            text-shadow: 0 0 20px #00ff00;
            animation: glow 2s ease-in-out infinite;
        }
        @keyframes glow {
            0%, 100% { text-shadow: 0 0 20px #00ff00; }
            50% { text-shadow: 0 0 30px #00ff00, 0 0 40px #00ff00; }
        }
        .status-bar {
            background: #111;
            border: 1px solid #00ff00;
            padding: 10px;
            margin: 20px 0;
            border-radius: 5px;
            text-align: center;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ff0000;
            margin-right: 10px;
            animation: blink 2s infinite;
        }
        .status-dot.connected {
            background: #00ff00;
            animation: none;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .mic-button {
            width: 250px;
            height: 250px;
            border-radius: 50%;
            background: #000;
            border: 3px solid #00ff00;
            color: #00ff00;
            font-size: 100px;
            cursor: pointer;
            display: block;
            margin: 50px auto;
            transition: all 0.3s;
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
            background: radial-gradient(circle, rgba(0,255,0,0.2) 0%, transparent 70%);
            animation: rotate 3s linear infinite;
        }
        @keyframes rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 50px #00ff00;
        }
        .mic-button.listening {
            background: #220000;
            border-color: #ff0000;
            color: #ff0000;
            animation: pulse-red 1s infinite;
        }
        @keyframes pulse-red {
            0%, 100% { box-shadow: 0 0 30px #ff0000; }
            50% { box-shadow: 0 0 50px #ff0000, 0 0 70px #ff0000; }
        }
        .status {
            text-align: center;
            font-size: 20px;
            margin: 20px 0;
            color: #00ff00;
        }
        .terminal {
            background: #000;
            border: 1px solid #00ff00;
            padding: 20px;
            margin-top: 30px;
            height: 300px;
            overflow-y: auto;
            font-family: monospace;
            white-space: pre-wrap;
        }
        .terminal::-webkit-scrollbar {
            width: 10px;
        }
        .terminal::-webkit-scrollbar-track {
            background: #111;
        }
        .terminal::-webkit-scrollbar-thumb {
            background: #00ff00;
        }
        .cmd-line {
            color: #00ff00;
            margin: 5px 0;
        }
        .response {
            color: #00bbff;
            margin: 5px 0;
        }
        .error {
            color: #ff0000;
        }
        .info {
            background: #001100;
            border: 1px solid #00ff00;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .button {
            background: #001100;
            border: 1px solid #00ff00;
            color: #00ff00;
            padding: 10px 20px;
            cursor: pointer;
            margin: 5px;
            transition: all 0.3s;
        }
        .button:hover {
            background: #00ff00;
            color: #000;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 CLAUDE AUTO VOICE TERMINAL</h1>
        
        <div class="status-bar">
            <span class="status-dot" id="statusDot"></span>
            <span id="connectionStatus">Checking terminal connection...</span>
        </div>
        
        <div class="info">
            <strong>🚀 AUTO MODE ACTIVE</strong><br>
            Voice commands are automatically sent to Claude!<br>
            <small>Terminal: <span id="terminalInfo">Detecting...</span></small>
        </div>
        
        <button id="micButton" class="mic-button">
            <span style="position: relative; z-index: 1;">🎤</span>
        </button>
        
        <div class="status" id="status">Ready for voice command</div>
        
        <div style="text-align: center; margin: 20px 0;">
            <button class="button" onclick="testConnection()">Test Connection</button>
            <button class="button" onclick="clearTerminal()">Clear Display</button>
        </div>
        
        <div class="terminal" id="terminal">
            <div class="cmd-line">[SYSTEM] Auto Voice Terminal Started</div>
            <div class="cmd-line">[SYSTEM] Commands will be sent directly to Claude</div>
        </div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let isConnected = false;
        
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
                document.getElementById('status').textContent = '🔴 LISTENING...';
                addToTerminal('[MIC] Listening for voice command...', 'cmd-line');
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
                    autoSendCommand(text);
                }
            };
            
            recognition.onerror = (event) => {
                addToTerminal('[ERROR] ' + event.error, 'error');
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
            };
        }
        
        // Mic button handler
        document.getElementById('micButton').addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Auto send command
        async function autoSendCommand(text) {
            addToTerminal('> ' + text, 'cmd-line');
            document.getElementById('status').textContent = '⚡ Sending to Claude...';
            
            try {
                const response = await fetch('/auto-send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addToTerminal('[SENT] ✅ Command delivered to Claude terminal', 'response');
                    document.getElementById('status').textContent = '✅ Sent to Claude!';
                    
                    // Speak confirmation
                    speak('Command sent');
                } else {
                    addToTerminal('[ERROR] ' + data.error, 'error');
                    document.getElementById('status').textContent = '❌ Failed to send';
                }
            } catch (err) {
                addToTerminal('[ERROR] ' + err.message, 'error');
            }
        }
        
        // Text to speech
        function speak(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.2;
                utterance.volume = 0.5;
                speechSynthesis.speak(utterance);
            }
        }
        
        // Add to terminal
        function addToTerminal(text, className) {
            const terminal = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = className || 'cmd-line';
            line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
        }
        
        // Test connection
        async function testConnection() {
            try {
                const response = await fetch('/test-terminal');
                const data = await response.json();
                
                if (data.success) {
                    addToTerminal('[TEST] ' + data.message, 'response');
                    updateConnectionStatus(true);
                } else {
                    addToTerminal('[TEST] Failed: ' + data.error, 'error');
                    updateConnectionStatus(false);
                }
            } catch (err) {
                addToTerminal('[ERROR] ' + err.message, 'error');
                updateConnectionStatus(false);
            }
        }
        
        // Update connection status
        function updateConnectionStatus(connected) {
            isConnected = connected;
            const dot = document.getElementById('statusDot');
            const status = document.getElementById('connectionStatus');
            
            if (connected) {
                dot.classList.add('connected');
                status.textContent = 'Connected to Claude terminal';
            } else {
                dot.classList.remove('connected');
                status.textContent = 'Not connected';
            }
        }
        
        // Clear terminal
        function clearTerminal() {
            document.getElementById('terminal').innerHTML = '<div class="cmd-line">[CLEARED]</div>';
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                document.getElementById('micButton').click();
            }
        });
        
        // Check connection on load
        window.onload = () => {
            testConnection();
            addToTerminal('[TIP] Press Ctrl+Space for quick voice input', 'response');
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/auto-send', methods=['POST'])
def auto_send():
    """Automatically send command to Claude terminal"""
    data = request.json
    command = data.get('command', '')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] AUTO VOICE: {command}")
    
    try:
        # Method 1: Try to find the tmux session
        # Check if we're in a tmux session
        tmux_result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True)
        
        if tmux_result.returncode == 0:
            # We have tmux, try to send to the Claude session
            # Look for a session that might have Claude
            sessions = tmux_result.stdout.strip().split('\n')
            
            # Try to send to the first session (or specific one if we know the name)
            send_result = subprocess.run([
                'tmux', 'send-keys', '-t', '0', command, 'Enter'
            ], capture_output=True, text=True)
            
            if send_result.returncode == 0:
                return jsonify({'success': True, 'method': 'tmux'})
        
        # Method 2: Write to a FIFO pipe
        fifo_path = '/tmp/claude_voice_pipe'
        if not os.path.exists(fifo_path):
            os.mkfifo(fifo_path)
        
        with open(fifo_path, 'w') as f:
            f.write(command + '\n')
        
        # Method 3: Use xdotool to type into active window
        subprocess.run(['xdotool', 'type', '--clearmodifiers', command + '\n'], capture_output=True)
        
        return jsonify({
            'success': True,
            'command': command,
            'timestamp': timestamp
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test-terminal')
def test_terminal():
    """Test terminal connection"""
    try:
        # Check various methods
        methods = []
        
        # Check tmux
        tmux_check = subprocess.run(['which', 'tmux'], capture_output=True)
        if tmux_check.returncode == 0:
            tmux_sessions = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True)
            if tmux_sessions.returncode == 0:
                methods.append('tmux available')
        
        # Check xdotool
        xdotool_check = subprocess.run(['which', 'xdotool'], capture_output=True)
        if xdotool_check.returncode == 0:
            methods.append('xdotool available')
        
        # Check FIFO
        if os.path.exists('/tmp/claude_voice_pipe'):
            methods.append('FIFO pipe exists')
        
        return jsonify({
            'success': True,
            'message': f"Terminal methods: {', '.join(methods) if methods else 'none found'}"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎤 CLAUDE AUTO VOICE TERMINAL")
    print("="*60)
    print("\n⚡ AUTOMATIC MODE - Voice commands sent directly to Claude!")
    print("\n📋 SETUP:")
    print("1. Make sure you're running Claude in a tmux session:")
    print("   tmux new -s claude")
    print("\n2. Or install xdotool for direct typing:")
    print("   sudo apt-get install xdotool")
    print("\n3. Access the voice interface at:")
    print("   https://192.168.40.232:8446")
    print("\n🎯 Your voice commands will be automatically typed!")
    print("="*60 + "\n")
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8446, ssl_context=context, debug=False)
    else:
        print("Running HTTP version on port 8100")
        app.run(host='0.0.0.0', port=8100, debug=False)