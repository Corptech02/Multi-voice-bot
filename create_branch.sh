#!/bin/bash
# Script to create a new development branch

if [ -z "$1" ]; then
    echo "Usage: ./create_branch.sh <branch-name>"
    echo "Example: ./create_branch.sh add-volume-control"
    exit 1
fi

BRANCH_NAME="feature-$1"
BRANCH_FILE="branches/${BRANCH_NAME}.py"
DATE=$(date +"%Y-%m-%d")

# Create branch
cp voice_tts_realtime.py "$BRANCH_FILE"

# Create branch info file
cat > "branches/${BRANCH_NAME}.info" << EOF
Branch: ${BRANCH_NAME}
Created: ${DATE}
Base Version: Current voice_tts_realtime.py
Status: In Development

Purpose:
[Describe the purpose of this branch]

Changes:
[List changes as you make them]
EOF

echo "✓ Created branch: ${BRANCH_NAME}"
echo "✓ Branch file: ${BRANCH_FILE}"
echo "✓ Info file: branches/${BRANCH_NAME}.info"
echo ""
echo "Next steps:"
echo "1. Edit ${BRANCH_FILE} to make your changes"
echo "2. Update branches/${BRANCH_NAME}.info with your changes"
echo "3. Test thoroughly"
echo "4. Use ./merge_branch.sh ${BRANCH_NAME} when ready"