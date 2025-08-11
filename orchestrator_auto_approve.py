#!/usr/bin/env python3
"""
Enhanced Claude Orchestrator with Auto-Approval - Manages multiple Claude instances
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
import re

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
    # Auto-approval tracking
    last_approval_time: float = 0

class SimpleOrchestrator:
    """
    Enhanced orchestrator with auto-approval functionality
    """
    
    def __init__(self):
        self.sessions: Dict[str, BotSession] = {}
        self.active_tab_id: Optional[str] = None
        self.max_sessions = 4
        self.event_queue = queue.Queue()
        # Permission patterns from single voice version
        self.permission_patterns = [
            r'❯\s*1\.\s*yes',
            r'do you want to proceed\?',
            r'bash command.*\n.*yes.*\n.*no',
            r'\b(approve|permission|confirm|continue)\b.*\?',
            r'\b(yes|no|y/n)\b.*\?',
            r'press\s+(1|enter|y)',
            r'\[1\].*yes',
            r'1\).*yes',
            r'1\..*yes',
            r'(execute|run|perform).*\?',
            r'would you like to.*\?',
            r'are you sure.*\?'
        ]
        # Start auto-approval monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_for_approvals, daemon=True)
        self.monitor_thread.start()
        
    def _monitor_for_approvals(self):
        """Monitor all sessions for permission prompts and auto-approve"""
        while True:
            for session in self.sessions.values():
                if session.is_active:
                    # Check if we should look for approval prompts
                    current_time = time.time()
                    if current_time - session.last_approval_time > 2:  # 2 second cooldown
                        self._check_and_approve(session)
            time.sleep(0.5)  # Check every 500ms
    
    def _check_and_approve(self, session: BotSession):
        """Check session output for permission prompts and auto-approve"""
        try:
            # Capture current output
            result = subprocess.run([
                'tmux', 'capture-pane', '-t', f'{session.tmux_session}:0',
                '-p', '-S', '-50'  # Last 50 lines
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return
            
            output = result.stdout
            output_lower = output.lower()
            
            # Check for permission prompts
            prompt_detected = False
            
            # First check for ❯ symbol with context
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if '❯' in line:
                    context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                    if any(x in context.lower() for x in ['yes', '1.', 'proceed', 'approve']):
                        prompt_detected = True
                        print(f"[AUTO-APPROVE] Detected ❯ prompt for session {session.tmux_session}")
                        break
            
            # Check other patterns
            if not prompt_detected:
                for pattern in self.permission_patterns:
                    if re.search(pattern, output_lower, re.IGNORECASE | re.MULTILINE):
                        prompt_detected = True
                        print(f"[AUTO-APPROVE] Detected pattern for session {session.tmux_session}: {pattern}")
                        break
            
            # Send approval if detected
            if prompt_detected:
                print(f"[AUTO-APPROVE] Sending approval to session {session.tmux_session}")
                subprocess.run(['tmux', 'send-keys', '-t', f'{session.tmux_session}:0', '1'], check=True)
                subprocess.run(['tmux', 'send-keys', '-t', f'{session.tmux_session}:0', 'Enter'], check=True)
                session.last_approval_time = time.time()
                print(f"[AUTO-APPROVE] Sent: 1 + Enter to session {session.tmux_session}")
                
        except Exception as e:
            print(f"[AUTO-APPROVE] Error checking session {session.tmux_session}: {e}")
    
    def create_session(self, tab_id: str, project_name: str) -> BotSession:
        """Create a new Claude session for a tab"""
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
        
        session_id = str(uuid.uuid4())
        tmux_session = f"claude_{tab_id.replace('-', '_')}"
        
        # Kill any existing tmux session with this name
        subprocess.run(['tmux', 'kill-session', '-t', tmux_session], 
                      capture_output=True, stderr=subprocess.DEVNULL)
        
        # Create new tmux session with Claude
        # Using bypassPermissions flag but also have auto-approval as backup
        subprocess.run([
            'tmux', 'new-session', '-d', '-s', tmux_session,
            'bash', '-c', 
            f'cd /home/corp06/software_projects/ClaudeVoiceBot/current && exec /usr/local/bin/claude --permission-mode bypassPermissions'
        ])
        
        # Wait for the prompt to appear
        time.sleep(2)
        
        # Send arrow down to select "Yes, I accept"
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{tmux_session}:0',
            'Down'
        ])
        time.sleep(0.5)
        
        # Send Enter to confirm
        subprocess.run([
            'tmux', 'send-keys', '-t', f'{tmux_session}:0',
            'Enter'
        ])
        
        # Create session object
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            tmux_session=tmux_session,
            created_at=datetime.now(),
            project_name=project_name,
            last_update_time=datetime.now()
        )
        
        # Store session
        self.sessions[tab_id] = session
        
        # Set as active if it's the first session
        if self.active_tab_id is None:
            self.active_tab_id = tab_id
        
        print(f"[CREATE_SESSION] Created session: {session_id}")
        return session
    
    def send_message(self, tab_id: str, message: str) -> bool:
        """Send a message to a specific tab's Claude instance"""
        session = self.sessions.get(tab_id)
        if not session:
            print(f"[SEND] No session found for tab {tab_id}")
            return False
        
        # Update last activity
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
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"[SEND] Message sent to session {session.session_id}")
        return True
    
    def capture_response(self, session_id: str) -> Optional[str]:
        """Capture response from a specific Claude instance"""
        session = None
        for s in self.sessions.values():
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            return None
        
        # Update session duration
        if session.last_update_time:
            time_diff = (datetime.now() - session.last_update_time).total_seconds()
            session.session_duration += time_diff
        session.last_update_time = datetime.now()
        
        # Capture tmux pane content
        result = subprocess.run([
            'tmux', 'capture-pane', '-t', f'{session.tmux_session}:0',
            '-p', '-S', '-500'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return None
        
        return result.stdout
    
    def get_session_stats(self, tab_id: str) -> Dict:
        """Get statistics for a specific session"""
        session = self.sessions.get(tab_id)
        if not session:
            return {
                'active': False,
                'duration': '00:00',
                'tokens': 0
            }
        
        # Calculate duration
        duration_seconds = session.session_duration
        if session.last_update_time:
            duration_seconds += (datetime.now() - session.last_update_time).total_seconds()
        
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        
        return {
            'active': session.is_active,
            'duration': f'{minutes:02d}:{seconds:02d}',
            'tokens': session.total_tokens
        }
    
    def switch_tab(self, tab_id: str):
        """Switch active tab"""
        if tab_id not in self.sessions:
            raise Exception(f"No session found for tab {tab_id}")
        self.active_tab_id = tab_id
        print(f"[SWITCH] Switched to tab {tab_id}")
    
    def close_session(self, tab_id: str):
        """Close a specific session"""
        session = self.sessions.get(tab_id)
        if session:
            # Kill tmux session
            subprocess.run(['tmux', 'kill-session', '-t', session.tmux_session],
                          capture_output=True, stderr=subprocess.DEVNULL)
            
            # Remove from sessions
            del self.sessions[tab_id]
            
            # Switch to another tab if this was active
            if self.active_tab_id == tab_id:
                self.active_tab_id = list(self.sessions.keys())[0] if self.sessions else None
            
            print(f"[CLOSE] Closed session for tab {tab_id}")
    
    def get_all_sessions(self) -> Dict[str, BotSession]:
        """Get all active sessions"""
        return self.sessions.copy()

# Create global orchestrator instance
orchestrator = SimpleOrchestrator()