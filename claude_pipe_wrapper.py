#!/usr/bin/env python3
"""
Claude pipe wrapper - uses Claude in --print mode for each message
"""
import subprocess
import time
import uuid
import threading
import queue
from typing import Dict, Optional
import os

class ClaudePipeSession:
    """Manages a Claude session using --print mode"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history = []
        self.lock = threading.Lock()
        
    def send_message(self, message: str) -> str:
        """Send a message to Claude and get response"""
        try:
            # Add message to history
            self.conversation_history.append(f"Human: {message}")
            
            # Build the full prompt with conversation history
            full_prompt = "\n\n".join(self.conversation_history[-10:])  # Keep last 10 exchanges
            
            # Call Claude with --print mode
            cmd = [
                'claude',
                '--dangerously-skip-permissions',
                '--print',
                full_prompt
            ]
            
            print(f"[SESSION {self.session_id[:8]}] Running: claude --print with prompt")
            
            # Run Claude and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                response = result.stdout.strip()
                
                # Add Claude's response to history
                self.conversation_history.append(f"Claude: {response}")
                
                print(f"[SESSION {self.session_id[:8]}] Response: {response[:100]}...")
                return response
            else:
                print(f"[SESSION {self.session_id[:8]}] Error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[SESSION {self.session_id[:8]}] Timeout waiting for response")
            return None
        except Exception as e:
            print(f"[SESSION {self.session_id[:8]}] Error: {e}")
            return None

class ClaudePipeOrchestrator:
    """Orchestrator using pipe-based Claude sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ClaudePipeSession] = {}
        self.max_sessions = 4
        
    def create_session(self, tab_id: str) -> str:
        """Create a new Claude session for a tab"""
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
            
        session_id = str(uuid.uuid4())
        session = ClaudePipeSession(session_id)
        
        self.sessions[tab_id] = session
        print(f"[ORCHESTRATOR] Created session {session_id[:8]} for tab {tab_id}")
        return session_id
        
    def send_message(self, tab_id: str, message: str) -> Optional[str]:
        """Send message to a session and get response"""
        if tab_id not in self.sessions:
            print(f"[ORCHESTRATOR] No session for tab {tab_id}")
            return None
            
        session = self.sessions[tab_id]
        response = session.send_message(message)
        return response
        
    def cleanup_session(self, tab_id: str):
        """Clean up a session"""
        if tab_id in self.sessions:
            print(f"[ORCHESTRATOR] Cleaning up session for tab {tab_id}")
            del self.sessions[tab_id]
            
    def get_session_id(self, tab_id: str) -> Optional[str]:
        """Get session ID for a tab"""
        if tab_id in self.sessions:
            return self.sessions[tab_id].session_id
        return None

# Create global instance
pipe_orchestrator = ClaudePipeOrchestrator()

if __name__ == "__main__":
    # Test the wrapper
    print("Testing Claude pipe wrapper...")
    
    try:
        # Create a session
        session_id = pipe_orchestrator.create_session("test_tab")
        print(f"Created session: {session_id}")
        
        # Send a test message
        response = pipe_orchestrator.send_message("test_tab", "What is 2+2?")
        print(f"Response: {response}")
        
        # Send another message
        response = pipe_orchestrator.send_message("test_tab", "What color is the sky?")
        print(f"Response: {response}")
        
        # Cleanup
        pipe_orchestrator.cleanup_session("test_tab")
        print("Test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()