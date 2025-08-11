#!/bin/bash
# Voice to FIFO - Creates a named pipe for voice commands

echo "================================"
echo "🎤 VOICE TO TERMINAL PIPE"
echo "================================"
echo ""

# Create named pipe
FIFO="/tmp/claude_voice_pipe"
if [[ ! -p $FIFO ]]; then
    mkfifo $FIFO
    echo "Created named pipe: $FIFO"
fi

echo "To use this:"
echo "1. In your Claude terminal, run:"
echo "   cat /tmp/claude_voice_pipe"
echo ""
echo "2. Voice commands will appear automatically!"
echo "================================"
echo ""

# Monitor voice commands and send to pipe
tail -f /tmp/claude_voice_commands.txt 2>/dev/null | while IFS= read -r line; do
    if [[ "$line" =~ \]\ (.+)$ ]]; then
        command="${BASH_REMATCH[1]}"
        echo "🎤 Sending to terminal: $command"
        echo "$command" > $FIFO
    fi
done