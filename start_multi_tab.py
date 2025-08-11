#!/usr/bin/env python3
"""
Start the multi-tab voice assistant with proper module reloading
"""
import sys
import importlib

# Force reload the orchestrator module
if 'orchestrator_simple' in sys.modules:
    importlib.reload(sys.modules['orchestrator_simple'])

# Now import and run the HTTPS runner
from multi_tab_https_runner import app, socketio
import ssl

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT V2 (HTTPS)")
    print("="*60)
    print("✨ Features:")
    print("  - Interface matching port 8103 style")
    print("  - Up to 4 simultaneous Claude sessions")
    print("  - Tab bar at top for easy switching")
    print("  - Audio plays only for active tab")
    print("")
    print("📱 Access at: https://192.168.40.232:8402")
    print("⚠️  Accept the certificate warning to continue")
    print("="*60 + "\n")
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    socketio.run(app, 
                 host='0.0.0.0',
                 port=8402,
                 ssl_context=context,
                 debug=False,
                 allow_unsafe_werkzeug=True)