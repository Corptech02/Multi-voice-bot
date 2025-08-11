#!/usr/bin/env python3
"""
Simple Voice Bot Test Script
Tests basic voice input/output functionality
"""
from flask import Flask, render_template_string, request, jsonify
import time
from datetime import datetime
from gtts import gTTS
import base64
import io

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Simple Voice Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #fff;
            padding: 20px;
            text-align: center;
        }
        
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: #2a2a2a;
            padding: 30px;
            border-radius: 10px;
        }
        
        h1 {
            color: #00ff00;
            margin-bottom: 30px;
        }
        
        .mic-button {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: #333;
            border: 3px solid #00ff00;
            color: #00ff00;
            font-size: 40px;
            cursor: pointer;
            margin: 20px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }
        
        .mic-button:hover {
            background: #444;
        }
        
        .mic-button.recording {
            background: #ff3333;
            border-color: #ff3333;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.1); opacity: 0.8; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        .status {
            margin: 20px 0;
            font-size: 18px;
            min-height: 30px;
        }
        
        .transcript {
            margin: 20px 0;
            padding: 15px;
            background: #1a1a1a;
            border-radius: 5px;
            min-height: 60px;
            font-style: italic;
        }
        
        .response {
            margin: 20px 0;
            padding: 15px;
            background: #1a1a1a;
            border-radius: 5px;
            min-height: 60px;
        }
        
        .error {
            color: #ff6666;
        }
        
        .success {
            color: #66ff66;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 Simple Voice Test</h1>
        
        <div class="status" id="status">Click microphone to start</div>
        
        <button class="mic-button" id="micButton" onclick="toggleRecording()">
            🎤
        </button>
        
        <div class="transcript" id="transcript">
            <strong>You said:</strong> <span id="transcriptText">-</span>
        </div>
        
        <div class="response" id="response">
            <strong>Response:</strong> <span id="responseText">-</span>
        </div>
    </div>

    <script>
        let isRecording = false;
        let recognition = null;
        let audioContext = null;
        let currentAudio = null;
        
        // Initialize speech recognition
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
                showStatus('Speech recognition not supported', 'error');
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                showStatus('Listening...', 'success');
            };
            
            recognition.onresult = (event) => {
                const last = event.results.length - 1;
                const transcript = event.results[last][0].transcript;
                document.getElementById('transcriptText').textContent = transcript;
                
                if (event.results[last].isFinal) {
                    sendCommand(transcript);
                }
            };
            
            recognition.onerror = (event) => {
                showStatus(`Error: ${event.error}`, 'error');
                stopRecording();
            };
            
            recognition.onend = () => {
                stopRecording();
            };
        }
        
        function toggleRecording() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            if (!recognition) {
                initSpeechRecognition();
            }
            
            if (!recognition) return;
            
            isRecording = true;
            document.getElementById('micButton').classList.add('recording');
            recognition.start();
        }
        
        function stopRecording() {
            isRecording = false;
            document.getElementById('micButton').classList.remove('recording');
            if (recognition) {
                recognition.stop();
            }
            showStatus('Click microphone to start', '');
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = type;
        }
        
        async function sendCommand(command) {
            showStatus('Processing...', '');
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ command: command })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('responseText').textContent = data.response;
                    
                    // Play TTS audio if available
                    if (data.audio) {
                        playAudio(data.audio);
                    }
                    
                    showStatus('Response received', 'success');
                } else {
                    showStatus('Error processing command', 'error');
                }
            } catch (error) {
                showStatus('Connection error', 'error');
                console.error(error);
            }
        }
        
        function playAudio(base64Audio) {
            // Stop any currently playing audio
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            // Create and play new audio
            const audio = new Audio('data:audio/mp3;base64,' + base64Audio);
            audio.volume = 0.8;
            currentAudio = audio;
            
            audio.play().catch(error => {
                console.error('Audio playback error:', error);
            });
        }
        
        // Initialize on page load
        window.onload = () => {
            initSpeechRecognition();
            
            // Request microphone permission on first interaction
            document.addEventListener('click', () => {
                if (!audioContext) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
            }, { once: true });
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process_command():
    """Process voice command and generate response"""
    try:
        data = request.json
        command = data.get('command', '')
        
        if not command:
            return jsonify({'success': False, 'error': 'No command provided'})
        
        # Log the command
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Received: {command}")
        
        # Generate a simple response
        response_text = generate_response(command)
        
        # Generate TTS audio
        tts = gTTS(text=response_text, lang='en', slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_base64 = base64.b64encode(audio_buffer.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'response': response_text,
            'audio': audio_base64
        })
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'success': False, 'error': str(e)})

def generate_response(command):
    """Generate a simple response based on the command"""
    command_lower = command.lower()
    
    # Simple response logic
    if 'hello' in command_lower or 'hi' in command_lower:
        return "Hello! I'm your voice assistant. How can I help you today?"
    elif 'time' in command_lower:
        current_time = datetime.now().strftime('%I:%M %p')
        return f"The current time is {current_time}"
    elif 'date' in command_lower:
        current_date = datetime.now().strftime('%B %d, %Y')
        return f"Today's date is {current_date}"
    elif 'how are you' in command_lower:
        return "I'm doing great! Thank you for asking. How can I assist you?"
    elif 'test' in command_lower:
        return "Voice test successful! I can hear you clearly."
    elif 'bye' in command_lower or 'goodbye' in command_lower:
        return "Goodbye! Have a great day!"
    else:
        return f"I heard you say: {command}. This is a test response."

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Simple Voice Bot Test")
    print("="*50)
    print("\nAccess the voice interface at:")
    print("  http://localhost:5000")
    print("\nPress Ctrl+C to stop")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)