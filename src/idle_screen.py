"""Generate and manage the idle screen (black + play icon)."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import DEFAULT_DATA_DIR

logger = logging.getLogger(__name__)

IDLE_IMAGE_NAME = "idle.png"
IDLE_IMAGE_FALLBACK = "idle.ppm"


def get_idle_image_path() -> Path:
    """Return path to idle image, creating it if needed."""
    data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / IDLE_IMAGE_NAME
    fallback_path = data_dir / IDLE_IMAGE_FALLBACK

    if path.exists():
        return path
    if fallback_path.exists():
        return fallback_path

    _create_idle_image(path)
    return path if path.exists() else fallback_path


def _create_idle_image(path: Path) -> None:
    """Create a black image with play icon (▶) in the center."""
    try:
        from PIL import Image, ImageDraw

        # 1920x1080 for common display resolution
        width, height = 1920, 1080
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw play triangle in center (pointing right)
        center_x, center_y = width // 2, height // 2
        size = min(width, height) // 4
        # Triangle vertices: left, top-right, bottom-right
        triangle = [
            (center_x - size, center_y - size),
            (center_x - size, center_y + size),
            (center_x + size, center_y),
        ]
        draw.polygon(triangle, fill=(255, 255, 255), outline=(200, 200, 200))

        img.save(path)
        logger.info("Created idle screen image at %s", path)
    except ImportError:
        # Fallback: create minimal black image without Pillow (raw PNG)
        _create_minimal_black_png(path)
    except Exception as e:
        logger.warning("Could not create idle image with Pillow: %s", e)
        _create_minimal_black_png(path)


def _create_minimal_black_png(path: Path) -> None:
    """Create a minimal black PPM image (mpv will scale it to fullscreen)."""
    ppm_path = path.parent / IDLE_IMAGE_FALLBACK
    ppm_header = b"P6\n1920 1080\n255\n"
    ppm_data = ppm_header + (b"\x00\x00\x00" * (1920 * 1080))
    ppm_path.write_bytes(ppm_data)
    logger.info("Created minimal black idle image at %s", ppm_path)
