#!/usr/bin/env python3
"""
Smart Bash Approver - Only approves actual bash permission prompts ONCE
"""

import subprocess
import time
import re

print("🎯 SMART BASH APPROVER ACTIVE", flush=True)
print("Will approve bash prompts ONCE when detected", flush=True)
print("-" * 50, flush=True)

last_approval_time = 0
last_bash_command = ""
approval_cooldown = 10  # Don't approve again for 10 seconds after approval

def has_bash_prompt(text):
    """Check if text contains a bash permission prompt"""
    # Look for specific bash prompt patterns
    patterns = [
        r"Bash command.*Do you want to proceed\?",
        r"Do you want to proceed\?.*❯.*1\.\s*Yes",
        r"❯\s*1\.\s*Yes.*2\.\s*No",
        r"Would you like to.*bash",
        r"Execute.*command.*\?",
        r"Run.*bash.*\?"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            return True
    
    # Also check for the combination of key elements
    has_question = "?" in text
    has_bash_keyword = any(word in text.lower() for word in ["bash", "command", "execute", "run"])
    has_yes_option = "1. yes" in text.lower() or "❯" in text
    
    return has_question and has_bash_keyword and has_yes_option

def extract_bash_command(text):
    """Try to extract the bash command being requested"""
    # Look for patterns like "Bash(command here)"
    match = re.search(r"Bash\((.*?)\)", text)
    if match:
        return match.group(1)
    return ""

while True:
    try:
        # Capture the last 50 lines to get full context
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-50'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            
            # Check if enough time has passed since last approval
            if time.time() - last_approval_time < approval_cooldown:
                time.sleep(0.5)
                continue
            
            # Check if this is a bash prompt
            if has_bash_prompt(output):
                # Extract the command to avoid approving the same one twice
                current_command = extract_bash_command(output)
                
                # Only approve if it's a new command
                if current_command and current_command != last_bash_command:
                    print(f"\n✅ BASH PROMPT DETECTED!", flush=True)
                    print(f"Command: {current_command[:60]}...", flush=True)
                    print(f"Time: {time.strftime('%H:%M:%S')}", flush=True)
                    print("🚀 Sending approval: 1 + Enter", flush=True)
                    
                    # Send approval ONCE
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                    time.sleep(0.1)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                    
                    # Update tracking
                    last_approval_time = time.time()
                    last_bash_command = current_command
                    
                    print("✓ Approved! Waiting for command to complete...\n", flush=True)
                    
                    # Wait longer to ensure command completes
                    time.sleep(5)
        
        time.sleep(0.5)  # Check every 500ms
        
    except KeyboardInterrupt:
        print("\n✋ Smart approver stopped", flush=True)
        break
    except Exception as e:
        print(f"\n❌ ERROR: {e}", flush=True)
        time.sleep(1)

print("Smart bash approver stopped.", flush=True)