#!/usr/bin/env python3
"""
Edge-TTS Server for high-quality text-to-speech
"""
import asyncio
import edge_tts
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import io
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available high-quality voices
VOICES = {
    "jenny": "en-US-JennyNeural",  # Female, friendly
    "aria": "en-US-AriaNeural",     # Female, casual
    "guy": "en-US-GuyNeural",       # Male, casual
    "davis": "en-US-DavisNeural",   # Male, professional
    "jane": "en-US-JaneNeural",     # Female, professional
    "jason": "en-US-JasonNeural",   # Male, younger
    "sara": "en-US-SaraNeural",     # Female, younger
    "tony": "en-US-TonyNeural",     # Male, casual
    "nancy": "en-US-NancyNeural",   # Female, friendly
    "amber": "en-US-AmberNeural",   # Female, warm
    "ashley": "en-US-AshleyNeural", # Female, pleasant
    "brandon": "en-US-BrandonNeural", # Male, warm
    "christopher": "en-US-ChristopherNeural", # Male, professional
    "cora": "en-US-CoraNeural",     # Female, pleasant
    "elizabeth": "en-US-ElizabethNeural", # Female, refined
    "eric": "en-US-EricNeural",     # Male, casual
    "jacob": "en-US-JacobNeural",   # Male, friendly
    "monica": "en-US-MonicaNeural", # Female, professional
    "roger": "en-US-RogerNeural",   # Male, mature
    "steffan": "en-US-SteffanNeural", # Male, professional
}

# Default voice
DEFAULT_VOICE = "jenny"

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voices"""
    return jsonify({
        "voices": list(VOICES.keys()),
        "default": DEFAULT_VOICE,
        "details": {k: {"name": k, "id": v} for k, v in VOICES.items()}
    })

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech using edge-tts"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice_name = data.get('voice', DEFAULT_VOICE).lower()
        rate = data.get('rate', '+0%')  # e.g., "+20%" for faster, "-20%" for slower
        pitch = data.get('pitch', '+0Hz')  # e.g., "+5Hz" for higher pitch
        volume = data.get('volume', '+0%')  # e.g., "+10%" for louder
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Get the voice ID
        voice_id = VOICES.get(voice_name, VOICES[DEFAULT_VOICE])
        
        logger.info(f"TTS request: voice={voice_name} ({voice_id}), text_length={len(text)}")
        
        # Create async function for edge-tts
        async def generate_speech():
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
            
            return audio_data
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(generate_speech())
        loop.close()
        
        # Return audio as response
        return Response(
            io.BytesIO(audio_data),
            mimetype='audio/mpeg',
            headers={
                'Content-Disposition': 'inline; filename="speech.mp3"',
                'Cache-Control': 'no-cache'
            }
        )
        
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/tts/stream', methods=['POST'])
async def text_to_speech_stream():
    """Stream text to speech using edge-tts"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice_name = data.get('voice', DEFAULT_VOICE).lower()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Get the voice ID
        voice_id = VOICES.get(voice_name, VOICES[DEFAULT_VOICE])
        
        logger.info(f"TTS stream request: voice={voice_name} ({voice_id}), text_length={len(text)}")
        
        # Create communication instance
        communicate = edge_tts.Communicate(text=text, voice=voice_id)
        
        # Stream audio data
        async def generate():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        
        return Response(
            generate(),
            mimetype='audio/mpeg',
            headers={
                'Content-Disposition': 'inline; filename="speech.mp3"',
                'Cache-Control': 'no-cache'
            }
        )
        
    except Exception as e:
        logger.error(f"TTS stream error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "edge-tts-server"})

if __name__ == '__main__':
    print("Starting Edge-TTS Server...")
    print(f"Available voices: {', '.join(VOICES.keys())}")
    print(f"Default voice: {DEFAULT_VOICE}")
    print("Server running on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)