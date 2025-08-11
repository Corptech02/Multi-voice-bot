#!/usr/bin/env python3
"""
Simple Voice Command Display - Shows commands for easy copy/paste
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
from datetime import datetime

app = Flask(__name__)

# Store recent commands
recent_commands = []

# Simple HTML template optimized for copy/paste
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Commands</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: monospace;
            background: #000;
            color: #0f0;
            padding: 20px;
            margin: 0;
        }
        h1 {
            text-align: center;
            color: #0f0;
            font-size: 24px;
        }
        .mic-button {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: #001100;
            border: 3px solid #0f0;
            color: #0f0;
            font-size: 80px;
            cursor: pointer;
            display: block;
            margin: 30px auto;
        }
        .mic-button:active {
            transform: scale(0.95);
        }
        .mic-button.listening {
            background: #110000;
            border-color: #f00;
            color: #f00;
        }
        .command-box {
            background: #001100;
            border: 2px solid #0f0;
            padding: 20px;
            margin: 20px auto;
            max-width: 800px;
            font-size: 18px;
            cursor: pointer;
            position: relative;
        }
        .command-box:hover {
            background: #002200;
        }
        .copy-hint {
            position: absolute;
            top: 5px;
            right: 10px;
            font-size: 12px;
            color: #888;
        }
        .status {
            text-align: center;
            margin: 20px 0;
            font-size: 16px;
        }
        .history {
            max-width: 800px;
            margin: 30px auto;
        }
        .history-item {
            background: #111;
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #555;
            cursor: pointer;
        }
        .history-item:hover {
            border-color: #0f0;
            background: #1a1a1a;
        }
        .copied {
            animation: flash 0.5s;
        }
        @keyframes flash {
            0%, 100% { background: #001100; }
            50% { background: #00ff00; color: #000; }
        }
    </style>
</head>
<body>
    <h1>🎤 CLAUDE VOICE → COPY & PASTE</h1>
    
    <button id="micButton" class="mic-button">🎤</button>
    
    <div class="status" id="status">Click mic and speak your command</div>
    
    <div class="command-box" id="commandBox" onclick="copyCommand()" style="display: none;">
        <span class="copy-hint">CLICK TO COPY</span>
        <div id="commandText"></div>
    </div>
    
    <div class="history" id="history"></div>
    
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
                document.getElementById('status').textContent = 'Click mic and speak your command';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').textContent = '💭 ' + text;
                } else {
                    displayCommand(text);
                }
            };
            
            recognition.onerror = (event) => {
                document.getElementById('status').textContent = 'Error: ' + event.error;
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
        
        // Display command
        function displayCommand(text) {
            document.getElementById('commandBox').style.display = 'block';
            document.getElementById('commandText').textContent = text;
            document.getElementById('status').textContent = '✅ Click the green box to copy!';
            
            // Add to history
            addToHistory(text);
            
            // Save to server
            fetch('/save-command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: text})
            });
            
            // Auto-copy to clipboard
            copyToClipboard(text);
        }
        
        // Copy command
        function copyCommand() {
            const text = document.getElementById('commandText').textContent;
            copyToClipboard(text);
        }
        
        // Copy to clipboard
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                document.getElementById('commandBox').classList.add('copied');
                document.getElementById('status').textContent = '📋 Copied! Paste in Claude terminal';
                setTimeout(() => {
                    document.getElementById('commandBox').classList.remove('copied');
                }, 500);
            }).catch(() => {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                document.getElementById('status').textContent = '📋 Copied! Paste in Claude terminal';
            });
        }
        
        // Add to history
        function addToHistory(text) {
            const history = document.getElementById('history');
            const item = document.createElement('div');
            item.className = 'history-item';
            item.textContent = text;
            item.onclick = () => {
                copyToClipboard(text);
                item.style.borderColor = '#0f0';
                setTimeout(() => {
                    item.style.borderColor = '#555';
                }, 500);
            };
            history.insertBefore(item, history.firstChild);
            
            // Keep only last 10 items
            while (history.children.length > 10) {
                history.removeChild(history.lastChild);
            }
        }
        
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/save-command', methods=['POST'])
def save_command():
    data = request.json
    command = data.get('command', '')
    
    # Save to file
    with open('/tmp/claude_voice_commands.txt', 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {command}\n")
    
    # Add to recent commands
    recent_commands.append({
        'command': command,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep only last 20
    if len(recent_commands) > 20:
        recent_commands.pop(0)
    
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎤 SIMPLE VOICE COMMAND INTERFACE")
    print("="*60)
    print("\n✅ EASY COPY & PASTE MODE")
    print("\n1. Open: https://192.168.40.232:8447")
    print("2. Click the microphone")
    print("3. Speak your command")
    print("4. It's automatically copied!")
    print("5. Just paste in this terminal")
    print("\n💡 TIP: Press Ctrl+Space for quick voice input")
    print("="*60 + "\n")
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8447, ssl_context=context, debug=False)
    else:
        app.run(host='0.0.0.0', port=8101, debug=False)