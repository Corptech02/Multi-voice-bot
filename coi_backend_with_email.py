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
from email_monitor import EmailMonitor

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
        email_monitor = EmailMonitor()
        if email_monitor.connect():
            logger.info("Email monitor connected successfully")
            monitoring_active = True
            email_monitor.monitor_loop(callback=process_new_emails)
        else:
            logger.error("Failed to connect email monitor")
            monitoring_active = False
    except Exception as e:
        logger.error(f"Email monitor error: {str(e)}")
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
    additional_insureds: List[str]
    status: str
    preview_content: Optional[str] = None
    ai_confidence: float

class COIGenerateRequest(BaseModel):
    request_id: str

class EmailResponse(BaseModel):
    request_id: str
    email_content: str

# API endpoints
@app.get("/")
async def root():
    return {"message": "Insurance COI Automation API v3.0"}

@app.get("/api/v1/requests", response_model=List[COIRequest])
async def get_requests():
    """Get all COI requests."""
    return coi_requests

@app.get("/api/v1/requests/{request_id}", response_model=COIRequest)
async def get_request(request_id: str):
    """Get a specific COI request."""
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request

@app.post("/api/v1/requests/{request_id}/archive")
async def archive_request(request_id: str):
    """Archive a COI request."""
    global coi_requests
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request["status"] = "Archived"
    return {"message": "Request archived", "request_id": request_id}

@app.get("/api/v1/requests/monitoring/status")
async def get_monitoring_status():
    """Get email monitoring status."""
    global monitoring_active, email_count, last_scan_time, scan_results
    
    # Check if email config exists
    config_exists = os.path.exists("email_config.json")
    
    return {
        "active": monitoring_active,
        "email_count": email_count,
        "last_scan": last_scan_time.isoformat(),
        "scan_results": scan_results,
        "config_exists": config_exists,
        "status": "active" if monitoring_active else "inactive"
    }

@app.post("/api/v1/requests/monitoring/start")
async def start_monitoring():
    """Start email monitoring."""
    global monitoring_active, monitor_thread
    
    if monitoring_active:
        return {"message": "Monitoring already active", "status": "success"}
    
    # Check if email config exists
    if not os.path.exists("email_config.json"):
        return {
            "status": "error",
            "message": "Email configuration not found. Please create email_config.json from email_config_template.json"
        }
    
    # Start monitor in background thread
    monitor_thread = threading.Thread(target=run_email_monitor, daemon=True)
    monitor_thread.start()
    
    # Wait a moment to see if it connects
    await asyncio.sleep(2)
    
    if monitoring_active:
        return {"message": "Email monitoring started", "status": "success"}
    else:
        return {
            "status": "error", 
            "message": "Failed to start monitoring. Check email configuration and credentials."
        }

@app.post("/api/v1/requests/monitoring/stop")
async def stop_monitoring():
    """Stop email monitoring."""
    global monitoring_active, email_monitor
    
    monitoring_active = False
    if email_monitor:
        email_monitor.disconnect()
    
    return {"message": "Email monitoring stopped", "status": "success"}

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
                "new_requests": len(new_requests),
                "message": f"Found {len(new_requests)} new requests"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/requests/add_manual")
async def add_manual_request(request: Dict[str, Any]):
    """Manually add a COI request (simulating an email)."""
    global coi_requests, email_count
    
    # Generate unique ID
    request_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    # Create COI request from manual input
    parsed_data = request.get("parsed_data", {})
    
    coi_request = {
        "id": request_id,
        "insured_name": parsed_data.get("insured", {}).get("name", "Unknown"),
        "certificate_holder": parsed_data.get("certificate_holder", {}).get("name", "Unknown"),
        "coverage_type": parsed_data.get("coverages", [{}])[0].get("type", "General Liability"),
        "effective_date": parsed_data.get("coverages", [{}])[0].get("effective_date", datetime.now().strftime("%Y-%m-%d")),
        "expiration_date": parsed_data.get("coverages", [{}])[0].get("expiration_date", (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")),
        "status": "Pending",
        "email_from": request.get("email_from", "manual@entry.com"),
        "email_subject": request.get("email_subject", "Manual COI Request"),
        "email_body": request.get("email_body", "Manually entered request"),
        "created_at": datetime.now().isoformat(),
        "parsed_data": parsed_data
    }
    
    # Add to requests list
    coi_requests.insert(0, coi_request)
    email_count += 1
    
    logger.info(f"Manual COI request added: {request_id}")
    
    return {
        "status": "success",
        "request_id": request_id,
        "message": "COI request added successfully"
    }

@app.post("/api/v1/generate", response_model=Dict[str, Any])
async def generate_coi(request: COIGenerateRequest):
    """Generate a COI document."""
    coi_request = next((r for r in coi_requests if r["id"] == request.request_id), None)
    if not coi_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Create PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Add content
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "CERTIFICATE OF INSURANCE")
    
    c.setFont("Helvetica", 12)
    y = height - 100
    
    c.drawString(50, y, f"Certificate Holder: {coi_request['certificate_holder']}")
    y -= 30
    
    c.drawString(50, y, f"Insured: {coi_request['insured_name']}")
    y -= 30
    
    c.drawString(50, y, f"Project: {coi_request['project_description']}")
    y -= 30
    
    c.drawString(50, y, f"Coverage: {coi_request['coverage_requirements']}")
    y -= 30
    
    if coi_request['additional_insureds']:
        c.drawString(50, y, f"Additional Insureds: {', '.join(coi_request['additional_insureds'])}")
        y -= 30
    
    c.drawString(50, y, f"Issue Date: {datetime.now().strftime('%Y-%m-%d')}")
    
    c.save()
    
    # Encode PDF
    buffer.seek(0)
    pdf_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    
    # Update request status
    coi_request["status"] = "Processed"
    coi_request["preview_content"] = pdf_base64
    
    return {
        "request_id": request.request_id,
        "status": "success",
        "coi_document": pdf_base64
    }

@app.post("/api/v1/compose", response_model=EmailResponse)
async def compose_email(request: COIGenerateRequest):
    """Compose email response with COI."""
    coi_request = next((r for r in coi_requests if r["id"] == request.request_id), None)
    if not coi_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    email_content = f"""Dear {coi_request['from_email'].split('@')[0]},

Thank you for your Certificate of Insurance request.

I have generated the COI for {coi_request['insured_name']} with {coi_request['certificate_holder']} as the certificate holder.

The certificate includes:
- Project: {coi_request['project_description']}
- Coverage: {coi_request['coverage_requirements']}
"""
    
    if coi_request['additional_insureds']:
        email_content += f"- Additional Insureds: {', '.join(coi_request['additional_insureds'])}\n"
    
    email_content += """
The COI document is attached to this email.

Please let me know if you need any modifications or have questions.

Best regards,
Insurance Team"""
    
    # Update request status
    coi_request["status"] = "Sent"
    
    return EmailResponse(
        request_id=request.request_id,
        email_content=email_content
    )

@app.get("/api/v1/requests/{request_id}/download")
async def download_coi(request_id: str):
    """Download COI document."""
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request or not request.get("preview_content"):
        raise HTTPException(status_code=404, detail="COI document not found")
    
    pdf_bytes = base64.b64decode(request["preview_content"])
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=COI_{request_id}.pdf"
        }
    )

if __name__ == "__main__":
    # Check if email config exists
    if not os.path.exists("email_config.json"):
        logger.warning("=" * 60)
        logger.warning("EMAIL CONFIGURATION NOT FOUND!")
        logger.warning("Please create email_config.json from email_config_template.json")
        logger.warning("and add your email credentials for the quartet02 account.")
        logger.warning("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)