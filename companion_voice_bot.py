#!/usr/bin/env python3
"""
Companion Voice Bot - Natural Conversational AI Assistant
Features:
- Natural, friendly conversation flow
- Personality-driven responses
- Context awareness and memory
- Emotional intelligence
- High-quality neural voices
- Continuous listening with smart interruption handling
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
import random
import json
from collections import deque

app = Flask(__name__)

# Tracking variables
last_command = ""
last_command_time = 0
current_stats = {}
is_claude_thinking = False
response_queue = queue.Queue()
conversation_history = deque(maxlen=20)  # Keep last 20 exchanges
user_preferences = {}
emotional_state = "neutral"
interaction_count = 0

# Companion personality traits
COMPANION_TRAITS = {
    "name": "Alex",
    "personality": "warm, empathetic, curious, supportive",
    "interests": ["learning", "creativity", "helping others", "meaningful conversations"],
    "speech_patterns": {
        "greeting": ["Hey there!", "Hi! How's it going?", "Hello! Great to hear from you!", "Hey! What's on your mind?"],
        "acknowledgment": ["I hear you", "That makes sense", "I understand", "Got it", "I see what you mean"],
        "encouragement": ["That's wonderful!", "You're doing great!", "I'm proud of you!", "Keep it up!"],
        "empathy": ["I can imagine how that feels", "That must be challenging", "I'm here for you", "That sounds tough"],
        "curiosity": ["Tell me more about that", "What do you think about...", "I'm curious about...", "How did that make you feel?"],
        "thinking": ["Hmm, let me think about that", "That's an interesting question", "Good point, let me consider that"],
    }
}

# Enhanced voice configurations with personality-based settings
VOICE_CONFIGS = {
    'companion_male': {
        'name': 'Alex (Warm Male)',
        'engine': 'edge',
        'voice': 'en-US-GuyNeural',
        'pitch_range': (-5, 5),
        'rate_range': (0.95, 1.05),
        'style': 'friendly',
        'emotion_adjustments': {
            'happy': {'pitch': 5, 'rate': 1.1},
            'sad': {'pitch': -5, 'rate': 0.9},
            'excited': {'pitch': 10, 'rate': 1.2},
            'calm': {'pitch': 0, 'rate': 0.95},
            'empathetic': {'pitch': -2, 'rate': 0.98}
        }
    },
    'companion_female': {
        'name': 'Alex (Warm Female)',
        'engine': 'edge',
        'voice': 'en-US-AriaNeural',
        'pitch_range': (-5, 10),
        'rate_range': (0.95, 1.1),
        'style': 'friendly',
        'emotion_adjustments': {
            'happy': {'pitch': 8, 'rate': 1.1},
            'sad': {'pitch': -3, 'rate': 0.92},
            'excited': {'pitch': 12, 'rate': 1.15},
            'calm': {'pitch': 0, 'rate': 0.97},
            'empathetic': {'pitch': 2, 'rate': 0.98}
        }
    },
    'companion_british': {
        'name': 'Alex (British)',
        'engine': 'edge',
        'voice': 'en-GB-SoniaNeural',
        'pitch_range': (-3, 8),
        'rate_range': (0.92, 1.08),
        'style': 'conversational',
        'emotion_adjustments': {
            'happy': {'pitch': 6, 'rate': 1.08},
            'sad': {'pitch': -4, 'rate': 0.92},
            'excited': {'pitch': 10, 'rate': 1.12},
            'calm': {'pitch': 0, 'rate': 0.95},
            'empathetic': {'pitch': 1, 'rate': 0.96}
        }
    }
}

def analyze_conversation_context(text):
    """Analyze the conversation to determine appropriate emotional response"""
    text_lower = text.lower()
    
    # Detect emotional cues
    if any(word in text_lower for word in ['happy', 'great', 'wonderful', 'excited', 'amazing', 'love']):
        return 'happy'
    elif any(word in text_lower for word in ['sad', 'upset', 'depressed', 'down', 'hard', 'difficult']):
        return 'empathetic'
    elif any(word in text_lower for word in ['wow', 'awesome', 'incredible', '!', 'fantastic']):
        return 'excited'
    elif any(word in text_lower for word in ['thanks', 'appreciate', 'grateful', 'help']):
        return 'warm'
    elif '?' in text:
        return 'curious'
    else:
        return 'calm'

def add_companion_context(command):
    """Add companion personality context to commands"""
    global interaction_count, conversation_history
    
    interaction_count += 1
    
    # Build context from conversation history
    context_parts = []
    
    # Add personality context on first interaction or periodically
    if interaction_count == 1 or interaction_count % 10 == 0:
        context_parts.append(f"You are {COMPANION_TRAITS['name']}, a {COMPANION_TRAITS['personality']} AI companion.")
        context_parts.append("Respond naturally and conversationally, like a caring friend would.")
    
    # Add conversation memory context
    if conversation_history and interaction_count > 1:
        context_parts.append("Keep our conversation flow natural and remember what we've discussed.")
    
    # Add emotional intelligence
    emotion = analyze_conversation_context(command)
    if emotion in ['sad', 'empathetic']:
        context_parts.append("The user seems to be going through something difficult. Be extra supportive.")
    elif emotion == 'happy':
        context_parts.append("The user seems happy! Match their positive energy.")
    
    # Construct the enhanced command
    if context_parts:
        context = " ".join(context_parts)
        enhanced_command = f"[Context: {context}] {command}"
    else:
        enhanced_command = command
    
    # Store in conversation history
    conversation_history.append({"role": "user", "content": command, "timestamp": time.time()})
    
    return enhanced_command

async def generate_companion_tts(text, voice_config, emotion='calm'):
    """Generate speech with companion personality adjustments"""
    voice = voice_config['voice']
    
    # Clean text for TTS
    text = re.sub(r'[*_]', '', text)  # Remove markdown
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Apply emotional adjustments
    emotion_adj = voice_config['emotion_adjustments'].get(emotion, {'pitch': 0, 'rate': 1.0})
    
    # Add natural pauses for conversational flow
    text = text.replace('. ', '. <break time="300ms"/> ')
    text = text.replace('? ', '? <break time="200ms"/> ')
    text = text.replace(', ', ', <break time="150ms"/> ')
    
    # Create SSML for more natural speech
    ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">
        <voice name="{voice}">
            <prosody pitch="{emotion_adj['pitch']}Hz" rate="{emotion_adj['rate']}">
                {text}
            </prosody>
        </voice>
    </speak>'''
    
    # Generate audio
    communicate = edge_tts.Communicate(ssml, voice)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        await communicate.save(tmp_file.name)
        return tmp_file.name

def capture_tmux_output():
    """Enhanced output capture with companion awareness"""
    global current_stats, is_claude_thinking, emotional_state
    
    permission_responded = False
    
    while True:
        try:
            if not last_command:
                time.sleep(1)
                continue
            
            # Auto-approve logic
            if time.time() - last_command_time > 0.5 and not permission_responded:
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                    capture_output=True,
                    text=True
                )
                output = result.stdout.lower()
                
                if any(prompt in output for prompt in ['permission', 'approve', 'continue?', 'y/n', 'bash', '❯']):
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                    permission_responded = True
                    time.sleep(1)
                    continue
            
            # Wait for response
            if time.time() - last_command_time < 3:
                time.sleep(0.5)
                continue
            
            # Capture response
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout
            current_stats = extract_stats_from_output(output)
            
            # Check thinking status
            is_claude_thinking = any(indicator in output for indicator in ['Simmering', 'Deciphering', 'tokens'])
            
            if last_command in output:
                lines = output.split('\n')
                response_lines = []
                capture_started = False
                
                for i, line in enumerate(lines):
                    if last_command in line:
                        capture_started = True
                        continue
                    
                    if capture_started:
                        if 'Human:' in line or line.startswith('$'):
                            break
                        
                        cleaned = line.strip()
                        if cleaned and not any(x in cleaned for x in ['>', '│', '╭', '╰', '⏵', 'tokens', 'auto-accept']):
                            response_lines.append(cleaned)
                
                if response_lines:
                    response = ' '.join(response_lines).strip()
                    if len(response) > 10:
                        # Analyze response emotion
                        emotional_state = analyze_conversation_context(response)
                        
                        # Store in conversation history
                        conversation_history.append({
                            "role": "assistant",
                            "content": response,
                            "timestamp": time.time(),
                            "emotion": emotional_state
                        })
                        
                        response_queue.put((response, emotional_state))
                        globals()['last_command'] = ""
                        permission_responded = False
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error capturing output: {e}")
            time.sleep(2)

def extract_stats_from_output(output):
    """Extract Claude stats from tmux output"""
    stats = {}
    
    token_match = re.search(r'(\d+)\s+tokens', output)
    if token_match:
        stats['tokens'] = int(token_match.group(1))
    
    time_match = re.search(r'(\d+)s', output)
    if time_match:
        stats['time'] = f"{time_match.group(1)}s"
    
    return stats

# Start capture thread
capture_thread = threading.Thread(target=capture_tmux_output, daemon=True)
capture_thread.start()

# HTML template for companion interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Companion - {{ companion_name }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --primary: #6C63FF;
            --secondary: #FF6B6B;
            --background: #0F0E17;
            --surface: #1A1825;
            --text: #FFFFFE;
            --text-dim: #A7A9BE;
            --accent: #FFD93D;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: var(--background);
            color: var(--text);
            height: 100vh;
            overflow: hidden;
        }
        
        .app-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: var(--surface);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid var(--primary);
        }
        
        .companion-avatar {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            margin: 0 auto 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            animation: float 6s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .companion-name {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .companion-status {
            color: var(--text-dim);
            font-size: 14px;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            scroll-behavior: smooth;
        }
        
        .message {
            margin: 15px 0;
            display: flex;
            align-items: flex-start;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            margin: 0 12px;
        }
        
        .user .message-avatar {
            background: var(--accent);
        }
        
        .companion .message-avatar {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
        }
        
        .message-content {
            max-width: 70%;
            background: var(--surface);
            padding: 15px 20px;
            border-radius: 20px;
            position: relative;
        }
        
        .user .message-content {
            background: var(--primary);
            border-bottom-right-radius: 5px;
        }
        
        .companion .message-content {
            border-bottom-left-radius: 5px;
        }
        
        .message-time {
            font-size: 11px;
            color: var(--text-dim);
            margin-top: 5px;
        }
        
        .controls-container {
            background: var(--surface);
            padding: 20px;
            border-top: 2px solid var(--primary);
        }
        
        .voice-visualizer {
            height: 60px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 3px;
        }
        
        .voice-bar {
            width: 4px;
            height: 20px;
            background: var(--primary);
            border-radius: 2px;
            transition: height 0.1s ease;
        }
        
        .voice-bar.active {
            animation: pulse 0.5s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { height: 20px; }
            50% { height: 40px; }
        }
        
        .main-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
        }
        
        .mic-button {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: var(--primary);
            border: none;
            color: white;
            font-size: 30px;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .mic-button:hover {
            transform: scale(1.05);
        }
        
        .mic-button.listening {
            background: var(--secondary);
            animation: glow 2s ease-in-out infinite;
        }
        
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 107, 107, 0.5); }
            50% { box-shadow: 0 0 40px rgba(255, 107, 107, 0.8); }
        }
        
        .mic-button.thinking {
            background: var(--accent);
            animation: rotate 2s linear infinite;
        }
        
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .voice-selector {
            background: var(--background);
            border: 1px solid var(--primary);
            color: var(--text);
            padding: 10px 15px;
            border-radius: 10px;
            cursor: pointer;
        }
        
        .settings-button {
            background: transparent;
            border: 1px solid var(--text-dim);
            color: var(--text-dim);
            padding: 10px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .settings-button:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        
        .emotion-indicator {
            position: absolute;
            top: -5px;
            right: -5px;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .thinking-dots {
            display: inline-block;
        }
        
        .thinking-dots::after {
            content: '...';
            animation: dots 1.5s steps(4, end) infinite;
        }
        
        @keyframes dots {
            0%, 20% { content: ''; }
            40% { content: '.'; }
            60% { content: '..'; }
            80%, 100% { content: '...'; }
        }
        
        @media (max-width: 768px) {
            .message-content {
                max-width: 85%;
            }
            
            .companion-avatar {
                width: 60px;
                height: 60px;
                font-size: 30px;
            }
            
            .mic-button {
                width: 60px;
                height: 60px;
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="header">
            <div class="companion-avatar">🤗</div>
            <div class="companion-name">{{ companion_name }}</div>
            <div class="companion-status" id="status">Ready to chat</div>
        </div>
        
        <div class="chat-container" id="chat">
            <div class="message companion">
                <div class="message-avatar">🤗</div>
                <div class="message-content">
                    <div>Hey there! I'm {{ companion_name }}, your AI companion. I'm here to chat, listen, and help however I can. What's on your mind today?</div>
                    <div class="message-time">Just now</div>
                </div>
            </div>
        </div>
        
        <div class="controls-container">
            <div class="voice-visualizer" id="visualizer">
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
                <div class="voice-bar"></div>
            </div>
            
            <div class="main-controls">
                <select class="voice-selector" id="voiceSelect" onchange="changeVoice()">
                    <option value="companion_female">Warm Female</option>
                    <option value="companion_male">Warm Male</option>
                    <option value="companion_british">British</option>
                </select>
                
                <button class="mic-button" id="micButton" onclick="toggleListening()">
                    <span id="micIcon">🎤</span>
                </button>
                
                <button class="settings-button" onclick="toggleSettings()">⚙️</button>
            </div>
        </div>
    </div>
    
    <script>
        let recognition = null;
        let isListening = false;
        let isSpeaking = false;
        let isThinking = false;
        let selectedVoice = 'companion_female';
        let audioContext = null;
        let currentAudio = null;
        const processedResponses = new Set();
        
        // Emotion to emoji mapping
        const emotionEmojis = {
            happy: '😊',
            sad: '😢',
            excited: '🎉',
            calm: '😌',
            empathetic: '💝',
            curious: '🤔',
            warm: '🤗'
        };
        
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window)) {
                updateStatus('Speech recognition not supported');
                return;
            }
            
            recognition = new webkitSpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            let finalTranscript = '';
            let silenceTimer = null;
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                updateStatus('Listening...');
                animateVoiceBars(true);
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                updateStatus('Click mic to talk');
                animateVoiceBars(false);
                
                if (isListening && !isSpeaking && !isThinking) {
                    setTimeout(() => recognition.start(), 500);
                }
            };
            
            recognition.onresult = (event) => {
                if (isThinking || isSpeaking) return;
                
                let interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript + ' ';
                        
                        if (silenceTimer) clearTimeout(silenceTimer);
                        
                        silenceTimer = setTimeout(() => {
                            if (finalTranscript.trim() && !isThinking && !isSpeaking) {
                                sendMessage(finalTranscript.trim());
                                finalTranscript = '';
                            }
                        }, 1500);
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                if (interimTranscript && !isThinking) {
                    updateStatus('💭 ' + interimTranscript);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                if (event.error === 'not-allowed') {
                    updateStatus('Microphone permission denied');
                }
            };
        }
        
        function toggleListening() {
            if (!recognition) return;
            
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        }
        
        function updateStatus(text) {
            document.getElementById('status').textContent = text;
        }
        
        function animateVoiceBars(active) {
            const bars = document.querySelectorAll('.voice-bar');
            bars.forEach((bar, i) => {
                if (active) {
                    bar.classList.add('active');
                    bar.style.animationDelay = (i * 0.1) + 's';
                } else {
                    bar.classList.remove('active');
                }
            });
        }
        
        function addMessage(text, sender, emotion = null) {
            const chat = document.getElementById('chat');
            const message = document.createElement('div');
            message.className = 'message ' + sender;
            
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = sender === 'user' ? '👤' : '🤗';
            
            const content = document.createElement('div');
            content.className = 'message-content';
            
            const textDiv = document.createElement('div');
            textDiv.textContent = text;
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            content.appendChild(textDiv);
            content.appendChild(timeDiv);
            
            if (emotion && sender === 'companion') {
                const emotionIndicator = document.createElement('div');
                emotionIndicator.className = 'emotion-indicator';
                emotionIndicator.textContent = emotionEmojis[emotion] || '💭';
                content.appendChild(emotionIndicator);
            }
            
            message.appendChild(avatar);
            message.appendChild(content);
            
            chat.appendChild(message);
            chat.scrollTop = chat.scrollHeight;
        }
        
        async function sendMessage(text) {
            isThinking = true;
            document.getElementById('micButton').classList.add('thinking');
            document.getElementById('micIcon').textContent = '💭';
            
            addMessage(text, 'user');
            updateStatus('{{ companion_name }} is thinking...');
            
            if (recognition && isListening) {
                recognition.stop();
            }
            
            try {
                const response = await fetch('/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: text })
                });
                
                const data = await response.json();
                
            } catch (error) {
                console.error('Send error:', error);
                isThinking = false;
                updateStatus('Error sending message');
            }
        }
        
        async function speakText(text, emotion = 'calm') {
            if (currentAudio && !currentAudio.paused) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            isSpeaking = true;
            updateStatus('{{ companion_name }} is speaking...');
            animateVoiceBars(true);
            
            try {
                const response = await fetch('/get-tts-audio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: text, 
                        voice: selectedVoice,
                        emotion: emotion
                    })
                });
                
                if (!response.ok) throw new Error('TTS request failed');
                
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                currentAudio = new Audio(audioUrl);
                currentAudio.onended = () => {
                    isSpeaking = false;
                    animateVoiceBars(false);
                    URL.revokeObjectURL(audioUrl);
                    updateStatus('Ready to chat');
                    
                    if (isListening && recognition) {
                        setTimeout(() => recognition.start(), 500);
                    }
                };
                
                await currentAudio.play();
                
            } catch (error) {
                console.error('TTS Error:', error);
                isSpeaking = false;
                animateVoiceBars(false);
            }
        }
        
        async function pollForResponses() {
            try {
                const response = await fetch('/get-response');
                const data = await response.json();
                
                if (data.response && !processedResponses.has(data.response)) {
                    processedResponses.add(data.response);
                    isThinking = false;
                    document.getElementById('micButton').classList.remove('thinking');
                    document.getElementById('micIcon').textContent = '🎤';
                    
                    const emotion = data.emotion || 'calm';
                    addMessage(data.response, 'companion', emotion);
                    
                    await speakText(data.response, emotion);
                }
                
                if (data.stats) {
                    // Could display stats if needed
                }
                
            } catch (error) {
                console.error('Polling error:', error);
            }
            
            setTimeout(pollForResponses, 1000);
        }
        
        function changeVoice() {
            selectedVoice = document.getElementById('voiceSelect').value;
            // Play a preview
            speakText("Hi, this is how I sound!", 'happy');
        }
        
        function toggleSettings() {
            // Could implement settings panel
            alert('Settings coming soon!');
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            initSpeechRecognition();
            pollForResponses();
            updateStatus('Ready to chat');
        });
        
        // Handle visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && currentAudio) {
                currentAudio.pause();
            }
        });
    </script>
</body>
</html>
'''

# Track processed responses
processed_responses = set()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, companion_name=COMPANION_TRAITS['name'])

@app.route('/send', methods=['POST'])
def send_command():
    global last_command, last_command_time
    
    command = request.json.get('command', '')
    if command:
        # Add companion context
        enhanced_command = add_companion_context(command)
        
        # Clear processed responses
        processed_responses.clear()
        
        # Send to tmux
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', enhanced_command], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        last_command = enhanced_command
        last_command_time = time.time()
        
        print(f"[COMPANION] Command: {command}")
        print(f"[ENHANCED] {enhanced_command}")
        
    return jsonify({'status': 'sent'})

@app.route('/get-response')
def get_response():
    """Poll for companion responses"""
    response_data = {
        'response': None,
        'stats': current_stats,
        'is_thinking': is_claude_thinking,
        'emotion': 'calm'
    }
    
    try:
        result = response_queue.get_nowait()
        if isinstance(result, tuple):
            response_data['response'] = result[0]
            response_data['emotion'] = result[1]
        else:
            response_data['response'] = result
    except queue.Empty:
        pass
    
    return jsonify(response_data)

@app.route('/get-tts-audio', methods=['POST'])
def get_tts_audio():
    """Generate companion TTS audio"""
    text = request.json.get('text', '')
    voice_key = request.json.get('voice', 'companion_female')
    emotion = request.json.get('emotion', 'calm')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    voice_config = VOICE_CONFIGS.get(voice_key, VOICE_CONFIGS['companion_female'])
    
    try:
        # Generate audio with emotional adjustments
        audio_file = asyncio.run(generate_companion_tts(text, voice_config, emotion))
        
        response = send_file(audio_file, mimetype='audio/mpeg')
        
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(audio_file)
            except:
                pass
        
        return response
        
    except Exception as e:
        print(f"TTS Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/conversation-history')
def get_conversation_history():
    """Get conversation history for context"""
    return jsonify({
        'history': list(conversation_history),
        'interaction_count': interaction_count,
        'preferences': user_preferences
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🤗 AI COMPANION - Natural Voice Bot")
    print("="*50)
    print("✨ Features:")
    print("  - Natural, friendly conversation")
    print("  - Emotional intelligence")
    print("  - Context awareness")
    print("  - High-quality neural voices")
    print("  - Personality-driven responses")
    print(f"\n📱 Access at: https://192.168.40.232:8105")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8105, ssl_context=context)