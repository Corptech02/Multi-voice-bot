#!/usr/bin/env python3
"""
Claude wrapper that runs in REAL tmux sessions for terminal preview
"""
import subprocess
import uuid
import time
import json
from typing import Dict, Optional, List
from datetime import datetime
from tmux_terminal_capture import tmux_capture

class ClaudeTmuxSession:
    """Session that runs Claude in a real tmux session"""
    
    def __init__(self, session_id: str, tab_id: str):
        self.session_id = session_id
        self.tab_id = tab_id
        self.message_count = 0
        self.conversation_history: List[Dict[str, str]] = []
        self.max_context_messages = 10
        
        # Create tmux session for this tab
        tmux_capture.create_tmux_session(tab_id)
        
    def send_message(self, message: str, retry_count: int = 0) -> str:
        """Send a message to Claude via tmux"""
        max_retries = 2
        
        try:
            self.message_count += 1
            print(f"[TMUX SESSION {self.session_id[:8]}] Sending message #{self.message_count}: {message}")
            
            # Build context from conversation history
            context_prompt = self._build_context_prompt(message)
            
            # Send command to tmux session
            claude_cmd = f'claude --dangerously-skip-permissions --print "{context_prompt}"'
            tmux_capture.send_to_tmux(self.tab_id, claude_cmd)
            
            # Wait for response (this is a simple approach - could be improved)
            time.sleep(3)  # Give Claude time to respond
            
            # Capture the tmux pane to get the response
            pane_content = tmux_capture.capture_tmux_pane(self.tab_id)
            
            if pane_content:
                # Extract the response from pane content
                # This is simplified - in production you'd parse more carefully
                lines = pane_content.split('\n')
                response_lines = []
                capture_response = False
                
                for line in reversed(lines):
                    if 'claude --dangerously-skip-permissions' in line:
                        break
                    if line.strip() and not line.startswith('$'):
                        response_lines.insert(0, line)
                
                response = '\n'.join(response_lines).strip()
                
                if response:
                    # Store the exchange in history
                    self.conversation_history.append({
                        'role': 'user',
                        'content': message,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.conversation_history.append({
                        'role': 'assistant',
                        'content': response,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Trim history if too long
                    if len(self.conversation_history) > self.max_context_messages * 2:
                        self.conversation_history = self.conversation_history[-(self.max_context_messages * 2):]
                    
                    print(f"[TMUX SESSION {self.session_id[:8]}] Got response: {response[:100]}...")
                    return response
                else:
                    return "No response captured from tmux session"
            else:
                return "Failed to capture tmux pane"
                
        except Exception as e:
            print(f"[TMUX SESSION {self.session_id[:8]}] Exception: {e}")
            return f"Error: {str(e)}"
    
    def _build_context_prompt(self, new_message: str) -> str:
        """Build prompt with conversation context"""
        if not self.conversation_history:
            return new_message
            
        # Include recent context
        context_parts = []
        recent_history = self.conversation_history[-6:]  # Last 3 exchanges
        
        for msg in recent_history:
            role = "Human" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        context_parts.append(f"Human: {new_message}")
        
        full_prompt = "\\n\\n".join(context_parts)
        return full_prompt
    
    def cleanup(self):
        """Cleanup tmux session"""
        tmux_capture.cleanup_session(self.tab_id)

class ClaudeTmuxOrchestrator:
    """Orchestrator for Claude tmux sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ClaudeTmuxSession] = {}
        self.session_data: Dict[str, Dict] = {}
        print("[TMUX ORCHESTRATOR] Initialized with real tmux sessions")
        
    def create_session(self, tab_id: str) -> str:
        """Create a new Claude tmux session for a tab"""
        session_id = str(uuid.uuid4())
        session = ClaudeTmuxSession(session_id, tab_id)
        self.sessions[tab_id] = session
        self.session_data[tab_id] = {
            'created_at': datetime.now().isoformat(),
            'message_count': 0
        }
        print(f"[TMUX ORCHESTRATOR] Created tmux session {session_id[:8]} for tab {tab_id}")
        return session_id
        
    def send_message(self, tab_id: str, message: str) -> Optional[str]:
        """Send message to a tmux session and get response"""
        if tab_id not in self.sessions:
            print(f"[TMUX ORCHESTRATOR] No session for tab {tab_id}, creating one")
            self.create_session(tab_id)
            
        session = self.sessions[tab_id]
        response = session.send_message(message)
        
        # Update session data
        if tab_id in self.session_data:
            self.session_data[tab_id]['message_count'] += 1
            self.session_data[tab_id]['last_activity'] = datetime.now().isoformat()
            
        return response
        
    def cleanup_session(self, tab_id: str):
        """Clean up a tmux session"""
        if tab_id in self.sessions:
            self.sessions[tab_id].cleanup()
            del self.sessions[tab_id]
            if tab_id in self.session_data:
                del self.session_data[tab_id]
            print(f"[TMUX ORCHESTRATOR] Cleaned up session for tab {tab_id}")
            
    def get_session_info(self, tab_id: str) -> Optional[Dict]:
        """Get information about a session"""
        if tab_id in self.sessions:
            return {
                'session_id': self.sessions[tab_id].session_id,
                'message_count': self.sessions[tab_id].message_count,
                **self.session_data.get(tab_id, {})
            }
        return None
        
    def get_conversation_history(self, tab_id: str) -> List[Dict]:
        """Get conversation history for a tab"""
        if tab_id in self.sessions:
            return self.sessions[tab_id].conversation_history
        return []

# Create global instance
tmux_orchestrator = ClaudeTmuxOrchestrator()

if __name__ == "__main__":
    # Test
    print("Testing Claude tmux wrapper...")
    
    session_id = tmux_orchestrator.create_session("test_tab")
    print(f"Created session: {session_id}")
    
    # Test message
    response = tmux_orchestrator.send_message("test_tab", "Hello! Can you see this in the terminal?")
    print(f"Response: {response}")
    
    # Capture screenshot
    screenshot = tmux_capture.get_terminal_screenshot("test_tab")
    if screenshot:
        print(f"Screenshot captured! Length: {len(screenshot)}")
    
    # Cleanup
    tmux_orchestrator.cleanup_session("test_tab")
    print("Test completed!")