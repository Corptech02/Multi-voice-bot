#!/usr/bin/env python3
import imaplib
import email
from email.header import decode_header
import json
import logging
from datetime import datetime
import re
import time
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class EmailMonitor:
    def __init__(self, config_file: str = "email_config.json"):
        """Initialize email monitor with configuration from file."""
        self.config_file = config_file
        self.config = self.load_config()
        self.imap = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load email configuration from JSON file."""
        if not os.path.exists(self.config_file):
            logger.error(f"Configuration file {self.config_file} not found!")
            logger.info("Please create email_config.json from email_config_template.json")
            raise FileNotFoundError(f"Configuration file {self.config_file} not found")
            
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            # Create IMAP connection
            if self.config.get('use_ssl', True):
                self.imap = imaplib.IMAP4_SSL(
                    self.config['imap_server'],
                    self.config.get('imap_port', 993)
                )
            else:
                self.imap = imaplib.IMAP4(
                    self.config['imap_server'],
                    self.config.get('imap_port', 143)
                )
            
            # Login
            self.imap.login(self.config['email_account'], self.config['password'])
            logger.info(f"Successfully connected to {self.config['email_account']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass
    
    def extract_coi_info(self, email_body: str) -> Dict[str, Any]:
        """Extract COI information from email body using patterns."""
        info = {
            "certificate_holder": None,
            "insured_name": None,
            "project_description": None,
            "coverage_requirements": None,
            "additional_insureds": []
        }
        
        # Pattern matching for common COI request fields
        patterns = {
            "certificate_holder": [
                r"certificate holder[:\s]+([^\n]+)",
                r"cert holder[:\s]+([^\n]+)",
                r"holder[:\s]+([^\n]+)",
                r"for[:\s]+([^\n]+(?:LLC|Inc|Corp|Company|Properties|Group))"
            ],
            "insured_name": [
                r"insured[:\s]+([^\n]+)",
                r"contractor[:\s]+([^\n]+)",
                r"company[:\s]+([^\n]+)"
            ],
            "project_description": [
                r"project[:\s]+([^\n]+)",
                r"job site[:\s]+([^\n]+)",
                r"location[:\s]+([^\n]+)",
                r"address[:\s]+([^\n]+)"
            ],
            "coverage_requirements": [
                r"coverage[:\s]+([^\n]+)",
                r"required[:\s]+([^\n]+)",
                r"limits[:\s]+([^\n]+)",
                r"GL[:\s]+([^\n]+)"
            ]
        }
        
        # Try to extract information using patterns
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, email_body, re.IGNORECASE)
                if match:
                    if field == "additional_insureds":
                        info[field].append(match.group(1).strip())
                    else:
                        info[field] = match.group(1).strip()
                    break
        
        # Calculate AI confidence based on how many fields were extracted
        extracted_count = sum(1 for v in info.values() if v and (v != [] if isinstance(v, list) else True))
        info['ai_confidence'] = round(extracted_count / 5.0, 2)
        
        return info
    
    def fetch_emails(self) -> List[Dict[str, Any]]:
        """Fetch new emails and convert them to COI requests."""
        if not self.imap:
            if not self.connect():
                return []
        
        try:
            # Select folder
            folder = self.config.get('folder', 'INBOX')
            self.imap.select(folder)
            
            # Search for emails
            search_criteria = ' '.join(self.config.get('search_criteria', ['UNSEEN']))
            typ, data = self.imap.search(None, search_criteria)
            
            if typ != 'OK':
                logger.error("Failed to search emails")
                return []
            
            email_ids = data[0].split()
            coi_requests = []
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    typ, msg_data = self.imap.fetch(email_id, '(RFC822)')
                    if typ != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extract basic info
                    subject = self.decode_header_value(msg['Subject'])
                    from_addr = self.decode_header_value(msg['From'])
                    date_str = msg['Date']
                    
                    # Extract body
                    body = self.get_email_body(msg)
                    
                    # Extract COI information
                    coi_info = self.extract_coi_info(body)
                    
                    # Create COI request
                    coi_request = {
                        "id": f"REQ{datetime.now().strftime('%Y%m%d%H%M%S')}_{email_id.decode()}",
                        "timestamp": datetime.now().isoformat(),
                        "from_email": from_addr,
                        "subject": subject,
                        "original_text": body,
                        "certificate_holder": coi_info['certificate_holder'],
                        "insured_name": coi_info['insured_name'],
                        "project_description": coi_info['project_description'],
                        "coverage_requirements": coi_info['coverage_requirements'],
                        "additional_insureds": coi_info['additional_insureds'],
                        "status": "Pending",
                        "preview_content": None,
                        "ai_confidence": coi_info['ai_confidence']
                    }
                    
                    coi_requests.append(coi_request)
                    
                    # Mark as read if configured
                    if self.config.get('mark_as_read', False):
                        self.imap.store(email_id, '+FLAGS', '\\Seen')
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {str(e)}")
                    continue
            
            return coi_requests
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    def decode_header_value(self, header_value: str) -> str:
        """Decode email header value."""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        result = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += part
        return result
    
    def get_email_body(self, msg) -> str:
        """Extract email body from message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        body = re.sub('<[^<]+?>', '', html)
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())
        
        return body.strip()

    def monitor_loop(self, callback=None):
        """Continuous monitoring loop."""
        interval = self.config.get('check_interval_seconds', 60)
        
        while True:
            try:
                logger.info("Checking for new emails...")
                new_requests = self.fetch_emails()
                
                if new_requests:
                    logger.info(f"Found {len(new_requests)} new COI requests")
                    if callback:
                        callback(new_requests)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(interval)

if __name__ == "__main__":
    # Test the email monitor
    logging.basicConfig(level=logging.INFO)
    
    try:
        monitor = EmailMonitor()
        print("Email monitor initialized successfully")
        
        # Test connection
        if monitor.connect():
            print("Connected to email server successfully")
            
            # Fetch emails once
            requests = monitor.fetch_emails()
            print(f"Found {len(requests)} COI requests")
            
            for req in requests:
                print(f"\nRequest ID: {req['id']}")
                print(f"From: {req['from_email']}")
                print(f"Subject: {req['subject']}")
                print(f"Certificate Holder: {req['certificate_holder']}")
                print(f"AI Confidence: {req['ai_confidence']}")
            
            monitor.disconnect()
        else:
            print("Failed to connect to email server")
            
    except FileNotFoundError:
        print("\nEmail configuration not found!")
        print("Please create email_config.json from email_config_template.json")
        print("and add your email credentials.")