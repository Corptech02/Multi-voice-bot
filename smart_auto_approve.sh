#!/bin/bash

echo "🚀 SMART AUTO-APPROVE STARTED"
echo "Monitoring for Claude prompts..."
echo "----------------------------"

last_send=0

while true; do
    # Get the last 20 lines from tmux
    output=$(tmux capture-pane -t claude:0 -p -S -20 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Check for various prompt indicators
        if echo "$output" | grep -qE "(Do you want to proceed\?|Would you like|Confirm|Allow|Execute|Run|Bash command)" &&
           echo "$output" | grep -qE "(❯|1\.|Yes|No|\?)" &&
           [ $(($(date +%s) - last_send)) -gt 1 ]; then
            
            echo "[$(date +%H:%M:%S)] Prompt detected! Sending: 1 + Enter"
            
            # Send 1 and Enter
            tmux send-keys -t claude:0 "1" C-m
            
            last_send=$(date +%s)
        fi
    fi
    
    sleep 0.1
done