#!/usr/bin/env python3
"""
Multi-line response fix - This is just the capture_responses function
that should replace the one in multi_tab_voice_http.py
"""

def capture_responses(session_id, tab_id):
    """Capture responses from Claude for a specific session"""
    last_content = ""
    last_position = 0
    processed_responses = set()
    
    print(f"[CAPTURE] Started capture thread for tab {tab_id}, session {session_id}")
    
    while tab_id in capture_threads:
        try:
            # Capture current output
            content = orchestrator.capture_response(session_id)
            
            if content and len(content) > last_position:
                # Get only new content
                new_content = content[last_position:]
                
                # Look for response patterns in the new content
                lines = new_content.split('\n')
                current_response = []
                in_response = False
                
                for line in lines:
                    cleaned_line = line.strip()
                    
                    # Check for real-time stats first
                    stats = extract_stats_from_output(cleaned_line)
                    if stats["time"] or stats["tokens"]:
                        if tab_id not in tab_stats:
                            tab_stats[tab_id] = {"time": "", "tokens": ""}
                        tab_stats[tab_id].update(stats)
                        
                        socketio.emit('realtime_stats', {
                            'tab_id': tab_id,
                            'time': stats["time"],
                            'tokens': stats["tokens"]
                        })
                    
                    # Check for start of Claude response
                    if cleaned_line.startswith('●'):
                        # Start new response
                        if current_response and in_response:
                            # Send previous response if any
                            full_response = '\n'.join(current_response)
                            if len(full_response.strip()) > 3:
                                response_hash = hash(full_response)
                                if response_hash not in processed_responses:
                                    processed_responses.add(response_hash)
                                    socketio.emit('response', {
                                        'tab_id': tab_id,
                                        'text': full_response
                                    })
                                    orchestrator.store_bot_response(tab_id, full_response)
                                    print(f"[RESPONSE] Tab {tab_id}: {full_response[:100]}...")
                        
                        # Start new response
                        response_text = cleaned_line[1:].strip()
                        current_response = [response_text] if response_text else []
                        in_response = True
                        
                    elif in_response:
                        # Continue collecting response
                        if line.startswith('│') and line.endswith('│'):
                            # End of response box
                            if current_response:
                                full_response = '\n'.join(current_response)
                                if len(full_response.strip()) > 3:
                                    # Skip tool calls
                                    tool_patterns = ['List(.', 'Call(', 'Read(', 'Edit(', 'Write(', 
                                                   'Bash(', 'MultiEdit(', 'Grep(', 'Glob(', 'LS(',
                                                   'WebFetch(', 'WebSearch(', 'NotebookRead(', 'NotebookEdit(']
                                    if not any(full_response.strip().startswith(p) for p in tool_patterns):
                                        response_hash = hash(full_response)
                                        if response_hash not in processed_responses:
                                            processed_responses.add(response_hash)
                                            socketio.emit('response', {
                                                'tab_id': tab_id,
                                                'text': full_response
                                            })
                                            orchestrator.store_bot_response(tab_id, full_response)
                                            print(f"[RESPONSE] Tab {tab_id}: {full_response[:100]}...")
                                
                                current_response = []
                                in_response = False
                        elif line.startswith('│ ') and line.endswith(' │'):
                            # Inside response box - extract content
                            content_line = line[2:-2].strip()
                            if content_line:
                                current_response.append(content_line)
                        elif cleaned_line and not line.startswith('╭') and not line.startswith('╰'):
                            # Regular line that might be part of response
                            current_response.append(cleaned_line)
                
                last_position = len(content)
                last_content = content
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error capturing response for session {session_id}: {e}")
            time.sleep(1)