#!/usr/bin/env python3
"""Quick test to verify DOT entry works"""

from element_scanner_browser import ElementScannerBrowser
import time

scanner = ElementScannerBrowser()
scanner.setup_driver(headless=False)

# Navigate to GEICO
scanner.driver.get('https://gateway.geico.com')
time.sleep(3)

# Try the DOT entry
print("Testing DOT entry...")
result = scanner.enter_dot_number("111111111")
print(f"Result: {result}")

input("Press Enter to close...")
scanner.cleanup()