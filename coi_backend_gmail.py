#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
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
from gmail_email_monitor import GmailEmailMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Insurance COI Automation API", version="3.0")

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
email_monitor = None
monitor_thread = None

# Initialize with some example data
coi_requests = [
    {
        "id": "REQ001",
        "timestamp": "2024-08-07T10:15:00",
        "from_email": "john.smith@abccorp.com",
        "subject": "Certificate of Insurance Request - ABC Corporation",
        "original_text": "Dear Insurance Team,\n\nWe need a Certificate of Insurance for our upcoming project at 123 Main Street, Springfield, IL.\n\nInsured: ABC Corporation\nCertificate Holder: XYZ Properties LLC\nProject: Office Renovation\nRequired Coverage: General Liability $2M\n\nPlease send ASAP.\n\nBest regards,\nJohn Smith",
        "certificate_holder": "XYZ Properties LLC",
        "insured_name": "ABC Corporation",
        "project_description": "Office Renovation at 123 Main Street",
        "coverage_requirements": "General Liability - $2,000,000",
        "additional_insureds": [],
        "status": "Pending",
        "preview_content": None,
        "ai_confidence": 0.95
    }
]

def process_new_emails(new_requests: List[Dict[str, Any]]):
    """Callback function to process new emails from monitor."""
    global coi_requests, email_count, scan_results, last_scan_time
    
    for request in new_requests:
        coi_requests.append(request)
        email_count += 1
        scan_results["new_emails"] += 1
    
    last_scan_time = datetime.now()
    logger.info(f"Added {len(new_requests)} new COI requests")

def run_email_monitor():
    """Run email monitor in a separate thread."""
    global email_monitor, monitoring_active
    
    try:
        email_monitor = GmailEmailMonitor()
        if email_monitor.connect():
            logger.info("Gmail monitor connected successfully")
            monitoring_active = True
            email_monitor.monitor_loop(callback=process_new_emails, interval=30)
        else:
            logger.error("Failed to connect Gmail monitor")
            monitoring_active = False
    except Exception as e:
        logger.error(f"Gmail monitor error: {str(e)}")
        monitoring_active = False

# Request models
class COIRequest(BaseModel):
    id: str
    timestamp: str
    from_email: str
    subject: str
    original_text: str
    certificate_holder: str
    insured_name: str
    project_description: str
    coverage_requirements: str
    additional_insureds: List[str] = []
    status: str = "Pending"
    preview_content: Optional[str] = None
    ai_confidence: float = 0.0

class COIResponse(BaseModel):
    success: bool
    message: str
    request_id: Optional[str] = None
    preview_image: Optional[str] = None

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
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/requests")
async def get_all_requests():
    """Get all COI requests."""
    return coi_requests

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

@app.post("/api/v1/requests/{request_id}/send")
async def send_coi(request_id: str):
    """Send COI via email."""
    for req in coi_requests:
        if req["id"] == request_id:
            req["status"] = "Sent"
            return {"success": True, "message": "COI sent successfully"}
    raise HTTPException(status_code=404, detail="Request not found")

# Email Monitoring Endpoints
@app.get("/api/v1/requests/monitoring/status")
async def get_monitoring_status():
    """Get email monitoring status."""
    global email_count, last_scan_time, scan_results, monitoring_active
    
    # For Gmail monitoring, we'll check if the monitor is active
    if monitoring_active and email_monitor:
        monitoring_active = True
    else:
        monitoring_active = False
    
    return {
        "active": monitoring_active,
        "email_count": email_count,
        "last_scan": last_scan_time.isoformat(),
        "scan_results": scan_results
    }

@app.post("/api/v1/requests/monitoring/start")
async def start_monitoring():
    """Start email monitoring."""
    global monitoring_active, monitor_thread
    
    if monitoring_active:
        return {"status": "already_running", "message": "Monitoring is already active"}
    
    # Start monitor in background thread
    monitor_thread = threading.Thread(target=run_email_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Wait a moment for connection
    await asyncio.sleep(2)
    
    return {
        "status": "started",
        "message": "Email monitoring started",
        "active": monitoring_active
    }

@app.post("/api/v1/requests/monitoring/stop")
async def stop_monitoring():
    """Stop email monitoring."""
    global monitoring_active
    
    monitoring_active = False
    return {"status": "stopped", "message": "Email monitoring stopped"}

@app.post("/api/v1/requests/scan")
async def scan_emails():
    """Manually trigger email scan."""
    global email_monitor, scan_results, last_scan_time
    
    if not monitoring_active:
        return {"status": "error", "message": "Monitoring is not active"}
    
    try:
        if email_monitor:
            new_requests = email_monitor.fetch_emails()
            process_new_emails(new_requests)
            return {
                "status": "success",
                "new_emails": len(new_requests),
                "total_requests": len(coi_requests)
            }
        else:
            return {"status": "error", "message": "Email monitor not initialized"}
    except Exception as e:
        logger.error(f"Scan error: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    uvicorn.run(app, host="0.0.0.0", port=port)