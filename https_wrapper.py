#!/usr/bin/env python3
"""
HTTPS Wrapper for Multi-Tab Voice Bot
Provides secure HTTPS access with proper SSL handling
"""
import ssl
import os
from werkzeug.serving import run_simple
from werkzeug.middleware.proxy_fix import ProxyFix
import sys

# Import the Flask app from multi_tab_voice_http_complete
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multi_tab_voice_http_complete import app, socketio

# Apply proxy fix for proper HTTPS handling
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔒 HTTPS Multi-Tab Claude Voice Assistant")
    print("="*60)
    print("Starting HTTPS server...")
    print("Access at: https://192.168.40.232:8443")
    print("="*60 + "\n")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    # Run with SocketIO
    socketio.run(app, 
                 host='0.0.0.0',
                 port=8443,
                 ssl_context=context,
                 debug=False,
                 allow_unsafe_werkzeug=True)