#!/usr/bin/env python3
"""
Claude subprocess manager - manages Claude instances using subprocess instead of tmux
"""
import subprocess
import threading
import queue
import time
from typing import Dict, Optional
import uuid
import os

class ClaudeSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.process = None
        self.output_queue = queue.Queue()
        self.response_buffer = []
        self.is_ready = False
        
    def start(self):
        """Start Claude subprocess"""
        env = os.environ.copy()
        env['TERM'] = 'dumb'  # Disable terminal codes
        
        self.process = subprocess.Popen(
            ['claude', '--dangerously-skip-permissions'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Start output reader thread
        self.reader_thread = threading.Thread(
            target=self._read_output,
            daemon=True
        )
        self.reader_thread.start()
        
        # Wait for Claude to be ready
        time.sleep(2)
        self.is_ready = True
        
    def _read_output(self):
        """Read output from Claude process"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_queue.put(line.rstrip())
            except:
                break
                
    def send_message(self, message: str):
        """Send message to Claude"""
        if self.process and self.process.poll() is None:
            self.process.stdin.write(message + '\n')
            self.process.stdin.flush()
            
    def get_response(self, timeout=5):
        """Get response from Claude"""
        response_lines = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                line = self.output_queue.get(timeout=0.1)
                response_lines.append(line)
                
                # Check if response is complete
                if line.strip() == "" and len(response_lines) > 1:
                    break
            except queue.Empty:
                if response_lines:
                    break
                    
        return '\n'.join(response_lines)
        
    def stop(self):
        """Stop Claude process"""
        if self.process:
            self.process.terminate()
            self.process.wait()

class ClaudeSubprocessManager:
    def __init__(self):
        self.sessions: Dict[str, ClaudeSession] = {}
        
    def create_session(self, tab_id: str) -> str:
        """Create new Claude session"""
        session_id = str(uuid.uuid4())[:8]
        session = ClaudeSession(session_id)
        session.start()
        self.sessions[tab_id] = session
        return session_id
        
    def send_message(self, tab_id: str, message: str) -> Optional[str]:
        """Send message to Claude session"""
        if tab_id in self.sessions:
            session = self.sessions[tab_id]
            session.send_message(message)
            return session.get_response()
        return None
        
    def cleanup_session(self, tab_id: str):
        """Clean up Claude session"""
        if tab_id in self.sessions:
            self.sessions[tab_id].stop()
            del self.sessions[tab_id]

# Test if this works
if __name__ == "__main__":
    manager = ClaudeSubprocessManager()
    session_id = manager.create_session("test")
    print(f"Created session: {session_id}")
    
    response = manager.send_message("test", "What is 2+2?")
    print(f"Response: {response}")
    
    manager.cleanup_session("test")