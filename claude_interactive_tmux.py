#!/usr/bin/env python3
"""
Run Claude in interactive mode in tmux sessions to see the actual Claude interface
"""
import subprocess
import time
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import os
from typing import Optional, Dict

class ClaudeInteractiveTmux:
    """Manages interactive Claude sessions in tmux"""
    
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
                    self.font = ImageFont.truetype(path, 10)
                    break
            if not self.font:
                self.font = ImageFont.load_default()
        except:
            self.font = ImageFont.load_default()
    
    def create_claude_session(self, tab_id: str) -> bool:
        """Create a tmux session running Claude interactively"""
        session_name = f"claude_{tab_id}"
        
        # Check if session already exists
        check_cmd = ['tmux', 'has-session', '-t', session_name]
        result = subprocess.run(check_cmd, capture_output=True)
        
        if result.returncode != 0:
            # Create new tmux session running Claude
            create_cmd = [
                'tmux', 'new-session', '-d', '-s', session_name,
                '-x', '100', '-y', '40',  # Terminal size
                'claude'  # Run claude command directly
            ]
            result = subprocess.run(create_cmd, capture_output=True)
            
            if result.returncode == 0:
                self.sessions[tab_id] = session_name
                print(f"[CLAUDE INTERACTIVE] Created session {session_name} running Claude")
                return True
            else:
                print(f"[CLAUDE INTERACTIVE] Failed to create session: {result.stderr}")
        else:
            self.sessions[tab_id] = session_name
            return True
            
        return False
    
    def send_to_claude(self, tab_id: str, message: str):
        """Send message to Claude running in tmux"""
        session_name = self.sessions.get(tab_id)
        if not session_name:
            if not self.create_claude_session(tab_id):
                return False
            session_name = self.sessions[tab_id]
            time.sleep(1)  # Give Claude time to start
            
        # Send message to Claude
        # First clear any partial input
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'C-u'])
        # Type the message
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', message])
        # Press Enter to send
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', 'Enter'])
        return True
    
    def capture_claude_terminal(self, tab_id: str) -> Optional[str]:
        """Capture the Claude terminal showing thinking and responses"""
        session_name = self.sessions.get(tab_id)
        if not session_name:
            if not self.create_claude_session(tab_id):
                return None
            session_name = self.sessions[tab_id]
            time.sleep(0.5)
            
        try:
            # Capture entire tmux pane with ANSI codes
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', f'{session_name}:0', '-p', '-e', '-S', '-'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return None
                
        except Exception as e:
            print(f"[CLAUDE INTERACTIVE] Capture error: {e}")
            return None
    
    def create_terminal_image(self, content: str) -> str:
        """Convert Claude terminal content to image"""
        try:
            # Image settings
            width, height = 600, 400
            bg_color = (0, 0, 0)
            text_color = (0, 255, 0)
            thinking_color = (255, 255, 0)  # Yellow for thinking
            human_color = (100, 255, 100)   # Bright green for human input
            
            # Create image
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Parse content and draw
            lines = content.split('\n')
            y_offset = 5
            char_height = 10
            
            for line in lines[-40:]:  # Show last 40 lines
                if y_offset > height - 15:
                    break
                
                # Color based on content
                color = text_color
                if 'Human:' in line or line.startswith('>'):
                    color = human_color
                elif 'thinking' in line.lower() or '...' in line:
                    color = thinking_color
                elif 'Claude:' in line or 'Assistant:' in line:
                    color = text_color
                    
                # Draw line (truncate to fit)
                draw.text((5, y_offset), line[:95], fill=color, font=self.font)
                y_offset += char_height
            
            # Add terminal border
            draw.rectangle((0, 0, width-1, height-1), outline=(0, 100, 0), width=1)
            
            # Add "LIVE CLAUDE TERMINAL" indicator
            draw.text((5, height-15), "● LIVE CLAUDE TERMINAL", fill=(255, 0, 0), font=self.font)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"[CLAUDE INTERACTIVE] Image error: {e}")
            return None
    
    def get_terminal_screenshot(self, tab_id: str) -> Optional[str]:
        """Get screenshot of Claude interactive terminal"""
        content = self.capture_claude_terminal(tab_id)
        if content:
            return self.create_terminal_image(content)
        return None

# Global instance
claude_interactive = ClaudeInteractiveTmux()

if __name__ == "__main__":
    print("Testing Claude interactive terminal...")
    
    # Test with tab_1
    if claude_interactive.create_claude_session("tab_1"):
        print("Created Claude session")
        
        # Wait for Claude to start
        time.sleep(2)
        
        # Send a test message
        claude_interactive.send_to_claude("tab_1", "Hello Claude! Can you see this?")
        time.sleep(3)
        
        # Capture screenshot
        screenshot = claude_interactive.get_terminal_screenshot("tab_1")
        if screenshot:
            print(f"Screenshot captured! Length: {len(screenshot)}")
        else:
            print("Failed to capture screenshot")