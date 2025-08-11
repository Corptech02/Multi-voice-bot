#!/bin/bash
# Start Claude Voice Bot with options

echo "================================"
echo "Claude Voice Bot Launcher"
echo "================================"
echo ""
echo "Choose how to access the voice bot:"
echo ""
echo "1. Local access only (localhost)"
echo "2. Network access (requires HTTPS for mic)"
echo "3. Development mode (with detailed logs)"
echo ""
read -p "Enter choice (1-3): " choice

cd /home/corp06/software_projects/ClaudeVoiceBot/current
source venv/bin/activate

case $choice in
    1)
        echo "Starting local-only server..."
        echo "Access at: http://localhost:8097"
        python secure_voice_bot.py
        ;;
    2)
        echo "Starting network server..."
        echo ""
        echo "⚠️  For microphone access from other devices:"
        echo "   - Use Chrome/Edge"
        echo "   - Start Chrome with:"
        echo "     chrome --unsafely-treat-insecure-origin-as-secure=\"http://192.168.40.232:8097\""
        echo ""
        python secure_voice_bot.py
        ;;
    3)
        echo "Starting in development mode..."
        FLASK_ENV=development python secure_voice_bot.py
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac