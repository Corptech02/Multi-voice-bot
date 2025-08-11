#!/usr/bin/env python3
"""
Claude Voice Bot with Edge TTS for Better Voice Options
- Uses edge-tts for high-quality male and female voices
- Microsoft's neural voices
- Free and high quality
"""
from flask import Flask, render_template_string, request, jsonify, send_file
import subprocess
import ssl
import time
from datetime import datetime
import threading
import queue
import re
import os
import tempfile
import asyncio
import edge_tts
import base64
import io

app = Flask(__name__)

# Queue to store Claude's responses
response_queue = queue.Queue()

# Track conversation state
last_command = ""
last_command_time = 0
processed_responses = set()
current_stats = {"time": "", "tokens": ""}
is_claude_thinking = False

# Available Edge TTS voices
EDGE_VOICES = {
    # US Voices
    'en-US-JennyNeural': {'name': 'Jenny (US Female)', 'gender': 'Female', 'locale': 'en-US'},
    'en-US-GuyNeural': {'name': 'Guy (US Male)', 'gender': 'Male', 'locale': 'en-US'},
    'en-US-AriaNeural': {'name': 'Aria (US Female)', 'gender': 'Female', 'locale': 'en-US'},
    'en-US-DavisNeural': {'name': 'Davis (US Male)', 'gender': 'Male', 'locale': 'en-US'},
    'en-US-JasonNeural': {'name': 'Jason (US Male)', 'gender': 'Male', 'locale': 'en-US'},
    'en-US-TonyNeural': {'name': 'Tony (US Male)', 'gender': 'Male', 'locale': 'en-US'},
    
    # UK Voices  
    'en-GB-SoniaNeural': {'name': 'Sonia (UK Female)', 'gender': 'Female', 'locale': 'en-GB'},
    'en-GB-RyanNeural': {'name': 'Ryan (UK Male)', 'gender': 'Male', 'locale': 'en-GB'},
    'en-GB-LibbyNeural': {'name': 'Libby (UK Female)', 'gender': 'Female', 'locale': 'en-GB'},
    'en-GB-ThomasNeural': {'name': 'Thomas (UK Male)', 'gender': 'Male', 'locale': 'en-GB'},
    
    # Australian Voices
    'en-AU-NatashaNeural': {'name': 'Natasha (AU Female)', 'gender': 'Female', 'locale': 'en-AU'},
    'en-AU-WilliamNeural': {'name': 'William (AU Male)', 'gender': 'Male', 'locale': 'en-AU'},
}

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
    global current_stats, is_claude_thinking
    
    permission_detected = False
    permission_responded = False
    
    while True:
        try:
            if not last_command:
                time.sleep(1)
                continue
                
            # Check for permission prompts immediately
            if time.time() - last_command_time > 0.5:
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                    capture_output=True,
                    text=True
                )
                output = result.stdout.lower()
                
                # Check for permission prompts
                if any(prompt in output for prompt in ['permission', 'approve', 'continue?', 'y/n', 'yes/no', 'press enter', 'auto-accept']):
                    if not permission_responded:
                        print("[AUTO-APPROVE] Detected permission prompt, sending approval...")
                        # Send approval
                        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'y'], check=True)
                        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                        permission_detected = True
                        permission_responded = True
                        time.sleep(1)
                        continue
                
            # Wait longer if we just handled permissions
            wait_time = 5 if permission_detected else 3
            if time.time() - last_command_time < wait_time:
                time.sleep(0.5)
                continue
                
            # Capture entire pane to ensure we get the full response
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout
            
            # Update stats
            current_stats = extract_stats_from_output(output)
            
            # Check if Claude is thinking
            if any(indicator in output for indicator in ['Simmering', 'Deciphering', 'tokens', 'esc to interrupt']):
                is_claude_thinking = True
            else:
                is_claude_thinking = False
            
            if last_command in output:
                # Find all occurrences of the command
                cmd_positions = [i for i in range(len(output)) if output.startswith(last_command, i)]
                
                if cmd_positions:
                    # Use the last occurrence
                    last_pos = cmd_positions[-1]
                    after_command = output[last_pos + len(last_command):].strip()
                    
                    # Look for Claude's response more intelligently
                    response_lines = []
                    lines = output.split('\n')
                    
                    # Find the last occurrence of the command
                    cmd_line_idx = -1
                    for idx in range(len(lines) - 1, -1, -1):
                        if last_command in lines[idx]:
                            cmd_line_idx = idx
                            break
                    
                    if cmd_line_idx >= 0:
                        # Start capturing immediately after the command line
                        capture_started = False
                        
                        for i in range(cmd_line_idx + 1, len(lines)):
                            line = lines[i]
                            
                            # Start capturing when we see any non-empty, non-UI content
                            if not capture_started:
                                stripped_line = line.strip()
                                # Skip empty lines and obvious UI elements
                                if (stripped_line and 
                                    not any(x in line for x in ['>', '│', '╭', '╰', '⏵', '⎿', 'tokens', 'esc to interrupt', 'Simmering', 'Deciphering'])):
                                    capture_started = True
                            
                            # Stop at next prompt or system message
                            if ('Human:' in line or 'The user sent' in line or line.startswith('$') or '╭───' in line):
                                break
                            
                            if capture_started or (line.strip() and not any(x in line for x in ['>', '│', '╭', '╰', '⏵', '⎿'])):
                                # Clean the line
                                cleaned_line = line.strip()
                                
                                # Skip UI elements and system messages
                                if (cleaned_line and 
                                    not cleaned_line.startswith('>') and
                                    not cleaned_line.startswith('╭') and
                                    not cleaned_line.startswith('│') and
                                    not cleaned_line.startswith('╰') and
                                    not cleaned_line.startswith('⏵') and
                                    not cleaned_line.startswith('✽') and
                                    not cleaned_line.startswith('✢') and
                                    not cleaned_line.startswith('✻') and
                                    not cleaned_line.startswith('✶') and
                                    not cleaned_line.startswith('*') and
                                    '🤖' not in cleaned_line and
                                    'tokens' not in cleaned_line.lower() and
                                    'auto-accept' not in cleaned_line.lower() and
                                    'shift+tab' not in cleaned_line.lower() and
                                    'esc to interrupt' not in cleaned_line.lower() and
                                    'Deciphering' not in cleaned_line and
                                    'Simmering' not in cleaned_line and
                                    'Shimmying' not in cleaned_line and
                                    # Skip permission-related messages
                                    'permission' not in cleaned_line.lower() and
                                    'approve' not in cleaned_line.lower() and
                                    'y/n' not in cleaned_line.lower() and
                                    'yes/no' not in cleaned_line.lower() and
                                    'continue?' not in cleaned_line.lower()):
                                    
                                    # Remove any timestamp prefixes
                                    cleaned_line = re.sub(r'^\[\d+:\d+:\d+ [AP]M\]:\s*', '', cleaned_line)
                                    # Remove bullet points but keep the content
                                    cleaned_line = re.sub(r'^[•●]\s*', '', cleaned_line)
                                    
                                    if cleaned_line:
                                        response_lines.append(cleaned_line)
                                        if not capture_started:
                                            capture_started = True
                    
                    if response_lines:
                        response = ' '.join(response_lines).strip()
                        response_hash = hash(response)
                        
                        if response_hash not in processed_responses and len(response) > 10:
                            processed_responses.add(response_hash)
                            response_queue.put(response)
                            print(f"[CAPTURED] Full response ({len(response)} chars): {response[:150]}...")
                            # Clear command after processing
                            globals()['last_command'] = ""
                            # Reset permission flags for next command
                            permission_detected = False
                            permission_responded = False
                    else:
                        # Log if we found the command but no response
                        if cmd_line_idx >= 0:
                            print(f"[DEBUG] Found command at line {cmd_line_idx} but no response captured")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error capturing output: {e}")
            time.sleep(2)

# Start the output capture thread
capture_thread = threading.Thread(target=capture_tmux_output, daemon=True)
capture_thread.start()

# HTML template with Edge TTS voices
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant - Edge TTS</title>
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
            transition: all 0.3s;
        }
        .mic-button.listening {
            background: #ff0000;
            border-color: #ff0000;
            animation: pulse-listening 2s infinite;
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
        @keyframes pulse-listening {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
            50% { transform: scale(1.05); box-shadow: 0 0 0 20px rgba(255, 0, 0, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
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
        .voice-controls {
            margin: 20px 0;
            padding: 15px;
            background: #0f2027;
            border-radius: 10px;
        }
        .voice-option {
            margin: 10px 0;
        }
        select, input[type="range"] {
            margin: 0 10px;
            padding: 5px;
            background: #16213e;
            color: white;
            border: 1px solid #00ff00;
            border-radius: 5px;
            width: 300px;
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
        .listening-mode {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid #ff0000;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            display: none;
        }
        .stop-button {
            background: #e74c3c;
        }
        .stop-button:hover {
            background: #c0392b;
        }
        .voice-preview {
            color: #888;
            font-size: 14px;
            margin-top: 5px;
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
                <button class="stop-button" onclick="stopSpeaking()">🛑 STOP Speaking</button>
            </div>
            
            <div class="voice-controls">
                <div class="voice-option">
                    <label>Voice:</label>
                    <select id="voiceSelect" onchange="updateVoice()"></select>
                    <div class="voice-preview" id="voicePreview"></div>
                </div>
                <div class="voice-option">
                    <label>Speed: <span id="speedValue">1.0</span></label>
                    <input type="range" id="speedSlider" min="0.5" max="2" step="0.1" value="1" onchange="updateSpeed()">
                </div>
                <div class="voice-option">
                    <label>Pitch: <span id="pitchValue">0</span></label>
                    <input type="range" id="pitchSlider" min="-20" max="20" step="1" value="0" onchange="updatePitch()">
                </div>
            </div>
            
            <button id="micButton" class="mic-button">🎤</button>
            
            <div class="listening-mode" id="listeningMode">
                🔴 CONTINUOUS LISTENING MODE - Click mic to stop
            </div>
            
            <div id="status">Click mic to start continuous listening</div>
            <div class="speaking-indicator" id="speakingIndicator">🔊 Speaking...</div>
            
            <div class="conversation" id="conversation"></div>
        </div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        let autoSpeak = true;
        let speechRate = 1.0;
        let speechPitch = 0;
        let isSpeaking = false;
        let lastSpokenText = "";
        let selectedVoice = 'en-US-JasonNeural'; // Default to US Male
        let continuousMode = true;
        let wasListeningBeforeSpeech = false;
        let currentAudio = null;
        
        // Available voices from server
        const edgeVoices = {{ edge_voices | tojson }};
        
        // Load voices into select
        function loadVoices() {
            const voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '';
            
            // Group by locale
            const locales = {
                'en-US': 'US English',
                'en-GB': 'UK English', 
                'en-AU': 'Australian English'
            };
            
            Object.entries(locales).forEach(([locale, label]) => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = label;
                
                Object.entries(edgeVoices).forEach(([id, info]) => {
                    if (info.locale === locale) {
                        const option = document.createElement('option');
                        option.value = id;
                        option.textContent = info.name;
                        optgroup.appendChild(option);
                    }
                });
                
                if (optgroup.children.length > 0) {
                    voiceSelect.appendChild(optgroup);
                }
            });
            
            // Set default
            voiceSelect.value = selectedVoice;
            updateVoicePreview();
        }
        
        function updateVoicePreview() {
            const preview = document.getElementById('voicePreview');
            const voice = edgeVoices[selectedVoice];
            if (voice) {
                preview.textContent = `${voice.gender} voice, ${voice.locale}`;
            }
        }
        
        // Update clock
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        updateClock();
        
        function updateVoice() {
            selectedVoice = document.getElementById('voiceSelect').value;
            updateVoicePreview();
            // Test the voice by saying its name
            const voiceInfo = edgeVoices[selectedVoice];
            if (voiceInfo) {
                const testMessage = `Hello, this is ${voiceInfo.name.split(' ')[0]}. I'm a ${voiceInfo.gender.toLowerCase()} voice from ${voiceInfo.locale}.`;
                speak(testMessage, true);
            }
        }
        
        function updateSpeed() {
            speechRate = parseFloat(document.getElementById('speedSlider').value);
            document.getElementById('speedValue').textContent = speechRate;
        }
        
        function updatePitch() {
            speechPitch = parseInt(document.getElementById('pitchSlider').value);
            document.getElementById('pitchValue').textContent = speechPitch + 'Hz';
        }
        
        function toggleAutoSpeak() {
            autoSpeak = !autoSpeak;
            document.getElementById('autoSpeakStatus').textContent = autoSpeak ? 'ON' : 'OFF';
        }
        
        function stopSpeaking() {
            // Stop any playing audio
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                currentAudio = null;
            }
            
            // Reset states
            isSpeaking = false;
            document.getElementById('speakingIndicator').style.display = 'none';
            document.getElementById('micButton').classList.remove('speaking');
            updateStatus('Speech stopped - ready to chat!');
            
            // Resume listening if needed
            if (wasListeningBeforeSpeech && continuousMode && recognition) {
                wasListeningBeforeSpeech = false;
                setTimeout(() => {
                    recognition.start();
                    updateStatus('🔴 Listening - speak when ready');
                }, 300);
            }
        }
        
        async function speak(text, isTest = false) {
            if (!text || (isSpeaking && !isTest) || (!isTest && text === lastSpokenText)) return;
            
            // Stop current audio
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            // Stop recognition while speaking (but not for tests)
            if (!isTest && recognition && isListening) {
                recognition.stop();
                wasListeningBeforeSpeech = true;
            }
            
            if (!isTest) {
                lastSpokenText = text;
            }
            isSpeaking = true;
            document.getElementById('speakingIndicator').style.display = 'block';
            document.getElementById('micButton').classList.add('speaking');
            if (!isTest) {
                updateStatus('🔊 Claude is speaking...');
            }
            
            try {
                // Use Edge TTS
                const response = await fetch('/get-tts-audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: text,
                        voice: selectedVoice,
                        rate: speechRate,
                        pitch: speechPitch
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const audio = new Audio('data:audio/mp3;base64,' + data.audio);
                    currentAudio = audio;
                    
                    audio.onended = () => {
                        currentAudio = null;
                        onSpeechEnd(isTest);
                    };
                    
                    audio.onerror = () => {
                        currentAudio = null;
                        onSpeechEnd(isTest);
                    };
                    
                    audio.play();
                } else {
                    console.error('TTS failed:', data.error);
                    onSpeechEnd(isTest);
                }
            } catch (err) {
                console.error('TTS error:', err);
                onSpeechEnd(isTest);
            }
        }
        
        function onSpeechEnd(isTest = false) {
            isSpeaking = false;
            document.getElementById('speakingIndicator').style.display = 'none';
            document.getElementById('micButton').classList.remove('speaking');
            
            // Resume listening if it was active before (but not for tests)
            if (!isTest && wasListeningBeforeSpeech && continuousMode) {
                setTimeout(() => {
                    recognition.start();
                    updateStatus('🔴 Listening - speak when ready');
                }, 500);
            }
            if (!isTest) {
                wasListeningBeforeSpeech = false;
            }
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
                    window.claudeThinking = false;
                    
                    if (isListening) {
                        updateStatus('🔴 Listening - speak when ready');
                    } else {
                        updateStatus('Claude responded - click mic to resume');
                    }
                    
                    if (autoSpeak && !isSpeaking) {
                        speak(data.response);
                    }
                }
            } catch (err) {
                console.error('Error checking response:', err);
            }
        }
        
        // Initialize speech recognition with continuous mode
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
                updateStatus('❌ Speech recognition not supported!');
                document.getElementById('micButton').disabled = true;
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            
            recognition.continuous = true;  // Keep listening
            recognition.interimResults = true;  // Show interim results
            recognition.lang = 'en-US';
            
            let finalTranscript = '';
            let silenceTimer = null;
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                document.getElementById('listeningMode').style.display = 'block';
                updateStatus('🔴 Listening continuously - speak anytime');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('listeningMode').style.display = 'none';
                updateStatus('Click mic to start continuous listening');
                
                // Auto-restart if it ended unexpectedly
                if (continuousMode && isListening) {
                    setTimeout(() => {
                        if (!isListening) recognition.start();
                    }, 500);
                }
            };
            
            recognition.onresult = (event) => {
                // Don't process if Claude is thinking or speaking
                if (window.claudeThinking || isSpeaking) return;
                
                let interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript = transcript;
                        
                        // Clear any existing silence timer
                        if (silenceTimer) clearTimeout(silenceTimer);
                        
                        // Set a timer to send after 1.5 seconds of silence
                        silenceTimer = setTimeout(() => {
                            if (finalTranscript.trim() && !window.claudeThinking && !isSpeaking) {
                                sendCommand(finalTranscript);
                                finalTranscript = '';
                            }
                        }, 1500);
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                // Show what's being heard (only if not speaking)
                if (interimTranscript && !window.claudeThinking && !isSpeaking) {
                    updateStatus('💬 ' + interimTranscript);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                
                if (event.error === 'not-allowed') {
                    isListening = false;
                    document.getElementById('micButton').classList.remove('listening');
                    document.getElementById('listeningMode').style.display = 'none';
                    updateStatus('❌ Microphone permission denied!');
                    alert('Please allow microphone access and refresh.');
                } else if (event.error === 'no-speech') {
                    // Ignore no-speech errors in continuous mode
                    updateStatus('🔴 Listening - speak when ready');
                }
            };
        }
        
        // Send command
        async function sendCommand(text) {
            window.claudeThinking = true;
            addMessage(text, 'user');
            updateStatus('Claude is thinking... (listening paused)');
            
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
                    updateStatus('⏳ Claude is thinking... (listening paused)');
                    // Resume listening after Claude responds
                    setTimeout(() => {
                        window.claudeThinking = false;
                        if (isListening) {
                            updateStatus('🔴 Listening - speak when ready');
                        }
                    }, 5000); // Resume after 5 seconds max
                } else {
                    window.claudeThinking = false;
                    updateStatus('❌ Failed to send - listening resumed');
                }
            } catch (err) {
                window.claudeThinking = false;
                updateStatus('❌ Error: ' + err.message);
            }
        }
        
        // Mic button - toggle continuous listening
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition) return;
            
            // Stop any ongoing speech
            if (isSpeaking) {
                stopSpeaking();
            }
            
            if (isListening) {
                continuousMode = false;
                recognition.stop();
            } else {
                continuousMode = true;
                recognition.start();
            }
        });
        
        // Initialize
        window.onload = () => {
            loadVoices();
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
    return render_template_string(HTML_TEMPLATE, edge_voices=EDGE_VOICES)

@app.route('/send', methods=['POST'])
def send_to_tmux():
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

@app.route('/get-tts-audio', methods=['POST'])
def get_tts_audio():
    """Generate high-quality TTS audio using Edge TTS"""
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'en-US-JasonNeural')
        rate = data.get('rate', 1.0)
        pitch = data.get('pitch', 0)
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        # Create temp file for audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Generate audio with Edge TTS
        async def generate():
            # Format rate and pitch
            rate_str = f"+{int((rate-1)*100)}%" if rate > 1 else f"{int((rate-1)*100)}%"
            pitch_str = f"+{pitch}Hz" if pitch > 0 else f"{pitch}Hz"
            
            communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)
            await communicate.save(tmp_path)
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate())
        
        # Read and encode audio
        with open(tmp_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'audio': audio_base64,
            'format': 'mp3'
        })
        
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  CLAUDE VOICE - EDGE TTS")
    print("="*50)
    print("✨ Features:")
    print("  - Microsoft Edge neural voices")
    print("  - Real male and female voices")
    print("  - US, UK, and Australian accents")
    print("  - Auto-approval of permissions")
    print("  - Immediate stop functionality")
    print("")
    print("📱 Access at: https://192.168.40.232:8106")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8106, debug=False, ssl_context=context)