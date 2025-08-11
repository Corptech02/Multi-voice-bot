#!/usr/bin/env python3
"""
Simple Claude wrapper - uses subprocess for each message
"""
import subprocess
import uuid
import time
from typing import Dict, Optional

class SimpleClaudeSession:
    """Simple session that just passes messages to Claude"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.message_count = 0
        
    def send_message(self, message: str) -> str:
        """Send a message to Claude and get response"""
        try:
            self.message_count += 1
            start_time = time.time()
            print(f"[SESSION {self.session_id[:8]}] Sending message #{self.message_count}: {message}")
            
            # Call Claude directly with the message - NO TIMEOUT
            cmd = ['claude', '--dangerously-skip-permissions', '--print', message]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
                # No timeout - let it run as long as needed
            )
            
            elapsed_time = time.time() - start_time
            print(f"[SESSION {self.session_id[:8]}] Request took {elapsed_time:.1f} seconds")
            
            if result.returncode == 0 and result.stdout:
                response = result.stdout.strip()
                # Log full response for debugging
                print(f"[SESSION {self.session_id[:8]}] Got response ({len(response)} chars): {response[:500]}...")
                if len(response) > 500:
                    print(f"[SESSION {self.session_id[:8]}] ...truncated for logging, full response is {len(response)} chars")
                return response
            else:
                print(f"[SESSION {self.session_id[:8]}] Error: returncode={result.returncode}, stderr={result.stderr}")
                return "Sorry, I couldn't process that request."
                
        except Exception as e:
            print(f"[SESSION {self.session_id[:8]}] Exception: {e}")
            return f"Sorry, an error occurred: {str(e)}"

class SimpleClaudeOrchestrator:
    """Simple orchestrator for Claude sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, SimpleClaudeSession] = {}
        print("[SIMPLE ORCHESTRATOR] Initialized")
        
    def create_session(self, tab_id: str) -> str:
        """Create a new Claude session for a tab"""
        session_id = str(uuid.uuid4())
        session = SimpleClaudeSession(session_id)
        self.sessions[tab_id] = session
        print(f"[SIMPLE ORCHESTRATOR] Created session {session_id[:8]} for tab {tab_id}")
        return session_id
        
    def send_message(self, tab_id: str, message: str) -> Optional[str]:
        """Send message to a session and get response"""
        if tab_id not in self.sessions:
            print(f"[SIMPLE ORCHESTRATOR] No session for tab {tab_id}, creating one")
            self.create_session(tab_id)
            
        session = self.sessions[tab_id]
        response = session.send_message(message)
        return response
        
    def cleanup_session(self, tab_id: str):
        """Clean up a session"""
        if tab_id in self.sessions:
            print(f"[SIMPLE ORCHESTRATOR] Cleaning up session for tab {tab_id}")
            del self.sessions[tab_id]
            
    def get_session_id(self, tab_id: str) -> Optional[str]:
        """Get session ID for a tab"""
        if tab_id in self.sessions:
            return self.sessions[tab_id].session_id
        return None

# Create global instance
simple_orchestrator = SimpleClaudeOrchestrator()

if __name__ == "__main__":
    # Test
    print("Testing simple Claude wrapper...")
    
    session_id = simple_orchestrator.create_session("test_tab")
    print(f"Created session: {session_id}")
    
    response = simple_orchestrator.send_message("test_tab", "What is 2+2?")
    print(f"Response: {response}")
    
    response = simple_orchestrator.send_message("test_tab", "What color is the sky?")
    print(f"Response: {response}")
    
    simple_orchestrator.cleanup_session("test_tab")
    print("Test completed!")