#!/usr/bin/env python3
"""Simple HTTP Voice Assistant - No SSL"""
from flask import Flask, render_template_string
import os

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Voice Assistant</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #1a1a2e; color: white; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #00ff00; text-align: center; }
        .status { background: #0f2027; padding: 20px; border-radius: 10px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Claude Voice Assistant</h1>
        <div class="status">
            <h2>Status: Running</h2>
            <p>Voice assistant is active on port 8080</p>
            <p>This is a simplified version for testing connectivity.</p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎙️ SIMPLE VOICE ASSISTANT (HTTP)")
    print("="*50)
    print("Access at: http://192.168.40.232:7777")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=7777, debug=False)