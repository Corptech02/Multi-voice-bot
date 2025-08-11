#!/usr/bin/env python3
"""Run multi-tab voice bot with HTTPS"""
import subprocess
import os

os.chdir('/home/corp06/software_projects/ClaudeVoiceBot/current')
subprocess.run(['./venv/bin/python3', 'multi_tab_voice_http.py'])