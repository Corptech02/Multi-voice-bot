#!/usr/bin/env python3
from flask import Flask, send_file, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    return send_file('retro_shooter_improved.html')

@app.route('/retro_shooter_improved.html')
def retro_game():
    return send_file('retro_shooter_improved.html')

@app.route('/<path:path>')
def serve_file(path):
    if os.path.exists(path):
        return send_file(path)
    else:
        return f"File not found: {path}", 404

if __name__ == '__main__':
    print("Starting Retro Game Server on http://0.0.0.0:8000")
    print("Access from other devices: http://192.168.40.232:8000/")
    app.run(host='0.0.0.0', port=8000, debug=True)