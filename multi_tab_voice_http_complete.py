#!/usr/bin/env python3
"""
Multi-Tab Claude Voice Assistant V2 - Complete Version
With notification chime, bell toggle, and text input features
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
from orchestrator_simple_v2 import orchestrator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-claude-secret-key-v2'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state for each tab
response_queues = {}  # tab_id -> queue
capture_threads = {}  # tab_id -> thread
active_tab_id = None
tab_stats = {}  # tab_id -> {"time": "", "tokens": "", "start_time": time}

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
    <title>Multi-Tab Claude Voice Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #000;
            color: #0f0;
            font-family: 'Courier New', monospace;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        
        .tab-bar {
            background: #111;
            border-bottom: 2px solid #0f0;
            padding: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 60px;
            overflow-x: auto;
            overflow-y: hidden;
            white-space: nowrap;
        }
        
        .tab-bar::-webkit-scrollbar {
            height: 8px;
        }
        
        .tab-bar::-webkit-scrollbar-track {
            background: #111;
        }
        
        .tab-bar::-webkit-scrollbar-thumb {
            background: #0f0;
            border-radius: 4px;
        }
        
        .tab {
            padding: 8px 15px;
            margin: 0 3px;
            background: #222;
            border: 2px solid #0f0;
            border-radius: 5px 5px 0 0;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 4px;
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
        
        /* Notification styles for tabs */
        .tab.notification-yellow {
            background: #444400;
            border-color: #ffff00;
            box-shadow: 0 0 10px rgba(255, 255, 0, 0.5);
            animation: pulse-yellow 2s infinite;
        }
        
        .tab.notification-orange {
            background: #442200;
            border-color: #ff8800;
            box-shadow: 0 0 12px rgba(255, 136, 0, 0.6);
            animation: pulse-orange 1.5s infinite;
        }
        
        .tab.notification-red {
            background: #440000;
            border-color: #ff0000;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.6);
            animation: pulse-red 1s infinite;
        }
        
        /* Don't apply notification styles to active tab */
        .tab.active.notification-yellow,
        .tab.active.notification-orange,
        .tab.active.notification-red {
            background: #0f0;
            border-color: #0f0;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
            animation: none;
        }
        
        @keyframes pulse-yellow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        @keyframes pulse-orange {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        @keyframes pulse-red {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
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
            width: 120px;
            outline: none;
        }
        
        .add-tab {
            padding: 10px 15px;
            background: #111;
            border: 2px dashed #0f0;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
            opacity: 0.5;
        }
        
        .add-tab:hover {
            opacity: 1;
            background: #222;
        }
        
        .container {
            flex: 1;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: auto;
        }
        
        .main-card {
            background: #111;
            border: 2px solid #0f0;
            border-radius: 20px;
            padding: 30px;
            width: 100%;
            max-width: 800px;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }
        
        h1 {
            color: #0f0;
            text-align: center;
            margin: 15px 0;
            font-size: 20px;
            text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }
        
        .subtitle {
            text-align: center;
            font-size: 24px;
            color: #0f0;
            margin: 10px 0;
            text-shadow: 0 0 15px rgba(0, 255, 0, 0.8);
        }
        
        .mic-container {
            display: flex;
            justify-content: center;
            margin: 30px 0;
        }
        
        .mic-button {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: #0f0;
            border: 3px solid #0f0;
            font-size: 50px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.5);
            position: relative;
            overflow: hidden;
        }
        
        .mic-button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 50px rgba(0, 255, 0, 0.8);
        }
        
        .mic-button.recording {
            background: #f00;
            border-color: #f00;
            box-shadow: 0 0 50px rgba(255, 0, 0, 0.8);
            animation: pulse 1s infinite;
        }
        
        .mic-button.disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        
        .mic-button.disabled:hover {
            transform: none;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            transform: scale(0);
            animation: ripple-animation 0.6s ease-out;
        }
        
        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
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
            padding: 15px;
            margin-top: 15px;
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
            margin: 8px 0;
            padding: 8px;
            border-radius: 5px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .user-message {
            background: #001100;
            border-left: 3px solid #0f0;
        }
        
        .bot-message {
            background: #110011;
            border-left: 3px solid #f0f;
        }
        
        .timestamp {
            display: block;
            font-size: 10px;
            color: #666;
            margin-bottom: 4px;
        }
        
        .info {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            color: #666;
        }
        
        .connection-status {
            position: absolute;
            top: 10px;
            right: 10px;
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
        }
        
        .connection-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #f00;
        }
        
        .connection-dot.connected {
            background: #0f0;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
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
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.5);
            max-width: 400px;
            width: 90%;
        }
        
        .modal-header {
            font-size: 20px;
            margin-bottom: 20px;
            text-align: center;
            color: #0f0;
        }
        
        .modal-input {
            width: 100%;
            padding: 10px;
            background: #000;
            border: 2px solid #0f0;
            color: #0f0;
            font-size: 16px;
            border-radius: 5px;
            margin-bottom: 20px;
            outline: none;
        }
        
        .modal-input:focus {
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        }
        
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        
        .modal-button {
            padding: 10px 20px;
            background: #0f0;
            color: #000;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .modal-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
        }
        
        .modal-button.cancel {
            background: #333;
            color: #0f0;
        }
        
        .token-usage-box {
            background: #0a0a0a;
            border: 1px solid #0f0;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            font-family: 'Courier New', monospace;
        }
        
        .token-header {
            color: #0f0;
            font-size: 16px;
            margin-bottom: 10px;
            text-align: center;
            text-shadow: 0 0 5px rgba(0, 255, 0, 0.5);
        }
        
        .token-content {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }
        
        .token-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 10px;
            background: #111;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .token-label {
            color: #888;
        }
        
        .token-value {
            color: #0f0;
            font-weight: bold;
            text-shadow: 0 0 3px rgba(0, 255, 0, 0.3);
        }
        
        /* Control buttons container */
        .control-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 15px 0;
            align-items: center;
        }
        
        .control-button {
            padding: 8px 15px;
            background: #0f0;
            color: #000;
            border: 2px solid #0f0;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .control-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
        }
        
        .control-button.muted {
            background: #333;
            color: #999;
            border-color: #666;
        }
        
        .control-button.bell-off {
            background: #333;
            color: #999;
            border-color: #666;
        }
        
        /* Text input field */
        .text-input-container {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .text-input {
            flex: 1;
            padding: 10px;
            background: #111;
            border: 2px solid #0f0;
            color: #0f0;
            border-radius: 5px;
            font-size: 14px;
            font-family: 'Courier New', monospace;
            outline: none;
            transition: all 0.3s;
        }
        
        .text-input:focus {
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
        }
        
        .text-input::placeholder {
            color: #666;
        }
        
        .send-button {
            padding: 10px 20px;
            background: #0f0;
            color: #000;
            border: 2px solid #0f0;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .send-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
        }
        
        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
    </style>
</head>
<body>
    <!-- Tab Bar -->
    <div class="tab-bar" id="tabBar">
        <div class="add-tab" onclick="showNewTabModal()">+</div>
    </div>
    
    <!-- Debug Info -->
    <div id="debugBox" style="position: fixed; bottom: 10px; left: 10px; background: #111; border: 1px solid #0f0; padding: 10px; color: #0f0; font-size: 12px; z-index: 9999;">
        <button onclick="document.getElementById('debugBox').style.display='none'" style="position: absolute; top: 2px; right: 2px; background: transparent; border: none; color: #0f0; font-size: 16px; cursor: pointer; padding: 0 5px;">×</button>
        <div>Tab Bar Children: <span id="debugTabCount">0</span></div>
        <div>Tabs Object: <span id="debugTabsObject">{}</span></div>
        <button onclick="testAddTab()" style="margin-top: 5px; background: #0f0; color: #000; border: none; padding: 5px 10px; cursor: pointer;">Test Add Tab</button>
    </div>
    
    <!-- Main Container -->
    <div class="container">
        <div class="main-card">
            <!-- Connection Status -->
            <div class="connection-status">
                <div class="connection-dot" id="connectionDot"></div>
                <span id="connectionStatus">Connecting...</span>
            </div>
            
            <h1>🎙️ Claude Voice Assistant</h1>
            <div class="subtitle" id="subtitle">Select or create a tab</div>
            
            <!-- Control Buttons -->
            <div class="control-buttons">
                <button class="control-button" id="muteButton" onclick="toggleMute()">
                    <span id="muteIcon">🔊</span>
                    <span id="muteText">Mute</span>
                </button>
                <button class="control-button" id="bellButton" onclick="toggleBell()">
                    <span id="bellIcon">🔔</span>
                    <span id="bellText">Notifications</span>
                </button>
            </div>
            
            <div class="mic-container">
                <button class="mic-button disabled" id="micButton" onclick="toggleRecording()">
                    🎤
                </button>
            </div>
            
            <div class="status" id="status"></div>
            
            <!-- Text Input -->
            <div class="text-input-container">
                <input type="text" 
                       class="text-input" 
                       id="textInput" 
                       placeholder="Type your message here..." 
                       onkeypress="handleTextInputKeyPress(event)">
                <button class="send-button" 
                        id="sendButton" 
                        onclick="sendTextMessage()">
                    Send
                </button>
            </div>
            
            <select class="voice-select" id="voiceSelect">
                <option value="en-US-AriaNeural">Aria (Female, US)</option>
                <option value="en-US-JennyNeural">Jenny (Female, US)</option>
                <option value="en-US-GuyNeural">Guy (Male, US)</option>
                <option value="en-US-DavisNeural">Davis (Male, US)</option>
                <option value="en-GB-SoniaNeural">Sonia (Female, UK)</option>
                <option value="en-GB-RyanNeural">Ryan (Male, UK)</option>
                <option value="en-AU-NatashaNeural">Natasha (Female, AU)</option>
                <option value="en-AU-WilliamNeural">William (Male, AU)</option>
            </select>
            
            <div class="conversation-log" id="conversationLog">
                <div style="text-align: center; color: #666;">No conversation yet</div>
            </div>
            
            <!-- Token Usage Box -->
            <div class="token-usage-box" id="tokenUsageBox">
                <div class="token-header">📊 Session Stats</div>
                <div class="token-content">
                    <div class="token-item">
                        <span class="token-label">REAL-TIME:</span>
                        <span class="token-value">
                            <span id="realtimeTime">-</span> · <span id="realtimeTokens">-</span>
                        </span>
                    </div>
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
            
        </div>
    </div>
    
    <!-- New Tab Modal -->
    <div class="modal" id="newTabModal">
        <div class="modal-content">
            <div class="modal-header">Create New Tab</div>
            <input type="text" 
                   class="modal-input" 
                   id="newTabName" 
                   placeholder="Enter tab name..." 
                   maxlength="20"
                   onkeyup="handleModalKeyup(event)">
            <div class="modal-buttons">
                <button class="modal-button" onclick="createNewTab()">Create</button>
                <button class="modal-button cancel" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <script>
        // State management
        let socket = null;
        let isRecording = false;
        let recognition = null;
        let activeTabId = null;
        let tabs = {};
        let audioContext = null;
        let currentAudio = null;
        let isMuted = false;
        let bellEnabled = true;
        
        // Initialize
        function init() {
            initSocket();
            initAudioContext();
            setupKeyboardShortcuts();
            
            // Load saved preferences
            const savedVoice = localStorage.getItem('selectedVoice');
            if (savedVoice) {
                document.getElementById('voiceSelect').value = savedVoice;
            }
            
            // Load mute state
            const savedMute = localStorage.getItem('isMuted');
            if (savedMute === 'true') {
                isMuted = true;
                updateMuteButton();
            }
            
            // Load bell state
            const savedBell = localStorage.getItem('bellEnabled');
            if (savedBell === 'false') {
                bellEnabled = false;
                updateBellButton();
            }
            
            // Start stats update interval
            setInterval(updateStats, 1000);
        }
        
        // Initialize Web Audio API
        function initAudioContext() {
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            } catch (e) {
                console.error('Web Audio API not supported:', e);
            }
        }
        
        // Play notification chime
        function playChime() {
            if (!bellEnabled || !audioContext) return;
            
            try {
                const duration = 0.15;
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                // Create a pleasant chime sound
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
                oscillator.frequency.exponentialRampToValueAtTime(1200, audioContext.currentTime + duration * 0.5);
                oscillator.frequency.exponentialRampToValueAtTime(1000, audioContext.currentTime + duration);
                
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + duration);
            } catch (e) {
                console.error('Error playing chime:', e);
            }
        }
        
        // Toggle mute
        function toggleMute() {
            isMuted = !isMuted;
            localStorage.setItem('isMuted', isMuted);
            updateMuteButton();
            
            // If muting while audio is playing, stop it
            if (isMuted && currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            if (isMuted && window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
        }
        
        // Toggle bell notifications
        function toggleBell() {
            bellEnabled = !bellEnabled;
            localStorage.setItem('bellEnabled', bellEnabled);
            updateBellButton();
            
            // Play a test chime when enabling
            if (bellEnabled) {
                playChime();
            }
        }
        
        // Update mute button appearance
        function updateMuteButton() {
            const button = document.getElementById('muteButton');
            const icon = document.getElementById('muteIcon');
            const text = document.getElementById('muteText');
            
            if (isMuted) {
                button.classList.add('muted');
                icon.textContent = '🔇';
                text.textContent = 'Unmute';
            } else {
                button.classList.remove('muted');
                icon.textContent = '🔊';
                text.textContent = 'Mute';
            }
        }
        
        // Update bell button appearance
        function updateBellButton() {
            const button = document.getElementById('bellButton');
            const icon = document.getElementById('bellIcon');
            const text = document.getElementById('bellText');
            
            if (bellEnabled) {
                button.classList.remove('bell-off');
                icon.textContent = '🔔';
                text.textContent = 'Notifications';
            } else {
                button.classList.add('bell-off');
                icon.textContent = '🔕';
                text.textContent = 'Silent';
            }
        }
        
        // Update token usage stats
        function updateStats() {
            if (!activeTabId) {
                document.getElementById('inputTokens').textContent = '0';
                document.getElementById('outputTokens').textContent = '0';
                document.getElementById('totalTokens').textContent = '0';
                document.getElementById('sessionTime').textContent = '0s';
                return;
            }
            
            // Fetch stats from server
            fetch('/get_session_stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab_id: activeTabId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('inputTokens').textContent = data.input_tokens || '0';
                    document.getElementById('outputTokens').textContent = data.output_tokens || '0';
                    document.getElementById('totalTokens').textContent = data.total_tokens || '0';
                    
                    // Calculate session time
                    if (tabs[activeTabId] && tabs[activeTabId].startTime) {
                        const elapsed = Math.floor((Date.now() - tabs[activeTabId].startTime) / 1000);
                        const minutes = Math.floor(elapsed / 60);
                        const seconds = elapsed % 60;
                        document.getElementById('sessionTime').textContent = 
                            minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
                    }
                }
            })
            .catch(error => console.error('Error fetching stats:', error));
        }
        
        // Socket.IO connection
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
                if (data.text && data.tab_id) {
                    // Play chime for bot response (across all tabs)
                    playChime();
                    
                    // Store message for the tab that received it
                    if (tabs[data.tab_id]) {
                        tabs[data.tab_id].messages.push({
                            type: 'bot',
                            text: data.text,
                            timestamp: new Date().toLocaleTimeString()
                        });
                        
                        // Update notification state for inactive tabs
                        if (data.tab_id !== activeTabId) {
                            updateTabNotification(data.tab_id);
                        }
                    }
                    
                    // If it's the active tab, handle the response
                    if (data.tab_id === activeTabId) {
                        handleResponse(data.text);
                    }
                }
            });
            
            socket.on('realtime_stats', (data) => {
                if (data.tab_id === activeTabId) {
                    document.getElementById('realtimeTime').textContent = data.time || '-';
                    document.getElementById('realtimeTokens').textContent = data.tokens || '-';
                }
            });
        }
        
        // Update tab notification state based on time since last activity
        function updateTabNotification(tabId) {
            const tabElement = document.getElementById(tabId);
            if (!tabElement || tabElement.classList.contains('active')) return;
            
            const now = Date.now();
            const lastActivity = tabs[tabId].lastActivity || now;
            const timeSinceActivity = now - lastActivity;
            
            // Remove all notification classes first
            tabElement.classList.remove('notification-yellow', 'notification-orange', 'notification-red');
            
            // Apply appropriate notification level
            if (timeSinceActivity < 5000) { // Less than 5 seconds
                tabElement.classList.add('notification-yellow');
            } else if (timeSinceActivity < 30000) { // Less than 30 seconds
                tabElement.classList.add('notification-orange');
            } else { // More than 30 seconds
                tabElement.classList.add('notification-red');
            }
            
            // Update last activity
            tabs[tabId].lastActivity = now;
        }
        
        // Tab management
        function showNewTabModal() {
            if (Object.keys(tabs).length >= 4) {
                alert('Maximum 4 tabs allowed');
                return;
            }
            document.getElementById('newTabModal').classList.add('show');
            document.getElementById('newTabName').value = '';
            document.getElementById('newTabName').focus();
        }
        
        function closeModal() {
            document.getElementById('newTabModal').classList.remove('show');
        }
        
        function handleModalKeyup(event) {
            if (event.key === 'Enter') {
                createNewTab();
            } else if (event.key === 'Escape') {
                closeModal();
            }
        }
        
        function createNewTab() {
            const name = document.getElementById('newTabName').value.trim();
            if (!name) {
                alert('Please enter a tab name');
                return;
            }
            
            const tabId = 'tab_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
            
            // Create tab data
            tabs[tabId] = {
                id: tabId,
                name: name,
                messages: [],
                startTime: Date.now(),
                lastActivity: Date.now()
            };
            
            // Add to UI
            addTabToUI(tabId, name);
            
            // Create session on server
            fetch('/create_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tab_id: tabId,
                    project_name: name 
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    tabs[tabId].sessionId = data.session_id;
                    switchTab(tabId);
                    closeModal();
                    updateTabCount();
                }
            })
            .catch(error => {
                console.error('Error creating session:', error);
                delete tabs[tabId];
                document.getElementById(tabId).remove();
            });
        }
        
        function addTabToUI(tabId, name) {
            const tabBar = document.getElementById('tabBar');
            const addButton = tabBar.querySelector('.add-tab');
            
            const tabDiv = document.createElement('div');
            tabDiv.className = 'tab';
            tabDiv.id = tabId;
            tabDiv.innerHTML = `
                <span class="tab-name" ondblclick="startRenameTab('${tabId}')">${name}</span>
                <span class="tab-close" onclick="closeTab('${tabId}', event)">×</span>
            `;
            tabDiv.onclick = (e) => {
                if (!e.target.classList.contains('tab-close')) {
                    switchTab(tabId);
                }
            };
            
            tabBar.insertBefore(tabDiv, addButton);
            
            // Hide add button if we have 4 tabs
            if (Object.keys(tabs).length >= 4) {
                addButton.style.display = 'none';
            }
        }
        
        function switchTab(tabId) {
            if (!tabs[tabId] || activeTabId === tabId) return;
            
            // Update active tab
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
                // Remove notification classes when switching to a tab
                if (tab.id === tabId) {
                    tab.classList.remove('notification-yellow', 'notification-orange', 'notification-red');
                }
            });
            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
            }
            
            activeTabId = tabId;
            
            // Update UI
            const project = tabs[tabId];
            document.getElementById('subtitle').textContent = project.name;
            
            // Update stats immediately
            updateStats();
            
            // Load conversation history
            const log = document.getElementById('conversationLog');
            log.innerHTML = '';
            
            if (project.messages.length === 0) {
                log.innerHTML = '<div style="text-align: center; color: #666;">Start your conversation...</div>';
            } else {
                project.messages.forEach(msg => {
                    addMessageToLog(msg.type, msg.text, false, msg.timestamp);
                });
            }
            
            // Enable microphone
            document.getElementById('micButton').classList.remove('disabled');
            
            // Clear any playing audio
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
            
            // Notify server
            if (socket) {
                socket.emit('switch_tab', { tab_id: tabId });
            }
        }
        
        function closeTab(tabId, event) {
            event.stopPropagation();
            
            if (!tabs[tabId]) return;
            
            // Remove from UI
            document.getElementById(tabId).remove();
            
            // Remove from server
            fetch('/close_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab_id: tabId })
            });
            
            // Remove from local state
            delete tabs[tabId];
            
            // If this was the active tab, switch to another
            if (activeTabId === tabId) {
                activeTabId = null;
                const remainingTabs = Object.keys(tabs);
                if (remainingTabs.length > 0) {
                    switchTab(remainingTabs[0]);
                } else {
                    document.getElementById('subtitle').textContent = 'Select or create a tab';
                    document.getElementById('conversationLog').innerHTML = '<div style="text-align: center; color: #666;">No conversation yet</div>';
                    document.getElementById('micButton').classList.add('disabled');
                }
            }
            
            // Show add button if we have less than 4 tabs
            if (Object.keys(tabs).length < 4) {
                document.querySelector('.add-tab').style.display = 'block';
            }
            
            updateTabCount();
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
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
                
                let finalTranscript = '';
                let silenceTimer = null;
                
                recognition.onresult = (event) => {
                    clearTimeout(silenceTimer);
                    
                    let interimTranscript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript + ' ';
                        } else {
                            interimTranscript = transcript;
                        }
                    }
                    
                    const currentTranscript = finalTranscript + interimTranscript;
                    document.getElementById('status').textContent = currentTranscript || 'Listening...';
                    
                    // Set silence timer - stop after 2 seconds of silence
                    silenceTimer = setTimeout(() => {
                        if (finalTranscript.trim()) {
                            sendCommand(finalTranscript.trim());
                        }
                        stopRecording();
                    }, 2000);
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    let errorMsg = 'Error: ' + event.error;
                    
                    // Check if it's a permission/security error
                    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                        errorMsg = 'Microphone access denied. Please allow microphone access and ensure you are using HTTPS.';
                        if (window.location.protocol !== 'https:') {
                            errorMsg = 'Microphone requires HTTPS. Please use https:// instead of http://';
                        }
                    } else if (event.error === 'network') {
                        errorMsg = 'Network error. Check your internet connection.';
                    } else if (event.error === 'no-speech') {
                        errorMsg = 'No speech detected. Please try again.';
                    }
                    
                    document.getElementById('status').textContent = errorMsg;
                    if (silenceTimer) {
                        clearTimeout(silenceTimer);
                    }
                    stopRecording();
                };
                
                recognition.onend = () => {
                    if (silenceTimer) {
                        clearTimeout(silenceTimer);
                    }
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
        
        function sendTextMessage() {
            const input = document.getElementById('textInput');
            const text = input.value.trim();
            
            if (!text || !activeTabId) return;
            
            sendCommand(text);
            input.value = '';
            input.focus();
        }
        
        function handleTextInputKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendTextMessage();
            }
        }
        
        function handleResponse(text) {
            addMessageToLog('bot', text, true);
            speakText(text);
        }
        
        function addMessageToLog(type, text, save = true, existingTimestamp = null) {
            const log = document.getElementById('conversationLog');
            
            // Clear placeholder
            if (log.querySelector('div[style*="text-align: center"]')) {
                log.innerHTML = '';
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            
            const timestamp = existingTimestamp || new Date().toLocaleTimeString();
            messageDiv.innerHTML = `
                <span class="timestamp">${timestamp}</span>
                ${text}
            `;
            
            log.appendChild(messageDiv);
            log.scrollTop = log.scrollHeight;
            
            // Save to tab history
            if (save && activeTabId && tabs[activeTabId]) {
                tabs[activeTabId].messages.push({ 
                    type, 
                    text, 
                    timestamp: timestamp 
                });
            }
        }
        
        function speakText(text) {
            if (isMuted) return;
            
            // Cancel any ongoing speech
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            // Also cancel browser speech synthesis
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
            
            const selectedVoice = document.getElementById('voiceSelect').value;
            console.log('Speaking with voice:', selectedVoice);
            console.log('Text to speak:', text.substring(0, 50) + '...');
            
            // Use Edge-TTS server for high-quality voices
            // Use same protocol as current page to avoid mixed content issues
            const protocol = window.location.protocol;
            const ttsUrl = protocol === 'https:' 
                ? 'https://192.168.40.232:5001/tts'
                : 'http://192.168.40.232:5001/tts';
            
            fetch(ttsUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    voice: selectedVoice,
                    rate: '+0%',  // Normal speed
                    pitch: '+0Hz', // Normal pitch
                    volume: '+0%'  // Normal volume
                })
            })
            .then(response => {
                console.log('Edge-TTS response status:', response.status);
                if (!response.ok) {
                    throw new Error('TTS request failed');
                }
                return response.blob();
            })
            .then(blob => {
                console.log('Got audio blob, size:', blob.size);
                // Create audio element and play
                const audioUrl = URL.createObjectURL(blob);
                currentAudio = new Audio(audioUrl);
                currentAudio.volume = 1.0;
                
                // Clean up when done
                currentAudio.addEventListener('ended', () => {
                    URL.revokeObjectURL(audioUrl);
                    currentAudio = null;
                });
                
                currentAudio.play().then(() => {
                    console.log('Audio playing successfully with voice:', selectedVoice);
                }).catch(error => {
                    console.error('Audio playback error:', error);
                    // Fallback to browser speech synthesis
                    fallbackToWebSpeech(text);
                });
            })
            .catch(error => {
                console.error('Edge-TTS error:', error);
                // Fallback to browser speech synthesis
                fallbackToWebSpeech(text);
            });
        }
        
        function fallbackToWebSpeech(text) {
            console.log('Falling back to Web Speech API');
            if (window.speechSynthesis && !isMuted) {
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
                } else if (e.ctrlKey && e.key === 'w' && activeTabId) {
                    e.preventDefault();
                    closeTab(activeTabId, e);
                } else if (e.key === ' ' && !e.target.matches('input, textarea')) {
                    e.preventDefault();
                    toggleRecording();
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
                const size = 100;
                const x = size / 2;
                const y = size / 2;
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = (x - size / 2) + 'px';
                ripple.style.top = (y - size / 2) + 'px';
                this.appendChild(ripple);
                
                setTimeout(() => ripple.remove(), 600);
            }
        });
        
        // Tab rename functionality
        function startRenameTab(tabId) {
            const tabElement = document.getElementById(tabId);
            const nameSpan = tabElement.querySelector('.tab-name');
            const currentName = nameSpan.textContent;
            
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'tab-rename-input';
            input.value = currentName;
            input.maxLength = 20;
            
            input.onblur = () => finishRenameTab(tabId, input.value);
            input.onkeyup = (e) => {
                if (e.key === 'Enter') {
                    finishRenameTab(tabId, input.value);
                } else if (e.key === 'Escape') {
                    finishRenameTab(tabId, currentName);
                }
            };
            
            nameSpan.replaceWith(input);
            input.focus();
            input.select();
        }
        
        function finishRenameTab(tabId, newName) {
            const tabElement = document.getElementById(tabId);
            const input = tabElement.querySelector('.tab-rename-input');
            
            if (!input) return;
            
            newName = newName.trim() || tabs[tabId].name;
            tabs[tabId].name = newName;
            
            const nameSpan = document.createElement('span');
            nameSpan.className = 'tab-name';
            nameSpan.textContent = newName;
            nameSpan.ondblclick = () => startRenameTab(tabId);
            
            input.replaceWith(nameSpan);
            
            if (activeTabId === tabId) {
                document.getElementById('subtitle').textContent = newName;
            }
        }
        
        // Debug functions
        function updateTabCount() {
            document.getElementById('debugTabCount').textContent = 
                document.querySelectorAll('.tab').length;
            document.getElementById('debugTabsObject').textContent = 
                JSON.stringify(Object.keys(tabs));
        }
        
        function testAddTab() {
            const testTabId = 'tab_test_' + Date.now();
            tabs[testTabId] = {
                id: testTabId,
                name: 'Test Tab ' + Object.keys(tabs).length,
                messages: [],
                startTime: Date.now()
            };
            addTabToUI(testTabId, tabs[testTabId].name);
            updateTabCount();
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
            console.log('[INIT] Creating default tabs...');
            
            // Create 4 tabs programmatically
            const tabNames = ['Tab 1', 'Tab 2', 'Tab 3', 'Tab 4'];
            const promises = [];
            
            tabNames.forEach((name, index) => {
                const tabId = 'tab_' + Date.now() + '_' + index;
                
                // Create tab data
                tabs[tabId] = {
                    id: tabId,
                    name: name,
                    messages: [],
                    startTime: Date.now()
                };
                
                // Add to UI immediately - tabs appear instantly
                addTabToUI(tabId, name);
                
                // Create session on server
                const promise = fetch('/create_session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        tab_id: tabId,
                        project_name: name 
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        tabs[tabId].sessionId = data.session_id;
                        console.log(`[INIT] Created session for ${name}: ${data.session_id}`);
                    }
                })
                .catch(error => {
                    console.error(`[INIT] Error creating session for ${name}:`, error);
                });
                
                promises.push(promise);
            });
            
            // After all sessions are created, switch to first tab
            Promise.all(promises).then(() => {
                const firstTabId = Object.keys(tabs)[0];
                if (firstTabId) {
                    switchTab(firstTabId);
                }
                updateTabCount();
            });
            
            // Hide add button since we have 4 tabs
            document.querySelector('.add-tab').style.display = 'none';
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/create_session', methods=['POST'])
def create_session():
    """Create a new Claude session for a tab"""
    data = request.json
    tab_id = data.get('tab_id')
    project_name = data.get('project_name', 'Untitled')
    
    try:
        print(f"[CREATE_SESSION] Creating session for tab {tab_id}, project: {project_name}")
        session_id = orchestrator.create_session(tab_id, project_name)
        print(f"[CREATE_SESSION] Session created: {session_id}")
        
        # Start response capture thread
        thread = threading.Thread(
            target=capture_responses, 
            args=(session_id, tab_id),
            daemon=True
        )
        thread.start()
        capture_threads[tab_id] = thread
        print(f"[CREATE] Started capture thread for tab {tab_id}, session {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        print(f"[CREATE_SESSION] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/close_session', methods=['POST'])
def close_session():
    """Close a Claude session"""
    data = request.json
    tab_id = data.get('tab_id')
    
    try:
        orchestrator.close_session(tab_id)
        if tab_id in capture_threads:
            del capture_threads[tab_id]
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        }), 500

@app.route('/get_session_stats', methods=['POST'])
def get_session_stats():
    """Get token usage stats for a session"""
    data = request.json
    tab_id = data.get('tab_id')
    
    try:
        stats = orchestrator.get_session_stats(tab_id)
        return jsonify({
            'success': True,
            'input_tokens': stats.get('input_tokens', 0),
            'output_tokens': stats.get('output_tokens', 0),
            'total_tokens': stats.get('total_tokens', 0)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"[SOCKET] Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"[SOCKET] Client disconnected: {request.sid}")

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
    
    while True:
        if tab_id not in capture_threads:
            print(f"[CAPTURE] Stopping capture thread for tab {tab_id}")
            break
            
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
                    
                    # Look for Claude's responses (multiple patterns)
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
                        print(f"[CAPTURE] Found Claude response for tab {tab_id}: {response_text[:50]}...")
                        
                        # Skip tool call patterns
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
    print("\n" + "="*60)
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT V2 (HTTP)")
    print("="*60)
    print("✨ Features:")
    print("  - Interface matching port 8103 style")
    print("  - Up to 4 simultaneous Claude sessions")
    print("  - Tab bar at top for easy switching")
    print("  - Audio plays only for active tab")
    print("  - Notification chime for all bot responses")
    print("  - Bell toggle button for silent mode")
    print("  - Text input field for typing messages")
    print("")
    print("📱 Access at: http://192.168.40.232:8402")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=8402, allow_unsafe_werkzeug=True)