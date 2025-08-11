#!/bin/bash
# Script to rollback to a specific version

echo "=== Claude Voice Assistant - Version Rollback ==="
echo ""
echo "Available versions:"
ls -la versions/
echo ""
echo "Current version running on port 8103"
echo ""

if [ -z "$1" ]; then
    echo "Usage: ./rollback.sh <version>"
    echo "Example: ./rollback.sh v1.0.0"
    exit 1
fi

VERSION="$1"
VERSION_FILE="versions/${VERSION}/voice_tts_realtime.py"

# Check if version exists
if [ ! -f "$VERSION_FILE" ]; then
    echo "Error: Version not found: $VERSION_FILE"
    exit 1
fi

echo "This will rollback to version: ${VERSION}"
read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create safety backup
    SAFETY_BACKUP="backups/pre_rollback_$(date +%Y%m%d_%H%M%S).py"
    cp voice_tts_realtime.py "$SAFETY_BACKUP"
    echo "✓ Created safety backup: $SAFETY_BACKUP"
    
    # Perform rollback
    cp "$VERSION_FILE" voice_tts_realtime.py
    echo "✓ Rolled back to ${VERSION}"
    
    # Log the rollback
    echo "$(date): Rolled back to ${VERSION}" >> rollback_history.log
    
    echo ""
    echo "Rollback complete! Remember to restart the voice assistant service."
else
    echo "Rollback cancelled."
fi