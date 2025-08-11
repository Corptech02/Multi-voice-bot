#!/usr/bin/env python3
"""
Claude Terminal Connector - Bridges voice commands to Claude CLI
"""
import subprocess
import threading
import queue
import time
import re
import os
import json
from datetime import datetime

class ClaudeTerminalConnector:
    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.is_ready = False
        self.current_response = []
        self.command_history = []
        
    def start_claude(self):
        """Start Claude in terminal mode"""
        try:
            # Start Claude CLI
            # Adjust this command based on how Claude is invoked in your terminal
            self.process = subprocess.Popen(
                ['claude'],  # or 'claude-cli', 'claude-ai', etc.
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy()
            )
            
            # Start output reader thread
            output_thread = threading.Thread(target=self._read_output, daemon=True)
            output_thread.start()
            
            # Wait for Claude to be ready
            time.sleep(2)
            self.is_ready = True
            
            print("[CLAUDE CONNECTOR] Claude terminal started successfully")
            return True
            
        except FileNotFoundError:
            print("[ERROR] Claude command not found. Trying alternative methods...")
            # Try alternative Claude invocation methods
            return self._try_alternative_claude_start()
        except Exception as e:
            print(f"[ERROR] Failed to start Claude: {e}")
            return False
    
    def _try_alternative_claude_start(self):
        """Try alternative methods to start Claude"""
        alternative_commands = [
            ['python', '-m', 'claude'],
            ['python3', '-m', 'claude'],
            ['/usr/local/bin/claude'],
            ['~/bin/claude'],
            ['npx', 'claude'],
        ]
        
        for cmd in alternative_commands:
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                output_thread = threading.Thread(target=self._read_output, daemon=True)
                output_thread.start()
                
                time.sleep(2)
                self.is_ready = True
                print(f"[CLAUDE CONNECTOR] Started with command: {' '.join(cmd)}")
                return True
            except:
                continue
        
        return False
    
    def _read_output(self):
        """Read output from Claude terminal"""
        buffer = []
        
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    # Clean ANSI escape codes
                    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                    clean_line = clean_line.strip()
                    
                    if clean_line:
                        print(f"[CLAUDE OUTPUT] {clean_line}")
                        buffer.append(clean_line)
                        
                        # Check if response is complete
                        if self._is_response_complete(clean_line, buffer):
                            # Join the response and clean it
                            full_response = '\n'.join(buffer)
                            self.response_queue.put(full_response)
                            buffer = []
                            
                        # Auto-confirm prompts
                        if self._needs_confirmation(clean_line):
                            self.process.stdin.write("y\n")
                            self.process.stdin.flush()
                            print("[AUTO-CONFIRM] Sent 'y' to confirmation prompt")
                            
            except Exception as e:
                print(f"[ERROR] Reading output: {e}")
                break
    
    def _is_response_complete(self, line, buffer):
        """Check if Claude's response is complete"""
        # Look for patterns that indicate Claude is done responding
        complete_patterns = [
            r'^Human:',
            r'^Assistant:',
            r'^\>',
            r'^\$',
            r'^#',
        ]
        
        # Check if we've been collecting for a while and no new input
        if len(buffer) > 3 and any(re.match(pattern, line) for pattern in complete_patterns):
            return True
            
        # Check for common end-of-response patterns
        if any(phrase in line.lower() for phrase in ['is there anything else', 'let me know if', 'feel free to ask']):
            # Wait a bit more to ensure complete response
            time.sleep(0.5)
            return True
            
        return False
    
    def _needs_confirmation(self, line):
        """Check if line is asking for confirmation"""
        confirm_patterns = [
            r'continue\?',
            r'proceed\?',
            r'confirm',
            r'y/n',
            r'\[y/N\]',
            r'\[Y/n\]',
            r'yes.*no',
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in confirm_patterns)
    
    def send_voice_command(self, text):
        """Send voice command to Claude"""
        if not self.is_ready or not self.process:
            return "Claude is not ready. Please wait..."
        
        try:
            # Clear any pending responses
            while not self.response_queue.empty():
                self.response_queue.get_nowait()
            
            # Send the command
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
            
            # Log the command
            self.command_history.append({
                'timestamp': datetime.now().isoformat(),
                'command': text,
                'type': 'voice'
            })
            
            print(f"[VOICE->CLAUDE] {text}")
            
            # Wait for response with timeout
            try:
                response = self.response_queue.get(timeout=30)
                
                # Clean up the response
                response = self._clean_response(response)
                
                # Log the response
                self.command_history[-1]['response'] = response
                
                return response
                
            except queue.Empty:
                return "Claude is taking longer than expected. Please try again."
                
        except Exception as e:
            print(f"[ERROR] Sending command: {e}")
            return f"Error communicating with Claude: {str(e)}"
    
    def _clean_response(self, response):
        """Clean up Claude's response for voice output"""
        # Remove common Claude prefixes
        response = re.sub(r'^(Assistant:|Claude:)\s*', '', response, flags=re.IGNORECASE)
        
        # Remove markdown code blocks for voice
        response = re.sub(r'```[\s\S]*?```', '[Code block removed for voice]', response)
        
        # Simplify URLs
        response = re.sub(r'https?://\S+', '[URL]', response)
        
        # Remove excessive whitespace
        response = ' '.join(response.split())
        
        return response
    
    def get_status(self):
        """Get current status"""
        return {
            'ready': self.is_ready,
            'process_alive': self.process is not None and self.process.poll() is None,
            'command_count': len(self.command_history)
        }
    
    def restart(self):
        """Restart Claude terminal"""
        self.stop()
        time.sleep(1)
        return self.start_claude()
    
    def stop(self):
        """Stop Claude terminal"""
        if self.process:
            self.process.terminate()
            self.process = None
            self.is_ready = False
            print("[CLAUDE CONNECTOR] Claude terminal stopped")

# Global connector instance
claude_connector = None

def initialize_connector():
    """Initialize the Claude connector"""
    global claude_connector
    claude_connector = ClaudeTerminalConnector()
    
    # Try to start Claude
    if not claude_connector.start_claude():
        print("[WARNING] Could not start Claude automatically")
        print("Please ensure Claude CLI is installed and accessible")
        # Continue anyway for demo mode
        claude_connector.is_ready = True
    
    return claude_connector