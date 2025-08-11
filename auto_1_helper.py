#!/usr/bin/env python3
"""
Auto-1 Helper - Detects when you're trying to approve and helps
"""

import subprocess
import time

print("🤖 AUTO-1 HELPER ACTIVE")
print("I'll help when I see you need to approve something")
print("-" * 40)

last_help = 0
consecutive_ones = 0

while True:
    try:
        # Check current tmux content
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', 'claude:0', '-p', '-S', '-10'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            recent = result.stdout.lower()
            
            # If we see "1" being typed by user
            if '> 1' in recent or '│ > 1' in recent:
                consecutive_ones += 1
                
                # If user typed 1 multiple times, they need help
                if consecutive_ones >= 2 and time.time() - last_help > 2:
                    print(f"[{time.strftime('%H:%M:%S')}] I see you need help! Sending approval...")
                    
                    # Clear and send fresh 1 + Enter
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'C-c'])  # Clear
                    time.sleep(0.1)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                    time.sleep(0.05)
                    subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                    
                    last_help = time.time()
                    consecutive_ones = 0
            else:
                # Reset counter if no 1s seen
                if consecutive_ones > 0:
                    consecutive_ones = max(0, consecutive_ones - 1)
            
            # Also check for obvious prompts
            prompt_words = ['proceed?', 'bash command', 'do you want', 'would you like', 'confirm', 'approve']
            if any(word in recent for word in prompt_words) and time.time() - last_help > 3:
                print(f"[{time.strftime('%H:%M:%S')}] Prompt detected! Auto-approving...")
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', '1'])
                time.sleep(0.05)
                subprocess.run(['tmux', 'send-keys', '-t', 'claude:0', 'Enter'])
                last_help = time.time()
        
        time.sleep(0.2)
        
    except KeyboardInterrupt:
        print("\nHelper stopped")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)