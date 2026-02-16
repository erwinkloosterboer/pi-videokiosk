"""Extensible URL parser for video platforms. Recognizes video URLs and extracts IDs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse

# YouTube video ID: 11 chars, alphanumeric + underscore + hyphen
YOUTUBE_VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


@dataclass
class ParsedVideo:
    """Parsed video from a supported platform URL."""

    platform: str
    video_id: str
    original_url: str


class PlatformHandler:
    """Interface for platform-specific URL parsers."""

    def can_handle(self, url: str) -> bool:
        """Return True if this handler can parse the given URL."""
        raise NotImplementedError

    def parse(self, url: str) -> Optional[ParsedVideo]:
        """Parse URL and return ParsedVideo, or None if invalid."""
        raise NotImplementedError


class YouTubeHandler(PlatformHandler):
    """Parse YouTube URLs and extract video ID."""

    # Patterns for YouTube URLs we support
    _WATCH_PATTERNS = (
        "youtube.com/watch",
        "www.youtube.com/watch",
        "m.youtube.com/watch",
    )
    _SHORT_PATTERN = "youtu.be/"
    _EMBED_PATTERN = "youtube.com/embed/"

    def can_handle(self, url: str) -> bool:
        url_lower = url.lower().strip()
        if any(p in url_lower for p in self._WATCH_PATTERNS):
            return True
        if self._SHORT_PATTERN in url_lower:
            return True
        if self._EMBED_PATTERN in url_lower:
            return True
        return False

    def parse(self, url: str) -> Optional[ParsedVideo]:
        url = url.strip()
        if not url:
            return None

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None

        video_id: Optional[str] = None

        # youtu.be/VIDEO_ID
        if "youtu.be" in parsed.netloc:
            path = parsed.path.strip("/")
            if path and "?" not in path.split("/")[0]:
                video_id = path.split("/")[0].split("?")[0]

        # youtube.com/embed/VIDEO_ID
        elif "youtube.com" in parsed.netloc and "/embed/" in parsed.path:
            parts = parsed.path.split("/embed/")
            if len(parts) >= 2:
                video_id = parts[1].split("/")[0].split("?")[0]

        # youtube.com/watch?v=VIDEO_ID
        elif "youtube.com" in parsed.netloc and "watch" in parsed.path:
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                video_id = qs["v"][0]

        if not video_id or not YOUTUBE_VIDEO_ID_RE.match(video_id):
            return None

        return ParsedVideo(
            platform="youtube",
            video_id=video_id,
            original_url=url,
        )


# Registry of platform handlers
_PLATFORM_HANDLERS: list[PlatformHandler] = [YouTubeHandler()]


def register_handler(handler: PlatformHandler) -> None:
    """Register a platform handler for future expansion."""
    _PLATFORM_HANDLERS.append(handler)


def parse_video_url(url: str) -> Optional[ParsedVideo]:
    """
    Parse a full video URL and return ParsedVideo if supported.

    Returns None for unsupported or invalid URLs (silent reject for minimal distraction).
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    for handler in _PLATFORM_HANDLERS:
        if handler.can_handle(url):
            result = handler.parse(url)
            if result:
                return result

    return None
