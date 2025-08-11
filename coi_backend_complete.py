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
# import aiofiles  # Not needed
import os

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
email_count = 2
last_scan_time = datetime.now()
scan_results = {"new_emails": 0, "processed": 0}
monitoring_active = True

# Initialize with mock data
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
    },
    {
        "id": "REQ002",
        "timestamp": "2024-08-07T09:30:00",
        "from_email": "sarah.jones@buildrite.com",
        "subject": "COI needed for construction project",
        "original_text": "Hi,\n\nWe need a COI for our construction project:\n\nJob Site: 456 Oak Avenue, Chicago, IL\nGeneral Contractor: BuildRite Construction\nProperty Owner: Metro Development Group\nRequired: GL $1M/$2M, Auto $1M, WC statutory\n\nNeed this by Friday.\n\nThanks,\nSarah",
        "certificate_holder": "Metro Development Group",
        "insured_name": "BuildRite Construction",
        "project_description": "Construction at 456 Oak Avenue",
        "coverage_requirements": "GL $1M/$2M, Auto $1M, Workers Comp",
        "additional_insureds": ["Metro Development Group"],
        "status": "Pending",
        "preview_content": None,
        "ai_confidence": 0.92
    }
]

# Mock scanner that generates new requests
async def mock_email_scanner():
    global email_count, coi_requests, scan_results, monitoring_active
    
    while True:
        if monitoring_active:
            # Simulate finding new emails every 30-60 seconds
            await asyncio.sleep(random.randint(30, 60))
            
            if random.random() > 0.3:  # 70% chance of new email
                email_count += 1
                new_request = {
                    "id": f"REQ{str(email_count).zfill(3)}",
                    "timestamp": datetime.now().isoformat(),
                    "from_email": f"user{email_count}@company{random.randint(1,5)}.com",
                    "subject": f"COI Request #{email_count}",
                    "original_text": f"Mock email request #{email_count}",
                    "certificate_holder": f"Company {email_count} LLC",
                    "insured_name": f"Contractor {email_count} Inc",
                    "project_description": f"Project at {random.randint(100,999)} Street",
                    "coverage_requirements": "General Liability $1M",
                    "additional_insureds": [],
                    "status": "Pending",
                    "preview_content": None,
                    "ai_confidence": round(random.uniform(0.85, 0.99), 2)
                }
                coi_requests.append(new_request)
                scan_results["new_emails"] += 1
        else:
            await asyncio.sleep(5)

# Start scanner on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(mock_email_scanner())

# Models
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
    preview_content: Optional[str]
    ai_confidence: float

class MonitoringStatus(BaseModel):
    active: bool
    last_scan: str
    email_count: int
    scan_results: Dict[str, int]

# Endpoints
@app.get("/")
async def root():
    return {"message": "COI Automation API v3.0", "scanner": "active"}

@app.get("/api/v1/emails/coi-requests", response_model=List[COIRequest])
async def get_coi_requests():
    """Get all COI requests"""
    return coi_requests

@app.get("/api/v1/requests/coi", response_model=List[COIRequest])
async def get_requests_alt():
    """Alternative endpoint for COI requests"""
    return coi_requests

@app.get("/api/v1/requests", response_model=List[COIRequest])
async def get_requests():
    """Get all requests - endpoint expected by Surefire"""
    return coi_requests

@app.get("/api/v1/requests/{request_id}", response_model=COIRequest)
async def get_request_by_id(request_id: str):
    """Get a specific request by ID"""
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request

@app.get("/api/v1/requests/monitoring/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """Get email monitoring status"""
    return MonitoringStatus(
        active=monitoring_active,
        last_scan=last_scan_time.isoformat(),
        email_count=len(coi_requests),
        scan_results=scan_results
    )

@app.post("/api/v1/requests/monitoring/toggle")
async def toggle_monitoring():
    """Toggle email monitoring on/off"""
    global monitoring_active
    monitoring_active = not monitoring_active
    return {"active": monitoring_active}

@app.post("/api/v1/monitoring/start")
async def start_monitoring():
    """Start email monitoring"""
    global monitoring_active
    monitoring_active = True
    return {"status": "active", "message": "Email monitoring started"}

@app.post("/api/v1/monitoring/stop")
async def stop_monitoring():
    """Stop email monitoring"""
    global monitoring_active
    monitoring_active = False
    return {"status": "inactive", "message": "Email monitoring stopped"}

@app.post("/api/v1/requests/monitoring/start")
async def start_monitoring_requests():
    """Start email monitoring (Surefire endpoint)"""
    return await start_monitoring()

@app.post("/api/v1/requests/monitoring/stop")
async def stop_monitoring_requests():
    """Stop email monitoring (Surefire endpoint)"""
    return await stop_monitoring()

@app.post("/api/v1/scanner/start")
async def start_scanner():
    """Start email scanner (alias for start_monitoring)"""
    return await start_monitoring()

@app.post("/api/v1/scanner/stop")
async def stop_scanner():
    """Stop email scanner (alias for stop_monitoring)"""
    return await stop_monitoring()

@app.get("/api/v1/scanner/status")
async def scanner_status():
    """Get scanner status"""
    return {
        "status": "active" if monitoring_active else "inactive",
        "requests_count": len(coi_requests),
        "last_scan": last_scan_time.isoformat()
    }


@app.post("/api/v1/requests/{request_id}/process")
async def process_request_surefire(request_id: str):
    """Process request - Surefire endpoint format"""
    return await process_request(request_id)

@app.post("/api/v1/process/{request_id}")
async def process_request(request_id: str):
    """Process and generate COI for a request"""
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Generate PDF
    pdf_filename = f"coi_{request_id}.pdf"
    pdf_path = f"/tmp/{pdf_filename}"
    
    # Create ACCORD 25 form
    create_accord_25_pdf(pdf_path, request)
    
    # Update request
    request["status"] = "Processed"
    request["preview_content"] = pdf_filename
    
    return {"message": "COI generated", "filename": pdf_filename}

@app.get("/api/v1/preview/{filename}")
async def get_preview(filename: str):
    """Get generated COI file"""
    filepath = f"/tmp/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        filepath,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )

@app.post("/api/v1/requests/{request_id}/send")
async def send_response_surefire(request_id: str):
    """Send response - Surefire endpoint format"""
    return await send_response(request_id)

@app.post("/api/v1/send/{request_id}")
async def send_response(request_id: str):
    """Send COI response email"""
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request["status"] != "Processed":
        raise HTTPException(status_code=400, detail="Request must be processed first")
    
    request["status"] = "Sent"
    request["sent_timestamp"] = datetime.now().isoformat()
    
    return {
        "message": "COI sent successfully",
        "to": request["from_email"],
        "timestamp": request["sent_timestamp"]
    }

@app.post("/api/v1/requests/{request_id}/archive")
async def archive_request_surefire(request_id: str):
    """Archive request - Surefire endpoint format"""
    return await archive_request(request_id)

@app.post("/api/v1/archive/{request_id}")
async def archive_request(request_id: str):
    """Archive a COI request"""
    request = next((r for r in coi_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request["status"] = "Archived"
    request["archived_timestamp"] = datetime.now().isoformat()
    
    return {
        "message": "Request archived successfully",
        "id": request_id,
        "timestamp": request["archived_timestamp"]
    }

def create_accord_25_pdf(filepath: str, request: dict):
    """Create a simple ACCORD 25 PDF form"""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "ACCORD")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 65, "CERTIFICATE OF LIABILITY INSURANCE")
    
    # Form fields
    y_pos = height - 100
    c.setFont("Helvetica", 9)
    
    # Producer section
    c.drawString(50, y_pos, "PRODUCER")
    c.drawString(50, y_pos - 15, "Insurance Agency Inc.")
    c.drawString(50, y_pos - 30, "123 Insurance Way")
    c.drawString(50, y_pos - 45, "Insurance City, ST 12345")
    
    # Insured section
    c.drawString(300, y_pos, "INSURED")
    c.drawString(300, y_pos - 15, request["insured_name"])
    
    # Certificate holder
    y_pos -= 100
    c.drawString(50, y_pos, "CERTIFICATE HOLDER")
    c.drawString(50, y_pos - 15, request["certificate_holder"])
    
    # Coverage section
    y_pos -= 80
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "COVERAGES")
    c.setFont("Helvetica", 9)
    y_pos -= 20
    c.drawString(50, y_pos, "General Liability")
    c.drawString(250, y_pos, "X")
    c.drawString(300, y_pos, "Each Occurrence: $2,000,000")
    
    # Project description
    y_pos -= 100
    c.drawString(50, y_pos, "DESCRIPTION OF OPERATIONS:")
    c.drawString(50, y_pos - 15, request["project_description"])
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 50, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    c.save()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)