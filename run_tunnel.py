#!/usr/bin/env python3
import subprocess
import time
import requests
import json

# Start local server if not running
print("Starting local server...")
server = subprocess.Popen(['python3', 'server.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)

# Try bore.pub - a simple TCP tunnel that doesn't require auth
print("Creating tunnel with bore.pub...")
try:
    bore = subprocess.Popen(['npx', 'bore', 'local', '8000', '--to', 'bore.pub'], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(3)
    
    # Read output
    output, error = bore.communicate(timeout=5)
    print("Output:", output)
    print("Error:", error)
except:
    pass

# Alternative: try localhost.run
print("\nTrying localhost.run...")
ssh_cmd = "ssh -R 80:localhost:8000 localhost.run -o StrictHostKeyChecking=no"
process = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=10)
print("localhost.run output:", process.stdout)
print("localhost.run error:", process.stderr)