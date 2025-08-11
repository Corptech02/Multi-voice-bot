#!/usr/bin/env python3
"""
Terminal Voice Bridge - Sends voice commands to the current terminal session
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
import sys
from datetime import datetime
import subprocess

app = Flask(__name__)

# Store the terminal session info
VOICE_COMMAND_FILE = "/tmp/claude_voice_commands.txt"
RESPONSE_FILE = "/tmp/claude_voice_response.txt"

# HTML template with improved UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Terminal Voice Bridge</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0a0a0a;
            color: #00ff00;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00ff00;
            text-shadow: 0 0 20px #00ff00;
            margin-bottom: 10px;
        }
        .info {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }
        .mic-button {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: #001100;
            border: 3px solid #00ff00;
            color: #00ff00;
            font-size: 80px;
            cursor: pointer;
            display: block;
            margin: 40px auto;
            transition: all 0.3s;
            box-shadow: 0 0 30px #00ff00;
        }
        .mic-button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 50px #00ff00;
        }
        .mic-button.listening {
            background: #ff0000;
            border-color: #ff0000;
            box-shadow: 0 0 50px #ff0000;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .status {
            text-align: center;
            font-size: 20px;
            margin: 20px 0;
            min-height: 30px;
            color: #00ff00;
            font-family: monospace;
        }
        .terminal {
            background: #000;
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 20px;
            margin-top: 30px;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
        }
        .terminal-line {
            margin: 5px 0;
            white-space: pre-wrap;
        }
        .user-input {
            color: #00ff00;
        }
        .claude-response {
            color: #00bbff;
        }
        .system-msg {
            color: #ff6600;
        }
        .instructions {
            background: #001100;
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            font-size: 14px;
        }
        .instructions h3 {
            margin-top: 0;
            color: #00ff00;
        }
        .command {
            background: #000;
            padding: 5px 10px;
            border-radius: 3px;
            font-family: monospace;
            display: inline-block;
            margin: 2px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 Claude Terminal Voice Bridge</h1>
        <p class="info">Speak to Claude in your WSL terminal</p>
        
        <div class="instructions">
            <h3>⚡ Quick Setup (Run in your Claude terminal):</h3>
            <div class="command">watch -n 1 cat /tmp/claude_voice_commands.txt 2>/dev/null</div>
            <p style="margin-top: 10px;">This will show voice commands as they come in!</p>
        </div>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div class="status" id="status">Click microphone to speak to Claude</div>
        
        <div class="terminal" id="terminal">
            <div class="terminal-line system-msg">[SYSTEM] Voice bridge ready</div>
            <div class="terminal-line system-msg">[SYSTEM] Your voice commands will appear in the terminal</div>
        </div>
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
                document.getElementById('status').textContent = '🔴 LISTENING...';
                addTerminalLine('[MIC] Listening...', 'system-msg');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('status').textContent = 'Click microphone to speak to Claude';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').textContent = '💭 ' + text;
                } else {
                    sendToTerminal(text);
                }
            };
            
            recognition.onerror = (event) => {
                addTerminalLine('[ERROR] ' + event.error, 'system-msg');
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
        
        // Send to terminal
        async function sendToTerminal(text) {
            addTerminalLine('> ' + text, 'user-input');
            document.getElementById('status').textContent = 'Sending to Claude terminal...';
            
            try {
                const response = await fetch('/send-to-terminal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addTerminalLine('[SENT] Command written to terminal', 'system-msg');
                    document.getElementById('status').textContent = '✅ Sent to terminal';
                    
                    // Speak confirmation
                    if ('speechSynthesis' in window) {
                        const utterance = new SpeechSynthesisUtterance('Command sent to Claude');
                        speechSynthesis.speak(utterance);
                    }
                } else {
                    addTerminalLine('[ERROR] ' + data.error, 'system-msg');
                }
            } catch (err) {
                addTerminalLine('[ERROR] ' + err.message, 'system-msg');
            }
        }
        
        // Add to terminal display
        function addTerminalLine(text, className) {
            const terminal = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = 'terminal-line ' + (className || '');
            line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
        }
        
        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.ctrlKey) {
                e.preventDefault();
                document.getElementById('micButton').click();
            }
        });
        
        addTerminalLine('[TIP] Press Ctrl+Space for quick voice input', 'system-msg');
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send-to-terminal', methods=['POST'])
def send_to_terminal():
    data = request.json
    command = data.get('command', '')
    
    # Log the command
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[VOICE COMMAND] {command}")
    
    try:
        # Write command to file that terminal can read
        with open(VOICE_COMMAND_FILE, 'w') as f:
            f.write(f"[{timestamp}] {command}\n")
        
        # Also append to history
        with open('/tmp/claude_voice_history.txt', 'a') as f:
            f.write(f"[{timestamp}] {command}\n")
        
        # Create a notification for the terminal
        print(f"\n{'='*60}")
        print(f"🎤 VOICE COMMAND RECEIVED: {command}")
        print(f"{'='*60}\n")
        
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

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎤 CLAUDE TERMINAL VOICE BRIDGE")
    print("="*60)
    print("\n📋 SETUP INSTRUCTIONS:")
    print("\n1. In THIS terminal (where Claude is running), run:")
    print("   tail -f /tmp/claude_voice_commands.txt")
    print("\n2. Open the voice interface at:")
    print("   https://192.168.40.232:8445")
    print("\n3. Speak your commands!")
    print("\nYour voice commands will appear in the terminal file.")
    print("="*60 + "\n")
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8445, ssl_context=context, debug=False)
    else:
        print("Running HTTP version on port 8099")
        app.run(host='0.0.0.0', port=8099, debug=False)