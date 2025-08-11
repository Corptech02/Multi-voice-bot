#!/usr/bin/env python3
"""
Simple Claude Orchestrator - Manages multiple Claude instances without Redis
"""
import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import threading
import queue

@dataclass
class BotSession:
    """Represents a single Claude bot session"""
    session_id: str
    tab_id: str
    tmux_session: str
    created_at: datetime
    project_name: str
    is_active: bool = True
    last_activity: datetime = None
    messages: List[dict] = field(default_factory=list)
    # Token usage tracking
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    # Time tracking
    session_duration: float = 0.0  # seconds
    last_update_time: datetime = None

class SimpleOrchestrator:
    """
    Simple orchestrator that manages multiple Claude instances
    """
    
    def __init__(self):
        self.sessions: Dict[str, BotSession] = {}
        self.active_tab_id: Optional[str] = None
        self.max_sessions = 4
        self.event_queue = queue.Queue()
        
    def create_session(self, tab_id: str, project_name: str) -> BotSession:
        """Create a new Claude session for a tab"""
        print(f"[ORCHESTRATOR] create_session called with tab_id={tab_id}, project_name={project_name}")
        
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
        
        session_id = str(uuid.uuid4())
        tmux_session = f"claude_{session_id[:8]}"
        
        print(f"[ORCHESTRATOR] Creating tmux session: {tmux_session}")
        
        # Create tmux session with Claude
        # Need to handle the interactive prompt properly
        result = subprocess.run([
            'tmux', 'new-session', '-d', '-s', tmux_session,
            'bash', '-c', 
            f'cd /home/corp06/software_projects/ClaudeVoiceBot/current && exec /usr/local/bin/claude --dangerously-skip-permissions'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ORCHESTRATOR] Error creating tmux session: {result.stderr}")
            raise Exception(f"Failed to create tmux session: {result.stderr}")
        
        # Wait for Claude to fully initialize
        time.sleep(3)
        
        # Create session object
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            tmux_session=tmux_session,
            created_at=datetime.now(),
            project_name=project_name,
            last_activity=datetime.now(),
            last_update_time=datetime.now()
        )
        
        # Store session
        self.sessions[tab_id] = session
        
        print(f"[ORCHESTRATOR] Session created successfully. Total sessions: {len(self.sessions)}")
        print(f"[ORCHESTRATOR] Session IDs: {list(self.sessions.keys())}")
        
        # Publish event
        self.publish_event('session_created', {
            'tab_id': tab_id,
            'session_id': session_id,
            'project_name': project_name
        })
        
        return session
    
    def route_message(self, tab_id: str, message: str) -> str:
        """Route a message to the appropriate Claude instance"""
        if tab_id not in self.sessions:
            raise Exception(f"No session found for tab {tab_id}")
        
        session = self.sessions[tab_id]
        session.last_activity = datetime.now()
        
        # Clear the line first
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
            'C-u'
        ])
        time.sleep(0.1)
        
        # Send message to appropriate tmux session
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
            '-l', message
        ])
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
            'Enter'
        ])
        
        # Store message
        session.messages.append({
            'type': 'user',
            'text': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Publish message event
        self.publish_event('message_sent', {
            'tab_id': tab_id,
            'session_id': session.session_id,
            'message': message
        })
        
        return session.session_id
    
    def capture_response(self, session_id: str) -> Optional[str]:
        """Capture response from a specific Claude instance"""
        session = None
        for s in self.sessions.values():
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            print(f"[ORCHESTRATOR] No session found for session_id: {session_id}")
            print(f"[ORCHESTRATOR] Available sessions: {list(self.sessions.keys())}")
            return None
        
        # Update session duration
        if session.last_update_time:
            time_diff = (datetime.now() - session.last_update_time).total_seconds()
            session.session_duration += time_diff
        session.last_update_time = datetime.now()
        
        # Capture tmux pane content - get everything from the start
        result = subprocess.run([
            'tmux', 'capture-pane', '-t', f'{session.tmux_session}:0',
            '-p', '-S', '-'  # '-S -' means start from beginning
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            content = result.stdout
            # Extract token usage from Claude's output
            self._extract_token_usage(session, content)
            return content
        
        return None
    
    def _extract_token_usage(self, session: BotSession, content: str):
        """Extract token usage from Claude's output"""
        # Look for token usage patterns in Claude's output
        # Pattern: "Input: X tokens | Output: Y tokens | Total: Z tokens"
        import re
        
        # Search for token usage in the content
        token_pattern = r'Input:\s*(\d+)\s*tokens?\s*\|\s*Output:\s*(\d+)\s*tokens?\s*\|\s*Total:\s*(\d+)\s*tokens?'
        matches = re.findall(token_pattern, content)
        
        if matches:
            # Get the most recent match
            latest_match = matches[-1]
            input_tokens = int(latest_match[0])
            output_tokens = int(latest_match[1])
            total_tokens = int(latest_match[2])
            
            # Update session token counts
            session.input_tokens = input_tokens
            session.output_tokens = output_tokens
            session.total_tokens = total_tokens
    
    def switch_tab(self, tab_id: str):
        """Switch active tab and update audio routing"""
        if tab_id not in self.sessions:
            raise Exception(f"No session found for tab {tab_id}")
        
        self.active_tab_id = tab_id
        
        # Publish tab switch event
        self.publish_event('tab_switched', {
            'tab_id': tab_id,
            'session_id': self.sessions[tab_id].session_id
        })
    
    def get_active_session(self) -> Optional[BotSession]:
        """Get the currently active session"""
        if self.active_tab_id and self.active_tab_id in self.sessions:
            return self.sessions[self.active_tab_id]
        return None
    
    def publish_event(self, event_type: str, data: dict):
        """Publish event to event queue"""
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.event_queue.put(event)
    
    def get_events(self) -> List[dict]:
        """Get all pending events"""
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events
    
    def cleanup_session(self, tab_id: str):
        """Clean up a session when tab is closed"""
        if tab_id not in self.sessions:
            return
        
        session = self.sessions[tab_id]
        
        # Kill tmux session
        subprocess.run(['tmux', 'kill-session', '-t', session.tmux_session])
        
        # Remove from active sessions
        del self.sessions[tab_id]
        
        # Publish cleanup event
        self.publish_event('session_closed', {
            'tab_id': tab_id,
            'session_id': session.session_id
        })
    
    def get_session_info(self, tab_id: str) -> Optional[dict]:
        """Get information about a specific session"""
        if tab_id not in self.sessions:
            return None
        
        session = self.sessions[tab_id]
        
        # Update duration if session is active
        current_duration = session.session_duration
        if session.last_update_time:
            time_diff = (datetime.now() - session.last_update_time).total_seconds()
            current_duration += time_diff
        
        return {
            'session_id': session.session_id,
            'tab_id': session.tab_id,
            'project_name': session.project_name,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat() if session.last_activity else None,
            'is_active': session.is_active,
            'message_count': len(session.messages),
            # Token usage
            'total_tokens': session.total_tokens,
            'input_tokens': session.input_tokens,
            'output_tokens': session.output_tokens,
            # Time tracking
            'session_duration': current_duration,
            'session_duration_formatted': self._format_duration(current_duration)
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def list_active_sessions(self) -> list:
        """List all active sessions"""
        return [self.get_session_info(tab_id) for tab_id in self.sessions.keys()]
    
    def store_bot_response(self, tab_id: str, response: str):
        """Store bot response in session history"""
        if tab_id in self.sessions:
            self.sessions[tab_id].messages.append({
                'type': 'bot',
                'text': response,
                'timestamp': datetime.now().isoformat()
            })


# Singleton instance
orchestrator = SimpleOrchestrator()