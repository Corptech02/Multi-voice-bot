#!/usr/bin/env python3
"""
Multi-Tab Claude Voice Assistant
Supports multiple simultaneous Claude conversations with tab isolation
"""
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import json
import time
import threading
import queue
from datetime import datetime
import ssl
import os
from orchestrator_simple import orchestrator
import subprocess
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-claude-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
active_tab = None
response_queues = {}  # tab_id -> queue
capture_threads = {}  # tab_id -> thread

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }
        
        .container {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        
        /* Tab System */
        .tab-container {
            display: flex;
            background: #1a1a1a;
            border-bottom: 2px solid #333;
            overflow-x: auto;
            min-height: 50px;
        }
        
        .tab {
            padding: 15px 25px;
            background: #2a2a2a;
            border: 1px solid #333;
            border-bottom: none;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 150px;
        }
        
        .tab:hover {
            background: #3a3a3a;
        }
        
        .tab.active {
            background: #00ff00;
            color: #000;
            font-weight: bold;
        }
        
        .tab-close {
            margin-left: auto;
            cursor: pointer;
            opacity: 0.7;
        }
        
        .tab-close:hover {
            opacity: 1;
        }
        
        .add-tab {
            padding: 15px 25px;
            background: transparent;
            border: 2px dashed #666;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }
        
        .add-tab:hover {
            border-color: #00ff00;
            color: #00ff00;
        }
        
        /* Main Content */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 20px;
            overflow-y: auto;
        }
        
        .status-bar {
            background: #1a1a1a;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .conversation-area {
            flex: 1;
            background: #1a1a1a;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            overflow-y: auto;
            max-height: 400px;
        }
        
        .message {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 8px;
            animation: fadeIn 0.3s ease-in;
        }
        
        .user-message {
            background: #2a4a2a;
            border-left: 4px solid #00ff00;
        }
        
        .bot-message {
            background: #2a2a4a;
            border-left: 4px solid #4a9eff;
        }
        
        .control-panel {
            background: #1a1a1a;
            border-radius: 10px;
            padding: 20px;
        }
        
        .mic-button {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: #2a2a2a;
            border: 3px solid #00ff00;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            transition: all 0.3s;
            margin: 0 auto;
        }
        
        .mic-button:hover {
            background: #3a3a3a;
            transform: scale(1.05);
        }
        
        .mic-button.recording {
            background: #ff4444;
            border-color: #ff0000;
            animation: pulse 1.5s infinite;
        }
        
        .voice-select {
            margin-top: 20px;
            padding: 10px;
            background: #2a2a2a;
            border: 1px solid #666;
            color: #e0e0e0;
            border-radius: 5px;
            width: 100%;
        }
        
        .info-panel {
            margin-top: 20px;
            padding: 15px;
            background: #2a2a2a;
            border-radius: 8px;
            font-size: 14px;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.7); }
            70% { box-shadow: 0 0 0 20px rgba(255, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Modal for new tab */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
        }
        
        .modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #2a2a2a;
            padding: 30px;
            border-radius: 10px;
            border: 2px solid #00ff00;
            min-width: 400px;
        }
        
        .modal input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            background: #1a1a1a;
            border: 1px solid #666;
            color: #e0e0e0;
            border-radius: 5px;
        }
        
        .modal button {
            padding: 10px 20px;
            margin: 5px;
            background: #00ff00;
            color: #000;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .modal button:hover {
            background: #00cc00;
        }
        
        .modal button.cancel {
            background: #666;
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Tab Bar -->
        <div class="tab-container" id="tabContainer">
            <div class="add-tab" onclick="showNewTabModal()">+ New Tab</div>
        </div>
        
        <!-- Main Content -->
        <div class="main-content">
            <div class="status-bar">
                <div>
                    <h2 id="currentProject">Select or Create a Tab</h2>
                    <span id="sessionInfo"></span>
                </div>
                <div id="connectionStatus">
                    <span class="status-indicator">●</span> Disconnected
                </div>
            </div>
            
            <div class="conversation-area" id="conversationArea">
                <p style="text-align: center; color: #666;">Create a new tab to start a conversation</p>
            </div>
            
            <div class="control-panel">
                <button class="mic-button" id="micButton" onclick="toggleRecording()" disabled>
                    🎤
                </button>
                
                <select class="voice-select" id="voiceSelect">
                    <option value="alloy">Alloy (Neutral)</option>
                    <option value="echo">Echo (Male)</option>
                    <option value="fable">Fable (British)</option>
                    <option value="onyx">Onyx (Deep)</option>
                    <option value="nova">Nova (Female)</option>
                    <option value="shimmer">Shimmer (Soft)</option>
                </select>
                
                <div class="info-panel">
                    <div>Active Sessions: <span id="sessionCount">0</span>/4</div>
                    <div>Current Tab: <span id="currentTab">None</span></div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- New Tab Modal -->
    <div class="modal" id="newTabModal">
        <div class="modal-content">
            <h3>Create New Project Tab</h3>
            <input type="text" id="projectName" placeholder="Enter project name..." maxlength="50">
            <div style="margin-top: 20px;">
                <button onclick="createNewTab()">Create</button>
                <button class="cancel" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        let socket = null;
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        let recognition = null;
        let activeTabId = null;
        let tabs = {};
        let speechSynthesis = window.speechSynthesis;
        let currentUtterance = null;
        
        // Initialize WebSocket connection
        function initSocket() {
            socket = io();
            
            socket.on('connect', () => {
                document.getElementById('connectionStatus').innerHTML = 
                    '<span style="color: #00ff00;">●</span> Connected';
                console.log('Connected to orchestrator');
            });
            
            socket.on('disconnect', () => {
                document.getElementById('connectionStatus').innerHTML = 
                    '<span style="color: #ff0000;">●</span> Disconnected';
            });
            
            socket.on('response', (data) => {
                if (data.tab_id === activeTabId) {
                    handleResponse(data.text);
                }
            });
            
            socket.on('session_created', (data) => {
                updateSessionCount();
            });
            
            socket.on('session_closed', (data) => {
                updateSessionCount();
                if (data.tab_id === activeTabId) {
                    activeTabId = null;
                    updateUI();
                }
            });
        }
        
        // Tab Management
        function showNewTabModal() {
            if (Object.keys(tabs).length >= 4) {
                alert('Maximum 4 tabs allowed');
                return;
            }
            document.getElementById('newTabModal').style.display = 'block';
            document.getElementById('projectName').focus();
        }
        
        function closeModal() {
            document.getElementById('newTabModal').style.display = 'none';
            document.getElementById('projectName').value = '';
        }
        
        function createNewTab() {
            const projectName = document.getElementById('projectName').value.trim();
            if (!projectName) {
                alert('Please enter a project name');
                return;
            }
            
            const tabId = 'tab_' + Date.now();
            
            fetch('/create_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab_id: tabId, project_name: projectName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    tabs[tabId] = {
                        name: projectName,
                        messages: []
                    };
                    addTabToUI(tabId, projectName);
                    switchTab(tabId);
                    closeModal();
                } else {
                    alert('Failed to create session: ' + data.error);
                }
            });
        }
        
        function addTabToUI(tabId, projectName) {
            const tabContainer = document.getElementById('tabContainer');
            const addButton = tabContainer.querySelector('.add-tab');
            
            const tab = document.createElement('div');
            tab.className = 'tab';
            tab.id = tabId;
            tab.innerHTML = `
                <span onclick="switchTab('${tabId}')">${projectName}</span>
                <span class="tab-close" onclick="closeTab('${tabId}')">✕</span>
            `;
            
            tabContainer.insertBefore(tab, addButton);
        }
        
        function switchTab(tabId) {
            // Update active tab
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
            
            activeTabId = tabId;
            
            // Update UI
            const project = tabs[tabId];
            document.getElementById('currentProject').textContent = project.name;
            document.getElementById('currentTab').textContent = project.name;
            
            // Load conversation history
            const conversationArea = document.getElementById('conversationArea');
            conversationArea.innerHTML = '';
            
            if (project.messages.length === 0) {
                conversationArea.innerHTML = '<p style="text-align: center; color: #666;">Start your conversation...</p>';
            } else {
                project.messages.forEach(msg => {
                    addMessageToUI(msg.type, msg.text, false);
                });
            }
            
            // Enable microphone
            document.getElementById('micButton').disabled = false;
            
            // Notify server of tab switch
            if (socket) {
                socket.emit('switch_tab', { tab_id: tabId });
            }
        }
        
        function closeTab(tabId) {
            if (confirm('Close this tab? The session will be terminated.')) {
                fetch('/close_session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tab_id: tabId })
                })
                .then(() => {
                    document.getElementById(tabId).remove();
                    delete tabs[tabId];
                    
                    if (tabId === activeTabId) {
                        activeTabId = null;
                        updateUI();
                    }
                });
            }
        }
        
        function updateUI() {
            if (!activeTabId) {
                document.getElementById('currentProject').textContent = 'Select or Create a Tab';
                document.getElementById('currentTab').textContent = 'None';
                document.getElementById('conversationArea').innerHTML = 
                    '<p style="text-align: center; color: #666;">Create a new tab to start a conversation</p>';
                document.getElementById('micButton').disabled = true;
            }
        }
        
        function updateSessionCount() {
            fetch('/session_count')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('sessionCount').textContent = data.count;
                });
        }
        
        // Voice Recording
        function toggleRecording() {
            if (!activeTabId) {
                alert('Please select or create a tab first');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            const micButton = document.getElementById('micButton');
            micButton.classList.add('recording');
            isRecording = true;
            
            // Initialize speech recognition
            if ('webkitSpeechRecognition' in window) {
                recognition = new webkitSpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';
                
                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    console.log('Transcript:', transcript);
                    sendCommand(transcript);
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    stopRecording();
                };
                
                recognition.onend = () => {
                    stopRecording();
                };
                
                recognition.start();
            }
        }
        
        function stopRecording() {
            const micButton = document.getElementById('micButton');
            micButton.classList.remove('recording');
            isRecording = false;
            
            if (recognition) {
                recognition.stop();
            }
        }
        
        function sendCommand(command) {
            if (!activeTabId) return;
            
            // Add to UI
            addMessageToUI('user', command, true);
            
            // Send to server
            fetch('/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tab_id: activeTabId, 
                    command: command 
                })
            });
        }
        
        function addMessageToUI(type, text, save = true) {
            const conversationArea = document.getElementById('conversationArea');
            
            // Clear placeholder if exists
            if (conversationArea.querySelector('p')) {
                conversationArea.innerHTML = '';
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            messageDiv.textContent = text;
            conversationArea.appendChild(messageDiv);
            
            // Scroll to bottom
            conversationArea.scrollTop = conversationArea.scrollHeight;
            
            // Save to tab history
            if (save && activeTabId && tabs[activeTabId]) {
                tabs[activeTabId].messages.push({ type, text });
            }
        }
        
        function handleResponse(text) {
            // Add to UI
            addMessageToUI('bot', text, true);
            
            // Speak the response
            if (speechSynthesis) {
                // Cancel any ongoing speech
                speechSynthesis.cancel();
                
                currentUtterance = new SpeechSynthesisUtterance(text);
                currentUtterance.voice = getSelectedVoice();
                currentUtterance.rate = 1.0;
                currentUtterance.pitch = 1.0;
                
                speechSynthesis.speak(currentUtterance);
            }
        }
        
        function getSelectedVoice() {
            const voiceName = document.getElementById('voiceSelect').value;
            const voices = speechSynthesis.getVoices();
            
            // Try to find a matching voice
            for (let voice of voices) {
                if (voice.name.toLowerCase().includes(voiceName.toLowerCase())) {
                    return voice;
                }
            }
            
            // Default to first available voice
            return voices[0];
        }
        
        // Initialize on page load
        window.onload = () => {
            initSocket();
            updateSessionCount();
            
            // Load voices
            if (speechSynthesis) {
                speechSynthesis.onvoiceschanged = () => {
                    console.log('Voices loaded');
                };
            }
            
            // Keyboard shortcut for new tab
            document.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 't') {
                    e.preventDefault();
                    showNewTabModal();
                }
            });
        };
        
        // Handle page close
        window.onbeforeunload = () => {
            if (Object.keys(tabs).length > 0) {
                return 'You have active sessions. Are you sure you want to leave?';
            }
        };
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
    project_name = data.get('project_name')
    
    try:
        session = orchestrator.create_session(tab_id, project_name)
        
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
        
        return jsonify({
            'success': True,
            'session_id': session.session_id
        })
    except Exception as e:
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
        session_id = orchestrator.route_message(tab_id, command)
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/close_session', methods=['POST'])
def close_session():
    """Close a Claude session"""
    data = request.json
    tab_id = data.get('tab_id')
    
    try:
        # Stop capture thread
        if tab_id in capture_threads:
            # Thread will stop on next iteration
            del capture_threads[tab_id]
        
        if tab_id in response_queues:
            del response_queues[tab_id]
        
        orchestrator.cleanup_session(tab_id)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/session_count')
def session_count():
    """Get active session count"""
    return jsonify({
        'count': len(orchestrator.list_active_sessions())
    })

@socketio.on('switch_tab')
def handle_switch_tab(data):
    """Handle tab switch event"""
    tab_id = data.get('tab_id')
    orchestrator.switch_tab(tab_id)
    emit('tab_switched', {'tab_id': tab_id}, broadcast=True)

def capture_responses(session_id, tab_id):
    """Capture responses from Claude for a specific session"""
    last_content = ""
    
    while tab_id in capture_threads:
        try:
            # Capture current output
            content = orchestrator.capture_response(session_id)
            
            if content and content != last_content:
                # Look for new Claude responses
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    # Look for Claude's responses (gray circles)
                    if line.strip().startswith('●') and i > 0:
                        # Extract response text
                        response_text = line.strip()[1:].strip()
                        
                        # Skip tool calls and technical output
                        if not any(skip in response_text for skip in [
                            'Call(', 'Update(', 'Read(', 'Edit(', 'Write(',
                            'Bash(', 'MultiEdit(', 'Grep(', 'Glob(', 'LS(',
                            'TodoWrite(', 'Task(', 'ExitPlanMode(', 'Search(',
                            'WebFetch(', 'WebSearch(', 'NotebookRead(', 'NotebookEdit('
                        ]):
                            # Send response via WebSocket
                            socketio.emit('response', {
                                'tab_id': tab_id,
                                'text': response_text
                            })
                
                last_content = content
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error capturing response for session {session_id}: {e}")
            time.sleep(1)

if __name__ == '__main__':
    
    # SSL context for HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    print("\n" + "="*60)
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT")
    print("="*60)
    print("✨ Features:")
    print("  - Up to 4 simultaneous Claude sessions")
    print("  - Tab-based conversation isolation")
    print("  - Audio plays only for active tab")
    print("  - Centralized orchestration")
    print("")
    print("📱 Access at: https://192.168.40.232:8300")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=8300, ssl_context=context, allow_unsafe_werkzeug=True)