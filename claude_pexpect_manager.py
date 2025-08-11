#!/usr/bin/env python3
"""
Claude pexpect manager - handles Claude's interactive terminal properly
"""
import pexpect
import time
import re
import threading
import queue
import uuid
from typing import Dict, Optional, List
import os

class ClaudeSession:
    """Manages a single Claude session using pexpect"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.process = None
        self.output_queue = queue.Queue()
        self.reader_thread = None
        self.is_ready = False
        self.last_output = ""
        
    def start(self):
        """Start Claude process with pexpect"""
        try:
            # Start Claude with pexpect
            self.process = pexpect.spawn(
                'claude',
                ['--dangerously-skip-permissions'],
                encoding='utf-8',
                timeout=None,
                dimensions=(24, 80)
            )
            
            # Start output reader thread
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            
            # Wait for Claude to be ready (look for the prompt)
            time.sleep(5)  # Give it time to start
            
            # Clear any initial output
            self._clear_output_queue()
            
            self.is_ready = True
            print(f"[SESSION {self.session_id[:8]}] Claude started successfully")
            
        except Exception as e:
            print(f"[SESSION {self.session_id[:8]}] Error starting Claude: {e}")
            raise
            
    def _read_output(self):
        """Continuously read output from Claude"""
        buffer = ""
        while self.process and self.process.isalive():
            try:
                # Read any available data
                data = self.process.read_nonblocking(size=1024, timeout=0.1)
                if data:
                    buffer += data
                    # Split by newlines and put complete lines in queue
                    lines = buffer.split('\n')
                    for line in lines[:-1]:
                        if line.strip():
                            self.output_queue.put(line + '\n')
                    buffer = lines[-1]  # Keep incomplete line in buffer
            except pexpect.TIMEOUT:
                continue
            except pexpect.EOF:
                break
            except Exception as e:
                if "would block" not in str(e):
                    print(f"[SESSION {self.session_id[:8]}] Reader error: {e}")
                continue
                
    def _clear_output_queue(self):
        """Clear the output queue"""
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break
                
    def send_message(self, message: str) -> str:
        """Send a message to Claude and get response"""
        if not self.process or not self.process.isalive():
            print(f"[SESSION {self.session_id[:8]}] Process not alive")
            return None
            
        try:
            # Clear any pending output
            self._clear_output_queue()
            
            # Send the message
            self.process.sendline(message)
            print(f"[SESSION {self.session_id[:8]}] Sent: {message}")
            
            # Wait a bit for Claude to process
            time.sleep(0.5)
            
            # Collect all output for up to 5 seconds
            response_lines = []
            start_time = time.time()
            last_output_time = start_time
            
            while time.time() - start_time < 10:  # 10 second max timeout
                try:
                    line = self.output_queue.get(timeout=0.1)
                    
                    # Skip ANSI escape sequences and control characters
                    clean_line = re.sub(r'\x1b\[[0-9;]*[mGKHJ]', '', line)
                    clean_line = re.sub(r'\x1b\[[\?0-9]*[hlr]', '', clean_line)
                    clean_line = re.sub(r'\[\d+m', '', clean_line)
                    clean_line = clean_line.strip()
                    
                    # Skip empty lines and the echoed input
                    if not clean_line or clean_line == message:
                        continue
                    
                    # Skip prompts and UI elements
                    if clean_line.startswith('>') or '│' in clean_line:
                        continue
                    
                    # Add non-empty lines to response
                    response_lines.append(clean_line)
                    last_output_time = time.time()
                    
                except queue.Empty:
                    # If we haven't received output for 1 second and we have some response, we're done
                    if response_lines and (time.time() - last_output_time > 1.0):
                        break
                    continue
            
            # Join all lines into response
            response = ' '.join(response_lines).strip()
            
            # If no response collected, try reading directly from process
            if not response:
                try:
                    available_output = self.process.read_nonblocking(size=4096, timeout=0.5)
                    if available_output:
                        clean_output = re.sub(r'\x1b\[[0-9;]*[mGKHJ]', '', available_output)
                        clean_output = re.sub(r'\x1b\[[\?0-9]*[hlr]', '', clean_output)
                        lines = clean_output.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and line != message and not line.startswith('>') and '│' not in line:
                                response_lines.append(line)
                        response = ' '.join(response_lines).strip()
                except:
                    pass
            
            print(f"[SESSION {self.session_id[:8]}] Response: {response[:100]}...")
            return response
            
        except Exception as e:
            print(f"[SESSION {self.session_id[:8]}] Error sending message: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def stop(self):
        """Stop the Claude process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait()
            except:
                pass
            self.process = None
            
class ClaudePexpectOrchestrator:
    """Orchestrator using pexpect for Claude sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ClaudeSession] = {}
        self.max_sessions = 4
        
    def create_session(self, tab_id: str) -> str:
        """Create a new Claude session for a tab"""
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
            
        session_id = str(uuid.uuid4())
        session = ClaudeSession(session_id)
        
        try:
            session.start()
            self.sessions[tab_id] = session
            print(f"[ORCHESTRATOR] Created session {session_id[:8]} for tab {tab_id}")
            return session_id
        except Exception as e:
            print(f"[ORCHESTRATOR] Failed to create session: {e}")
            raise
            
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
            self.sessions[tab_id].stop()
            del self.sessions[tab_id]
            
    def get_session_id(self, tab_id: str) -> Optional[str]:
        """Get session ID for a tab"""
        if tab_id in self.sessions:
            return self.sessions[tab_id].session_id
        return None

# Create global instance
pexpect_orchestrator = ClaudePexpectOrchestrator()

if __name__ == "__main__":
    # Test the manager
    print("Testing Claude pexpect manager...")
    
    try:
        # Create a session
        session_id = pexpect_orchestrator.create_session("test_tab")
        print(f"Created session: {session_id}")
        
        # Send a test message
        response = pexpect_orchestrator.send_message("test_tab", "What is 2+2?")
        print(f"Response: {response}")
        
        # Send another message
        response = pexpect_orchestrator.send_message("test_tab", "What color is the sky?")
        print(f"Response: {response}")
        
        # Cleanup
        pexpect_orchestrator.cleanup_session("test_tab")
        print("Test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()