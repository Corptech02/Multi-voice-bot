#!/usr/bin/env python3
"""
Orchestrator using pexpect-based Claude manager
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import threading
import queue
from claude_pexpect_manager import pexpect_orchestrator

@dataclass
class BotSession:
    """Represents a single Claude bot session"""
    session_id: str
    tab_id: str
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
    Orchestrator that uses pexpect-based Claude manager
    """
    
    def __init__(self):
        self.sessions: Dict[str, BotSession] = {}
        self.active_tab_id: Optional[str] = None
        self.max_sessions = 4
        self.event_queue = queue.Queue()
        self.last_responses: Dict[str, str] = {}  # Store last response for each tab
        print(f"[ORCHESTRATOR] Initialized with pexpect manager")
        
    def create_session(self, tab_id: str, project_name: str) -> BotSession:
        """Create a new Claude session for a tab"""
        print(f"[ORCHESTRATOR] create_session called with tab_id={tab_id}, project_name={project_name}")
        
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
        
        try:
            # Use pexpect orchestrator to create the actual Claude session
            session_id = pexpect_orchestrator.create_session(tab_id)
            
            # Create session object
            session = BotSession(
                session_id=session_id,
                tab_id=tab_id,
                created_at=datetime.now(),
                project_name=project_name,
                last_activity=datetime.now(),
                last_update_time=datetime.now()
            )
            
            # Store session
            self.sessions[tab_id] = session
            
            print(f"[ORCHESTRATOR] Session created successfully. Total sessions: {len(self.sessions)}")
            
            # Publish event
            self.publish_event('session_created', {
                'tab_id': tab_id,
                'session_id': session_id,
                'project_name': project_name
            })
            
            return session
            
        except Exception as e:
            print(f"[ORCHESTRATOR] Error creating session: {e}")
            raise
    
    def route_message(self, tab_id: str, message: str) -> str:
        """Route a message to the appropriate Claude instance"""
        if tab_id not in self.sessions:
            raise Exception(f"No session found for tab {tab_id}")
        
        session = self.sessions[tab_id]
        session.last_activity = datetime.now()
        
        # Send message using pexpect orchestrator
        response = pexpect_orchestrator.send_message(tab_id, message)
        
        if response:
            # Store the response
            self.last_responses[tab_id] = response
            
            # Update token count (estimate based on response length)
            # This is a rough estimate - 1 token ≈ 4 characters
            estimated_tokens = len(message) // 4 + len(response) // 4
            session.input_tokens += len(message) // 4
            session.output_tokens += len(response) // 4
            session.total_tokens += estimated_tokens
            
            # Store message and response
            session.messages.append({
                'type': 'user',
                'text': message,
                'timestamp': datetime.now().isoformat()
            })
            
            session.messages.append({
                'type': 'bot',
                'text': response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Publish message event
            self.publish_event('message_sent', {
                'tab_id': tab_id,
                'session_id': session.session_id,
                'message': message,
                'response': response
            })
        
        return session.session_id
    
    def capture_response(self, session_id: str) -> Optional[str]:
        """Get the last response for a session"""
        # Find the tab_id for this session
        tab_id = None
        for tid, sess in self.sessions.items():
            if sess.session_id == session_id:
                tab_id = tid
                break
                
        if not tab_id:
            return None
            
        session = self.sessions[tab_id]
        
        # Update session duration
        if session.last_update_time:
            time_diff = (datetime.now() - session.last_update_time).total_seconds()
            session.session_duration += time_diff
        session.last_update_time = datetime.now()
        
        # Return the last response if available
        if tab_id in self.last_responses:
            response = self.last_responses[tab_id]
            # Clear it so we don't send the same response multiple times
            del self.last_responses[tab_id]
            return f"● {response}"
        
        return None
    
    def switch_tab(self, tab_id: str):
        """Switch active tab"""
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
        
        # Clean up pexpect session
        pexpect_orchestrator.cleanup_session(tab_id)
        
        # Remove from active sessions
        del self.sessions[tab_id]
        
        # Remove any stored responses
        if tab_id in self.last_responses:
            del self.last_responses[tab_id]
        
        # Publish cleanup event
        self.publish_event('session_closed', {
            'tab_id': tab_id
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