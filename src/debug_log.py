"""Debug log buffer for on-screen display when debug mode is enabled."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from collections import deque

logger = logging.getLogger(__name__)

MAX_LINES = 10
OSD_UPDATE_INTERVAL = 2.0  # seconds
OSD_DURATION = 30  # seconds (mpv show-text duration)

_log_buffer: deque[str] = deque(maxlen=MAX_LINES)
_lock = threading.Lock()


def add(msg: str) -> None:
    """Add a debug message to the buffer."""
    with _lock:
        _log_buffer.append(msg)


def get_lines() -> list[str]:
    """Get the current log lines (newest last)."""
    with _lock:
        return list(_log_buffer)


def clear() -> None:
    """Clear the log buffer."""
    with _lock:
        _log_buffer.clear()


def _mpv_show_text(sock_path: str, text: str) -> None:
    """Send show-text command to mpv via IPC."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(sock_path)
        msg = json.dumps({"command": ["show-text", text, OSD_DURATION * 1000]}) + "\n"
        sock.sendall(msg.encode())
        sock.close()
    except Exception:
        pass


def run_osd_updater(sock_path: str, db_path=None) -> None:
    """
    Background thread that periodically updates mpv OSD with debug log.
    Runs until the process exits.
    """
    while True:
        time.sleep(OSD_UPDATE_INTERVAL)
        try:
            from .config import load_config

            config = load_config(db_path)
            if not config.debug_mode:
                continue
            lines = get_lines()
            if not lines:
                continue
            text = "\n".join(lines)
            _mpv_show_text(sock_path, text)
        except Exception as e:
            logger.debug("OSD updater error: %s", e)
