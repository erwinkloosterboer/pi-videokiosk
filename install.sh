#!/bin/bash
# Install dependencies and set up the Pi Video Player on Raspberry Pi OS

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

echo "Installing autostart..."
INSTALL_USER=$(whoami)
USER_HOME=$(getent passwd "$INSTALL_USER" | cut -d: -f6)
WORK_DIR=$(cd "$SCRIPT_DIR" && pwd)

# Remove old system service if present
sudo systemctl disable pi-videoplayer 2>/dev/null || true
sudo rm -f /etc/systemd/system/pi-videoplayer.service 2>/dev/null || true
sudo systemctl daemon-reload 2>/dev/null || true

# Desktop autostart (reliable on Raspberry Pi - runs when user logs in)
mkdir -p "$USER_HOME/.config/autostart"
cat > "$USER_HOME/.config/autostart/pi-videoplayer.desktop" << AUTOSTART_EOF
[Desktop Entry]
Type=Application
Name=Pi Video Player
Exec=$WORK_DIR/venv/bin/python -m src
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
AUTOSTART_EOF

echo "Autostart enabled. The app will start when you log in to the desktop."
echo "To start now: $WORK_DIR/venv/bin/python -m src"
echo ""
echo "Note: The USB scanner may require root or udev rules for access."
echo "Add user to input group: sudo usermod -aG input $USER"
