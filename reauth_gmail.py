#!/usr/bin/env python3
"""
Re-authenticate Gmail OAuth for COI email monitoring.
This will open a browser to authenticate the quartet02 account.
"""

import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def main():
    creds_path = "/home/corp06/software_projects/ClaudeVoiceBot/current/credentials/credentials.json"
    token_path = "/home/corp06/software_projects/ClaudeVoiceBot/current/credentials/token.json"
    
    print("Gmail OAuth Re-authentication Tool")
    print("=" * 50)
    
    if not os.path.exists(creds_path):
        print(f"ERROR: OAuth credentials file not found at {creds_path}")
        print("Please ensure the credentials.json file exists.")
        return
    
    print(f"Using credentials from: {creds_path}")
    print(f"Token will be saved to: {token_path}")
    print()
    
    # Delete existing token to force re-authentication
    if os.path.exists(token_path):
        print("Removing existing token to force re-authentication...")
        os.remove(token_path)
    
    try:
        # Run the OAuth flow
        print("Starting OAuth flow...")
        print("A browser window will open for authentication.")
        print("Please log in with the quartet02@gmail.com account.")
        print()
        
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(
            port=0,
            authorization_prompt_message='Please visit this URL to authorize this application: {url}',
            success_message='The authentication flow has completed. You may close this window.',
            open_browser=True
        )
        
        # Save the token
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        print("✓ Authentication successful!")
        
        # Test the connection
        print("\nTesting connection...")
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"✓ Connected to Gmail account: {profile.get('emailAddress')}")
        print(f"  Messages total: {profile.get('messagesTotal')}")
        print(f"  Threads total: {profile.get('threadsTotal')}")
        
        print("\nAuthentication complete! The COI backend can now monitor emails.")
        
    except Exception as e:
        print(f"\nERROR during authentication: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're logged into the correct Google account (quartet02)")
        print("2. If you see 'Access blocked', the app may need to be verified")
        print("3. Try using an App Password instead of OAuth")

if __name__ == "__main__":
    main()