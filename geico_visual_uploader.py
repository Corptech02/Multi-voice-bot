#!/usr/bin/env python3
"""
GEICO Visual Upload Status Indicator
Shows when quote data is ready and copies fields to clipboard
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import webbrowser

class GeicoVisualUploader:
    def __init__(self):
        self.data = None
        self.window = None
        self.copied_fields = set()
        
    def load_data(self):
        """Load quote data from JSON file"""
        try:
            with open('truck_quote_example.json', 'r') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def create_window(self):
        """Create the visual interface"""
        self.window = tk.Tk()
        self.window.title("GEICO Quote Data Uploader")
        self.window.geometry("500x700")
        self.window.configure(bg='#f0f0f0')
        
        # Header with status
        header_frame = tk.Frame(self.window, bg='#004B87', height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title = tk.Label(header_frame, text="🚗 GEICO Quote Auto-Upload", 
                        font=("Arial", 18, "bold"), fg="white", bg='#004B87')
        title.pack(pady=20)
        
        # Status indicator
        status_frame = tk.Frame(self.window, bg='#e8f4f8', height=60)
        status_frame.pack(fill="x", padx=10, pady=10)
        status_frame.pack_propagate(False)
        
        status_label = tk.Label(status_frame, text="✅ Quote Data Loaded Successfully!", 
                              font=("Arial", 14, "bold"), fg="green", bg='#e8f4f8')
        status_label.pack(pady=15)
        
        # Data preview
        preview_frame = tk.LabelFrame(self.window, text="Loaded Quote Data", 
                                    font=("Arial", 12, "bold"), bg='white')
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create scrollable area
        canvas = tk.Canvas(preview_frame, bg='white')
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add data fields
        self.add_data_fields(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Action buttons
        button_frame = tk.Frame(self.window, bg='#f0f0f0')
        button_frame.pack(fill="x", padx=10, pady=10)
        
        open_geico_btn = tk.Button(button_frame, text="🌐 Open GEICO Website", 
                                 command=self.open_geico, bg='#004B87', fg='white',
                                 font=("Arial", 12, "bold"), padx=20, pady=10)
        open_geico_btn.pack(side="left", padx=5)
        
        instructions_btn = tk.Button(button_frame, text="📋 Show Instructions", 
                                   command=self.show_instructions, bg='#6c757d', 
                                   fg='white', font=("Arial", 12), padx=20, pady=10)
        instructions_btn.pack(side="left", padx=5)
        
        # Progress indicator
        progress_frame = tk.Frame(self.window, bg='#f0f0f0')
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(progress_frame, text="Fields Copied:", font=("Arial", 10), 
                bg='#f0f0f0').pack(side="left", padx=5)
        
        self.progress_label = tk.Label(progress_frame, text="0 / 0", 
                                     font=("Arial", 10, "bold"), bg='#f0f0f0')
        self.progress_label.pack(side="left")
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=200, mode='determinate')
        self.progress_bar.pack(side="left", padx=10)
    
    def add_data_fields(self, parent):
        """Add all data fields with copy buttons"""
        sections = [
            ("🚛 Vehicle Information", [
                ("Year", str(self.data["vehicle"]["year"])),
                ("Make", self.data["vehicle"]["make"]),
                ("Model", self.data["vehicle"]["model"]),
                ("Trim", self.data["vehicle"]["trim"]),
                ("Body Style", self.data["vehicle"]["body_style"]),
                ("VIN", self.data["vehicle"]["vin"])
            ]),
            ("👤 Driver Information", [
                ("First Name", self.data["driver"]["first_name"]),
                ("Last Name", self.data["driver"]["last_name"]),
                ("Date of Birth", self.data["driver"]["date_of_birth"]),
                ("Gender", self.data["driver"]["gender"]),
                ("Marital Status", self.data["driver"]["marital_status"]),
                ("Email", self.data["driver"]["email"]),
                ("Phone", self.data["driver"]["phone"])
            ]),
            ("🏠 Address", [
                ("Street", self.data["driver"]["address"]["street"]),
                ("City", self.data["driver"]["address"]["city"]),
                ("State", self.data["driver"]["address"]["state"]),
                ("ZIP", self.data["driver"]["address"]["zip"])
            ]),
            ("📋 Coverage Preferences", [
                ("Bodily Injury", self.data["coverage_preferences"]["bodily_injury_liability"]),
                ("Property Damage", self.data["coverage_preferences"]["property_damage_liability"]),
                ("Uninsured Motorist", self.data["coverage_preferences"]["uninsured_motorist"]),
                ("Comprehensive Deductible", self.data["coverage_preferences"]["comprehensive_deductible"]),
                ("Collision Deductible", self.data["coverage_preferences"]["collision_deductible"])
            ])
        ]
        
        total_fields = sum(len(fields) for _, fields in sections)
        field_count = 0
        
        for section_title, fields in sections:
            # Section header
            section_frame = tk.Frame(parent, bg='#e8f4f8', relief="ridge", bd=1)
            section_frame.pack(fill="x", padx=5, pady=5)
            
            tk.Label(section_frame, text=section_title, font=("Arial", 11, "bold"),
                    bg='#e8f4f8').pack(anchor="w", padx=10, pady=5)
            
            # Fields
            for field_name, field_value in fields:
                field_frame = tk.Frame(parent, bg='white')
                field_frame.pack(fill="x", padx=10, pady=2)
                
                # Field label
                label = tk.Label(field_frame, text=f"{field_name}:", 
                               width=20, anchor="w", bg='white')
                label.pack(side="left", padx=5)
                
                # Field value
                value_label = tk.Label(field_frame, text=str(field_value), 
                                     font=("Courier", 10), bg='white', fg='#333')
                value_label.pack(side="left", padx=5, fill="x", expand=True)
                
                # Copy button
                field_id = f"{field_count}"
                copy_btn = tk.Button(field_frame, text="📋 Copy", 
                                   command=lambda v=field_value, fid=field_id, t=total_fields: 
                                   self.copy_to_clipboard(v, fid, t),
                                   bg='#28a745', fg='white', font=("Arial", 9))
                copy_btn.pack(side="right", padx=5)
                
                field_count += 1
    
    def copy_to_clipboard(self, value, field_id, total):
        """Copy value to clipboard and update progress"""
        pyperclip.copy(str(value))
        self.copied_fields.add(field_id)
        
        # Update progress
        copied_count = len(self.copied_fields)
        self.progress_label.config(text=f"{copied_count} / {total}")
        self.progress_bar['value'] = (copied_count / total) * 100
        
        # Show temporary notification
        messagebox.showinfo("Copied!", f"'{value}' copied to clipboard!", parent=self.window)
    
    def open_geico(self):
        """Open GEICO website in browser"""
        webbrowser.open("https://www.geico.com/auto-insurance-quote/")
        messagebox.showinfo("GEICO Opened", 
                          "GEICO website opened in your browser.\n\n" +
                          "Click the 'Copy' buttons next to each field to copy the values!",
                          parent=self.window)
    
    def show_instructions(self):
        """Show usage instructions"""
        instructions = """How to use the GEICO Quote Auto-Uploader:

1. Click '🌐 Open GEICO Website' to open the quote form
2. As you fill out the form, click the 'Copy' button next to each field
3. Paste the copied value into the corresponding GEICO form field
4. The progress bar shows how many fields you've copied

Tips:
• The data is from truck_quote_example.json
• All values are test data for a 2021 Ford F-150
• You can edit the JSON file to change the test data
• Green 'Copy' buttons copy the value to your clipboard"""
        
        messagebox.showinfo("Instructions", instructions, parent=self.window)
    
    def run(self):
        """Main entry point"""
        if not self.load_data():
            messagebox.showerror("Error", "Could not load truck_quote_example.json")
            return
        
        self.create_window()
        self.window.mainloop()

if __name__ == "__main__":
    print("Starting GEICO Visual Uploader...")
    print("This tool helps you quickly fill GEICO forms with test data.")
    
    try:
        import pyperclip
    except ImportError:
        print("\nWARNING: pyperclip not installed. Installing now...")
        import subprocess
        subprocess.check_call(["pip3", "install", "pyperclip"])
        import pyperclip
    
    uploader = GeicoVisualUploader()
    uploader.run()