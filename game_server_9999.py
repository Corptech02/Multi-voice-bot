#!/usr/bin/env python3
"""Simple HTTP server to host games on port 9999."""

import http.server
import socketserver
import os
import signal
import sys

PORT = 9999

class GameHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for serving game files."""
    
    def end_headers(self):
        # Add headers for better game compatibility
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Custom logging."""
        print(f"[Game Server] {self.address_string()} - {format % args}")

def signal_handler(sig, frame):
    print("\n[Game Server] Shutting down...")
    sys.exit(0)

def main():
    os.chdir('/home/corp06/software_projects/ClaudeVoiceBot/current')
    
    signal.signal(signal.SIGINT, signal_handler)
    
    with socketserver.TCPServer(("0.0.0.0", PORT), GameHTTPRequestHandler) as httpd:
        print(f"[Game Server] Starting on port {PORT}")
        print(f"[Game Server] Available games:")
        print(f"  - Binding of Isaac Clone: http://localhost:{PORT}/isaac_game.html")
        print(f"  - Retro Shooter: http://localhost:{PORT}/retro-shooter/")
        print(f"  - Connect Four: http://localhost:{PORT}/index.html")
        print(f"[Game Server] Press Ctrl+C to stop")
        httpd.serve_forever()

if __name__ == "__main__":
    main()