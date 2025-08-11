#!/usr/bin/env python3
"""Simple multi-tab test with existing sessions"""
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import threading
import time
import ssl
from datetime import datetime
from orchestrator_simple import orchestrator, BotSession

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Fixed tab IDs matching our sessions
TAB_IDS = ["tab_existing_0", "tab_existing_1", "tab_existing_2", "tab_existing_3"]

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Test</title>
    <style>
        body { font-family: Arial; background: #1a1a1a; color: white; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #333; cursor: pointer; border-radius: 5px; }
        .tab.active { background: #007aff; }
        #messages { height: 300px; background: #252525; padding: 10px; overflow-y: auto; margin-bottom: 20px; border-radius: 5px; }
        .message { margin: 5px 0; padding: 5px; }
        .user { text-align: right; color: #007aff; }
        .bot { text-align: left; color: #4CAF50; }
        .input-area { display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; background: #333; border: none; color: white; border-radius: 5px; }
        button { padding: 10px 20px; background: #007aff; border: none; color: white; cursor: pointer; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Multi-Tab Claude Test</h1>
        <div class="tabs">
            <div class="tab active" onclick="switchTab(0)">Tab 1</div>
            <div class="tab" onclick="switchTab(1)">Tab 2</div>
            <div class="tab" onclick="switchTab(2)">Tab 3</div>
            <div class="tab" onclick="switchTab(3)">Tab 4</div>
        </div>
        <div id="messages"></div>
        <div class="input-area">
            <input type="text" id="input" placeholder="Type a message..." onkeypress="if(event.key==='Enter')sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        let currentTab = 0;
        const tabIds = {{ tab_ids | tojson }};
        
        function switchTab(index) {
            currentTab = index;
            document.querySelectorAll('.tab').forEach((tab, i) => {
                tab.classList.toggle('active', i === index);
            });
            document.getElementById('messages').innerHTML = '';
        }
        
        function sendMessage() {
            const input = document.getElementById('input');
            const msg = input.value.trim();
            if (msg) {
                addMessage(msg, 'user');
                
                fetch('/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tab_id: tabIds[currentTab],
                        message: msg
                    })
                });
                
                input.value = '';
            }
        }
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = type === 'user' ? 'You: ' + text : 'Claude: ' + text;
            document.getElementById('messages').appendChild(div);
            document.getElementById('messages').scrollTop = 9999;
        }
        
        socket.on('response', (data) => {
            if (tabIds[currentTab] === data.tab_id) {
                addMessage(data.text, 'bot');
            }
        });
    </script>
</body>
</html>
'''

# Capture threads for each session
capture_threads = {}

def capture_responses(session_id, tab_id):
    """Capture responses from Claude"""
    last_content = ""
    
    while True:
        try:
            # Get tmux session name
            session = orchestrator.sessions.get(tab_id)
            if not session:
                time.sleep(1)
                continue
                
            # Capture tmux pane content
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', f'{session.tmux_session}:0', '-p'],
                capture_output=True,
                text=True
            )
            
            content = result.stdout
            if content and content != last_content:
                # Look for new Claude responses
                lines = content.split('\n')
                for line in lines:
                    if line.strip().startswith('●'):
                        response = line[1:].strip()
                        if response and len(response) > 5:
                            print(f"[CAPTURE] Found response: {response[:50]}...")
                            socketio.emit('response', {
                                'tab_id': tab_id,
                                'text': response
                            })
                
                last_content = content
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[CAPTURE] Error: {e}")
            time.sleep(1)

@app.route('/')
def index():
    return render_template_string(HTML, tab_ids=TAB_IDS)

@app.route('/send', methods=['POST'])
def send():
    data = request.json
    tab_id = data.get('tab_id')
    message = data.get('message')
    
    print(f"[SEND] {tab_id}: {message}")
    
    # Get session
    session = orchestrator.sessions.get(tab_id)
    if session:
        # Send to tmux
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
            message, 'Enter'
        ])
        return jsonify({'success': True})
    else:
        print(f"[SEND] No session found for {tab_id}")
        return jsonify({'success': False, 'error': 'No session'})

if __name__ == '__main__':
    # Use existing sessions
    EXISTING = [
        ("claude_f7304c08", "f7304c08"),
        ("claude_9191c9fd", "9191c9fd"),
        ("claude_ea80a41c", "ea80a41c"),
        ("claude_30bbf96f", "30bbf96f")
    ]
    
    # Clear and add sessions
    orchestrator.sessions.clear()
    
    for i, (tmux_session, session_id) in enumerate(EXISTING):
        tab_id = TAB_IDS[i]
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            project_name=f"Tab {i+1}",
            tmux_session=tmux_session,
            created_at=datetime.now()
        )
        orchestrator.sessions[tab_id] = session
        print(f"Added {tab_id}: {tmux_session}")
        
        # Start capture thread
        thread = threading.Thread(
            target=capture_responses,
            args=(session_id, tab_id),
            daemon=True
        )
        thread.start()
        capture_threads[tab_id] = thread
        print(f"Started capture thread for {tab_id}")
    
    # Run with HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    print("\n" + "="*50)
    print("Simple Multi-Tab Test")
    print("Using existing Claude sessions")
    print("Access at: https://192.168.40.232:8403")
    print("="*50 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=8403, ssl_context=context, allow_unsafe_werkzeug=True)