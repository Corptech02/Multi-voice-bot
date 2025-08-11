#\!/bin/bash
BACKEND_DIR="/home/corp06/software_projects/UIGCRM/current/UIG COI Tool/backend"
cd "$BACKEND_DIR" && source venv/bin/activate && python -m uvicorn api.main:app --reload --port 8001
