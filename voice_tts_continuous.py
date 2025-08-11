#!/usr/bin/env python3
"""
Claude Voice Bot with Realistic TTS and Continuous Listening
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
    global current_stats, is_claude_thinking
    
    last_output_hash = ""
    permission_cooldown = 0
    last_response_time = 0
    response_buffer = []
    response_timeout = 2.0  # Wait 2 seconds after last change before considering response complete
    last_full_output = ""
    
    while True:
        try:
            # Always check for permission prompts, not just when there's a command
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                capture_output=True,
                text=True
            )
            
            full_output = result.stdout
            output_lower = full_output.lower()
            
            # Create a hash of the current output to detect changes
            current_hash = hash(full_output[-1000:])  # Last 1000 chars
            
            # Check if output has changed and cooldown has passed
            if current_hash != last_output_hash and time.time() > permission_cooldown:
                last_output_hash = current_hash
                
                # Check for permission prompts - expanded patterns
                permission_patterns = [
                    # Claude specific patterns
                    r'❯\s*1\.\s*yes',
                    r'do you want to proceed\?',
                    r'bash command.*\n.*yes.*\n.*no',
                    # General patterns
                    r'\b(approve|permission|confirm|continue)\b.*\?',
                    r'\b(yes|no|y/n)\b.*\?',
                    r'press\s+(1|enter|y)',
                    r'\[1\].*yes',
                    r'1\).*yes',
                    r'1\..*yes',
                    # Action patterns
                    r'(execute|run|perform).*\?',
                    r'(allow|grant|authorize).*\?'
                ]
                
                # Check both original and lowercase for different patterns
                prompt_detected = False
                
                # Check for ❯ symbol (needs original case)
                if '❯' in full_output:
                    # Look for the context around ❯
                    lines = full_output.split('\n')
                    for i, line in enumerate(lines):
                        if '❯' in line:
                            # Check surrounding lines for yes/no pattern
                            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                            if any(x in context.lower() for x in ['yes', '1.', 'proceed', 'approve']):
                                prompt_detected = True
                                print(f"[AUTO-APPROVE] Detected ❯ prompt in context: {context[:100]}")
                                break
                
                # Check other patterns
                if not prompt_detected:
                    for pattern in permission_patterns:
                        if re.search(pattern, output_lower, re.IGNORECASE | re.MULTILINE):
                            prompt_detected = True
                            print(f"[AUTO-APPROVE] Detected pattern: {pattern}")
                            break
                
                # Quick keyword check as fallback
                if not prompt_detected:
                    quick_keywords = [
                        'do you want to proceed',
                        'bash command',
                        'press 1',
                        'approve?',
                        'continue?',
                        'y/n',
                        'yes/no',
                        'confirm?'
                    ]
                    if any(keyword in output_lower for keyword in quick_keywords):
                        prompt_detected = True
                        print("[AUTO-APPROVE] Detected via keyword match")
                
                if prompt_detected:
                    print("[AUTO-APPROVE] Permission prompt detected! Sending approval...")
                    
                    # Always try sending 1 first for Claude prompts
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                    print("[AUTO-APPROVE] Sent: 1 + Enter")
                    
                    # Set cooldown to avoid duplicate approvals
                    permission_cooldown = time.time() + 3
                    continue
                
            # Continue with response capture if we have a command
            if not last_command:
                time.sleep(0.2)  # Check frequently for prompts
                continue
                
            # Start monitoring immediately after command, don't wait
            # Track output changes to detect when Claude is done responding
            if full_output != last_full_output:
                last_full_output = full_output
                last_response_time = time.time()
                
            # Capture entire pane to ensure we get the full response
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout
            
            # Update stats
            current_stats = extract_stats_from_output(output)
            
            # Check if Claude is thinking or using tools
            thinking_indicators = ['Simmering', 'Deciphering', 'tokens', 'esc to interrupt', 
                                   'Running bash command', 'Editing file', 'Reading file',
                                   'Writing file', 'Searching', 'Using tool']
            if any(indicator in output for indicator in thinking_indicators):
                is_claude_thinking = True
            else:
                is_claude_thinking = False
            
            # Always try to capture responses, even if command not visible in current pane
            if last_command and time.time() - last_command_time > 0.5:
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
                            
                            # Start capturing immediately after command for any text
                            if not capture_started:
                                stripped_line = line.strip()
                                # Start capture on ANY text that's not a UI element or tool update
                                if (stripped_line and 
                                    not any(x in line for x in ['>', '│', '╭', '╰', '⏵', '⎿', 'tokens', 'esc to interrupt', 'Simmering', 'Deciphering']) and
                                    not line.strip().startswith('● Update(') and
                                    not line.strip().startswith('● Call(') and
                                    not line.strip().startswith('● Read(') and
                                    not line.strip().startswith('● Edit(') and
                                    not line.strip().startswith('● Write(') and
                                    not line.strip().startswith('● Bash(') and
                                    not line.strip().startswith('● MultiEdit(') and
                                    not line.strip().startswith('● TodoWrite(')):
                                    capture_started = True
                                    response_lines.append(stripped_line)
                            
                            # Stop at next prompt or system message (but not tool results)
                            if ('Human:' in line or 'The user sent' in line or line.startswith('$') or 
                                ('╭───' in line and 'Result' not in line)):
                                # If we were capturing commentary, we're done
                                if capture_started:
                                    break
                            
                            if capture_started or (line.strip() and not any(x in line for x in ['>', '│', '╭', '╰', '⏵', '⎿'])):
                                # Clean the line
                                cleaned_line = line.strip()
                                
                                # Skip UI elements and system messages but keep commentary
                                # Skip lines with green dot tool updates
                                skip_tool_update = any(cleaned_line.startswith(f'● {tool}(') for tool in 
                                    ['Update', 'Call', 'Read', 'Edit', 'Write', 'Bash', 'MultiEdit', 'Grep', 'Glob', 'LS'])
                                
                                if (cleaned_line and 
                                    not skip_tool_update and
                                    not cleaned_line.startswith('>') and
                                    not cleaned_line.startswith('╭') and
                                    not cleaned_line.startswith('│') and
                                    not cleaned_line.startswith('╰') and
                                    not cleaned_line.startswith('⏵') and
                                    not cleaned_line.startswith('⎿') and
                                    not cleaned_line.startswith('✽') and
                                    not cleaned_line.startswith('✢') and
                                    not cleaned_line.startswith('✻') and
                                    not cleaned_line.startswith('✶') and
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
                                    
                                    # Check if this is a grey dot commentary line
                                    is_commentary = cleaned_line.startswith('●') and not any(cleaned_line.startswith(f'● {tool}(') for tool in 
                                        ['Update', 'Call', 'Read', 'Edit', 'Write', 'Bash', 'MultiEdit', 'Grep', 'Glob', 'LS', 'TodoWrite'])
                                    
                                    # Skip commentary lines entirely - we don't want to speak them
                                    if is_commentary:
                                        continue
                                    
                                    # If not commentary and we haven't started capturing, skip
                                    if not capture_started:
                                        continue
                                    
                                    # Remove bullet points but keep the content
                                    cleaned_line = re.sub(r'^[•●]\s*', '', cleaned_line)
                                    
                                    if cleaned_line:
                                        response_lines.append(cleaned_line)
                    
                    if response_lines:
                        response = ' '.join(response_lines).strip()
                        response_hash = hash(response)
                        
                        # Update response buffer and timing
                        current_time = time.time()
                        if response_hash not in processed_responses and len(response) > 10:
                            # Check if this is a longer version of an existing response
                            is_duplicate = False
                            for existing in response_buffer:
                                # If new response contains the old one at the start, replace it
                                if response.startswith(existing['response']) and len(response) > len(existing['response']):
                                    response_buffer.remove(existing)
                                    print(f"[REPLACED] Shorter response with longer one")
                                    break
                                # If old response contains the new one, skip this
                                elif existing['response'].startswith(response):
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                # Store in buffer with timestamp
                                response_buffer.append({
                                    'response': response,
                                    'hash': response_hash,
                                    'time': current_time
                                })
                                last_response_time = current_time
                                print(f"[BUFFERED] Response ({len(response)} chars): {response[:100]}...")
                
                # Alternative: Look for response at the end of output if command not found
                else:
                    # Get the last 50 lines for analysis
                    lines = output.split('\n')
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    response_lines = []
                    
                    for line in recent_lines:
                        cleaned_line = line.strip()
                        # Capture lines that look like Claude's response
                        if (cleaned_line and 
                            not cleaned_line.startswith('>') and
                            not cleaned_line.startswith('╭') and
                            not cleaned_line.startswith('│') and
                            not cleaned_line.startswith('╰') and
                            not any(x in cleaned_line for x in ['tokens', 'Simmering', 'Deciphering', '🤖']) and
                            not any(x in cleaned_line.lower() for x in ['permission', 'approve', 'y/n'])):
                            response_lines.append(cleaned_line)
                    
                    if response_lines:
                        # Take the last meaningful chunk as response
                        response = ' '.join(response_lines[-10:]).strip()
                        if len(response) > 20:
                            response_hash = hash(response)
                            current_time = time.time()
                            if response_hash not in processed_responses:
                                response_buffer.append({
                                    'response': response,
                                    'hash': response_hash,
                                    'time': current_time
                                })
                                last_response_time = current_time
                                print(f"[BUFFERED-ALT] Response ({len(response)} chars): {response[:100]}...")
            
            # Check if we should send the final response
            current_time = time.time()
            
            # Check for tool usage indicators in the output
            has_tool_indicators = any(indicator in output for indicator in [
                'Calling tool:', 'Tool result:', 'Using tool:', 
                'function_calls', 'antml:invoke', 'antml:function_calls',
                'calling the', 'called the', 'Result of calling',
                'I\'ve fixed', 'I\'ve added', 'Let me', 'I\'ll'
            ])
            
            # Increase timeout if tools are being used (they take longer)
            effective_timeout = response_timeout * 5 if has_tool_indicators else response_timeout
            
            # Send response if we have one and enough time has passed
            if response_buffer and (current_time - last_response_time) > effective_timeout and not is_claude_thinking:
                # Find the longest response in the buffer (most complete)
                longest_response = max(response_buffer, key=lambda x: len(x['response']))
                
                # Check if we haven't already sent this exact response
                if longest_response['hash'] not in processed_responses:
                    # Mark all partial versions as processed too
                    for buf_resp in response_buffer:
                        processed_responses.add(buf_resp['hash'])
                    
                    response_queue.put(longest_response['response'])
                    print(f"[CAPTURED] Final response ({len(longest_response['response'])} chars): {longest_response['response'][:150]}...")
                    
                # Clear command and buffer after processing
                globals()['last_command'] = ""
                response_buffer.clear()
            
            time.sleep(1)
            
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
    <title>Claude Voice Assistant</title>
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
        </div>
        
        <div class="content-container">
            <h1>🎙️ Claude Voice Assistant</h1>
            
            <div class="controls">
                <button onclick="toggleAutoSpeak()">Auto-Speak: <span id="autoSpeakStatus">ON</span></button>
                <button onclick="clearConversation()">Clear</button>
                <button onclick="stopSpeaking()">Stop Speaking</button>
            </div>
            
            <div class="voice-controls">
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
        let lastSpokenText = "";
        let selectedVoice = null;
        let continuousMode = true;
        let wasListeningBeforeSpeech = false;
        
        // Initialize speech synthesis
        const synth = window.speechSynthesis;
        let voices = [];
        
        // Load voices
        function loadVoices() {
            voices = synth.getVoices();
            const voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '';
            
            // Quality ranking for voice selection - expanded list
            const qualityKeywords = [
                'Natural', 'Premium', 'Enhanced', 'Neural', 'HD',
                'Samantha', 'Alex', 'Daniel', 'Karen', 'Moira',
                'Tessa', 'Fiona', 'Victoria', 'Susan', 'Allison',
                'Ava', 'Nicky', 'Vicki', 'Siri', 'Tom', 'Serena',
                'Google UK English Female', 'Google UK English Male',
                'Google US English', 'Microsoft', 'Amazon',
                'Zira', 'David', 'Mark', 'Catherine', 'James',
                'Linda', 'Richard', 'George', 'Hazel', 'Sean'
            ];
            
            // Filter and rank English voices
            let englishVoices = voices.filter(v => v.lang.startsWith('en'));
            
            // Sort by quality
            englishVoices.sort((a, b) => {
                // Check quality keywords
                let aScore = 0, bScore = 0;
                qualityKeywords.forEach((keyword, index) => {
                    if (a.name.includes(keyword)) aScore += (100 - index);
                    if (b.name.includes(keyword)) bScore += (100 - index);
                });
                
                // Penalize compact/low quality voices
                if (a.name.includes('Compact') || a.name.includes('com.apple')) aScore -= 50;
                if (b.name.includes('Compact') || b.name.includes('com.apple')) bScore -= 50;
                
                return bScore - aScore;
            });
            
            // Group voices by type
            const femaleVoices = [];
            const maleVoices = [];
            const neutralVoices = [];
            
            englishVoices.forEach(voice => {
                const name = voice.name.toLowerCase();
                if (name.includes('female') || ['samantha', 'karen', 'moira', 'tessa', 'fiona', 'victoria', 'susan', 'allison', 'ava', 'nicky', 'vicki', 'serena', 'catherine', 'linda', 'hazel', 'zira', 'emily', 'alice', 'emma', 'sara', 'kate', 'anna'].some(n => name.includes(n))) {
                    femaleVoices.push(voice);
                } else if (name.includes('male') || ['alex', 'daniel', 'oliver', 'thomas', 'david', 'mark', 'james', 'richard', 'george', 'sean', 'tom', 'john', 'paul', 'peter', 'mike'].some(n => name.includes(n))) {
                    maleVoices.push(voice);
                } else {
                    neutralVoices.push(voice);
                }
            });
            
            // Add options grouped by type
            if (femaleVoices.length > 0) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = 'Female Voices (Google TTS)';
                femaleVoices.slice(0, 15).forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = voice.name.replace(/^(Microsoft|Google|com\.apple\.)/, '') + ' (High Quality)';
                    optgroup.appendChild(option);
                });
                voiceSelect.appendChild(optgroup);
            }
            
            if (maleVoices.length > 0) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = 'Male Voices (Browser TTS)';
                maleVoices.slice(0, 10).forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = voice.name.replace(/^(Microsoft|Google|com\.apple\.)/, '') + ' (Browser)';
                    optgroup.appendChild(option);
                });
                voiceSelect.appendChild(optgroup);
            }
            
            if (neutralVoices.length > 0) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = 'Other Voices';
                neutralVoices.slice(0, 10).forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = voice.name.replace(/^(Microsoft|Google|com\.apple\.)/, '');
                    optgroup.appendChild(option);
                });
                voiceSelect.appendChild(optgroup);
            }
            
            // Select the best available voice
            selectedVoice = englishVoices[0] || voices[0];
            if (selectedVoice) {
                voiceSelect.value = voices.indexOf(selectedVoice);
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
            selectedVoice = voices[voiceSelect.value];
            
            // Test the voice with a sample
            if (selectedVoice && !isSpeaking) {
                // Use the same speak function to test, ensuring consistent behavior
                speak('Testing voice selection', true);
            }
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
            if (!text || (isSpeaking && !isTest) || (!isTest && text === lastSpokenText)) return;
            
            // Stop recognition while speaking (but not for tests)
            if (!isTest && recognition && isListening) {
                recognition.stop();
                wasListeningBeforeSpeech = true;
            }
            
            // Cancel any ongoing speech
            synth.cancel();
            
            if (!isTest) {
                lastSpokenText = text;
            }
            isSpeaking = true;
            document.getElementById('speakingIndicator').style.display = 'block';
            document.getElementById('micButton').classList.add('speaking');
            if (!isTest) {
                updateStatus('🔊 Claude is speaking...');
            }
            
            // Try to use high-quality gTTS first
            try {
                // Determine accent based on voice selection
                let accent = 'com'; // default US
                let useGTTS = true;
                
                if (selectedVoice && selectedVoice.name) {
                    const voiceName = selectedVoice.name.toLowerCase();
                    if (voiceName.includes('uk') || voiceName.includes('british')) {
                        accent = 'co.uk';
                    } else if (voiceName.includes('australian')) {
                        accent = 'com.au';
                    } else if (voiceName.includes('male')) {
                        // gTTS doesn't support male voices well, fall back to browser TTS
                        useGTTS = false;
                    }
                }
                
                if (!useGTTS) {
                    // Use browser TTS for male voices
                    useBrowserTTS(text, isTest);
                    return;
                }
                
                const response = await fetch('/get-tts-audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: text,
                        lang: 'en',
                        accent: accent
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Stop any existing audio
                    if (currentAudio) {
                        currentAudio.pause();
                        currentAudio = null;
                    }
                    
                    // Play the high-quality audio
                    const audio = new Audio('data:audio/mp3;base64,' + data.audio);
                    currentAudio = audio; // Track this audio
                    audio.playbackRate = speechRate;
                    
                    audio.onended = () => {
                        currentAudio = null;
                        onSpeechEnd(isTest);
                    };
                    
                    audio.onerror = () => {
                        currentAudio = null;
                        // Fallback to browser TTS
                        useBrowserTTS(text, isTest);
                    };
                    
                    audio.play();
                } else {
                    // Fallback to browser TTS
                    useBrowserTTS(text, isTest);
                }
            } catch (err) {
                // Fallback to browser TTS
                console.error('gTTS error:', err);
                useBrowserTTS(text, isTest);
            }
        }
        
        function useBrowserTTS(text, isTest = false) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = speechRate;
            utterance.pitch = speechPitch;
            utterance.volume = 1;
            
            if (selectedVoice) {
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
                    // Additional check - don't speak if this is a substring of what we already spoke
                    const shouldSpeak = !lastSpokenText || 
                                       (!lastSpokenText.includes(data.response) && 
                                        !data.response.includes(lastSpokenText));
                    
                    if (shouldSpeak) {
                        addMessage(data.response, 'claude');
                        window.claudeThinking = false;
                        
                        // Stop recognition during response
                        if (recognition && isListening) {
                            recognition.stop();
                        }
                        
                        if (autoSpeak && !isSpeaking) {
                            speak(data.response);
                            // Listening will resume via onSpeechEnd callback
                        } else if (!autoSpeak && continuousMode) {
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
            // Check for responses every 2 seconds
            setInterval(checkForResponse, 500);  // Check more frequently for faster response
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

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️  CLAUDE VOICE - CONTINUOUS & REALISTIC")
    print("="*50)
    print("✨ Features:")
    print("  - Continuous listening mode")
    print("  - Multiple voice options")
    print("  - Adjustable pitch & speed")
    print("  - Auto-sends after silence")
    print("")
    print("📱 Access at: https://192.168.40.232:8103")
    print("="*50 + "\n")
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=8103, debug=False, ssl_context=context)