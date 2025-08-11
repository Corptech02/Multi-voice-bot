#!/usr/bin/env python3
"""
Monitor Claude terminal to understand what's happening
"""

import subprocess
import time

print("🔍 MONITORING CLAUDE TERMINAL")
print("=" * 40)

last_snapshot = ""
change_count = 0

while True:
    try:
        # Capture current state
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-30'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            current = result.stdout
            
            # Only print if something changed
            if current != last_snapshot:
                change_count += 1
                print(f"\n[Change #{change_count} at {time.strftime('%H:%M:%S')}]")
                print("-" * 40)
                
                # Show last 10 lines
                lines = current.strip().split('\n')[-10:]
                for line in lines:
                    print(f"| {line[:80]}")
                
                print("-" * 40)
                
                # Look for specific patterns
                if '?' in current:
                    print("⚠️  Question mark detected!")
                if '❯' in current:
                    print("⚠️  Arrow prompt detected!")
                if any(x in current.lower() for x in ['approve', 'proceed', 'confirm', 'bash']):
                    print("⚠️  Permission keywords detected!")
                
                last_snapshot = current
        
        time.sleep(0.5)
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        break