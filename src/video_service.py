"""Download videos via yt-dlp and play with mpv."""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from .config import DEFAULT_CACHE_DIR

logger = logging.getLogger(__name__)

# Format for Pi 4: 720p max for performance
YT_DLP_FORMAT = "best[height<=720]/best"
MPV_IDLE_SOCKET = "/tmp/pi-videoplayer-mpv.sock"


def _get_cache_dir() -> Path:
    """Return cache directory, creating it if needed."""
    cache = DEFAULT_CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def download_video(url: str, cache_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Download video from URL using yt-dlp.

    Returns path to downloaded file, or None on failure.
    Caches by video id; skips download if already cached.
    """
    import yt_dlp

    cache = cache_dir or _get_cache_dir()
    out_template = str(cache / "%(id)s.%(ext)s")

    opts = {
        "format": YT_DLP_FORMAT,
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
            video_id = info.get("id")
            if not video_id:
                return None
            # Find the downloaded file (ext may differ after post-processing)
            for p in cache.glob(f"{video_id}.*"):
                if p.is_file():
                    return p
            path = cache / f"{video_id}.{info.get('ext', 'mp4')}"
            return path if path.exists() else None
    except Exception as e:
        logger.exception("yt-dlp download failed for %s: %s", url, e)
        return None

    return None


def _mpv_ipc_send(sock_path: str, command: list) -> Optional[dict]:
    """Send a command to mpv via IPC socket, return response."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(sock_path)
        msg = json.dumps({"command": command}) + "\n"
        sock.sendall(msg.encode())
        data = sock.recv(4096).decode()
        sock.close()
        if data:
            return json.loads(data)
    except (socket.error, json.JSONDecodeError) as e:
        logger.debug("mpv IPC error: %s", e)
    return None


def _mpv_ipc_wait_idle(sock_path: str, timeout: float = 3600) -> bool:
    """
    Wait until mpv is idle (playback finished).
    Polls the idle-active property. Returns True when idle.
    """
    start = time.time()
    while (time.time() - start) < timeout:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(sock_path)
            # get_property idle-active: true when idle
            msg = json.dumps({"command": ["get_property", "idle-active"]}) + "\n"
            sock.sendall(msg.encode())
            data = sock.recv(4096).decode()
            sock.close()
            if data:
                resp = json.loads(data)
                if resp.get("data") is True:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def play_video_with_mpv(
    video_path: Path,
    ipc_socket: str = MPV_IDLE_SOCKET,
) -> bool:
    """
    Tell mpv (already running with --idle) to load and play the video.
    Blocks until playback finishes.

    Returns True if playback completed, False on error.
    """
    path_str = str(video_path.resolve())
    resp = _mpv_ipc_send(ipc_socket, ["loadfile", path_str, "replace"])
    if resp is None:
        logger.warning("Could not send loadfile to mpv")
        return False
    if "error" in resp:
        logger.warning("mpv loadfile error: %s", resp.get("error"))
        return False

    # Wait for playback to finish (mpv goes back to idle)
    return _mpv_ipc_wait_idle(ipc_socket)


def start_mpv_idle(ipc_socket: str = MPV_IDLE_SOCKET) -> Optional[subprocess.Popen]:
    """
    Start mpv in idle mode (black screen) with IPC server.

    Returns the Popen instance, or None on failure.
    """
    # Remove stale socket
    if os.path.exists(ipc_socket):
        try:
            os.unlink(ipc_socket)
        except OSError:
            pass

    cmd = [
        "mpv",
        "--idle=yes",
        "--no-osc",
        "--no-input-default-bindings",
        "--fs",
        f"--input-ipc-server={ipc_socket}",
        "--osd-align-y=bottom",
        "--osd-font-size=18",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # Wait for socket to appear
        for _ in range(50):
            if os.path.exists(ipc_socket):
                return proc
            time.sleep(0.1)
        proc.terminate()
        logger.error("mpv did not create IPC socket in time")
        return None
    except FileNotFoundError:
        logger.error("mpv not found. Install with: apt install mpv")
        return None
    except Exception as e:
        logger.exception("Failed to start mpv: %s", e)
        return None
