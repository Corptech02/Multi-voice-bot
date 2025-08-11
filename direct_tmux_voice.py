#!/usr/bin/env python3
"""
Direct Tmux Voice Bot - Types commands directly into Claude tmux session
"""
from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
from datetime import datetime

app = Flask(__name__)

# HTML template with voice recognition
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Direct Voice Control</title>
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
            background: #16213e;
            border: 1px solid #4fbdba;
        }
        .success {
            color: #00ff00;
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            border-radius: 10px;
        }
        .error {
            color: #ff6b6b;
            text-align: center;
            margin: 20px 0;
            background: rgba(255, 107, 107, 0.1);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #ff6b6b;
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
        <h1>🎙️ Claude Direct Voice Control</h1>
        
        <div class="info">
            <p>🚀 Direct voice-to-tmux interface</p>
            <p>🔗 Connected to tmux session: claude</p>
            <p>🎯 Say your command and it will be typed directly into Claude!</p>
        </div>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div class="status" id="status">Ready to listen...</div>
        
        <div id="notification" style="display: none;"></div>
        
        <div class="messages" id="messages"></div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        
        // Initialize speech recognition
        function initSpeechRecognition() {
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
                        sendToTmux(text);
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Recognition error:', event.error);
                    isListening = false;
                    document.getElementById('micButton').classList.remove('listening');
                    
                    if (event.error === 'not-allowed') {
                        showNotification('🎤 Microphone permission denied. Please allow access.', 'error');
                    } else {
                        showNotification('Error: ' + event.error, 'error');
                    }
                };
            } else {
                showNotification('Speech recognition not supported in this browser.', 'error');
                document.getElementById('micButton').disabled = true;
            }
        }
        
        // Mic button handler
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition) return;
            
            if (isListening) {
                recognition.stop();
            } else {
                try {
                    recognition.start();
                } catch (err) {
                    showNotification('Failed to start: ' + err.message, 'error');
                }
            }
        });
        
        // Send command to tmux via server
        async function sendToTmux(text) {
            addMessage(text);
            document.getElementById('status').textContent = '⏳ Sending to Claude...';
            
            try {
                const response = await fetch('/send-to-tmux', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification('✅ Command sent to Claude!', 'success');
                    document.getElementById('status').textContent = 'Command sent successfully!';
                } else {
                    showNotification('Failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (err) {
                showNotification('Error: ' + err.message, 'error');
            }
        }
        
        // Add message to display
        function addMessage(text) {
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = 'message';
            message.innerHTML = `<strong>🗣️ Voice Command:</strong><br>${text}`;
            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Show notification
        function showNotification(message, type) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = type;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 5000);
        }
        
        // Initialize on load
        window.onload = () => {
            initSpeechRecognition();
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send-to-tmux', methods=['POST'])
def send_to_tmux():
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({'success': False, 'error': 'No command provided'})
    
    try:
        # Log the command
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp}] VOICE COMMAND: {command}")
        
        # Send text to tmux session "claude"
        # First clear any existing text on the line with Ctrl+U
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        
        # Send the actual command
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', command], check=True)
        
        # Press Enter to submit
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        print(f"[{timestamp}] ✅ Command sent to tmux successfully")
        
        return jsonify({'success': True})
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to send to tmux: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️  CLAUDE DIRECT VOICE CONTROL")
    print("="*60)
    print("✅ Direct tmux integration ready!")
    print("")
    print("📱 Access at: http://192.168.40.232:8097")
    print("")
    print("🎯 How it works:")
    print("   1. Click the microphone button")
    print("   2. Speak your command")
    print("   3. It will be typed directly into Claude!")
    print("")
    print("⚠️  Requirements:")
    print("   - tmux session 'claude' must be active")
    print("   - You must be in the Claude terminal")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8097, debug=False)