#!/bin/bash
# Install dependencies and set up the Pi Kids Video Player on Raspberry Pi OS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip ffmpeg mpv

# evdev may need to be installed via pip (python3-evdev exists but pip is more reliable)
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install yt-dlp (can use pip or system)
pip install -U yt-dlp

echo "Installing systemd service..."
sudo tee /etc/systemd/system/pi-videoplayer.service > /dev/null << EOF
[Unit]
Description=Pi Kids Video Player
After=network.target graphical.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=DISPLAY=:0
ExecStart=$SCRIPT_DIR/venv/bin/python -m src
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

echo "Enabling autostart on boot..."
sudo systemctl enable pi-videoplayer
echo "To start now: sudo systemctl start pi-videoplayer"
echo "To view logs: journalctl -u pi-videoplayer -f"
echo ""
echo "Note: The USB scanner may require root or udev rules for access."
echo "Add user to input group: sudo usermod -aG input $USER"
