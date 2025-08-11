#!/bin/bash

echo "Starting Multi-Tab Claude Voice Assistant..."

# Activate virtual environment
source venv/bin/activate

# Check if Redis is running, start if not
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
fi

# Start the multi-tab voice assistant
echo "Starting Multi-Tab Voice Assistant on port 8200..."
python multi_tab_voice.py