#!/bin/bash
# Force Claude into a simpler mode
export TERM=dumb
export NO_COLOR=1
export CLAUDE_NO_INTERACTIVE=1

# Use unbuffer to handle PTY issues
exec unbuffer -p /usr/local/bin/claude --dangerously-skip-permissions