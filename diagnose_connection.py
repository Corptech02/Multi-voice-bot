#!/usr/bin/env python3
import socket
import subprocess
import sys

print("🔍 Connection Diagnostic Tool\n")

# Check all network interfaces
print("1. Network Interfaces:")
try:
    result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'inet ' in line and 'scope global' in line:
            print(f"   {line.strip()}")
except:
    print("   Unable to get network info")

print("\n2. Testing ports:")
ports = [5000, 8001, 8080]
for port in ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    status = "✅ OPEN" if result == 0 else "❌ CLOSED"
    print(f"   Port {port}: {status}")
    sock.close()

print("\n3. Firewall status:")
try:
    ufw_result = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
    if 'inactive' in ufw_result.stdout.lower():
        print("   UFW: Inactive ✅")
    else:
        print("   UFW: Active - may be blocking ports")
        print(ufw_result.stdout)
except:
    print("   Unable to check UFW status")

print("\n4. Running services:")
services = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
for line in services.stdout.split('\n'):
    if any(p in line for p in ['5000', '8001', '8080']):
        print(f"   {line.strip()}")

print("\n5. Test from this server to itself:")
import requests
try:
    response = requests.get('http://localhost:5000', timeout=2)
    print(f"   http://localhost:5000 - Status: {response.status_code} ✅")
except Exception as e:
    print(f"   http://localhost:5000 - Failed: {e}")

print("\n💡 SOLUTION:")
print("Since the services are running but you can't connect, try:")
print("1. Check if you're on the same network as 192.168.40.232")
print("2. Ask IT to open ports 5000, 8001, 8080")
print("3. Try accessing from the server itself using a local browser")
print("4. Use SSH port forwarding: ssh -L 5000:localhost:5000 corp06@192.168.40.232")