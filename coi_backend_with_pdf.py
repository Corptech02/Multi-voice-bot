"""
Enhanced COI Backend with PDF Generation and Monitoring
Combines monitoring features with real PDF generation
"""
import os
import io
import base64
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, HexColor
import fitz  # PyMuPDF
from PIL import Image
import uvicorn

app = FastAPI(
    title="Insurance COI Automation API with PDF",
    description="COI API with real PDF generation and monitoring",
    version="3.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for monitoring and requests
monitoring_active = False
email_requests = []
monitoring_task = None
generated_pdfs = {}  # Store generated PDFs in memory

# Ensure directories exist
os.makedirs("generated_pdfs", exist_ok=True)
os.makedirs("pdf_previews", exist_ok=True)

def generate_accord_25_pdf(request_data: dict) -> tuple[bytes, str]:
    """Generate ACCORD 25 Certificate of Liability Insurance PDF"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, height - inch, "ACORD CERTIFICATE OF LIABILITY INSURANCE")
    
    c.setFont("Helvetica", 10)
    c.drawString(inch * 7, height - inch, f"DATE (MM/DD/YYYY)")
    c.drawString(inch * 7, height - inch - 15, datetime.now().strftime("%m/%d/%Y"))
    
    # Producer section
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, height - inch - 40, "PRODUCER")
    c.setFont("Helvetica", 9)
    c.drawString(inch, height - inch - 55, "United Insurance Group")
    c.drawString(inch, height - inch - 70, "123 Insurance Way")
    c.drawString(inch, height - inch - 85, "New York, NY 10001")
    c.drawString(inch, height - inch - 100, "Phone: (555) 123-4567")
    
    # Insured section
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch * 4, height - inch - 40, "INSURED")
    c.setFont("Helvetica", 9)
    
    company_name = request_data.get("company_name", "Company Name Not Provided")
    c.drawString(inch * 4, height - inch - 55, company_name)
    c.drawString(inch * 4, height - inch - 70, "123 Business Street")
    c.drawString(inch * 4, height - inch - 85, "City, State 12345")
    
    # Coverage section header
    y_position = height - inch - 140
    c.setFont("Helvetica-Bold", 9)
    c.drawString(inch, y_position, "COVERAGES")
    c.setFont("Helvetica", 8)
    c.drawString(inch, y_position - 15, "CERTIFICATE NUMBER: " + request_data.get("id", "COI-001"))
    
    # Draw coverage grid
    y_position -= 40
    c.setFont("Helvetica-Bold", 8)
    c.drawString(inch, y_position, "TYPE OF INSURANCE")
    c.drawString(inch * 3, y_position, "POLICY NUMBER")
    c.drawString(inch * 4.5, y_position, "POLICY EFF")
    c.drawString(inch * 5.5, y_position, "POLICY EXP")
    c.drawString(inch * 6.5, y_position, "LIMITS")
    
    # Coverage lines
    y_position -= 20
    c.setFont("Helvetica", 8)
    
    # General Liability
    c.drawString(inch + 10, y_position, "GENERAL LIABILITY")
    c.drawString(inch * 3, y_position, "GL-2024-001")
    c.drawString(inch * 4.5, y_position, "01/01/2024")
    c.drawString(inch * 5.5, y_position, "01/01/2025")
    c.drawString(inch * 6.5, y_position, "$2,000,000")
    
    # Workers Comp
    y_position -= 20
    c.drawString(inch + 10, y_position, "WORKERS COMPENSATION")
    c.drawString(inch * 3, y_position, "WC-2024-001")
    c.drawString(inch * 4.5, y_position, "01/01/2024")
    c.drawString(inch * 5.5, y_position, "01/01/2025")
    c.drawString(inch * 6.5, y_position, "$1,000,000")
    
    # Certificate Holder section
    y_position = height - inch - 400
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y_position, "CERTIFICATE HOLDER")
    c.setFont("Helvetica", 9)
    
    requestor = request_data.get("requestor_email", "").split('@')[0].replace('.', ' ').title()
    c.drawString(inch, y_position - 20, requestor)
    c.drawString(inch, y_position - 35, request_data.get("company_name", "Company Name"))
    c.drawString(inch, y_position - 50, "Address Line 1")
    c.drawString(inch, y_position - 65, "City, State 12345")
    
    # Footer
    c.setFont("Helvetica", 7)
    c.drawString(inch, inch, "ACORD 25 (2016/03)")
    c.drawString(inch * 6, inch, "© 1988-2015 ACORD CORPORATION. All rights reserved.")
    
    c.save()
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    
    # Save to file
    filename = f"COI_{request_data.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("generated_pdfs", filename)
    with open(filepath, 'wb') as f:
        f.write(pdf_bytes)
    
    return pdf_bytes, filename

def pdf_to_image(pdf_bytes: bytes) -> str:
    """Convert PDF to base64 encoded image"""
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = pdf_document[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
    img_data = pix.tobytes("png")
    pdf_document.close()
    
    # Convert to base64
    return base64.b64encode(img_data).decode('utf-8')

# Initialize with some sample requests
def initialize_requests():
    global email_requests
    email_requests = [
        {
            "id": "coi-001",
            "subject": "COI Request - ABC Construction Project",
            "requestor_email": "john.smith@abcconstruction.com",
            "company_name": "ABC Construction LLC",
            "email_content": "Hello,\n\nWe need a Certificate of Insurance for our upcoming project at 123 Main Street. Please provide general liability coverage of $2M and workers comp.\n\nProject dates: March 1-30, 2025\nThank you!",
            "received_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "status": "new",
            "is_urgent": True,
            "sent_at": None,
            "error_message": None,
            "email_thread_id": "thread-001",
            "extracted_data": {
                "coverage_type": "General Liability & Workers Comp",
                "liability_limit": "$2,000,000",
                "project_location": "123 Main Street",
                "project_dates": "March 1-30, 2025"
            }
        },
        {
            "id": "coi-002", 
            "subject": "Certificate of Insurance Needed - Downtown Office",
            "requestor_email": "sarah.johnson@officemgmt.com",
            "company_name": "Downtown Office Management",
            "email_content": "Hi there,\n\nWe require a COI for our tenant insurance requirements. Need to show:\n- General Liability: $1M\n- Property coverage\n- Additional insured: Downtown Office Management\n\nLease starts April 1st.\n\nBest regards,\nSarah",
            "received_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "status": "processing",
            "is_urgent": False,
            "sent_at": None,
            "error_message": None,
            "email_thread_id": "thread-002",
            "extracted_data": {
                "coverage_type": "General Liability & Property",
                "liability_limit": "$1,000,000",
                "additional_insured": "Downtown Office Management",
                "lease_start": "April 1st"
            }
        }
    ]

# Monitoring endpoints
@app.get("/api/v1/requests/monitoring/status")
async def get_monitoring_status():
    return {"status": "active" if monitoring_active else "inactive"}

@app.post("/api/v1/requests/monitoring/start")
async def start_monitoring():
    global monitoring_active, monitoring_task
    if not monitoring_active:
        monitoring_active = True
        monitoring_task = asyncio.create_task(simulate_email_monitoring())
    return {"status": "started"}

@app.post("/api/v1/requests/monitoring/stop")
async def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    return {"status": "stopped"}

# Email requests endpoints
@app.get("/emails/coi-requests")
async def get_all_requests():
    return email_requests

@app.get("/emails/coi-requests/{request_id}")
async def get_request(request_id: str):
    for req in email_requests:
        if req["id"] == request_id:
            return req
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/api/v1/requests/{request_id}/process")
async def process_request(request_id: str):
    """Process a request and generate COI"""
    for req in email_requests:
        if req["id"] == request_id:
            # Generate PDF
            pdf_bytes, filename = generate_accord_25_pdf(req)
            
            # Convert to image
            image_base64 = pdf_to_image(pdf_bytes)
            
            # Store in memory
            generated_pdfs[filename] = pdf_bytes
            
            # Update request
            req["status"] = "ready_for_review"
            req["processed_at"] = datetime.now().isoformat()
            req["pdf_filename"] = filename
            req["processed_content"] = f"Extracted details:\n" + "\n".join([f"- {k}: {v}" for k, v in req.get("extracted_data", {}).items()])
            
            # Generate response message
            response_message = f"""Dear {req['requestor_email'].split('@')[0]},

Thank you for your COI request. Please find attached the Certificate of Liability Insurance for {req['company_name']}.

The certificate includes:
- General Liability Coverage: $2,000,000
- Workers Compensation: $1,000,000
- Policy Period: 01/01/2024 - 01/01/2025

If you need any modifications or have questions, please let us know.

Best regards,
United Insurance Group"""
            
            return {
                "status": "success",
                "preview_url": f"http://localhost:8001/api/v1/preview/{filename}",
                "preview_image": f"data:image/png;base64,{image_base64}",
                "response_message": response_message,
                "processed_content": req["processed_content"]
            }
    
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/api/v1/requests/{request_id}/send")
async def send_request(request_id: str):
    # Update request status
    for req in email_requests:
        if req["id"] == request_id:
            req["status"] = "completed"
            req["sent_at"] = datetime.now().isoformat()
            return {"status": "success", "message": "Response sent"}
    
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/api/v1/requests/{request_id}/archive")
async def archive_request(request_id: str):
    global email_requests
    for req in email_requests:
        if req["id"] == request_id:
            req["status"] = "archived"
            return {"status": "success", "message": "Request archived"}
    raise HTTPException(status_code=404, detail="Request not found")

# PDF preview endpoint
@app.get("/api/v1/preview/{filename}")
async def get_pdf_preview(filename: str):
    """Return actual PDF file"""
    # Check memory first
    if filename in generated_pdfs:
        return StreamingResponse(
            io.BytesIO(generated_pdfs[filename]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    # Check file system
    filepath = os.path.join("generated_pdfs", filename)
    if os.path.exists(filepath):
        return FileResponse(
            filepath,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    raise HTTPException(status_code=404, detail="PDF not found")

# Background task to simulate new emails
async def simulate_email_monitoring():
    """Simulate receiving new COI requests periodically"""
    global email_requests, monitoring_active
    
    while monitoring_active:
        await asyncio.sleep(random.randint(30, 60))
        
        if monitoring_active and random.random() > 0.3:
            companies = ["XYZ Corp", "Tech Solutions Inc", "Green Energy LLC", "City Municipality", "Regional Hospital"]
            company = random.choice(companies)
            
            new_request = {
                "id": f"coi-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "subject": f"COI Request - {company}",
                "requestor_email": f"contact@{company.lower().replace(' ', '')}.com",
                "company_name": company,
                "email_content": f"Please provide Certificate of Insurance showing General Liability and Workers Comp coverage.",
                "received_at": datetime.now().isoformat(),
                "status": "new",
                "is_urgent": random.random() > 0.7,
                "sent_at": None,
                "error_message": None,
                "email_thread_id": f"thread-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "extracted_data": {
                    "coverage_type": "General Liability & Workers Comp",
                    "liability_limit": "$2,000,000"
                }
            }
            email_requests.insert(0, new_request)

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    initialize_requests()
    print("Enhanced COI Backend with PDF Generation initialized")

if __name__ == "__main__":
    print("Starting Enhanced COI Backend with PDF Generation on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)