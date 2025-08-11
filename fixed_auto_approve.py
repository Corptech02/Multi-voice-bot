#!/usr/bin/env python3
"""
Fixed Auto Approve - Only approves bash prompts when needed
"""

import subprocess
import time
import re

print("✅ FIXED AUTO-APPROVE ACTIVE", flush=True)
print("Will approve bash commands intelligently", flush=True)
print("-" * 50, flush=True)

last_prompt_line = ""
approved_prompts = set()
last_check_time = 0

def get_tmux_content():
    """Get last 20 lines from tmux"""
    result = subprocess.run(
        ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-20'],
        capture_output=True,
        text=True
    )
    return result.stdout if result.returncode == 0 else ""

def find_bash_prompt(content):
    """Find lines that look like bash approval prompts"""
    lines = content.strip().split('\n')
    
    for i, line in enumerate(lines):
        # Look for the specific pattern of Claude's bash prompt
        if "Do you want to proceed?" in line:
            # Check if we have the Yes/No options nearby
            for j in range(i, min(i+5, len(lines))):
                if "1. Yes" in lines[j] or "❯ 1. Yes" in lines[j]:
                    return True, line
    
    # Also check for the compact prompt format
    if "Bash(" in content and "Do you want to proceed?" in content:
        return True, "Bash command prompt"
    
    return False, ""

# Main loop
prompt_count = 0
while True:
    try:
        time.sleep(0.5)  # Check every 500ms
        
        content = get_tmux_content()
        if not content:
            continue
        
        # Check for bash prompt
        has_prompt, prompt_line = find_bash_prompt(content)
        
        if has_prompt and prompt_line not in approved_prompts:
            # Check if "1" was already typed (avoid double approval)
            last_lines = content.strip().split('\n')[-3:]
            if any(line.strip() == "1" for line in last_lines):
                continue
            
            print(f"\n🎯 Bash prompt detected!", flush=True)
            print(f"Time: {time.strftime('%H:%M:%S')}", flush=True)
            print("➡️  Sending: 1 + Enter", flush=True)
            
            # Send approval
            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
            time.sleep(0.1)
            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
            
            # Remember this prompt
            approved_prompts.add(prompt_line)
            prompt_count += 1
            
            print(f"✓ Approved! (Total: {prompt_count})", flush=True)
            
            # Clear old prompts after 50 to prevent memory buildup
            if len(approved_prompts) > 50:
                approved_prompts = set(list(approved_prompts)[-25:])
            
            # Wait a bit to avoid re-triggering
            time.sleep(3)
        
    except KeyboardInterrupt:
        print("\n✋ Auto-approve stopped", flush=True)
        break
    except Exception as e:
        print(f"\n❌ Error: {e}", flush=True)
        time.sleep(1)