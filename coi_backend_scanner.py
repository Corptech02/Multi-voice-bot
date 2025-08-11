from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import base64
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PIL import Image
import pdf2image
import uuid

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
mock_requests = [
    {
        "id": "req-001",
        "from": "john.doe@company.com",
        "subject": "COI Request - ABC Construction Project",
        "timestamp": "2025-01-08T10:30:00",
        "status": "pending",
        "emailContent": """Dear United Insurance Group,

We are requesting a Certificate of Insurance for our upcoming construction project at 123 Main Street, Springfield, IL.

Please include the following coverage:
- General Liability: $2,000,000 per occurrence
- Auto Liability: $1,000,000
- Workers Compensation: Statutory limits

Certificate Holder:
ABC Construction Company
789 Business Blvd
Chicago, IL 60601

Project: Office Building Renovation
Location: 123 Main Street, Springfield, IL

Thank you,
John Doe"""
    },
    {
        "id": "req-002",
        "from": "sarah.smith@contractor.com",
        "subject": "Certificate of Insurance needed",
        "timestamp": "2025-01-08T11:15:00",
        "status": "pending",
        "emailContent": """Hi,

We need a COI for our work at the City Municipal Building.

Coverage needed:
- General Liability: $1M/$2M
- Professional Liability: $1M
- Auto: $500K

Send to:
City of Springfield
456 Government Plaza
Springfield, IL 62701

Thanks,
Sarah"""
    }
]

processed_data = {}

class ProcessRequest(BaseModel):
    requestId: str

class SendRequest(BaseModel):
    requestId: str

def generate_coi_pdf(request_data: dict) -> bytes:
    """Generate ACCORD 25 COI PDF"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, height - inch, "ACORD CERTIFICATE OF LIABILITY INSURANCE")
    
    c.setFont("Helvetica", 10)
    c.drawString(inch, height - 1.5*inch, f"DATE: {datetime.now().strftime('%m/%d/%Y')}")
    
    # Producer Section
    y_pos = height - 2*inch
    c.drawString(inch, y_pos, "PRODUCER:")
    c.drawString(inch, y_pos - 15, "United Insurance Group")
    c.drawString(inch, y_pos - 30, "123 Insurance Way")
    c.drawString(inch, y_pos - 45, "Chicago, IL 60601")
    c.drawString(inch, y_pos - 60, "Phone: (312) 555-0100")
    
    # Insured Section
    c.drawString(4*inch, y_pos, "INSURED:")
    c.drawString(4*inch, y_pos - 15, "Sample Insured Company")
    c.drawString(4*inch, y_pos - 30, "456 Business Street")
    c.drawString(4*inch, y_pos - 45, "Springfield, IL 62701")
    
    # Coverage Section
    y_pos = height - 4*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y_pos, "COVERAGES")
    
    c.setFont("Helvetica", 9)
    y_pos -= 30
    
    # Table headers
    c.drawString(inch, y_pos, "TYPE OF INSURANCE")
    c.drawString(3.5*inch, y_pos, "POLICY NUMBER")
    c.drawString(5*inch, y_pos, "POLICY EFF")
    c.drawString(6*inch, y_pos, "POLICY EXP")
    c.drawString(7*inch, y_pos, "LIMITS")
    
    # General Liability
    y_pos -= 20
    c.drawString(inch, y_pos, "GENERAL LIABILITY")
    c.drawString(3.5*inch, y_pos, "GL-123456")
    c.drawString(5*inch, y_pos, "01/01/2025")
    c.drawString(6*inch, y_pos, "01/01/2026")
    c.drawString(7*inch, y_pos, "$2,000,000")
    
    # Auto Liability
    y_pos -= 20
    c.drawString(inch, y_pos, "AUTOMOBILE LIABILITY")
    c.drawString(3.5*inch, y_pos, "AL-789012")
    c.drawString(5*inch, y_pos, "01/01/2025")
    c.drawString(6*inch, y_pos, "01/01/2026")
    c.drawString(7*inch, y_pos, "$1,000,000")
    
    # Workers Comp
    y_pos -= 20
    c.drawString(inch, y_pos, "WORKERS COMPENSATION")
    c.drawString(3.5*inch, y_pos, "WC-345678")
    c.drawString(5*inch, y_pos, "01/01/2025")
    c.drawString(6*inch, y_pos, "01/01/2026")
    c.drawString(7*inch, y_pos, "STATUTORY")
    
    # Certificate Holder
    y_pos = height - 7*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y_pos, "CERTIFICATE HOLDER:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 20
    
    # Extract certificate holder from request
    email_content = request_data.get('emailContent', '')
    if 'ABC Construction' in email_content:
        c.drawString(inch, y_pos, "ABC Construction Company")
        c.drawString(inch, y_pos - 15, "789 Business Blvd")
        c.drawString(inch, y_pos - 30, "Chicago, IL 60601")
    else:
        c.drawString(inch, y_pos, "City of Springfield")
        c.drawString(inch, y_pos - 15, "456 Government Plaza")
        c.drawString(inch, y_pos - 30, "Springfield, IL 62701")
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(inch, inch, "ACORD 25 (2016/03)")
    
    c.save()
    buffer.seek(0)
    return buffer.read()

def pdf_to_image(pdf_bytes: bytes) -> str:
    """Convert PDF to base64 image"""
    try:
        # Convert PDF to image
        images = pdf2image.convert_from_bytes(pdf_bytes, dpi=150)
        if images:
            # Convert first page to base64
            img_buffer = io.BytesIO()
            images[0].save(img_buffer, format='PNG')
            img_buffer.seek(0)
            return base64.b64encode(img_buffer.read()).decode()
    except:
        pass
    return ""

@app.get("/")
async def root():
    return {"message": "COI Tool Backend with Scanner"}

@app.get("/scanner/status")
async def scanner_status():
    return {
        "status": "active",
        "lastCheck": datetime.now().isoformat(),
        "emailCount": len(mock_requests)
    }

@app.get("/api/scanner/status")
async def api_scanner_status():
    return {
        "status": "active",
        "lastCheck": datetime.now().isoformat(),
        "emailCount": len(mock_requests)
    }

@app.get("/requests")
async def get_requests():
    return mock_requests

@app.get("/requests/{request_id}")
async def get_request(request_id: str):
    for req in mock_requests:
        if req["id"] == request_id:
            return req
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/process")
async def process_request(data: ProcessRequest):
    request_id = data.requestId
    
    # Find the request
    request_data = None
    for req in mock_requests:
        if req["id"] == request_id:
            request_data = req
            break
    
    if not request_data:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Extract details
    extracted_details = {
        "insuredName": "Sample Insured Company",
        "insuredAddress": "456 Business Street, Springfield, IL 62701",
        "coverages": [
            {"type": "General Liability", "limit": "$2,000,000 per occurrence"},
            {"type": "Automobile Liability", "limit": "$1,000,000"},
            {"type": "Workers Compensation", "limit": "Statutory"}
        ],
        "certificateHolder": "ABC Construction Company" if "ABC Construction" in request_data["emailContent"] else "City of Springfield",
        "projectInfo": "Construction Project" if "construction" in request_data["emailContent"].lower() else "Municipal Work"
    }
    
    # Generate response
    response_message = f"""Dear {request_data['from'].split('@')[0]},

Thank you for your Certificate of Insurance request. Please find the attached ACCORD 25 certificate with the following coverages:

- General Liability: $2,000,000 per occurrence
- Automobile Liability: $1,000,000
- Workers Compensation: Statutory limits

The certificate has been issued to {extracted_details['certificateHolder']} for the {extracted_details['projectInfo']}.

If you need any modifications or have questions, please let me know.

Best regards,
United Insurance Group"""
    
    # Generate COI PDF
    coi_pdf = generate_coi_pdf(request_data)
    coi_base64 = base64.b64encode(coi_pdf).decode()
    
    # Generate preview image
    coi_image = pdf_to_image(coi_pdf)
    
    # Store processed data
    processed_data[request_id] = {
        "extractedDetails": extracted_details,
        "responseMessage": response_message,
        "coiPdf": coi_base64,
        "coiImage": coi_image,
        "processed": True,
        "sent": False
    }
    
    # Update request status
    for req in mock_requests:
        if req["id"] == request_id:
            req["status"] = "processed"
    
    return {
        "success": True,
        "extractedDetails": extracted_details,
        "responseMessage": response_message,
        "coiPdf": coi_base64,
        "coiImage": coi_image
    }

@app.post("/send")
async def send_response(data: SendRequest):
    request_id = data.requestId
    
    if request_id not in processed_data:
        raise HTTPException(status_code=400, detail="Request not processed yet")
    
    # Mark as sent
    processed_data[request_id]["sent"] = True
    
    # Update request status
    for req in mock_requests:
        if req["id"] == request_id:
            req["status"] = "completed"
    
    return {
        "success": True,
        "message": "Response sent successfully"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)