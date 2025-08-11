#!/usr/bin/env python3
"""
Precise auto-approval for Claude bash permission prompts only
"""

import subprocess
import time
import re

print("🎯 PRECISE AUTO-APPROVAL STARTED", flush=True)
print("Looking for ACTUAL permission prompts only...", flush=True)
print("-" * 50, flush=True)

last_approval = 0
last_snapshot = ""

# Exact patterns for Claude's permission prompts
PERMISSION_PATTERNS = [
    # Claude's exact bash prompt format
    r"Bash command.*\n.*\n.*Do you want to proceed\?.*\n.*❯\s*1\.\s*Yes",
    r"Do you want to proceed\?.*\n.*❯\s*1\.\s*Yes",
    
    # Other permission formats
    r"Would you like to.*\n.*❯\s*1\.\s*Yes",
    r"Confirm.*\n.*❯\s*1\.\s*Yes",
    r"Allow.*\n.*❯\s*1\.\s*Yes",
    r"Execute.*\n.*❯\s*1\.\s*Yes",
    r"Run.*\n.*❯\s*1\.\s*Yes",
    
    # Simple pattern for bash commands
    r"bash.*command.*yes.*no",
    r"execute.*command.*yes.*no"
]

# Things to EXCLUDE (UI elements)
EXCLUDE_PATTERNS = [
    "Press up to edit",
    "auto-accept edits",
    "shift+tab to cycle",
    "> 1",  # User typing 1
    "│ > 1",  # User input in box
]

while True:
    try:
        # Get more lines for context
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-50'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            
            # Only process if changed
            if output != last_snapshot:
                last_snapshot = output
                
                # Check for exclusions first
                is_ui_element = any(exclude in output for exclude in EXCLUDE_PATTERNS)
                
                if not is_ui_element:
                    # Check for permission patterns
                    for pattern in PERMISSION_PATTERNS:
                        match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                        if match:
                            # Additional validation - must have ❯ followed by "1. Yes"
                            if '❯' in output:
                                # Find lines with ❯
                                lines = output.split('\n')
                                for i, line in enumerate(lines):
                                    if '❯' in line and i + 1 < len(lines):
                                        next_line = lines[i + 1] if i + 1 < len(lines) else ""
                                        # Check if this looks like a real prompt
                                        if ('1.' in line or '1.' in next_line) and time.time() - last_approval > 3:
                                            print(f"\n✅ REAL PROMPT DETECTED!", flush=True)
                                            print(f"Pattern: {pattern[:50]}...", flush=True)
                                            print(f"Time: {time.strftime('%H:%M:%S')}", flush=True)
                                            
                                            # Show context
                                            context_lines = lines[max(0, i-3):min(len(lines), i+4)]
                                            print("Context:", flush=True)
                                            for cl in context_lines:
                                                print(f"  {cl[:80]}", flush=True)
                                            
                                            # Send approval
                                            print("🚀 Sending: 1 + Enter", flush=True)
                                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                                            time.sleep(0.1)
                                            subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                                            
                                            last_approval = time.time()
                                            break
        
        # Heartbeat every 5 seconds
        if int(time.time()) % 5 == 0 and int(time.time()) != last_approval:
            print(".", end="", flush=True)
        
        time.sleep(0.2)  # Check every 200ms
        
    except KeyboardInterrupt:
        print("\nStopped", flush=True)
        break
    except Exception as e:
        print(f"\nERROR: {e}", flush=True)
        time.sleep(1)