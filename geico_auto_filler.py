#!/usr/bin/env python3
"""
GEICO Auto Quote Filler with Visual Status Interface
Automatically fills GEICO insurance quote forms with test data
"""

import json
import time
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import threading

class GeicoAutoFiller:
    def __init__(self):
        self.driver = None
        self.status_window = None
        self.status_label = None
        self.progress_bar = None
        self.field_labels = {}
        self.data = None
        
    def load_data(self):
        """Load quote data from JSON file"""
        try:
            with open('truck_quote_example.json', 'r') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def create_status_window(self):
        """Create visual status window"""
        self.status_window = tk.Tk()
        self.status_window.title("GEICO Auto Filler Status")
        self.status_window.geometry("400x500")
        
        # Title
        title = tk.Label(self.status_window, text="GEICO Quote Auto-Filler", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(self.status_window, text="Ready to start", 
                                   font=("Arial", 12), fg="blue")
        self.status_label.pack(pady=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(self.status_window, length=350, 
                                          mode='determinate')
        self.progress_bar.pack(pady=10)
        
        # Field status frame
        field_frame = tk.LabelFrame(self.status_window, text="Field Status", 
                                   font=("Arial", 10, "bold"))
        field_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Field labels
        fields = [
            "ZIP Code", "Vehicle Year", "Vehicle Make", "Vehicle Model",
            "First Name", "Last Name", "Date of Birth", "Email",
            "Phone", "Coverage Selection", "Deductibles"
        ]
        
        for field in fields:
            frame = tk.Frame(field_frame)
            frame.pack(fill="x", padx=10, pady=2)
            
            label = tk.Label(frame, text=f"{field}:", width=20, anchor="w")
            label.pack(side="left")
            
            status = tk.Label(frame, text="⏳ Pending", fg="gray")
            status.pack(side="left")
            
            self.field_labels[field] = status
        
        # Buttons
        button_frame = tk.Frame(self.status_window)
        button_frame.pack(pady=10)
        
        self.start_button = tk.Button(button_frame, text="Start Auto-Fill", 
                                     command=self.start_filling, bg="green", 
                                     fg="white", font=("Arial", 10, "bold"))
        self.start_button.pack(side="left", padx=5)
        
        close_button = tk.Button(button_frame, text="Close", 
                               command=self.close_all, bg="red", fg="white")
        close_button.pack(side="left", padx=5)
        
    def update_status(self, message, color="blue"):
        """Update status message"""
        if self.status_label:
            self.status_label.config(text=message, fg=color)
            self.status_window.update()
    
    def update_field_status(self, field, status, color="green"):
        """Update individual field status"""
        if field in self.field_labels:
            if status == "done":
                self.field_labels[field].config(text="✅ Complete", fg=color)
            elif status == "working":
                self.field_labels[field].config(text="⚡ Filling...", fg="orange")
            elif status == "error":
                self.field_labels[field].config(text="❌ Error", fg="red")
            self.status_window.update()
    
    def update_progress(self, value):
        """Update progress bar"""
        if self.progress_bar:
            self.progress_bar['value'] = value
            self.status_window.update()
    
    def fill_geico_form(self):
        """Main function to fill GEICO form"""
        try:
            self.update_status("Opening GEICO website...", "blue")
            self.driver = webdriver.Chrome()  # Or Firefox()
            self.driver.get("https://www.geico.com")
            self.driver.maximize_window()
            
            wait = WebDriverWait(self.driver, 10)
            
            # Click on Auto insurance
            self.update_status("Navigating to auto quote...", "blue")
            auto_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Auto")))
            auto_link.click()
            self.update_progress(10)
            
            # Start quote
            start_quote = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn--primary")))
            start_quote.click()
            self.update_progress(20)
            
            # Fill ZIP code
            self.update_field_status("ZIP Code", "working")
            zip_input = wait.until(EC.presence_of_element_located((By.ID, "bundle-zip")))
            zip_input.clear()
            zip_input.send_keys(self.data["driver"]["address"]["zip"])
            self.update_field_status("ZIP Code", "done")
            self.update_progress(30)
            
            # Continue button
            continue_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
            
            # Vehicle information
            self.update_status("Filling vehicle information...", "blue")
            time.sleep(2)
            
            # Year
            self.update_field_status("Vehicle Year", "working")
            year_select = Select(wait.until(EC.presence_of_element_located((By.NAME, "year"))))
            year_select.select_by_visible_text(str(self.data["vehicle"]["year"]))
            self.update_field_status("Vehicle Year", "done")
            self.update_progress(40)
            
            # Make
            self.update_field_status("Vehicle Make", "working")
            make_select = Select(self.driver.find_element(By.NAME, "make"))
            make_select.select_by_visible_text(self.data["vehicle"]["make"])
            self.update_field_status("Vehicle Make", "done")
            self.update_progress(50)
            
            # Model
            self.update_field_status("Vehicle Model", "working")
            model_select = Select(self.driver.find_element(By.NAME, "model"))
            model_select.select_by_visible_text(self.data["vehicle"]["model"])
            self.update_field_status("Vehicle Model", "done")
            self.update_progress(60)
            
            # Personal information
            self.update_status("Filling personal information...", "blue")
            
            # First name
            self.update_field_status("First Name", "working")
            first_name = self.driver.find_element(By.NAME, "firstName")
            first_name.send_keys(self.data["driver"]["first_name"])
            self.update_field_status("First Name", "done")
            self.update_progress(70)
            
            # Last name
            self.update_field_status("Last Name", "working")
            last_name = self.driver.find_element(By.NAME, "lastName")
            last_name.send_keys(self.data["driver"]["last_name"])
            self.update_field_status("Last Name", "done")
            self.update_progress(80)
            
            # Email
            self.update_field_status("Email", "working")
            email = self.driver.find_element(By.NAME, "email")
            email.send_keys(self.data["driver"]["email"])
            self.update_field_status("Email", "done")
            self.update_progress(90)
            
            # Phone
            self.update_field_status("Phone", "working")
            phone = self.driver.find_element(By.NAME, "phone")
            phone.send_keys(self.data["driver"]["phone"])
            self.update_field_status("Phone", "done")
            self.update_progress(100)
            
            self.update_status("✅ Form filled successfully!", "green")
            messagebox.showinfo("Success", "GEICO form has been filled with test data!")
            
        except TimeoutException:
            self.update_status("❌ Timeout waiting for page to load", "red")
            messagebox.showerror("Error", "Page took too long to load")
        except NoSuchElementException as e:
            self.update_status(f"❌ Could not find element: {e}", "red")
            messagebox.showerror("Error", f"Could not find form element: {e}")
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}", "red")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def start_filling(self):
        """Start the filling process in a separate thread"""
        self.start_button.config(state="disabled")
        self.progress_bar['value'] = 0
        
        # Reset all field statuses
        for field in self.field_labels:
            self.field_labels[field].config(text="⏳ Pending", fg="gray")
        
        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.fill_geico_form)
        thread.daemon = True
        thread.start()
    
    def close_all(self):
        """Close browser and window"""
        if self.driver:
            self.driver.quit()
        if self.status_window:
            self.status_window.destroy()
    
    def run(self):
        """Main entry point"""
        if not self.load_data():
            messagebox.showerror("Error", "Could not load truck_quote_example.json")
            return
        
        self.create_status_window()
        
        # Show loaded data info
        info_text = f"Loaded quote data:\n"
        info_text += f"• Driver: {self.data['driver']['first_name']} {self.data['driver']['last_name']}\n"
        info_text += f"• Vehicle: {self.data['vehicle']['year']} {self.data['vehicle']['make']} {self.data['vehicle']['model']}\n"
        info_text += f"• ZIP: {self.data['driver']['address']['zip']}"
        
        messagebox.showinfo("Data Loaded", info_text)
        
        self.status_window.mainloop()

if __name__ == "__main__":
    print("Starting GEICO Auto Filler with Visual Interface...")
    print("Make sure you have Chrome/Firefox and the appropriate driver installed!")
    print("(ChromeDriver for Chrome, GeckoDriver for Firefox)")
    
    filler = GeicoAutoFiller()
    filler.run()