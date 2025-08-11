#!/usr/bin/env python3
"""
Multi-Tab Claude Voice Assistant with Stats Panel
Based on the single voice assistant interface with real-time stats
"""
from flask import Flask, render_template_string, request, jsonify, make_response
from flask_socketio import SocketIO, emit
import json
import time
import threading
import queue
from datetime import datetime
import ssl
import os
import subprocess
import re
import json as json_lib
from orchestrator_simple import orchestrator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-claude-secret-key-v2'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state for each tab
response_queues = {}  # tab_id -> queue
capture_threads = {}  # tab_id -> thread
active_tab_id = None
tab_stats = {}  # tab_id -> {"time": "", "tokens": "", "start_time": time}

# Permanent tabs configuration file
TABS_CONFIG_FILE = 'permanent_tabs.json'

def load_permanent_tabs():
    """Load permanent tabs configuration from file"""
    try:
        if os.path.exists(TABS_CONFIG_FILE):
            with open(TABS_CONFIG_FILE, 'r') as f:
                return json_lib.load(f)
    except Exception as e:
        print(f"Error loading permanent tabs: {e}")
    return {}

def save_permanent_tabs(tabs):
    """Save permanent tabs configuration to file"""
    try:
        with open(TABS_CONFIG_FILE, 'w') as f:
            json_lib.dump(tabs, f, indent=2)
    except Exception as e:
        print(f"Error saving permanent tabs: {e}")

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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Claude Voice Assistant v3</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='80' font-size='80'>🎙️</text></svg>">
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
            max-width: 1400px;
            margin: 0 auto;
            gap: 20px;
            height: calc(100vh - 40px);
        }
        
        /* Stats Panel - Left Side */
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
        
        .clock {
            font-size: 18px !important;
        }
        
        .real-time-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #00ff00;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 5px;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
        }
        
        /* Content Area - Right Side */
        .content-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        /* Tab Bar */
        .tab-bar {
            background: #111;
            border: 2px solid #0f0;
            border-radius: 10px;
            display: flex;
            align-items: center;
            padding: 5px;
            margin-bottom: 20px;
            overflow-x: auto;
        }
        
        .tab {
            background: #222;
            border: 1px solid #0f0;
            color: #0f0;
            padding: 8px 16px;
            margin-right: 5px;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            font-size: 14px;
            border-radius: 5px;
        }
        
        .tab:hover {
            background: #333;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }
        
        .tab.active {
            background: #0f0;
            color: #000;
            font-weight: bold;
        }
        
        .tab.permanent {
            border-color: #ffa500;
        }
        
        .permanent-indicator {
            color: #ffa500;
            margin-right: 5px;
            font-size: 12px;
        }
        
        .tab-close {
            cursor: pointer;
            font-size: 16px;
            opacity: 0.7;
        }
        
        .tab-close:hover {
            opacity: 1;
        }
        
        .tab-rename-input {
            background: #000;
            border: 1px solid #0f0;
            color: #0f0;
            padding: 4px 8px;
            font-size: 14px;
            width: 100px;
            outline: none;
        }
        
        .add-tab {
            background: transparent;
            border: 2px dashed #0f0;
            color: #0f0;
            padding: 8px 16px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 20px;
            border-radius: 5px;
        }
        
        .add-tab:hover {
            background: rgba(0, 255, 0, 0.1);
        }
        
        /* Main Content Card */
        .main-card {
            background: rgba(0, 10, 0, 0.9);
            border: 2px solid #0f0;
            border-radius: 20px;
            padding: 40px;
            flex: 1;
            display: flex;
            flex-direction: column;
            text-align: center;
        }
        
        .connection-indicator {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
        }
        
        .connection-dot {
            width: 10px;
            height: 10px;
            background: #ff0000;
            border-radius: 50%;
            transition: all 0.3s;
        }
        
        .connection-dot.connected {
            background: #00ff00;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.8);
        }
        
        h1 {
            margin: 20px 0;
            font-size: 2.5em;
        }
        
        .subtitle {
            color: #0f0;
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        
        .mic-container {
            margin: 30px 0;
        }
        
        .mic-button {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: #222;
            border: 3px solid #0f0;
            color: #0f0;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .mic-button:hover:not(.disabled) {
            transform: scale(1.1);
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.8);
        }
        
        .mic-button.active {
            background: #0f0;
            color: #000;
            animation: recording 1.5s infinite;
        }
        
        .mic-button.disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        
        @keyframes recording {
            0% { box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.8); }
            50% { box-shadow: 0 0 0 20px rgba(0, 255, 0, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); }
        }
        
        .status {
            height: 30px;
            color: #0f0;
            margin: 10px 0;
        }
        
        .voice-select {
            background: #222;
            border: 1px solid #0f0;
            color: #0f0;
            padding: 10px;
            border-radius: 5px;
            margin: 20px 0;
        }
        
        .conversation-log {
            flex: 1;
            background: #111;
            border: 1px solid #0f0;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            overflow-y: auto;
            text-align: left;
            max-height: 300px;
            min-height: 200px;
        }
        
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        
        .message.user {
            background: #1a3a1a;
            border-left: 3px solid #0f0;
        }
        
        .message.assistant {
            background: #1a1a3a;
            border-left: 3px solid #00f;
        }
        
        .info {
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
            animation: fadeIn 0.3s;
        }
        
        .modal-content {
            background-color: #222;
            margin: 15% auto;
            padding: 30px;
            border: 2px solid #0f0;
            width: 400px;
            border-radius: 10px;
            text-align: center;
        }
        
        .modal-close {
            color: #0f0;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .modal-close:hover {
            color: #fff;
        }
        
        .modal input {
            width: 100%;
            padding: 10px;
            margin: 20px 0;
            background: #111;
            border: 1px solid #0f0;
            color: #0f0;
            border-radius: 5px;
        }
        
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        
        .modal button {
            padding: 10px 20px;
            border: 1px solid #0f0;
            background: #222;
            color: #0f0;
            cursor: pointer;
            border-radius: 5px;
            transition: all 0.3s;
        }
        
        .modal button:hover {
            background: #0f0;
            color: #000;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Stats Panel -->
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
                <div id="clock" class="stats-value clock"></div>
            </div>
            
            <div class="stats-item">
                <div class="stats-label">ACTIVE TAB</div>
                <div style="font-size: 14px; color: #0f0;" id="activeTabName">None</div>
            </div>
            
            <div class="stats-item">
                <div class="stats-label">SESSION</div>
                <div class="stats-value" id="sessionTime">0s</div>
            </div>
        </div>
        
        <!-- Content Container -->
        <div class="content-container">
            <!-- Tab Bar -->
            <div class="tab-bar" id="tabBar">
                <button class="add-tab" onclick="showNewTabModal()">+</button>
            </div>
            
            <!-- Main Card -->
            <div class="main-card">
                <div class="connection-indicator">
                    <div class="connection-dot" id="connectionDot"></div>
                    <span id="connectionStatus">Disconnected</span>
                </div>
                
                <h1>🎙️ Claude Voice v3</h1>
                <div class="subtitle" id="subtitle">Create a tab to start</div>
                
                <div class="mic-container">
                    <button class="mic-button disabled" id="micButton" onclick="toggleRecording()">
                        🎤
                    </button>
                </div>
                
                <div class="status" id="status"></div>
                
                <select class="voice-select" id="voiceSelect">
                    <option value="alloy">Alloy (Neutral)</option>
                    <option value="echo">Echo (Male)</option>
                    <option value="fable">Fable (British)</option>
                    <option value="onyx">Onyx (Deep)</option>
                    <option value="nova">Nova (Female)</option>
                    <option value="shimmer">Shimmer (Soft)</option>
                </select>
                
                <div class="conversation-log" id="conversationLog">
                    <div style="text-align: center; color: #666;">No conversation yet</div>
                </div>
                
                <div class="info">
                    Multi-tab support • Up to 4 simultaneous sessions • Real-time voice interaction
                </div>
            </div>
        </div>
    </div>
    
    <!-- New Tab Modal -->
    <div class="modal" id="newTabModal">
        <div class="modal-content">
            <span class="modal-close" onclick="closeModal()">&times;</span>
            <h3>Create New Project Tab</h3>
            <input type="text" id="projectName" placeholder="Enter project name..." maxlength="30" autofocus>
            <div class="modal-buttons">
                <button onclick="closeModal()">Cancel</button>
                <button onclick="createNewTab()">Create</button>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js?v=20250802"></script>
    <script>
        // Global state
        let socket = null;
        let isRecording = false;
        let recognition = null;
        let activeTabId = null;
        let tabs = {};
        let audioContext = null;
        let voiceQueue = [];
        let isPlaying = false;
        
        // Initialize
        function init() {
            initSocket();
            initAudioContext();
            setupKeyboardShortcuts();
            updateClock();
            setInterval(updateClock, 1000);
            
            // Load saved voice preference
            const savedVoice = localStorage.getItem('selectedVoice');
            if (savedVoice) {
                document.getElementById('voiceSelect').value = savedVoice;
            }
            
            // Create 4 default tabs
            setTimeout(() => {
                createDefaultTabs();
            }, 500);
        }
        
        function createDefaultTabs() {
            // Load permanent tabs from server
            fetch('/get_permanent_tabs')
            .then(response => response.json())
            .then(data => {
                const permanentTabs = data.tabs || {};
                const tabCount = Object.keys(permanentTabs).length;
                
                if (tabCount === 0) {
                    // Create default tabs if none exist
                    const defaultNames = ['Project 1', 'Project 2', 'Project 3', 'Project 4'];
                    for (let i = 0; i < 4; i++) {
                        const tabId = 'permanent_' + i;
                        permanentTabs[tabId] = {
                            name: defaultNames[i],
                            order: i
                        };
                    }
                    // Save the default tabs
                    fetch('/save_permanent_tabs', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tabs: permanentTabs })
                    });
                }
                
                // Create tabs in order
                const sortedTabs = Object.entries(permanentTabs)
                    .sort((a, b) => (a[1].order || 0) - (b[1].order || 0));
                
                let tabsCreated = 0;
                
                function createNextTab() {
                    if (tabsCreated < sortedTabs.length) {
                        const [tabId, tabInfo] = sortedTabs[tabsCreated];
                        
                        fetch('/create_session', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                tab_id: tabId, 
                                project_name: tabInfo.name,
                                is_permanent: true
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                tabs[tabId] = {
                                    name: tabInfo.name,
                                    messages: [],
                                    startTime: Date.now(),
                                    isPermanent: true
                                };
                                addTabToUI(tabId, tabInfo.name, true);
                                
                                // Only switch to first tab
                                if (tabsCreated === 0) {
                                    switchTab(tabId);
                                }
                                
                                tabsCreated++;
                                setTimeout(createNextTab, 100);
                            }
                        });
                    } else {
                        updateAddButtonVisibility();
                    }
                }
                
                createNextTab();
            });
        }
        
        function updateClock() {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
            document.getElementById('clock').textContent = timeString;
        }
        
        // Socket.IO initialization
        function initSocket() {
            socket = io();
            
            socket.on('connect', () => {
                document.getElementById('connectionDot').classList.add('connected');
                document.getElementById('connectionStatus').textContent = 'Connected';
            });
            
            socket.on('disconnect', () => {
                document.getElementById('connectionDot').classList.remove('connected');
                document.getElementById('connectionStatus').textContent = 'Disconnected';
            });
            
            socket.on('response', (data) => {
                if (data.tab_id === activeTabId && data.text) {
                    handleResponse(data.text);
                }
            });
            
            socket.on('realtime_stats', (data) => {
                if (data.tab_id === activeTabId) {
                    // Update real-time stats display
                    document.getElementById('responseTime').textContent = data.time || '-';
                    document.getElementById('tokenCount').textContent = data.tokens || '-';
                }
            });
            
            socket.on('session_created', updateTabCount);
            socket.on('session_closed', updateTabCount);
        }
        
        // Audio context for better voice handling
        function initAudioContext() {
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            } catch (e) {
                console.error('Web Audio API not supported:', e);
            }
        }
        
        // Tab Management
        function updateAddButtonVisibility() {
            const tabCount = Object.keys(tabs).length;
            const addButton = document.querySelector('.add-tab');
            if (tabCount >= 4) {
                addButton.style.display = 'none';
            } else {
                addButton.style.display = 'block';
            }
        }
        
        function showNewTabModal() {
            const tabCount = Object.keys(tabs).length;
            if (tabCount >= 4) {
                alert('Maximum 4 tabs allowed. Please close a tab first.');
                return;
            }
            
            document.getElementById('newTabModal').style.display = 'block';
            document.getElementById('projectName').value = '';
            document.getElementById('projectName').focus();
        }
        
        function closeModal() {
            document.getElementById('newTabModal').style.display = 'none';
        }
        
        function createNewTab() {
            const projectName = document.getElementById('projectName').value.trim();
            if (!projectName) {
                alert('Please enter a project name');
                return;
            }
            
            const tabId = 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            
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
                        messages: [],
                        startTime: Date.now()
                    };
                    addTabToUI(tabId, projectName);
                    switchTab(tabId);
                    closeModal();
                    updateAddButtonVisibility();
                } else {
                    alert('Failed to create session: ' + data.error);
                }
            });
        }
        
        function addTabToUI(tabId, projectName, isPermanent = false) {
            const tabBar = document.getElementById('tabBar');
            const addButton = tabBar.querySelector('.add-tab');
            
            const tab = document.createElement('div');
            tab.className = 'tab' + (isPermanent ? ' permanent' : '');
            tab.id = tabId;
            tab.innerHTML = `
                ${isPermanent ? '<span class="permanent-indicator" title="Permanent Tab">📌</span>' : ''}
                <span class="tab-name" onclick="switchTab('${tabId}')" ondblclick="startRename('${tabId}')">${projectName}</span>
                <input type="text" class="tab-rename-input" style="display:none;" onblur="finishRename('${tabId}')" onkeypress="if(event.key==='Enter') finishRename('${tabId}')">
                ${!isPermanent ? `<span class="tab-close" onclick="closeTab('${tabId}')">×</span>` : ''}
            `;
            
            tabBar.insertBefore(tab, addButton);
        }
        
        function startRename(tabId) {
            const tab = document.getElementById(tabId);
            const nameSpan = tab.querySelector('.tab-name');
            const input = tab.querySelector('.tab-rename-input');
            
            input.value = tabs[tabId].name;
            nameSpan.style.display = 'none';
            input.style.display = 'block';
            input.focus();
            input.select();
        }
        
        function finishRename(tabId) {
            const tab = document.getElementById(tabId);
            const nameSpan = tab.querySelector('.tab-name');
            const input = tab.querySelector('.tab-rename-input');
            
            const newName = input.value.trim();
            if (newName && newName !== tabs[tabId].name) {
                tabs[tabId].name = newName;
                nameSpan.textContent = newName;
                
                // Update subtitle and active tab name if this is the active tab
                if (tabId === activeTabId) {
                    document.getElementById('subtitle').textContent = newName;
                    document.getElementById('activeTabName').textContent = newName;
                }
                
                // Update permanent tab name if it's permanent
                if (tabs[tabId].isPermanent) {
                    fetch('/update_permanent_tab', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tab_id: tabId, name: newName })
                    });
                }
            }
            
            nameSpan.style.display = 'block';
            input.style.display = 'none';
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
            document.getElementById('subtitle').textContent = project.name;
            document.getElementById('activeTabName').textContent = project.name;
            
            // Reset real-time stats display
            document.getElementById('responseTime').textContent = '-';
            document.getElementById('tokenCount').textContent = '-';
            
            // Update session time
            updateSessionTime();
            
            // Load conversation history
            const log = document.getElementById('conversationLog');
            log.innerHTML = '';
            
            if (project.messages.length === 0) {
                log.innerHTML = '<div style="text-align: center; color: #666;">Start your conversation...</div>';
            } else {
                project.messages.forEach(msg => {
                    addMessageToLog(msg.type, msg.text, false);
                });
            }
            
            // Enable microphone
            document.getElementById('micButton').classList.remove('disabled');
            
            // Clear any playing audio
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
            
            // Notify server
            if (socket) {
                socket.emit('switch_tab', { tab_id: tabId });
            }
        }
        
        function closeTab(tabId) {
            // Don't allow closing permanent tabs
            if (tabs[tabId] && tabs[tabId].isPermanent) {
                alert('Permanent tabs cannot be closed. You can rename them by double-clicking.');
                return;
            }
            
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
                        document.getElementById('subtitle').textContent = 'Create a tab to start';
                        document.getElementById('activeTabName').textContent = 'None';
                        document.getElementById('conversationLog').innerHTML = '<div style="text-align: center; color: #666;">No conversation yet</div>';
                        document.getElementById('micButton').classList.add('disabled');
                        document.getElementById('responseTime').textContent = '-';
                        document.getElementById('tokenCount').textContent = '-';
                        document.getElementById('sessionTime').textContent = '0s';
                    }
                    
                    updateTabCount();
                    updateAddButtonVisibility();
                });
            }
        }
        
        function updateTabCount() {
            const count = Object.keys(tabs).length;
            // Update any UI elements that show tab count if needed
        }
        
        function updateSessionTime() {
            if (!activeTabId || !tabs[activeTabId]) {
                document.getElementById('sessionTime').textContent = '0s';
                return;
            }
            
            const startTime = tabs[activeTabId].startTime;
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            
            if (elapsed < 60) {
                document.getElementById('sessionTime').textContent = elapsed + 's';
            } else if (elapsed < 3600) {
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                document.getElementById('sessionTime').textContent = minutes + 'm ' + seconds + 's';
            } else {
                const hours = Math.floor(elapsed / 3600);
                const minutes = Math.floor((elapsed % 3600) / 60);
                document.getElementById('sessionTime').textContent = hours + 'h ' + minutes + 'm';
            }
        }
        
        // Update session time every second
        setInterval(updateSessionTime, 1000);
        
        // Voice Recording
        function toggleRecording() {
            if (!activeTabId) {
                alert('Please create or select a tab first');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            if (!recognition) {
                recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.continuous = true;
                recognition.interimResults = true;
                
                recognition.onresult = (event) => {
                    const last = event.results.length - 1;
                    const transcript = event.results[last][0].transcript;
                    
                    if (event.results[last].isFinal) {
                        sendCommand(transcript);
                    } else {
                        document.getElementById('status').textContent = 'Listening: ' + transcript;
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    document.getElementById('status').textContent = 'Error: ' + event.error;
                    stopRecording();
                };
                
                recognition.onend = () => {
                    if (isRecording) {
                        recognition.start();
                    }
                };
            }
            
            recognition.start();
            isRecording = true;
            document.getElementById('micButton').classList.add('active');
            document.getElementById('status').textContent = 'Listening...';
        }
        
        function stopRecording() {
            if (recognition) {
                recognition.stop();
            }
            isRecording = false;
            document.getElementById('micButton').classList.remove('active');
            document.getElementById('status').textContent = '';
        }
        
        function sendCommand(text) {
            if (!text.trim() || !activeTabId) return;
            
            addMessageToLog('user', text);
            
            fetch('/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tab_id: activeTabId,
                    command: text 
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Failed to send command:', data.error);
                    addMessageToLog('error', 'Failed to send command: ' + data.error);
                }
            });
            
            document.getElementById('status').textContent = 'Processing...';
        }
        
        function handleResponse(text) {
            addMessageToLog('assistant', text);
            speakText(text);
        }
        
        function addMessageToLog(type, text, save = true) {
            const log = document.getElementById('conversationLog');
            
            if (log.children.length === 1 && log.children[0].textContent.includes('No conversation')) {
                log.innerHTML = '';
            }
            
            const message = document.createElement('div');
            message.className = 'message ' + type;
            
            const label = type === 'user' ? '🎤 You: ' : '🤖 Claude: ';
            message.innerHTML = `<strong>${label}</strong>${text}`;
            
            log.appendChild(message);
            log.scrollTop = log.scrollHeight;
            
            if (save && activeTabId && tabs[activeTabId]) {
                tabs[activeTabId].messages.push({ type, text });
            }
        }
        
        function speakText(text) {
            const voice = document.getElementById('voiceSelect').value;
            
            fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.audio) {
                    const audio = new Audio('data:audio/mp3;base64,' + data.audio);
                    audio.play();
                }
            });
        }
        
        // Keyboard shortcuts
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.key === ' ' && e.ctrlKey) {
                    e.preventDefault();
                    toggleRecording();
                } else if (e.key === 't' && e.ctrlKey) {
                    e.preventDefault();
                    showNewTabModal();
                } else if (e.key === 'Escape') {
                    closeModal();
                }
            });
        }
        
        // Initialize when page loads
        window.onload = init;
    </script>
</body>
</html>
'''

@app.route('/')
@app.route('/v3')
def index():
    # Add timestamp to template for cache busting
    import time as time_module
    template_with_timestamp = HTML_TEMPLATE.replace(
        '<script src="https://cdn.socket.io/4.5.4/socket.io.min.js?v=20250802"></script>',
        f'<script src="https://cdn.socket.io/4.5.4/socket.io.min.js?v={int(time_module.time())}"></script>'
    )
    
    # Add cache-control headers to prevent caching
    response = make_response(render_template_string(template_with_timestamp))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/get_permanent_tabs')
def get_permanent_tabs():
    """Get permanent tabs configuration"""
    tabs = load_permanent_tabs()
    return jsonify({'tabs': tabs})

@app.route('/save_permanent_tabs', methods=['POST'])
def save_permanent_tabs_route():
    """Save permanent tabs configuration"""
    data = request.json
    tabs = data.get('tabs', {})
    save_permanent_tabs(tabs)
    return jsonify({'success': True})

@app.route('/update_permanent_tab', methods=['POST'])
def update_permanent_tab():
    """Update a permanent tab's name"""
    data = request.json
    tab_id = data.get('tab_id')
    name = data.get('name')
    
    tabs = load_permanent_tabs()
    if tab_id in tabs:
        tabs[tab_id]['name'] = name
        save_permanent_tabs(tabs)
    
    return jsonify({'success': True})

@app.route('/create_session', methods=['POST'])
def create_session():
    """Create a new Claude session for a tab"""
    data = request.json
    tab_id = data.get('tab_id')
    project_name = data.get('project_name', 'Untitled')
    
    try:
        # Create a unique session for this tab
        session_id = f"claude_{tab_id}"
        orchestrator.create_session(tab_id, session_id)
        
        # Initialize response queue for this tab
        response_queues[tab_id] = queue.Queue()
        
        # Start capture thread for this tab
        capture_thread = threading.Thread(
            target=capture_responses,
            args=(session_id, tab_id),
            daemon=True
        )
        capture_thread.start()
        capture_threads[tab_id] = capture_thread
        
        socketio.emit('session_created', {'tab_id': tab_id}, broadcast=True)
        
        return jsonify({
            'success': True,
            'tab_id': tab_id,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/send_command', methods=['POST'])
def send_command():
    """Send a command to Claude in a specific tab"""
    data = request.json
    tab_id = data.get('tab_id')
    command = data.get('command')
    
    if not tab_id or not command:
        return jsonify({
            'success': False,
            'error': 'Missing tab_id or command'
        })
    
    try:
        session_id = f"claude_{tab_id}"
        orchestrator.send_command(session_id, command)
        
        return jsonify({'success': True})
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

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech using OpenAI API"""
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'nova')
    
    if not text:
        return jsonify({'success': False, 'error': 'No text provided'})
    
    try:
        # Get OpenAI API key from environment
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'OpenAI API key not configured'})
        
        import requests
        import base64
        
        # OpenAI TTS API endpoint
        url = "https://api.openai.com/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "tts-1",
            "input": text[:4096],  # Limit to 4096 characters
            "voice": voice,
            "response_format": "mp3"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            # Convert to base64 for sending to client
            audio_base64 = base64.b64encode(response.content).decode('utf-8')
            return jsonify({
                'success': True,
                'audio': audio_base64,
                'format': 'mp3'
            })
        else:
            return jsonify({
                'success': False,
                'error': f"OpenAI API error: {response.status_code}"
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('switch_tab')
def handle_switch_tab(data):
    """Handle tab switch event"""
    global active_tab_id
    tab_id = data.get('tab_id')
    active_tab_id = tab_id
    orchestrator.switch_tab(tab_id)
    emit('tab_switched', {'tab_id': tab_id}, broadcast=True)

def capture_responses(session_id, tab_id):
    """Capture responses from Claude for a specific session"""
    last_content = ""
    last_seen_lines = set()
    processed_responses = set()
    
    print(f"[CAPTURE] Started capture thread for tab {tab_id}, session {session_id}")
    
    while tab_id in capture_threads:
        try:
            # Capture current output
            content = orchestrator.capture_response(session_id)
            
            if content and content != last_content:
                lines = content.split('\n')
                
                # Process lines to find Claude's responses
                for line in lines:
                    line_hash = hash(line)
                    
                    # Skip already processed lines
                    if line_hash in last_seen_lines:
                        continue
                    
                    cleaned_line = line.strip()
                    
                    # Check for real-time stats
                    stats = extract_stats_from_output(cleaned_line)
                    if stats["time"] or stats["tokens"]:
                        # Update tab stats
                        if tab_id not in tab_stats:
                            tab_stats[tab_id] = {"time": "", "tokens": ""}
                        tab_stats[tab_id].update(stats)
                        
                        # Emit real-time stats update
                        socketio.emit('realtime_stats', {
                            'tab_id': tab_id,
                            'time': stats["time"],
                            'tokens': stats["tokens"]
                        })
                    
                    # Look for Claude's responses
                    is_claude_response = False
                    
                    if cleaned_line.startswith('●'):
                        is_claude_response = True
                    elif cleaned_line.startswith('Claude:'):
                        is_claude_response = True
                        cleaned_line = cleaned_line[7:].strip()
                    elif cleaned_line.startswith('Assistant:'):
                        is_claude_response = True  
                        cleaned_line = cleaned_line[10:].strip()
                    
                    if is_claude_response:
                        # Extract response text
                        if cleaned_line.startswith('●'):
                            response_text = cleaned_line[1:].strip()
                        else:
                            response_text = cleaned_line
                        
                        # Skip tool calls
                        tool_patterns = [
                            'List(.', 'Call(', 'Read(', 'Edit(', 'Write(',
                            'Bash(', 'MultiEdit(', 'Grep(', 'Glob(', 'LS(',
                            'WebFetch(', 'WebSearch(', 'NotebookRead(', 'NotebookEdit(',
                        ]
                        
                        is_tool_call = any(response_text.startswith(pattern) for pattern in tool_patterns)
                        if is_tool_call or len(response_text) < 3:
                            continue
                        
                        # Process valid responses
                        response_hash = hash(response_text)
                        if response_hash not in processed_responses:
                            processed_responses.add(response_hash)
                            last_seen_lines.add(line_hash)
                            
                            # Send response via WebSocket
                            socketio.emit('response', {
                                'tab_id': tab_id,
                                'text': response_text
                            })
                            
                            print(f"[RESPONSE] Tab {tab_id}: {response_text}")
                
                last_content = content
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error capturing response for session {session_id}: {e}")
            time.sleep(1)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT (WITH STATS)")
    print("="*60)
    print("✨ Features:")
    print("  - Real-time stats panel (TIME/TOKENS)")
    print("  - Up to 4 simultaneous Claude sessions")
    print("  - Tab bar for easy switching")
    print("  - Stats update for active tab only")
    print("")
    print("📱 Access at: http://192.168.40.232:8402/v3")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=8402, allow_unsafe_werkzeug=True)