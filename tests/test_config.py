"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest

from src.config import (
    AppConfig,
    add_view,
    count_views_since,
    get_recent_views,
    load_config,
    save_config,
)


@pytest.fixture
def temp_db():
    """Use a temporary database for tests."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        (db_path.parent / "cache").mkdir(exist_ok=True)
        yield db_path


def test_load_config_defaults(temp_db):
    """Empty DB returns default config."""
    config = load_config(temp_db)
    assert config.max_videos == 3
    assert config.period_hours == 24.0
    assert config.scanner_device_path is None


def test_save_and_load_config(temp_db):
    """Config round-trip."""
    config = AppConfig(
        max_videos=5,
        period_hours=12.0,
        scanner_device_path="/dev/input/event0",
        web_port=9000,
        debug_mode=False,
    )
    save_config(config, temp_db)
    loaded = load_config(temp_db)
    assert loaded.max_videos == 5
    assert loaded.period_hours == 12.0
    assert loaded.scanner_device_path == "/dev/input/event0"
    assert loaded.web_port == 9000


def test_add_and_count_views(temp_db):
    """View history and count."""
    import time

    add_view("vid1", "youtube", "https://youtube.com/watch?v=vid1", temp_db)
    add_view("vid2", "youtube", "https://youtube.com/watch?v=vid2", temp_db)

    now = time.time()
    assert count_views_since(now - 3600, temp_db) == 2
    assert count_views_since(now + 1, temp_db) == 0


def test_get_recent_views(temp_db):
    """Recent views ordered by time."""
    add_view("a", "youtube", None, temp_db)
    add_view("b", "youtube", None, temp_db)
    recent = get_recent_views(10, temp_db)
    assert len(recent) == 2
    assert recent[0]["video_id"] == "b"  # Most recent first
