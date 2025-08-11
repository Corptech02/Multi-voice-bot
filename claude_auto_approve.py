#!/usr/bin/env python3
"""
Auto-approval specifically for Claude terminal bash prompts
"""

import subprocess
import time
import re

print("🎯 CLAUDE AUTO-APPROVE ACTIVE", flush=True)
print("Monitoring for bash permission prompts...", flush=True)
print("-" * 50, flush=True)

last_approval = 0
previous_lines = []

while True:
    try:
        # Capture the pane
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            
            # Look for specific Claude prompt patterns
            for i in range(len(lines)):
                line = lines[i].strip()
                
                # Pattern 1: "Do you want to proceed?"
                if 'Do you want to proceed?' in line and time.time() - last_approval > 2:
                    print(f"\n✅ Found 'Do you want to proceed?' at line {i}", flush=True)
                    
                    # Look for "1. Yes" or "❯ 1." nearby
                    for j in range(max(0, i-3), min(len(lines), i+5)):
                        check_line = lines[j].strip()
                        if '1. Yes' in check_line or '❯ 1.' in check_line or '1.' in check_line:
                            print(f"✅ Found option '1' at line {j}: {check_line[:50]}", flush=True)
                            print("🚀 AUTO-APPROVING NOW!", flush=True)
                            
                            # Send 1 + Enter
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                            time.sleep(0.05)
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                            
                            last_approval = time.time()
                            break
                
                # Pattern 2: Lines with ❯ followed by numbers
                if '❯' in line and time.time() - last_approval > 2:
                    # Check if there's a question mark in recent lines
                    recent_text = '\n'.join(lines[max(0, i-10):i+3])
                    if '?' in recent_text and any(word in recent_text.lower() for word in 
                        ['proceed', 'confirm', 'approve', 'allow', 'execute', 'run', 'bash']):
                        
                        print(f"\n✅ Found ❯ with question context", flush=True)
                        print("🚀 AUTO-APPROVING!", flush=True)
                        
                        # Send 1 + Enter
                        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                        time.sleep(0.05)
                        subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                        
                        last_approval = time.time()
                
                # Pattern 3: Bash command header
                if 'Bash command' in line and time.time() - last_approval > 2:
                    print(f"\n✅ Found 'Bash command' header", flush=True)
                    
                    # Look ahead for approval prompt
                    for j in range(i, min(len(lines), i+10)):
                        if '?' in lines[j] or '1.' in lines[j] or '❯' in lines[j]:
                            print("🚀 AUTO-APPROVING BASH COMMAND!", flush=True)
                            
                            # Send 1 + Enter
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                            time.sleep(0.05)
                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                            
                            last_approval = time.time()
                            break
            
            # Store current state
            previous_lines = lines
        
        time.sleep(0.1)  # Check every 100ms
        
    except KeyboardInterrupt:
        print("\n✋ Stopped by user", flush=True)
        break
    except Exception as e:
        print(f"\n❌ ERROR: {e}", flush=True)
        time.sleep(1)

print("Auto-approval stopped.", flush=True)