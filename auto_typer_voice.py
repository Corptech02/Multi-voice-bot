#!/usr/bin/env python3
"""
Auto Typer Voice Bot - Automatically types voice commands into terminal
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
import subprocess
import time
from datetime import datetime
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Auto Voice Typer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #000;
            color: #0f0;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #0f0;
            text-shadow: 0 0 20px #0f0;
        }
        .warning {
            background: #110000;
            border: 2px solid #ff0000;
            padding: 20px;
            margin: 20px auto;
            max-width: 600px;
            border-radius: 10px;
        }
        .warning h2 {
            color: #ff0000;
            margin-top: 0;
        }
        .mic-button {
            width: 300px;
            height: 300px;
            border-radius: 50%;
            background: #001100;
            border: 5px solid #0f0;
            color: #0f0;
            font-size: 120px;
            cursor: pointer;
            margin: 40px auto;
            display: block;
            transition: all 0.3s;
            position: relative;
        }
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 50px #0f0;
        }
        .mic-button.listening {
            background: #220000;
            border-color: #ff0000;
            color: #ff0000;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status {
            font-size: 24px;
            margin: 20px 0;
            min-height: 40px;
        }
        .countdown {
            font-size: 48px;
            color: #ff0000;
            margin: 20px 0;
        }
        .log {
            background: #111;
            border: 1px solid #0f0;
            padding: 20px;
            margin: 30px auto;
            max-width: 800px;
            text-align: left;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
        }
        .log-entry {
            margin: 5px 0;
        }
        .auto-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #ff0000;
            color: #fff;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 14px;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <h1>🤖 CLAUDE AUTO VOICE TYPER</h1>
    
    <div class="warning">
        <h2>⚠️ AUTOMATIC TYPING MODE</h2>
        <p>Voice commands will be AUTOMATICALLY typed into your terminal!</p>
        <p>Make sure this terminal window is active before speaking.</p>
        <p><strong>5 second delay before typing starts</strong></p>
    </div>
    
    <button id="micButton" class="mic-button">
        🎤
        <span class="auto-indicator">AUTO</span>
    </button>
    
    <div class="status" id="status">Click microphone to start</div>
    <div class="countdown" id="countdown"></div>
    
    <div class="log" id="log">
        <div class="log-entry">[SYSTEM] Auto typer ready. Commands will be typed automatically!</div>
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
                addLog('[MIC] Listening for command...');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('status').textContent = 'Click microphone to start';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').innerHTML = '💭 <em>' + text + '</em>';
                } else {
                    autoTypeCommand(text);
                }
            };
            
            recognition.onerror = (event) => {
                addLog('[ERROR] ' + event.error);
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
        
        // Auto type command
        async function autoTypeCommand(text) {
            addLog('[VOICE] ' + text);
            document.getElementById('status').textContent = '⏳ Preparing to type...';
            
            // Countdown
            for (let i = 5; i > 0; i--) {
                document.getElementById('countdown').textContent = i;
                await sleep(1000);
            }
            document.getElementById('countdown').textContent = '';
            
            document.getElementById('status').textContent = '⌨️ TYPING NOW!';
            
            try {
                const response = await fetch('/auto-type', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addLog('[SUCCESS] Command typed automatically!');
                    document.getElementById('status').textContent = '✅ Command sent to Claude!';
                } else {
                    addLog('[ERROR] ' + data.error);
                    document.getElementById('status').textContent = '❌ Failed to type';
                }
            } catch (err) {
                addLog('[ERROR] ' + err.message);
            }
        }
        
        // Sleep function
        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
        
        // Add to log
        function addLog(text) {
            const log = document.getElementById('log');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
        }
        
        // Alert user
        addLog('[WARNING] Make sure this terminal window is active!');
        addLog('[TIP] You have 5 seconds to click on the terminal after speaking');
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/auto-type', methods=['POST'])
def auto_type():
    """Automatically type the command"""
    data = request.json
    command = data.get('command', '')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] AUTO TYPING: {command}")
    
    try:
        # Method 1: Try xdotool first (most reliable)
        xdotool_path = subprocess.run(['which', 'xdotool'], capture_output=True, text=True)
        if xdotool_path.returncode == 0:
            # Type the command
            subprocess.run(['xdotool', 'type', '--clearmodifiers', command])
            # Press Enter
            subprocess.run(['xdotool', 'key', 'Return'])
            
            return jsonify({
                'success': True,
                'method': 'xdotool'
            })
        
        # Method 2: Try pyautogui if available
        if PYAUTOGUI_AVAILABLE:
            pyautogui.typewrite(command)
            pyautogui.press('enter')
            
            return jsonify({
                'success': True,
                'method': 'pyautogui'
            })
        
        # Method 3: Try sending to tmux if available
        tmux_result = subprocess.run(['tmux', 'send-keys', '-t', 'claude', command, 'Enter'], 
                                   capture_output=True, text=True)
        if tmux_result.returncode == 0:
            return jsonify({
                'success': True,
                'method': 'tmux'
            })
        
        return jsonify({
            'success': False,
            'error': 'No typing method available. Install xdotool: sudo apt-get install xdotool'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 AUTO VOICE TYPER")
    print("="*60)
    print("\n⚡ FULLY AUTOMATIC - Voice → Terminal")
    print("\n⚠️  IMPORTANT:")
    print("   1. Install xdotool first:")
    print("      sudo apt-get install xdotool")
    print("\n   2. Keep this terminal window ACTIVE")
    print("\n   3. You have 5 seconds after speaking")
    print("      to click on the terminal window")
    print("\n🌐 Access at: https://192.168.40.232:8448")
    print("="*60 + "\n")
    
    # Try to install pyautogui
    try:
        import pyautogui
        print("✅ PyAutoGUI available")
    except:
        print("📦 Installing pyautogui...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyautogui'])
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8448, ssl_context=context, debug=False)
    else:
        app.run(host='0.0.0.0', port=8102, debug=False)