#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
import base64
from io import BytesIO

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import fitz  # PyMuPDF for PDF to image conversion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="UIG COI Tool Backend", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class RequestStatus:
    NEW = "New"
    PROCESSING = "Processing"
    READY_FOR_REVIEW = "ReadyForReview"
    SENT = "Sent"
    COMPLETED = "Completed"
    ERROR = "Error"
    ARCHIVED = "Archived"

# Models
class COIRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    requestor_email: str = Field(alias="requestorEmail")
    company_name: Optional[str] = Field(None, alias="companyName")
    email_content: Optional[str] = Field(None, alias="emailContent")
    processed_content: Optional[str] = Field(None, alias="processedContent")
    response_message: Optional[str] = Field(None, alias="responseMessage")
    pdf_preview_url: Optional[str] = Field(None, alias="pdfPreviewUrl")
    extracted_data: Optional[Dict[str, Any]] = Field(None, alias="extractedData")
    status: str = RequestStatus.NEW
    received_at: datetime = Field(default_factory=datetime.now, alias="receivedAt")
    processed_at: Optional[datetime] = Field(None, alias="processedAt")
    sent_at: Optional[datetime] = Field(None, alias="sentAt")
    is_urgent: bool = Field(False, alias="isUrgent")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ProcessRequestResponse(BaseModel):
    pdf_preview_url: Optional[str] = Field(None, alias="pdfPreviewUrl")
    preview_image: Optional[str] = Field(None, alias="previewImage")  # Base64 encoded image
    response_message: Optional[str] = Field(None, alias="responseMessage")
    processed_content: Optional[str] = Field(None, alias="processedContent")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    
    class Config:
        populate_by_name = True

# In-memory storage
requests_db: Dict[str, COIRequest] = {}
email_monitoring = True
pdf_storage: Dict[str, bytes] = {}  # Store PDFs in memory

# Helper functions
def extract_coi_details(email_content: str) -> Dict[str, Any]:
    """Extract COI details from email content using pattern matching."""
    details = {
        "insured_name": "ACME Corporation",
        "policy_number": "CPP-2024-001234",
        "effective_date": "01/01/2024",
        "expiration_date": "01/01/2025",
        "general_aggregate": "$2,000,000",
        "products_completed": "$2,000,000",
        "each_occurrence": "$1,000,000",
        "personal_injury": "$1,000,000",
        "damage_to_premises": "$100,000",
        "medical_expense": "$5,000",
        "insurance_company": "United Insurance Group",
        "producer": "UIG Insurance Services",
        "certificate_holder": "Sample Certificate Holder",
        "description": "For informational purposes only"
    }
    
    # Try to extract company name from email
    company_match = re.search(r'(?:company|organization|business):\s*([^\n]+)', email_content, re.I)
    if company_match:
        details["insured_name"] = company_match.group(1).strip()
    
    # Try to extract policy number
    policy_match = re.search(r'(?:policy|policy\s*number|policy\s*#):\s*([A-Z0-9-]+)', email_content, re.I)
    if policy_match:
        details["policy_number"] = policy_match.group(1).strip()
    
    return details

def generate_accord_25_pdf(details: Dict[str, Any]) -> bytes:
    """Generate ACCORD 25 PDF with the provided details."""
    buffer = BytesIO()
    
    # Create canvas
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "CERTIFICATE OF LIABILITY INSURANCE")
    
    # Date
    c.setFont("Helvetica", 10)
    c.drawString(450, height - 70, f"DATE: {datetime.now().strftime('%m/%d/%Y')}")
    
    # Form header
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, height - 90, "THIS CERTIFICATE IS ISSUED AS A MATTER OF INFORMATION ONLY AND CONFERS NO RIGHTS UPON THE CERTIFICATE HOLDER.")
    
    # Producer section
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 120, "PRODUCER")
    c.drawString(50, height - 140, details.get("producer", "UIG Insurance Services"))
    c.drawString(50, height - 155, "123 Main Street")
    c.drawString(50, height - 170, "Anytown, ST 12345")
    c.drawString(50, height - 185, "Phone: (555) 123-4567")
    
    # Insured section
    c.drawString(300, height - 120, "INSURED")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(300, height - 140, details.get("insured_name", "ACME Corporation"))
    c.setFont("Helvetica", 10)
    c.drawString(300, height - 155, "456 Business Ave")
    c.drawString(300, height - 170, "Commerce City, ST 67890")
    
    # Insurance companies
    c.drawString(50, height - 220, "INSURERS AFFORDING COVERAGE")
    c.drawString(50, height - 240, f"INSURER A: {details.get('insurance_company', 'United Insurance Group')}")
    
    # Coverage section
    y_pos = height - 280
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y_pos, "TYPE OF INSURANCE")
    c.drawString(250, y_pos, "POLICY NUMBER")
    c.drawString(350, y_pos, "POLICY EFF")
    c.drawString(420, y_pos, "POLICY EXP")
    c.drawString(490, y_pos, "LIMITS")
    
    # General Liability
    y_pos -= 20
    c.setFont("Helvetica", 9)
    c.drawString(50, y_pos, "COMMERCIAL GENERAL LIABILITY")
    c.drawString(250, y_pos, details.get("policy_number", "CPP-2024-001234"))
    c.drawString(350, y_pos, details.get("effective_date", "01/01/2024"))
    c.drawString(420, y_pos, details.get("expiration_date", "01/01/2025"))
    
    # Limits
    y_pos -= 15
    c.drawString(380, y_pos, "EACH OCCURRENCE")
    c.drawString(490, y_pos, details.get("each_occurrence", "$1,000,000"))
    
    y_pos -= 15
    c.drawString(380, y_pos, "DAMAGE TO RENTED PREMISES")
    c.drawString(490, y_pos, details.get("damage_to_premises", "$100,000"))
    
    y_pos -= 15
    c.drawString(380, y_pos, "MED EXP (Any one person)")
    c.drawString(490, y_pos, details.get("medical_expense", "$5,000"))
    
    y_pos -= 15
    c.drawString(380, y_pos, "PERSONAL & ADV INJURY")
    c.drawString(490, y_pos, details.get("personal_injury", "$1,000,000"))
    
    y_pos -= 15
    c.drawString(380, y_pos, "GENERAL AGGREGATE")
    c.drawString(490, y_pos, details.get("general_aggregate", "$2,000,000"))
    
    y_pos -= 15
    c.drawString(380, y_pos, "PRODUCTS-COMP/OP AGG")
    c.drawString(490, y_pos, details.get("products_completed", "$2,000,000"))
    
    # Certificate holder
    y_pos = height - 500
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "CERTIFICATE HOLDER")
    c.setFont("Helvetica", 10)
    y_pos -= 20
    c.drawString(50, y_pos, details.get("certificate_holder", "Sample Certificate Holder"))
    y_pos -= 15
    c.drawString(50, y_pos, "789 Client Street")
    y_pos -= 15
    c.drawString(50, y_pos, "Customer City, ST 13579")
    
    # Description
    y_pos = height - 600
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "DESCRIPTION OF OPERATIONS / LOCATIONS / VEHICLES")
    c.setFont("Helvetica", 9)
    y_pos -= 20
    c.drawString(50, y_pos, details.get("description", "For informational purposes only"))
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 50, "ACORD 25 (2016/03)")
    c.drawString(450, 50, "© 1988-2015 ACORD CORPORATION")
    
    # Save the PDF
    c.save()
    
    # Get the PDF bytes
    buffer.seek(0)
    pdf_bytes = buffer.read()
    buffer.close()
    
    return pdf_bytes

def pdf_to_image(pdf_bytes: bytes) -> str:
    """Convert first page of PDF to base64 encoded JPEG image."""
    try:
        # Open PDF with PyMuPDF
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Get the first page
        page = pdf_document[0]
        
        # Render page to image (scale up for better quality)
        mat = fitz.Matrix(2, 2)  # 2x scale
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(BytesIO(img_data))
        
        # Convert to JPEG and encode as base64
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        pdf_document.close()
        
        return img_base64
    except Exception as e:
        logger.error(f"Error converting PDF to image: {e}")
        return ""

def generate_email_response(request: COIRequest, details: Dict[str, Any]) -> str:
    """Generate email response for COI request."""
    return f"""Dear {request.requestor_email},

Thank you for your Certificate of Insurance request. Please find attached the ACCORD 25 Certificate of Liability Insurance for {details.get('insured_name', request.company_name or 'your organization')}.

Certificate Details:
- Policy Number: {details.get('policy_number', 'CPP-2024-001234')}
- Effective Date: {details.get('effective_date', '01/01/2024')}
- Expiration Date: {details.get('expiration_date', '01/01/2025')}
- General Aggregate Limit: {details.get('general_aggregate', '$2,000,000')}

The certificate has been issued for informational purposes only. If you need any modifications or have questions about the coverage, please don't hesitate to contact us.

Best regards,
UIG Insurance Services Team
Phone: (555) 123-4567
Email: coi@uig.com"""

# API Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/coi/requests")
async def get_all_requests():
    """Get all COI requests."""
    return list(requests_db.values())

@app.get("/coi/requests/{request_id}")
async def get_request(request_id: str):
    """Get a specific COI request."""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    return requests_db[request_id]

@app.post("/coi/process/{request_id}")
async def process_request(request_id: str) -> ProcessRequestResponse:
    """Process a COI request and generate preview."""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = requests_db[request_id]
    
    try:
        # Update status
        request.status = RequestStatus.PROCESSING
        
        # Extract COI details
        details = extract_coi_details(request.email_content or "")
        request.extracted_data = details
        
        # Generate ACCORD 25 PDF
        pdf_bytes = generate_accord_25_pdf(details)
        
        # Store PDF
        pdf_id = f"coi_{request_id}"
        pdf_storage[pdf_id] = pdf_bytes
        
        # Convert PDF to image for preview
        preview_image = pdf_to_image(pdf_bytes)
        
        # Generate email response
        response_message = generate_email_response(request, details)
        
        # Update request
        request.status = RequestStatus.READY_FOR_REVIEW
        request.processed_at = datetime.now()
        request.pdf_preview_url = f"http://localhost:8001/coi/pdf/{pdf_id}"
        request.response_message = response_message
        request.processed_content = json.dumps(details, indent=2)
        
        return ProcessRequestResponse(
            pdf_preview_url=request.pdf_preview_url,
            preview_image=preview_image,
            response_message=response_message,
            processed_content=request.processed_content
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        request.status = RequestStatus.ERROR
        request.error_message = str(e)
        return ProcessRequestResponse(error_message=str(e))

@app.get("/coi/pdf/{pdf_id}")
async def get_pdf(pdf_id: str):
    """Get generated PDF."""
    if pdf_id not in pdf_storage:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    return Response(
        content=pdf_storage[pdf_id],
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={pdf_id}.pdf"
        }
    )

@app.post("/coi/send/{request_id}")
async def send_response(request_id: str):
    """Send COI response via email."""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = requests_db[request_id]
    
    # Simulate sending email
    request.status = RequestStatus.COMPLETED
    request.sent_at = datetime.now()
    
    logger.info(f"COI response sent for request {request_id} to {request.requestor_email}")
    
    return {"success": True}

@app.post("/coi/archive/{request_id}")
async def archive_request(request_id: str):
    """Archive a COI request."""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = requests_db[request_id]
    request.status = RequestStatus.ARCHIVED
    
    return {"success": True}

@app.get("/coi/monitoring/status")
async def get_monitoring_status():
    """Get email monitoring status."""
    return {"active": email_monitoring}

@app.post("/coi/monitoring/start")
async def start_monitoring():
    """Start email monitoring."""
    global email_monitoring
    email_monitoring = True
    
    # Add some mock requests if empty
    if not requests_db:
        mock_requests = [
            COIRequest(
                subject="COI Request - ABC Construction",
                requestor_email="abc@construction.com",
                company_name="ABC Construction LLC",
                email_content="Please provide a Certificate of Insurance for ABC Construction LLC. We need coverage verification for our upcoming project at 123 Main St. Policy should include General Liability with minimum $1M per occurrence.",
                is_urgent=True
            ),
            COIRequest(
                subject="Certificate needed for XYZ Corp",
                requestor_email="procurement@xyzcorp.com",
                company_name="XYZ Corporation",
                email_content="Hi, We need a COI for XYZ Corporation for vendor approval. Please include General Liability coverage details. This is for our vendor management system. Thanks!",
                is_urgent=False
            ),
            COIRequest(
                subject="URGENT: COI for Tomorrow's Meeting",
                requestor_email="john@smithco.com",
                company_name="Smith & Associates",
                email_content="Need COI ASAP for Smith & Associates. Meeting with client tomorrow morning. Must show $2M aggregate coverage. Please expedite!",
                is_urgent=True
            )
        ]
        
        for req in mock_requests:
            requests_db[req.id] = req
    
    return {"success": True}

@app.post("/coi/monitoring/stop")
async def stop_monitoring():
    """Stop email monitoring."""
    global email_monitoring
    email_monitoring = False
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)