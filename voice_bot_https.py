#!/usr/bin/env python3
"""
Claude Voice Bot - HTTPS version for public access
"""
from flask import Flask, render_template_string, request, jsonify
import ssl
import os
from datetime import datetime

app = Flask(__name__)

# Store conversation history
conversation_history = []
last_response = ""

# Professional website template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude AI Voice Assistant</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .stars {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
        }
        
        .star {
            position: absolute;
            width: 2px;
            height: 2px;
            background: white;
            border-radius: 50%;
            animation: twinkle 3s infinite;
        }
        
        @keyframes twinkle {
            0%, 100% { opacity: 0; }
            50% { opacity: 1; }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }
        
        header {
            text-align: center;
            padding: 40px 0;
        }
        
        h1 {
            font-size: 3em;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00ff88, #00bbff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px rgba(0, 255, 136, 0.5);
        }
        
        .subtitle {
            font-size: 1.2em;
            color: #a0a0a0;
            margin-bottom: 40px;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 40px;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .voice-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .mic-container {
            display: flex;
            justify-content: center;
            margin: 40px 0;
        }
        
        .mic-button {
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(145deg, #00ff88, #00bbff);
            color: white;
            font-size: 80px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 40px rgba(0, 255, 136, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .mic-button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.3s, height 0.3s;
        }
        
        .mic-button:hover::before {
            width: 100%;
            height: 100%;
        }
        
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 15px 50px rgba(0, 255, 136, 0.4);
        }
        
        .mic-button.listening {
            animation: pulse-mic 1.5s infinite;
            background: linear-gradient(145deg, #ff3366, #ff6b6b);
        }
        
        @keyframes pulse-mic {
            0% { transform: scale(1); box-shadow: 0 10px 40px rgba(255, 51, 102, 0.3); }
            50% { transform: scale(1.1); box-shadow: 0 15px 60px rgba(255, 51, 102, 0.5); }
            100% { transform: scale(1); box-shadow: 0 10px 40px rgba(255, 51, 102, 0.3); }
        }
        
        .status {
            text-align: center;
            font-size: 1.2em;
            margin: 20px 0;
            min-height: 40px;
            color: #00ff88;
        }
        
        .chat-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chat-container {
            height: 500px;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .chat-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .chat-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }
        
        .chat-container::-webkit-scrollbar-thumb {
            background: rgba(0, 255, 136, 0.5);
            border-radius: 4px;
        }
        
        .message {
            margin: 20px 0;
            padding: 20px;
            border-radius: 15px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { 
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .user-message {
            background: linear-gradient(145deg, #2a2a4e, #1a1a3e);
            border: 1px solid rgba(0, 255, 136, 0.3);
            margin-left: 20%;
        }
        
        .claude-message {
            background: linear-gradient(145deg, #1a1a3e, #0f0f23);
            border: 1px solid rgba(0, 187, 255, 0.3);
            margin-right: 20%;
        }
        
        .message-header {
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .message-icon {
            font-size: 1.5em;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 40px;
        }
        
        .feature {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .feature:hover {
            transform: translateY(-5px);
            border-color: rgba(0, 255, 136, 0.5);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
        }
        
        .feature-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        .feature h3 {
            font-size: 1.3em;
            margin-bottom: 10px;
            color: #00ff88;
        }
        
        .feature p {
            color: #a0a0a0;
            line-height: 1.6;
        }
        
        .error-message {
            background: rgba(255, 51, 102, 0.1);
            border: 1px solid rgba(255, 51, 102, 0.5);
            color: #ff6b6b;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            display: none;
        }
        
        footer {
            text-align: center;
            padding: 40px 0;
            color: #666;
        }
        
        .pulse-ring {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: 3px solid rgba(0, 255, 136, 0.5);
            transform: translate(-50%, -50%);
            animation: pulse-ring 2s infinite;
            pointer-events: none;
        }
        
        @keyframes pulse-ring {
            0% {
                transform: translate(-50%, -50%) scale(1);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.5);
                opacity: 0;
            }
        }
    </style>
</head>
<body>
    <div class="stars"></div>
    
    <div class="container">
        <header>
            <h1>Claude AI Voice Assistant</h1>
            <p class="subtitle">Speak naturally, get intelligent responses</p>
        </header>
        
        <div class="main-content">
            <div class="voice-section">
                <h2 style="text-align: center; margin-bottom: 30px;">🎙️ Voice Control</h2>
                
                <div class="mic-container">
                    <button id="micButton" class="mic-button">
                        <span id="micIcon">🎤</span>
                    </button>
                    <div class="pulse-ring" id="pulseRing" style="display: none;"></div>
                </div>
                
                <div class="status" id="status">Click the microphone to start</div>
                
                <div class="error-message" id="error"></div>
                
                <div style="margin-top: 40px; text-align: center;">
                    <p style="color: #666; font-size: 0.9em;">
                        Tip: Speak clearly and naturally. Claude understands context and can handle complex requests.
                    </p>
                </div>
            </div>
            
            <div class="chat-section">
                <h2 style="text-align: center; margin-bottom: 30px;">💬 Conversation</h2>
                <div class="chat-container" id="chatContainer">
                    <div class="message claude-message">
                        <div class="message-header">
                            <span class="message-icon">🤖</span>
                            <span>Claude</span>
                        </div>
                        <p>Hello! I'm Claude, your AI assistant. Click the microphone and ask me anything!</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">🧠</div>
                <h3>Intelligent Understanding</h3>
                <p>Claude comprehends context and nuance in your speech</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🔊</div>
                <h3>Natural Voice Response</h3>
                <p>Hear Claude's responses with text-to-speech</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🔒</div>
                <h3>Secure & Private</h3>
                <p>Your conversations are processed securely</p>
            </div>
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <h3>Real-time Processing</h3>
                <p>Get instant responses to your questions</p>
            </div>
        </div>
        
        <footer>
            <p>Powered by Claude AI • Voice Interface v1.0</p>
        </footer>
    </div>
    
    <script>
        // Create stars background
        function createStars() {
            const starsContainer = document.querySelector('.stars');
            for (let i = 0; i < 100; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.animationDelay = Math.random() * 3 + 's';
                starsContainer.appendChild(star);
            }
        }
        createStars();
        
        let recognition;
        let isListening = false;
        let synthesis = window.speechSynthesis;
        
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
                document.getElementById('micIcon').textContent = '🔴';
                document.getElementById('status').textContent = 'Listening...';
                document.getElementById('pulseRing').style.display = 'block';
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('micIcon').textContent = '🎤';
                document.getElementById('status').textContent = 'Click the microphone to start';
                document.getElementById('pulseRing').style.display = 'none';
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript;
                
                if (!event.results[last].isFinal) {
                    document.getElementById('status').textContent = '💭 ' + text;
                } else {
                    sendToClaude(text);
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                showError('Microphone error: ' + event.error);
                isListening = false;
                document.getElementById('micButton').classList.remove('listening');
                document.getElementById('micIcon').textContent = '🎤';
                document.getElementById('pulseRing').style.display = 'none';
            };
        }
        
        // Microphone button handler
        document.getElementById('micButton').addEventListener('click', () => {
            if (!recognition) {
                showError('Speech recognition not supported in your browser');
                return;
            }
            
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        // Send to Claude
        async function sendToClaude(text) {
            addMessage(text, 'user');
            document.getElementById('status').textContent = 'Processing...';
            
            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                
                const data = await response.json();
                
                if (data.response) {
                    addMessage(data.response, 'claude');
                    speakResponse(data.response);
                }
            } catch (err) {
                showError('Failed to connect to Claude');
            }
        }
        
        // Add message to chat
        function addMessage(text, sender) {
            const container = document.getElementById('chatContainer');
            const message = document.createElement('div');
            message.className = 'message ' + (sender === 'user' ? 'user-message' : 'claude-message');
            
            const header = document.createElement('div');
            header.className = 'message-header';
            header.innerHTML = `
                <span class="message-icon">${sender === 'user' ? '🗣️' : '🤖'}</span>
                <span>${sender === 'user' ? 'You' : 'Claude'}</span>
            `;
            
            const content = document.createElement('p');
            content.textContent = text;
            
            message.appendChild(header);
            message.appendChild(content);
            container.appendChild(message);
            
            container.scrollTop = container.scrollHeight;
        }
        
        // Text to speech
        function speakResponse(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                synthesis.speak(utterance);
            }
        }
        
        // Show error
        function showError(message) {
            const error = document.getElementById('error');
            error.textContent = message;
            error.style.display = 'block';
            setTimeout(() => {
                error.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process():
    global last_response
    data = request.json
    text = data.get('text', '')
    
    # Log the request
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] Voice input: {text}")
    
    # Process the command (integrate with Claude here)
    response = f"I heard you say: '{text}'. This is where Claude's response would appear."
    
    # Store in history
    conversation_history.append({
        'user': text,
        'claude': response,
        'timestamp': timestamp
    })
    
    return jsonify({'response': response})

if __name__ == '__main__':
    # Check if SSL certificates exist
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        print("\n" + "="*60)
        print("🎙️  CLAUDE VOICE ASSISTANT (HTTPS)")
        print("="*60)
        print("✅ Secure website ready!")
        print("")
        print("🌐 Access at:")
        print("   https://192.168.40.232:8443")
        print("")
        print("⚠️  Certificate warning:")
        print("   Click 'Advanced' > 'Proceed' to accept self-signed cert")
        print("")
        print("📱 Works on all devices with HTTPS!")
        print("="*60 + "\n")
        
        # Run with HTTPS
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain('cert.pem', 'key.pem')
        app.run(host='0.0.0.0', port=8443, ssl_context=context, debug=False)
    else:
        print("SSL certificates not found. Running HTTP version.")
        app.run(host='0.0.0.0', port=8097, debug=False)