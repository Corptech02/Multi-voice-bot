#!/usr/bin/env python3
"""
WebSocket Voice Bot - Direct communication without copy/paste
"""
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import os
import subprocess
import time
from datetime import datetime
import pyautogui
import pynput
from pynput.keyboard import Key, Controller

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize keyboard controller
keyboard = Controller()

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Direct Voice Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #000;
            color: #0f0;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #0f0;
            text-shadow: 0 0 30px #0f0;
            margin-bottom: 10px;
        }
        .warning {
            background: #330000;
            border: 2px solid #ff0000;
            padding: 20px;
            margin: 20px auto;
            max-width: 600px;
            border-radius: 10px;
            color: #ff6666;
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
            background: #330000;
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
            height: 40px;
        }
        .auto-label {
            position: absolute;
            top: -20px;
            right: 50%;
            transform: translateX(50%);
            background: #ff0000;
            color: #fff;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 16px;
            font-weight: bold;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        #log {
            background: #111;
            border: 1px solid #0f0;
            padding: 20px;
            margin: 20px auto;
            max-width: 800px;
            height: 200px;
            overflow-y: auto;
            text-align: left;
            font-family: monospace;
        }
        .connected {
            color: #0f0;
            font-weight: bold;
        }
        .disconnected {
            color: #f00;
            font-weight: bold;
        }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
    <h1>🤖 CLAUDE DIRECT VOICE CONTROL</h1>
    
    <div class="warning">
        <h2>⚡ FULL AUTO MODE</h2>
        <p>Voice commands are sent DIRECTLY to your terminal!</p>
        <p>Make sure your Claude terminal is the active window!</p>
        <p id="connectionStatus" class="disconnected">Connecting...</p>
    </div>
    
    <button id="micButton" class="mic-button">
        🎤
        <span class="auto-label">AUTO</span>
    </button>
    
    <div class="status" id="status">Click to start voice control</div>
    
    <div id="log"></div>
    
    <script>
        const socket = io();
        let recognition;
        let isListening = false;
        
        // Socket connection
        socket.on('connect', () => {
            document.getElementById('connectionStatus').textContent = '✅ Connected to terminal';
            document.getElementById('connectionStatus').className = 'connected';
            addLog('[SYSTEM] Connected to voice server');
        });
        
        socket.on('disconnect', () => {
            document.getElementById('connectionStatus').textContent = '❌ Disconnected';
            document.getElementById('connectionStatus').className = 'disconnected';
            addLog('[SYSTEM] Disconnected from server');
        });
        
        socket.on('command_sent', (data) => {
            addLog('[SENT] ' + data.command);
            document.getElementById('status').textContent = '✅ Command sent to terminal!';
        });
        
        socket.on('error', (data) => {
            addLog('[ERROR] ' + data.message);
            document.getElementById('status').textContent = '❌ ' + data.message;
        });
        
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
                addLog('[MIC] Listening...');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('status').textContent = 'Click to start voice control';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').textContent = '💭 ' + text;
                } else {
                    sendCommand(text);
                }
            };
            
            recognition.onerror = (event) => {
                addLog('[ERROR] ' + event.error);
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
            };
        }
        
        // Send command via WebSocket
        function sendCommand(text) {
            addLog('[VOICE] ' + text);
            document.getElementById('status').textContent = '⚡ Sending to terminal...';
            socket.emit('voice_command', {command: text});
        }
        
        // Mic button
        document.getElementById('micButton').addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Add to log
        function addLog(text) {
            const log = document.getElementById('log');
            const entry = document.createElement('div');
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
        }
        
        // Test connection
        socket.emit('test_connection');
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle incoming voice command"""
    command = data.get('command', '')
    
    print(f"\n[WEBSOCKET] Received voice command: {command}")
    
    try:
        # Method 1: Try using pyautogui
        try:
            pyautogui.typewrite(command)
            pyautogui.press('enter')
            emit('command_sent', {'command': command})
            return
        except:
            pass
        
        # Method 2: Try using pynput
        try:
            keyboard.type(command)
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
            emit('command_sent', {'command': command})
            return
        except:
            pass
        
        # Method 3: Try xdotool
        result = subprocess.run(['xdotool', 'type', '--clearmodifiers', command], 
                              capture_output=True)
        if result.returncode == 0:
            subprocess.run(['xdotool', 'key', 'Return'])
            emit('command_sent', {'command': command})
            return
        
        # If all methods fail
        emit('error', {'message': 'Could not send to terminal. Install typing tools first.'})
        
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('test_connection')
def test_connection():
    """Test the connection"""
    emit('connected', {'status': 'ok'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 WEBSOCKET VOICE BOT")
    print("="*60)
    print("\n⚡ DIRECT TERMINAL CONTROL via WebSocket")
    print("\n📋 Required setup:")
    print("   1. Install dependencies:")
    print("      pip install flask-socketio python-socketio pynput")
    print("\n   2. For WSL, you may need:")
    print("      export DISPLAY=:0")
    print("\n   3. Access at:")
    print("      http://192.168.40.232:5000")
    print("="*60 + "\n")
    
    # Try to install dependencies
    try:
        import flask_socketio
    except:
        print("Installing flask-socketio...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'flask-socketio'])
    
    try:
        import pynput
    except:
        print("Installing pynput...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pynput'])
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)