#!/usr/bin/env python3
"""
Edge-TTS Server with HTTPS support - Only working voices
"""
import asyncio
import edge_tts
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import io
import logging
import ssl
import os

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Only voices that are confirmed working
VOICES = {
    # Confirmed working voices
    "jenny": "en-US-JennyNeural",          # Female, friendly
    "aria": "en-US-AriaNeural",            # Female, casual  
    "guy": "en-US-GuyNeural",              # Male, casual
    "eric": "en-US-EricNeural",            # Male, casual
    "christopher": "en-US-ChristopherNeural", # Male, professional
    "steffan": "en-US-SteffanNeural",      # Male, professional
    "roger": "en-US-RogerNeural",          # Male, mature
    
    # Additional voices to try
    "ryan": "en-US-RyanNeural",            # Male voice
    "michelle": "en-US-MichelleNeural",    # Female voice
    "andrew": "en-US-AndrewNeural",        # Male voice
    "emma": "en-US-EmmaNeural",            # Female voice
    "brian": "en-US-BrianNeural",          # Male voice
    "ana": "en-US-AnaNeural",              # Female child voice
}

# Default voice
DEFAULT_VOICE = "jenny"

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voices"""
    return jsonify({
        "voices": list(VOICES.keys()),
        "default": DEFAULT_VOICE,
        "details": {k: {"name": k, "id": v, "gender": "Female" if k in ["jenny", "aria", "michelle", "emma", "ana"] else "Male"} for k, v in VOICES.items()}
    })

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech using edge-tts"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice_name = data.get('voice', DEFAULT_VOICE).lower()
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        volume = data.get('volume', '+0%')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Get the voice ID
        voice_id = VOICES.get(voice_name, VOICES[DEFAULT_VOICE])
        
        logger.info(f"TTS request: voice={voice_name} ({voice_id}), text_length={len(text)}")
        
        # Create async function for edge-tts
        async def generate_speech():
            try:
                # Create communication instance
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice_id,
                    rate=rate,
                    pitch=pitch,
                    volume=volume
                )
                
                # Generate speech and collect audio data
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                
                if not audio_data:
                    logger.error(f"No audio data received for voice {voice_id}")
                    return None
                    
                return audio_data
                
            except Exception as e:
                logger.error(f"Edge-TTS generation error: {str(e)}")
                return None
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(generate_speech())
        loop.close()
        
        if not audio_data:
            # Fallback to a known working voice
            logger.warning(f"Voice {voice_name} failed, falling back to {DEFAULT_VOICE}")
            voice_id = VOICES[DEFAULT_VOICE]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_data = loop.run_until_complete(generate_speech())
            loop.close()
            
            if not audio_data:
                return jsonify({"error": "Failed to generate audio"}), 500
        
        # Return audio as response
        return Response(
            io.BytesIO(audio_data),
            mimetype='audio/mpeg',
            headers={
                'Content-Disposition': 'inline; filename="speech.mp3"',
                'Cache-Control': 'no-cache',
                'X-Voice-Used': voice_id  # Include which voice was actually used
            }
        )
        
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "edge-tts-server"})

if __name__ == '__main__':
    print("Starting Edge-TTS HTTPS Server (Working Voices Only)...")
    print(f"Available voices: {', '.join(VOICES.keys())}")
    print(f"Default voice: {DEFAULT_VOICE}")
    
    # Check if certs exist
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        # Try to find existing certs
        possible_paths = [
            ('/home/corp06/software_projects/ClaudeVoiceBot/current/cert.pem', 
             '/home/corp06/software_projects/ClaudeVoiceBot/current/key.pem'),
            ('cert.pem', 'key.pem')
        ]
        
        for cp, kp in possible_paths:
            if os.path.exists(cp) and os.path.exists(kp):
                cert_path = cp
                key_path = kp
                break
    
    print(f"Using certificates: {cert_path}, {key_path}")
    print("Server running on https://192.168.40.232:5001")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    
    app.run(host='0.0.0.0', port=5001, debug=False, ssl_context=context)