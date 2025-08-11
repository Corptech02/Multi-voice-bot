#!/usr/bin/env python3
"""
Ultra-aggressive auto-approval for Claude terminal
"""

import subprocess
import time
import sys

print("🚀 ULTRA AUTO-APPROVAL V2 STARTED", flush=True)
print("Monitoring for ANY approval prompts...", flush=True)
print("-" * 50, flush=True)

last_send_time = 0
consecutive_unchanged = 0

# Keywords that strongly indicate a prompt
STRONG_INDICATORS = [
    '❯', 'yes', 'no', 'proceed', 'approve', 'bash', 'command',
    'continue', 'confirm', 'allow', 'execute', 'run', 'perform',
    '1.', '1)', '[1]', 'press', 'enter'
]

while True:
    try:
        # Get last 30 lines of tmux
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-30'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            output_lower = output.lower()
            
            # Count indicators
            indicator_count = sum(1 for word in STRONG_INDICATORS if word.lower() in output_lower)
            
            # Special check for ❯
            has_arrow = '❯' in output
            
            # Check for question marks
            has_question = '?' in output
            
            # Decision logic
            should_approve = False
            reason = ""
            
            # Immediate triggers
            if has_arrow and ('yes' in output_lower or '1' in output_lower):
                should_approve = True
                reason = "Arrow + yes/1"
            elif 'do you want to proceed' in output_lower:
                should_approve = True
                reason = "Direct proceed prompt"
            elif 'bash command' in output_lower and has_question:
                should_approve = True
                reason = "Bash command prompt"
            elif indicator_count >= 3 and has_question:
                should_approve = True
                reason = f"Multiple indicators ({indicator_count})"
            elif 'press 1' in output_lower or 'type 1' in output_lower:
                should_approve = True
                reason = "Press 1 instruction"
            
            # Send approval if needed and cooldown passed
            if should_approve and time.time() - last_send_time > 1.5:
                print(f"\n🎯 TRIGGER: {reason}", flush=True)
                print(f"Time: {time.strftime('%H:%M:%S')}", flush=True)
                
                # Show context
                last_lines = output.strip().split('\n')[-5:]
                print("Context:", flush=True)
                for line in last_lines:
                    print(f"  {line[:100]}", flush=True)
                
                # Send approval
                print("✓ Sending: 1 + Enter", flush=True)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                time.sleep(0.1)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                
                last_send_time = time.time()
                consecutive_unchanged = 0
            
            # Periodic status
            consecutive_unchanged += 1
            if consecutive_unchanged % 50 == 0:  # Every 5 seconds
                print(".", end="", flush=True)
        
        time.sleep(0.1)  # Check every 100ms
        
    except KeyboardInterrupt:
        print("\nStopped", flush=True)
        break
    except Exception as e:
        print(f"\nERROR: {e}", flush=True)
        time.sleep(1)