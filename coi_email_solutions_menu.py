#!/usr/bin/env python3
"""
COI Email Solutions Menu
Interactive menu to help with COI email monitoring without Gmail
"""

import os
import sys
import subprocess
import requests
import json

def check_backend_status():
    """Check if backend is running and show status."""
    try:
        response = requests.get("http://localhost:8001/")
        if response.status_code == 200:
            print("✓ Backend is running on port 8001")
            
            # Get monitoring status
            response = requests.get("http://localhost:8001/api/v1/requests/monitoring/status")
            if response.status_code == 200:
                status = response.json()
                print(f"  Monitoring: {'Active' if status['active'] else 'Inactive'}")
                print(f"  Email count: {status['email_count']}")
            
            # Get request count
            response = requests.get("http://localhost:8001/api/v1/requests")
            if response.status_code == 200:
                requests_data = response.json()
                print(f"  Total requests: {len(requests_data)}")
            
            return True
    except:
        print("✗ Backend is not running on port 8001")
        return False
    
def show_menu():
    """Display the main menu."""
    print("\n" + "="*60)
    print("COI EMAIL MONITORING SOLUTIONS")
    print("="*60)
    print("\n1. Check backend status")
    print("2. Populate with test data (5 requests)")
    print("3. Start mock email monitor (generates emails every 30-60s)")
    print("4. Generate mock data file (JSON)")
    print("5. Start/Stop monitoring via API")
    print("6. View current COI requests")
    print("7. Instructions for running mock-enabled backend")
    print("8. Exit")
    print("\n" + "="*60)

def populate_test_data():
    """Run the populate script."""
    print("\nPopulating with test data...")
    subprocess.run([sys.executable, "populate_simple_backend.py"])

def start_mock_monitor():
    """Start the mock email monitor."""
    print("\nStarting mock email monitor...")
    print("This will generate mock emails every 30-60 seconds")
    print("Press Ctrl+C to stop\n")
    subprocess.run([sys.executable, "enhance_simple_backend.py"])

def generate_mock_file():
    """Generate a mock data file."""
    count = input("\nHow many mock requests to generate? [10]: ").strip() or "10"
    filename = input("Output filename [mock_coi_requests.json]: ").strip() or "mock_coi_requests.json"
    
    subprocess.run([
        sys.executable, 
        "coi_mock_data_generator.py",
        "--count", count,
        "--save-file", filename
    ])

def toggle_monitoring():
    """Start or stop monitoring via API."""
    try:
        # Check current status
        response = requests.get("http://localhost:8001/api/v1/requests/monitoring/status")
        if response.status_code == 200:
            status = response.json()
            is_active = status['active']
            
            if is_active:
                print("\nMonitoring is currently ACTIVE")
                choice = input("Stop monitoring? (y/n): ").lower()
                if choice == 'y':
                    response = requests.post("http://localhost:8001/api/v1/requests/monitoring/stop")
                    print("✓ Monitoring stopped")
            else:
                print("\nMonitoring is currently INACTIVE")
                choice = input("Start monitoring? (y/n): ").lower()
                if choice == 'y':
                    response = requests.post("http://localhost:8001/api/v1/requests/monitoring/start")
                    print("✓ Monitoring started")
    except Exception as e:
        print(f"✗ Error: {e}")

def view_requests():
    """View current COI requests."""
    try:
        response = requests.get("http://localhost:8001/api/v1/requests")
        if response.status_code == 200:
            requests_data = response.json()
            print(f"\nTotal COI Requests: {len(requests_data)}")
            print("-" * 60)
            
            for req in requests_data[-10:]:  # Show last 10
                print(f"ID: {req['id']} | Date: {req['date']} | Vendor: {req['vendor']}")
                print(f"   Status: {req['status']}")
                if 'coverages' in req:
                    for coverage, details in req['coverages'].items():
                        print(f"   {coverage}: ${details.get('required', 0):,}")
                print()
    except Exception as e:
        print(f"✗ Error: {e}")

def show_instructions():
    """Show instructions for mock-enabled backend."""
    print("\n" + "="*60)
    print("INSTRUCTIONS FOR MOCK-ENABLED BACKEND")
    print("="*60)
    print("\nThe mock-enabled backend provides automatic email generation")
    print("without requiring Gmail authentication.\n")
    print("To use it:")
    print("\n1. Stop the current backend (if running)")
    print("2. Run: python coi_backend_with_mock.py 8001")
    print("3. The mock backend provides:")
    print("   - Automatic email generation when monitoring is active")
    print("   - Manual scan endpoint to trigger emails")
    print("   - Bulk generation endpoint")
    print("\nAPI Endpoints:")
    print("   POST /api/v1/requests/mock/generate?count=5")
    print("   POST /api/v1/requests/monitoring/scan")
    print("\nAll other endpoints remain the same.")

def main():
    """Main menu loop."""
    print("COI Email Monitoring Solutions")
    print("This tool helps populate the COI system without Gmail auth")
    
    while True:
        show_menu()
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == '1':
            check_backend_status()
        elif choice == '2':
            if check_backend_status():
                populate_test_data()
        elif choice == '3':
            if check_backend_status():
                start_mock_monitor()
        elif choice == '4':
            generate_mock_file()
        elif choice == '5':
            if check_backend_status():
                toggle_monitoring()
        elif choice == '6':
            if check_backend_status():
                view_requests()
        elif choice == '7':
            show_instructions()
        elif choice == '8':
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid option. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()