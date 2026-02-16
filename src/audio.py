"""Play feedback sounds (success/error) via mpv."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

SOUNDS_DIR = Path(__file__).resolve().parent.parent / "sounds"
SUCCESS_SOUND = SOUNDS_DIR / "success.mp3"
ERROR_SOUND = SOUNDS_DIR / "error.mp3"


def play_sound(path: Path) -> None:
    """Play an audio file in the background (non-blocking)."""
    if not path.exists():
        logger.debug("Sound file not found: %s", path)
        return
    try:
        subprocess.Popen(
            ["mpv", "--no-video", "--really-quiet", str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        logger.debug("mpv not found for audio playback")
    except Exception as e:
        logger.debug("Could not play sound %s: %s", path, e)


def play_success() -> None:
    """Play the success sound (video about to play)."""
    play_sound(SUCCESS_SOUND)


def play_error() -> None:
    """Play the error sound (rate limit or other error)."""
    play_sound(ERROR_SOUND)
