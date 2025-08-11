#!/bin/bash
# Restart Surefire with updated configuration

echo "Stopping Surefire..."
pkill -f "dotnet.*UIGCRM"
sleep 2

echo "Starting Surefire..."
cd /home/corp06/software_projects/UIGCRM/current
nohup dotnet run > surefire.log 2>&1 &

echo "Surefire restarted. Check logs at /home/corp06/software_projects/UIGCRM/current/surefire.log"