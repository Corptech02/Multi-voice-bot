#!/bin/bash

echo "Starting Movie URL Quarter Scanner..."
echo "=================================="
echo ""

# Get the IP address
IP=$(hostname -I | awk '{print $1}')

echo "Server will be accessible at:"
echo "  - From this computer: http://localhost:5556"
echo "  - From other computers: http://$IP:5556"
echo ""
echo "=================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the movie scanner
python3 movie_url_scanner.py