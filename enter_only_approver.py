#!/usr/bin/env python3
"""
Enter-Only Approver - Just presses Enter when bash prompt appears
No typing "1", just Enter to accept the default
"""

import subprocess
import time
import re

print("⏎ ENTER-ONLY APPROVER ACTIVE", flush=True)
print("Will press Enter when bash prompts appear", flush=True)
print("-" * 50, flush=True)

last_enter_time = 0
cooldown = 5  # Wait 5 seconds between Enter presses

def has_bash_prompt(content):
    """Check if there's a bash prompt waiting"""
    # Look for Claude's specific prompt patterns
    prompt_indicators = [
        "Do you want to proceed?",
        "❯ 1. Yes",
        "1. Yes",
        "2. No",
        "Bash command:",
        "Execute this command?"
    ]
    
    for indicator in prompt_indicators:
        if indicator in content:
            # Make sure it's recent (in last 5 lines)
            lines = content.strip().split('\n')
            for line in lines[-5:]:
                if indicator in line:
                    return True
    return False

while True:
    try:
        # Get last 10 lines from tmux
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-10'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            content = result.stdout
            
            # Check cooldown
            if time.time() - last_enter_time < cooldown:
                time.sleep(0.5)
                continue
            
            # Check for bash prompt
            if has_bash_prompt(content):
                # Check if cursor is at a prompt (not already processing)
                last_line = content.strip().split('\n')[-1] if content.strip() else ""
                
                # Only press Enter if we're at a prompt waiting for input
                if any(x in last_line for x in ["❯", "?", "1.", "Yes", "No", ":"]):
                    print(f"\n⏎ Bash prompt detected at {time.strftime('%H:%M:%S')}", flush=True)
                    print("  Pressing Enter...", flush=True)
                    
                    # Just press Enter (accepts default option 1)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                    
                    last_enter_time = time.time()
                    print("  ✓ Done!", flush=True)
                    
                    # Wait for command to process
                    time.sleep(3)
        
        time.sleep(0.5)  # Check every 500ms
        
    except KeyboardInterrupt:
        print("\n✋ Enter-only approver stopped", flush=True)
        break
    except Exception as e:
        print(f"\n❌ Error: {e}", flush=True)
        time.sleep(1)