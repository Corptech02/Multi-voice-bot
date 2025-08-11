#!/usr/bin/env python3
"""
Capture REAL terminal content using tmux sessions
This creates actual tmux sessions for Claude and captures their real output
"""
import subprocess
import time
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import os
from typing import Optional, Dict

class TmuxTerminalCapture:
    """Captures REAL terminal content from tmux sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, str] = {}  # tab_id -> tmux_session mapping
        self.font = None
        self._load_font()
        
    def _load_font(self):
        """Load monospace font"""
        try:
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
                '/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf',
            ]
            for path in font_paths:
                if os.path.exists(path):
                    self.font = ImageFont.truetype(path, 11)
                    break
            if not self.font:
                self.font = ImageFont.load_default()
        except:
            self.font = ImageFont.load_default()
    
    def create_tmux_session(self, tab_id: str) -> bool:
        """Create a tmux session for the tab"""
        session_name = f"claude_{tab_id}"
        
        # Check if session already exists
        check_cmd = ['tmux', 'has-session', '-t', session_name]
        result = subprocess.run(check_cmd, capture_output=True)
        
        if result.returncode != 0:
            # Create new tmux session
            create_cmd = [
                'tmux', 'new-session', '-d', '-s', session_name,
                '-x', '120', '-y', '35'  # Set terminal size
            ]
            result = subprocess.run(create_cmd, capture_output=True)
            
            if result.returncode == 0:
                self.sessions[tab_id] = session_name
                # Clear and add initial prompt
                time.sleep(0.1)
                subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'clear', 'Enter'])
                time.sleep(0.1)
                subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 
                               f'echo "=== Claude Terminal Session - Tab {tab_id.split("_")[1]} ==="', 'Enter'])
                return True
        else:
            self.sessions[tab_id] = session_name
            return True
            
        return False
    
    def send_to_tmux(self, tab_id: str, command: str):
        """Send command to tmux session"""
        session_name = self.sessions.get(tab_id)
        if not session_name:
            if not self.create_tmux_session(tab_id):
                return False
            session_name = self.sessions[tab_id]
            
        # Clear line and send command
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'C-u'])
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', command])
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'Enter'])
        return True
    
    def capture_tmux_pane(self, tab_id: str) -> Optional[str]:
        """Capture REAL tmux pane content"""
        session_name = self.sessions.get(tab_id)
        if not session_name:
            if not self.create_tmux_session(tab_id):
                return None
            session_name = self.sessions[tab_id]
            
        try:
            # Capture tmux pane content
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', f'{session_name}:0', '-p', '-e'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error capturing tmux session: {result.stderr}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_terminal_image(self, content: str) -> str:
        """Convert terminal content to image"""
        try:
            # Image settings
            width, height = 600, 400
            bg_color = (0, 0, 0)
            text_color = (0, 255, 0)
            prompt_color = (100, 255, 100)
            
            # Create image
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Parse content and draw
            lines = content.split('\n')
            y_offset = 5
            char_height = 12
            
            for line in lines:
                if y_offset > height - 20:
                    break
                    
                # Highlight prompts
                if line.startswith('$') or line.startswith('#') or '~$' in line or '~#' in line:
                    draw.text((5, y_offset), line[:95], fill=prompt_color, font=self.font)
                else:
                    draw.text((5, y_offset), line[:95], fill=text_color, font=self.font)
                    
                y_offset += char_height
            
            # Add border
            draw.rectangle((0, 0, width-1, height-1), outline=(0, 100, 0), width=1)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"[TMUX CAPTURE] Error creating image: {e}")
            return None
    
    def get_terminal_screenshot(self, tab_id: str) -> Optional[str]:
        """Get real terminal screenshot for tab"""
        content = self.capture_tmux_pane(tab_id)
        if content:
            return self.create_terminal_image(content)
        return None
    
    def cleanup_session(self, tab_id: str):
        """Kill tmux session when done"""
        session_name = self.sessions.get(tab_id)
        if session_name:
            subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
            del self.sessions[tab_id]

# Global instance
tmux_capture = TmuxTerminalCapture()

if __name__ == "__main__":
    print("Testing tmux terminal capture...")
    
    # Test with tab_1
    if tmux_capture.create_tmux_session("tab_1"):
        print("Created tmux session")
        
        # Send a test command
        tmux_capture.send_to_tmux("tab_1", "echo 'This is a REAL terminal!'")
        time.sleep(0.5)
        
        # Capture and show result
        screenshot = tmux_capture.get_terminal_screenshot("tab_1")
        if screenshot:
            print(f"Screenshot captured! Length: {len(screenshot)}")
        else:
            print("Failed to capture screenshot")
            
        # Cleanup
        tmux_capture.cleanup_session("tab_1")
    else:
        print("Failed to create tmux session")