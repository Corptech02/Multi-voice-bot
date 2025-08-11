from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime, timedelta
from pathlib import Path
import base64
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

app = FastAPI(title="COI Tool Backend with Scanner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class EmailRequest(BaseModel):
    id: str
    from_email: str
    subject: str
    date: str
    status: str
    body: Optional[str] = None

class COIDetails(BaseModel):
    insuredName: str
    insuredAddress: str
    holderName: str
    holderAddress: str
    effectiveDate: str
    expirationDate: str
    coverageTypes: List[str]
    policyNumber: str

class ProcessedCOI(BaseModel):
    request_id: str
    original_email: str
    extracted_details: COIDetails
    email_response: str
    coi_pdf_path: str
    status: str

# Mock data storage
email_requests = [
    EmailRequest(
        id="req_001",
        from_email="john.smith@abccontractors.com",
        subject="COI Request - ABC Contractors Project",
        date="2025-08-08T10:15:00",
        status="pending",
        body="Hi, We need a Certificate of Insurance for our upcoming project at 123 Main St. Please include General Liability and Workers Comp coverage. The certificate holder should be ABC Contractors Inc., 456 Oak Avenue, Suite 200, Chicago, IL 60601. Thanks, John Smith"
    ),
    EmailRequest(
        id="req_002",
        from_email="sarah.jones@xyzrealty.com",
        subject="Insurance Certificate Needed - XYZ Realty",
        date="2025-08-08T09:30:00",
        status="pending",
        body="Good morning, Please provide a certificate of insurance for our property management contract. We need to see General Liability coverage with XYZ Realty LLC as additional insured. Certificate Holder: XYZ Realty LLC, 789 Pine Street, New York, NY 10001. Best regards, Sarah Jones"
    )
]

processed_cois = {}

# Scanner status
scanner_status = {
    "status": "active",
    "lastCheck": datetime.now().isoformat(),
    "emailCount": len(email_requests)
}

@app.get("/")
def root():
    return {"message": "COI Tool Backend with Scanner"}

@app.get("/scanner/status")
def get_scanner_status():
    scanner_status["lastCheck"] = datetime.now().isoformat()
    scanner_status["emailCount"] = len([req for req in email_requests if req.status == "pending"])
    return scanner_status

@app.get("/emails/coi-requests", response_model=List[EmailRequest])
def get_coi_requests():
    return email_requests

@app.get("/emails/coi-requests/{request_id}", response_model=EmailRequest)
def get_coi_request(request_id: str):
    for req in email_requests:
        if req.id == request_id:
            return req
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/coi/review/{request_id}")
def review_coi_request(request_id: str):
    # Find the request
    request = None
    for req in email_requests:
        if req.id == request_id:
            request = req
            break
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Extract details from the email
    extracted = COIDetails(
        insuredName="United Insurance Group",
        insuredAddress="1000 Insurance Plaza, Suite 500, Chicago, IL 60601",
        holderName="ABC Contractors Inc." if "ABC" in request.body else "XYZ Realty LLC",
        holderAddress="456 Oak Avenue, Suite 200, Chicago, IL 60601" if "ABC" in request.body else "789 Pine Street, New York, NY 10001",
        effectiveDate="2025-08-08",
        expirationDate="2026-08-08",
        coverageTypes=["General Liability", "Workers Compensation"] if "Workers Comp" in request.body else ["General Liability"],
        policyNumber=f"GL-2025-{random.randint(100000, 999999)}"
    )
    
    # Generate email response
    email_response = f"""Dear {request.from_email.split('@')[0].replace('.', ' ').title()},

Thank you for your Certificate of Insurance request. I've prepared the certificate as requested with the following details:

Certificate Holder: {extracted.holderName}
Coverage Types: {', '.join(extracted.coverageTypes)}
Policy Period: {extracted.effectiveDate} to {extracted.expirationDate}

The ACCORD 25 Certificate of Insurance is attached to this email. Please review and let me know if you need any modifications.

Best regards,
Insurance Service Team
United Insurance Group"""
    
    # Create the PDF (mock)
    pdf_content = b"Mock PDF Content for ACCORD 25 Certificate"
    pdf_base64 = base64.b64encode(pdf_content).decode()
    
    # Store the processed COI
    processed = ProcessedCOI(
        request_id=request_id,
        original_email=request.body,
        extracted_details=extracted,
        email_response=email_response,
        coi_pdf_path=f"/coi/pdf/{request_id}",
        status="reviewed"
    )
    
    processed_cois[request_id] = processed
    
    # Update request status
    request.status = "reviewed"
    
    return {
        "status": "success",
        "message": "COI reviewed successfully",
        "data": {
            "request_id": request_id,
            "extracted_details": extracted.dict(),
            "email_response": email_response,
            "pdf_base64": pdf_base64,
            "image_preview": f"/coi/preview/{request_id}"
        }
    }

@app.post("/coi/send/{request_id}")
def send_coi_response(request_id: str):
    if request_id not in processed_cois:
        raise HTTPException(status_code=404, detail="Processed COI not found")
    
    processed = processed_cois[request_id]
    
    # Update status
    for req in email_requests:
        if req.id == request_id:
            req.status = "completed"
            break
    
    processed.status = "sent"
    
    return {
        "status": "success",
        "message": "Response sent successfully",
        "sent_to": next(req.from_email for req in email_requests if req.id == request_id)
    }

@app.get("/coi/preview/{request_id}")
def get_coi_preview(request_id: str):
    # Return a mock image preview
    return {
        "image_url": f"data:image/png;base64,{generate_mock_accord_image()}",
        "width": 850,
        "height": 1100
    }

def generate_mock_accord_image():
    # This would normally convert PDF to image
    # For now, return a simple base64 encoded placeholder
    mock_image = """iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="""
    return mock_image

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)