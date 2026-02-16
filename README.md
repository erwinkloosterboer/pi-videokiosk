# Pi Kids Video Player

A distraction-free Raspberry Pi video player for children. Scan a QR code (containing a YouTube URL) with a USB barcode scanner to watch a single video. When idle, only a black screen is shown.

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
- Display connected via HDMI

## System Dependencies

```bash
sudo apt-get install python3-venv python3-pip ffmpeg mpv
```

## Installation

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
2. Scan a QR code containing a YouTube URL with the USB scanner
3. The video downloads (if not cached) and plays fullscreen
4. When finished, the screen returns to black

## Sounds

Place `success.mp3` and `error.mp3` in the `sounds/` directory:
- **success.mp3** – plays when a video is scanned successfully (right before download)
- **error.mp3** – plays when rate limit is met or any error occurs

## Web Interface

- **Dashboard** (`/`): Current settings, recent views
- **Settings** (`/settings`): Edit max videos per period, period hours, scanner device path, web port, debug mode

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| max_videos | 3 | Maximum videos allowed per period |
| period_hours | 24 | Time period in hours |
| scanner_device_path | (auto) | Optional path like `/dev/input/event0` |
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

## Scanner Setup

Most USB barcode/QR scanners emulate a keyboard. The app auto-detects keyboard-like devices. If you have multiple, set `scanner_device_path` in the web settings to the correct `/dev/input/eventX` device.

For permission issues, add your user to the `input` group:

```bash
sudo usermod -aG input $USER
```

## Legal Note

Downloading videos from YouTube may violate YouTube's Terms of Service. Use at your own responsibility.

## License

MIT
