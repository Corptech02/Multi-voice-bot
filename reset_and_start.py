#!/usr/bin/env python3
"""Reset sessions and start the server fresh"""
import os
import sys

# Force reset of the orchestrator sessions
if os.path.exists('orchestrator_simple_v2.py'):
    # Temporarily modify the module to reset sessions
    import orchestrator_simple_v2
    if hasattr(orchestrator_simple_v2, 'orchestrator'):
        orchestrator_simple_v2.orchestrator.sessions.clear()
        print("Cleared orchestrator sessions")

# Also reset the claude_memory_wrapper sessions
if os.path.exists('claude_memory_wrapper.py'):
    import claude_memory_wrapper
    if hasattr(claude_memory_wrapper, 'simple_orchestrator'):
        claude_memory_wrapper.simple_orchestrator.sessions.clear()
        print("Cleared memory orchestrator sessions")

print("Sessions reset. Now start the server:")
print("python3 multi_tab_voice_https_final_working.py")