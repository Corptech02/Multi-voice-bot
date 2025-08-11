#!/usr/bin/env python3
"""
Terminal Injector - Injects voice commands directly into terminal
"""
import sys
import select
import termios
import tty
import os
import time
import threading
import requests
from queue import Queue

# Voice command queue
command_queue = Queue()

def monitor_voice_commands():
    """Monitor for voice commands from the web interface"""
    print("\n[VOICE MONITOR] Starting voice command monitor...")
    print("[VOICE MONITOR] Speak into the web interface at https://192.168.40.232:8449")
    print("[VOICE MONITOR] Commands will appear here automatically!\n")
    
    last_check = 0
    while True:
        try:
            # Check for new commands every second
            current_time = time.time()
            if current_time - last_check > 1:
                # Read from the command file
                if os.path.exists('/tmp/claude_voice_commands.txt'):
                    with open('/tmp/claude_voice_commands.txt', 'r') as f:
                        lines = f.readlines()
                        if lines and len(lines) > command_queue.qsize():
                            # Get the latest command
                            latest = lines[-1].strip()
                            if '] ' in latest:
                                command = latest.split('] ', 1)[1]
                                command_queue.put(command)
                                print(f"\n[VOICE RECEIVED] {command}")
                
                last_check = current_time
        except Exception as e:
            print(f"[ERROR] {e}")
        
        time.sleep(0.1)

def inject_to_terminal():
    """Inject commands into the terminal"""
    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        # Set terminal to raw mode
        tty.setraw(sys.stdin.fileno())
        
        # Start voice monitor in background
        monitor_thread = threading.Thread(target=monitor_voice_commands, daemon=True)
        monitor_thread.start()
        
        while True:
            # Check for keyboard input
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                sys.stdout.write(char)
                sys.stdout.flush()
            
            # Check for voice commands
            if not command_queue.empty():
                command = command_queue.get()
                # Type the command
                for char in command:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    time.sleep(0.01)
                # Press enter
                sys.stdout.write('\r\n')
                sys.stdout.flush()
    
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    print("="*60)
    print("🎤 TERMINAL VOICE INJECTOR")
    print("="*60)
    print("This will inject voice commands directly into your terminal!")
    print("Keep this running alongside Claude")
    print("="*60)
    
    try:
        inject_to_terminal()
    except KeyboardInterrupt:
        print("\n\nVoice injector stopped.")