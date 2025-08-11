#!/usr/bin/env python3
"""
Super aggressive auto-1 sender
Sends 1+Enter whenever it detects certain patterns
"""

import subprocess
import time
import hashlib

print("🔥 AGGRESSIVE AUTO-1 ACTIVE", flush=True)
print("Will send '1' when detecting prompts...", flush=True)
print("-" * 50, flush=True)

last_send = 0
last_hash = ""

while True:
    try:
        # Get tmux content
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-e'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            content = result.stdout
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # If content changed
            if content_hash != last_hash:
                last_hash = content_hash
                
                # Aggressive triggers
                triggers = [
                    '?',  # Any question
                    '❯',  # Arrow prompt
                    'Do you',
                    'Would you',
                    'proceed',
                    'Bash',
                    'command',
                    'Press',
                    'Type',
                    'Enter',
                    '1.',
                    '1)',
                    'Yes',
                    'No',
                    'approve',
                    'confirm',
                    'allow',
                    'execute',
                    'run'
                ]
                
                # Count triggers
                trigger_count = sum(1 for t in triggers if t in content)
                
                # Send if enough triggers and cooldown passed
                if trigger_count >= 2 and time.time() - last_send > 1.0:
                    # Extra check: Don't send if it's just user input
                    if not content.strip().endswith('> 1'):
                        print(f"🎯 Triggers found: {trigger_count} | Sending 1+Enter", flush=True)
                        
                        # Send 1
                        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                        time.sleep(0.05)
                        # Send Enter
                        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                        
                        last_send = time.time()
        
        time.sleep(0.1)  # 100ms checks
        
    except KeyboardInterrupt:
        print("\nStopped", flush=True)
        break
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(0.5)