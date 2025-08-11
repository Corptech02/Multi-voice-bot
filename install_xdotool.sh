#!/bin/bash
# Install xdotool for automatic typing

echo "Installing xdotool for automatic typing..."
echo "Please enter your sudo password when prompted:"
echo "corp06"

# Install xdotool
sudo apt-get update
sudo apt-get install -y xdotool

# Also install xvfb for virtual display if needed
sudo apt-get install -y xvfb

echo "Installation complete!"