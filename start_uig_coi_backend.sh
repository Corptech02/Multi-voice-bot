#!/bin/bash

# Stop any existing COI backend processes
pkill -f "api.main" 2>/dev/null

# Navigate to the UIG COI Tool backend directory
cd "/home/corp06/software_projects/UIGCRM/current/UIG COI Tool/backend"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:/home/corp06/software_projects/UIGCRM/current/UIG COI Tool/backend"

# Start the backend
echo "Starting UIG COI Tool backend on port 8001..."
python -m api.main