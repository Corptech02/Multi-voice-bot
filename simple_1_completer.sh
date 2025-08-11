#!/bin/bash

echo "Simple 1 Completer Active"
echo "When you type 1, I'll help complete it"
echo "------------------------"

while true; do
    # Get current content
    current=$(tmux capture-pane -t claude:0 -p 2>/dev/null | tail -5)
    
    # If we see "> 1" (user typed 1), send Enter to complete it
    if echo "$current" | grep -q "^> 1$"; then
        echo "[$(date +%H:%M:%S)] Detected '1' - sending Enter"
        tmux send-keys -t claude:0 Enter
        sleep 2  # Wait before checking again
    fi
    
    sleep 0.1
done