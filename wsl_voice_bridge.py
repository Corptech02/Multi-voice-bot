#!/usr/bin/env python3
"""
WSL Voice Bridge - Optimized for WSL terminal use
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
from datetime import datetime
import subprocess

app = Flask(__name__)

# Store command queue and message history
command_queue = []
message_history = []

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude WSL Voice Bridge</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #0f0;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #0f0;
            text-shadow: 0 0 30px #0f0;
            font-size: 32px;
            margin-bottom: 30px;
        }
        .message-log {
            background: #000;
            border: 1px solid #0f0;
            border-radius: 5px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 20px;
            font-family: 'Courier New', monospace;
        }
        .message {
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
            border-left: 3px solid #0f0;
            margin-right: 20%;
        }
        .bot-message {
            background: rgba(0, 100, 255, 0.1);
            border-left: 3px solid #0064ff;
            margin-left: 20%;
        }
        .message-label {
            font-weight: bold;
            color: #0f0;
            margin-bottom: 5px;
        }
        .bot-message .message-label {
            color: #0064ff;
        }
        .message-text {
            color: #fff;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .message-time {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        /* Custom scrollbar */
        .message-log::-webkit-scrollbar {
            width: 10px;
        }
        .message-log::-webkit-scrollbar-track {
            background: #001100;
            border-radius: 5px;
        }
        .message-log::-webkit-scrollbar-thumb {
            background: #0f0;
            border-radius: 5px;
        }
        .message-log::-webkit-scrollbar-thumb:hover {
            background: #00ff00;
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
        .section {
            background: #0a0a0a;
            border: 2px solid #0f0;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }
        .mic-container {
            text-align: center;
            padding: 40px 0;
        }
        .mic-button {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, #003300, #000000);
            border: 4px solid #0f0;
            color: #0f0;
            font-size: 80px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 
                0 0 50px rgba(0, 255, 0, 0.5),
                inset 0 0 50px rgba(0, 255, 0, 0.1);
            position: relative;
            overflow: hidden;
        }
        .mic-button::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(transparent, rgba(0, 255, 0, 0.1), transparent);
            animation: rotate 3s linear infinite;
        }
        @keyframes rotate {
            100% { transform: rotate(360deg); }
        }
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 
                0 0 80px rgba(0, 255, 0, 0.8),
                inset 0 0 50px rgba(0, 255, 0, 0.2);
        }
        .mic-button.listening {
            background: radial-gradient(circle at 30% 30%, #330000, #000000);
            border-color: #f00;
            color: #f00;
            animation: pulse-red 1s infinite;
            box-shadow: 
                0 0 50px rgba(255, 0, 0, 0.5),
                inset 0 0 50px rgba(255, 0, 0, 0.1);
        }
        @keyframes pulse-red {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status {
            text-align: center;
            font-size: 18px;
            margin: 20px 0;
            color: #0f0;
            height: 30px;
        }
        .command-display {
            background: #000;
            border: 1px solid #0f0;
            padding: 20px;
            margin: 20px 0;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            position: relative;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }
        .command-display:hover {
            background: #001100;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        }
        .command-display.has-command {
            animation: glow 2s ease-in-out infinite;
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 0, 0.5); }
            50% { box-shadow: 0 0 40px rgba(0, 255, 0, 0.8), inset 0 0 20px rgba(0, 255, 0, 0.2); }
        }
        .copy-indicator {
            position: absolute;
            top: 5px;
            right: 10px;
            font-size: 12px;
            color: #888;
        }
        .terminal-output {
            background: #000;
            border: 1px solid #0f0;
            padding: 15px;
            height: 300px;
            overflow-y: auto;
            font-size: 14px;
            white-space: pre-wrap;
        }
        .terminal-output::-webkit-scrollbar {
            width: 10px;
        }
        .terminal-output::-webkit-scrollbar-track {
            background: #111;
        }
        .terminal-output::-webkit-scrollbar-thumb {
            background: #0f0;
            border-radius: 5px;
        }
        .log-entry {
            margin: 2px 0;
            opacity: 0;
            animation: fadeIn 0.3s forwards;
        }
        @keyframes fadeIn {
            to { opacity: 1; }
        }
        .user-cmd { color: #0f0; }
        .system-msg { color: #ff0; }
        .error-msg { color: #f00; }
        .success-msg { color: #0ff; }
        
        .instructions {
            background: #001100;
            border: 1px solid #0f0;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .shortcut {
            display: inline-block;
            background: #000;
            border: 1px solid #0f0;
            padding: 5px 10px;
            margin: 2px;
            border-radius: 3px;
            font-weight: bold;
        }
        .copied-flash {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #0f0;
            color: #000;
            padding: 20px 40px;
            font-size: 24px;
            font-weight: bold;
            border-radius: 10px;
            z-index: 1000;
            animation: flash-fade 1s forwards;
        }
        @keyframes flash-fade {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
            50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 CLAUDE WSL VOICE BRIDGE</h1>
        
        <div class="main-grid">
            <div class="section">
                <h2 style="text-align: center; color: #0f0; margin-top: 0;">Voice Input</h2>
                
                <div class="mic-container">
                    <button id="micButton" class="mic-button">
                        <span style="position: relative; z-index: 1;">🎤</span>
                    </button>
                </div>
                
                <div class="status" id="status">Ready for voice command</div>
                
                <div class="command-display" id="commandDisplay" onclick="copyCommand()">
                    <span class="copy-indicator">CLICK TO COPY</span>
                    <span id="commandText">Speak your command...</span>
                </div>
                
                <div class="instructions">
                    <strong>Quick Tips:</strong><br>
                    • <span class="shortcut">Ctrl+Space</span> Quick voice input<br>
                    • <span class="shortcut">Esc</span> Stop listening<br>
                    • Commands auto-copy to clipboard<br>
                    • Just paste in your terminal!
                </div>
            </div>
            
            <div class="section">
                <h2 style="text-align: center; color: #0f0; margin-top: 0;">Activity Log</h2>
                
                <div class="terminal-output" id="log">
                    <div class="log-entry system-msg">[SYSTEM] WSL Voice Bridge initialized</div>
                    <div class="log-entry system-msg">[SYSTEM] Ready for voice commands</div>
                    <div class="log-entry success-msg">[TIP] Your commands will auto-copy!</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 style="text-align: center; color: #0f0; margin-top: 0;">Conversation Log</h2>
            <div class="message-log" id="messageLog">
                <div class="message bot-message">
                    <div class="message-label">🤖 Claude Assistant</div>
                    <div class="message-text">Hello! I'm ready to help. Speak your command and I'll assist you.</div>
                    <div class="message-time">${new Date().toLocaleTimeString()}</div>
                </div>
            </div>
        </div>
        
        <div class="section" style="text-align: center;">
            <h3 style="color: #0f0;">How it works:</h3>
            <p>🎤 Speak → 📝 Auto-transcribe → 📋 Auto-copy → 📍 Paste in terminal</p>
        </div>
    </div>
    
    <script>
        let recognition;
        let isListening = false;
        
        // Initialize speech recognition
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('micButton').classList.add('listening');
                document.getElementById('status').textContent = '🔴 Listening...';
                addLog('[MIC] Listening for voice input...', 'system-msg');
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('status').textContent = 'Ready for voice command';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('commandText').textContent = text;
                    document.getElementById('status').innerHTML = '💭 <em>Processing...</em>';
                } else {
                    processCommand(text);
                    addMessage(text, 'user');
                }
            };
            
            recognition.onerror = (event) => {
                addLog('[ERROR] ' + event.error, 'error-msg');
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('status').textContent = 'Error: ' + event.error;
            };
        }
        
        // Process command
        async function processCommand(text) {
            document.getElementById('commandText').textContent = text;
            document.getElementById('commandDisplay').classList.add('has-command');
            addLog('> ' + text, 'user-cmd');
            
            // Auto-copy to clipboard
            copyToClipboard(text);
            
            // Send to server and get response
            try {
                const response = await fetch('/voice-command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
                
                const data = await response.json();
                if (data.response) {
                    addMessage(data.response, 'bot');
                    
                    // Speak response using browser TTS
                    if ('speechSynthesis' in window) {
                        const utterance = new SpeechSynthesisUtterance(data.response);
                        utterance.rate = 1.0;
                        utterance.pitch = 1.0;
                        window.speechSynthesis.speak(utterance);
                    }
                }
            } catch (err) {
                console.error('Failed to send to server:', err);
            }
        }
        
        // Add message to log
        function addMessage(text, sender) {
            const log = document.getElementById('messageLog');
            const message = document.createElement('div');
            message.className = 'message ' + (sender === 'user' ? 'user-message' : 'bot-message');
            
            const label = document.createElement('div');
            label.className = 'message-label';
            label.textContent = sender === 'user' ? '🎤 You' : '🤖 Claude Assistant';
            
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.textContent = text;
            
            const time = document.createElement('div');
            time.className = 'message-time';
            time.textContent = new Date().toLocaleTimeString();
            
            message.appendChild(label);
            message.appendChild(textDiv);
            message.appendChild(time);
            
            log.appendChild(message);
            log.scrollTop = log.scrollHeight;
        }
        
        // Copy command
        function copyCommand() {
            const text = document.getElementById('commandText').textContent;
            if (text && text !== 'Speak your command...') {
                copyToClipboard(text);
            }
        }
        
        // Copy to clipboard
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Show copied indicator
                const flash = document.createElement('div');
                flash.className = 'copied-flash';
                flash.textContent = '📋 COPIED!';
                document.body.appendChild(flash);
                setTimeout(() => flash.remove(), 1000);
                
                document.getElementById('status').textContent = '✅ Copied to clipboard - paste in terminal!';
                addLog('[COPIED] Ready to paste in terminal', 'success-msg');
            }).catch(() => {
                // Fallback method
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                
                document.getElementById('status').textContent = '✅ Copied - paste in terminal!';
            });
        }
        
        // Add to log
        function addLog(text, className) {
            const log = document.getElementById('log');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + (className || '');
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
            
            // Keep only last 50 entries
            while (log.children.length > 50) {
                log.removeChild(log.firstChild);
            }
        }
        
        // Mic button
        document.getElementById('micButton').addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                document.getElementById('micButton').click();
            } else if (e.code === 'Escape' && isListening) {
                recognition.stop();
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/voice-command', methods=['POST'])
def voice_command():
    data = request.json
    command = data.get('command', '')
    
    # Log to terminal
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*60}")
    print(f"🎤 VOICE COMMAND RECEIVED: {command}")
    print(f"   Time: {timestamp}")
    print(f"   Ready to paste in terminal!")
    print(f"{'='*60}\n")
    
    # Save to history
    command_queue.append({
        'command': command,
        'timestamp': timestamp
    })
    message_history.append({
        'role': 'user',
        'content': command,
        'timestamp': timestamp
    })
    
    # Generate response
    response = generate_response(command)
    
    message_history.append({
        'role': 'assistant',
        'content': response,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Keep only last 100
    if len(command_queue) > 100:
        command_queue.pop(0)
    if len(message_history) > 100:
        message_history.pop(0)
    
    # Try to send to tmux if available
    try:
        subprocess.run(['tmux', 'send-keys', '-t', 'claude', command, 'C-m'], check=False)
    except:
        pass
    
    return jsonify({'success': True, 'response': response})

def generate_response(command):
    """Generate appropriate response based on command"""
    command_lower = command.lower()
    
    # Basic responses for common queries
    if any(greeting in command_lower for greeting in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm Claude, your AI assistant. How can I help you today?"
    
    elif any(q in command_lower for q in ['how are you', 'how do you do', "how's it going"]):
        return "I'm doing well, thank you for asking! I'm here and ready to help you with any questions or tasks you might have."
    
    elif 'time' in command_lower and ('what' in command_lower or 'tell' in command_lower):
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."
    
    elif 'date' in command_lower and ('what' in command_lower or 'tell' in command_lower):
        current_date = datetime.now().strftime("%B %d, %Y")
        return f"Today's date is {current_date}."
    
    elif any(q in command_lower for q in ['help', 'what can you do', 'capabilities']):
        return ("I can help you with various tasks including:\n"
                "• Answering questions\n"
                "• Running terminal commands\n" 
                "• Writing and editing code\n"
                "• Explaining technical concepts\n"
                "• Problem-solving and debugging\n"
                "Just speak your request and I'll do my best to assist!")
    
    elif 'thank' in command_lower:
        return "You're welcome! I'm happy to help. Is there anything else you'd like to know?"
    
    elif any(q in command_lower for q in ['goodbye', 'bye', 'see you', 'quit', 'exit']):
        return "Goodbye! Feel free to come back anytime you need assistance. Have a great day!"
    
    else:
        # For other commands, acknowledge and indicate processing
        return f"I understood: '{command}'. I've sent it to the terminal. For other requests, I'm here to help - just ask!"

@app.route('/get-commands')
def get_commands():
    return jsonify({'commands': command_queue[-10:]})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎤 WSL VOICE BRIDGE FOR CLAUDE")
    print("="*60)
    print("\n✨ OPTIMIZED FOR WSL TERMINAL USE")
    print("\n📋 Features:")
    print("   • Voice recognition")
    print("   • Auto-copy to clipboard")
    print("   • Just paste in terminal!")
    print("\n🌐 Access at: https://192.168.40.232:8449")
    print("\n⌨️  Shortcuts:")
    print("   • Ctrl+Space = Quick voice")
    print("   • Esc = Stop listening")
    print("="*60 + "\n")
    
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8449, ssl_context=context, debug=False)
    else:
        app.run(host='0.0.0.0', port=8103, debug=False)