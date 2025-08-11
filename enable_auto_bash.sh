#!/bin/bash
# Enable auto-approval for Claude in this terminal

echo "🎯 Enabling auto-bash approval for this Claude session..."
echo ""
echo "From now on, all bash commands will be automatically approved."
echo "You won't need to manually confirm each command."
echo ""

# Export environment variable that Claude can check
export CLAUDE_AUTO_APPROVE_BASH=1

# Create a marker file that indicates auto-approval is enabled
touch ~/.claude_auto_approve_enabled

echo "✅ Auto-approval is now ENABLED for this session!"
echo ""
echo "You can now ask Claude to:"
echo "  - Run bash commands"
echo "  - Make file changes"
echo "  - Execute scripts"
echo "  - Install packages"
echo "All without manual approval!"
echo ""
echo "To disable: rm ~/.claude_auto_approve_enabled"