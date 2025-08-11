#!/usr/bin/env python3
"""
Advanced AI Companion Voice Bot with Enhanced Features
- Memory and context persistence
- Mood tracking and adaptation
- Proactive check-ins
- Natural conversation breaks and fillers
- Voice modulation based on context
"""

from flask import Flask, render_template_string, request, jsonify, send_file, session
import subprocess
import ssl
import time
from datetime import datetime, timedelta
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
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database for persistent memory
DB_PATH = 'companion_memory.db'

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  timestamp REAL,
                  role TEXT,
                  content TEXT,
                  emotion TEXT,
                  topics TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                 (user_id TEXT PRIMARY KEY,
                  name TEXT,
                  voice_preference TEXT,
                  interests TEXT,
                  last_interaction REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mood_tracking
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  timestamp REAL,
                  mood TEXT,
                  energy_level INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# Global state
last_command = ""
last_command_time = 0
current_stats = {}
is_claude_thinking = False
response_queue = queue.Queue()
active_sessions = {}

# Enhanced companion configuration
COMPANION_CONFIG = {
    "name": "Alex",
    "personality": {
        "core_traits": ["empathetic", "curious", "supportive", "witty", "thoughtful"],
        "conversation_style": "warm and engaging with natural flow",
        "humor_level": "light and appropriate",
        "formality": "casual but respectful"
    },
    "conversation_elements": {
        "fillers": ["Hmm", "Oh", "Well", "You know", "Actually", "So"],
        "thinking": ["Let me think", "That's interesting", "Good question", "I see"],
        "acknowledgments": ["I hear you", "That makes sense", "Absolutely", "Right"],
        "transitions": ["By the way", "Speaking of which", "That reminds me", "Also"],
        "empathy": ["I understand", "That must be", "I can imagine", "It sounds like"],
        "encouragement": ["You've got this", "That's great", "Keep going", "Well done"]
    },
    "proactive_behaviors": {
        "check_in_phrases": [
            "How are you feeling today?",
            "What's been on your mind lately?",
            "Anything interesting happen recently?",
            "How's your day been so far?",
            "What are you working on these days?"
        ],
        "follow_up_phrases": [
            "How did that go?",
            "Any updates on that?",
            "Did you manage to figure that out?",
            "How are you feeling about that now?"
        ],
        "mood_responses": {
            "happy": ["That's wonderful to hear!", "Your happiness is contagious!", "I'm so glad!"],
            "sad": ["I'm here for you", "Would you like to talk about it?", "That sounds really tough"],
            "stressed": ["Take a deep breath", "One step at a time", "You're doing your best"],
            "excited": ["That's so exciting!", "Tell me more!", "I can feel your energy!"],
            "neutral": ["Thanks for sharing", "I'm listening", "Go on"]
        }
    },
    "memory_prompts": [
        "Remember when you told me about",
        "Last time you mentioned",
        "You were working on",
        "How's your {topic} going?"
    ]
}

# Enhanced voice configurations with more nuanced settings
VOICE_PROFILES = {
    'warm_supportive': {
        'name': 'Warm & Supportive',
        'engine': 'edge',
        'voice': 'en-US-AriaNeural',
        'base_pitch': 0,
        'base_rate': 0.95,
        'prosody_style': 'friendly',
        'emphasis': 'moderate'
    },
    'cheerful_energetic': {
        'name': 'Cheerful & Energetic',
        'engine': 'edge',
        'voice': 'en-US-JennyNeural',
        'base_pitch': 5,
        'base_rate': 1.05,
        'prosody_style': 'cheerful',
        'emphasis': 'strong'
    },
    'calm_soothing': {
        'name': 'Calm & Soothing',
        'engine': 'edge',
        'voice': 'en-US-AnaNeural',
        'base_pitch': -3,
        'base_rate': 0.9,
        'prosody_style': 'gentle',
        'emphasis': 'reduced'
    },
    'professional_clear': {
        'name': 'Professional & Clear',
        'engine': 'edge',
        'voice': 'en-US-MichelleNeural',
        'base_pitch': 0,
        'base_rate': 1.0,
        'prosody_style': 'newscast',
        'emphasis': 'moderate'
    }
}

def get_user_id(ip_address):
    """Generate consistent user ID from IP"""
    return hashlib.md5(ip_address.encode()).hexdigest()[:8]

def save_conversation(user_id, role, content, emotion='neutral', topics=None):
    """Save conversation to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO conversations (user_id, timestamp, role, content, emotion, topics)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, time.time(), role, content, emotion, json.dumps(topics or [])))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, limit=10):
    """Retrieve recent conversation history"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT timestamp, role, content, emotion FROM conversations
                 WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?''',
              (user_id, limit))
    history = c.fetchall()
    conn.close()
    return history[::-1]  # Reverse to get chronological order

def analyze_user_mood(text, history):
    """Advanced mood analysis based on text and history"""
    text_lower = text.lower()
    
    # Mood indicators
    mood_indicators = {
        'happy': ['happy', 'great', 'wonderful', 'excited', 'amazing', 'fantastic', 'good', 'love'],
        'sad': ['sad', 'down', 'depressed', 'unhappy', 'lonely', 'miss', 'lost', 'cry'],
        'stressed': ['stressed', 'overwhelmed', 'anxious', 'worried', 'pressure', 'deadline', 'busy'],
        'angry': ['angry', 'mad', 'frustrated', 'annoyed', 'irritated', 'upset', 'hate'],
        'tired': ['tired', 'exhausted', 'sleepy', 'fatigue', 'worn out', 'drained'],
        'excited': ['excited', 'thrilled', 'can\'t wait', 'looking forward', 'pumped'],
        'peaceful': ['peaceful', 'calm', 'relaxed', 'content', 'serene', 'tranquil']
    }
    
    # Count mood indicators
    mood_scores = {mood: 0 for mood in mood_indicators}
    for mood, indicators in mood_indicators.items():
        for indicator in indicators:
            if indicator in text_lower:
                mood_scores[mood] += 1
    
    # Also consider punctuation and caps
    if text.count('!') > 1 or text.isupper():
        mood_scores['excited'] += 1
    if '?' in text and any(w in text_lower for w in ['how', 'what', 'why', 'when']):
        mood_scores['stressed'] += 0.5
    
    # Get dominant mood
    dominant_mood = max(mood_scores.items(), key=lambda x: x[1])
    if dominant_mood[1] == 0:
        return 'neutral'
    return dominant_mood[0]

def generate_contextual_response(user_input, user_id):
    """Generate companion context with memory and personality"""
    # Get user history
    history = get_conversation_history(user_id, 5)
    
    # Analyze mood
    current_mood = analyze_user_mood(user_input, history)
    
    # Build context
    context_parts = [
        f"You are {COMPANION_CONFIG['name']}, an AI companion with these traits: {', '.join(COMPANION_CONFIG['personality']['core_traits'])}.",
        f"Conversation style: {COMPANION_CONFIG['personality']['conversation_style']}."
    ]
    
    # Add conversation history context
    if history:
        recent_topics = []
        for _, role, content, _ in history[-3:]:
            if role == 'user':
                recent_topics.append(content[:50])
        if recent_topics:
            context_parts.append(f"Recent conversation touched on: {'; '.join(recent_topics)}")
    
    # Add mood-appropriate guidance
    if current_mood in ['sad', 'stressed', 'angry']:
        context_parts.append("Be extra supportive and empathetic. Listen actively.")
    elif current_mood in ['happy', 'excited']:
        context_parts.append("Match their positive energy while staying grounded.")
    
    # Add natural conversation elements
    if random.random() < 0.3:  # 30% chance to use filler
        filler = random.choice(COMPANION_CONFIG['conversation_elements']['fillers'])
        context_parts.append(f"Start with '{filler}' for natural flow.")
    
    # Check for follow-up opportunity
    if history and len(history) > 2:
        last_user_msg = next((h[2] for h in reversed(history) if h[1] == 'user'), None)
        if last_user_msg and any(word in last_user_msg.lower() for word in ['will', 'going to', 'plan to', 'trying to']):
            follow_up = random.choice(COMPANION_CONFIG['proactive_behaviors']['follow_up_phrases'])
            context_parts.append(f"Consider asking: '{follow_up}'")
    
    # Save user input
    save_conversation(user_id, 'user', user_input, current_mood)
    
    # Construct enhanced command
    context = " ".join(context_parts)
    enhanced_command = f"[Context: {context}] [User mood: {current_mood}] {user_input}"
    
    return enhanced_command, current_mood

async def generate_natural_tts(text, voice_profile, mood='neutral', user_prefs=None):
    """Generate natural-sounding speech with dynamic adjustments"""
    profile = VOICE_PROFILES.get(voice_profile, VOICE_PROFILES['warm_supportive'])
    
    # Clean and prepare text
    text = re.sub(r'[*_]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Dynamic adjustments based on mood
    pitch_adjustment = 0
    rate_adjustment = 1.0
    
    if mood == 'happy':
        pitch_adjustment = 3
        rate_adjustment = 1.05
    elif mood in ['sad', 'stressed']:
        pitch_adjustment = -2
        rate_adjustment = 0.95
    elif mood == 'excited':
        pitch_adjustment = 5
        rate_adjustment = 1.1
    
    # Add natural pauses and emphasis
    text = text.replace('. ', '. <break time="400ms"/> ')
    text = text.replace('? ', '? <break time="300ms"/> ')
    text = text.replace(', ', ', <break time="200ms"/> ')
    text = re.sub(r'\b(really|very|so|quite)\b', r'<emphasis level="strong">\1</emphasis>', text)
    
    # Build SSML
    final_pitch = profile['base_pitch'] + pitch_adjustment
    final_rate = profile['base_rate'] * rate_adjustment
    
    ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">
        <voice name="{profile['voice']}">
            <prosody pitch="{final_pitch}Hz" rate="{final_rate}">
                {text}
            </prosody>
        </voice>
    </speak>'''
    
    # Generate audio
    communicate = edge_tts.Communicate(ssml, profile['voice'])
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        await communicate.save(tmp_file.name)
        return tmp_file.name

def capture_tmux_output():
    """Enhanced output capture with conversation flow management"""
    global current_stats, is_claude_thinking
    
    permission_handled = False
    
    while True:
        try:
            if not last_command:
                time.sleep(1)
                continue
            
            # Quick permission check
            if time.time() - last_command_time < 1 and not permission_handled:
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                    capture_output=True,
                    text=True
                )
                
                if any(p in result.stdout.lower() for p in ['permission', 'approve', 'bash', '❯', 'y/n']):
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                    permission_handled = True
                    time.sleep(1)
                    continue
            
            # Wait for response
            if time.time() - last_command_time < 3:
                time.sleep(0.5)
                continue
            
            # Capture full response
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout
            current_stats = extract_stats_from_output(output)
            is_claude_thinking = any(ind in output for ind in ['Simmering', 'Deciphering', 'tokens'])
            
            # Extract response
            if last_command in output:
                lines = output.split('\n')
                response_lines = []
                capture = False
                
                for line in lines:
                    if last_command in line:
                        capture = True
                        continue
                    
                    if capture:
                        if any(stop in line for stop in ['Human:', 'The user sent', '$']):
                            break
                        
                        cleaned = line.strip()
                        if cleaned and not any(x in cleaned for x in ['>', '│', '╭', 'tokens', 'auto-accept']):
                            response_lines.append(cleaned)
                
                if response_lines:
                    response = ' '.join(response_lines).strip()
                    if len(response) > 10:
                        # Extract user info from command
                        user_match = re.search(r'\[User: ([^\]]+)\]', last_command)
                        user_id = user_match.group(1) if user_match else 'default'
                        
                        # Analyze response mood
                        response_mood = analyze_user_mood(response, [])
                        
                        # Save to history
                        save_conversation(user_id, 'assistant', response, response_mood)
                        
                        # Queue response with metadata
                        response_queue.put({
                            'text': response,
                            'mood': response_mood,
                            'user_id': user_id
                        })
                        
                        globals()['last_command'] = ""
                        permission_handled = False
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Capture error: {e}")
            time.sleep(2)

def extract_stats_from_output(output):
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

# Modern companion UI template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ name }} - Your AI Companion</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #7C3AED;
            --primary-light: #A78BFA;
            --primary-dark: #5B21B6;
            --secondary: #EC4899;
            --bg-dark: #111827;
            --bg-light: #1F2937;
            --text-primary: #F9FAFB;
            --text-secondary: #D1D5DB;
            --accent: #34D399;
            --error: #EF4444;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
            position: relative;
        }
        
        .background-animation {
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: -1;
        }
        
        .blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(40px);
            opacity: 0.3;
            animation: float 20s infinite ease-in-out;
        }
        
        .blob1 {
            top: -100px;
            right: -100px;
            width: 300px;
            height: 300px;
            background: var(--primary);
            animation-delay: 0s;
        }
        
        .blob2 {
            bottom: -150px;
            left: -150px;
            width: 400px;
            height: 400px;
            background: var(--secondary);
            animation-delay: 5s;
        }
        
        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            25% { transform: translate(30px, -30px) scale(1.1); }
            50% { transform: translate(-20px, 20px) scale(0.9); }
            75% { transform: translate(20px, 30px) scale(1.05); }
        }
        
        .app-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
            z-index: 1;
        }
        
        .header {
            background: rgba(31, 41, 55, 0.8);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .companion-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .companion-avatar {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            position: relative;
        }
        
        .status-indicator {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 14px;
            height: 14px;
            background: var(--accent);
            border-radius: 50%;
            border: 2px solid var(--bg-light);
        }
        
        .status-indicator.thinking {
            background: var(--secondary);
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        .companion-details h2 {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 2px;
        }
        
        .companion-status {
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
        }
        
        .icon-button {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        
        .icon-button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            scroll-behavior: smooth;
        }
        
        .date-divider {
            text-align: center;
            margin: 20px 0;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .message {
            margin: 12px 0;
            display: flex;
            align-items: flex-end;
            gap: 10px;
            animation: messageSlide 0.3s ease-out;
        }
        
        @keyframes messageSlide {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 18px;
            border-radius: 18px;
            position: relative;
            word-wrap: break-word;
        }
        
        .user .message-content {
            background: var(--primary);
            border-bottom-right-radius: 4px;
        }
        
        .companion .message-content {
            background: var(--bg-light);
            border-bottom-left-radius: 4px;
        }
        
        .message-time {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 4px;
            opacity: 0;
            transition: opacity 0.2s;
        }
        
        .message:hover .message-time {
            opacity: 1;
        }
        
        .typing-indicator {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 8px 12px;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            background: var(--text-secondary);
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
            30% { opacity: 1; transform: scale(1); }
        }
        
        .input-container {
            background: rgba(31, 41, 55, 0.8);
            backdrop-filter: blur(10px);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
        }
        
        .input-wrapper {
            display: flex;
            align-items: center;
            gap: 15px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .voice-button {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--primary);
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            transition: all 0.3s;
            position: relative;
            box-shadow: var(--shadow);
        }
        
        .voice-button:hover {
            transform: scale(1.05);
            background: var(--primary-light);
        }
        
        .voice-button.listening {
            background: var(--error);
            animation: recordPulse 1.5s infinite;
        }
        
        @keyframes recordPulse {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            50% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        
        .voice-button.speaking {
            background: var(--accent);
        }
        
        .input-field {
            flex: 1;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 25px;
            padding: 15px 20px;
            color: var(--text-primary);
            font-size: 16px;
            transition: all 0.2s;
        }
        
        .input-field:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(255, 255, 255, 0.15);
        }
        
        .voice-settings {
            background: rgba(31, 41, 55, 0.95);
            backdrop-filter: blur(10px);
            position: absolute;
            bottom: 100px;
            right: 20px;
            padding: 20px;
            border-radius: 12px;
            box-shadow: var(--shadow);
            display: none;
            min-width: 250px;
        }
        
        .voice-settings.show {
            display: block;
            animation: slideUp 0.3s ease-out;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .settings-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
        }
        
        .voice-option {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .voice-option:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .voice-option.selected {
            background: var(--primary);
        }
        
        .mood-indicator {
            display: inline-block;
            margin-left: 8px;
            font-size: 16px;
        }
        
        @media (max-width: 768px) {
            .message-content {
                max-width: 85%;
            }
            
            .input-wrapper {
                gap: 10px;
            }
            
            .voice-button {
                width: 48px;
                height: 48px;
                font-size: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="background-animation">
        <div class="blob blob1"></div>
        <div class="blob blob2"></div>
    </div>
    
    <div class="app-container">
        <div class="header">
            <div class="companion-info">
                <div class="companion-avatar">
                    🤗
                    <div class="status-indicator" id="statusIndicator"></div>
                </div>
                <div class="companion-details">
                    <h2>{{ name }}</h2>
                    <div class="companion-status" id="companionStatus">Ready to chat</div>
                </div>
            </div>
            <div class="header-actions">
                <button class="icon-button" onclick="toggleVoiceSettings()">🎵</button>
                <button class="icon-button" onclick="clearChat()">🗑️</button>
            </div>
        </div>
        
        <div class="chat-container" id="chatContainer">
            <div class="date-divider">Today</div>
            <div class="message companion">
                <div class="message-content">
                    <div>Hey there! I'm {{ name }}, your AI companion. I'm here to chat, listen, and support you however I can. How are you doing today?</div>
                    <div class="message-time">Just now</div>
                </div>
            </div>
        </div>
        
        <div class="input-container">
            <div class="input-wrapper">
                <button class="voice-button" id="voiceButton" onclick="toggleVoice()">
                    <span id="voiceIcon">🎤</span>
                </button>
                <input type="text" class="input-field" id="textInput" placeholder="Type a message or use voice..." onkeypress="handleKeyPress(event)">
            </div>
        </div>
        
        <div class="voice-settings" id="voiceSettings">
            <div class="settings-title">Voice Settings</div>
            <div class="voice-option" onclick="selectVoice('warm_supportive')">Warm & Supportive</div>
            <div class="voice-option" onclick="selectVoice('cheerful_energetic')">Cheerful & Energetic</div>
            <div class="voice-option" onclick="selectVoice('calm_soothing')">Calm & Soothing</div>
            <div class="voice-option selected" onclick="selectVoice('professional_clear')">Professional & Clear</div>
        </div>
    </div>
    
    <script>
        let recognition = null;
        let isListening = false;
        let isSpeaking = false;
        let isThinking = false;
        let selectedVoice = 'warm_supportive';
        let currentAudio = null;
        let sessionId = null;
        const processedResponses = new Set();
        
        // Mood emojis
        const moodEmojis = {
            happy: '😊',
            sad: '😢',
            stressed: '😰',
            angry: '😠',
            tired: '😴',
            excited: '🎉',
            peaceful: '😌',
            neutral: '💭'
        };
        
        function initSession() {
            sessionId = localStorage.getItem('companionSessionId');
            if (!sessionId) {
                sessionId = Date.now().toString(36) + Math.random().toString(36).substr(2);
                localStorage.setItem('companionSessionId', sessionId);
            }
        }
        
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
                updateStatus('Speech recognition not supported');
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            let finalTranscript = '';
            let silenceTimer = null;
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('voiceButton').classList.add('listening');
                document.getElementById('voiceIcon').textContent = '🔴';
                updateStatus('Listening...');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('voiceButton').classList.remove('listening');
                document.getElementById('voiceIcon').textContent = '🎤';
                updateStatus('Ready to chat');
                
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
                            if (finalTranscript.trim()) {
                                sendMessage(finalTranscript.trim());
                                finalTranscript = '';
                            }
                        }, 1500);
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                if (interimTranscript) {
                    document.getElementById('textInput').value = finalTranscript + interimTranscript;
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
            };
        }
        
        function toggleVoice() {
            if (!recognition) return;
            
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                const input = document.getElementById('textInput');
                if (input.value.trim()) {
                    sendMessage(input.value.trim());
                    input.value = '';
                }
            }
        }
        
        async function sendMessage(text) {
            if (isThinking) return;
            
            isThinking = true;
            document.getElementById('statusIndicator').classList.add('thinking');
            updateStatus('{{ name }} is thinking...');
            
            // Add user message to chat
            addMessage(text, 'user');
            
            // Clear input
            document.getElementById('textInput').value = '';
            
            // Stop listening while processing
            if (recognition && isListening) {
                recognition.stop();
            }
            
            try {
                const response = await fetch('/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        command: text,
                        session_id: sessionId,
                        voice_preference: selectedVoice
                    })
                });
                
                if (!response.ok) throw new Error('Failed to send message');
                
            } catch (error) {
                console.error('Send error:', error);
                isThinking = false;
                updateStatus('Error sending message');
                document.getElementById('statusIndicator').classList.remove('thinking');
            }
        }
        
        function addMessage(text, sender, mood = null) {
            const container = document.getElementById('chatContainer');
            const message = document.createElement('div');
            message.className = 'message ' + sender;
            
            const content = document.createElement('div');
            content.className = 'message-content';
            
            const textDiv = document.createElement('div');
            textDiv.textContent = text;
            if (mood && sender === 'companion') {
                const moodSpan = document.createElement('span');
                moodSpan.className = 'mood-indicator';
                moodSpan.textContent = moodEmojis[mood] || '';
                textDiv.appendChild(moodSpan);
            }
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            content.appendChild(textDiv);
            content.appendChild(timeDiv);
            message.appendChild(content);
            
            container.appendChild(message);
            container.scrollTop = container.scrollHeight;
        }
        
        function showTypingIndicator() {
            const container = document.getElementById('chatContainer');
            const typing = document.createElement('div');
            typing.className = 'message companion';
            typing.id = 'typingIndicator';
            
            const content = document.createElement('div');
            content.className = 'message-content typing-indicator';
            content.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
            
            typing.appendChild(content);
            container.appendChild(typing);
            container.scrollTop = container.scrollHeight;
        }
        
        function removeTypingIndicator() {
            const typing = document.getElementById('typingIndicator');
            if (typing) typing.remove();
        }
        
        async function speakText(text, mood = 'neutral') {
            if (currentAudio && !currentAudio.paused) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            isSpeaking = true;
            document.getElementById('voiceButton').classList.add('speaking');
            updateStatus('{{ name }} is speaking...');
            
            try {
                const response = await fetch('/get-tts-audio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: text, 
                        voice: selectedVoice,
                        mood: mood,
                        session_id: sessionId
                    })
                });
                
                if (!response.ok) throw new Error('TTS failed');
                
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                currentAudio = new Audio(audioUrl);
                currentAudio.onended = () => {
                    isSpeaking = false;
                    document.getElementById('voiceButton').classList.remove('speaking');
                    updateStatus('Ready to chat');
                    URL.revokeObjectURL(audioUrl);
                    
                    // Resume listening
                    if (isListening && recognition) {
                        setTimeout(() => recognition.start(), 500);
                    }
                };
                
                await currentAudio.play();
                
            } catch (error) {
                console.error('TTS Error:', error);
                isSpeaking = false;
                document.getElementById('voiceButton').classList.remove('speaking');
            }
        }
        
        async function pollForResponses() {
            try {
                const response = await fetch('/get-response');
                const data = await response.json();
                
                if (data.response && !processedResponses.has(data.response.text)) {
                    processedResponses.add(data.response.text);
                    
                    isThinking = false;
                    document.getElementById('statusIndicator').classList.remove('thinking');
                    removeTypingIndicator();
                    
                    // Add message with mood
                    addMessage(data.response.text, 'companion', data.response.mood);
                    
                    // Speak the response
                    await speakText(data.response.text, data.response.mood);
                }
                
            } catch (error) {
                console.error('Polling error:', error);
            }
            
            setTimeout(pollForResponses, 1000);
        }
        
        function updateStatus(text) {
            document.getElementById('companionStatus').textContent = text;
        }
        
        function toggleVoiceSettings() {
            const settings = document.getElementById('voiceSettings');
            settings.classList.toggle('show');
        }
        
        function selectVoice(voice) {
            selectedVoice = voice;
            document.querySelectorAll('.voice-option').forEach(option => {
                option.classList.remove('selected');
            });
            event.target.classList.add('selected');
            toggleVoiceSettings();
            
            // Test voice
            speakText('This is how I sound now!', 'happy');
        }
        
        function clearChat() {
            if (confirm('Clear conversation history?')) {
                const container = document.getElementById('chatContainer');
                container.innerHTML = '<div class="date-divider">Today</div>';
                addMessage("Let's start fresh! How can I help you?", 'companion');
            }
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            initSession();
            initSpeechRecognition();
            pollForResponses();
        });
        
        // Auto-save conversation preference
        window.addEventListener('beforeunload', () => {
            localStorage.setItem('selectedVoice', selectedVoice);
        });
        
        // Restore preferences
        window.addEventListener('load', () => {
            const savedVoice = localStorage.getItem('selectedVoice');
            if (savedVoice) {
                selectedVoice = savedVoice;
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
    return render_template_string(HTML_TEMPLATE, name=COMPANION_CONFIG['name'])

@app.route('/send', methods=['POST'])
def send_command():
    global last_command, last_command_time
    
    data = request.json
    command = data.get('command', '')
    session_id = data.get('session_id', 'default')
    voice_pref = data.get('voice_preference', 'warm_supportive')
    
    if command:
        # Get user ID from request
        user_id = get_user_id(request.remote_addr + session_id)
        
        # Generate contextual response
        enhanced_command, mood = generate_contextual_response(command, user_id)
        
        # Add user identifier
        enhanced_command = f"[User: {user_id}] {enhanced_command}"
        
        # Clear processed responses
        processed_responses.clear()
        
        # Send to tmux
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', enhanced_command], check=True)
        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
        
        last_command = enhanced_command
        last_command_time = time.time()
        
        # Update user preferences
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO user_preferences 
                     (user_id, voice_preference, last_interaction) 
                     VALUES (?, ?, ?)''',
                  (user_id, voice_pref, time.time()))
        conn.commit()
        conn.close()
        
        print(f"[USER-{user_id}] {command}")
        print(f"[MOOD] {mood}")
        
    return jsonify({'status': 'sent'})

@app.route('/get-response')
def get_response():
    """Poll for companion responses"""
    response_data = {
        'response': None,
        'stats': current_stats,
        'is_thinking': is_claude_thinking
    }
    
    try:
        result = response_queue.get_nowait()
        if isinstance(result, dict):
            response_data['response'] = {
                'text': result['text'],
                'mood': result.get('mood', 'neutral'),
                'user_id': result.get('user_id', 'default')
            }
    except queue.Empty:
        pass
    
    return jsonify(response_data)

@app.route('/get-tts-audio', methods=['POST'])
def get_tts_audio():
    """Generate natural TTS audio"""
    data = request.json
    text = data.get('text', '')
    voice_profile = data.get('voice', 'warm_supportive')
    mood = data.get('mood', 'neutral')
    session_id = data.get('session_id', 'default')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    user_id = get_user_id(request.remote_addr + session_id)
    
    try:
        # Get user preferences
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT voice_preference FROM user_preferences WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            voice_profile = result[0]
        
        # Generate audio
        audio_file = asyncio.run(generate_natural_tts(text, voice_profile, mood))
        
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

@app.route('/conversation-summary/<user_id>')
def get_conversation_summary(user_id):
    """Get conversation summary for a user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get conversation stats
    c.execute('''SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
                 FROM conversations WHERE user_id = ?''', (user_id,))
    count, first, last = c.fetchone()
    
    # Get mood distribution
    c.execute('''SELECT emotion, COUNT(*) FROM conversations 
                 WHERE user_id = ? AND role = 'user' 
                 GROUP BY emotion''', (user_id,))
    moods = dict(c.fetchall())
    
    conn.close()
    
    return jsonify({
        'message_count': count,
        'first_interaction': first,
        'last_interaction': last,
        'mood_distribution': moods
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🤗 ADVANCED AI COMPANION")
    print("="*50)
    print("✨ Features:")
    print("  - Natural conversation with memory")
    print("  - Emotional intelligence & mood tracking")
    print("  - Personalized interactions")
    print("  - Voice modulation based on context")
    print("  - Proactive engagement")
    print(f"\n📱 Access at: https://192.168.40.232:8106")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8106, ssl_context=context)