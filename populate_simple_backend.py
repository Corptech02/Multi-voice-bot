#!/usr/bin/env python3
"""
Simple script to populate the COI simple backend with test data
"""

import requests
import json
import random
from datetime import datetime

# Sample vendors
VENDORS = [
    "ABC Construction Inc.",
    "XYZ Electrical Services", 
    "Premier Plumbing LLC",
    "SafeGuard Security Systems",
    "Metro Cleaning Services",
    "TechPro IT Solutions",
    "GreenScape Landscaping",
    "Elite HVAC Services",
    "Quality Roofing Co.",
    "ProPaint Services LLC"
]

def create_coi_request(vendor_name):
    """Create a COI request for the simple backend."""
    url = "http://localhost:8001/api/v1/requests"
    
    data = {
        "vendor": vendor_name,
        "coverages": {
            "general_liability": {
                "required": random.choice([1000000, 2000000, 5000000]),
                "received": 0,
                "status": "missing"
            }
        }
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Created request {result['id']} for {vendor_name}")
            return True
        else:
            print(f"✗ Failed to create request for {vendor_name}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("Populating COI Simple Backend with Test Data")
    print("=" * 50)
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:8001/")
        if response.status_code != 200:
            print("✗ Backend is not running on port 8001")
            return
        print("✓ Backend is running")
    except:
        print("✗ Cannot connect to backend on port 8001")
        return
    
    # Get current requests
    response = requests.get("http://localhost:8001/api/v1/requests")
    current_count = len(response.json()) if response.status_code == 200 else 0
    print(f"✓ Current requests: {current_count}")
    
    # Create new requests
    print("\nCreating new COI requests...")
    created = 0
    for vendor in random.sample(VENDORS, min(5, len(VENDORS))):
        if create_coi_request(vendor):
            created += 1
    
    # Show final count
    response = requests.get("http://localhost:8001/api/v1/requests")
    final_count = len(response.json()) if response.status_code == 200 else 0
    
    print(f"\n✓ Created {created} new requests")
    print(f"✓ Total requests now: {final_count}")
    
    # Show monitoring status
    response = requests.get("http://localhost:8001/api/v1/requests/monitoring/status")
    if response.status_code == 200:
        status = response.json()
        print(f"\nMonitoring Status:")
        print(f"  Active: {status['active']}")
        print(f"  Email count: {status['email_count']}")
        
        if not status['active']:
            print("\nTo start monitoring, make a POST request to:")
            print("  http://localhost:8001/api/v1/requests/monitoring/start")

if __name__ == "__main__":
    main()