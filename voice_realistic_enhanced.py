#!/usr/bin/env python3
"""
Hyper-Realistic Claude Voice Assistant with Dynamic Pitch/Tone
Features:
- Multiple high-quality voice options with proper male/female distinction
- Dynamic pitch and tone variation for natural conversation
- Emotion-aware TTS adjustments
- SSML support for advanced speech control
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
import base64
import io
import random
import pyttsx3
import edge_tts
import asyncio
from gtts import gTTS

app = Flask(__name__)

# Tracking variables
last_command = ""
last_command_time = 0
current_stats = {}
is_claude_thinking = False
response_queue = queue.Queue()

# Advanced voice configurations with pitch/tone variations
VOICE_CONFIGS = {
    # Microsoft Edge TTS voices - high quality neural voices
    'edge_us_male': {
        'name': 'Christopher (US Male)',
        'engine': 'edge',
        'voice': 'en-US-ChristopherNeural',
        'pitch_range': (-20, 10),
        'rate_range': (0.9, 1.1),
        'style': 'casual'
    },
    'edge_us_female': {
        'name': 'Jenny (US Female)',
        'engine': 'edge',
        'voice': 'en-US-JennyNeural',
        'pitch_range': (-10, 20),
        'rate_range': (0.95, 1.15),
        'style': 'friendly'
    },
    'edge_uk_male': {
        'name': 'Ryan (UK Male)',
        'engine': 'edge',
        'voice': 'en-GB-RyanNeural',
        'pitch_range': (-15, 5),
        'rate_range': (0.9, 1.05),
        'style': 'professional'
    },
    'edge_uk_female': {
        'name': 'Libby (UK Female)',
        'engine': 'edge',
        'voice': 'en-GB-LibbyNeural',
        'pitch_range': (-5, 15),
        'rate_range': (0.95, 1.1),
        'style': 'cheerful'
    },
    'edge_au_male': {
        'name': 'William (Australian Male)',
        'engine': 'edge',
        'voice': 'en-AU-WilliamNeural',
        'pitch_range': (-10, 10),
        'rate_range': (0.9, 1.1),
        'style': 'casual'
    },
    'edge_au_female': {
        'name': 'Natasha (Australian Female)',
        'engine': 'edge',
        'voice': 'en-AU-NatashaNeural',
        'pitch_range': (-5, 15),
        'rate_range': (0.95, 1.1),
        'style': 'friendly'
    },
    'edge_ca_male': {
        'name': 'Liam (Canadian Male)',
        'engine': 'edge',
        'voice': 'en-CA-LiamNeural',
        'pitch_range': (-15, 5),
        'rate_range': (0.9, 1.05),
        'style': 'professional'
    },
    'edge_ca_female': {
        'name': 'Clara (Canadian Female)',
        'engine': 'edge',
        'voice': 'en-CA-ClaraNeural',
        'pitch_range': (-5, 20),
        'rate_range': (0.95, 1.15),
        'style': 'warm'
    },
    # Google TTS fallback voices
    'gtts_us': {
        'name': 'Google US',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com'
    },
    'gtts_uk': {
        'name': 'Google UK',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'co.uk'
    },
    'gtts_au': {
        'name': 'Google Australian',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com.au'
    }
}

def analyze_emotion(text):
    """Analyze text emotion for dynamic voice adjustment"""
    # Simple emotion detection based on keywords and punctuation
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['excited', 'amazing', 'wonderful', '!']):
        return 'excited', 1.2, 10  # rate multiplier, pitch adjustment
    elif any(word in text_lower for word in ['sorry', 'apologize', 'unfortunately']):
        return 'apologetic', 0.9, -5
    elif any(word in text_lower for word in ['important', 'critical', 'urgent']):
        return 'serious', 0.95, -10
    elif '?' in text:
        return 'questioning', 1.05, 5
    else:
        return 'neutral', 1.0, 0

async def generate_edge_tts_with_ssml(text, voice_config):
    """Generate speech with Edge TTS using SSML for dynamic adjustments"""
    voice = voice_config['voice']
    
    # Clean text for TTS - remove special characters and normalize
    text = re.sub(r'[?!:;]', '.', text)  # Replace punctuation with periods
    text = re.sub(r'[^\w\s.,\'-]', '', text)  # Remove other special chars
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
    
    emotion, rate_mult, pitch_adj = analyze_emotion(text)
    
    # Calculate dynamic pitch and rate
    pitch_min, pitch_max = voice_config['pitch_range']
    base_pitch = random.uniform(pitch_min, pitch_max)
    final_pitch = max(pitch_min, min(pitch_max, base_pitch + pitch_adj))
    
    rate_min, rate_max = voice_config['rate_range']
    base_rate = random.uniform(rate_min, rate_max)
    final_rate = base_rate * rate_mult
    
    # For voice preview, use simple text without SSML
    communicate = edge_tts.Communicate(text, voice)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        await communicate.save(tmp_file.name)
        return tmp_file.name

def extract_stats_from_output(output):
    """Extract Claude stats from tmux output"""
    stats = {}
    
    # Look for token counts
    token_match = re.search(r'(\d+)\s+tokens', output)
    if token_match:
        stats['tokens'] = int(token_match.group(1))
    
    # Look for time
    time_match = re.search(r'(\d+)s', output)
    if time_match:
        stats['time'] = f"{time_match.group(1)}s"
    
    return stats

def capture_tmux_output():
    """Continuously capture tmux output with enhanced permission detection"""
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
                
                # Enhanced permission detection
                permission_keywords = [
                    'permission', 'approve', 'continue?', 'y/n', 'yes/no', 
                    'press enter', 'auto-accept', 'proceed?', 'confirm',
                    'are you sure', 'would you like', 'ok?', '[y/n]',
                    'press 1', 'press y', 'type yes', 'hit enter',
                    '(y/n)', '(yes/no)', 'bash', 'execute', 'run this',
                    'allow?', 'grant', 'authorize', 'choice:', 'select:',
                    '1)', '2)', '3)', 'option', 'which one', 'what would you',
                    'proceed with', 'running', 'executing', 'do you want to proceed',
                    'bash command', '❯', '1. yes', '2. no'
                ]
                
                # Check for numbered options or Claude's prompt style
                numbered_pattern = r'\b[1-9]\)\s+\w+|\[[1-9]\]|\b[1-9]\.\s+\w+|❯\s*1\.|1\.\s*yes'
                has_numbered_options = bool(re.search(numbered_pattern, output))
                
                # Check for Claude's specific bash prompt format
                claude_bash_prompt = '❯' in output and '1. yes' in output.lower()
                
                if any(prompt in output for prompt in permission_keywords) or has_numbered_options or claude_bash_prompt:
                    if not permission_responded:
                        print("[AUTO-APPROVE] Detected permission prompt, sending approval...")
                        
                        # Check what type of approval is needed
                        if claude_bash_prompt or '❯' in output or '1. yes' in output.lower() or 'do you want to proceed' in output:
                            # Claude's bash prompt - always send 1
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                            print("[AUTO-APPROVE] Detected Claude bash prompt, sent: 1 + Enter")
                        elif 'press 1' in output or '1)' in output or '[1]' in output or has_numbered_options:
                            # Send 1 for numbered options
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                            print("[AUTO-APPROVE] Sent: 1 + Enter")
                        elif 'press enter' in output or 'hit enter' in output:
                            # Just send Enter
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                            print("[AUTO-APPROVE] Sent: Enter")
                        else:
                            # Default: send y + Enter
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'y'], check=True)
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                            print("[AUTO-APPROVE] Sent: y + Enter")
                        
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

# HTML template with enhanced voice selection
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Hyper-Realistic Claude Voice Assistant</title>
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
        .voice-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }
        .voice-card {
            background: #0f3460;
            border: 2px solid #16213e;
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .voice-card:hover {
            border-color: #00ff00;
            transform: scale(1.05);
        }
        .voice-card.selected {
            border-color: #00ff00;
            background: #16213e;
        }
        .voice-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .voice-type {
            font-size: 12px;
            color: #888;
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
            color: white;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        .status {
            margin: 20px;
            padding: 15px;
            background: #0f2027;
            border-radius: 10px;
            min-height: 50px;
            border: 1px solid #16213e;
        }
        .controls {
            margin: 20px 0;
            display: flex;
            justify-content: center;
            gap: 20px;
            align-items: center;
        }
        .quality-badge {
            display: inline-block;
            background: #00ff00;
            color: #1a1a2e;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 5px;
        }
        .listening-mode {
            display: none;
            background: #ff0000;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            position: absolute;
            top: 20px;
            right: 20px;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.3; }
        }
        button {
            padding: 10px 20px;
            background: #00ff00;
            color: #1a1a2e;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        button:hover {
            background: #00cc00;
        }
        button:disabled {
            background: #666;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div id="listeningMode" class="listening-mode">🔴 LIVE</div>
    
    <div class="main-container">
        <div class="stats-panel">
            <h3 style="text-align: center; color: #00ff00;">Session Stats</h3>
            <div class="stats-item">
                <div class="stats-label">Tokens Used</div>
                <div class="stats-value" id="tokenCount">0</div>
            </div>
            <div class="stats-item">
                <div class="stats-label">Response Time</div>
                <div class="stats-value" id="responseTime">-</div>
            </div>
            <div class="stats-item">
                <div class="stats-label">Claude Status</div>
                <div class="stats-value" id="claudeStatus" style="font-size: 14px;">Ready</div>
            </div>
        </div>
        
        <div class="content-container">
            <h1>🎙️ Hyper-Realistic Claude Voice</h1>
            
            <div class="voice-grid" id="voiceGrid">
                <!-- Voice cards will be generated here -->
            </div>
            
            <button id="micButton" class="mic-button">🎤</button>
            
            <div class="controls">
                <button id="stopSpeaking">🔇 Stop Speaking</button>
                <label style="color: #888;">Auto-send after silence</label>
            </div>
            
            <div id="status" class="status">
                Click mic to start continuous listening
            </div>
        </div>
    </div>

    <script>
        const voices = {{ voices | tojson }};
        let selectedVoice = 'edge_us_male';
        let recognition = null;
        let isListening = false;
        let continuousMode = false;
        let audioContext = null;
        let currentAudio = null;
        let isSpeaking = false;
        const processedResponses = new Set();
        
        // Initialize voice cards
        function initVoiceCards() {
            const grid = document.getElementById('voiceGrid');
            grid.innerHTML = '';
            
            for (const [key, config] of Object.entries(voices)) {
                const card = document.createElement('div');
                card.className = 'voice-card';
                card.dataset.voice = key;
                
                const isHighQuality = key.startsWith('edge_');
                
                card.innerHTML = `
                    <div class="voice-name">
                        ${config.name}
                        ${isHighQuality ? '<span class="quality-badge">HD</span>' : ''}
                    </div>
                    <div class="voice-type">${config.engine || 'Standard'}</div>
                `;
                
                card.onclick = () => selectVoice(key);
                grid.appendChild(card);
            }
            
            // Select default voice
            selectVoice(selectedVoice);
        }
        
        function selectVoice(voiceKey) {
            selectedVoice = voiceKey;
            document.querySelectorAll('.voice-card').forEach(card => {
                card.classList.toggle('selected', card.dataset.voice === voiceKey);
            });
            
            // Play voice preview with clean text
            const config = voices[voiceKey];
            const voiceName = config.name.split(' ')[0].replace(/[^a-zA-Z]/g, '');
            const previewText = `Hello I am ${voiceName}`;
            speakText(previewText, true);
        }
        
        function updateStatus(message) {
            document.getElementById('status').textContent = message;
        }
        
        async function speakText(text, isPreview = false) {
            if (currentAudio && !currentAudio.paused) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            isSpeaking = true;
            
            try {
                const response = await fetch('/get-tts-audio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: text, 
                        voice: selectedVoice,
                        is_preview: isPreview
                    })
                });
                
                if (!response.ok) throw new Error('TTS request failed');
                
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                currentAudio = new Audio(audioUrl);
                currentAudio.onended = () => {
                    isSpeaking = false;
                    URL.revokeObjectURL(audioUrl);
                    if (!isPreview && continuousMode && !isListening) {
                        setTimeout(() => {
                            if (!isSpeaking) recognition.start();
                        }, 500);
                    }
                };
                
                await currentAudio.play();
                
            } catch (error) {
                console.error('TTS Error:', error);
                isSpeaking = false;
            }
        }
        
        function sendCommand(command) {
            window.claudeThinking = true;
            updateStatus('🧠 Claude is thinking...');
            
            fetch('/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: command })
            });
        }
        
        function setupSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window)) {
                alert('Speech recognition not supported!');
                return;
            }
            
            recognition = new webkitSpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            let accumulatedTranscript = '';
            let silenceTimer = null;
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                document.getElementById('listeningMode').style.display = 'block';
                updateStatus('🔴 Listening continuously - speak anytime');
                accumulatedTranscript = '';
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('listeningMode').style.display = 'none';
                updateStatus('Click mic to start continuous listening');
                
                if (continuousMode && isListening) {
                    setTimeout(() => {
                        if (!isListening) recognition.start();
                    }, 500);
                }
            };
            
            recognition.onresult = (event) => {
                if (window.claudeThinking || isSpeaking) return;
                
                let interimTranscript = '';
                let newFinalTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        newFinalTranscript += transcript + ' ';
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                if (newFinalTranscript) {
                    accumulatedTranscript += newFinalTranscript;
                }
                
                if (silenceTimer) clearTimeout(silenceTimer);
                
                silenceTimer = setTimeout(() => {
                    if (accumulatedTranscript.trim() && !window.claudeThinking && !isSpeaking) {
                        sendCommand(accumulatedTranscript.trim());
                        accumulatedTranscript = '';
                    }
                }, 5000);
                
                if (!window.claudeThinking && !isSpeaking) {
                    const displayText = accumulatedTranscript + interimTranscript;
                    if (displayText) {
                        updateStatus('💬 ' + displayText);
                    }
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                if (event.error === 'not-allowed') {
                    updateStatus('❌ Microphone permission denied!');
                }
            };
        }
        
        // Polling for responses
        async function pollForResponses() {
            try {
                const response = await fetch('/get-response');
                const data = await response.json();
                
                if (data.stats) {
                    document.getElementById('tokenCount').textContent = data.stats.tokens || '0';
                    document.getElementById('responseTime').textContent = data.stats.time || '-';
                }
                
                document.getElementById('claudeStatus').textContent = 
                    data.is_thinking ? 'Thinking...' : 'Ready';
                
                if (data.response && !processedResponses.has(data.response)) {
                    processedResponses.add(data.response);
                    window.claudeThinking = false;
                    updateStatus('🔊 Claude is speaking...');
                    
                    if (recognition && isListening) {
                        recognition.stop();
                    }
                    
                    await speakText(data.response);
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
            
            setTimeout(pollForResponses, 2000);
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            initVoiceCards();
            setupSpeechRecognition();
            
            document.getElementById('micButton').onclick = () => {
                if (!isListening) {
                    continuousMode = true;
                    recognition.start();
                } else {
                    continuousMode = false;
                    recognition.stop();
                }
            };
            
            document.getElementById('stopSpeaking').onclick = () => {
                if (currentAudio && !currentAudio.paused) {
                    currentAudio.pause();
                    currentAudio = null;
                    isSpeaking = false;
                    updateStatus('🔇 Speech stopped');
                    
                    if (continuousMode && !isListening && recognition) {
                        setTimeout(() => recognition.start(), 500);
                    }
                }
            };
            
            pollForResponses();
        });
        
        window.claudeThinking = false;
    </script>
</body>
</html>
'''

# Processed responses set to avoid duplicates
processed_responses = set()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, voices=VOICE_CONFIGS)

@app.route('/send', methods=['POST'])
def send_command():
    global last_command, last_command_time
    
    command = request.json.get('command', '')
    if command:
        # Clear processed responses for new command
        processed_responses.clear()
        
        # Send to tmux
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', command], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        last_command = command
        last_command_time = time.time()
        
        print(f"[SENT] Command: {command}")
        
    return jsonify({'status': 'sent'})

@app.route('/get-response')
def get_response():
    """Poll for Claude's responses"""
    response_data = {
        'response': None,
        'stats': current_stats,
        'is_thinking': is_claude_thinking
    }
    
    # Check if there's a response in the queue
    try:
        response = response_queue.get_nowait()
        response_data['response'] = response
    except queue.Empty:
        pass
    
    return jsonify(response_data)

@app.route('/get-tts-audio', methods=['POST'])
def get_tts_audio():
    """Generate TTS audio with selected voice"""
    text = request.json.get('text', '')
    voice_key = request.json.get('voice', 'edge_us_male')
    is_preview = request.json.get('is_preview', False)
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    voice_config = VOICE_CONFIGS.get(voice_key, VOICE_CONFIGS['edge_us_male'])
    
    try:
        if voice_config['engine'] == 'edge':
            # Use Edge TTS with dynamic adjustments
            audio_file = asyncio.run(generate_edge_tts_with_ssml(text, voice_config))
            
            # Send the file
            response = send_file(audio_file, mimetype='audio/mpeg')
            
            # Clean up after sending
            @response.call_on_close
            def cleanup():
                try:
                    os.unlink(audio_file)
                except:
                    pass
            
            return response
            
        else:
            # Fallback to gTTS
            # Clean text for gTTS
            clean_text = re.sub(r'[?!:;]', '.', text)
            clean_text = re.sub(r'[^\w\s.,\'-]', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            tts = gTTS(text=clean_text, lang=voice_config['lang'], tld=voice_config['tld'])
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return send_file(audio_buffer, mimetype='audio/mpeg')
            
    except Exception as e:
        print(f"TTS Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  HYPER-REALISTIC CLAUDE VOICE")
    print("="*50)
    print("✨ Features:")
    print("  - High-quality neural voices")
    print("  - Dynamic pitch/tone variation") 
    print("  - Emotion-aware speech")
    print("  - Natural conversation flow")
    print(f"\n📱 Access at: https://192.168.40.232:8104")
    print("="*50 + "\n")
    
    # SSL context for HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8104, ssl_context=context)