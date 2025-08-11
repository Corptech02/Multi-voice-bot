#!/usr/bin/env python3
"""
Voice Typer - Simple solution that types voice commands into the terminal
"""
import time
import sys
import os

print("🎤 VOICE COMMAND TYPER")
print("="*40)
print("This will monitor for voice commands and type them")
print("Keep this running in the Claude terminal")
print("="*40)
print()

# Create the command file if it doesn't exist
COMMAND_FILE = '/tmp/claude_voice_commands.txt'
if not os.path.exists(COMMAND_FILE):
    open(COMMAND_FILE, 'w').close()

# Get the last position in the file
last_position = 0

print("Waiting for voice commands...")
print("(Commands will appear here and be typed automatically)")
print()

while True:
    try:
        with open(COMMAND_FILE, 'r') as f:
            f.seek(last_position)
            new_content = f.read()
            
            if new_content:
                # Extract just the command text (remove timestamp)
                lines = new_content.strip().split('\n')
                for line in lines:
                    if '] ' in line:
                        command = line.split('] ', 1)[1]
                        print(f"\n🎤 VOICE COMMAND: {command}")
                        
                        # Type it out character by character
                        for char in command:
                            sys.stdout.write(char)
                            sys.stdout.flush()
                            time.sleep(0.01)  # Small delay for natural typing
                        
                        # Press enter
                        print()  # This sends the command
                
                last_position = f.tell()
        
        time.sleep(0.5)  # Check twice per second
        
    except KeyboardInterrupt:
        print("\n\nVoice typer stopped.")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)