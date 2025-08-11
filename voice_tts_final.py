#!/usr/bin/env python3
"""
Claude Voice Bot with TTS and Stats Panel
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
processed_responses = set()
current_stats = {"time": "", "tokens": ""}

def extract_stats_from_output(output):
    """Extract time and token info from output"""
    stats = {"time": "", "tokens": ""}
    
    # Look for patterns like "4s · ⚒ 122 tokens"
    token_match = re.search(r'(\d+s)\s*·\s*[⚒↑↓]\s*(\d+)\s*tokens', output)
    if token_match:
        stats["time"] = token_match.group(1)
        stats["tokens"] = token_match.group(2) + " tokens"
    
    return stats

def capture_tmux_output():
    """Continuously capture tmux output to detect Claude's responses"""
    global current_stats
    
    while True:
        try:
            if not last_command or time.time() - last_command_time < 3:
                time.sleep(1)
                continue
                
            # Capture more lines to ensure we get the full response
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-100'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout
            
            # Update stats
            current_stats = extract_stats_from_output(output)
            
            if last_command in output:
                # Find all occurrences of the command
                cmd_positions = [i for i in range(len(output)) if output.startswith(last_command, i)]
                
                if cmd_positions:
                    # Use the last occurrence
                    last_pos = cmd_positions[-1]
                    after_command = output[last_pos + len(last_command):].strip()
                    
                    # Extract Claude's response more carefully
                    response_lines = []
                    in_response = False
                    
                    for line in after_command.split('\n'):
                        # Skip the command echo line
                        if last_command in line:
                            continue
                            
                        # Start capturing after seeing the command
                        if not in_response and line.strip() == '':
                            continue
                            
                        # Stop at system messages or next prompt
                        if 'Human:' in line or 'The user sent' in line or line.startswith('$'):
                            break
                        
                        # Filter out UI elements and system messages
                        line = line.strip()
                        if (line and 
                            not line.startswith('>') and
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
                            not re.match(r'^\[\d+:\d+:\d+ [AP]M\]:?$', line)):
                            
                            # Remove time stamps from beginning of lines
                            line = re.sub(r'^\[\d+:\d+:\d+ [AP]M\]:\s*', '', line)
                            if line:
                                response_lines.append(line)
                                in_response = True
                    
                    if response_lines:
                        response = ' '.join(response_lines).strip()
                        response_hash = hash(response)
                        
                        if response_hash not in processed_responses and len(response) > 10:
                            processed_responses.add(response_hash)
                            response_queue.put(response)
                            print(f"[CAPTURED] Response: {response[:80]}...")
                            # Clear command after processing
                            globals()['last_command'] = ""
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error capturing output: {e}")
            time.sleep(2)

# Start the output capture thread
capture_thread = threading.Thread(target=capture_tmux_output, daemon=True)
capture_thread.start()

# HTML template with TTS and stats
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
        }
        .main-container {
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            gap: 20px;
        }
        .stats-panel {
            width: 200px;
            background: #0f2027;
            border: 1px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            height: fit-content;
        }
        .stats-item {
            margin: 15px 0;
            padding: 10px;
            background: #16213e;
            border-radius: 5px;
            text-align: center;
        }
        .stats-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
        }
        .stats-value {
            font-size: 24px;
            color: #00ff00;
            font-weight: bold;
        }
        .content-container {
            flex: 1;
            text-align: center;
        }
        h1 {
            color: #00ff00;
            text-shadow: 0 0 20px #00ff00;
            margin-bottom: 20px;
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
        #clock {
            font-size: 18px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="stats-panel">
            <h3 style="text-align: center; color: #00ff00; margin-bottom: 20px;">📊 Stats</h3>
            
            <div class="stats-item">
                <div class="stats-label">TIME</div>
                <div class="stats-value" id="responseTime">-</div>
            </div>
            
            <div class="stats-item">
                <div class="stats-label">TOKENS</div>
                <div class="stats-value" id="tokenCount">-</div>
            </div>
            
            <div class="stats-item">
                <div class="stats-label">CLOCK</div>
                <div id="clock" class="stats-value" style="font-size: 18px;"></div>
            </div>
        </div>
        
        <div class="content-container">
            <h1>🎙️ Claude Voice Assistant</h1>
            
            <div class="controls">
                <button onclick="toggleAutoSpeak()">Auto-Speak: <span id="autoSpeakStatus">ON</span></button>
                <button onclick="clearConversation()">Clear</button>
                <button onclick="stopSpeaking()">Stop Speaking</button>
                <button onclick="testConnection()">Test</button>
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
        
        // Update clock
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        updateClock();
        
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
        
        async function testConnection() {
            try {
                const response = await fetch('/test', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    updateStatus('✅ Test successful!');
                }
            } catch (err) {
                updateStatus('❌ Test failed: ' + err.message);
            }
        }
        
        // Check for Claude's responses and stats
        async function checkForResponse() {
            try {
                const response = await fetch('/get-response');
                const data = await response.json();
                
                // Update stats
                if (data.stats) {
                    document.getElementById('responseTime').textContent = data.stats.time || '-';
                    document.getElementById('tokenCount').textContent = data.stats.tokens || '-';
                }
                
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
            
            // Reset stats for new query
            document.getElementById('responseTime').textContent = '...';
            document.getElementById('tokenCount').textContent = '...';
            
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

@app.route('/test', methods=['POST'])
def test():
    """Test tmux connection"""
    global last_command, last_command_time
    try:
        test_message = "VOICE BOT TEST: Final version with stats!"
        last_command = test_message
        last_command_time = time.time()
        
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', test_message], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
        
        # Clear processed responses for new command
        processed_responses.clear()
        
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
    """Get Claude's response and stats"""
    try:
        response_data = {'response': None, 'stats': current_stats}
        
        if not response_queue.empty():
            response = response_queue.get()
            print(f"[RESPONSE] Sending to TTS: {response[:50]}...")
            response_data['response'] = response
            
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'response': None, 'stats': current_stats, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  CLAUDE VOICE WITH TTS - FINAL VERSION")
    print("="*50)
    print("✨ Features:")
    print("  - Voice input & TTS output")
    print("  - Stats panel (time & tokens)")
    print("  - Better response capture")
    print("  - No duplicate messages")
    print("")
    print("📱 Access at: https://192.168.40.232:8102")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8102, debug=False, ssl_context=context)