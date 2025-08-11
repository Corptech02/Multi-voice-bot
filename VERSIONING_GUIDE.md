# Claude Voice Assistant - Versioning Guide

## Overview
This project uses a Git-like versioning system to manage code changes safely.

## Directory Structure
```
/current/
├── voice_tts_realtime.py      # Active running version
├── versions/                   # Stable release versions
│   └── v1.0.0/                # First stable release
│       ├── voice_tts_realtime.py
│       └── VERSION_INFO.md
├── branches/                   # Development branches
│   └── (feature branches go here)
└── VERSIONING_GUIDE.md        # This file
```

## Workflow

### 1. Creating a New Branch
When you want to make changes:
```bash
# Create a new branch
cp voice_tts_realtime.py branches/feature-[description].py
# Example: branches/feature-add-volume-control.py
```

### 2. Testing Changes
- Edit the branch file
- Test thoroughly
- Document what changed

### 3. Merging Changes
If the changes work well:
```bash
# Backup current version
cp voice_tts_realtime.py voice_tts_realtime.backup.py
# Apply the branch
cp branches/feature-[description].py voice_tts_realtime.py
```

### 4. Creating a New Version
When significant changes are stable:
```bash
# Create new version directory
mkdir versions/v1.1.0
# Save the files
cp voice_tts_realtime.py versions/v1.1.0/
# Document the changes
```

## Version Numbering
- **v1.0.0** - Major.Minor.Patch
- **Major**: Breaking changes
- **Minor**: New features
- **Patch**: Bug fixes

## Rollback Procedure
If something goes wrong:
```bash
# Stop the current service
# Restore from a stable version
cp versions/v1.0.0/voice_tts_realtime.py voice_tts_realtime.py
# Restart the service
```

## Current Stable Version
**v1.0.0** - The baseline version with core functionality

## Best Practices
1. Never edit version files directly
2. Always create a branch for new features
3. Test thoroughly before merging
4. Document all changes
5. Keep version history clean