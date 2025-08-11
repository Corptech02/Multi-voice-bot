#!/bin/bash

# Kill existing processes
echo "Stopping existing services..."
pkill -f "python.*8001" 2>/dev/null
pkill -f "Surefire.dll" 2>/dev/null
sleep 2

# Function to start services
start_services() {
    # Start COI backend with Gmail integration
    echo "Starting COI backend with Gmail integration on port 8001..."
    cd /home/corp06/software_projects/ClaudeVoiceBot/current
    
    # Check if we need to create a virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        
        echo "Installing dependencies..."
        pip install fastapi uvicorn pydantic reportlab pillow aiofiles
        pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
        pip install pymupdf
    else
        source venv/bin/activate
    fi
    
    # Copy Gmail credentials from UIGCRM
    echo "Setting up Gmail credentials..."
    mkdir -p credentials
    cp "/home/corp06/uig/codebase/UIGCRM/UIG COI Tool/backend/credentials/credentials.json" credentials/ 2>/dev/null || true
    cp "/home/corp06/uig/codebase/UIGCRM/UIG COI Tool/backend/credentials/token.json" credentials/ 2>/dev/null || true
    
    # Start the Gmail-enabled backend
    python3 coi_backend_gmail.py 8001 &
    COI_PID=$!
    
    echo "COI backend started with PID: $COI_PID"
    
    # Wait for backend to start
    sleep 3
    
    # Now start Surefire
    echo "Starting Surefire CRM..."
    cd /home/corp06/software_projects/UIGCRM/current
    
    # Create proper launch script with environment
    cat > launch_surefire.sh << 'EOF'
#!/bin/bash
export DOTNET_ROOT=/home/corp06/.dotnet
export PATH=$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools
export COI_BACKEND_URL=http://localhost:8001
cd /home/corp06/software_projects/UIGCRM/current/bin/Debug/net8.0
exec /home/corp06/.dotnet/dotnet Surefire.dll
EOF
    
    chmod +x launch_surefire.sh
    ./launch_surefire.sh &
    SUREFIRE_PID=$!
    
    echo "Surefire started with PID: $SUREFIRE_PID"
    
    # Save PIDs for later
    echo $COI_PID > /tmp/coi_backend.pid
    echo $SUREFIRE_PID > /tmp/surefire.pid
    
    echo ""
    echo "✅ All services started successfully!"
    echo "   - COI Backend (Gmail): http://localhost:8001"
    echo "   - Surefire CRM: http://192.168.40.232:5189"
    echo ""
    echo "To check Gmail account connected, visit: http://localhost:8001/api/v1/requests/monitoring/status"
}

# Main execution
start_services

# Keep script running
echo "Press Ctrl+C to stop all services..."
trap 'kill $COI_PID $SUREFIRE_PID 2>/dev/null; exit' INT
wait