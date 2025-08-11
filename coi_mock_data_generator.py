#!/usr/bin/env python3
"""
COI Mock Data Generator
Generate and populate COI requests without Gmail authentication
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests
import argparse

# Sample data for generating realistic COI requests
VENDORS = [
    "ABC Construction Inc.",
    "XYZ Electrical Services",
    "Premier Plumbing LLC",
    "SafeGuard Security Systems",
    "Metro Cleaning Services",
    "TechPro IT Solutions",
    "GreenScape Landscaping",
    "Elite HVAC Services"
]

CERTIFICATE_HOLDERS = [
    "Property Management Group LLC",
    "Citywide Development Corp",
    "Regional Mall Associates",
    "Commercial Real Estate Partners",
    "Municipal Building Authority",
    "University Campus Services",
    "Healthcare Facilities Inc",
    "Industrial Park Management"
]

PROJECTS = [
    "Office Renovation - Building A",
    "Parking Lot Maintenance",
    "HVAC System Upgrade",
    "Annual Grounds Maintenance",
    "Security System Installation",
    "Electrical Panel Upgrade",
    "Roof Repair Project",
    "IT Infrastructure Update"
]

COVERAGE_TYPES = [
    {"type": "General Liability", "limit": "$1,000,000"},
    {"type": "General Liability", "limit": "$2,000,000"},
    {"type": "Auto Liability", "limit": "$1,000,000"},
    {"type": "Workers Compensation", "limit": "Statutory"},
    {"type": "Professional Liability", "limit": "$1,000,000"},
    {"type": "Umbrella Policy", "limit": "$5,000,000"}
]

EMAIL_TEMPLATES = [
    """Dear Insurance Team,

We need a Certificate of Insurance for our upcoming project at {location}.

Insured: {vendor}
Certificate Holder: {holder}
Project: {project}
Required Coverage: {coverage}

Please send ASAP.

Best regards,
{sender}""",

    """Hello,

Please provide a COI for the following:

Vendor: {vendor}
Project Location: {location}
Certificate Holder: {holder}
Description: {project}

Coverage Requirements:
{coverage}

Additional Insured: {holder} must be named as additional insured.

Thank you,
{sender}""",

    """To Whom It May Concern:

This is a request for Certificate of Insurance documentation.

Named Insured: {vendor}
Certificate Holder: {holder}
Project Description: {project}
Location: {location}

Minimum Coverage Required:
{coverage}

Please email the certificate as soon as possible.

Sincerely,
{sender}"""
]

def generate_mock_coi_request() -> Dict[str, Any]:
    """Generate a single mock COI request."""
    vendor = random.choice(VENDORS)
    holder = random.choice(CERTIFICATE_HOLDERS)
    project = random.choice(PROJECTS)
    coverage = random.choice(COVERAGE_TYPES)
    
    # Generate random sender info
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson"]
    sender_first = random.choice(first_names)
    sender_last = random.choice(last_names)
    sender = f"{sender_first} {sender_last}"
    
    # Generate random location
    streets = ["Main Street", "Park Avenue", "Broadway", "Oak Lane", "Elm Street", "Market Street"]
    cities = ["Springfield", "Riverside", "Fairview", "Madison", "Georgetown", "Clinton"]
    states = ["IL", "NY", "CA", "TX", "FL", "PA", "OH", "MA"]
    location = f"{random.randint(100, 9999)} {random.choice(streets)}, {random.choice(cities)}, {random.choice(states)}"
    
    # Generate email content
    template = random.choice(EMAIL_TEMPLATES)
    email_content = template.format(
        vendor=vendor,
        holder=holder,
        project=project,
        coverage=f"{coverage['type']} - {coverage['limit']}",
        location=location,
        sender=sender
    )
    
    # Generate request data
    request_id = f"REQ{random.randint(1000, 9999)}"
    timestamp = datetime.now() - timedelta(hours=random.randint(0, 72))
    
    return {
        "id": request_id,
        "timestamp": timestamp.isoformat(),
        "from_email": f"{sender_first.lower()}.{sender_last.lower()}@{holder.lower().replace(' ', '').replace(',', '').replace('.', '')}.com",
        "subject": f"Certificate of Insurance Request - {vendor}",
        "original_text": email_content,
        "certificate_holder": holder,
        "insured_name": vendor,
        "project_description": f"{project} at {location}",
        "coverage_requirements": f"{coverage['type']} - {coverage['limit']}",
        "additional_insureds": [holder] if random.random() > 0.5 else [],
        "status": random.choice(["Pending", "In Progress", "Pending"]),  # More Pending
        "preview_content": None,
        "ai_confidence": round(random.uniform(0.75, 0.98), 2)
    }

def populate_coi_backend(base_url: str, count: int = 5) -> bool:
    """Populate the COI backend with mock requests."""
    try:
        # Check if backend is running (try root endpoint)
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            print("Backend connection check failed")
            return False
        
        print(f"Connected to COI backend at {base_url}")
        
        # Generate and send mock requests
        successful = 0
        for i in range(count):
            mock_request = generate_mock_coi_request()
            
            # Send to backend
            response = requests.post(
                f"{base_url}/api/v1/requests",
                json={
                    "vendor": mock_request["insured_name"],
                    "coverages": {
                        "general_liability": {
                            "required": 1000000,
                            "received": 0,
                            "status": "missing"
                        }
                    }
                }
            )
            
            if response.status_code == 200:
                successful += 1
                print(f"✓ Created request {i+1}/{count}: {mock_request['id']} - {mock_request['vendor']}")
            else:
                print(f"✗ Failed to create request {i+1}: {response.text}")
        
        print(f"\nSuccessfully created {successful}/{count} mock COI requests")
        return successful > 0
        
    except requests.exceptions.ConnectionError:
        print(f"Cannot connect to backend at {base_url}")
        print("Make sure the COI backend is running (python coi_backend_simple.py)")
        return False
    except Exception as e:
        print(f"Error populating backend: {e}")
        return False

def save_mock_data_to_file(filename: str, count: int = 10):
    """Save mock COI requests to a JSON file."""
    mock_requests = [generate_mock_coi_request() for _ in range(count)]
    
    with open(filename, 'w') as f:
        json.dump(mock_requests, f, indent=2)
    
    print(f"Saved {count} mock COI requests to {filename}")
    return mock_requests

def main():
    parser = argparse.ArgumentParser(description="Generate mock COI requests")
    parser.add_argument("--count", type=int, default=5, help="Number of requests to generate")
    parser.add_argument("--backend-url", default="http://localhost:8001", help="COI backend URL")
    parser.add_argument("--save-file", help="Save mock data to JSON file")
    parser.add_argument("--populate", action="store_true", help="Populate backend with mock data")
    
    args = parser.parse_args()
    
    if args.save_file:
        save_mock_data_to_file(args.save_file, args.count)
    
    if args.populate:
        populate_coi_backend(args.backend_url, args.count)
    
    if not args.save_file and not args.populate:
        # Just print a sample
        print("Sample mock COI request:")
        print(json.dumps(generate_mock_coi_request(), indent=2))
        print("\nUse --populate to send to backend or --save-file to save to file")

if __name__ == "__main__":
    main()