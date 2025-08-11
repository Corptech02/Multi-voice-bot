#!/usr/bin/env python3
"""Multi-tab bot with truly fixed tab IDs"""
import ssl
import threading
import queue
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import time
import re
from orchestrator_simple import orchestrator, BotSession

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-claude-secret-key-fixed'
socketio = SocketIO(app, cors_allowed_origins="*")

# Fixed tab configuration
FIXED_TABS = [
    ("tab_existing_0", "claude_f7304c08", "f7304c08", "Tab 1"),
    ("tab_existing_1", "claude_9191c9fd", "9191c9fd", "Tab 2"),
    ("tab_existing_2", "claude_ea80a41c", "ea80a41c", "Tab 3"),
    ("tab_existing_3", "claude_30bbf96f", "30bbf96f", "Tab 4")
]

# Global state
response_queues = {}
capture_threads = {}
active_tab_id = "tab_existing_0"

# Simple HTML with completely fixed tabs
HTML_FIXED = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Claude</title>
    <style>
        body { font-family: Arial; margin: 0; padding: 20px; background: #1a1a1a; color: #fff; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #333; cursor: pointer; border-radius: 5px; }
        .tab.active { background: #007aff; }
        #messages { height: 400px; background: #222; padding: 10px; overflow-y: auto; margin-bottom: 20px; }
        .message { margin: 5px 0; }
        .user { color: #007aff; }
        .bot { color: #4CAF50; }
        .input-area { display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; background: #333; border: 1px solid #555; color: white; }
        button { padding: 10px 20px; background: #007aff; border: none; color: white; cursor: pointer; }
        #status { margin-top: 10px; font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <h1>Multi-Tab Claude Assistant</h1>
    <div class="tabs">
        <div class="tab active" onclick="switchTab('tab_existing_0')">Tab 1</div>
        <div class="tab" onclick="switchTab('tab_existing_1')">Tab 2</div>
        <div class="tab" onclick="switchTab('tab_existing_2')">Tab 3</div>
        <div class="tab" onclick="switchTab('tab_existing_3')">Tab 4</div>
    </div>
    <div id="messages"></div>
    <div class="input-area">
        <input type="text" id="input" placeholder="Type a message..." onkeypress="if(event.key==='Enter')sendMessage()">
        <button onclick="sendMessage()">Send</button>
    </div>
    <div id="status">Connected to: tab_existing_0</div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        let currentTab = 'tab_existing_0';
        
        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.tab').forEach((tab, i) => {
                tab.classList.toggle('active', tab.onclick.toString().includes(tabId));
            });
            document.getElementById('status').textContent = 'Connected to: ' + tabId;
            document.getElementById('messages').innerHTML = '';
            
            socket.emit('switch_tab', { tab_id: tabId });
        }
        
        function sendMessage() {
            const input = document.getElementById('input');
            const msg = input.value.trim();
            if (!msg) return;
            
            addMessage('You: ' + msg, 'user');
            
            fetch('/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab_id: currentTab, command: msg })
            })
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    addMessage('Error: ' + data.error, 'error');
                }
            });
            
            input.value = '';
        }
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            const messages = document.getElementById('messages');
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
        
        socket.on('response', (data) => {
            if (data.tab_id === currentTab) {
                addMessage('Claude: ' + data.text, 'bot');
            }
        });
        
        socket.on('connect', () => {
            console.log('Connected to server');
        });
    </script>
</body>
</html>
'''

def capture_responses(session_id, tab_id):
    """Capture responses from Claude"""
    last_content = ""
    
    print(f"[CAPTURE] Started for {tab_id}")
    
    while tab_id in capture_threads:
        try:
            session = orchestrator.sessions.get(tab_id)
            if not session:
                time.sleep(1)
                continue
                
            # Capture tmux pane
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', f'{session.tmux_session}:0', '-p'],
                capture_output=True,
                text=True
            )
            
            content = result.stdout
            if content and content != last_content:
                # Find new lines
                new_content = content[len(last_content):] if len(content) > len(last_content) else ""
                
                if new_content:
                    lines = new_content.strip().split('\n')
                    for line in lines:
                        # Look for Claude responses (lines starting with ●)
                        if line.strip().startswith('●'):
                            response = line[1:].strip()
                            if response and len(response) > 2:
                                print(f"[CAPTURE] Found response: {response[:50]}...")
                                socketio.emit('response', {
                                    'tab_id': tab_id,
                                    'text': response
                                })
                
                last_content = content
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[CAPTURE] Error in {tab_id}: {e}")
            time.sleep(1)

@app.route('/')
def index():
    return HTML_FIXED

@app.route('/send_command', methods=['POST'])
def send_command():
    """Send command to Claude"""
    data = request.json
    tab_id = data.get('tab_id')
    command = data.get('command')
    
    print(f"[SEND] {tab_id}: {command}")
    
    try:
        session_id = orchestrator.route_message(tab_id, command)
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        print(f"[SEND] Error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('switch_tab')
def handle_switch_tab(data):
    """Handle tab switch"""
    global active_tab_id
    tab_id = data.get('tab_id')
    active_tab_id = tab_id
    print(f"[SWITCH] Active tab: {tab_id}")
    emit('tab_switched', {'tab_id': tab_id}, broadcast=True)

if __name__ == '__main__':
    # Clear and setup sessions
    orchestrator.sessions.clear()
    
    print("Setting up fixed sessions...")
    for tab_id, tmux_session, session_id, name in FIXED_TABS:
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            project_name=name,
            tmux_session=tmux_session,
            created_at=datetime.now()
        )
        orchestrator.sessions[tab_id] = session
        print(f"  ✓ {name}: {tmux_session}")
        
        # Start capture thread
        response_queue = queue.Queue()
        response_queues[tab_id] = response_queue
        
        capture_thread = threading.Thread(
            target=capture_responses,
            args=(session_id, tab_id),
            daemon=True
        )
        capture_threads[tab_id] = capture_thread
        capture_thread.start()
    
    print("\n" + "="*50)
    print("🎙️ MULTI-TAB CLAUDE - FIXED FINAL")
    print("="*50)
    print("📱 Access at: https://192.168.40.232:8402")
    print("="*50 + "\n")
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    socketio.run(app, 
                 host='0.0.0.0',
                 port=8402,
                 ssl_context=context,
                 debug=False,
                 allow_unsafe_werkzeug=True)