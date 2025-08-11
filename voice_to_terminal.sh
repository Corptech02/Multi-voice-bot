#!/bin/bash
# Voice to Terminal Bridge - Monitors voice commands and displays them

echo "================================"
echo "🎤 VOICE TO TERMINAL BRIDGE"
echo "================================"
echo ""
echo "This will display voice commands from the web interface."
echo "Open https://192.168.40.232:8445 in your browser"
echo ""
echo "Waiting for voice commands..."
echo "================================"
echo ""

# Create the file if it doesn't exist
touch /tmp/claude_voice_commands.txt

# Monitor the file for new commands
tail -f /tmp/claude_voice_commands.txt 2>/dev/null | while read line; do
    if [ ! -z "$line" ]; then
        echo ""
        echo "🎤 VOICE COMMAND: ${line#*] }"
        echo ""
        echo "Copy and paste the above command to Claude, or say 'execute' to run it"
        echo "---"
    fi
done