#!/usr/bin/env python3
"""
Launch Claude with pexpect to handle interactive prompt
"""
import pexpect
import sys
import os

def launch_claude():
    # Change to the correct directory
    os.chdir('/home/corp06/software_projects/ClaudeVoiceBot/current')
    
    # Launch Claude with pexpect
    child = pexpect.spawn('/usr/local/bin/claude --dangerously-skip-permissions', 
                         encoding='utf-8', 
                         dimensions=(24, 80))
    
    # Wait for the prompt
    child.expect('>', timeout=30)
    
    # Now Claude is ready - interact with it
    child.interact()

if __name__ == '__main__':
    launch_claude()