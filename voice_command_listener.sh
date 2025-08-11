#!/bin/bash
# Voice Command Listener - Monitors and displays voice commands

echo "================================"
echo "🎤 VOICE COMMAND LISTENER"
echo "================================"
echo ""
echo "This will show voice commands as they come in."
echo "Start speaking at: https://192.168.40.232:8449"
echo ""
echo "Commands will appear below:"
echo "================================"

# Monitor the voice command file
tail -f /tmp/claude_voice_commands.txt 2>/dev/null | while IFS= read -r line; do
    # Extract just the command (remove timestamp)
    if [[ "$line" =~ \]\ (.+)$ ]]; then
        command="${BASH_REMATCH[1]}"
        echo ""
        echo "🎤 VOICE COMMAND: $command"
        echo ""
        
        # Auto-type the command using xdotool if available
        if command -v xdotool &> /dev/null; then
            # Give user time to switch to terminal
            sleep 2
            xdotool type --clearmodifiers "$command"
            xdotool key Return
            echo "✅ Command auto-typed!"
        else
            echo "💡 Copy and paste the command above"
        fi
        echo "---"
    fi
done