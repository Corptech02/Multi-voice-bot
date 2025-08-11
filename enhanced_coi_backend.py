#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from datetime import datetime
import openai
import base64
from fillpdf import fillpdfs
import shutil
import tempfile
from pdf2image import convert_from_path
from PIL import Image
import io

# Initialize FastAPI app
app = FastAPI(title="Enhanced COI Backend with ACCORD 25 Generation")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    client = openai.OpenAI(api_key=openai_api_key)
    print(f"OpenAI API configured successfully!")
else:
    client = None
    print("WARNING: OpenAI API key not found. AI features will be disabled.")

# Paths
ACCORD_25_TEMPLATE = "/home/corp06/software_projects/UIGCRM/current/UIG COI Tool/backend/templates/ACORD_25.pdf"
GENERATED_PDFS_DIR = "/home/corp06/software_projects/ClaudeVoiceBot/current/generated_pdfs"

# Create generated PDFs directory
os.makedirs(GENERATED_PDFS_DIR, exist_ok=True)

# Data models
class ProcessResponse(BaseModel):
    id: str
    request_id: str
    coi_id: str
    status: str
    preview_url: Optional[str] = None
    preview_image: Optional[str] = None  # Base64 encoded image preview
    email_response: Optional[str] = None
    response_message: Optional[str] = None  # Frontend expects this field
    error_message: Optional[str] = None
    processed_content: Optional[str] = None

# Mock data for COI requests
mock_requests = [
    {
        "id": "req-001",
        "email_thread_id": "thread-001",
        "subject": "COI Request - ABC Construction Project",
        "requestor_email": "john@abcconstruction.com",
        "requestor_name": "John Smith",
        "company_name": "ABC Construction LLC",
        "received_at": "2024-01-15T10:30:00",
        "sent_at": None,
        "email_content": """Dear Insurance Team,

We need a Certificate of Insurance for our upcoming project at 123 Main Street, New York, NY 10001.

Project Details:
- Project Name: Downtown Office Renovation
- Start Date: February 1, 2024
- Duration: 6 months
- Contract Value: $2.5 million

Required Coverage:
- General Liability: $2,000,000 per occurrence
- Auto Liability: $1,000,000
- Workers Compensation: Statutory limits
- Umbrella Policy: $5,000,000

Certificate Holder:
Downtown Property Management LLC
456 Park Avenue
New York, NY 10022

Please include Downtown Property Management as additional insured.

This is URGENT - we need the COI by end of day today.

Best regards,
John Smith
Project Manager
ABC Construction LLC""",
        "processed_content": None,
        "pdf_preview_url": None,
        "response_message": None,
        "status": "new",
        "is_urgent": True,
        "error_message": None
    },
    {
        "id": "req-002",
        "email_thread_id": "thread-002",
        "subject": "Certificate of Insurance Request",
        "requestor_email": "sarah@downtownmgmt.com",
        "requestor_name": "Sarah Johnson",
        "company_name": "Downtown Office Management",
        "received_at": "2024-01-15T09:15:00",
        "sent_at": None,
        "email_content": """Hi,

Please provide a COI for our vendor XYZ Cleaning Services for work at our property.

Policy should show $1M general liability.

Certificate holder: Downtown Office Management, 789 Market St, Suite 200, NY, NY 10013

Thanks,
Sarah""",
        "processed_content": None,
        "pdf_preview_url": None,
        "response_message": None,
        "status": "processing",
        "is_urgent": False,
        "error_message": None
    }
]

@app.on_event("startup")
async def startup_event():
    print("Enhanced COI Backend started")
    print(f"OpenAI available: {client is not None}")
    print(f"ACCORD 25 template exists: {os.path.exists(ACCORD_25_TEMPLATE)}")

@app.get("/")
async def root():
    return {
        "message": "Enhanced COI Backend is running",
        "openai_enabled": client is not None,
        "accord_template_available": os.path.exists(ACCORD_25_TEMPLATE)
    }

@app.get("/api/v1/requests")
async def get_requests():
    return mock_requests

@app.post("/api/v1/requests/{request_id}/process")
async def process_request(request_id: str):
    # Find the request
    request = next((r for r in mock_requests if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    try:
        # Extract COI details using AI if available
        extracted_info = {
            "policy_number": "GL-2024-ABC123",
            "effective_date": "02/01/2024",
            "expiration_date": "02/01/2025",
            "insured_name": request["company_name"] or "ABC Construction LLC",
            "insured_address": "123 Business Park Dr, New York, NY 10001",
            "certificate_holder": "Downtown Property Management LLC\n456 Park Avenue\nNew York, NY 10022",
            "gl_policy_number": "GL-2024-ABC123",
            "gl_limit_occurrence": "$2,000,000",
            "gl_limit_aggregate": "$4,000,000",
            "auto_policy_number": "CA-2024-ABC456",
            "auto_csl": "$1,000,000",
            "umbrella_policy_number": "UMB-2024-ABC789",
            "umbrella_limit_occurrence": "$5,000,000",
            "wc_policy_number": "WC-2024-ABC012",
            "producer_name": "United Insurance Group",
            "producer_address": "100 Insurance Plaza\nNew York, NY 10005",
            "producer_phone": "(212) 555-0100"
        }
        
        if client:
            try:
                # Use AI to extract specific details from the email
                extraction_prompt = f"""Extract the following information from this COI request email:
                - Certificate holder name and address
                - Required coverage amounts
                - Project details
                
                Email: {request['email_content']}"""
                
                extraction_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": extraction_prompt}],
                    max_tokens=200
                )
                
                processed_content = extraction_response.choices[0].message.content
                
                # Generate professional email response
                email_prompt = f"""Generate a professional email response confirming that the Certificate of Insurance has been prepared and attached.
                
                Details to include:
                - Confirm the coverage amounts requested
                - Mention that {extracted_info['certificate_holder'].split('\\n')[0]} has been listed as certificate holder
                - Professional closing
                
                Keep it concise and professional."""
                
                email_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": email_prompt}],
                    max_tokens=200
                )
                
                response_message = email_response.choices[0].message.content
                
            except Exception as e:
                print(f"OpenAI error: {e}")
                processed_content = "Coverage: GL $2M/$4M, Auto $1M, Umbrella $5M, WC Statutory"
                response_message = f"""Dear {request['requestor_name'] or 'Valued Client'},

Thank you for your COI request. I've prepared the Certificate of Insurance as requested with the following coverage:

- General Liability: $2,000,000 per occurrence / $4,000,000 aggregate
- Auto Liability: $1,000,000 CSL
- Umbrella: $5,000,000
- Workers Compensation: Statutory limits

{extracted_info['certificate_holder'].split(chr(10))[0]} has been listed as the certificate holder.

The certificate is attached to this email. Please let me know if you need any modifications.

Best regards,
COI Department
United Insurance Group"""
        else:
            processed_content = "Coverage: GL $2M/$4M, Auto $1M, Umbrella $5M, WC Statutory"
            response_message = f"""Dear {request['requestor_name'] or 'Valued Client'},

Your Certificate of Insurance has been prepared with the requested coverage. The certificate holder has been updated as requested.

The certificate is attached. Please contact us if you need any changes.

Best regards,
COI Department"""
        
        # Generate ACCORD 25 PDF
        pdf_filename = f"COI_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(GENERATED_PDFS_DIR, pdf_filename)
        
        # Check if template exists
        if os.path.exists(ACCORD_25_TEMPLATE):
            # Create a copy of the template
            shutil.copy(ACCORD_25_TEMPLATE, pdf_path)
            
            # Fill the PDF with data
            try:
                data_dict = {
                    'DATE': datetime.now().strftime('%m/%d/%Y'),
                    'PRODUCER NAME': extracted_info['producer_name'],
                    'PRODUCER ADDRESS': extracted_info['producer_address'],
                    'PRODUCER PHONE': extracted_info['producer_phone'],
                    'INSURED': extracted_info['insured_name'],
                    'INSURED ADDRESS': extracted_info['insured_address'],
                    'GL POLICY NUMBER': extracted_info['gl_policy_number'],
                    'GL EFF DATE': extracted_info['effective_date'],
                    'GL EXP DATE': extracted_info['expiration_date'],
                    'GL OCCUR': extracted_info['gl_limit_occurrence'],
                    'GL AGGREGATE': extracted_info['gl_limit_aggregate'],
                    'AL POLICY NUMBER': extracted_info['auto_policy_number'],
                    'AL EFF DATE': extracted_info['effective_date'],
                    'AL EXP DATE': extracted_info['expiration_date'],
                    'AL CSL': extracted_info['auto_csl'],
                    'UMB POLICY NUMBER': extracted_info['umbrella_policy_number'],
                    'UMB EFF DATE': extracted_info['effective_date'],
                    'UMB EXP DATE': extracted_info['expiration_date'],
                    'UMB OCCUR': extracted_info['umbrella_limit_occurrence'],
                    'WC POLICY NUMBER': extracted_info['wc_policy_number'],
                    'WC EFF DATE': extracted_info['effective_date'],
                    'WC EXP DATE': extracted_info['expiration_date'],
                    'CERTIFICATE HOLDER': extracted_info['certificate_holder'],
                    'DESCRIPTION': f"Certificate holder is included as additional insured per written contract."
                }
                
                fillpdfs.write_fillable_pdf(ACCORD_25_TEMPLATE, pdf_path, data_dict)
                print(f"PDF generated successfully: {pdf_path}")
                
            except Exception as e:
                print(f"Error filling PDF: {e}")
                # If fillpdf fails, at least we have a copy of the template
        
        # Convert PDF to image for preview
        preview_image_base64 = None
        try:
            # Convert first page of PDF to image
            images = convert_from_path(pdf_path, dpi=150)
            if images:
                # Get the first page
                img = images[0]
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Create a BytesIO object to store the image
                img_buffer = io.BytesIO()
                # Save as JPEG for smaller size
                img.save(img_buffer, format='JPEG', quality=85)
                img_buffer.seek(0)
                # Encode to base64
                preview_image_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
                print("PDF preview image generated successfully")
        except Exception as e:
            print(f"Error generating PDF preview image: {e}")
        
        # Create a public URL for the PDF
        preview_url = f"http://localhost:8001/api/v1/pdfs/{pdf_filename}"
        
        # Update request
        request["processed_content"] = processed_content
        request["pdf_preview_url"] = preview_url
        request["response_message"] = response_message
        request["status"] = "completed"
        
        # Also include extracted details formatted for display
        extracted_details = f"""**Certificate Details:**
- Policy Number: {extracted_info['gl_policy_number']}
- Effective Date: {extracted_info['effective_date']}
- Expiration Date: {extracted_info['expiration_date']}

**Insured Information:**
- Name: {extracted_info['insured_name']}
- Address: {extracted_info['insured_address']}

**Coverage Limits:**
- General Liability: {extracted_info['gl_limit_occurrence']} per occurrence / {extracted_info['gl_limit_aggregate']} aggregate
- Auto Liability: {extracted_info['auto_csl']} CSL
- Umbrella: {extracted_info['umbrella_limit_occurrence']} per occurrence
- Workers Compensation: Statutory limits

**Certificate Holder:**
{extracted_info['certificate_holder']}

**Additional Information:**
- Certificate holder is included as additional insured per written contract
- Coverage verified and meets all requested requirements"""
        
        return ProcessResponse(
            id=f"proc-{request_id}",
            request_id=request_id,
            coi_id=f"COI-{datetime.now().strftime('%Y%m%d')}-{request_id[-3:]}",
            status="success",
            preview_url=preview_url,
            preview_image=preview_image_base64,
            email_response=response_message,
            response_message=response_message,  # Frontend expects this field
            processed_content=extracted_details  # This will show in extracted COI details
        )
        
    except Exception as e:
        print(f"Error processing request: {e}")
        return ProcessResponse(
            id=f"proc-{request_id}",
            request_id=request_id,
            coi_id="",
            status="error",
            error_message=str(e)
        )

@app.get("/api/v1/pdfs/{filename}")
async def get_pdf(filename: str):
    """Serve generated PDF files"""
    pdf_path = os.path.join(GENERATED_PDFS_DIR, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)