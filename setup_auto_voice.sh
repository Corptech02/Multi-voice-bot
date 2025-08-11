#!/bin/bash
# Setup auto voice typing for Claude

echo "================================"
echo "🎤 CLAUDE AUTO VOICE SETUP"
echo "================================"
echo ""

# Check if tmux is installed
if command -v tmux &> /dev/null; then
    echo "✅ tmux is installed"
    
    # Check if we're in tmux
    if [ -n "$TMUX" ]; then
        echo "✅ You're already in a tmux session!"
        SESSION_NAME=$(tmux display-message -p '#S')
        echo "   Session name: $SESSION_NAME"
    else
        echo "⚠️  You're not in a tmux session"
        echo ""
        echo "To use auto voice commands, run Claude in tmux:"
        echo "  1. Exit this terminal"
        echo "  2. Run: tmux new -s claude"
        echo "  3. Start Claude in the tmux session"
        echo "  4. Run this setup again"
    fi
else
    echo "❌ tmux not installed"
    echo ""
    echo "Installing tmux..."
    sudo apt-get update && sudo apt-get install -y tmux
fi

echo ""
echo "Checking for xdotool..."
if command -v xdotool &> /dev/null; then
    echo "✅ xdotool is installed"
else
    echo "❌ xdotool not installed"
    echo "Installing xdotool..."
    sudo apt-get install -y xdotool
fi

echo ""
echo "================================"
echo "READY TO START VOICE INTERFACE"
echo "================================"
echo ""
echo "Run the voice server:"
echo "  cd /home/corp06/software_projects/ClaudeVoiceBot/current"
echo "  source venv/bin/activate"
echo "  python auto_voice_terminal.py"
echo ""