#!/usr/bin/env python3
"""
Standalone auto-approval script for Claude terminal
Continuously monitors tmux for permission prompts and auto-approves
"""

import subprocess
import time
import re

def main():
    print("🤖 AUTO-APPROVAL SYSTEM STARTED")
    print("Monitoring Claude terminal for permission prompts...")
    print("-" * 50)
    
    last_approval_time = 0
    last_output_snapshot = ""
    check_interval = 0.1  # Check every 100ms for fast detection
    
    while True:
        try:
            # Capture tmux pane output
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-20'],  # Last 20 lines
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("Error: Claude tmux session not found. Waiting...")
                time.sleep(5)
                continue
            
            output = result.stdout
            
            # Only process if output changed
            if output != last_output_snapshot:
                last_output_snapshot = output
                
                # Multiple detection strategies
                prompt_found = False
                
                # Strategy 1: Look for ❯ with context
                if '❯' in output and time.time() - last_approval_time > 2:
                    lines = output.split('\n')
                    for i, line in enumerate(lines):
                        if '❯' in line:
                            # Check context around the arrow
                            context_start = max(0, i - 3)
                            context_end = min(len(lines), i + 3)
                            context = '\n'.join(lines[context_start:context_end])
                            
                            # Look for approval keywords in context
                            if any(word in context.lower() for word in [
                                'yes', 'no', 'proceed', 'approve', 'confirm',
                                'bash', 'command', 'execute', 'run', 'perform'
                            ]):
                                prompt_found = True
                                print(f"\n[DETECTED] Arrow prompt at line {i}")
                                break
                
                # Strategy 2: Direct pattern matching
                if not prompt_found and time.time() - last_approval_time > 2:
                    patterns = [
                        r'do you want to proceed',
                        r'bash command',
                        r'\byes\b.*\bno\b',
                        r'1\.\s*yes',
                        r'press 1',
                        r'approve.*\?',
                        r'confirm.*\?',
                        r'continue.*\?',
                        r'proceed.*\?',
                        r'execute.*\?',
                        r'run.*\?',
                        r'allow.*\?'
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, output.lower(), re.IGNORECASE):
                            prompt_found = True
                            print(f"\n[DETECTED] Pattern: {pattern}")
                            break
                
                # Strategy 3: Look for numbered options
                if not prompt_found and time.time() - last_approval_time > 2:
                    if re.search(r'1[.)\]]\s*(yes|approve|continue|proceed)', output.lower()):
                        prompt_found = True
                        print("\n[DETECTED] Numbered option")
                
                # Send approval if prompt detected
                if prompt_found:
                    print("[ACTION] Sending: 1 + Enter")
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'], check=True)
                    time.sleep(0.05)  # Small delay
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'], check=True)
                    last_approval_time = time.time()
                    print("[SUCCESS] Approval sent!")
                    
                    # Log what we approved
                    last_lines = output.strip().split('\n')[-5:]
                    print("Context:")
                    for line in last_lines:
                        print(f"  > {line[:80]}")
            
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n\nAuto-approval system stopped.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()