#!/bin/bash

# Start COI backend first
echo "Starting COI backend..."
cd "/home/corp06/software_projects/UIGCRM/current/UIG COI Tool/backend"
source venv/bin/activate
nohup python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001 > /tmp/coi_backend.log 2>&1 &
echo "COI backend started on port 8001"

# Wait for backend to start
sleep 3

# Start Surefire CRM
echo "Starting Surefire CRM..."
cd /home/corp06/software_projects/UIGCRM/current/bin/Debug/net8.0
nohup /home/corp06/.dotnet/dotnet Surefire.dll > /tmp/surefire.log 2>&1 &
echo "Surefire CRM started on port 5000"

echo "All services started successfully!"
echo "Access Surefire at: http://192.168.40.232:5000"