#!/usr/bin/env python3
"""
Claude Orchestrator - Manages multiple Claude instances across tabs
"""
import asyncio
import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime
import redis
import sqlite3
from pathlib import Path

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

class ClaudeOrchestrator:
    """
    Main orchestrator that manages multiple Claude instances
    Acts as the central hub for all bot communications
    """
    
    def __init__(self):
        self.sessions: Dict[str, BotSession] = {}
        self.active_tab_id: Optional[str] = None
        self.max_sessions = 4
        
        # Initialize storage
        self.init_storage()
        
        # Redis for real-time communication
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
    def init_storage(self):
        """Initialize SQLite database for persistent storage"""
        self.db_path = Path("orchestrator_data.db")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            tab_id TEXT UNIQUE,
            tmux_session TEXT,
            created_at TIMESTAMP,
            project_name TEXT,
            is_active BOOLEAN,
            last_activity TIMESTAMP
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TIMESTAMP,
            type TEXT,
            content TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT,
            rule_content TEXT,
            priority INTEGER
        )''')
        
        conn.commit()
        conn.close()
    
    def create_session(self, tab_id: str, project_name: str) -> BotSession:
        """Create a new Claude session for a tab"""
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
        
        session_id = str(uuid.uuid4())
        tmux_session = f"claude_{session_id[:8]}"
        
        # Create tmux session
        subprocess.run([
            'tmux', 'new-session', '-d', '-s', tmux_session,
            'bash', '-c', 'cd /home/corp06/software_projects/ClaudeVoiceBot/current && claude'
        ])
        
        # Wait for Claude to initialize
        time.sleep(2)
        
        # Create session object
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            tmux_session=tmux_session,
            created_at=datetime.now(),
            project_name=project_name,
            last_activity=datetime.now()
        )
        
        # Store in memory and database
        self.sessions[tab_id] = session
        self.save_session(session)
        
        # Publish creation event
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
        
        # Send message to appropriate tmux session
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
            '-l', message
        ])
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
            'Enter'
        ])
        
        # Log the message
        self.log_memory(session.session_id, 'user_message', message)
        
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
            return None
        
        # Capture tmux pane content
        result = subprocess.run([
            'tmux', 'capture-pane', '-t', f'{session.tmux_session}:0',
            '-p', '-S', '-500'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout
        
        return None
    
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
    
    def save_session(self, session: BotSession):
        """Save session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO sessions 
        (session_id, tab_id, tmux_session, created_at, project_name, is_active, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id, session.tab_id, session.tmux_session,
            session.created_at, session.project_name, session.is_active,
            session.last_activity
        ))
        
        conn.commit()
        conn.close()
    
    def log_memory(self, session_id: str, memory_type: str, content: str):
        """Log memory/context for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO memory (session_id, timestamp, type, content)
        VALUES (?, ?, ?, ?)
        ''', (session_id, datetime.now(), memory_type, content))
        
        conn.commit()
        conn.close()
    
    def publish_event(self, event_type: str, data: dict):
        """Publish event to Redis for real-time updates"""
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.redis_client.publish('orchestrator_events', json.dumps(event))
    
    def cleanup_session(self, tab_id: str):
        """Clean up a session when tab is closed"""
        if tab_id not in self.sessions:
            return
        
        session = self.sessions[tab_id]
        
        # Kill tmux session
        subprocess.run(['tmux', 'kill-session', '-t', session.tmux_session])
        
        # Mark as inactive in database
        session.is_active = False
        self.save_session(session)
        
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
        return {
            'session_id': session.session_id,
            'tab_id': session.tab_id,
            'project_name': session.project_name,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat() if session.last_activity else None,
            'is_active': session.is_active
        }
    
    def list_active_sessions(self) -> list:
        """List all active sessions"""
        return [self.get_session_info(tab_id) for tab_id in self.sessions.keys()]


# Singleton instance
orchestrator = ClaudeOrchestrator()