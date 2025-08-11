#!/usr/bin/env python3
"""Run the complete multi-tab voice assistant with HTTPS"""
import ssl
import subprocess
import sys

# Run the complete version directly with SSL
if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    # Run with subprocess to ensure proper environment
    subprocess.run([
        sys.executable, 
        'multi_tab_voice_http_complete.py',
        '--ssl-context'
    ])