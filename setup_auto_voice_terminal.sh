#!/bin/bash
# Setup script for automatic voice-to-terminal communication

echo "================================"
echo "CLAUDE AUTO VOICE SETUP"
echo "================================"
echo ""
echo "This will set up automatic voice → Claude communication"
echo ""

# Check if we're in tmux
if [ -n "$TMUX" ]; then
    SESSION_NAME=$(tmux display-message -p '#S')
    echo "✅ You're in tmux session: $SESSION_NAME"
    echo ""
    echo "Voice commands can now be sent to this session!"
    echo ""
    echo "The voice interface at https://192.168.40.232:8449"
    echo "will automatically type commands here!"
else
    echo "❌ You're NOT in a tmux session"
    echo ""
    echo "To enable auto-voice, please:"
    echo "1. Exit Claude (type 'exit')"
    echo "2. Run: tmux new -s claude"
    echo "3. Start Claude again in the tmux session"
    echo "4. Voice commands will auto-type!"
fi

echo ""
echo "================================"