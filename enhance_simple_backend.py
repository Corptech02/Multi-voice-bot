#!/usr/bin/env python3
"""
Script to enhance the simple backend with mock email generation
This adds a background task that creates mock email-style requests periodically
"""

import requests
import json
import time
import threading
import random
from datetime import datetime

# Email templates
EMAIL_TEMPLATES = [
    {
        "subject": "COI Request - {vendor}",
        "body": """Dear Insurance Team,

Please provide a Certificate of Insurance for our vendor.

Vendor: {vendor}
Project: {project}
Coverage Required: General Liability - ${coverage:,}

Thank you,
{sender}"""
    },
    {
        "subject": "Certificate of Insurance Needed - {vendor}",
        "body": """Hello,

We need a COI for the following vendor:

Company: {vendor}
Job Description: {project}
Insurance Requirements: GL ${coverage:,}

Please send at your earliest convenience.

Best regards,
{sender}"""
    }
]

PROJECTS = [
    "Building Maintenance",
    "Electrical Work",
    "Plumbing Repairs", 
    "HVAC Service",
    "Landscaping Services",
    "Cleaning Services",
    "Security Installation",
    "IT Support"
]

SENDERS = [
    "John Smith",
    "Jane Doe",
    "Mike Johnson",
    "Sarah Williams",
    "David Brown"
]

def generate_mock_email_request():
    """Generate a mock email-style COI request."""
    vendors = [
        "Quick Fix Plumbing",
        "Bright Electric Co.",
        "Green Thumb Landscaping",
        "Clean Sweep Services",
        "Tech Support Plus"
    ]
    
    vendor = random.choice(vendors)
    project = random.choice(PROJECTS)
    coverage = random.choice([1000000, 2000000, 5000000])
    sender = random.choice(SENDERS)
    template = random.choice(EMAIL_TEMPLATES)
    
    email_content = template["body"].format(
        vendor=vendor,
        project=project,
        coverage=coverage,
        sender=sender
    )
    
    print(f"\n{'='*50}")
    print(f"Mock Email Generated at {datetime.now().strftime('%H:%M:%S')}")
    print(f"Subject: {template['subject'].format(vendor=vendor)}")
    print(f"From: {sender}")
    print(f"{'='*50}")
    print(email_content)
    print(f"{'='*50}")
    
    # Create the request in the backend
    create_coi_request(vendor, coverage)

def create_coi_request(vendor_name, coverage_amount):
    """Create a COI request in the backend."""
    url = "http://localhost:8001/api/v1/requests"
    
    data = {
        "vendor": vendor_name,
        "coverages": {
            "general_liability": {
                "required": coverage_amount,
                "received": 0,
                "status": "missing"
            }
        }
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Created COI request {result['id']} for {vendor_name}")
            return True
    except Exception as e:
        print(f"\n✗ Error creating request: {e}")
    return False

def mock_email_monitor():
    """Simulate email monitoring by generating requests periodically."""
    print("\n🔄 Mock email monitor started")
    print("   Will generate a new 'email' every 30-60 seconds")
    print("   Press Ctrl+C to stop\n")
    
    while True:
        # Wait random time between 30-60 seconds
        wait_time = random.randint(30, 60)
        print(f"\n⏰ Next mock email in {wait_time} seconds...")
        time.sleep(wait_time)
        
        # Generate mock email
        generate_mock_email_request()

def main():
    print("Mock Email Generator for COI Simple Backend")
    print("=" * 50)
    
    # Check backend
    try:
        response = requests.get("http://localhost:8001/")
        if response.status_code != 200:
            print("✗ Backend is not running on port 8001")
            return
        print("✓ Backend is running")
    except:
        print("✗ Cannot connect to backend on port 8001")
        return
    
    # Check monitoring status
    response = requests.get("http://localhost:8001/api/v1/requests/monitoring/status")
    if response.status_code == 200:
        status = response.json()
        print(f"✓ Monitoring active: {status['active']}")
    
    # Generate one immediate example
    print("\nGenerating example mock email...")
    generate_mock_email_request()
    
    # Start continuous monitoring
    try:
        mock_email_monitor()
    except KeyboardInterrupt:
        print("\n\n✓ Mock email monitor stopped")

if __name__ == "__main__":
    main()