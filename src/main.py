"""Main entry point - orchestrates scanner, video service, and web interface."""

from __future__ import annotations

import logging
import signal
import sys
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
    download_video,
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


def _process_scan(url: str, db_path) -> None:
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
    if play_video_with_mpv(path, MPV_IDLE_SOCKET):
        record_view(parsed.video_id, parsed.platform, parsed.original_url)
        debug_add("Playback complete")
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

    # Start mpv in idle mode (black screen)
    mpv_proc = start_mpv_idle(MPV_IDLE_SOCKET)
    if not mpv_proc:
        logger.error("Failed to start mpv. Exiting.")
        return 1

    # Start scanner listener
    scanner_thread, _ = start_scanner_listener_thread(
        callback=lambda url: None,  # We use the queue instead
        device_path=config.scanner_device_path,
        queue=scan_queue,
    )

    # Start OSD updater for debug mode
    osd_thread = threading.Thread(
        target=run_osd_updater,
        args=(MPV_IDLE_SOCKET, db_path),
        daemon=True,
    )
    osd_thread.start()

    def shutdown(signum=None, frame=None):
        logger.info("Shutting down...")
        if mpv_proc:
            mpv_proc.terminate()
            mpv_proc.wait(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Main loop: process scanned URLs
    logger.info("Ready. Scan a QR code to play a video.")
    while True:
        try:
            url = scan_queue.get(timeout=1.0)
        except Empty:
            # Check if mpv died
            if mpv_proc.poll() is not None:
                logger.error("mpv exited unexpectedly")
                return 1
            continue

        _process_scan(url, db_path)


if __name__ == "__main__":
    sys.exit(main())
