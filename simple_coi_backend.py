#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime
import base64
from urllib.parse import urlparse, parse_qs

class COIHandler(BaseHTTPRequestHandler):
    
    # Mock data
    email_requests = [
        {
            "id": "req_001",
            "from": "john.smith@abccontractors.com",
            "subject": "COI Request - ABC Contractors Project",
            "date": "2025-08-08T10:15:00",
            "status": "pending",
            "body": "Hi, We need a Certificate of Insurance for our upcoming project at 123 Main St. Please include General Liability and Workers Comp coverage. The certificate holder should be ABC Contractors Inc., 456 Oak Avenue, Suite 200, Chicago, IL 60601. Thanks, John Smith"
        },
        {
            "id": "req_002",
            "from": "sarah.jones@xyzrealty.com",
            "subject": "Insurance Certificate Needed - XYZ Realty",
            "date": "2025-08-08T09:30:00",
            "status": "pending",
            "body": "Good morning, Please provide a certificate of insurance for our property management contract. We need General Liability coverage with XYZ Realty LLC as additional insured. Certificate Holder: XYZ Realty LLC, 789 Pine Street, New York, NY 10001. Best regards, Sarah Jones"
        }
    ]
    
    processed_cois = {}
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/scanner/status':
            self.send_json_response({
                "status": "active",
                "lastCheck": datetime.datetime.now().isoformat(),
                "emailCount": len([r for r in self.email_requests if r['status'] == 'pending'])
            })
        
        elif path == '/emails/coi-requests':
            self.send_json_response(self.email_requests)
        
        elif path.startswith('/emails/coi-requests/'):
            request_id = path.split('/')[-1]
            request = next((r for r in self.email_requests if r['id'] == request_id), None)
            if request:
                self.send_json_response(request)
            else:
                self.send_error_response(404, "Request not found")
        
        elif path.startswith('/coi/preview/'):
            request_id = path.split('/')[-1]
            # Send mock ACCORD 25 image
            self.send_json_response({
                "image_url": f"data:image/png;base64,{self.generate_mock_accord_image()}",
                "width": 850,
                "height": 1100
            })
        
        else:
            self.send_json_response({"message": "COI Tool Backend with Scanner"})
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        if path.startswith('/coi/review/'):
            request_id = path.split('/')[-1]
            request = next((r for r in self.email_requests if r['id'] == request_id), None)
            
            if not request:
                self.send_error_response(404, "Request not found")
                return
            
            # Extract details
            extracted = {
                "insuredName": "United Insurance Group",
                "insuredAddress": "1000 Insurance Plaza, Suite 500, Chicago, IL 60601",
                "holderName": "ABC Contractors Inc." if "ABC" in request['body'] else "XYZ Realty LLC",
                "holderAddress": "456 Oak Avenue, Suite 200, Chicago, IL 60601" if "ABC" in request['body'] else "789 Pine Street, New York, NY 10001",
                "effectiveDate": "2025-08-08",
                "expirationDate": "2026-08-08",
                "coverageTypes": ["General Liability", "Workers Compensation"] if "Workers Comp" in request['body'] else ["General Liability"],
                "policyNumber": f"GL-2025-{request_id[-3:]}"
            }
            
            # Generate response
            email_response = f"""Dear {request['from'].split('@')[0].replace('.', ' ').title()},

Thank you for your Certificate of Insurance request. I've prepared the certificate as requested with the following details:

Certificate Holder: {extracted['holderName']}
Coverage Types: {', '.join(extracted['coverageTypes'])}
Policy Period: {extracted['effectiveDate']} to {extracted['expirationDate']}

The ACCORD 25 Certificate of Insurance is attached to this email. Please review and let me know if you need any modifications.

Best regards,
Insurance Service Team
United Insurance Group"""
            
            # Update status
            request['status'] = 'reviewed'
            
            # Store processed COI
            self.processed_cois[request_id] = {
                "request_id": request_id,
                "original_email": request['body'],
                "extracted_details": extracted,
                "email_response": email_response,
                "status": "reviewed"
            }
            
            self.send_json_response({
                "status": "success",
                "message": "COI reviewed successfully",
                "data": {
                    "request_id": request_id,
                    "extracted_details": extracted,
                    "email_response": email_response,
                    "pdf_base64": base64.b64encode(b"Mock PDF Content").decode(),
                    "image_preview": f"/coi/preview/{request_id}"
                }
            })
        
        elif path.startswith('/coi/send/'):
            request_id = path.split('/')[-1]
            
            if request_id not in self.processed_cois:
                self.send_error_response(404, "Processed COI not found")
                return
            
            # Update status
            for req in self.email_requests:
                if req['id'] == request_id:
                    req['status'] = 'completed'
                    break
            
            self.processed_cois[request_id]['status'] = 'sent'
            
            self.send_json_response({
                "status": "success",
                "message": "Response sent successfully",
                "sent_to": next(r['from'] for r in self.email_requests if r['id'] == request_id)
            })
        
        else:
            self.send_error_response(404, "Not found")
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode())
    
    def generate_mock_accord_image(self):
        # This would be a real ACCORD 25 image
        # For now, return a larger placeholder that looks like a form
        return """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