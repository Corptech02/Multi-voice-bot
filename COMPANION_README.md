# AI Companion Voice Bot

A natural, conversational AI companion that provides emotional support, engaging conversations, and personalized interactions through voice.

## Features

### 🎯 Core Features
- **Natural Conversation Flow**: Includes fillers, transitions, and human-like speech patterns
- **Emotional Intelligence**: Detects and responds to user emotions appropriately
- **Memory & Context**: Remembers past conversations and user preferences
- **High-Quality Neural Voices**: Multiple voice profiles with dynamic adjustments
- **Continuous Listening**: Hands-free conversation mode
- **Auto-Approval**: Automatically handles Claude's permission prompts

### 🧠 Advanced Features (companion_voice_advanced.py)
- **Persistent Memory**: SQLite database for long-term conversation history
- **Mood Tracking**: Monitors and adapts to user emotional states
- **Proactive Engagement**: Asks follow-up questions and checks in on previous topics
- **Voice Modulation**: Adjusts pitch, rate, and tone based on conversation context
- **User Profiles**: Maintains individual preferences and conversation history

## Quick Start

### Basic Companion Bot
```bash
# Make sure Claude is running in tmux session 'claude'
tmux new -s claude
claude

# In another terminal, start the companion
./start_companion.sh
```

### Advanced Companion Bot
```bash
# For the advanced version with memory
python3 companion_voice_advanced.py
```

## Voice Profiles

### Basic Version
- **Warm Male**: Friendly, supportive male voice
- **Warm Female**: Caring, empathetic female voice  
- **British**: Professional yet friendly British accent

### Advanced Version
- **Warm & Supportive**: Default empathetic companion voice
- **Cheerful & Energetic**: Upbeat and enthusiastic
- **Calm & Soothing**: Relaxing and peaceful
- **Professional & Clear**: Articulate and focused

## How It Works

1. **Context Enhancement**: Each message is enhanced with personality traits and conversation context
2. **Emotional Analysis**: Detects user mood from text and conversation patterns
3. **Dynamic TTS**: Adjusts voice parameters based on emotional context
4. **Memory System**: Stores and retrieves conversation history for continuity

## Conversation Examples

### Natural Flow
- Uses fillers: "Hmm, that's interesting..."
- Transitions: "By the way, how did that project go?"
- Acknowledgments: "I hear you, that sounds challenging"

### Emotional Responses
- Happy: Matches positive energy with upbeat responses
- Sad/Stressed: Provides empathetic support and validation
- Excited: Shares enthusiasm while staying grounded

### Memory & Follow-ups
- "Last time you mentioned working on X, how's that going?"
- "Remember when you told me about Y? Any updates?"

## Technical Details

### Dependencies
- Flask (web framework)
- edge-tts (high-quality text-to-speech)
- SQLite3 (for advanced version)
- SSL certificates (auto-generated)

### Architecture
- Flask server for web interface
- Tmux integration for Claude communication
- Async TTS generation for smooth playback
- WebSocket-style polling for real-time responses

## Customization

### Personality Traits
Edit `COMPANION_CONFIG` in the Python files to adjust:
- Core personality traits
- Conversation style
- Response patterns
- Proactive behaviors

### Voice Settings
Modify `VOICE_CONFIGS` or `VOICE_PROFILES` to:
- Add new voices
- Adjust pitch/rate ranges
- Change emotion mappings

## Tips for Best Experience

1. **Natural Speech**: Speak naturally as you would to a friend
2. **Continuous Mode**: Click the mic once for hands-free conversation
3. **Emotional Expression**: The bot responds to your emotional state
4. **Context Building**: Share details for more personalized responses
5. **Memory Benefits**: Use the advanced version for ongoing relationships

## Privacy Note

The advanced version stores conversation history locally in `companion_memory.db`. This enables personalized interactions but means conversations are saved. Delete this file to reset all memory.

## Troubleshooting

- **No Claude Session**: Ensure Claude is running in tmux session named 'claude'
- **SSL Errors**: Certificates are auto-generated; accept the security warning
- **Voice Not Working**: Check microphone permissions in your browser
- **Memory Issues**: Delete `companion_memory.db` to reset if needed

Enjoy your AI companion! 🤗