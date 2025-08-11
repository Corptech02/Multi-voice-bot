#!/usr/bin/env python3

import http.server
import socketserver
import socket
import os

# Get local IP address
def get_local_ip():
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

PORT = 8889
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class BiddingGameHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        # Redirect root to bidding game
        if self.path == '/':
            self.path = '/bidding_game.html'
        return super().do_GET()
    
    def end_headers(self):
        # Add CORS headers for local network access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

# Get local IP
local_ip = get_local_ip()

print(f"Starting Bidding Game Server...")
print(f"=" * 50)
print(f"Access the game from any device on your network:")
print(f"")
print(f"  http://{local_ip}:{PORT}")
print(f"  http://localhost:{PORT}")
print(f"")
print(f"Press Ctrl+C to stop the server")
print(f"=" * 50)

# Start server
with socketserver.TCPServer(("", PORT), BiddingGameHandler) as httpd:
    httpd.serve_forever()