#!/usr/bin/env python3
import asyncio
import json
from flask import Flask, request, Response
from flask_cors import CORS
import edge_tts
import io

app = Flask(__name__)
CORS(app)  # Allow all origins

@app.route('/tts', methods=['POST'])
def tts():
    """Convert text to speech using Edge-TTS"""
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'en-US-AriaNeural')
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        volume = data.get('volume', '+0%')
        
        # Create async function to generate speech
        async def generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            audio_data = io.BytesIO()
            
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio_data.write(chunk['data'])
            
            audio_data.seek(0)
            return audio_data.read()
        
        # Run async function
        audio_bytes = asyncio.run(generate())
        
        return Response(audio_bytes, mimetype='audio/mpeg', 
                       headers={'Content-Type': 'audio/mpeg'})
    except Exception as e:
        return json.dumps({'error': str(e)}), 400

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get list of available voices"""
    try:
        async def list_voices():
            voices = await edge_tts.list_voices()
            return voices
        
        voices = asyncio.run(list_voices())
        return json.dumps(voices)
    except Exception as e:
        return json.dumps({'error': str(e)}), 400

if __name__ == '__main__':
    print("Starting Edge-TTS HTTP Server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)