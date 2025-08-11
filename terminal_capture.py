#!/usr/bin/env python3
"""
Terminal capture functionality for real terminal screenshots
"""
import subprocess
import base64
import tempfile
import os
import time
from typing import Optional, Dict
from PIL import Image, ImageDraw, ImageFont
import io
from terminal_monitor import terminal_monitor
from tmux_terminal_capture import tmux_capture
from claude_interactive_tmux import claude_interactive

class TerminalCapture:
    """Handles capturing real terminal screenshots"""
    
    def __init__(self):
        self.terminal_windows: Dict[str, str] = {}  # tab_id -> window_id mapping
        self.capture_method = self._detect_capture_method()
        
    def _detect_capture_method(self) -> str:
        """Detect available screenshot capture method"""
        # Check for import (ImageMagick)
        try:
            subprocess.run(['which', 'import'], check=True, capture_output=True)
            return 'import'
        except:
            pass
            
        # Check for scrot
        try:
            subprocess.run(['which', 'scrot'], check=True, capture_output=True)
            return 'scrot'
        except:
            pass
            
        # Check for gnome-screenshot
        try:
            subprocess.run(['which', 'gnome-screenshot'], check=True, capture_output=True)
            return 'gnome-screenshot'
        except:
            pass
            
        return 'none'
    
    def find_terminal_window(self, search_term: str = "ClaudeVoiceBot") -> Optional[str]:
        """Find terminal window ID by searching window titles"""
        try:
            # Use xwininfo to list all windows
            result = subprocess.run(
                ['xwininfo', '-root', '-tree'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if search_term in line:
                        # Extract window ID (hex format)
                        parts = line.strip().split()
                        if parts and parts[0].startswith('0x'):
                            return parts[0]
                            
            # Try wmctrl as alternative
            result = subprocess.run(
                ['wmctrl', '-l'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if search_term in line:
                        parts = line.split()
                        if parts:
                            return parts[0]
                            
        except Exception as e:
            print(f"[TERMINAL CAPTURE] Error finding window: {e}")
            
        return None
    
    def capture_window_screenshot(self, window_id: Optional[str] = None) -> Optional[str]:
        """Capture screenshot of specific window or active window"""
        # Since we don't have screenshot tools, always use tmux capture
        return self.capture_tmux_as_image()
    
    def capture_tmux_as_image(self, session_name: str = None) -> Optional[str]:
        """Capture tmux pane content and convert to terminal-like image"""
        try:
            # Try to capture tmux pane
            if session_name:
                cmd = ['tmux', 'capture-pane', '-t', f'{session_name}:0', '-p']
            else:
                # Try to capture from any claude session
                cmd = ['tmux', 'capture-pane', '-t', 'claude:0', '-p']
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                content = result.stdout
            else:
                # Fallback to placeholder content
                content = "Terminal preview not available\n\nClaude sessions run as subprocesses\nwithout visible terminal windows.\n\nTo see real terminals, run sessions\nin tmux or screen."
                
            # Convert text to image
            return self.text_to_terminal_image(content)
            
        except Exception as e:
            print(f"[TERMINAL CAPTURE] Tmux capture error: {e}")
            return self.text_to_terminal_image("Terminal capture error")
    
    def text_to_terminal_image(self, text: str) -> str:
        """Convert text to terminal-style image"""
        try:
            # Image settings
            width, height = 600, 400
            bg_color = (0, 0, 0)  # Black background
            text_color = (0, 255, 0)  # Green text
            
            # Create image
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Try to use a monospace font
            font_size = 12
            try:
                # Try different font paths
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
                    '/System/Library/Fonts/Menlo.ttc',  # macOS
                ]
                font = None
                for path in font_paths:
                    if os.path.exists(path):
                        font = ImageFont.truetype(path, font_size)
                        break
                if not font:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Draw text
            lines = text.split('\n')
            y_offset = 10
            for line in lines[:30]:  # Limit to 30 lines
                draw.text((10, y_offset), line[:80], fill=text_color, font=font)
                y_offset += font_size + 2
                
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"[TERMINAL CAPTURE] Image creation error: {e}")
            return None
    
    def capture_for_tab(self, tab_id: str) -> Optional[str]:
        """Capture REAL Claude interactive terminal screenshot"""
        # Use Claude interactive terminal capture
        screenshot = claude_interactive.get_terminal_screenshot(tab_id)
        
        if screenshot:
            return screenshot
            
        # Fallback to regular tmux capture
        screenshot = tmux_capture.get_terminal_screenshot(tab_id)
        
        if screenshot:
            return screenshot
            
        # Final fallback to terminal monitor
        screenshot = terminal_monitor.get_terminal_image(tab_id)
        
        return screenshot

# Global instance
terminal_capture = TerminalCapture()