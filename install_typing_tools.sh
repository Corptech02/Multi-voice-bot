#!/bin/bash
# Install tools for automatic typing

echo "Installing xdotool for automatic typing..."
echo ""
echo "Please enter your password (corp06) when prompted:"
echo ""

# Install xdotool
sudo apt-get update
sudo apt-get install -y xdotool xvfb x11-apps

# Install additional tools
sudo apt-get install -y wmctrl xclip

echo ""
echo "Installation complete!"
echo ""
echo "Testing xdotool..."
xdotool --version

echo ""
echo "If you see a version number above, xdotool is ready!"