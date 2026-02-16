"""Rate limiting for video views based on configurable max videos per period."""

from __future__ import annotations

import time
from typing import Optional

from .config import (
    AppConfig,
    add_view,
    count_views_since,
    get_db_path,
    load_config,
)


def check_rate_limit(config: Optional[AppConfig] = None) -> bool:
    """
    Check if the user is within the rate limit (can watch another video).

    Returns True if allowed, False if limit exceeded.
    """
    cfg = config or load_config()
    since = time.time() - (cfg.period_hours * 3600)
    count = count_views_since(since, get_db_path())
    return count < cfg.max_videos


def record_view(
    video_id: str,
    platform: str,
    original_url: Optional[str] = None,
) -> None:
    """Record a video view after successful playback."""
    add_view(video_id, platform, original_url, get_db_path())
