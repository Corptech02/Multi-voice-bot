#!/usr/bin/env python3
"""
Terminal Interface for Claude Voice Bot
Manages communication with Claude CLI
"""
import subprocess
import threading
import queue
import time
import re
import os

class ClaudeTerminalInterface:
    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self.current_response = []
        self.is_processing = False
        self.auto_confirm = True
        
    def start_claude_session(self):
        """Start a new Claude CLI session"""
        try:
            # Start Claude in the terminal
            # You'll need to adjust this command based on how Claude is invoked
            self.process = subprocess.Popen(
                ['claude'],  # or however you invoke Claude
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start output reader thread
            reader_thread = threading.Thread(target=self._read_output)
            reader_thread.daemon = True
            reader_thread.start()
            
            # Start input writer thread
            writer_thread = threading.Thread(target=self._write_input)
            writer_thread.daemon = True
            writer_thread.start()
            
            return True
        except Exception as e:
            print(f"Error starting Claude session: {e}")
            return False
    
    def _read_output(self):
        """Read output from Claude"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    print(f"[CLAUDE OUTPUT]: {line.strip()}")
                    self.output_queue.put(line)
                    
                    # Check for confirmation prompts
                    if self.auto_confirm and self._is_confirmation_prompt(line):
                        self.input_queue.put("y\n")
                        print("[AUTO-CONFIRM]: Sent 'y'")
            except Exception as e:
                print(f"Error reading output: {e}")
                break
    
    def _write_input(self):
        """Write input to Claude"""
        while self.process and self.process.poll() is None:
            try:
                command = self.input_queue.get(timeout=0.1)
                if command:
                    self.process.stdin.write(command)
                    self.process.stdin.flush()
                    print(f"[SENT TO CLAUDE]: {command.strip()}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error writing input: {e}")
                break
    
    def _is_confirmation_prompt(self, line):
        """Check if line is asking for confirmation"""
        confirm_patterns = [
            r'continue\?',
            r'proceed\?',
            r'confirm\?',
            r'y/n',
            r'\[y/N\]',
            r'\[Y/n\]',
            r'yes/no',
            r'OK\?'
        ]
        
        line_lower = line.lower()
        return any(re.search(pattern, line_lower, re.IGNORECASE) for pattern in confirm_patterns)
    
    def send_voice_command(self, text):
        """Send voice command to Claude"""
        self.is_processing = True
        self.current_response = []
        
        # Send the command
        self.input_queue.put(text + "\n")
        
        # Wait for response (with timeout)
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        while time.time() - start_time < timeout:
            try:
                line = self.output_queue.get(timeout=0.1)
                self.current_response.append(line)
                
                # Check if response seems complete
                if self._is_response_complete(line):
                    break
            except queue.Empty:
                # Check if we have enough response
                if len(self.current_response) > 0 and time.time() - start_time > 2:
                    break
        
        self.is_processing = False
        return ''.join(self.current_response)
    
    def _is_response_complete(self, line):
        """Check if Claude's response seems complete"""
        # Look for common end patterns
        end_patterns = [
            r'Human:',  # Claude is waiting for next input
            r'Assistant:',
            r'>\s*$',  # Command prompt
            r'\?\s*$',  # Question mark at end
            r'\.\s*$',  # Period at end
        ]
        
        return any(re.search(pattern, line) for pattern in end_patterns)
    
    def get_recent_response(self):
        """Get the most recent response"""
        if self.current_response:
            return ''.join(self.current_response)
        return ""
    
    def cleanup(self):
        """Clean up the terminal session"""
        if self.process:
            self.process.terminate()
            self.process = None