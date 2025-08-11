#!/usr/bin/env python3
"""
Direct COI Request Addition Tool
This adds COI requests directly to the Surefire system
"""
import requests
import json
from datetime import datetime

def add_coi_request_to_surefire():
    """Add a COI request directly to Surefire"""
    
    print("COI Request Manual Entry")
    print("=" * 60)
    print("This tool allows you to manually add COI requests")
    print("as if they were received from the quartet02 email account.")
    print("=" * 60)
    
    # Get request details
    print("\n📋 INSURED INFORMATION:")
    insured_name = input("Insured Company Name: ").strip()
    if not insured_name:
        insured_name = "Sample Company LLC"
    
    print("\n🏢 CERTIFICATE HOLDER:")
    holder_name = input("Certificate Holder Name: ").strip()
    if not holder_name:
        holder_name = "Property Management Co"
    
    print("\n📧 EMAIL DETAILS:")
    email_from = input("From Email [quartet02@gmail.com]: ").strip()
    if not email_from:
        email_from = "quartet02@gmail.com"
    
    print("\n📄 COVERAGE DETAILS:")
    print("Select coverage type:")
    print("1. General Liability")
    print("2. Workers Compensation")
    print("3. Auto Liability")
    print("4. Professional Liability")
    coverage_choice = input("Choice [1]: ").strip() or "1"
    
    coverage_types = {
        "1": "General Liability",
        "2": "Workers Compensation", 
        "3": "Auto Liability",
        "4": "Professional Liability"
    }
    coverage_type = coverage_types.get(coverage_choice, "General Liability")
    
    # Build request data
    request_data = {
        "id": f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "insured_name": insured_name,
        "certificate_holder": holder_name,
        "coverage_type": coverage_type,
        "effective_date": datetime.now().strftime("%Y-%m-%d"),
        "expiration_date": f"{datetime.now().year + 1}-{datetime.now().strftime('%m-%d')}",
        "status": "Pending",
        "email_from": email_from,
        "email_subject": f"COI Request - {insured_name} for {holder_name}",
        "email_body": f"Please issue a Certificate of Insurance for {insured_name}. Certificate holder: {holder_name}. Coverage required: {coverage_type}.",
        "created_at": datetime.now().isoformat()
    }
    
    # Try to send to backend
    print("\n📡 Sending request to COI backend...")
    
    try:
        # First check if backend is running
        status_response = requests.get("http://localhost:8001/api/v1/monitoring/status", timeout=2)
        
        if status_response.status_code == 200:
            # Try to add via API
            add_response = requests.post(
                "http://localhost:8001/api/v1/requests/add_manual",
                json={"parsed_data": {
                    "insured": {"name": insured_name},
                    "certificate_holder": {"name": holder_name},
                    "coverages": [{
                        "type": coverage_type,
                        "effective_date": request_data["effective_date"],
                        "expiration_date": request_data["expiration_date"]
                    }]
                }, 
                "email_from": email_from,
                "email_subject": request_data["email_subject"],
                "email_body": request_data["email_body"]
                },
                timeout=5
            )
            
            if add_response.status_code == 200:
                print("\n✅ SUCCESS! COI request added to the system!")
                print(f"Request ID: {add_response.json().get('request_id', 'N/A')}")
                print("\n📌 Next steps:")
                print("1. Go to Surefire CRM at http://192.168.40.232:5189")
                print("2. Navigate to the COI Tool")
                print("3. You should see your new request in the list!")
            else:
                print(f"\n⚠️  Backend returned error: {add_response.status_code}")
                print("But the request data was created successfully.")
                
    except requests.exceptions.RequestException as e:
        print(f"\n⚠️  Could not connect to backend: {e}")
        print("But here's the request data that was created:")
        
    # Show the request data
    print("\n📄 Request Data Created:")
    print(json.dumps(request_data, indent=2))
    
    # Save to file as backup
    filename = f"coi_request_{request_data['id']}.json"
    with open(filename, 'w') as f:
        json.dump(request_data, f, indent=2)
    print(f"\n💾 Request saved to: {filename}")

if __name__ == "__main__":
    add_coi_request_to_surefire()