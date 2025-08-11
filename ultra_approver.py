#!/usr/bin/env python3
"""
Ultra Approver - Monitors for ANY sign of waiting and sends 1+Enter
"""

import subprocess
import time

print("⚡ ULTRA APPROVER ACTIVE ⚡", flush=True)
print("Will send 1+Enter when detecting any pause or prompt", flush=True)
print("-" * 40, flush=True)

last_content = ""
unchanged_count = 0
last_approval = 0

while True:
    try:
        # Get current terminal content
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            current = result.stdout
            
            # Check if content is unchanged (waiting for input)
            if current == last_content:
                unchanged_count += 1
            else:
                unchanged_count = 0
                last_content = current
            
            # Trigger conditions
            should_approve = False
            
            # 1. If we see "Bash(" anywhere
            if "Bash(" in current and time.time() - last_approval > 3:
                should_approve = True
                print(f"\n[{time.strftime('%H:%M:%S')}] Detected Bash command", flush=True)
            
            # 2. If content unchanged for 2 seconds and contains ?
            elif unchanged_count > 20 and "?" in current and time.time() - last_approval > 3:
                should_approve = True
                print(f"\n[{time.strftime('%H:%M:%S')}] Detected question with pause", flush=True)
            
            # 3. If we see common prompt words
            elif any(word in current.lower() for word in ["proceed", "approve", "confirm", "allow"]) and time.time() - last_approval > 3:
                should_approve = True
                print(f"\n[{time.strftime('%H:%M:%S')}] Detected prompt keywords", flush=True)
            
            if should_approve:
                print("➡️  Sending: 1 + Enter", flush=True)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1', 'Enter'])
                last_approval = time.time()
                unchanged_count = 0
        
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(1)