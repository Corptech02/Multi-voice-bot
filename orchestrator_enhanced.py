#!/usr/bin/env python3
"""
Enhanced Claude Multi-Bot Orchestrator with Memory and Error Handling
"""

import subprocess
import uuid
import time
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import threading
import queue

@dataclass
class BotSession:
    """Represents a single Claude bot session with memory"""
    session_id: str
    tab_id: str
    tmux_session: str
    project_name: str
    created_at: datetime
    last_activity: datetime
    messages: List[Dict[str, Any]] = field(default_factory=list)
    memory_context: str = ""
    error_count: int = 0
    last_error: Optional[str] = None
    
class EnhancedOrchestrator:
    def __init__(self):
        """Initialize the enhanced orchestrator with memory support"""
        print("[ENHANCED ORCHESTRATOR] Initializing with memory and error handling")
        self.sessions: Dict[str, BotSession] = {}
        self.event_queue = queue.Queue()
        self.max_sessions = 10
        self.session_timeout = timedelta(minutes=30)
        self.max_memory_messages = 20  # Keep last 20 messages in memory
        
        # Initialize database for persistent memory
        self.init_database()
        
        # Load saved sessions from database
        self.load_sessions_from_db()
        
        # Start background thread for session maintenance
        self.maintenance_thread = threading.Thread(target=self._session_maintenance, daemon=True)
        self.maintenance_thread.start()
    
    def init_database(self):
        """Initialize SQLite database for session memory"""
        self.db_path = "/home/corp06/software_projects/ClaudeVoiceBot/current/bot_memory.db"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                tab_id TEXT,
                project_name TEXT,
                created_at TEXT,
                last_activity TEXT,
                memory_context TEXT,
                error_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                message_type TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_sessions_from_db(self):
        """Load previous sessions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clean up old sessions (older than 24 hours)
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute('DELETE FROM sessions WHERE last_activity < ?', (cutoff_time,))
        cursor.execute('DELETE FROM messages WHERE session_id NOT IN (SELECT session_id FROM sessions)')
        
        conn.commit()
        conn.close()
        print("[ORCHESTRATOR] Database cleaned up")
    
    def save_session_to_db(self, session: BotSession):
        """Save session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sessions 
            (session_id, tab_id, project_name, created_at, last_activity, memory_context, error_count, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.tab_id,
            session.project_name,
            session.created_at.isoformat(),
            session.last_activity.isoformat(),
            session.memory_context,
            session.error_count,
            session.last_error
        ))
        
        conn.commit()
        conn.close()
    
    def save_message_to_db(self, session_id: str, message_type: str, content: str):
        """Save message to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (session_id, message_type, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, message_type, content, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_session_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get message history for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_type, content, timestamp 
            FROM messages 
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'type': row[0],
                'content': row[1],
                'timestamp': row[2]
            })
        
        conn.close()
        return list(reversed(messages))  # Return in chronological order
    
    def create_session(self, tab_id: str, project_name: str) -> BotSession:
        """Create a new Claude session with memory initialization"""
        # Check if session already exists for this tab
        if tab_id in self.sessions:
            print(f"[ORCHESTRATOR] Reusing existing session for tab {tab_id}")
            return self.sessions[tab_id]
        
        # Clean up old sessions if needed
        if len(self.sessions) >= self.max_sessions:
            self.cleanup_old_sessions()
        
        session_id = str(uuid.uuid4())[:8]
        tmux_session = f"claude_bot_{session_id}"
        
        print(f"[SIMPLE ORCHESTRATOR] Creating session {session_id} for tab {tab_id}")
        
        # Create tmux session with error handling
        try:
            result = subprocess.run([
                'tmux', 'new-session', '-d', '-s', tmux_session,
                'claude', '--yes'  # Auto-approve mode
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Failed to create tmux session: {result.stderr}")
            
            # Wait for Claude to initialize
            time.sleep(3)
            
            # Create session object
            session = BotSession(
                session_id=session_id,
                tab_id=tab_id,
                tmux_session=tmux_session,
                project_name=project_name,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            
            # Load previous history if exists
            history = self.get_session_history(session_id)
            if history:
                session.messages = history
                # Build memory context from history
                context_messages = []
                for msg in history[-10:]:  # Last 10 messages
                    context_messages.append(f"{msg['type']}: {msg['content'][:100]}...")
                session.memory_context = "\n".join(context_messages)
            
            # Store session
            self.sessions[tab_id] = session
            self.save_session_to_db(session)
            
            print(f"[ORCHESTRATOR] Session created successfully. Total sessions: {len(self.sessions)}")
            
            # Send memory context to Claude if exists
            if session.memory_context:
                self._send_memory_context(session)
            
            return session
            
        except Exception as e:
            print(f"[ORCHESTRATOR] Error creating session: {str(e)}")
            raise
    
    def _send_memory_context(self, session: BotSession):
        """Send memory context to Claude"""
        if not session.memory_context:
            return
        
        context_msg = f"Previous conversation context:\n{session.memory_context}\n\nPlease continue based on this context."
        
        try:
            subprocess.run([
                'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
                '-l', context_msg
            ])
            subprocess.run([
                'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
                'Enter'
            ])
            time.sleep(2)  # Wait for Claude to process
        except Exception as e:
            print(f"[ORCHESTRATOR] Error sending memory context: {str(e)}")
    
    def route_message(self, tab_id: str, message: str) -> str:
        """Route message with error handling"""
        if tab_id not in self.sessions:
            raise Exception(f"No session found for tab {tab_id}")
        
        session = self.sessions[tab_id]
        session.last_activity = datetime.now()
        
        try:
            # Clear the line first
            subprocess.run([
                'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
                'C-u'
            ], check=True)
            time.sleep(0.1)
            
            # Send message to tmux session
            subprocess.run([
                'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
                '-l', message
            ], check=True)
            subprocess.run([
                'tmux', 'send-keys', '-t', f'{session.tmux_session}:0',
                'Enter'
            ], check=True)
            
            # Store message
            session.messages.append({
                'type': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save to database
            self.save_message_to_db(session.session_id, 'user', message)
            
            # Trim messages if too many
            if len(session.messages) > self.max_memory_messages:
                session.messages = session.messages[-self.max_memory_messages:]
            
            # Update session in database
            self.save_session_to_db(session)
            
            # Reset error count on successful message
            session.error_count = 0
            session.last_error = None
            
            return session.session_id
            
        except subprocess.CalledProcessError as e:
            session.error_count += 1
            session.last_error = f"Execution error: {str(e)}"
            self.save_session_to_db(session)
            
            # Try to recover if too many errors
            if session.error_count > 3:
                print(f"[ORCHESTRATOR] Too many errors for session {session.session_id}, attempting recovery")
                self._recover_session(session)
            
            raise Exception(f"Failed to send message: {session.last_error}")
    
    def _recover_session(self, session: BotSession):
        """Attempt to recover a failed session"""
        try:
            # Kill the old tmux session
            subprocess.run(['tmux', 'kill-session', '-t', session.tmux_session], capture_output=True)
            time.sleep(1)
            
            # Create new tmux session
            result = subprocess.run([
                'tmux', 'new-session', '-d', '-s', session.tmux_session,
                'claude', '--yes'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[ORCHESTRATOR] Session {session.session_id} recovered successfully")
                session.error_count = 0
                session.last_error = None
                time.sleep(3)  # Wait for Claude to initialize
                
                # Restore memory context
                self._send_memory_context(session)
            else:
                print(f"[ORCHESTRATOR] Failed to recover session: {result.stderr}")
                
        except Exception as e:
            print(f"[ORCHESTRATOR] Error during session recovery: {str(e)}")
    
    def capture_response(self, session_id: str) -> Optional[str]:
        """Capture response with better error handling"""
        # Find session by ID
        session = None
        for s in self.sessions.values():
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            return None
        
        try:
            # Capture from tmux
            result = subprocess.run([
                'tmux', 'capture-pane', '-t', f'{session.tmux_session}:0',
                '-p', '-S', '-100'
            ], capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                content = result.stdout
                # Look for Claude's response pattern
                lines = content.strip().split('\n')
                
                # Find last user input and get response after it
                response_lines = []
                capture = False
                
                for line in reversed(lines):
                    if capture and line.strip() and not line.startswith('>'):
                        response_lines.insert(0, line)
                    elif line.startswith('>') and not capture:
                        capture = True
                
                if response_lines:
                    response = '\n'.join(response_lines)
                    
                    # Save assistant response
                    if response not in [msg['content'] for msg in session.messages if msg['type'] == 'assistant']:
                        session.messages.append({
                            'type': 'assistant',
                            'content': response,
                            'timestamp': datetime.now().isoformat()
                        })
                        self.save_message_to_db(session.session_id, 'assistant', response)
                        self.save_session_to_db(session)
                    
                    return response
            
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"[ORCHESTRATOR] Error capturing response: {str(e)}")
            session.error_count += 1
            session.last_error = f"Capture error: {str(e)}"
            self.save_session_to_db(session)
            return None
    
    def cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for tab_id, session in self.sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                sessions_to_remove.append(tab_id)
        
        for tab_id in sessions_to_remove:
            self.cleanup_session(tab_id)
    
    def cleanup_session(self, tab_id: str):
        """Clean up a session"""
        if tab_id not in self.sessions:
            return
        
        session = self.sessions[tab_id]
        
        try:
            # Kill tmux session
            subprocess.run(['tmux', 'kill-session', '-t', session.tmux_session], capture_output=True)
        except:
            pass
        
        # Remove from active sessions
        del self.sessions[tab_id]
        print(f"[ORCHESTRATOR] Cleaned up session for tab {tab_id}")
    
    def _session_maintenance(self):
        """Background thread for session maintenance"""
        while True:
            try:
                # Clean up old sessions every 5 minutes
                time.sleep(300)
                self.cleanup_old_sessions()
            except Exception as e:
                print(f"[ORCHESTRATOR] Maintenance error: {str(e)}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for all sessions"""
        stats = {
            'active_sessions': len(self.sessions),
            'sessions': {}
        }
        
        for tab_id, session in self.sessions.items():
            stats['sessions'][tab_id] = {
                'session_id': session.session_id,
                'project_name': session.project_name,
                'message_count': len(session.messages),
                'error_count': session.error_count,
                'last_error': session.last_error,
                'last_activity': session.last_activity.isoformat(),
                'uptime': str(datetime.now() - session.created_at)
            }
        
        return stats

# Create global orchestrator instance
orchestrator = EnhancedOrchestrator()