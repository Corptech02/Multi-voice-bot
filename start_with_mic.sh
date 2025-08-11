#!/bin/bash

echo "Starting Multi-Voice Bot with Microphone Support..."
echo ""

# Kill any existing processes
pkill -f "python.*multi_tab_voice_http.py"
pkill -f "python.*edge_tts_server_https.py"
pkill -f "localtunnel"

# Start edge-tts server
echo "Starting Edge TTS server..."
python edge_tts_server_https.py > edge_tts.log 2>&1 &
sleep 2

# Start the main multi-voice bot
echo "Starting Multi-Voice Bot on port 8402..."
python multi_tab_voice_http.py > multi_tab.log 2>&1 &
sleep 2

# Start localtunnel
echo "Creating secure tunnel for microphone access..."
npx localtunnel --port 8402 > localtunnel.log 2>&1 &
sleep 3

# Get the tunnel URL
TUNNEL_URL=$(cat localtunnel.log | grep "your url is:" | cut -d' ' -f4)

echo ""
echo "============================================================"
echo "🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT WITH MICROPHONE"
echo "============================================================"
echo ""
echo "✅ Local access (no microphone): http://192.168.40.232:8402"
echo ""
echo "✅ Secure access (with microphone): $TUNNEL_URL"
echo ""
echo "📝 NOTE: The secure URL allows microphone access!"
echo "         You may need to click through a warning page."
echo ""
echo "============================================================"
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep script running
tail -f /dev/null