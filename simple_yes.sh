#!/bin/bash
echo "✅ SIMPLE YES APPROVER - Starting..."

while true; do
    # Check if there's a bash prompt
    if tmux capture-pane -t claude:0 -p | tail -5 | grep -q "Do you want to proceed?"; then
        echo "[$(date +%H:%M:%S)] Detected prompt - sending 1+Enter"
        tmux send-keys -t claude:0 "1" Enter
        sleep 3
    fi
    sleep 0.5
done