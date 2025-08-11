#!/usr/bin/env python3
"""
Multi-Tab Claude Voice Assistant - All Messages Version
Shows messages from all tabs but only speaks from active tab
"""
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import threading
import queue
import uuid
import time
from datetime import datetime
import ssl
import os
import re
from orchestrator_simple import orchestrator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-claude-secret-key-v3'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state for each tab
response_queues = {}  # tab_id -> queue
capture_threads = {}  # tab_id -> thread
active_tab_id = None

def extract_stats_from_output(output):
    """Extract time and token info from Claude's output"""
    stats = {"time": "", "tokens": ""}
    
    # Look for patterns like "4s · ⚒ 122 tokens"
    token_match = re.search(r'(\d+s)\s*·\s*[⚒↑↓]\s*(\d+)\s*tokens', output)
    if token_match:
        stats["time"] = token_match.group(1)
        token_count = int(token_match.group(2))
        
        # Format tokens with K notation
        if token_count >= 1000:
            if token_count >= 10000:
                stats["tokens"] = f"{token_count/1000:.0f}K"
            else:
                stats["tokens"] = f"{token_count/1000:.1f}K"
        else:
            stats["tokens"] = str(token_count)
    
    return stats

def check_for_permission_prompt(content, tab_id):
    """Check if content contains permission prompt and auto-approve if needed"""
    content_lower = content.lower()
    
    # Permission patterns
    permission_patterns = [
        r'❯\s*1\.\s*yes',
        r'do you want to proceed\?',
        r'bash command.*\n.*yes.*\n.*no',
        r'\b(approve|permission|confirm|continue)\b.*\?',
        r'\b(yes|no|y/n)\b.*\?',
        r'press\s+(1|enter|y)',
        r'\[1\].*yes',
        r'1\).*yes',
        r'1\..*yes',
        r'(execute|run|perform).*\?',
    ]
    
    # Check for permission prompts
    prompt_detected = False
    
    # First check for ❯ symbol with context
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '❯' in line:
            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
            if any(x in context.lower() for x in ['yes', '1.', 'proceed', 'approve']):
                prompt_detected = True
                print(f"[AUTO-APPROVE] Detected ❯ prompt in tab {tab_id}")
                break
    
    # Check other patterns
    if not prompt_detected:
        for pattern in permission_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                prompt_detected = True
                print(f"[AUTO-APPROVE] Detected pattern in tab {tab_id}: {pattern}")
                break
    
    # Send approval if detected
    if prompt_detected:
        session = orchestrator.sessions.get(tab_id)
        if session:
            print(f"[AUTO-APPROVE] Sending approval to tab {tab_id}")
            subprocess.run(['tmux', 'send-keys', '-t', f'{session.tmux_session}:0', '1'], check=True)
            subprocess.run(['tmux', 'send-keys', '-t', f'{session.tmux_session}:0', 'Enter'], check=True)
            print(f"[AUTO-APPROVE] Sent: 1 + Enter to tab {tab_id}")
            return True
    
    return False

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #1a1a1a;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        
        /* Tab Bar */
        .tab-bar {
            display: flex;
            background: #2a2a2a;
            border-bottom: 1px solid #444;
            overflow-x: auto;
            flex-shrink: 0;
        }
        
        .tab {
            flex: 1;
            min-width: 150px;
            padding: 12px 20px;
            background: #2a2a2a;
            border: none;
            color: #888;
            cursor: pointer;
            transition: all 0.3s ease;
            border-right: 1px solid #444;
            position: relative;
            text-align: center;
        }
        
        .tab:hover {
            background: #333;
        }
        
        .tab.active {
            background: #1a1a1a;
            color: #fff;
            border-bottom: 2px solid #007aff;
        }
        
        .tab-name {
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        .tab-stats {
            font-size: 11px;
            color: #666;
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        
        .tab.active .tab-stats {
            color: #888;
        }
        
        /* New message indicator */
        .tab.has-new-message::after {
            content: '';
            position: absolute;
            top: 8px;
            right: 8px;
            width: 8px;
            height: 8px;
            background: #4CAF50;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        
        /* Main Container */
        .container {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            padding: 20px;
        }
        
        /* Messages */
        #messages {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 20px;
            padding: 10px;
            background: #252525;
            border-radius: 10px;
        }
        
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 10px;
            animation: fadeIn 0.3s ease;
        }
        
        .user-message {
            background: #007aff;
            color: white;
            margin-left: 20%;
            text-align: right;
        }
        
        .assistant-message {
            background: #333;
            color: #fff;
            margin-right: 20%;
        }
        
        /* Input Area */
        .input-area {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        #voiceButton {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 3px solid #007aff;
            background: #1a1a1a;
            color: #007aff;
            font-size: 24px;
            cursor: pointer;
            transition: all 0.3s ease;
            flex-shrink: 0;
        }
        
        #voiceButton:hover {
            background: #007aff;
            color: white;
        }
        
        #voiceButton.recording {
            background: #ff3b30;
            border-color: #ff3b30;
            color: white;
            animation: pulse 1s infinite;
        }
        
        #textInput {
            flex: 1;
            padding: 15px;
            border: 1px solid #444;
            background: #252525;
            color: white;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
        }
        
        #textInput:focus {
            border-color: #007aff;
        }
        
        #status {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 20px 40px;
            border-radius: 10px;
            display: none;
            z-index: 1000;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="tab-bar" id="tabBar">
        <!-- Tabs will be dynamically created -->
    </div>
    
    <div class="container">
        <div id="messages"></div>
        
        <div class="input-area">
            <button id="voiceButton">🎤</button>
            <input type="text" id="textInput" placeholder="Type a message or use voice..." />
        </div>
    </div>
    
    <div id="status"></div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        let currentTabId = null;
        let recognition;
        const synth = window.speechSynthesis;
        let sessionStats = {};
        let tabMessages = {}; // Store messages for each tab
        
        // Create 4 tabs on load
        function initializeTabs() {
            const tabBar = document.getElementById('tabBar');
            for (let i = 0; i < 4; i++) {
                const tab = document.createElement('div');
                tab.className = 'tab';
                tab.id = `tab_${Date.now()}_${i}`;
                tab.innerHTML = `
                    <div class="tab-name" ondblclick="renameTab('${tab.id}')">Tab ${i + 1}</div>
                    <div class="tab-stats">
                        <span class="time">00:00</span>
                        <span class="tokens">0</span>
                    </div>
                `;
                tab.onclick = () => switchTab(tab.id);
                tabBar.appendChild(tab);
                
                // Initialize empty message array for this tab
                tabMessages[tab.id] = [];
                
                // Initialize session for this tab
                createSession(tab.id);
            }
            
            // Activate first tab
            const firstTab = tabBar.children[0];
            if (firstTab) {
                switchTab(firstTab.id);
            }
        }
        
        function createSession(tabId) {
            fetch('/create_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tab_id: tabId,
                    project_name: document.querySelector(`#${tabId} .tab-name`).textContent
                })
            });
        }
        
        function switchTab(tabId) {
            // Clear new message indicator
            document.getElementById(tabId).classList.remove('has-new-message');
            
            // Update UI
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
            
            currentTabId = tabId;
            
            // Show messages for this tab
            displayMessagesForTab(tabId);
            
            // Notify server
            socket.emit('switch_tab', { tab_id: tabId });
            
            // Update stats display
            updateStatsDisplay(tabId);
        }
        
        function displayMessagesForTab(tabId) {
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';
            
            const messages = tabMessages[tabId] || [];
            messages.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.type}-message`;
                messageDiv.textContent = msg.text;
                messagesDiv.appendChild(messageDiv);
            });
            
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function renameTab(tabId) {
            const tabElement = document.getElementById(tabId);
            const nameElement = tabElement.querySelector('.tab-name');
            const currentName = nameElement.textContent;
            const newName = prompt('Enter new tab name:', currentName);
            if (newName && newName !== currentName) {
                nameElement.textContent = newName;
            }
        }
        
        function updateStatsDisplay(tabId) {
            const stats = sessionStats[tabId] || { time: '00:00', tokens: '0' };
            const tab = document.getElementById(tabId);
            if (tab) {
                tab.querySelector('.time').textContent = stats.time;
                tab.querySelector('.tokens').textContent = stats.tokens;
            }
        }
        
        // Initialize speech recognition
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                sendMessage(transcript);
            };
            
            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                updateStatus('Speech recognition error');
                isRecording = false;
                updateRecordButton();
            };
            
            recognition.onend = function() {
                isRecording = false;
                updateRecordButton();
            };
        }
        
        // Voice button handling
        document.getElementById('voiceButton').addEventListener('click', toggleRecording);
        
        function toggleRecording() {
            if (!currentTabId) {
                updateStatus('Please select a tab first');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            if (recognition) {
                recognition.start();
                isRecording = true;
                updateRecordButton();
                updateStatus('Listening...');
            } else {
                updateStatus('Speech recognition not supported');
            }
        }
        
        function stopRecording() {
            if (recognition) {
                recognition.stop();
            }
            isRecording = false;
            updateRecordButton();
            updateStatus('');
        }
        
        function updateRecordButton() {
            const button = document.getElementById('voiceButton');
            if (isRecording) {
                button.classList.add('recording');
                button.textContent = '⏹️';
            } else {
                button.classList.remove('recording');
                button.textContent = '🎤';
            }
        }
        
        // Text input handling
        document.getElementById('textInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.value.trim()) {
                sendMessage(e.target.value.trim());
                e.target.value = '';
            }
        });
        
        function sendMessage(text) {
            if (!currentTabId) {
                updateStatus('Please select a tab first');
                return;
            }
            
            // Add to current tab's messages
            addMessage(currentTabId, text, 'user');
            
            // Send to server
            fetch('/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tab_id: currentTabId,
                    command: text
                })
            });
        }
        
        function addMessage(tabId, text, type) {
            // Store message for tab
            if (!tabMessages[tabId]) {
                tabMessages[tabId] = [];
            }
            tabMessages[tabId].push({ text, type });
            
            // If this is the current tab, display it
            if (tabId === currentTabId) {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}-message`;
                messageDiv.textContent = text;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            } else if (type === 'assistant') {
                // Show new message indicator for non-active tabs
                document.getElementById(tabId).classList.add('has-new-message');
            }
        }
        
        function updateStatus(text) {
            const status = document.getElementById('status');
            if (text) {
                status.textContent = text;
                status.style.display = 'block';
                setTimeout(() => {
                    status.style.display = 'none';
                }, 3000);
            } else {
                status.style.display = 'none';
            }
        }
        
        // Socket event handlers
        socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        socket.on('response', (data) => {
            // Always add message to the appropriate tab
            if (data.tab_id && data.text) {
                addMessage(data.tab_id, data.text, 'assistant');
                
                // Only speak if it's the current tab
                if (data.tab_id === currentTabId) {
                    speakText(data.text);
                }
            }
        });
        
        socket.on('stats_update', (data) => {
            sessionStats[data.tab_id] = {
                time: data.time || sessionStats[data.tab_id]?.time || '00:00',
                tokens: data.tokens || sessionStats[data.tab_id]?.tokens || '0'
            };
            updateStatsDisplay(data.tab_id);
        });
        
        // Text-to-speech
        function speakText(text) {
            // Simple TTS - you can enhance this
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            synth.speak(utterance);
        }
        
        // Update session stats periodically
        setInterval(() => {
            if (currentTabId) {
                fetch('/get_session_stats', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tab_id: currentTabId })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.stats) {
                        const time = data.stats.session_time || '00:00';
                        const tokens = data.stats.total_tokens || 0;
                        
                        sessionStats[currentTabId] = {
                            time: time,
                            tokens: tokens >= 1000 ? `${(tokens/1000).toFixed(1)}K` : tokens.toString()
                        };
                        updateStatsDisplay(currentTabId);
                    }
                });
            }
        }, 1000);
        
        // Initialize tabs on load
        window.onload = initializeTabs;
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create_session', methods=['POST'])
def create_session():
    """Create a new Claude session for a tab"""
    data = request.json
    tab_id = data.get('tab_id')
    project_name = data.get('project_name', f'Tab {tab_id[-1]}')
    
    try:
        print(f"[CREATE_SESSION] Creating session for tab {tab_id}, project: {project_name}")
        
        # Create session using orchestrator
        session = orchestrator.create_session(tab_id, project_name)
        print(f"[CREATE_SESSION] Session created: {session.session_id}")
        
        # Start capture thread for this session
        response_queue = queue.Queue()
        response_queues[tab_id] = response_queue
        
        capture_thread = threading.Thread(
            target=capture_responses,
            args=(session.session_id, tab_id),
            daemon=True
        )
        capture_threads[tab_id] = capture_thread
        capture_thread.start()
        print(f"[CREATE] Started capture thread for tab {tab_id}, session {session.session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session.session_id,
            'tab_id': tab_id
        })
    except Exception as e:
        print(f"[CREATE_SESSION] Error creating session for tab {tab_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/send_command', methods=['POST'])
def send_command():
    """Send command to appropriate Claude instance"""
    data = request.json
    tab_id = data.get('tab_id')
    command = data.get('command')
    
    try:
        # Log the command
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Tab {tab_id}: {command}")
        
        # Send to orchestrator
        success = orchestrator.send_message(tab_id, command)
        
        if success:
            print(f"[SEND] Sending '{command}' to tab {tab_id}")
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/get_session_stats', methods=['POST'])
def get_session_stats():
    """Get session statistics for a tab"""
    data = request.json
    tab_id = data.get('tab_id')
    
    try:
        stats = orchestrator.get_session_stats(tab_id)
        return jsonify({
            'success': True,
            'stats': {
                'total_tokens': stats['tokens'],
                'session_time': stats['duration']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@socketio.on('switch_tab')
def handle_switch_tab(data):
    """Handle tab switching"""
    tab_id = data.get('tab_id')
    global active_tab_id
    active_tab_id = tab_id
    orchestrator.switch_tab(tab_id)
    emit('tab_switched', {'tab_id': tab_id}, broadcast=True)

def capture_responses(session_id, tab_id):
    """Capture responses from Claude for a specific session with auto-approval"""
    last_content = ""
    last_seen_lines = set()
    processed_responses = set()
    
    print(f"[CAPTURE] Started capture thread for tab {tab_id}, session {session_id}")
    
    while tab_id in capture_threads:
        try:
            # Capture current output
            content = orchestrator.capture_response(session_id)
            
            if content and content != last_content:
                # Check for permission prompts FIRST
                check_for_permission_prompt(content, tab_id)
                
                # Debug: Show first 200 chars of new content
                if len(content) > len(last_content) + 10:
                    print(f"[CAPTURE] New content for tab {tab_id}: {content[-200:]}")  
                
                lines = content.split('\n')
                
                # Process lines to find Claude's responses
                for line in lines:
                    line_hash = hash(line)
                    
                    # Skip already processed lines
                    if line_hash in last_seen_lines:
                        continue
                    
                    cleaned_line = line.strip()
                    
                    # Check for stats in the output
                    stats = extract_stats_from_output(cleaned_line)
                    if stats["time"] or stats["tokens"]:
                        socketio.emit('stats_update', {
                            'tab_id': tab_id,
                            'time': stats["time"],
                            'tokens': stats["tokens"]
                        })
                    
                    # Look for Claude's responses (multiple patterns)
                    # Pattern 1: Lines starting with ● or • (bullet points)
                    if cleaned_line.startswith(('●', '•', '◆', '▸', '→')):
                        response_text = cleaned_line[1:].strip()
                        if response_text and len(response_text) > 10:
                            response_hash = hash(response_text)
                            if response_hash not in processed_responses:
                                print(f"[CAPTURE] Found Claude response for tab {tab_id}: {response_text[:50]}...")
                                socketio.emit('response', {
                                    'tab_id': tab_id,
                                    'text': response_text
                                })
                                processed_responses.add(response_hash)
                                print(f"[RESPONSE] Tab {tab_id}: {response_text}")
                    
                    # Pattern 2: Specific prefixes (from original code)
                    prefixes_to_skip = ['Human:', 'Assistant:', 'H:', 'A:', '[', '>', '```']
                    if not any(cleaned_line.startswith(prefix) for prefix in prefixes_to_skip):
                        # Check if line appears to be a response
                        if (len(cleaned_line) > 20 and 
                            not cleaned_line.startswith(('!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+')) and
                            cleaned_line[0].isalpha()):
                            
                            response_hash = hash(cleaned_line)
                            if response_hash not in processed_responses:
                                print(f"[CAPTURE] Found Claude response for tab {tab_id}: {cleaned_line[:50]}...")
                                socketio.emit('response', {
                                    'tab_id': tab_id,
                                    'text': cleaned_line
                                })
                                processed_responses.add(response_hash)
                                print(f"[RESPONSE] Tab {tab_id}: {cleaned_line}")
                    
                    last_seen_lines.add(line_hash)
                
                last_content = content
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[CAPTURE] Error in capture thread for tab {tab_id}: {str(e)}")
            time.sleep(1)

if __name__ == '__main__':
    # Print startup message
    print("\n" + "="*60)
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT - ALL MESSAGES VERSION")
    print("="*60)
    print("✨ Features:")
    print("  - Shows messages from ALL tabs")
    print("  - Only speaks from active tab")
    print("  - Green dot indicator for new messages")
    print("  - Auto-approval for bash commands")
    print("")
    print("📱 Access at: https://192.168.40.232:8402")
    print("="*60 + "\n")
    
    # Check if certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        # Run with HTTPS
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        socketio.run(app, 
                     host='0.0.0.0',
                     port=8402,
                     ssl_context=context,
                     debug=False,
                     allow_unsafe_werkzeug=True)
    else:
        print("⚠️  No SSL certificates found. Running on HTTP instead.")
        print("📱 Access at: http://192.168.40.232:8402")
        socketio.run(app, 
                     host='0.0.0.0',
                     port=8402,
                     debug=False,
                     allow_unsafe_werkzeug=True)