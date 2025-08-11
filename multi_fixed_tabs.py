#!/usr/bin/env python3
"""Multi-tab bot with fixed tab IDs matching existing sessions"""
import ssl
import threading
import queue
from datetime import datetime
from multi_tab_voice_http import app, socketio, capture_responses, response_queues, capture_threads, HTML_TEMPLATE
from orchestrator_simple import orchestrator, BotSession

# Use existing sessions with FIXED tab IDs
FIXED_TABS = [
    ("tab_existing_0", "claude_f7304c08", "f7304c08", "Tab 1"),
    ("tab_existing_1", "claude_9191c9fd", "9191c9fd", "Tab 2"),
    ("tab_existing_2", "claude_ea80a41c", "ea80a41c", "Tab 3"),
    ("tab_existing_3", "claude_30bbf96f", "30bbf96f", "Tab 4")
]

# Create a modified HTML template with fixed tabs
FIXED_HTML = HTML_TEMPLATE.replace(
    "// Load saved tabs or create default ones",
    """// Use fixed tabs that match our existing sessions
            tabs = {
                'tab_existing_0': { name: 'Tab 1', id: 'tab_existing_0' },
                'tab_existing_1': { name: 'Tab 2', id: 'tab_existing_1' },
                'tab_existing_2': { name: 'Tab 3', id: 'tab_existing_2' },
                'tab_existing_3': { name: 'Tab 4', id: 'tab_existing_3' }
            };
            
            // Don't create new sessions or use localStorage
            function loadOrCreateTabs() {
                console.log('Using fixed tabs:', tabs);
                displayTabs();
                
                // Set first tab as active
                activeTabId = 'tab_existing_0';
                switchTab(activeTabId);
            }
            
            // Override createSessionsInBackground to do nothing
            function createSessionsInBackground() {
                console.log('Sessions already exist, skipping creation');
            }
            
            // Load tabs"""
).replace(
    "loadOrCreateTabs();",
    "loadOrCreateTabs();"
)

# Override the index route
@app.route('/', methods=['GET'])
def fixed_index():
    return FIXED_HTML

if __name__ == '__main__':
    # Clear old sessions
    orchestrator.sessions.clear()
    
    # Add existing sessions with fixed IDs
    print("Setting up fixed tab sessions...")
    for tab_id, tmux_session, session_id, name in FIXED_TABS:
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            project_name=name,
            tmux_session=tmux_session,
            created_at=datetime.now()
        )
        orchestrator.sessions[tab_id] = session
        print(f"  ✓ {name}: {tmux_session} -> {tab_id}")
        
        # Start capture thread
        response_queue = queue.Queue()
        response_queues[tab_id] = response_queue
        
        capture_thread = threading.Thread(
            target=capture_responses,
            args=(session_id, tab_id),
            daemon=True
        )
        capture_threads[tab_id] = capture_thread
        capture_thread.start()
        print(f"  ✓ Started capture thread for {name}")
    
    print("\n" + "="*60)
    print("🎙️ MULTI-TAB CLAUDE - FIXED SESSIONS")
    print("="*60)
    print("✨ Using 4 existing Claude sessions with fixed tab IDs")
    print("")
    print("📱 Access at: https://192.168.40.232:8402")
    print("⚠️  Accept the certificate warning to continue")
    print("="*60 + "\n")
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    socketio.run(app, 
                 host='0.0.0.0',
                 port=8402,
                 ssl_context=context,
                 debug=False,
                 allow_unsafe_werkzeug=True)