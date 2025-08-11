#!/usr/bin/env python3
"""
Claude Voice Bot with Text-to-Speech - Fixed Version
"""
from flask import Flask, render_template_string, request, jsonify
import subprocess
import ssl
import time
from datetime import datetime
import threading
import queue
import re

app = Flask(__name__)

# Queue to store Claude's responses
response_queue = queue.Queue()

# Track conversation state
last_command = ""
last_command_time = 0
last_response_hash = ""
processed_responses = set()

def capture_tmux_output():
    """Continuously capture tmux output to detect Claude's responses"""
    global last_response_hash
    
    while True:
        try:
            # Wait a bit after command is sent
            if time.time() - last_command_time < 2:
                time.sleep(2)
                continue
                
            # Capture the last 30 lines from tmux
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-30'],
                capture_output=True,
                text=True
            )
            
            current_output = result.stdout
            
            if last_command and last_command in current_output:
                # Find the position of our command
                cmd_pos = current_output.rfind(last_command)
                # Get everything after our command
                after_command = current_output[cmd_pos + len(last_command):].strip()
                
                # Look for Claude's response pattern
                lines = []
                capture = False
                for line in after_command.split('\n'):
                    # Start capturing after we see the prompt
                    if '>' in line and last_command in line:
                        capture = True
                        continue
                    
                    # Stop at next Human: or system messages
                    if capture and ('Human:' in line or 'The user sent' in line):
                        break
                    
                    if capture:
                        line = line.strip()
                        # Filter out system messages and UI elements
                        if (line and 
                            not line.startswith('$') and
                            not line.startswith('>') and
                            not line.startswith('Human:') and
                            not line.startswith('Assistant:') and
                            not line.startswith('╭') and
                            not line.startswith('│') and
                            not line.startswith('╰') and
                            not line.startswith('⏵') and
                            not line.startswith('✽') and
                            not line.startswith('✢') and
                            not line.startswith('✻') and
                            not line.startswith('✶') and
                            not line.startswith('*') and
                            not line.startswith('●') and
                            '🤖' not in line and
                            'tokens' not in line.lower() and
                            'auto-accept' not in line.lower() and
                            'shift+tab' not in line.lower() and
                            'esc to interrupt' not in line.lower() and
                            'Deciphering' not in line and
                            'Simmering' not in line and
                            not re.match(r'^\[\d+:\d+:\d+ [AP]M\]', line)):
                            lines.append(line)
                
                if lines:
                    response = ' '.join(lines).strip()
                    # Create a hash to avoid duplicates
                    response_hash = hash(response)
                    
                    if response_hash not in processed_responses and len(response) > 10:
                        processed_responses.add(response_hash)
                        response_queue.put(response)
                        # Clear the last command to avoid re-processing
                        last_command = ""
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error capturing output: {e}")
            time.sleep(2)

# Start the output capture thread
capture_thread = threading.Thread(target=capture_tmux_output, daemon=True)
capture_thread.start()

# HTML template with TTS
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            color: #00ff00;
            text-shadow: 0 0 20px #00ff00;
        }
        .mic-button {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: 3px solid #00ff00;
            background: #0f3460;
            color: #00ff00;
            font-size: 60px;
            cursor: pointer;
            margin: 30px auto;
            display: block;
        }
        .mic-button.listening {
            background: #ff0000;
            border-color: #ff0000;
        }
        .mic-button.speaking {
            background: #9b59b6;
            border-color: #9b59b6;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        #status {
            font-size: 20px;
            margin: 20px 0;
            padding: 20px;
            background: #0f3460;
            border-radius: 10px;
        }
        .conversation {
            text-align: left;
            background: #0f2027;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            height: 400px;
            overflow-y: auto;
        }
        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
        }
        .user {
            background: #16213e;
            border-left: 4px solid #00ff00;
        }
        .claude {
            background: #1b1b2f;
            border-left: 4px solid #9b59b6;
        }
        .controls {
            margin: 20px 0;
        }
        button {
            background: #27ae60;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 16px;
        }
        button:hover {
            background: #229954;
        }
        .volume-control {
            margin: 10px;
        }
        input[type="range"] {
            width: 200px;
        }
        .speaking-indicator {
            display: none;
            color: #9b59b6;
            font-size: 18px;
            margin: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Voice Assistant</h1>
        
        <div class="controls">
            <button onclick="toggleAutoSpeak()">Auto-Speak: <span id="autoSpeakStatus">ON</span></button>
            <button onclick="clearConversation()">Clear</button>
            <button onclick="stopSpeaking()">Stop Speaking</button>
        </div>
        
        <div class="volume-control">
            <label>Voice Speed: <span id="speedValue">1.0</span></label><br>
            <input type="range" id="speedSlider" min="0.5" max="2" step="0.1" value="1" onchange="updateSpeed()">
        </div>
        
        <button id="micButton" class="mic-button">🎤</button>
        
        <div id="status">Ready to chat!</div>
        <div class="speaking-indicator" id="speakingIndicator">🔊 Speaking...</div>
        
        <div class="conversation" id="conversation"></div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let autoSpeak = true;
        let speechRate = 1.0;
        let isSpeaking = false;
        let lastSpokenText = "";
        
        // Initialize speech synthesis
        const synth = window.speechSynthesis;
        
        function updateSpeed() {
            speechRate = parseFloat(document.getElementById('speedSlider').value);
            document.getElementById('speedValue').textContent = speechRate;
        }
        
        function toggleAutoSpeak() {
            autoSpeak = !autoSpeak;
            document.getElementById('autoSpeakStatus').textContent = autoSpeak ? 'ON' : 'OFF';
        }
        
        function stopSpeaking() {
            synth.cancel();
            isSpeaking = false;
            document.getElementById('speakingIndicator').style.display = 'none';
            document.getElementById('micButton').classList.remove('speaking');
        }
        
        function speak(text) {
            if (!text || isSpeaking || text === lastSpokenText) return;
            
            // Cancel any ongoing speech
            synth.cancel();
            
            lastSpokenText = text;
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = speechRate;
            utterance.pitch = 1;
            utterance.volume = 1;
            
            utterance.onstart = () => {
                isSpeaking = true;
                document.getElementById('speakingIndicator').style.display = 'block';
                document.getElementById('micButton').classList.add('speaking');
            };
            
            utterance.onend = () => {
                isSpeaking = false;
                document.getElementById('speakingIndicator').style.display = 'none';
                document.getElementById('micButton').classList.remove('speaking');
            };
            
            utterance.onerror = (event) => {
                console.error('Speech error:', event);
                isSpeaking = false;
                document.getElementById('speakingIndicator').style.display = 'none';
                document.getElementById('micButton').classList.remove('speaking');
            };
            
            synth.speak(utterance);
        }
        
        function addMessage(text, sender) {
            const conv = document.getElementById('conversation');
            const msg = document.createElement('div');
            msg.className = 'message ' + sender;
            const time = new Date().toLocaleTimeString();
            msg.innerHTML = `<strong>${sender === 'user' ? '🗣️ You' : '🤖 Claude'} [${time}]:</strong><br>${text}`;
            conv.appendChild(msg);
            conv.scrollTop = conv.scrollHeight;
        }
        
        function updateStatus(text) {
            document.getElementById('status').textContent = text;
        }
        
        function clearConversation() {
            document.getElementById('conversation').innerHTML = '';
            updateStatus('Conversation cleared');
            lastSpokenText = "";
        }
        
        // Check for Claude's responses
        async function checkForResponse() {
            try {
                const response = await fetch('/get-response');
                const data = await response.json();
                
                if (data.response && data.response !== lastSpokenText) {
                    addMessage(data.response, 'claude');
                    updateStatus('Claude responded');
                    
                    if (autoSpeak && !isSpeaking) {
                        speak(data.response);
                    }
                }
            } catch (err) {
                console.error('Error checking response:', err);
            }
        }
        
        // Initialize speech recognition
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
                updateStatus('❌ Speech recognition not supported!');
                document.getElementById('micButton').disabled = true;
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                updateStatus('🔴 Listening...');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                updateStatus('Ready to chat!');
            };
            
            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                sendCommand(text);
            };
            
            recognition.onerror = (event) => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                
                if (event.error === 'not-allowed') {
                    updateStatus('❌ Microphone permission denied!');
                    alert('Please allow microphone access and refresh.');
                } else {
                    updateStatus('Error: ' + event.error);
                }
            };
        }
        
        // Send command
        async function sendCommand(text) {
            addMessage(text, 'user');
            updateStatus('Sending to Claude...');
            
            try {
                const response = await fetch('/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStatus('Waiting for Claude...');
                } else {
                    updateStatus('❌ Failed to send');
                }
            } catch (err) {
                updateStatus('❌ Error: ' + err.message);
            }
        }
        
        // Mic button
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition || isSpeaking) return;
            
            // Stop any ongoing speech
            if (isSpeaking) {
                synth.cancel();
                return;
            }
            
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Initialize
        window.onload = () => {
            initSpeechRecognition();
            // Check for responses every 2 seconds
            setInterval(checkForResponse, 2000);
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send', methods=['POST'])
def send():
    """Send voice command to tmux"""
    global last_command, last_command_time
    
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({'success': False, 'error': 'No command'})
    
    try:
        # Track this command
        last_command = command
        last_command_time = time.time()
        
        # Log it
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] VOICE: {command}")
        
        # Send to tmux
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', command], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR] Send failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-response')
def get_response():
    """Get Claude's response from the queue"""
    try:
        if not response_queue.empty():
            response = response_queue.get()
            print(f"[RESPONSE] Sending to TTS: {response[:50]}...")
            return jsonify({'response': response})
        return jsonify({'response': None})
    except Exception as e:
        return jsonify({'response': None, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  CLAUDE VOICE WITH TTS - FIXED")
    print("="*50)
    print("✨ Features:")
    print("  - Voice input")
    print("  - Text-to-speech (no duplicates)")
    print("  - Better filtering")
    print("  - Stop speaking button")
    print("")
    print("📱 Access at: https://192.168.40.232:8101")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8101, debug=False, ssl_context=context)