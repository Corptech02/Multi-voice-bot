#!/usr/bin/env python3
"""
Claude Voice Bot with Premium TTS Options
- Uses pyttsx3 for offline high-quality voices
- Better male/female voice selection
- Immediate stop functionality
"""
from flask import Flask, render_template_string, request, jsonify
import subprocess
import ssl
import time
from datetime import datetime
import threading
import queue
import re
import os
import tempfile
from gtts import gTTS
import base64
import io
import pyttsx3
import pygame

app = Flask(__name__)

# Initialize pygame for audio playback
pygame.mixer.init()

# Queue to store Claude's responses
response_queue = queue.Queue()

# Track conversation state
last_command = ""
last_command_time = 0
processed_responses = set()
current_stats = {"time": "", "tokens": ""}
is_claude_thinking = False

# Initialize pyttsx3 for better TTS
tts_engine = pyttsx3.init()
available_voices = tts_engine.getProperty('voices')

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
    
    while True:
        try:
            if not last_command:
                time.sleep(1)
                continue
                
            # Wait for response to fully render
            if time.time() - last_command_time < 3:
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
                                    'Shimmying' not in cleaned_line):
                                    
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

# HTML template with improved voice options
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant - Premium</title>
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
        .mic-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
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
                    <label>Voice Engine:</label>
                    <select id="voiceEngine" onchange="updateVoiceEngine()">
                        <option value="google">Google TTS (Female only)</option>
                        <option value="system">System Voices (Male/Female)</option>
                    </select>
                </div>
                <div class="voice-option">
                    <label>Voice:</label>
                    <select id="voiceSelect" onchange="updateVoice()"></select>
                </div>
                <div class="voice-option">
                    <label>Speed: <span id="speedValue">1.0</span></label>
                    <input type="range" id="speedSlider" min="0.5" max="2" step="0.1" value="1" onchange="updateSpeed()">
                </div>
                <div class="voice-option">
                    <label>Pitch: <span id="pitchValue">1.0</span></label>
                    <input type="range" id="pitchSlider" min="0.5" max="2" step="0.1" value="1" onchange="updatePitch()">
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
        let speechPitch = 1.0;
        let isSpeaking = false;
        let lastSpokenText = "";
        let selectedVoice = null;
        let continuousMode = true;
        let wasListeningBeforeSpeech = false;
        let voiceEngine = 'google';
        let currentAudio = null;
        let audioQueue = [];
        
        // Initialize speech synthesis
        const synth = window.speechSynthesis;
        let voices = [];
        
        // Load voices
        function loadVoices() {
            voices = synth.getVoices();
            updateVoiceList();
        }
        
        function updateVoiceList() {
            const voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '';
            
            if (voiceEngine === 'google') {
                // Google TTS options
                const googleVoices = [
                    { name: 'US English Female', value: 'com' },
                    { name: 'UK English Female', value: 'co.uk' },
                    { name: 'Australian Female', value: 'com.au' },
                    { name: 'Indian Female', value: 'co.in' }
                ];
                
                googleVoices.forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voice.value;
                    option.textContent = voice.name + ' (High Quality)';
                    voiceSelect.appendChild(option);
                });
                
                selectedVoice = 'com';
            } else {
                // System voices
                let englishVoices = voices.filter(v => v.lang.startsWith('en'));
                
                // Separate male and female voices
                const maleVoices = [];
                const femaleVoices = [];
                
                englishVoices.forEach(voice => {
                    const name = voice.name.toLowerCase();
                    if (name.includes('male') && !name.includes('female')) {
                        maleVoices.push(voice);
                    } else if (name.includes('female') || ['samantha', 'karen', 'moira', 'tessa', 'fiona', 'victoria', 'susan'].some(n => name.includes(n))) {
                        femaleVoices.push(voice);
                    } else if (['alex', 'daniel', 'oliver', 'thomas', 'fred', 'ralph'].some(n => name.includes(n))) {
                        maleVoices.push(voice);
                    } else {
                        femaleVoices.push(voice);
                    }
                });
                
                // Add male voices
                if (maleVoices.length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = 'Male Voices';
                    maleVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voices.indexOf(voice);
                        option.textContent = voice.name.replace(/^(Microsoft|Google|com\.apple\.)/, '');
                        optgroup.appendChild(option);
                    });
                    voiceSelect.appendChild(optgroup);
                }
                
                // Add female voices
                if (femaleVoices.length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = 'Female Voices';
                    femaleVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voices.indexOf(voice);
                        option.textContent = voice.name.replace(/^(Microsoft|Google|com\.apple\.)/, '');
                        optgroup.appendChild(option);
                    });
                    voiceSelect.appendChild(optgroup);
                }
                
                // Select first available voice
                if (maleVoices.length > 0) {
                    selectedVoice = maleVoices[0];
                    voiceSelect.value = voices.indexOf(maleVoices[0]);
                } else if (englishVoices.length > 0) {
                    selectedVoice = englishVoices[0];
                    voiceSelect.value = voices.indexOf(englishVoices[0]);
                }
            }
        }
        
        // Load voices when available
        synth.onvoiceschanged = loadVoices;
        loadVoices();
        
        // Update clock
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        updateClock();
        
        function updateVoiceEngine() {
            voiceEngine = document.getElementById('voiceEngine').value;
            updateVoiceList();
            // Test the new voice
            speak('Voice engine changed', true);
        }
        
        function updateVoice() {
            const voiceSelect = document.getElementById('voiceSelect');
            if (voiceEngine === 'system') {
                selectedVoice = voices[voiceSelect.value];
            } else {
                selectedVoice = voiceSelect.value;
            }
            // Test the voice
            speak('Testing voice selection', true);
        }
        
        function updateSpeed() {
            speechRate = parseFloat(document.getElementById('speedSlider').value);
            document.getElementById('speedValue').textContent = speechRate;
        }
        
        function updatePitch() {
            speechPitch = parseFloat(document.getElementById('pitchSlider').value);
            document.getElementById('pitchValue').textContent = speechPitch;
        }
        
        function toggleAutoSpeak() {
            autoSpeak = !autoSpeak;
            document.getElementById('autoSpeakStatus').textContent = autoSpeak ? 'ON' : 'OFF';
        }
        
        function stopSpeaking() {
            // Stop all speech immediately
            synth.cancel();
            
            // Stop any audio elements
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                currentAudio.src = '';
                currentAudio = null;
            }
            
            // Clear audio queue
            audioQueue = [];
            
            // Reset states
            isSpeaking = false;
            document.getElementById('speakingIndicator').style.display = 'none';
            document.getElementById('micButton').classList.remove('speaking');
            document.getElementById('micButton').disabled = false;
            updateStatus('Speech stopped - ready to listen!');
            
            // Resume listening if needed
            if (wasListeningBeforeSpeech && continuousMode && recognition && !isListening) {
                wasListeningBeforeSpeech = false;
                setTimeout(() => {
                    recognition.start();
                    isListening = true;
                    document.getElementById('micButton').classList.add('listening');
                    document.getElementById('listeningMode').style.display = 'block';
                    updateStatus('🔴 Listening - speak when ready');
                }, 500);
            }
        }
        
        async function speak(text, isTest = false) {
            if (!text || (isSpeaking && !isTest)) return;
            
            // For tests, don't interfere with listening
            if (!isTest && text === lastSpokenText) return;
            
            // Stop current speech first
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            synth.cancel();
            
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
            document.getElementById('micButton').disabled = true;
            
            if (!isTest) {
                updateStatus('🔊 Claude is speaking...');
            }
            
            try {
                if (voiceEngine === 'google') {
                    // Use Google TTS
                    const response = await fetch('/get-tts-audio', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            text: text,
                            lang: 'en',
                            accent: selectedVoice || 'com'
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        const audio = new Audio('data:audio/mp3;base64,' + data.audio);
                        currentAudio = audio;
                        audio.playbackRate = speechRate;
                        
                        audio.onended = () => {
                            currentAudio = null;
                            onSpeechEnd(isTest);
                        };
                        
                        audio.onerror = () => {
                            currentAudio = null;
                            useBrowserTTS(text, isTest);
                        };
                        
                        await audio.play();
                    } else {
                        useBrowserTTS(text, isTest);
                    }
                } else {
                    // Use system TTS
                    useBrowserTTS(text, isTest);
                }
            } catch (err) {
                console.error('TTS error:', err);
                useBrowserTTS(text, isTest);
            }
        }
        
        function useBrowserTTS(text, isTest = false) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = speechRate;
            utterance.pitch = speechPitch;
            utterance.volume = isTest ? 0.5 : 1;
            
            if (selectedVoice && typeof selectedVoice === 'object') {
                utterance.voice = selectedVoice;
            }
            
            utterance.onend = () => {
                onSpeechEnd(isTest);
            };
            
            utterance.onerror = (event) => {
                console.error('Speech error:', event);
                onSpeechEnd(isTest);
            };
            
            synth.speak(utterance);
        }
        
        function onSpeechEnd(isTest = false) {
            isSpeaking = false;
            document.getElementById('speakingIndicator').style.display = 'none';
            document.getElementById('micButton').classList.remove('speaking');
            document.getElementById('micButton').disabled = false;
            
            // Resume listening if it was active before (but not for tests)
            if (!isTest && wasListeningBeforeSpeech && continuousMode && !isListening) {
                setTimeout(() => {
                    if (recognition && !isListening) {
                        recognition.start();
                        updateStatus('🔴 Listening - speak when ready');
                    }
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
                if (continuousMode && !isSpeaking) {
                    setTimeout(() => {
                        if (!isListening && continuousMode) {
                            try {
                                recognition.start();
                            } catch (e) {
                                console.log('Could not restart recognition:', e);
                            }
                        }
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
                const response = await fetch('/send-to-tmux', {
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
            
            // Always stop any speech when clicking mic
            stopSpeaking();
            
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

@app.route('/send-to-tmux', methods=['POST'])
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
    """Generate high-quality TTS audio using gTTS"""
    try:
        data = request.json
        text = data.get('text', '')
        lang = data.get('lang', 'en')
        accent = data.get('accent', 'com')  # com=US, co.uk=UK, com.au=AU
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        # Create gTTS instance with specific accent
        tts = gTTS(text=text, lang=lang, tld=accent, slow=False)
        
        # Save to bytes buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Convert to base64 for sending
        audio_base64 = base64.b64encode(audio_buffer.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'audio': audio_base64,
            'format': 'mp3'
        })
        
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-system-voices')
def get_system_voices():
    """Get available system voices"""
    try:
        # Get pyttsx3 voices
        voices_list = []
        for voice in available_voices:
            voices_list.append({
                'id': voice.id,
                'name': voice.name,
                'gender': getattr(voice, 'gender', 'unknown'),
                'languages': getattr(voice, 'languages', [])
            })
        
        return jsonify({'success': True, 'voices': voices_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  CLAUDE VOICE - PREMIUM TTS")
    print("="*50)
    print("✨ Features:")
    print("  - Google TTS for female voices")
    print("  - System voices for male options")
    print("  - Immediate stop functionality")
    print("  - Better voice selection")
    print("")
    print("📱 Access at: https://192.168.40.232:8105")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8105, debug=False, ssl_context=context)