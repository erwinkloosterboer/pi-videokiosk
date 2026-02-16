"""Tests for rate_limiter module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import AppConfig, add_view, save_config
from src.rate_limiter import check_rate_limit


@pytest.fixture
def temp_db():
    """Use a temporary database for tests."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        (db_path.parent / "cache").mkdir(exist_ok=True)
        yield db_path


def test_rate_limit_allows_when_under_limit(temp_db):
    """Allow when under max."""
    config = AppConfig(
        max_videos=3,
        period_hours=24.0,
        scanner_device_path=None,
        web_port=8080,
        debug_mode=False,
        display_connectors="",
    )
    save_config(config, temp_db)
    with (
        patch("src.config.get_db_path", return_value=temp_db),
        patch("src.rate_limiter.get_db_path", return_value=temp_db),
    ):
        assert check_rate_limit(config) is True
        add_view("v1", "youtube", None, temp_db)
        assert check_rate_limit(config) is True
        add_view("v2", "youtube", None, temp_db)
        assert check_rate_limit(config) is True


def test_rate_limit_rejects_when_over_limit(temp_db):
    """Reject when at or over max."""
    config = AppConfig(
        max_videos=2,
        period_hours=24.0,
        scanner_device_path=None,
        web_port=8080,
        debug_mode=False,
        display_connectors="",
    )
    save_config(config, temp_db)
    with (
        patch("src.config.get_db_path", return_value=temp_db),
        patch("src.rate_limiter.get_db_path", return_value=temp_db),
    ):
        add_view("v1", "youtube", None, temp_db)
        add_view("v2", "youtube", None, temp_db)
        assert check_rate_limit(config) is False
