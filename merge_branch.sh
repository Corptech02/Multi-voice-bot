#!/bin/bash
# Script to merge a branch into the main version

if [ -z "$1" ]; then
    echo "Usage: ./merge_branch.sh <branch-name>"
    echo "Example: ./merge_branch.sh feature-add-volume-control"
    exit 1
fi

BRANCH_NAME="$1"
BRANCH_FILE="branches/${BRANCH_NAME}.py"
BACKUP_NAME="voice_tts_realtime.backup.$(date +%Y%m%d_%H%M%S).py"

# Check if branch exists
if [ ! -f "$BRANCH_FILE" ]; then
    echo "Error: Branch file not found: $BRANCH_FILE"
    exit 1
fi

echo "=== Merge Branch: ${BRANCH_NAME} ==="
echo ""
echo "This will:"
echo "1. Backup current voice_tts_realtime.py to ${BACKUP_NAME}"
echo "2. Replace it with ${BRANCH_FILE}"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create backup
    cp voice_tts_realtime.py "backups/${BACKUP_NAME}"
    echo "✓ Created backup: backups/${BACKUP_NAME}"
    
    # Merge branch
    cp "$BRANCH_FILE" voice_tts_realtime.py
    echo "✓ Merged ${BRANCH_NAME} into voice_tts_realtime.py"
    
    # Update merge log
    echo "$(date): Merged ${BRANCH_NAME}" >> merge_history.log
    
    echo ""
    echo "Merge complete! Remember to:"
    echo "1. Restart the voice assistant service"
    echo "2. Test the changes"
    echo "3. Create a new version if this is a significant update"
else
    echo "Merge cancelled."
fi