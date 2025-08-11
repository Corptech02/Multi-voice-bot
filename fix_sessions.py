#!/usr/bin/env python3
"""Quick fix to clear stuck sessions"""
import os
import signal

# Kill all orchestrator processes
os.system("pkill -f orchestrator_simple_v2")
os.system("pkill -f multi_tab_https_runner") 
os.system("pkill -f claude_simple_wrapper")
print("Cleared all processes")

# Restart services
os.system("./restart_bot.sh")
print("Services restarted")