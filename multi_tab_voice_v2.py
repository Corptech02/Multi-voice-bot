#!/usr/bin/env python3
"""
Multi-Tab Claude Voice Assistant V2
Based on the single voice assistant interface with added tab support
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
import subprocess
import re
from orchestrator_simple import orchestrator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-claude-secret-key-v2'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state for each tab
response_queues = {}  # tab_id -> queue
capture_threads = {}  # tab_id -> thread
active_tab_id = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='80' font-size='80'>🎙️</text></svg>">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
            background: #000;
            color: #0f0;
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
            margin: 0;
            padding: 0;
        }
        
        /* Tab Bar */
        .tab-bar {
            background: #111;
            border-bottom: 2px solid #0f0;
            display: flex;
            align-items: center;
            padding: 0 10px;
            min-height: 45px;
            overflow-x: auto;
            scrollbar-width: thin;
            scrollbar-color: #0f0 #111;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
        }
        
        .tab-bar::-webkit-scrollbar {
            height: 6px;
        }
        
        .tab-bar::-webkit-scrollbar-track {
            background: #111;
        }
        
        .tab-bar::-webkit-scrollbar-thumb {
            background: #0f0;
            border-radius: 3px;
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
            position: relative;
            font-size: 14px;
            height: 35px;
        }
        
        .tab:hover {
            background: #333;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }
        
        .tab.active {
            background: #0f0;
            color: #000;
            font-weight: bold;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
        }
        
        .tab-close {
            cursor: pointer;
            font-size: 16px;
            margin-left: 8px;
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
        
        .tab-name {
            cursor: pointer;
            user-select: none;
        }
        
        .add-tab {
            background: transparent;
            border: 2px dashed #0f0;
            color: #0f0;
            padding: 8px 16px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 40px;
        }
        
        .add-tab:hover {
            background: rgba(0, 255, 0, 0.1);
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }
        
        /* Main Container - matches 8103 style */
        .container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            padding-top: 65px;
            position: relative;
            overflow: hidden;
        }
        
        .main-card {
            background: rgba(0, 10, 0, 0.9);
            border: 2px solid #0f0;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            max-height: 90vh;
            box-shadow: 0 0 40px rgba(0, 255, 0, 0.3);
            position: relative;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        h1 {
            color: #0f0;
            text-align: center;
            margin-bottom: 10px;
            font-size: 36px;
            text-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
            animation: glow 2s ease-in-out infinite alternate;
        }
        
        .subtitle {
            text-align: center;
            color: #0a0;
            margin-bottom: 30px;
            font-size: 18px;
        }
        
        .mic-container {
            display: flex;
            justify-content: center;
            margin: 20px 0;
            flex-shrink: 0;
        }
        
        .mic-button {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: radial-gradient(circle, #0f0, #090);
            border: 3px solid #0f0;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 50px;
            transition: all 0.3s;
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.5);
            position: relative;
            overflow: hidden;
        }
        
        .mic-button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 50px rgba(0, 255, 0, 0.8);
        }
        
        .mic-button.recording {
            animation: pulse 1.5s infinite;
            background: radial-gradient(circle, #f00, #900);
            border-color: #f00;
            box-shadow: 0 0 50px rgba(255, 0, 0, 0.8);
        }
        
        .mic-button.disabled {
            opacity: 0.5;
            cursor: not-allowed;
            background: radial-gradient(circle, #666, #333);
            border-color: #666;
            box-shadow: none;
        }
        
        .mic-button.disabled:hover {
            transform: none;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.15); }
            100% { transform: scale(1); }
        }
        
        @keyframes glow {
            from { text-shadow: 0 0 20px rgba(0, 255, 0, 0.8); }
            to { text-shadow: 0 0 30px rgba(0, 255, 0, 1), 0 0 40px rgba(0, 255, 0, 0.8); }
        }
        
        .status {
            text-align: center;
            margin: 20px 0;
            font-size: 16px;
            color: #0a0;
            min-height: 24px;
        }
        
        .voice-select {
            width: 100%;
            padding: 12px;
            background: #111;
            border: 2px solid #0f0;
            color: #0f0;
            border-radius: 10px;
            font-size: 16px;
            margin-top: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .voice-select:hover {
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        }
        
        .voice-select:focus {
            outline: none;
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.8);
        }
        
        .conversation-log {
            background: #111;
            border: 2px solid #0f0;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            height: 250px;
            min-height: 250px;
            max-height: 250px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            scrollbar-width: thin;
            scrollbar-color: #0f0 #111;
            flex-shrink: 0;
        }
        
        .conversation-log::-webkit-scrollbar {
            width: 8px;
        }
        
        .conversation-log::-webkit-scrollbar-track {
            background: #111;
        }
        
        .conversation-log::-webkit-scrollbar-thumb {
            background: #0f0;
            border-radius: 4px;
        }
        
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            background: rgba(0, 255, 0, 0.1);
            border-left: 3px solid #0f0;
            color: #0f0;
        }
        
        .bot-message {
            background: rgba(0, 100, 255, 0.1);
            border-left: 3px solid #0af;
            color: #0af;
        }
        
        .timestamp {
            font-size: 12px;
            color: #666;
            margin-right: 10px;
        }
        
        /* Visual feedback elements */
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(0, 255, 0, 0.6);
            transform: scale(0);
            animation: ripple 0.6s ease-out;
            pointer-events: none;
        }
        
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        /* Connection indicator */
        .connection-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
        }
        
        .connection-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #f00;
            transition: background 0.3s;
        }
        
        .connection-dot.connected {
            background: #0f0;
            animation: pulse-dot 2s infinite;
        }
        
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Modal for new tab */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.show {
            display: flex;
        }
        
        .modal-content {
            background: #111;
            border: 2px solid #0f0;
            border-radius: 10px;
            padding: 30px;
            min-width: 400px;
            box-shadow: 0 0 40px rgba(0, 255, 0, 0.5);
            position: relative;
        }
        
        .modal-close {
            position: absolute;
            top: 10px;
            right: 10px;
            background: transparent;
            border: none;
            color: #0f0;
            font-size: 28px;
            cursor: pointer;
            width: 30px;
            height: 30px;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.3s;
        }
        
        .modal-close:hover {
            background: rgba(0, 255, 0, 0.1);
            transform: scale(1.1);
        }
        
        .modal h3 {
            color: #0f0;
            margin-bottom: 20px;
        }
        
        .modal input {
            width: 100%;
            padding: 12px;
            background: #000;
            border: 2px solid #0f0;
            color: #0f0;
            border-radius: 5px;
            font-size: 16px;
            margin-bottom: 20px;
        }
        
        .modal input:focus {
            outline: none;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        }
        
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        
        .modal button {
            padding: 10px 20px;
            background: #0f0;
            color: #000;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .modal button:hover {
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
        }
        
        .modal button.cancel {
            background: #333;
            color: #0f0;
            border: 2px solid #0f0;
        }
        
        /* Token usage box */
        .token-usage-box {
            background: #111;
            border: 1px solid #0f0;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            animation: glow 3s ease-in-out infinite;
            flex-shrink: 0;
        }
        
        .token-header {
            color: #0f0;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            text-align: center;
        }
        
        .token-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .token-item {
            display: flex;
            justify-content: space-between;
            padding: 5px;
            background: #0a0a0a;
            border-radius: 4px;
        }
        
        .token-label {
            color: #999;
            font-size: 14px;
        }
        
        .token-value {
            color: #0f0;
            font-weight: bold;
            font-size: 14px;
        }
        
        /* Info text */
        .info {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            color: #0a0;
            opacity: 0.8;
        }
        
        /* Tab count indicator */
        .tab-count {
            position: absolute;
            top: 10px;
            left: 10px;
            font-size: 14px;
            color: #0a0;
        }
    </style>
</head>
<body>
    <!-- Tab Bar -->
    <div class="tab-bar" id="tabBar">
        <div class="add-tab" onclick="showNewTabModal()">+</div>
    </div>
    
    <!-- Debug Info -->
    <div style="position: fixed; bottom: 10px; left: 10px; background: #111; border: 1px solid #0f0; padding: 10px; color: #0f0; font-size: 12px; z-index: 9999;">
        <div>Tab Bar Children: <span id="debugTabCount">0</span></div>
        <div>Tabs Object: <span id="debugTabsObject">{}</span></div>
        <button onclick="testAddTab()" style="margin-top: 5px; background: #0f0; color: #000; border: none; padding: 5px 10px; cursor: pointer;">Test Add Tab</button>
    </div>
    
    <!-- Main Container -->
    <div class="container">
        <div class="main-card">
            <div class="connection-indicator">
                <div class="connection-dot" id="connectionDot"></div>
                <span id="connectionStatus">Disconnected</span>
            </div>
            
            <div class="tab-count" id="tabCount">No active tabs</div>
            
            <h1>🎙️ Claude Voice</h1>
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
            
            <!-- Token Usage Box -->
            <div class="token-usage-box" id="tokenUsageBox">
                <div class="token-header">📊 Session Stats</div>
                <div class="token-content">
                    <div class="token-item">
                        <span class="token-label">Input Tokens:</span>
                        <span class="token-value" id="inputTokens">0</span>
                    </div>
                    <div class="token-item">
                        <span class="token-label">Output Tokens:</span>
                        <span class="token-value" id="outputTokens">0</span>
                    </div>
                    <div class="token-item">
                        <span class="token-label">Total Tokens:</span>
                        <span class="token-value" id="totalTokens">0</span>
                    </div>
                    <div class="token-item">
                        <span class="token-label">Session Time:</span>
                        <span class="token-value" id="sessionTime">0s</span>
                    </div>
                </div>
            </div>
            
            <div class="info">
                Multi-tab support • Up to 4 simultaneous sessions • Real-time voice interaction
                <button onclick="resetTabs()" style="margin-left: 20px; background: #333; border: 1px solid #0f0; color: #0f0; padding: 5px 10px; cursor: pointer; font-size: 12px;">Reset Tabs</button>
            </div>
            
            <!-- Debug input for testing -->
            <div style="margin-top: 20px; text-align: center;">
                <input type="text" id="debugInput" placeholder="Type and press Enter to test" 
                       style="background: #111; border: 1px solid #0f0; color: #0f0; padding: 8px; width: 300px;"
                       onkeypress="if(event.key==='Enter') { sendCommand(this.value); this.value=''; }">
            </div>
        </div>
    </div>
    
    <!-- New Tab Modal -->
    <div class="modal" id="newTabModal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
            <h3>Create New Project Tab</h3>
            <input type="text" id="projectName" placeholder="Enter project name..." maxlength="30" autofocus>
            <div class="modal-buttons">
                <button class="cancel" onclick="closeModal()">Cancel</button>
                <button onclick="createNewTab()">Create</button>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
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
            
            // Load saved voice preference
            const savedVoice = localStorage.getItem('selectedVoice');
            if (savedVoice) {
                document.getElementById('voiceSelect').value = savedVoice;
            }
            
            // Start stats update interval
            setInterval(updateStats, 1000); // Update every second
        }
        
        // Update token usage stats
        function updateStats() {
            if (!activeTabId) {
                // No active tab, show zeros
                document.getElementById('inputTokens').textContent = '0';
                document.getElementById('outputTokens').textContent = '0';
                document.getElementById('totalTokens').textContent = '0';
                document.getElementById('sessionTime').textContent = '0s';
                return;
            }
            
            fetch('/get_session_stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab_id: activeTabId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.stats) {
                    document.getElementById('inputTokens').textContent = data.stats.input_tokens.toLocaleString();
                    document.getElementById('outputTokens').textContent = data.stats.output_tokens.toLocaleString();
                    document.getElementById('totalTokens').textContent = data.stats.total_tokens.toLocaleString();
                    document.getElementById('sessionTime').textContent = data.stats.session_time;
                }
            })
            .catch(error => {
                console.error('Error fetching stats:', error);
            });
        }
        
        // Socket.IO connection
        function initSocket() {
            socket = io();
            
            socket.on('connect', () => {
                document.getElementById('connectionDot').classList.add('connected');
                document.getElementById('connectionStatus').textContent = 'Connected';
                console.log('Connected to server');
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
        
        // Tab management
        function showNewTabModal() {
            if (Object.keys(tabs).length >= 4) {
                alert('Maximum 4 tabs allowed');
                return;
            }
            document.getElementById('newTabModal').classList.add('show');
            document.getElementById('projectName').value = '';
            document.getElementById('projectName').focus();
        }
        
        function closeModal() {
            document.getElementById('newTabModal').classList.remove('show');
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
            console.log(`Adding tab to UI: ${tabId} - ${projectName}`);
            const tabBar = document.getElementById('tabBar');
            const addButton = tabBar.querySelector('.add-tab');
            
            const tab = document.createElement('div');
            tab.className = 'tab';
            tab.id = tabId;
            tab.innerHTML = `
                <span class="tab-name" onclick="switchTab('${tabId}')" ondblclick="startRename('${tabId}')">${projectName}</span>
                <input type="text" class="tab-rename-input" style="display:none;" onblur="finishRename('${tabId}')" onkeypress="if(event.key==='Enter') finishRename('${tabId}')">
            `;
            
            tabBar.insertBefore(tab, addButton);
            console.log(`Tab added to DOM. Total tabs in DOM: ${tabBar.querySelectorAll('.tab').length}`);
            
            // Update debug info
            updateDebugInfo();
        }
        
        function updateDebugInfo() {
            const tabBar = document.getElementById('tabBar');
            const tabCount = tabBar.querySelectorAll('.tab').length;
            document.getElementById('debugTabCount').textContent = tabCount;
            document.getElementById('debugTabsObject').textContent = JSON.stringify(Object.keys(tabs));
        }
        
        function testAddTab() {
            const testTabId = 'test_tab_' + Date.now();
            tabs[testTabId] = { name: 'Test Tab', messages: [] };
            addTabToUI(testTabId, 'Test Tab');
            console.log('Test tab added');
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
                
                // Update subtitle if this is the active tab
                if (tabId === activeTabId) {
                    document.getElementById('subtitle').textContent = newName;
                }
                
                // Save updated tabs to localStorage
                localStorage.setItem('multiTabSessions', JSON.stringify(tabs));
            }
            
            nameSpan.style.display = 'block';
            input.style.display = 'none';
        }
        
        function switchTab(tabId) {
            console.log(`Switching to tab: ${tabId}`);
            
            // Update active tab
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
                console.log(`Tab ${tabId} activated`);
            } else {
                console.error(`Tab ${tabId} not found in DOM!`);
            }
            
            activeTabId = tabId;
            
            // Update UI
            const project = tabs[tabId];
            document.getElementById('subtitle').textContent = project.name;
            
            // Update stats immediately when switching tabs
            updateStats();
            
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
                        document.getElementById('conversationLog').innerHTML = 
                            '<div style="text-align: center; color: #666;">No conversation yet</div>';
                        document.getElementById('micButton').classList.add('disabled');
                    }
                    
                    updateTabCount();
                });
            }
        }
        
        function updateTabCount() {
            const count = Object.keys(tabs).length;
            const text = count === 0 ? 'No active tabs' : 
                        count === 1 ? '1 active tab' : 
                        `${count} active tabs`;
            document.getElementById('tabCount').textContent = text;
        }
        
        // Voice recording
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
            const micButton = document.getElementById('micButton');
            micButton.classList.add('recording');
            isRecording = true;
            
            document.getElementById('status').textContent = 'Listening...';
            
            if ('webkitSpeechRecognition' in window) {
                recognition = new webkitSpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';
                
                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    sendCommand(transcript);
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    document.getElementById('status').textContent = 'Error: ' + event.error;
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
            
            document.getElementById('status').textContent = '';
            
            if (recognition) {
                recognition.stop();
            }
        }
        
        function sendCommand(command) {
            if (!activeTabId) return;
            
            addMessageToLog('user', command, true);
            
            fetch('/send_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tab_id: activeTabId, 
                    command: command 
                })
            });
        }
        
        function handleResponse(text) {
            addMessageToLog('bot', text, true);
            speakText(text);
        }
        
        function addMessageToLog(type, text, save = true) {
            const log = document.getElementById('conversationLog');
            
            // Clear placeholder
            if (log.querySelector('div[style*="text-align: center"]')) {
                log.innerHTML = '';
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            
            const timestamp = new Date().toLocaleTimeString();
            messageDiv.innerHTML = `
                <span class="timestamp">${timestamp}</span>
                ${text}
            `;
            
            log.appendChild(messageDiv);
            log.scrollTop = log.scrollHeight;
            
            // Save to tab history
            if (save && activeTabId && tabs[activeTabId]) {
                tabs[activeTabId].messages.push({ type, text });
            }
        }
        
        function speakText(text) {
            if (window.speechSynthesis) {
                // Cancel any ongoing speech
                window.speechSynthesis.cancel();
                
                const utterance = new SpeechSynthesisUtterance(text);
                const selectedVoice = document.getElementById('voiceSelect').value;
                
                // Try to find matching voice
                const voices = window.speechSynthesis.getVoices();
                for (let voice of voices) {
                    if (voice.name.toLowerCase().includes(selectedVoice.toLowerCase())) {
                        utterance.voice = voice;
                        break;
                    }
                }
                
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                utterance.volume = 1.0;
                
                window.speechSynthesis.speak(utterance);
            }
        }
        
        // Keyboard shortcuts
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 't') {
                    e.preventDefault();
                    showNewTabModal();
                } else if (e.key === 'Enter' && document.getElementById('newTabModal').classList.contains('show')) {
                    createNewTab();
                } else if (e.key === 'Escape' && document.getElementById('newTabModal').classList.contains('show')) {
                    closeModal();
                }
            });
        }
        
        // Save voice preference
        document.getElementById('voiceSelect').addEventListener('change', (e) => {
            localStorage.setItem('selectedVoice', e.target.value);
        });
        
        // Visual feedback
        document.getElementById('micButton').addEventListener('click', function(e) {
            if (!this.classList.contains('disabled')) {
                // Create ripple effect
                const ripple = document.createElement('span');
                ripple.className = 'ripple';
                ripple.style.width = ripple.style.height = '40px';
                ripple.style.left = '40px';
                ripple.style.top = '40px';
                this.appendChild(ripple);
                
                setTimeout(() => ripple.remove(), 600);
            }
        });
        
        // Handle page close
        window.onbeforeunload = () => {
            if (Object.keys(tabs).length > 0) {
                return 'You have active sessions. Are you sure you want to leave?';
            }
        };
        
        // Load voices when available
        if (window.speechSynthesis) {
            window.speechSynthesis.onvoiceschanged = () => {
                console.log('Voices loaded');
            };
        }
        
        // OLD Auto-create function - no longer used
        function autoCreateTabs_OLD() {
            console.log('Starting autoCreateTabs...');
            console.log('Current tabs object:', tabs);
            console.log('Tab bar current state:', document.getElementById('tabBar').innerHTML);
            
            // Check if tabs already exist in localStorage
            const savedTabs = localStorage.getItem('multiTabSessions');
            if (savedTabs) {
                console.log('Found saved tabs:', savedTabs);
                try {
                    const tabData = JSON.parse(savedTabs);
                    console.log('Parsed tab data:', tabData);
                    
                    // Clear existing tabs first
                    tabs = {};
                    document.querySelectorAll('.tab').forEach(tab => tab.remove());
                    
                    // Restore existing tabs - need to recreate sessions
                    let restoredCount = 0;
                    const tabEntries = Object.entries(tabData);
                    
                    function restoreNextTab() {
                        if (restoredCount < tabEntries.length && restoredCount < 4) {
                            const [oldTabId, tabInfo] = tabEntries[restoredCount];
                            const newTabId = 'tab_' + Date.now() + '_' + restoredCount;
                            
                            console.log(`Restoring tab: ${tabInfo.name}`);
                            
                            // Create new session for this tab
                            fetch('/create_session', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ tab_id: newTabId, project_name: tabInfo.name })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    tabs[newTabId] = {
                                        name: tabInfo.name,
                                        messages: tabInfo.messages || []
                                    };
                                    addTabToUI(newTabId, tabInfo.name);
                                    
                                    if (restoredCount === 0) {
                                        switchTab(newTabId);
                                    }
                                    
                                    restoredCount++;
                                    setTimeout(restoreNextTab, 500);
                                }
                            })
                            .catch(error => {
                                console.error('Failed to restore tab:', error);
                                restoredCount++;
                                setTimeout(restoreNextTab, 500);
                            });
                        } else {
                            // All tabs restored
                            if (Object.keys(tabs).length >= 4) {
                                document.querySelector('.add-tab').style.display = 'none';
                            }
                            updateTabCount();
                            localStorage.setItem('multiTabSessions', JSON.stringify(tabs));
                        }
                    }
                    
                    restoreNextTab();
                    return;
                } catch (e) {
                    console.error('Error parsing saved tabs:', e);
                    localStorage.removeItem('multiTabSessions');
                }
            }
            
            console.log('No saved tabs, creating new ones...');
            
            // Create new tabs if none exist
            const defaultProjects = [
                'Tab 1',
                'Tab 2', 
                'Tab 3',
                'Tab 4'
            ];
            
            let tabsCreated = 0;
            
            function createNextTab() {
                if (tabsCreated < 4) {
                    const tabId = 'tab_' + Date.now() + '_' + tabsCreated;
                    const projectName = defaultProjects[tabsCreated];
                    
                    fetch('/create_session', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tab_id: tabId, project_name: projectName })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            console.log(`Tab ${tabsCreated + 1} created successfully`);
                            tabs[tabId] = {
                                name: projectName,
                                messages: []
                            };
                            addTabToUI(tabId, projectName);
                            
                            // Activate first tab
                            if (tabsCreated === 0) {
                                switchTab(tabId);
                            }
                            
                            tabsCreated++;
                            
                            // Create next tab after a short delay
                            setTimeout(createNextTab, 500);
                            
                            // Hide add button after all tabs created
                            if (tabsCreated === 4) {
                                document.querySelector('.add-tab').style.display = 'none';
                                updateTabCount();
                                // Save tabs to localStorage
                                localStorage.setItem('multiTabSessions', JSON.stringify(tabs));
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Failed to create tab:', error);
                        tabsCreated++;
                        setTimeout(createNextTab, 500);
                    });
                }
            }
            
            // Start creating tabs
            createNextTab();
        }
        
        // Reset tabs function
        function resetTabs() {
            if (confirm('This will reset all tabs. Are you sure?')) {
                localStorage.removeItem('multiTabSessions');
                location.reload();
            }
        }
        
        // Initialize on load
        window.onload = () => {
            init();
            // Create default tabs immediately
            createDefaultTabs();
        };
        
        // Also ensure tabs are created if page loads differently
        document.addEventListener('DOMContentLoaded', function() {
            if (Object.keys(tabs).length === 0) {
                setTimeout(createDefaultTabs, 500);
            }
        });
        
        // Simple function to create 4 tabs immediately
        function createDefaultTabs() {
            // Prevent multiple calls
            if (window.tabsAlreadyCreated) {
                console.log('Tabs already created, skipping...');
                return;
            }
            window.tabsAlreadyCreated = true;
            
            console.log('Creating default tabs...');
            
            // Clear any existing tabs first
            tabs = {};
            document.querySelectorAll('.tab').forEach(tab => tab.remove());
            
            // Always create exactly 4 tabs
            const tabNames = ['Tab 1', 'Tab 2', 'Tab 3', 'Tab 4'];
            
            // Create all 4 tabs immediately in the UI
            for (let i = 0; i < 4; i++) {
                const tabId = `tab_${Date.now()}_${i}`;
                const tabName = tabNames[i];
                
                // Add to tabs object
                tabs[tabId] = {
                    name: tabName,
                    messages: []
                };
                
                // Add to UI immediately - tabs appear instantly
                addTabToUI(tabId, tabName);
            }
            
            // Activate first tab immediately
            const firstTabId = Object.keys(tabs)[0];
            if (firstTabId) {
                switchTab(firstTabId);
            }
            
            // Hide add button
            document.querySelector('.add-tab').style.display = 'none';
            updateTabCount();
            
            // Save tabs immediately
            localStorage.setItem('multiTabSessions', JSON.stringify(tabs));
            
            // Create sessions in background (won't delay tab display)
            createSessionsInBackground();
        }
        
        // Create sessions for all tabs in background
        function createSessionsInBackground() {
            console.log('Starting createSessionsInBackground...');
            const tabIds = Object.keys(tabs);
            console.log(`Creating sessions for ${tabIds.length} tabs:`, tabIds);
            
            if (tabIds.length === 0) {
                console.error('No tabs to create sessions for!');
                return;
            }
            
            let sessionIndex = 0;
            
            function createNextSession() {
                if (sessionIndex >= tabIds.length) {
                    console.log('All sessions created');
                    return;
                }
                
                const tabId = tabIds[sessionIndex];
                const tabInfo = tabs[tabId];
                console.log(`Creating session ${sessionIndex + 1}/${tabIds.length} for tab: ${tabId}, name: ${tabInfo.name}`);
                
                fetch('/create_session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tab_id: tabId, project_name: tabInfo.name })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        console.log(`✓ Session created for ${tabInfo.name} (${data.session_id})`);
                    } else {
                        console.error(`✗ Failed to create session for ${tabInfo.name}:`, data.error);
                    }
                    sessionIndex++;
                    setTimeout(createNextSession, 100); // Small delay between sessions
                })
                .catch(error => {
                    console.error(`✗ Error creating session for ${tabInfo.name}:`, error);
                    sessionIndex++;
                    setTimeout(createNextSession, 100);
                });
            }
            
            // Start creating sessions
            createNextSession();
        }
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
    
    print(f"[CREATE_SESSION] Creating session for tab {tab_id}, project: {project_name}")
    
    try:
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
        
        # Ensure the session is properly tracked
        global active_sessions
        if 'active_sessions' not in globals():
            active_sessions = {}
        active_sessions[tab_id] = session.session_id
        
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
        print(f"[SEND] Sending '{command}' to tab {tab_id}")
        
        session_id = orchestrator.route_message(tab_id, command)
        print(f"[SEND] Message sent to session {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test_send', methods=['GET'])
def test_send():
    """Test endpoint to verify sending works"""
    return jsonify({
        'active_sessions': len(orchestrator.sessions),
        'sessions': list(orchestrator.sessions.keys())
    })

@app.route('/check_session', methods=['POST'])
def check_session():
    """Check if a session exists for a tab"""
    data = request.json
    tab_id = data.get('tab_id')
    
    # Check if session exists
    session_exists = tab_id in orchestrator.sessions
    
    return jsonify({
        'exists': session_exists,
        'tab_id': tab_id
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

@app.route('/get_session_stats', methods=['POST'])
def get_session_stats():
    """Get session statistics for a tab"""
    data = request.json
    tab_id = data.get('tab_id')
    
    try:
        session_info = orchestrator.get_session_info(tab_id)
        if session_info:
            return jsonify({
                'success': True,
                'stats': {
                    'input_tokens': session_info['input_tokens'],
                    'output_tokens': session_info['output_tokens'],
                    'total_tokens': session_info['total_tokens'],
                    'session_time': session_info['session_duration_formatted']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@socketio.on('switch_tab')
def handle_switch_tab(data):
    """Handle tab switch event"""
    global active_tab_id
    tab_id = data.get('tab_id')
    active_tab_id = tab_id
    orchestrator.switch_tab(tab_id)
    emit('tab_switched', {'tab_id': tab_id}, broadcast=True)

def capture_responses(session_id, tab_id):
    """Capture responses from Claude for a specific session - matches 8103 style"""
    last_content = ""
    last_seen_lines = set()
    processed_responses = set()
    
    print(f"[CAPTURE] Started capture thread for tab {tab_id}, session {session_id}")
    
    while tab_id in capture_threads:
        try:
            # Capture current output
            content = orchestrator.capture_response(session_id)
            
            if content and content != last_content:
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
                    
                    # Look for Claude's responses (multiple patterns)
                    # Pattern 1: Gray circles (●)
                    # Pattern 2: Assistant responses after "Claude:" or similar
                    is_claude_response = False
                    
                    if cleaned_line.startswith('●'):
                        is_claude_response = True
                    elif cleaned_line.startswith('Claude:'):
                        is_claude_response = True
                        cleaned_line = cleaned_line[7:].strip()  # Remove "Claude:" prefix
                    elif cleaned_line.startswith('Assistant:'):
                        is_claude_response = True  
                        cleaned_line = cleaned_line[10:].strip()  # Remove "Assistant:" prefix
                    
                    if is_claude_response:
                        # Extract response text
                        if cleaned_line.startswith('●'):
                            response_text = cleaned_line[1:].strip()
                        else:
                            response_text = cleaned_line  # Already cleaned for other patterns
                        print(f"[CAPTURE] Found Claude response for tab {tab_id}: {response_text[:50]}...")
                        
                        # Skip ONLY obvious tool call patterns at the start
                        # Allow mentions of tools in normal conversation
                        tool_start_patterns = [
                            'List(.', 'Call(', 'Read(', 'Edit(', 'Write(',
                            'Bash(', 'MultiEdit(', 'Grep(', 'Glob(', 'LS(',
                            'WebFetch(', 'WebSearch(', 'NotebookRead(', 'NotebookEdit(',
                        ]
                        
                        # Skip if it starts with a tool call
                        is_tool_call = any(response_text.startswith(pattern) for pattern in tool_start_patterns)
                        if is_tool_call:
                            continue
                            
                        # Skip very short responses
                        if len(response_text) < 3:
                            continue
                        
                        # Process valid responses
                        if True:
                            
                            response_hash = hash(response_text)
                            if response_hash not in processed_responses:
                                processed_responses.add(response_hash)
                                last_seen_lines.add(line_hash)
                                
                                # Send response via WebSocket
                                socketio.emit('response', {
                                    'tab_id': tab_id,
                                    'text': response_text
                                })
                                
                                # Store in orchestrator
                                orchestrator.store_bot_response(tab_id, response_text)
                                
                                print(f"[RESPONSE] Tab {tab_id}: {response_text}")
                
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
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT V2")
    print("="*60)
    print("✨ Features:")
    print("  - Interface matching port 8103 style")
    print("  - Up to 4 simultaneous Claude sessions")
    print("  - Tab bar at top for easy switching")
    print("  - Audio plays only for active tab")
    print("")
    print("📱 Access at: https://192.168.40.232:8400")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=8400, ssl_context=context, allow_unsafe_werkzeug=True)