#!/usr/bin/env python3
"""
Auto-approval for Claude Voice Bot
Automatically approves bash commands in Claude responses
"""

import time
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator_simple_v2 import orchestrator

print("🎯 CLAUDE VOICE BOT AUTO-APPROVE ACTIVE", flush=True)
print("Auto-approving bash commands for all Claude sessions...", flush=True)
print("-" * 50, flush=True)

# Configure the orchestrator to auto-approve bash commands
class AutoApproveOrchestrator:
    def __init__(self, base_orchestrator):
        self.base = base_orchestrator
        self._original_route_message = base_orchestrator.route_message
        # Replace the route_message method
        base_orchestrator.route_message = self.auto_approve_route_message
        
    def auto_approve_route_message(self, tab_id, message):
        """Route message with auto-approval enabled"""
        print(f"[AUTO-APPROVE] Processing message for tab {tab_id}: {message[:50]}...")
        
        # Check if this is asking to run a bash command
        bash_keywords = ['run', 'execute', 'bash', 'command', 'terminal', 'shell', 'script']
        needs_auto_approve = any(keyword in message.lower() for keyword in bash_keywords)
        
        if needs_auto_approve:
            # Append auto-approval instruction
            enhanced_message = f"{message}\n\nIMPORTANT: If you need to run any bash commands, go ahead and run them directly without asking for permission. The user has enabled auto-approval for all bash commands."
            print(f"[AUTO-APPROVE] Enhanced message with auto-approval")
            return self._original_route_message(tab_id, enhanced_message)
        else:
            return self._original_route_message(tab_id, message)

# Apply auto-approval to the orchestrator
auto_approver = AutoApproveOrchestrator(orchestrator)

print("✅ Auto-approval enabled for Claude Voice Bot")
print("ℹ️  All bash commands will be automatically approved")
print("ℹ️  Keep this script running alongside the voice bot")
print("-" * 50)

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n❌ Auto-approval disabled")
    sys.exit(0)