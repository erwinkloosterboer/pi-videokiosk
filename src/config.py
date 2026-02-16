"""SQLite config and viewing history persistence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "videoplayer.db"
DEFAULT_CACHE_DIR = DEFAULT_DATA_DIR / "cache"

# Default config values
DEFAULT_MAX_VIDEOS = 3
DEFAULT_PERIOD_HOURS = 24.0
DEFAULT_WEB_PORT = 8080
DEFAULT_DEBUG_MODE = False


@dataclass
class AppConfig:
    """Application configuration."""

    max_videos: int
    period_hours: float
    scanner_device_path: Optional[str]
    web_port: int
    debug_mode: bool

    @classmethod
    def defaults(cls) -> AppConfig:
        return cls(
            max_videos=DEFAULT_MAX_VIDEOS,
            period_hours=DEFAULT_PERIOD_HOURS,
            scanner_device_path=None,
            web_port=DEFAULT_WEB_PORT,
            debug_mode=DEFAULT_DEBUG_MODE,
        )


def _ensure_data_dir(db_path: Path) -> None:
    """Create data directory and cache subdirectory if they don't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    (db_path.parent / "cache").mkdir(exist_ok=True)


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS view_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            viewed_at REAL NOT NULL,
            video_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            original_url TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_view_history_viewed_at
            ON view_history(viewed_at);
    """)


def _config_to_dict(config: AppConfig) -> dict[str, str]:
    return {
        "max_videos": str(config.max_videos),
        "period_hours": str(config.period_hours),
        "scanner_device_path": config.scanner_device_path or "",
        "web_port": str(config.web_port),
        "debug_mode": "true" if config.debug_mode else "false",
    }


def _dict_to_config(d: dict[str, str]) -> AppConfig:
    return AppConfig(
        max_videos=int(d.get("max_videos", DEFAULT_MAX_VIDEOS)),
        period_hours=float(d.get("period_hours", DEFAULT_PERIOD_HOURS)),
        scanner_device_path=d.get("scanner_device_path") or None,
        web_port=int(d.get("web_port", DEFAULT_WEB_PORT)),
        debug_mode=d.get("debug_mode", "false").lower() in ("true", "1", "yes"),
    )


def get_db_path() -> Path:
    """Return the database path, ensuring the directory exists."""
    _ensure_data_dir(DEFAULT_DB_PATH)
    return DEFAULT_DB_PATH


def load_config(db_path: Optional[Path] = None) -> AppConfig:
    """Load config from SQLite. Returns defaults if no config exists."""
    path = db_path or get_db_path()
    _ensure_data_dir(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)

    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()

    if not rows:
        return AppConfig.defaults()

    d = {row["key"]: row["value"] for row in rows}
    return _dict_to_config(d)


def save_config(config: AppConfig, db_path: Optional[Path] = None) -> None:
    """Save config to SQLite."""
    path = db_path or get_db_path()
    _ensure_data_dir(path)

    conn = sqlite3.connect(path)
    _init_schema(conn)

    for key, value in _config_to_dict(config).items():
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()
    conn.close()


def add_view(
    video_id: str,
    platform: str,
    original_url: Optional[str],
    db_path: Optional[Path] = None,
) -> None:
    """Record a video view for rate limiting."""
    import time

    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    _init_schema(conn)
    conn.execute(
        "INSERT INTO view_history (viewed_at, video_id, platform, original_url) VALUES (?, ?, ?, ?)",
        (time.time(), video_id, platform, original_url or ""),
    )
    conn.commit()
    conn.close()


def count_views_since(since_timestamp: float, db_path: Optional[Path] = None) -> int:
    """Count views since the given timestamp."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    _init_schema(conn)
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM view_history WHERE viewed_at >= ?",
        (since_timestamp,),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_recent_views(limit: int = 50, db_path: Optional[Path] = None) -> list[dict]:
    """Get recent view history for the dashboard."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    rows = conn.execute(
        """
        SELECT viewed_at, video_id, platform, original_url
        FROM view_history
        ORDER BY viewed_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
