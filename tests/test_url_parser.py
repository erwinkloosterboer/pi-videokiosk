"""Tests for url_parser module."""

from src.url_parser import parse_video_url


class TestYouTubeHandler:
    """Test YouTube URL parsing."""

    def test_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = parse_video_url(url)
        assert result is not None
        assert result.platform == "youtube"
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.original_url == url

    def test_youtu_be_short(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = parse_video_url(url)
        assert result is not None
        assert result.platform == "youtube"
        assert result.video_id == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = parse_video_url(url)
        assert result is not None
        assert result.platform == "youtube"
        assert result.video_id == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        result = parse_video_url(url)
        assert result is not None
        assert result.platform == "youtube"
        assert result.video_id == "dQw4w9WgXcQ"

    def test_youtube_com_no_www(self):
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        result = parse_video_url(url)
        assert result is not None
        assert result.video_id == "dQw4w9WgXcQ"

    def test_invalid_video_id_too_short(self):
        url = "https://www.youtube.com/watch?v=short"
        result = parse_video_url(url)
        assert result is None

    def test_invalid_video_id_invalid_chars(self):
        url = "https://www.youtube.com/watch?v=invalid!!!"
        result = parse_video_url(url)
        assert result is None

    def test_non_youtube_url(self):
        url = "https://vimeo.com/123456789"
        result = parse_video_url(url)
        assert result is None

    def test_invalid_url(self):
        assert parse_video_url("") is None
        assert parse_video_url("not a url") is None
        assert parse_video_url("https://example.com") is None
