#!/usr/bin/env python3
import json
import pyperclip
import sys

def load_quote_data(filename="truck_quote_example.json"):
    with open(filename, 'r') as f:
        return json.load(f)

def copy_field(data, field_path):
    """Copy a specific field to clipboard"""
    fields = field_path.split('.')
    value = data
    for field in fields:
        value = value.get(field, '')
    pyperclip.copy(str(value))
    return str(value)

def print_menu(data):
    print("\n=== GEICO Quote Auto-Fill Helper ===")
    print("\nDriver Information:")
    print("1. Full Name:", data['driver_info']['first_name'], data['driver_info']['last_name'])
    print("2. Date of Birth:", data['driver_info']['date_of_birth'])
    print("3. Address:", f"{data['driver_info']['address']['street']}, {data['driver_info']['address']['city']}, {data['driver_info']['address']['state']} {data['driver_info']['address']['zip']}")
    print("4. Email:", data['driver_info']['email'])
    print("5. Phone:", data['driver_info']['phone'])
    
    print("\nVehicle Information:")
    print("6. Vehicle:", f"{data['vehicle_info']['year']} {data['vehicle_info']['make']} {data['vehicle_info']['model']} {data['vehicle_info']['trim']}")
    print("7. VIN:", data['vehicle_info']['vin'])
    print("8. Annual Mileage:", data['vehicle_info']['annual_mileage'])
    
    print("\nQuick Copy Options:")
    print("9. Copy ZIP Code")
    print("10. Copy VIN")
    print("11. Copy Full Address")
    print("12. Copy Vehicle Year/Make/Model")
    
    print("\n0. Exit")
    print("\nEnter number to copy field to clipboard:")

def main():
    data = load_quote_data()
    
    while True:
        print_menu(data)
        choice = input("> ")
        
        if choice == '0':
            break
        elif choice == '1':
            value = f"{data['driver_info']['first_name']} {data['driver_info']['last_name']}"
            pyperclip.copy(value)
            print(f"Copied: {value}")
        elif choice == '2':
            value = copy_field(data, 'driver_info.date_of_birth')
            print(f"Copied: {value}")
        elif choice == '3':
            addr = data['driver_info']['address']
            value = f"{addr['street']}, {addr['city']}, {addr['state']} {addr['zip']}"
            pyperclip.copy(value)
            print(f"Copied: {value}")
        elif choice == '4':
            value = copy_field(data, 'driver_info.email')
            print(f"Copied: {value}")
        elif choice == '5':
            value = copy_field(data, 'driver_info.phone')
            print(f"Copied: {value}")
        elif choice == '6':
            v = data['vehicle_info']
            value = f"{v['year']} {v['make']} {v['model']} {v['trim']}"
            pyperclip.copy(value)
            print(f"Copied: {value}")
        elif choice == '7':
            value = copy_field(data, 'vehicle_info.vin')
            print(f"Copied: {value}")
        elif choice == '8':
            value = copy_field(data, 'vehicle_info.annual_mileage')
            print(f"Copied: {value}")
        elif choice == '9':
            value = copy_field(data, 'driver_info.address.zip')
            print(f"Copied: {value}")
        elif choice == '10':
            value = copy_field(data, 'vehicle_info.vin')
            print(f"Copied: {value}")
        elif choice == '11':
            addr = data['driver_info']['address']
            value = f"{addr['street']}, {addr['city']}, {addr['state']} {addr['zip']}"
            pyperclip.copy(value)
            print(f"Copied: {value}")
        elif choice == '12':
            v = data['vehicle_info']
            value = f"{v['year']} {v['make']} {v['model']}"
            pyperclip.copy(value)
            print(f"Copied: {value}")

if __name__ == "__main__":
    main()