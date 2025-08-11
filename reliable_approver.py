#!/usr/bin/env python3
"""
Reliable Auto Approver - Detects and approves bash prompts correctly
"""

import subprocess
import time
import sys

print("✅ RELIABLE AUTO-APPROVER ACTIVE", flush=True)
print("Will automatically approve bash commands", flush=True)
print("-" * 50, flush=True)

last_approval = 0
prompt_patterns = [
    "Do you want to proceed?",
    "❯ 1. Yes",
    "1. Yes",
    "Press Enter to continue"
]

def send_approval():
    """Send approval by typing 1 and pressing Enter"""
    # Type 1
    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
    time.sleep(0.1)
    # Press Enter
    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
    print(f"✓ Approved at {time.strftime('%H:%M:%S')}", flush=True)

while True:
    try:
        # Capture last 15 lines
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-15'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            content = result.stdout
            
            # Check if we recently approved (avoid double approval)
            if time.time() - last_approval < 3:
                time.sleep(0.3)
                continue
            
            # Look for bash prompt
            if "Do you want to proceed?" in content:
                # Check if it's waiting for input (has Yes/No options)
                lines = content.strip().split('\n')
                
                # Find the prompt line
                for i, line in enumerate(lines):
                    if "Do you want to proceed?" in line:
                        # Check next few lines for options
                        for j in range(i+1, min(i+5, len(lines))):
                            if "1. Yes" in lines[j] or "❯" in lines[j]:
                                # We found a prompt!
                                send_approval()
                                last_approval = time.time()
                                time.sleep(2)
                                break
                        break
        
        time.sleep(0.3)  # Check every 300ms
        
    except KeyboardInterrupt:
        print("\n✋ Approver stopped by user", flush=True)
        break
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(1)