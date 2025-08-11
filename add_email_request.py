#!/usr/bin/env python3
"""
Manual email request addition tool for COI Tool
This allows you to manually add COI requests as if they came from email
"""
import requests
import json
from datetime import datetime

def add_coi_request():
    """Add a manual COI request to the system"""
    
    print("Add COI Request to the System")
    print("-" * 50)
    
    # Get request details from user
    insured_name = input("Insured Name (e.g., ABC Company): ").strip()
    certificate_holder = input("Certificate Holder (e.g., XYZ Property Management): ").strip()
    email_from = input("Email From (e.g., john@abccompany.com): ").strip() or "quartet02@example.com"
    
    # Policy details
    print("\nPolicy Details (press Enter for defaults):")
    policy_type = input("Policy Type [General Liability]: ").strip() or "General Liability"
    policy_number = input("Policy Number [GL-2024-001]: ").strip() or "GL-2024-001"
    effective_date = input("Effective Date [2024-01-01]: ").strip() or "2024-01-01"
    expiration_date = input("Expiration Date [2025-01-01]: ").strip() or "2025-01-01"
    
    # Coverage limits
    print("\nCoverage Limits (press Enter for defaults):")
    each_occurrence = input("Each Occurrence [$1,000,000]: ").strip() or "$1,000,000"
    general_aggregate = input("General Aggregate [$2,000,000]: ").strip() or "$2,000,000"
    
    # Additional requirements
    additional_insured = input("\nAdditional Insured Required? (y/n) [n]: ").strip().lower() == 'y'
    waiver_of_subrogation = input("Waiver of Subrogation Required? (y/n) [n]: ").strip().lower() == 'y'
    
    # Build the request data
    request_data = {
        "email_from": email_from,
        "email_subject": f"COI Request - {insured_name} for {certificate_holder}",
        "email_body": f"Please issue a Certificate of Insurance for {insured_name}",
        "parsed_data": {
            "insured": {
                "name": insured_name,
                "address": "123 Main Street, City, State 12345"
            },
            "certificate_holder": {
                "name": certificate_holder,
                "address": "456 Property Lane, City, State 12345"
            },
            "coverages": [
                {
                    "type": policy_type,
                    "policy_number": policy_number,
                    "effective_date": effective_date,
                    "expiration_date": expiration_date,
                    "limits": {
                        "each_occurrence": each_occurrence,
                        "general_aggregate": general_aggregate
                    }
                }
            ],
            "additional_insured": additional_insured,
            "waiver_of_subrogation": waiver_of_subrogation
        }
    }
    
    # Send to API
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/requests/add_manual",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ COI Request added successfully!")
            print(f"Request ID: {result['request_id']}")
            print("\nYou can now see this request in the Surefire CRM COI Tool!")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to COI backend on port 8001")
        print("Make sure the COI backend is running.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    add_coi_request()