#!/bin/bash

echo "=== Connection Test Script ==="
echo

echo "1. Checking services on ports 5000 and 8001:"
ss -tlnp 2>/dev/null | grep -E ':(5000|8001)' || netstat -tlnp 2>/dev/null | grep -E ':(5000|8001)'
echo

echo "2. Testing local connectivity:"
echo -n "Port 5000: "
timeout 2 curl -s http://localhost:5000 >/dev/null 2>&1 && echo "✓ Responding" || echo "✗ Not responding"
echo -n "Port 8001: "
timeout 2 curl -s http://localhost:8001 >/dev/null 2>&1 && echo "✓ Responding" || echo "✗ Not responding"
echo

echo "3. Checking UFW status (requires sudo):"
sudo ufw status 2>/dev/null || echo "Need sudo access"
echo

echo "4. Network interface:"
ip addr show | grep -E "inet.*192.168" | awk '{print "IP: " $2}'
echo

echo "=== End of test ==="