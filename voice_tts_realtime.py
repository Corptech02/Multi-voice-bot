#!/usr/bin/env python3
"""
Claude Voice Bot with Real-Time Commentary Capture
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
from gtts import gTTS
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
last_commentary_hash = ""
last_seen_lines = set()  # Track lines we've already seen
last_output_time = time.time()  # Track when we last saw new output
pending_final_message = None  # Store potential final message
final_message_timer = None  # Timer for sending final message

def extract_stats_from_output(output):
    """Extract time and token info from output"""
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

def capture_tmux_output():
    """Continuously capture tmux output to detect Claude's responses"""
    global current_stats, is_claude_thinking, last_commentary_hash, last_seen_lines, last_command, last_command_time, last_output_time
    
    last_output_hash = ""
    permission_cooldown = 0
    last_full_output = ""  # Store previous full output to detect changes
    
    while True:
        try:
            # Capture tmux pane
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                capture_output=True,
                text=True
            )
            
            full_output = result.stdout
            output_lower = full_output.lower()
            
            # Create a hash of the current output to detect changes
            current_hash = hash(full_output[-1000:])  # Last 1000 chars
            
            # Check if output has changed
            if current_hash != last_output_hash:
                last_output_hash = current_hash
                last_output_time = time.time()  # Reset the output timer
                
            # Check for permission prompts and cooldown
            if time.time() > permission_cooldown:
                
                # Check for permission prompts (existing code)
                permission_patterns = [
                    r'❯\s*1\.\s*yes',
                    r'do you want to proceed\?',
                    r'bash command.*\n.*yes.*\n.*no',
                    r'\b(approve|permission|confirm|continue)\b.*\?',
                    r'\b(yes|no|y/n)\b.*\?',
                    r'press\s+(1|enter|y)',
                    r'\[1\].*yes',
                    r'1\).*yes',
                    r'1\..*yes',
                    r'(execute|run|perform).*\?',
                    r'(allow|grant|authorize).*\?'
                ]
                
                prompt_detected = False
                
                # Check for ❯ symbol (needs original case)
                if '❯' in full_output:
                    lines = full_output.split('\n')
                    for i, line in enumerate(lines):
                        if '❯' in line:
                            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                            if any(x in context.lower() for x in ['yes', '1.', 'proceed', 'approve']):
                                prompt_detected = True
                                print(f"[AUTO-APPROVE] Detected ❯ prompt in context: {context[:100]}")
                                break
                
                if not prompt_detected:
                    for pattern in permission_patterns:
                        if re.search(pattern, output_lower, re.IGNORECASE | re.MULTILINE):
                            prompt_detected = True
                            print(f"[AUTO-APPROVE] Detected pattern: {pattern}")
                            break
                
                if prompt_detected:
                    print("[AUTO-APPROVE] Permission prompt detected! Sending approval...")
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                    print("[AUTO-APPROVE] Sent: 1 + Enter")
                    permission_cooldown = time.time() + 3
                    continue
            
            # Update stats
            current_stats = extract_stats_from_output(full_output)
            
            # Check if Claude is thinking or using tools
            thinking_indicators = ['Simmering', 'Deciphering', 'tokens', 'esc to interrupt', 
                                   'Running bash command', 'Editing file', 'Reading file',
                                   'Writing file', 'Searching', 'Using tool']
            was_thinking = is_claude_thinking
            if any(indicator in full_output for indicator in thinking_indicators):
                is_claude_thinking = True
            else:
                is_claude_thinking = False
                
            # Detect when Claude just finished thinking (transition from thinking to not thinking)
            just_finished_thinking = was_thinking and not is_claude_thinking
            
            # REAL-TIME COMMENTARY CAPTURE
            if last_command and time.time() - last_command_time > 0.5:
                # Only process if output has changed significantly
                if full_output != last_full_output:
                    # Find what's new by comparing with last output
                    new_content = ""
                    if last_full_output and len(full_output) > len(last_full_output):
                        # Get the new content that was added
                        new_content = full_output[len(last_full_output):]
                    
                    lines = full_output.split('\n')
                    
                    # Process lines from bottom up to catch latest comments
                    for line in reversed(lines[-50:]):  # Check last 50 lines
                        line_hash = hash(line)
                        
                        # Skip if we've already processed this line
                        if line_hash in last_seen_lines:
                            continue
                        
                        cleaned_line = line.strip()
                        
                        # Check if this is a gray circle commentary line
                        is_commentary = (cleaned_line.startswith('●') and 
                                       not any(cleaned_line.startswith(f'● {tool}(') for tool in 
                                       ['Update', 'Call', 'Read', 'Edit', 'Write', 'Bash', 'MultiEdit', 
                                        'Grep', 'Glob', 'LS', 'TodoWrite', 'Task', 'ExitPlanMode', 
                                        'Search', 'WebFetch', 'WebSearch', 'NotebookRead', 'NotebookEdit']) and
                                       not re.match(r'^●\s*\d+', cleaned_line) and  # Not line numbers
                                       not '(' in cleaned_line and  # Not function calls
                                       not ')' in cleaned_line and
                                       not 'Update Todos' in cleaned_line and  # Skip todo updates
                                       not 'Todos have been modified' in cleaned_line)
                        
                        if is_commentary:
                            # Extract the actual comment text
                            comment_text = re.sub(r'^●\s*', '', cleaned_line)
                            
                            # Skip empty or very short comments
                            if len(comment_text) > 5:
                                # Send this comment immediately
                                comment_hash = hash(comment_text)
                                if comment_hash not in processed_responses:
                                    processed_responses.add(comment_hash)
                                    last_seen_lines.add(line_hash)
                                    response_queue.put(comment_text)
                                    print(f"[REAL-TIME COMMENT] {comment_text}")
                        
                        # Special handling for final messages when Claude finishes
                        elif just_finished_thinking and cleaned_line and len(cleaned_line) > 10:
                            # Look for final summary lines that don't have the gray circle
                            # These are often the "completion" messages like "Great! The voice assistant is running..."
                            # Skip lines that look like prompts, paths, or technical output
                            if (not cleaned_line.startswith(('$', '/', '>', '<', '[', '(', '{', '#', '-', '*', '•', '○', '?', '⎿', '·')) and
                                not any(skip in cleaned_line.lower() for skip in 
                                        ['error:', 'warning:', 'traceback', 'exception', 'failed', 
                                         '.py', '.js', '.html', 'http://', 'https://', '```',
                                         'file:', 'line:', 'column:', '==', '--', '**',
                                         'for shortcuts', 'esc to interrupt', 'ctrl+', 'alt+',
                                         'running…', 'wizarding', 'wibbling', 'tokens']) and
                                not re.match(r'^\d+[:\-\s]', cleaned_line) and  # Not timestamps or line numbers
                                not re.match(r'^[A-Z][A-Z\s]{2,}:', cleaned_line) and  # Not section headers like "FIXES:"
                                '::' not in cleaned_line and  # Not log entries
                                '|' not in cleaned_line and  # Not tables or formatted output
                                '╭' not in cleaned_line and '╰' not in cleaned_line and  # Not box drawing
                                cleaned_line.count(' ') >= 2):  # Has at least a few words
                                
                                # This looks like a natural language summary
                                comment_hash = hash(cleaned_line)
                                if comment_hash not in processed_responses:
                                    # Get only the first 1-2 sentences
                                    sentences = []
                                    # Split by sentence endings
                                    parts = re.split(r'(?<=[.!?])\s+', cleaned_line)
                                    
                                    for part in parts:
                                        if part.strip():
                                            sentences.append(part.strip())
                                            # Stop after 2 sentences or 150 characters
                                            if len(sentences) >= 2 or len(' '.join(sentences)) > 150:
                                                break
                                    
                                    if sentences:
                                        brief_message = ' '.join(sentences)
                                        # Make sure it's not too long
                                        if len(brief_message) > 200:
                                            brief_message = brief_message[:197] + '...'
                                        
                                        processed_responses.add(comment_hash)
                                        last_seen_lines.add(line_hash)
                                        response_queue.put(brief_message)
                                        print(f"[FINAL MESSAGE] {brief_message}")
                                        
                                        # Stop looking for more lines once we found the summary
                                        break
            
            # Timeout-based final message detection
            # If Claude was active but hasn't produced new output for 2 seconds, send any pending final message
            if (last_command and 
                time.time() - last_command_time > 1.0 and  # Command was sent at least 1 second ago
                time.time() - last_output_time > 2.0 and   # No new output for 2 seconds
                not is_claude_thinking):                    # Claude is not currently thinking
                
                # Look for a final message in the last few lines
                lines = full_output.split('\n')
                for line in reversed(lines[-20:]):  # Check last 20 lines
                    cleaned_line = line.strip()
                    
                    # Look for final completion messages
                    if (cleaned_line and len(cleaned_line) > 10 and
                        not cleaned_line.startswith(('$', '/', '>', '<', '[', '(', '{', '#', '-', '*', '•', '○', '●', '?', '⎿', '·')) and
                        not any(skip in cleaned_line.lower() for skip in 
                                ['error:', 'warning:', 'traceback', 'exception', 'failed', 
                                 '.py', '.js', '.html', 'http://', 'https://', '```',
                                 'file:', 'line:', 'column:', '==', '--', '**',
                                 'for shortcuts', 'esc to interrupt', 'ctrl+', 'alt+',
                                 'running…', 'wizarding', 'wibbling', 'tokens']) and
                        not re.match(r'^\d+[:\-\s]', cleaned_line) and
                        not re.match(r'^[A-Z][A-Z\s]{2,}:', cleaned_line) and
                        '::' not in cleaned_line and
                        '|' not in cleaned_line and
                        '╭' not in cleaned_line and '╰' not in cleaned_line and
                        cleaned_line.count(' ') >= 2):
                        
                        # This looks like a natural language summary
                        comment_hash = hash(cleaned_line)
                        if comment_hash not in processed_responses:
                            # Get only the first 1-2 sentences
                            sentences = []
                            parts = re.split(r'(?<=[.!?])\s+', cleaned_line)
                            
                            for part in parts:
                                if part.strip():
                                    sentences.append(part.strip())
                                    if len(sentences) >= 2 or len(' '.join(sentences)) > 150:
                                        break
                            
                            if sentences:
                                brief_message = ' '.join(sentences)
                                if len(brief_message) > 200:
                                    brief_message = brief_message[:197] + '...'
                                
                                processed_responses.add(comment_hash)
                                response_queue.put(brief_message)
                                print(f"[TIMEOUT FINAL MESSAGE] {brief_message}")
                                last_command = None  # Clear command to avoid repeated sends
                                break
            
            # Clean up old seen lines periodically (keep last 1000)
            if len(last_seen_lines) > 1000:
                last_seen_lines = set(list(last_seen_lines)[-500:])
            
            # Clean up old processed responses periodically
            if len(processed_responses) > 500:
                processed_responses.clear()
            
            # Update last full output for next iteration
            last_full_output = full_output
            
            time.sleep(0.5)  # Check more frequently for real-time capture
            
        except Exception as e:
            print(f"Error capturing output: {e}")
            time.sleep(2)

# Start the output capture thread
capture_thread = threading.Thread(target=capture_tmux_output, daemon=True)
capture_thread.start()

# HTML template with improved TTS and continuous listening
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant - Real-Time</title>
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
        .conversation {
            margin-top: 20px;
            background: #0f2027;
            border: 1px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
            text-align: left;
        }
        .chat-message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-message {
            background: rgba(0, 255, 0, 0.1);
            border-left: 3px solid #00ff00;
            margin-right: 20%;
        }
        .bot-message {
            background: rgba(155, 89, 182, 0.1);
            border-left: 3px solid #9b59b6;
            margin-left: 20%;
        }
        .message-time {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
        }
        .message-text {
            color: white;
            line-height: 1.5;
        }
        .real-time-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #00ff00;
            border-radius: 50%;
            margin-right: 5px;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        /* Custom scrollbar for chat */
        .conversation::-webkit-scrollbar {
            width: 8px;
        }
        .conversation::-webkit-scrollbar-track {
            background: #16213e;
            border-radius: 4px;
        }
        .conversation::-webkit-scrollbar-thumb {
            background: #00ff00;
            border-radius: 4px;
        }
        .conversation::-webkit-scrollbar-thumb:hover {
            background: #00cc00;
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
            
            <div class="stats-item">
                <div class="stats-label">REAL-TIME</div>
                <div><span class="real-time-indicator"></span>Active</div>
            </div>
        </div>
        
        <div class="content-container">
            <h1>🎙️ Claude Voice Assistant</h1>
            <p style="color: #888;">Real-Time Commentary Mode</p>
            
            <div class="controls">
                <button onclick="toggleAutoSpeak()">Auto-Speak: <span id="autoSpeakStatus">ON</span></button>
                <button onclick="clearConversation()">Clear</button>
                <button onclick="stopSpeaking()">Stop Speaking</button>
            </div>
            
            <div class="voice-controls">
                <div class="voice-option">
                    <label>Voice:</label>
                    <select id="voiceSelect" onchange="updateVoice()"></select>
                    <button onclick="previewVoice()" style="margin-left: 10px; padding: 5px 10px; background: #333; color: #0f0; border: 1px solid #0f0; cursor: pointer;">Preview</button>
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
            
            <h3 style="color: #00ff00; margin-top: 30px; margin-bottom: 10px;">💬 Chat Log</h3>
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
        let speechQueue = [];  // Queue for managing multiple messages
        let selectedVoice = null;
        let continuousMode = true;
        let wasListeningBeforeSpeech = false;
        
        // Initialize speech synthesis
        const synth = window.speechSynthesis;
        let voices = [];
        
        // Load voices with focus on hyper-realistic options
        function loadVoices() {
            voices = synth.getVoices();
            const voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '';
            
            // Ultra-realistic voice profiles with enhanced natural speech patterns
            const hyperRealisticProfiles = [
                // Premium Natural Female Voices
                { name: 'Ava', pattern: /Samantha|Ava|Siri.*Female|Google.*Natural.*Female|Microsoft.*Zira.*Desktop|Microsoft.*Eva/i, gender: 'female', description: 'Natural conversational', rate: 1.05, pitch: 1.05 },
                { name: 'Nova', pattern: /Karen|Microsoft.*Aria|Google.*Wavenet.*Female|Joanna/i, gender: 'female', description: 'Clear professional', rate: 1.0, pitch: 1.1 },
                { name: 'Luna', pattern: /Moira|Tessa|Fiona|Microsoft.*Natasha/i, gender: 'female', description: 'Warm friendly', rate: 0.95, pitch: 1.15 },
                { name: 'Zara', pattern: /Allison|Ava.*Premium|Microsoft.*Zira/i, gender: 'female', description: 'Modern dynamic', rate: 1.1, pitch: 1.0 },
                { name: 'Ivy', pattern: /Susan|Victoria|Veena|Microsoft.*Hazel/i, gender: 'female', description: 'Sophisticated calm', rate: 0.9, pitch: 1.05 },
                
                // Premium Natural Male Voices  
                { name: 'Atlas', pattern: /Daniel|Alex.*English|Microsoft.*David.*Desktop|Microsoft.*Mark/i, gender: 'male', description: 'Deep authoritative', rate: 0.95, pitch: 0.85 },
                { name: 'Phoenix', pattern: /Oliver|Tom|Microsoft.*James|Google.*Wavenet.*Male/i, gender: 'male', description: 'Warm professional', rate: 1.0, pitch: 0.95 },
                { name: 'Orion', pattern: /Rishi|Microsoft.*George|Fred|Gordon/i, gender: 'male', description: 'Natural friendly', rate: 1.05, pitch: 0.9 },
                { name: 'Kai', pattern: /Aaron|Bruce|Microsoft.*Richard/i, gender: 'male', description: 'Young energetic', rate: 1.1, pitch: 1.0 },
                { name: 'River', pattern: /Nathan|Microsoft.*Sean|Russell/i, gender: 'male', description: 'Smooth narrator', rate: 0.9, pitch: 0.88 },
                
                // International Premium Voices
                { name: 'Jasper', pattern: /Google.*UK.*Male|British.*English.*Male|Microsoft.*Hazel.*UK|Daniel.*UK/i, gender: 'male', description: 'British accent', rate: 1.0, pitch: 0.92 },
                { name: 'Willow', pattern: /Google.*UK.*Female|British.*English.*Female|Microsoft.*Hazel.*UK.*Female|Kate/i, gender: 'female', description: 'British accent', rate: 0.98, pitch: 1.08 },
                { name: 'Hunter', pattern: /Google.*Australian.*Male|Microsoft.*James.*Australia|Lee/i, gender: 'male', description: 'Australian accent', rate: 1.05, pitch: 0.9 },
                { name: 'Skye', pattern: /Google.*Australian.*Female|Microsoft.*Natasha.*Australia|Matilda/i, gender: 'female', description: 'Australian accent', rate: 1.02, pitch: 1.12 },
                
                // Enhanced AI Assistant Voices
                { name: 'Sage', pattern: /Microsoft.*Neural|Google.*Studio|Eloquence/i, gender: 'neutral', description: 'Advanced AI', rate: 1.0, pitch: 1.0 },
                { name: 'Echo', pattern: /Whisper|Conversational.*AI|Assistant/i, gender: 'neutral', description: 'Natural AI', rate: 0.95, pitch: 0.98 }
            ];
            
            // Categorize available voices
            const categorizedVoices = {
                '⭐ Premium Female Voices': [],
                '⭐ Premium Male Voices': [],
                '🌍 International Accents': [],
                '🤖 AI Assistant Voices': [],
                '📱 Standard Voices': []
            };
            
            // Process each system voice
            voices.forEach(voice => {
                if (!voice.lang.startsWith('en')) return;
                
                let matched = false;
                
                // Check against hyper-realistic profiles
                for (const profile of hyperRealisticProfiles) {
                    if (profile.pattern.test(voice.name)) {
                        const category = profile.gender === 'female' ? '⭐ Premium Female Voices' :
                                       profile.gender === 'male' ? '⭐ Premium Male Voices' :
                                       profile.gender === 'neutral' ? '🤖 AI Assistant Voices' :
                                       '🌍 International Accents';
                        
                        categorizedVoices[category].push({
                            voice: voice,
                            displayName: profile.name,
                            description: profile.description,
                            realName: voice.name,
                            rate: profile.rate || 1.0,
                            pitch: profile.pitch || 1.0
                        });
                        matched = true;
                        break;
                    }
                }
                
                // If not matched, add to standard voices
                if (!matched) {
                    const cleanName = voice.name
                        .replace(/^(Microsoft |Google |com\.apple\.|com\.apple\.ttsbundle\.)/, '')
                        .replace(/\s*\(.*?\)\s*/g, '')
                        .trim();
                    
                    categorizedVoices['📱 Standard Voices'].push({
                        voice: voice,
                        displayName: cleanName,
                        description: 'System voice',
                        realName: voice.name
                    });
                }
            });
            
            // Add voices to select dropdown
            Object.entries(categorizedVoices).forEach(([category, voiceList]) => {
                if (voiceList.length === 0) return;
                
                const optgroup = document.createElement('optgroup');
                optgroup.label = category;
                
                // Limit standard voices
                const limit = category === '📱 Standard Voices' ? 5 : 20;
                
                voiceList.slice(0, limit).forEach(({voice, displayName, description, rate, pitch}) => {
                    const option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = `${displayName} - ${description}`;
                    option.dataset.voiceName = displayName;
                    option.dataset.realVoiceName = voice.name;
                    option.dataset.voiceSettings = JSON.stringify({ rate: rate || 1.0, pitch: pitch || 1.0 });
                    optgroup.appendChild(option);
                });
                
                voiceSelect.appendChild(optgroup);
            });
            
            // Select the first premium voice available
            const premiumCategories = ['⭐ Premium Female Voices', '⭐ Premium Male Voices'];
            for (const category of premiumCategories) {
                if (categorizedVoices[category].length > 0) {
                    selectedVoice = categorizedVoices[category][0].voice;
                    voiceSelect.value = voices.indexOf(selectedVoice);
                    break;
                }
            }
            
            // Fallback to first available voice
            if (!selectedVoice && voices.length > 0) {
                selectedVoice = voices[0];
                voiceSelect.value = 0;
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
        
        function updateVoice() {
            const voiceSelect = document.getElementById('voiceSelect');
            const option = voiceSelect.options[voiceSelect.selectedIndex];
            selectedVoice = voices[voiceSelect.value];
            
            // Show selected voice info
            if (option && option.dataset.voiceName) {
                updateStatus(`Selected voice: ${option.dataset.voiceName}`);
            }
        }
        
        // Preview voice function
        function previewVoice() {
            const voiceSelect = document.getElementById('voiceSelect');
            const option = voiceSelect.options[voiceSelect.selectedIndex];
            
            if (!option || !selectedVoice) {
                updateStatus('No voice selected');
                return;
            }
            
            const voiceName = option.dataset.voiceName || 'this voice';
            const previewText = `Hi, my name is ${voiceName}. I'm ready to assist you with anything you need.`;
            
            // Speak the preview
            speak(previewText, true);
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
        
        let currentAudio = null; // Track current audio element
        
        function stopSpeaking() {
            // Stop browser TTS
            synth.cancel();
            
            // Stop any playing audio element
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                currentAudio = null;
            }
            
            // Clear speech queue
            speechQueue = [];
            
            // Reset all states
            isSpeaking = false;
            document.getElementById('speakingIndicator').style.display = 'none';
            document.getElementById('micButton').classList.remove('speaking');
            updateStatus('Speech stopped - ready to chat!');
            
            // If was listening before, resume
            if (wasListeningBeforeSpeech && continuousMode && recognition) {
                wasListeningBeforeSpeech = false;
                setTimeout(() => {
                    recognition.start();
                    updateStatus('🔴 Listening - speak when ready');
                }, 300);
            }
        }
        
        async function speak(text, isTest = false) {
            if (!text || (!isTest && !autoSpeak)) return;
            
            // Add to speech queue
            speechQueue.push({ text, isTest });
            
            // If not already speaking, process the queue
            if (!isSpeaking) {
                processSpeechQueue();
            }
        }
        
        async function processSpeechQueue() {
            if (speechQueue.length === 0) {
                isSpeaking = false;
                document.getElementById('speakingIndicator').style.display = 'none';
                document.getElementById('micButton').classList.remove('speaking');
                
                // Resume listening if needed
                if (wasListeningBeforeSpeech && continuousMode && recognition) {
                    setTimeout(() => {
                        recognition.start();
                        updateStatus('🔴 Listening - speak when ready');
                    }, 500);
                }
                wasListeningBeforeSpeech = false;
                return;
            }
            
            const { text, isTest } = speechQueue.shift();
            
            // Stop recognition while speaking (but not for tests)
            if (!isTest && recognition && isListening) {
                recognition.stop();
                wasListeningBeforeSpeech = true;
            }
            
            isSpeaking = true;
            document.getElementById('speakingIndicator').style.display = 'block';
            document.getElementById('micButton').classList.add('speaking');
            if (!isTest) {
                updateStatus('🔊 Claude is speaking...');
            }
            
            // Use browser TTS with enhanced settings for natural speech
            const utterance = new SpeechSynthesisUtterance(text);
            
            // Get voice-specific settings if available
            const voiceSelect = document.getElementById('voiceSelect');
            const selectedOption = voiceSelect.options[voiceSelect.selectedIndex];
            let voiceRate = speechRate;
            let voicePitch = speechPitch;
            
            // Apply voice-specific adjustments for more natural sound
            if (selectedOption && selectedOption.dataset) {
                const voiceData = JSON.parse(selectedOption.dataset.voiceSettings || '{}');
                voiceRate = (voiceData.rate || 1.0) * speechRate;
                voicePitch = (voiceData.pitch || 1.0) * speechPitch;
            }
            
            // Add slight variations for more natural speech
            const variation = 0.02;
            utterance.rate = voiceRate + (Math.random() - 0.5) * variation;
            utterance.pitch = voicePitch + (Math.random() - 0.5) * variation;
            utterance.volume = 0.95; // Slightly lower for more natural sound
            
            if (selectedVoice) {
                utterance.voice = selectedVoice;
            }
            
            utterance.onend = () => {
                // Process next item in queue
                setTimeout(() => processSpeechQueue(), 100);
            };
            
            utterance.onerror = (event) => {
                console.error('Speech error:', event);
                // Try next item in queue
                setTimeout(() => processSpeechQueue(), 100);
            };
            
            synth.speak(utterance);
        }
        
        function addMessage(text, sender) {
            const conv = document.getElementById('conversation');
            const msg = document.createElement('div');
            msg.className = sender === 'user' ? 'chat-message user-message' : 'chat-message bot-message';
            
            const time = new Date().toLocaleTimeString();
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = time;
            
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.innerHTML = `<strong>${sender === 'user' ? '🗣️ You' : '🤖 Claude'}:</strong><br>${text}`;
            
            msg.appendChild(timeDiv);
            msg.appendChild(textDiv);
            conv.appendChild(msg);
            conv.scrollTop = conv.scrollHeight;
        }
        
        function updateStatus(text) {
            document.getElementById('status').textContent = text;
        }
        
        function clearConversation() {
            document.getElementById('conversation').innerHTML = '';
            updateStatus('Conversation cleared');
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
                
                if (data.response) {
                    addMessage(data.response, 'claude');
                    window.claudeThinking = false;
                    
                    // Stop recognition during response
                    if (recognition && isListening) {
                        recognition.stop();
                    }
                    
                    if (autoSpeak) {
                        speak(data.response);
                    } else if (continuousMode) {
                        // If not speaking, resume listening immediately
                        setTimeout(() => {
                            if (continuousMode && !recognition.active) {
                                recognition.start();
                                updateStatus('🔴 Listening - speak when ready');
                            }
                        }, 500);
                    } else {
                        updateStatus('Claude responded - click mic to resume');
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
            let accumulatedTranscript = ''; // Keep all speech accumulated
            let silenceTimer = null;
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                document.getElementById('listeningMode').style.display = 'block';
                updateStatus('🔴 Listening continuously - speak anytime');
                accumulatedTranscript = ''; // Reset when starting fresh
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
                if (window.claudeThinking || isSpeaking) {
                    // Stop recognition if Claude is processing
                    if (window.claudeThinking && recognition) {
                        recognition.stop();
                    }
                    return;
                }
                
                let interimTranscript = '';
                let newFinalTranscript = '';
                
                // Process only new results (from resultIndex onward)
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        newFinalTranscript += transcript + ' ';
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                // Add any new final transcript to accumulated
                if (newFinalTranscript) {
                    accumulatedTranscript += newFinalTranscript;
                }
                
                // Clear any existing silence timer
                if (silenceTimer) clearTimeout(silenceTimer);
                
                // Set a timer to send after 2 seconds of silence
                silenceTimer = setTimeout(() => {
                    if (accumulatedTranscript.trim() && !window.claudeThinking && !isSpeaking) {
                        sendCommand(accumulatedTranscript.trim());
                        accumulatedTranscript = '';
                    }
                }, 2000);
                
                // Show what's being heard (accumulated + interim)
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
                    // Don't set a fixed timeout - let real-time capture handle it
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
                synth.cancel();
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
            initSpeechRecognition();
            // Check for responses every 200ms for real-time capture
            setInterval(checkForResponse, 200);
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send', methods=['POST'])
def send():
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
        
        # Clear any pending responses in queue
        while not response_queue.empty():
            response_queue.get()
        
        # Log it
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] VOICE: {command}")
        
        # Send to tmux with improved reliability
        try:
            # Clear current line first
            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
            time.sleep(0.1)  # Increased delay for better reliability
            
            # Method 1: Use literal mode for text to avoid special character issues
            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '-l', command], check=True)
            time.sleep(0.2)  # Increased delay to ensure text is fully pasted
            
            # Send Enter key - only once to avoid creating extra lines
            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
            
            print(f"[SEND] Command sent successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Primary send failed: {e}, trying paste-buffer method")
            # Try alternative method using tmux paste-buffer
            try:
                # Clear line first
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-u'], check=True)
                time.sleep(0.1)
                
                # Write command WITH newline to buffer and paste
                subprocess.run(['tmux', 'set-buffer', '-b', 'voicecmd', command + '\n'], check=True)
                subprocess.run(['tmux', 'paste-buffer', '-b', 'voicecmd', '-t', 'claude:0'], check=True)
                
                # Still send Enter as backup
                time.sleep(0.1)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                
                print(f"[SEND] Used paste-buffer fallback with newline")
            except Exception as fallback_error:
                print(f"[ERROR] All methods failed: {fallback_error}")
        
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

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  CLAUDE VOICE - REAL-TIME COMMENTARY")
    print("="*50)
    print("✨ Features:")
    print("  - Real-time commentary capture")
    print("  - Speaks Claude's comments as they appear")
    print("  - Continuous listening mode")
    print("  - Multiple voice options")
    print("")
    print("📱 Access at: https://192.168.40.232:8103")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8103, debug=False, ssl_context=context)