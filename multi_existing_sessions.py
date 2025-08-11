#!/usr/bin/env python3
"""Multi-tab bot using existing Claude sessions"""
import ssl
import threading
import queue
from datetime import datetime
from multi_tab_voice_http import app, socketio, capture_responses, response_queues, capture_threads
from orchestrator_simple import orchestrator, BotSession

# Use existing sessions that have auto-approval
EXISTING_SESSIONS = [
    ("claude_f7304c08", "f7304c08", "Tab 1"),
    ("claude_9191c9fd", "9191c9fd", "Tab 2"),
    ("claude_ea80a41c", "ea80a41c", "Tab 3"),
    ("claude_30bbf96f", "30bbf96f", "Tab 4")
]

if __name__ == '__main__':
    # Clear old sessions
    orchestrator.sessions.clear()
    
    # Add existing sessions
    print("Adding existing Claude sessions with auto-approval...")
    for i, (tmux_session, session_id, name) in enumerate(EXISTING_SESSIONS):
        tab_id = f"tab_existing_{i}"
        session = BotSession(
            session_id=session_id,
            tab_id=tab_id,
            project_name=name,
            tmux_session=tmux_session,
            created_at=datetime.now()
        )
        orchestrator.sessions[tab_id] = session
        print(f"  ✓ {name}: {tmux_session}")
        
        # Start capture thread for this session
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
    print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT - EXISTING SESSIONS")
    print("="*60)
    print("✨ Using 4 existing Claude sessions with auto-approval")
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