#!/usr/bin/env python3
"""
Terminal monitor that captures real subprocess output for terminal preview
"""
import threading
import time
from collections import deque
from typing import Dict, List, Optional
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import os

class TerminalMonitor:
    """Monitors and captures subprocess output for terminal preview"""
    
    def __init__(self):
        self.terminal_buffers: Dict[str, deque] = {}  # tab_id -> terminal lines
        self.max_lines = 100  # Keep last 100 lines per terminal
        self.font_cache = None
        
    def initialize_buffer(self, tab_id: str):
        """Initialize terminal buffer for a tab"""
        if tab_id not in self.terminal_buffers:
            self.terminal_buffers[tab_id] = deque(maxlen=self.max_lines)
            # Add initial message
            self.terminal_buffers[tab_id].append(f"[Terminal Session - Tab {tab_id.split('_')[1]}]")
            self.terminal_buffers[tab_id].append("")
            
    def add_line(self, tab_id: str, line: str):
        """Add a line to the terminal buffer"""
        if tab_id not in self.terminal_buffers:
            self.initialize_buffer(tab_id)
            
        # Split long lines
        max_width = 100
        if len(line) > max_width:
            for i in range(0, len(line), max_width):
                self.terminal_buffers[tab_id].append(line[i:i+max_width])
        else:
            self.terminal_buffers[tab_id].append(line)
            
    def add_command(self, tab_id: str, command: str):
        """Add a command to the terminal buffer"""
        self.add_line(tab_id, f"$ {command}")
        
    def add_output(self, tab_id: str, output: str):
        """Add command output to the terminal buffer"""
        for line in output.split('\n'):
            self.add_line(tab_id, line)
            
    def get_terminal_image(self, tab_id: str) -> Optional[str]:
        """Generate terminal image from buffer"""
        try:
            # Get buffer content
            if tab_id not in self.terminal_buffers:
                self.initialize_buffer(tab_id)
                
            lines = list(self.terminal_buffers[tab_id])
            
            # Image settings
            width, height = 600, 400
            bg_color = (0, 0, 0)  # Black background
            text_color = (0, 255, 0)  # Green text
            cursor_color = (0, 255, 0)  # Green cursor
            
            # Create image
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Load font
            if not self.font_cache:
                font_size = 10
                try:
                    # Try different font paths
                    font_paths = [
                        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                        '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
                        '/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf',
                        '/System/Library/Fonts/Menlo.ttc',  # macOS
                    ]
                    for path in font_paths:
                        if os.path.exists(path):
                            self.font_cache = ImageFont.truetype(path, font_size)
                            break
                    if not self.font_cache:
                        self.font_cache = ImageFont.load_default()
                except:
                    self.font_cache = ImageFont.load_default()
                    
            font = self.font_cache
            
            # Calculate visible lines
            line_height = 12
            visible_lines = min(len(lines), height // line_height - 2)
            start_line = max(0, len(lines) - visible_lines)
            
            # Draw terminal content
            y_offset = 10
            for i in range(start_line, len(lines)):
                line = lines[i]
                
                # Highlight commands
                if line.startswith('$ '):
                    # Draw prompt in brighter green
                    draw.text((10, y_offset), '$ ', fill=(0, 255, 0), font=font)
                    draw.text((25, y_offset), line[2:], fill=(150, 255, 150), font=font)
                else:
                    # Regular output
                    draw.text((10, y_offset), line, fill=text_color, font=font)
                    
                y_offset += line_height
                
            # Draw cursor (blinking effect based on current time)
            if int(time.time() * 2) % 2 == 0:  # Blink every 0.5 seconds
                cursor_y = y_offset
                if cursor_y < height - 10:
                    draw.rectangle((10, cursor_y, 20, cursor_y + 10), fill=cursor_color)
                    
            # Add terminal border effect
            draw.rectangle((0, 0, width-1, height-1), outline=(0, 100, 0), width=1)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"[TERMINAL MONITOR] Error creating image: {e}")
            return None
            
    def clear_buffer(self, tab_id: str):
        """Clear terminal buffer for a tab"""
        if tab_id in self.terminal_buffers:
            self.terminal_buffers[tab_id].clear()
            self.initialize_buffer(tab_id)

# Global instance
terminal_monitor = TerminalMonitor()