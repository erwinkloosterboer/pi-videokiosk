#!/bin/bash
# Install dependencies and set up the Pi Video Player on Raspberry Pi OS
# Usage: ./install.sh [--kiosk]
#   --kiosk  Install kiosk mode (X only, no desktop) instead of systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

KIOSK_MODE=false
for arg in "$@"; do
    case "$arg" in
        --kiosk) KIOSK_MODE=true ;;
    esac
done

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

INSTALL_USER=$(whoami)
USER_HOME=$(getent passwd "$INSTALL_USER" | cut -d: -f6)
WORK_DIR=$(cd "$SCRIPT_DIR" && pwd)

if [ "$KIOSK_MODE" = true ]; then
    echo "Installing kiosk mode..."
    sudo systemctl disable pi-videoplayer 2>/dev/null || true
    sudo apt-get install -y xserver-xorg xinit x11-xserver-utils

    # Create ~/.xinitrc
    cat > "$USER_HOME/.xinitrc" << XINITRC_EOF
#!/bin/sh
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Run the video player (fullscreen, no other UI)
exec $WORK_DIR/venv/bin/python -m src
XINITRC_EOF
    chmod +x "$USER_HOME/.xinitrc"

    # Add startx to .bashrc if not already present
    BASHRC_MARKER="# pi-videokiosk kiosk autostart"
    if ! grep -q "$BASHRC_MARKER" "$USER_HOME/.bashrc" 2>/dev/null; then
        cat >> "$USER_HOME/.bashrc" << 'BASHRC_EOF'

# pi-videokiosk kiosk autostart
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  exec startx
fi
BASHRC_EOF
    fi

    echo ""
    echo "Kiosk mode installed. Next steps:"
    echo "  1. Set boot to console: sudo raspi-config → System Options → Boot / Auto Login → Console Autologin"
    echo "  2. Reboot: sudo reboot"
    echo ""
else
    echo "Installing systemd service..."
    rm -f "$USER_HOME/.config/autostart/pi-videoplayer.desktop" 2>/dev/null || true

    sed -e "s|@WORK_DIR@|$WORK_DIR|g" \
        -e "s|@INSTALL_USER@|$INSTALL_USER|g" \
        -e "s|@USER_HOME@|$USER_HOME|g" << 'SERVICE_EOF' | sudo tee /etc/systemd/system/pi-videoplayer.service > /dev/null
[Unit]
Description=Pi Video Player
After=network.target graphical.target

[Service]
Type=simple
User=@INSTALL_USER@
WorkingDirectory=@WORK_DIR@
Environment=PATH=@WORK_DIR@/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=DISPLAY=:0
Environment=XAUTHORITY=@USER_HOME@/.Xauthority
ExecStartPre=/bin/sleep 15
ExecStart=@WORK_DIR@/venv/bin/python -m src
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
SERVICE_EOF

    echo "Enabling autostart on boot..."
    sudo systemctl daemon-reload
    sudo systemctl enable pi-videoplayer
    echo "To start now: sudo systemctl start pi-videoplayer"
    echo "To check status: sudo systemctl status pi-videoplayer"
    echo "To view logs: journalctl -u pi-videoplayer -f"
fi

echo ""
echo "Note: The USB scanner may require root or udev rules for access."
echo "Add user to input group: sudo usermod -aG input $USER"
