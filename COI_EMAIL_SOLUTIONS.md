# COI Email Monitoring Solutions

## Overview
This document provides practical solutions for populating the COI tool with requests without requiring Gmail OAuth authentication.

## Current Issues Identified

1. **Gmail Authentication Problems**:
   - The `coi_backend_gmail.py` requires Gmail OAuth credentials
   - Missing dependencies in some virtual environments
   - Token authentication failures

2. **Running Services**:
   - `coi_backend_simple.py` is currently running on port 8001
   - It has mock monitoring capabilities but doesn't generate data automatically

## Solutions Implemented

### 1. Mock Data Generator (`coi_mock_data_generator.py`)

A standalone tool to generate realistic COI request data:

```bash
# Generate and view a sample request
python coi_mock_data_generator.py

# Generate 10 requests and save to file
python coi_mock_data_generator.py --count 10 --save-file mock_coi_requests.json

# Populate the running backend with 5 mock requests
python coi_mock_data_generator.py --count 5 --populate --backend-url http://localhost:8001
```

Features:
- Generates realistic vendor names, certificate holders, and project descriptions
- Creates properly formatted email content
- Can save to JSON file or send directly to backend API
- No authentication required

### 2. Enhanced Backend with Mock Monitoring (`coi_backend_with_mock.py`)

An improved backend that simulates email monitoring:

```bash
# Run the mock-enabled backend
python coi_backend_with_mock.py 8001
```

Features:
- Automatic mock email generation every 30 seconds when monitoring is active
- Manual scan endpoint to trigger immediate mock emails
- Bulk generation endpoint for testing
- All original COI functionality preserved

### 3. Test Script (`test_mock_coi_system.py`)

A comprehensive test script to verify the mock system:

```bash
python test_mock_coi_system.py
```

This script:
- Verifies backend health
- Generates mock requests
- Tests monitoring start/stop
- Downloads sample PDFs
- Shows complete workflow

## Quick Start Guide

### Option 1: Use Current Simple Backend with Mock Data

1. Keep the current `coi_backend_simple.py` running
2. Generate mock data:
   ```bash
   python coi_mock_data_generator.py --count 10 --populate
   ```

### Option 2: Switch to Mock-Enabled Backend

1. Stop current backend (if running)
2. Start the mock-enabled backend:
   ```bash
   python coi_backend_with_mock.py 8001
   ```
3. Start monitoring via API or UI
4. Mock emails will be generated automatically

### Option 3: Manual Data Population

1. Generate a JSON file with mock data:
   ```bash
   python coi_mock_data_generator.py --count 20 --save-file coi_requests.json
   ```
2. Use the generated file for testing or import into your system

## API Endpoints

### Mock-Specific Endpoints

- `POST /api/v1/requests/mock/generate?count=5` - Generate mock requests
- `POST /api/v1/requests/monitoring/scan` - Trigger manual scan (generates mock emails)
- `GET /api/v1/requests/monitoring/status` - Shows monitoring status with mode indicator

### Standard COI Endpoints

- `GET /api/v1/requests` - Get all COI requests
- `POST /api/v1/requests` - Create new request
- `GET /api/v1/requests/{id}` - Get specific request
- `PUT /api/v1/requests/{id}/status` - Update request status
- `GET /api/v1/requests/{id}/download` - Download COI PDF

## Integration with UI

The mock backend is fully compatible with the existing UI. When monitoring shows as "inactive":

1. Call the start monitoring endpoint
2. The UI will show monitoring as active
3. Mock emails will appear automatically
4. No Gmail authentication required

## Advantages of Mock System

1. **No Authentication Required**: Works immediately without OAuth setup
2. **Predictable Testing**: Consistent data for development and testing
3. **Customizable**: Easy to modify templates and generation rates
4. **Safe**: No risk of accessing real email data
5. **Fast**: Immediate results without network delays

## Migrating to Real Email Later

When ready to use real Gmail:

1. Set up Gmail OAuth credentials
2. Switch from `coi_backend_with_mock.py` to `coi_backend_gmail.py`
3. The same API endpoints work with both versions
4. UI requires no changes

## Troubleshooting

### Backend Won't Start
- Check if port 8001 is already in use
- Ensure all dependencies are installed: `pip install fastapi uvicorn reportlab pillow`

### No Mock Emails Appearing
- Verify monitoring is started: Check `/api/v1/requests/monitoring/status`
- Use manual scan: `POST /api/v1/requests/monitoring/scan`
- Check logs for errors

### UI Not Updating
- Ensure CORS is enabled (it is in both backends)
- Check browser console for errors
- Verify backend URL in UI configuration