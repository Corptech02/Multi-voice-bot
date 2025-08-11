#!/usr/bin/env python3
import json
import time
import webbrowser
import os
import sys
import pyperclip
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
from pathlib import Path

class GeicoAutoUploader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GEICO Auto Quote Uploader")
        self.root.geometry("600x800")
        self.root.configure(bg='#f0f4f8')
        
        # Load quote data
        self.quote_data = self.load_quote_data()
        self.upload_progress = 0
        self.total_fields = self.count_total_fields()
        self.uploaded_fields = []
        
        self.setup_ui()
        
    def load_quote_data(self):
        quote_file = Path("truck_quote_example.json")
        if not quote_file.exists():
            messagebox.error("Error", "truck_quote_example.json not found!")
            sys.exit(1)
        
        with open(quote_file, 'r') as f:
            return json.load(f)
    
    def count_total_fields(self):
        """Count total number of fields to upload"""
        count = 0
        for section in self.quote_data.values():
            if isinstance(section, dict):
                count += len(section)
        return count
    
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg='#2e7d32', height=100)
        header.pack(fill='x')
        
        title = tk.Label(header, text="GEICO Auto Quote Uploader", 
                        font=('Arial', 24, 'bold'), fg='white', bg='#2e7d32')
        title.pack(pady=20)
        
        # Status Section
        status_frame = tk.Frame(self.root, bg='#f0f4f8')
        status_frame.pack(fill='x', padx=20, pady=10)
        
        self.status_label = tk.Label(status_frame, text="Status: Ready to Upload",
                                    font=('Arial', 14), bg='#f0f4f8')
        self.status_label.pack()
        
        # Progress Bar
        self.progress = ttk.Progressbar(status_frame, length=500, mode='determinate')
        self.progress.pack(pady=10)
        
        self.progress_label = tk.Label(status_frame, text="0% Complete",
                                      font=('Arial', 12), bg='#f0f4f8')
        self.progress_label.pack()
        
        # Control Buttons
        button_frame = tk.Frame(self.root, bg='#f0f4f8')
        button_frame.pack(pady=20)
        
        self.auto_upload_btn = tk.Button(button_frame, text="Start Auto Upload",
                                        command=self.start_auto_upload,
                                        font=('Arial', 14, 'bold'),
                                        bg='#4CAF50', fg='white',
                                        padx=20, pady=10)
        self.auto_upload_btn.pack(side='left', padx=10)
        
        self.pause_btn = tk.Button(button_frame, text="Pause",
                                  command=self.toggle_pause,
                                  font=('Arial', 14),
                                  bg='#FF9800', fg='white',
                                  padx=20, pady=10,
                                  state='disabled')
        self.pause_btn.pack(side='left', padx=10)
        
        self.open_geico_btn = tk.Button(button_frame, text="Open GEICO Site",
                                       command=self.open_geico,
                                       font=('Arial', 14),
                                       bg='#2196F3', fg='white',
                                       padx=20, pady=10)
        self.open_geico_btn.pack(side='left', padx=10)
        
        # Upload Log
        log_frame = tk.Frame(self.root, bg='#f0f4f8')
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        log_label = tk.Label(log_frame, text="Upload Log:",
                            font=('Arial', 14, 'bold'), bg='#f0f4f8')
        log_label.pack(anchor='w')
        
        # Scrollable log area
        log_container = tk.Frame(log_frame)
        log_container.pack(fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side='right', fill='y')
        
        self.log_text = tk.Text(log_container, height=15, width=60,
                               yscrollcommand=scrollbar.set,
                               font=('Courier', 10))
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Configure text tags for coloring
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('info', foreground='blue')
        self.log_text.tag_config('warning', foreground='orange')
        
        # Visual indicator panel
        self.indicator_frame = tk.Frame(self.root, bg='#f0f4f8', height=100)
        self.indicator_frame.pack(fill='x', padx=20, pady=10)
        
        self.create_visual_indicators()
        
        # Auto upload state
        self.is_uploading = False
        self.is_paused = False
        
    def create_visual_indicators(self):
        """Create visual status indicators"""
        indicator_label = tk.Label(self.indicator_frame, text="Field Status:",
                                  font=('Arial', 12, 'bold'), bg='#f0f4f8')
        indicator_label.pack()
        
        # Create a row of indicator lights
        self.indicators = tk.Frame(self.indicator_frame, bg='#f0f4f8')
        self.indicators.pack(pady=10)
        
        # Sample indicators
        self.driver_indicator = self.create_indicator("Driver Info", 'gray')
        self.vehicle_indicator = self.create_indicator("Vehicle Info", 'gray')
        self.coverage_indicator = self.create_indicator("Coverage", 'gray')
        self.address_indicator = self.create_indicator("Address", 'gray')
        
    def create_indicator(self, label, color):
        frame = tk.Frame(self.indicators, bg='#f0f4f8')
        frame.pack(side='left', padx=10)
        
        canvas = tk.Canvas(frame, width=20, height=20, bg='#f0f4f8', highlightthickness=0)
        indicator = canvas.create_oval(2, 2, 18, 18, fill=color, outline='black')
        canvas.pack()
        
        text = tk.Label(frame, text=label, font=('Arial', 10), bg='#f0f4f8')
        text.pack()
        
        return {'canvas': canvas, 'indicator': indicator}
    
    def update_indicator(self, indicator, color):
        """Update indicator color"""
        indicator['canvas'].itemconfig(indicator['indicator'], fill=color)
        self.root.update()
    
    def log_message(self, message, tag='info'):
        """Add message to log with timestamp"""
        timestamp = time.strftime('%H:%M:%S')
        self.log_text.insert('end', f"[{timestamp}] {message}\n", tag)
        self.log_text.see('end')
        self.root.update()
    
    def open_geico(self):
        """Open GEICO website"""
        self.log_message("Opening GEICO website...", 'info')
        webbrowser.open('https://www.geico.com/auto-insurance-quote/')
    
    def toggle_pause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="Resume", bg='#4CAF50')
            self.log_message("Upload paused", 'warning')
        else:
            self.pause_btn.config(text="Pause", bg='#FF9800')
            self.log_message("Upload resumed", 'info')
    
    def start_auto_upload(self):
        """Start automatic upload process"""
        if self.is_uploading:
            self.stop_upload()
            return
        
        self.is_uploading = True
        self.auto_upload_btn.config(text="Stop Upload", bg='#f44336')
        self.pause_btn.config(state='normal')
        self.log_message("Starting automatic upload...", 'success')
        
        # Start upload in separate thread
        self.upload_thread = Thread(target=self.upload_process)
        self.upload_thread.daemon = True
        self.upload_thread.start()
    
    def stop_upload(self):
        """Stop upload process"""
        self.is_uploading = False
        self.auto_upload_btn.config(text="Start Auto Upload", bg='#4CAF50')
        self.pause_btn.config(state='disabled')
        self.log_message("Upload stopped", 'warning')
    
    def upload_process(self):
        """Main upload process"""
        sections = [
            ('driver_info', self.driver_indicator),
            ('vehicle_info', self.vehicle_indicator),
            ('coverage_preferences', self.coverage_indicator),
            ('address_info', self.address_indicator)
        ]
        
        field_count = 0
        
        for section_name, indicator in sections:
            if not self.is_uploading:
                break
                
            self.update_indicator(indicator, 'yellow')
            section_data = self.quote_data.get(section_name, {})
            
            for field_name, field_value in section_data.items():
                if not self.is_uploading:
                    break
                    
                # Wait if paused
                while self.is_paused and self.is_uploading:
                    time.sleep(0.1)
                
                # Copy field to clipboard
                pyperclip.copy(str(field_value))
                field_count += 1
                
                # Update progress
                progress_percent = (field_count / self.total_fields) * 100
                self.progress['value'] = progress_percent
                self.progress_label.config(text=f"{int(progress_percent)}% Complete")
                
                # Log upload
                self.log_message(f"Uploaded: {field_name} = {field_value}", 'success')
                
                # Add small delay to simulate realistic upload
                time.sleep(0.5)
            
            # Mark section as complete
            self.update_indicator(indicator, 'green')
        
        if self.is_uploading:
            self.log_message("Upload completed successfully!", 'success')
            self.status_label.config(text="Status: Upload Complete!")
            messagebox.showinfo("Success", "All fields have been uploaded to clipboard!\n" +
                              "Paste them into the GEICO form as needed.")
        
        self.stop_upload()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GeicoAutoUploader()
    app.run()