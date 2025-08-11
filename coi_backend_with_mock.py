#!/usr/bin/env python3
"""
COI Backend with Mock Email Monitoring
Provides email monitoring simulation without Gmail authentication
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import random
import string
import json
import asyncio
from datetime import datetime, timedelta
import base64
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import os
import logging
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Insurance COI Automation API", version="4.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
coi_requests = []
email_count = 0
last_scan_time = datetime.now()
scan_results = {"new_emails": 0, "processed": 0}
monitoring_active = False
mock_monitor_thread = None

# Mock email templates for automatic generation
MOCK_EMAIL_TEMPLATES = [
    {
        "vendor": "ABC Construction Inc.",
        "holder": "Property Management Group LLC",
        "project": "Office Renovation - Building A",
        "coverage": "General Liability - $2,000,000"
    },
    {
        "vendor": "XYZ Electrical Services",
        "holder": "Citywide Development Corp",
        "project": "Electrical Panel Upgrade",
        "coverage": "General Liability - $1,000,000"
    },
    {
        "vendor": "Premier Plumbing LLC",
        "holder": "Regional Mall Associates",
        "project": "Plumbing System Maintenance",
        "coverage": "General Liability - $1,000,000"
    }
]

def generate_mock_email() -> Dict[str, Any]:
    """Generate a mock COI email request."""
    template = random.choice(MOCK_EMAIL_TEMPLATES)
    request_id = f"REQ{random.randint(1000, 9999)}"
    
    email_content = f"""Dear Insurance Team,

We need a Certificate of Insurance for our upcoming project.

Insured: {template['vendor']}
Certificate Holder: {template['holder']}
Project: {template['project']}
Required Coverage: {template['coverage']}

Please send ASAP.

Best regards,
John Smith"""
    
    return {
        "id": request_id,
        "timestamp": datetime.now().isoformat(),
        "from_email": "john.smith@example.com",
        "subject": f"Certificate of Insurance Request - {template['vendor']}",
        "original_text": email_content,
        "certificate_holder": template['holder'],
        "insured_name": template['vendor'],
        "project_description": template['project'],
        "coverage_requirements": template['coverage'],
        "additional_insureds": [],
        "status": "Pending",
        "preview_content": None,
        "ai_confidence": 0.95
    }

def mock_email_monitor():
    """Simulate email monitoring by generating mock requests periodically."""
    global monitoring_active, email_count, scan_results, last_scan_time
    
    logger.info("Mock email monitor started")
    
    while monitoring_active:
        try:
            # Wait between scans
            time.sleep(30)  # Check every 30 seconds
            
            if monitoring_active:
                # Randomly decide if we found new emails (70% chance)
                if random.random() < 0.7:
                    # Generate 1-3 new mock emails
                    num_emails = random.randint(1, 3)
                    
                    for _ in range(num_emails):
                        mock_email = generate_mock_email()
                        coi_requests.append(mock_email)
                        email_count += 1
                        scan_results["new_emails"] += 1
                    
                    last_scan_time = datetime.now()
                    logger.info(f"Mock monitor found {num_emails} new COI requests")
                else:
                    last_scan_time = datetime.now()
                    logger.info("Mock monitor scan complete - no new emails")
                    
        except Exception as e:
            logger.error(f"Error in mock monitor: {e}")
            
    logger.info("Mock email monitor stopped")

# Request models
class COIRequest(BaseModel):
    vendor: str
    coverages: Dict[str, Dict[str, Any]]

class StatusUpdateRequest(BaseModel):
    status: str

# COI Generation
def generate_coi_pdf(request: Dict[str, Any]) -> bytes:
    """Generate a simple COI PDF."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "CERTIFICATE OF LIABILITY INSURANCE")
    
    # Date
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, f"DATE: {datetime.now().strftime('%m/%d/%Y')}")
    
    # Certificate details
    y_pos = height - 120
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "INSURED:")
    c.setFont("Helvetica", 10)
    c.drawString(150, y_pos, request.get("insured_name", "N/A"))
    
    y_pos -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "CERTIFICATE HOLDER:")
    c.setFont("Helvetica", 10)
    c.drawString(200, y_pos, request.get("certificate_holder", "N/A"))
    
    y_pos -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "PROJECT:")
    c.setFont("Helvetica", 10)
    c.drawString(150, y_pos, request.get("project_description", "N/A"))
    
    y_pos -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "COVERAGE:")
    c.setFont("Helvetica", 10)
    c.drawString(150, y_pos, request.get("coverage_requirements", "N/A"))
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 50, "This is a sample COI generated for demonstration purposes.")
    
    c.save()
    buffer.seek(0)
    return buffer.read()

# API Endpoints
@app.get("/")
async def root():
    return {"message": "COI Backend API with Mock Monitoring", "version": "4.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/requests")
async def get_all_requests():
    """Get all COI requests."""
    return coi_requests

@app.post("/api/v1/requests")
async def create_request(request: COIRequest):
    """Create a new COI request."""
    request_id = f"REQ{random.randint(100, 999)}"
    new_request = {
        "id": request_id,
        "timestamp": datetime.now().isoformat(),
        "vendor": request.vendor,
        "status": "Pending",
        "coverages": request.coverages,
        "from_email": "manual@request.com",
        "subject": f"Manual COI Request - {request.vendor}",
        "certificate_holder": "Manual Entry",
        "insured_name": request.vendor,
        "project_description": "Manually created request",
        "coverage_requirements": "See coverages",
        "additional_insureds": [],
        "ai_confidence": 1.0
    }
    coi_requests.append(new_request)
    return new_request

@app.get("/api/v1/requests/{request_id}")
async def get_request(request_id: str):
    """Get specific COI request."""
    for req in coi_requests:
        if req["id"] == request_id:
            return req
    raise HTTPException(status_code=404, detail="Request not found")

@app.put("/api/v1/requests/{request_id}/status")
async def update_status(request_id: str, update: StatusUpdateRequest):
    """Update request status."""
    for req in coi_requests:
        if req["id"] == request_id:
            req["status"] = update.status
            return {"success": True, "message": "Status updated"}
    raise HTTPException(status_code=404, detail="Request not found")

@app.get("/api/v1/requests/{request_id}/download")
async def download_coi(request_id: str):
    """Download COI PDF."""
    for req in coi_requests:
        if req["id"] == request_id:
            pdf_bytes = generate_coi_pdf(req)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=COI_{request_id}.pdf"
                }
            )
    raise HTTPException(status_code=404, detail="Request not found")

# Email Monitoring Endpoints
@app.get("/api/v1/requests/monitoring/status")
async def get_monitoring_status():
    """Get email monitoring status."""
    return {
        "active": monitoring_active,
        "email_count": email_count,
        "last_scan": last_scan_time.isoformat(),
        "scan_results": scan_results,
        "mode": "mock"  # Indicate we're in mock mode
    }

@app.post("/api/v1/requests/monitoring/start")
async def start_monitoring():
    """Start mock email monitoring."""
    global monitoring_active, mock_monitor_thread
    
    if monitoring_active:
        return {"status": "already_running", "message": "Monitoring is already active"}
    
    monitoring_active = True
    
    # Start mock monitor in background thread
    mock_monitor_thread = threading.Thread(target=mock_email_monitor)
    mock_monitor_thread.daemon = True
    mock_monitor_thread.start()
    
    logger.info("Mock email monitoring started")
    
    return {
        "status": "started",
        "message": "Mock email monitoring started",
        "active": monitoring_active,
        "mode": "mock"
    }

@app.post("/api/v1/requests/monitoring/stop")
async def stop_monitoring():
    """Stop mock email monitoring."""
    global monitoring_active
    
    monitoring_active = False
    logger.info("Mock email monitoring stopped")
    
    return {
        "status": "stopped",
        "message": "Mock email monitoring stopped",
        "active": monitoring_active
    }

@app.post("/api/v1/requests/monitoring/scan")
async def manual_scan():
    """Manually trigger a mock email scan."""
    global email_count, scan_results, last_scan_time
    
    # Generate 1-3 mock emails immediately
    num_emails = random.randint(1, 3)
    new_requests = []
    
    for _ in range(num_emails):
        mock_email = generate_mock_email()
        coi_requests.append(mock_email)
        new_requests.append(mock_email)
        email_count += 1
        scan_results["new_emails"] += 1
    
    last_scan_time = datetime.now()
    
    return {
        "status": "success",
        "new_emails": num_emails,
        "total_requests": len(coi_requests),
        "mode": "mock"
    }

@app.post("/api/v1/requests/mock/generate")
async def generate_mock_requests(count: int = 5):
    """Generate multiple mock COI requests."""
    new_requests = []
    
    for _ in range(count):
        mock_email = generate_mock_email()
        coi_requests.append(mock_email)
        new_requests.append(mock_email)
    
    return {
        "status": "success",
        "generated": count,
        "total_requests": len(coi_requests),
        "new_requests": new_requests
    }

# Initialize with some example data
coi_requests = [
    {
        "id": "REQ001",
        "timestamp": datetime.now().isoformat(),
        "from_email": "demo@example.com",
        "subject": "Certificate of Insurance Request - Demo Company",
        "original_text": "This is a demo COI request for testing purposes.",
        "certificate_holder": "Demo Certificate Holder",
        "insured_name": "Demo Insurance Company",
        "project_description": "Demo Project",
        "coverage_requirements": "General Liability - $1,000,000",
        "additional_insureds": [],
        "status": "Pending",
        "preview_content": None,
        "ai_confidence": 0.95
    }
]

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    uvicorn.run(app, host="0.0.0.0", port=port)