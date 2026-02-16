"""Main entry point - orchestrates scanner, video service, and web interface."""

from __future__ import annotations

import logging
import signal
import sys
import time
from queue import Empty, Queue

from .audio import play_error, play_success
from .config import get_db_path, load_config
from .debug_log import add as debug_add
from .debug_log import run_osd_updater
from .rate_limiter import check_rate_limit, record_view
from .scanner_listener import start_scanner_listener_thread
from .url_parser import parse_video_url
from .video_service import (
    MPV_IDLE_SOCKET,
    _mpv_is_idle,
    download_video,
    load_idle_screen,
    play_video_with_mpv,
    start_mpv_idle,
)
from .web.app import run_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _process_scan(url: str, db_path, mpv_sockets: list[str]) -> None:
    """Handle a scanned URL: parse, rate limit, download, play, record."""
    debug_add(f"Scanned: {url[:60]}...")

    parsed = parse_video_url(url)
    if not parsed:
        logger.debug("Unsupported or invalid URL, ignoring: %s", url[:80])
        debug_add("Error: Invalid or unsupported URL")
        play_error()
        return

    if not check_rate_limit():
        logger.info("Rate limit exceeded, skipping: %s", parsed.original_url[:60])
        debug_add("Error: Rate limit exceeded")
        play_error()
        return

    play_success()
    debug_add("Downloading...")

    logger.info("Downloading: %s", parsed.original_url)
    path = download_video(parsed.original_url)
    if not path:
        logger.warning("Download failed for %s", parsed.original_url[:60])
        debug_add("Error: Download failed")
        play_error()
        return

    debug_add(f"Playing: {path.name}")
    logger.info("Playing: %s", path.name)
    if play_video_with_mpv(path, ipc_sockets=mpv_sockets, wait=False):
        record_view(parsed.video_id, parsed.platform, parsed.original_url)
    else:
        logger.warning("Playback failed for %s", path.name)
        debug_add("Error: Playback failed")
        play_error()


def main() -> int:
    """Run the video player service."""
    config = load_config()
    db_path = get_db_path()
    scan_queue: Queue = Queue()

    # Start web server in background
    import threading

    web_thread = threading.Thread(
        target=run_web_server,
        kwargs={
            "host": "0.0.0.0",
            "port": config.web_port,
            "db_path": db_path,
            "scan_queue": scan_queue,
        },
        daemon=True,
    )
    web_thread.start()
    logger.info("Web interface at http://0.0.0.0:%d", config.web_port)

    # Start mpv in idle mode (black screen); supports multi-HDMI via display_connectors
    connectors = (
        [c.strip() for c in config.display_connectors.split(",") if c.strip()] if config.display_connectors else None
    )
    mpv_result = start_mpv_idle(MPV_IDLE_SOCKET, display_connectors=connectors)
    if not mpv_result:
        logger.error("Failed to start mpv. Exiting.")
        return 1
    mpv_procs, mpv_sockets = mpv_result
    mpv_socket = mpv_sockets[0]  # Primary socket for playback

    # Load idle screen (black + play icon) immediately
    time.sleep(0.5)  # Let mpv finish initializing
    load_idle_screen(ipc_sockets=mpv_sockets)

    # Start scanner listener
    scanner_thread, _ = start_scanner_listener_thread(
        callback=lambda url: None,  # We use the queue instead
        device_path=config.scanner_device_path,
        queue=scan_queue,
    )

    # Start OSD updater for debug mode
    osd_thread = threading.Thread(
        target=run_osd_updater,
        args=(mpv_socket, db_path),
        daemon=True,
    )
    osd_thread.start()

    def run_idle_screen_reloader():
        """Reload idle screen when video playback ends (not when idle image is showing)."""
        last_was_video = False  # Track if we were playing a video (not the idle image)
        while True:
            time.sleep(2)
            try:
                idle = _mpv_is_idle(mpv_socket)
                if last_was_video and idle:
                    load_idle_screen(ipc_sockets=mpv_sockets)
                    last_was_video = False
                elif not idle:
                    last_was_video = True  # Not idle = playing something (video or idle image)
            except Exception:
                pass

    idle_thread = threading.Thread(target=run_idle_screen_reloader, daemon=True)
    idle_thread.start()

    def shutdown(signum=None, frame=None):
        logger.info("Shutting down...")
        for proc in mpv_procs:
            proc.terminate()
        for proc in mpv_procs:
            proc.wait(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Main loop: process scanned URLs (replace mode: drain queue, only process most recent)
    logger.info("Ready. Scan a QR code to play a video.")
    while True:
        try:
            url = scan_queue.get(timeout=1.0)
            # Drain queue so we only process the most recent scan (replace, don't queue)
            while True:
                try:
                    url = scan_queue.get_nowait()
                except Empty:
                    break
        except Empty:
            # Check if any mpv died
            if any(p.poll() is not None for p in mpv_procs):
                logger.error("mpv exited unexpectedly")
                return 1
            continue

        _process_scan(url, db_path, mpv_sockets)


if __name__ == "__main__":
    sys.exit(main())
