#!/usr/bin/env python3
"""
Auto-approval for multi-tab Claude Voice Bot
Monitors all Claude sessions and auto-approves bash commands
"""

import subprocess
import time
import re
import threading

print("🎯 MULTI-TAB CLAUDE AUTO-APPROVE ACTIVE", flush=True)
print("Monitoring all Claude sessions for bash permission prompts...", flush=True)
print("-" * 50, flush=True)

def monitor_session(session_name):
    """Monitor a single Claude session for approval prompts"""
    last_approval = 0
    print(f"📍 Monitoring session: {session_name}", flush=True)
    
    while True:
        try:
            # Check if session still exists
            check = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                 capture_output=True)
            if check.returncode != 0:
                print(f"❌ Session {session_name} no longer exists", flush=True)
                break
                
            # Capture the pane
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', f'{session_name}:0', '-p'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                # Look for bash approval prompts
                for i in range(len(lines)):
                    line = lines[i].strip()
                    
                    # Pattern 1: "Allow?"
                    if 'Allow?' in line and time.time() - last_approval > 2:
                        print(f"\n✅ [{session_name}] Found 'Allow?' prompt", flush=True)
                        print(f"🚀 [{session_name}] AUTO-APPROVING with 'y'", flush=True)
                        
                        # Send 'y' for yes
                        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'y'])
                        time.sleep(0.05)
                        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'Enter'])
                        
                        last_approval = time.time()
                        break
                    
                    # Pattern 2: "Do you want to proceed?" or "Continue?"
                    if ('Do you want to proceed?' in line or 'Continue?' in line) and time.time() - last_approval > 2:
                        print(f"\n✅ [{session_name}] Found approval prompt", flush=True)
                        
                        # Look for "1. Yes" or similar patterns
                        for j in range(max(0, i-5), min(len(lines), i+5)):
                            check_line = lines[j].strip()
                            if '1. Yes' in check_line or '1)' in check_line or '❯ 1' in check_line:
                                print(f"✅ [{session_name}] Found option 1", flush=True)
                                print(f"🚀 [{session_name}] AUTO-APPROVING with '1'", flush=True)
                                
                                # Send 1 + Enter
                                subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', '1'])
                                time.sleep(0.05)
                                subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'Enter'])
                                
                                last_approval = time.time()
                                break
                    
                    # Pattern 3: Direct bash command confirmation (y/n)
                    if re.search(r'\[y/n\]|\(y/n\)|Y/N|y/N', line) and time.time() - last_approval > 2:
                        # Check if it's asking about a bash command
                        context = '\n'.join(lines[max(0, i-3):i+1])
                        if 'bash' in context.lower() or 'command' in context.lower() or 'execute' in context.lower():
                            print(f"\n✅ [{session_name}] Found y/n prompt for command", flush=True)
                            print(f"🚀 [{session_name}] AUTO-APPROVING with 'y'", flush=True)
                            
                            # Send y
                            subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'y'])
                            time.sleep(0.05)
                            subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'Enter'])
                            
                            last_approval = time.time()
                            break
            
            time.sleep(0.5)  # Check twice per second
            
        except Exception as e:
            print(f"❌ Error monitoring {session_name}: {e}", flush=True)
            time.sleep(1)

def main():
    """Main loop to discover and monitor Claude sessions"""
    monitored_sessions = set()
    
    while True:
        try:
            # Get all tmux sessions
            result = subprocess.run(['tmux', 'list-sessions'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n')
                
                # Find Claude sessions
                for session_line in sessions:
                    if 'claude' in session_line.lower():
                        session_name = session_line.split(':')[0]
                        
                        if session_name not in monitored_sessions:
                            print(f"🆕 Found new Claude session: {session_name}", flush=True)
                            monitored_sessions.add(session_name)
                            
                            # Start monitoring thread
                            thread = threading.Thread(
                                target=monitor_session,
                                args=(session_name,),
                                daemon=True
                            )
                            thread.start()
            
            time.sleep(5)  # Check for new sessions every 5 seconds
            
        except Exception as e:
            print(f"❌ Error in main loop: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()