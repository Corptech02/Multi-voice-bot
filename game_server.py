#!/usr/bin/env python3
import http.server
import socketserver
import socket

PORT = 7777
Handler = http.server.SimpleHTTPRequestHandler

class MyTCPServer(socketserver.TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

print(f"Starting server on all interfaces (0.0.0.0:{PORT})")
print(f"Local machine: http://localhost:{PORT}/retro_game.html")
print(f"Network access: http://192.168.40.232:{PORT}/retro_game.html")
print("\nServer is ready for connections...")

with MyTCPServer(("0.0.0.0", PORT), Handler) as httpd:
    httpd.serve_forever()