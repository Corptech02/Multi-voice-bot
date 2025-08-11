#!/usr/bin/env python3
"""
FORCE AUTO-APPROVE - Maximum aggression
Sends 1+Enter whenever ANY of these conditions are met
"""

import subprocess
import time
import sys

print("⚡ FORCE AUTO-APPROVE ACTIVE ⚡", flush=True)
print("Sending 1+Enter on ANY suspicious pause", flush=True)
print("-" * 40, flush=True)

last_content = ""
last_change = time.time()
last_send = 0
no_change_count = 0

while True:
    try:
        # Capture current state
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-e'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            current = result.stdout
            
            # Track if content changed
            if current != last_content:
                last_content = current
                last_change = time.time()
                no_change_count = 0
            else:
                no_change_count += 1
            
            # AGGRESSIVE TRIGGERS:
            
            # 1. If no change for 1 second AND contains question mark
            if (time.time() - last_change > 1.0 and 
                '?' in current and 
                time.time() - last_send > 2):
                print(f"[{time.strftime('%H:%M:%S')}] Trigger: Question + Pause", flush=True)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1', 'Enter'])
                last_send = time.time()
                continue
            
            # 2. If we see ❯ anywhere
            if '❯' in current and time.time() - last_send > 2:
                print(f"[{time.strftime('%H:%M:%S')}] Trigger: Arrow detected", flush=True)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1', 'Enter'])
                last_send = time.time()
                continue
            
            # 3. If content hasn't changed for 2 seconds AND contains certain words
            if (time.time() - last_change > 2.0 and 
                time.time() - last_send > 3):
                keywords = ['Do you', 'Would you', 'proceed', 'bash', 'command', 
                           'confirm', 'approve', 'allow', 'Yes', 'No']
                if any(kw in current for kw in keywords):
                    print(f"[{time.strftime('%H:%M:%S')}] Trigger: Keywords + Long pause", flush=True)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1', 'Enter'])
                    last_send = time.time()
                    continue
            
            # 4. If user is stuck typing 1s
            if current.count('> 1') > 1 or current.count('1\n') > 2:
                print(f"[{time.strftime('%H:%M:%S')}] Trigger: Multiple 1s detected", flush=True)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-c', '1', 'Enter'])
                last_send = time.time()
                continue
            
            # 5. Ultimate fallback - if NOTHING changed for 3 seconds
            if (no_change_count > 30 and  # 3 seconds of no change
                len(current.strip()) > 100 and  # Not empty screen
                time.time() - last_send > 5):
                print(f"[{time.strftime('%H:%M:%S')}] Trigger: Extended pause", flush=True)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1', 'Enter'])
                last_send = time.time()
        
        time.sleep(0.1)  # Check every 100ms
        
    except KeyboardInterrupt:
        print("\n✋ Force approve stopped", flush=True)
        break
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(0.5)