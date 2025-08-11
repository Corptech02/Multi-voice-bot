#!/usr/bin/env python3
import http.server
import socketserver
import os
import sys

PORT = 8000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

# Serve from the retro-shooter directory
game_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'retro-shooter')
os.chdir(game_dir)

print(f"Starting game server on port {PORT}...")
print(f"Game directory: {game_dir}")
print(f"Server running at http://0.0.0.0:{PORT}/")
print(f"Access the game at http://YOUR_SERVER_IP:{PORT}/")
print("\nPress Ctrl+C to stop the server")

Handler = CORSHTTPRequestHandler

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    httpd.allow_reuse_address = True
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)