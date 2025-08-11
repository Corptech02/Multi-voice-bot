# Claude Voice Bot Setup Guide

## Overview
This voice bot system allows you to interact with Claude using voice commands through a web interface.

## Architecture
- **Web Interface**: Flask server with HTML/JavaScript frontend
- **Voice Input**: Web Speech API for speech recognition
- **Voice Output**: Google Text-to-Speech (gTTS) for responses
- **Terminal Integration**: tmux for managing Claude terminal sessions
- **Communication**: WebSockets for real-time updates

## Quick Start

### 1. Test Basic Voice Functionality
```bash
# Activate virtual environment
source venv/bin/activate

# Run the simple test script
python simple_voice_test.py
```
Open http://localhost:5000 and test voice input/output.

### 2. Run the Full Voice Bot
```bash
# Start the main voice assistant
./start_voice_bot.sh
```

### 3. HTTPS Setup (for remote access)
```bash
# The multi-tab HTTPS version allows secure microphone access
python multi_tab_voice_https_complete.py
```

## Key Components

### Main Scripts
- `voice_tts_realtime.py` - Main voice bot with real-time Claude integration
- `multi_tab_voice_https_complete.py` - Multi-tab version with HTTPS support
- `simple_voice_test.py` - Basic voice I/O test script
- `orchestrator_simple_v2.py` - Manages multiple Claude sessions

### Features
1. **Real-time Commentary**: Captures Claude's thinking process
2. **Auto-approval**: Automatically approves bash commands
3. **Multi-tab Support**: Run multiple Claude sessions
4. **TTS Voices**: Multiple voice options (US, UK, AU accents)
5. **Visual Feedback**: Shows recording status and responses

## Requirements
- Python 3.8+
- tmux
- Chrome/Edge browser (for microphone access)
- SSL certificates (for HTTPS version)

## Dependencies
```bash
pip install flask flask-socketio gtts
```

## Troubleshooting

### Microphone Not Working
1. Ensure using HTTPS or localhost
2. Check browser permissions
3. Use Chrome flag for insecure origins:
   ```
   chrome --unsafely-treat-insecure-origin-as-secure="http://YOUR_IP:PORT"
   ```

### No Audio Output
1. Check system volume
2. Verify gTTS is installed
3. Test with simple_voice_test.py first

### tmux Connection Issues
1. Ensure tmux session 'claude' exists
2. Check session permissions
3. Verify orchestrator is running

## Customization

### Change TTS Voice
Edit the accent parameter in get_tts_audio():
- 'com' - US English
- 'co.uk' - British English  
- 'com.au' - Australian English

### Modify Response Filtering
Edit capture_tmux_output() to change what Claude responses are captured.

### Add New Commands
Extend generate_response() in simple_voice_test.py for custom commands.