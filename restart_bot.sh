#!/bin/bash
echo "Stopping all services..."
pkill -f orchestrator_simple_v2
pkill -f multi_tab_https_runner
pkill -f edge_tts_server
pkill -f claude_simple_wrapper

sleep 3

echo "Starting services..."
nohup python3 edge_tts_server_working.py > edge_tts_server.log 2>&1 &
sleep 1
nohup python3 orchestrator_simple_v2.py > orchestrator.log 2>&1 &
sleep 1
nohup python3 multi_tab_https_runner.py > multi_tab_https.log 2>&1 &

echo "Waiting for services to start..."
sleep 3

echo "Checking status..."
ps aux | grep -E '(orchestrator|multi_tab|edge_tts)' | grep -v grep
netstat -tuln | grep -E '(8402|5001)'

echo "Bot restarted! Access at https://192.168.40.232:8402"