# Pi Video Player

A distraction-free Raspberry Pi video player. Scan a QR code (containing a YouTube URL) with a USB barcode scanner to watch a single video. When idle, only a black screen is shown.

## Features

- **QR code scanning**: USB hand scanner reads full YouTube URLs from QR codes
- **Single video playback**: One video per scan, fullscreen, no UI chrome
- **Black idle screen**: No distractions when no video is playing
- **Rate limiting**: Configure max videos per time period (e.g., 3 per 24 hours)
- **Web management**: HTTP interface to adjust settings (max videos, period, scanner device)

## Requirements

- Raspberry Pi 4 or 5 (recommended)
- Raspberry Pi OS
- USB barcode/QR scanner (HID keyboard emulation)
- Display(s) connected via HDMI (supports multiple; configure display connectors in settings)

## System Dependencies

```bash
sudo apt-get install python3-venv python3-pip ffmpeg mpv
```

## Installation

### Quick install (curl)

Install or update with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/erwinkloosterboer/pi-videokiosk/main/bootstrap.sh | bash
```

Installs to `~/pi-videokiosk` by default. Override with:

```bash
curl -fsSL https://raw.githubusercontent.com/erwinkloosterboer/pi-videokiosk/main/bootstrap.sh | INSTALL_DIR=/opt/pi-videokiosk bash
```

### Manual install

```bash
# Clone or copy the project, then:
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
```

On Raspberry Pi, use `install.sh` for full setup including systemd:

```bash
chmod +x install.sh
./install.sh
```

## Usage

```bash
source venv/bin/activate
python -m src
# Or: make run
```

Then:

1. Open the web interface at `http://<pi-ip>:8080` to configure settings
2. Play a video by:
   - **Scanning** a QR code containing a YouTube URL with the USB scanner
   - **Pasting** a YouTube URL into the "Play Video" field on the dashboard
   - **Direct URL**: `http://<pi-ip>:8080/directplay/<youtube-url>` (URL-encode the video URL, e.g. `http://<pi-ip>:8080/directplay/https%3A%2F%2Fyoutube.com%2Fwatch%3Fv%3DVIDEOID`)
3. The video downloads (if not cached) and plays fullscreen
4. When finished, the screen returns to black

## Sounds

Place `success.mp3` and `error.mp3` in the `sounds/` directory:
- **success.mp3** – plays when a video is scanned successfully (right before download)
- **error.mp3** – plays when rate limit is met or any error occurs

## Web Interface

- **Dashboard** (`/`): Play video (paste URL), current settings, recent views
- **Settings** (`/settings`): Edit max videos per period, period hours, scanner device path, web port, debug mode
- **Direct play** (`/directplay/<url>`): Queue a video by URL path, e.g. `http://mgmt.local:8080/directplay/https%3A%2F%2Fyoutube.com%2Fwatch%3Fv%3DVIDEOID`

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| max_videos | 3 | Maximum videos allowed per period |
| period_hours | 24 | Time period in hours |
| scanner_device_path | (auto) | Optional path like `/dev/input/event0` |
| display_connectors | (default) | Comma-separated DRM connectors for multi-HDMI, e.g. `0.HDMI-A-1,1.HDMI-A-2`. Run `mpv --drm-connector help` to list. |
| web_port | 8080 | HTTP management interface port |
| debug_mode | false | Show debug log at bottom of screen (max 10 lines, small font) |

## Project Structure

```
pi-videoplayer/
├── sounds/             # success.mp3, error.mp3
├── src/
│   ├── main.py           # Entry point
│   ├── scanner_listener.py
│   ├── url_parser.py
│   ├── video_service.py
│   ├── rate_limiter.py
│   ├── config.py
│   └── web/
├── data/                 # Created at runtime
│   ├── videoplayer.db
│   └── cache/
├── requirements.txt
├── Makefile
└── install.sh
```

## Kiosk Setup

For a dedicated display with no desktop or console visible, use kiosk mode. This replaces the desktop entirely with just the video player.

**Quick install:**

```bash
./install.sh --kiosk
```

Then set boot to console and reboot (see step 1 below).

### 1. Boot to console (no desktop)

```bash
sudo raspi-config
# System Options → Boot / Auto Login → Console Autologin
```

### 2. Install X server (minimal)

```bash
sudo apt-get install xserver-xorg xinit x11-xserver-utils
```

### 3. Create ~/.xinitrc

Replace the desktop with only the video player:

```bash
#!/bin/sh
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Run the video player (fullscreen, no other UI)
# Adjust path if you installed elsewhere (e.g. /opt/pi-videokiosk)
exec $HOME/pi-videokiosk/venv/bin/python -m src
```

```bash
chmod +x ~/.xinitrc
```

### 4. Auto-start X on login

Add to `~/.bashrc` (for the autologin user):

```bash
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  exec startx
fi
```

### 5. Reboot

```bash
sudo reboot
```

The Pi will boot to console, autologin to your user, then start X with only the video player. No desktop, no taskbar, no console visible.

If you need to access the console for maintenance, press `Ctrl+Alt+F2` (or F3–F6) to switch to another TTY, then `Ctrl+Alt+F1` to return.

**Black screen with blinking cursor?** You may be at a login prompt or shell. Try:
- Log in if prompted (default user `pi`), then run `startx` manually
- Check X errors: `cat ~/.xsession-errors`
- Ensure "Console Autologin" is set (not "Desktop Autologin"): `sudo raspi-config` → Boot / Auto Login → Console Autologin

## Troubleshooting

**Service shows "inactive (dead)" after boot**

Check logs: `journalctl -u pi-videoplayer -b`. Try starting manually: `sudo systemctl start pi-videoplayer`. If that works, the 15s delay may need to be increased in the service file.

**Black screen doesn't appear; desktop keeps showing**

The service needs X11 access. The install script sets `XAUTHORITY` in the systemd unit. If it still fails:

- Check logs: `journalctl -u pi-videoplayer -f`
- If you see "cannot open display" or "Authorization required", try running manually first: `DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority ./venv/bin/python -m src` (adjust path if your user is not `pi`). If that works, the service file may need the correct `XAUTHORITY` path.
- On Wayland (newer Pi OS), X11 apps may not work; use an X11 session if available.

## Scanner Setup

Most USB barcode/QR scanners emulate a keyboard. The app auto-detects keyboard-like devices. If you have multiple, set `scanner_device_path` in the web settings to the correct `/dev/input/eventX` device.

For permission issues, add your user to the `input` group:

```bash
sudo usermod -aG input $USER
```

## Legal Note

Downloading videos from YouTube may violate YouTube's Terms of Service. Use at your own responsibility.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
