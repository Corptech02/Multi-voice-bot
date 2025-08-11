#!/bin/bash
# Wrapper script to run Claude with proper terminal settings
export TERM=xterm-256color
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Force interactive mode
exec script -qfc "/usr/local/bin/claude --dangerously-skip-permissions" /dev/null