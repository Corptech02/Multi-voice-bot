#!/usr/bin/env python3
"""
Claude FIFO wrapper - manages Claude through named pipes
"""
import os
import subprocess
import tempfile
import time
import threading
import select

class ClaudeFIFOSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.temp_dir = tempfile.mkdtemp()
        self.input_fifo = os.path.join(self.temp_dir, "input")
        self.output_fifo = os.path.join(self.temp_dir, "output")
        
        # Create FIFOs
        os.mkfifo(self.input_fifo)
        os.mkfifo(self.output_fifo)
        
        # Start Claude process
        self.process = subprocess.Popen(
            f"exec /usr/local/bin/claude --dangerously-skip-permissions < {self.input_fifo} > {self.output_fifo} 2>&1",
            shell=True,
            preexec_fn=os.setsid
        )
        
        # Open FIFOs
        self.input_fd = os.open(self.input_fifo, os.O_WRONLY | os.O_NONBLOCK)
        self.output_fd = os.open(self.output_fifo, os.O_RDONLY | os.O_NONBLOCK)
        
    def send_message(self, message):
        """Send message to Claude"""
        try:
            os.write(self.input_fd, (message + "\n").encode())
        except:
            pass
            
    def read_output(self, timeout=0.5):
        """Read available output"""
        output = []
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            ready, _, _ = select.select([self.output_fd], [], [], 0.1)
            if ready:
                try:
                    data = os.read(self.output_fd, 4096)
                    if data:
                        output.append(data.decode('utf-8', errors='ignore'))
                except:
                    break
            else:
                if output:
                    break
                    
        return ''.join(output)
        
    def cleanup(self):
        """Clean up resources"""
        try:
            os.close(self.input_fd)
            os.close(self.output_fd)
            self.process.terminate()
            os.unlink(self.input_fifo)
            os.unlink(self.output_fifo)
            os.rmdir(self.temp_dir)
        except:
            pass

# Test
if __name__ == "__main__":
    session = ClaudeFIFOSession("test")
    time.sleep(3)  # Wait for Claude to start
    
    print("Reading initial output...")
    output = session.read_output(2)
    print(f"Initial: {output[:200]}...")
    
    print("\nSending message...")
    session.send_message("What is 2+2?")
    
    time.sleep(2)
    output = session.read_output(2)
    print(f"Response: {output}")
    
    session.cleanup()