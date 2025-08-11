#!/bin/bash
echo "Starting app with logging..."
python3 multi_tab_voice_exact_replica.py 2>&1 | tee app.log