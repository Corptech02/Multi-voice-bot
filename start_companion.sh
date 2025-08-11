#!/bin/bash

echo "🤗 Starting AI Companion Voice Bot..."
echo "=================================="

# Check if tmux session exists
if ! tmux has-session -t claude 2>/dev/null; then
    echo "❌ No Claude tmux session found!"
    echo "Please start Claude in a tmux session named 'claude' first:"
    echo "  tmux new -s claude"
    echo "  claude"
    exit 1
fi

# Check for SSL certificates
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    echo "🔐 Generating SSL certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
fi

# Install required Python packages if needed
echo "📦 Checking dependencies..."
pip3 install -q flask edge-tts asyncio

# Start the companion bot
echo "🚀 Starting companion on https://192.168.40.232:8105"
echo "✨ Features:"
echo "  - Natural, friendly conversation"
echo "  - Emotional intelligence" 
echo "  - Context awareness"
echo "  - High-quality neural voices"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================="

python3 companion_voice_bot.py