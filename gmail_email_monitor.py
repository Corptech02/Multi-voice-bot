#!/usr/bin/env python3
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GmailEmailMonitor:
    """Gmail API-based email monitor for COI requests."""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """Initialize Gmail monitor with OAuth credentials."""
        self.creds = None
        self.service = None
        
        # Default paths if not provided
        if not credentials_path:
            credentials_path = "/home/corp06/software_projects/ClaudeVoiceBot/current/credentials/credentials.json"
        if not token_path:
            token_path = "/home/corp06/software_projects/ClaudeVoiceBot/current/credentials/token.json"
            
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.last_message_id = None
        
    def connect(self) -> bool:
        """Connect to Gmail using OAuth2."""
        try:
            # Load existing token
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
                logger.info("Loaded existing Gmail token")
            
            # Refresh or get new token if needed
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                    logger.info("Refreshed Gmail token")
                else:
                    if os.path.exists(self.credentials_path):
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, self.SCOPES)
                        self.creds = flow.run_local_server(port=0)
                        logger.info("Got new Gmail token")
                    else:
                        logger.error(f"Credentials file not found: {self.credentials_path}")
                        return False
                
                # Save the token
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            # Build the service
            self.service = build('gmail', 'v1', credentials=self.creds)
            
            # Test connection
            profile = self.service.users().getProfile(userId='me').execute()
            logger.info(f"Connected to Gmail account: {profile.get('emailAddress')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {str(e)}")
            return False
    
    def _extract_text_from_message(self, message: dict) -> str:
        """Extract text content from Gmail message."""
        text_content = ""
        
        def extract_from_parts(parts):
            nonlocal text_content
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part.get('body', {}):
                        try:
                            text_content += base64.urlsafe_b64decode(
                                part['body']['data']).decode('utf-8')
                        except Exception as e:
                            logger.error(f"Error decoding part: {e}")
                elif 'parts' in part:
                    extract_from_parts(part['parts'])
        
        payload = message.get('payload', {})
        if 'parts' in payload:
            extract_from_parts(payload['parts'])
        elif payload.get('body', {}).get('data'):
            try:
                text_content = base64.urlsafe_b64decode(
                    payload['body']['data']).decode('utf-8')
            except Exception as e:
                logger.error(f"Error decoding body: {e}")
        
        return text_content
    
    def fetch_emails(self, check_unread: bool = True) -> List[Dict[str, Any]]:
        """Fetch new emails and check for COI requests."""
        if not self.service:
            logger.error("Gmail service not initialized")
            return []
        
        try:
            # Build search query
            query_parts = []
            query_parts.append('(subject:"COI" OR subject:"Certificate of Insurance" OR subject:"CERTIFICATE OF INSURANCE")')
            
            if check_unread:
                query_parts.append('is:unread')
            
            query = ' '.join(query_parts)
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            coi_requests = []
            
            for msg in messages:
                try:
                    # Get full message
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()
                    
                    # Extract headers
                    headers = {}
                    for header in message['payload'].get('headers', []):
                        headers[header['name'].lower()] = header['value']
                    
                    # Extract text content
                    text_content = self._extract_text_from_message(message)
                    
                    # Parse COI request details (basic extraction)
                    request_data = {
                        "id": f"REQ{msg['id'][:8]}",
                        "timestamp": datetime.now().isoformat(),
                        "from_email": headers.get('from', 'unknown@email.com'),
                        "subject": headers.get('subject', 'No Subject'),
                        "original_text": text_content,
                        "certificate_holder": self._extract_field(text_content, ["Certificate Holder:", "Holder:", "For:"]),
                        "insured_name": self._extract_field(text_content, ["Insured:", "Company:", "Organization:"]),
                        "project_description": self._extract_field(text_content, ["Project:", "Description:", "Job:"]),
                        "coverage_requirements": self._extract_field(text_content, ["Coverage:", "Requirements:", "Limits:"]),
                        "additional_insureds": [],
                        "status": "Pending",
                        "preview_content": None,
                        "ai_confidence": 0.85
                    }
                    
                    coi_requests.append(request_data)
                    
                    # Mark as read
                    if check_unread:
                        self.service.users().messages().modify(
                            userId='me',
                            id=msg['id'],
                            body={'removeLabelIds': ['UNREAD']}
                        ).execute()
                    
                except Exception as e:
                    logger.error(f"Error processing message {msg['id']}: {e}")
                    continue
            
            logger.info(f"Found {len(coi_requests)} COI requests")
            return coi_requests
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    def _extract_field(self, text: str, keywords: List[str]) -> str:
        """Extract field value from text based on keywords."""
        lines = text.split('\n')
        for i, line in enumerate(lines):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Get the rest of the line after the keyword
                    parts = line.split(keyword, 1)
                    if len(parts) > 1:
                        value = parts[1].strip()
                        if value:
                            return value
                    # Check next line if current line only has keyword
                    if i + 1 < len(lines):
                        return lines[i + 1].strip()
        return ""
    
    def monitor_loop(self, callback=None, interval: int = 60):
        """Monitor Gmail for new COI requests."""
        logger.info(f"Starting Gmail monitor loop with {interval}s interval")
        
        while True:
            try:
                # Fetch new emails
                new_requests = self.fetch_emails(check_unread=True)
                
                if new_requests and callback:
                    callback(new_requests)
                
                # Wait before next check
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(interval)