#!/usr/bin/env python3
"""Test Claude in pipe mode"""
import subprocess

# Test with pipe mode
result = subprocess.run(
    ['claude', '--dangerously-skip-permissions', '-p'],
    input="What is 3+3?",
    text=True,
    capture_output=True
)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)