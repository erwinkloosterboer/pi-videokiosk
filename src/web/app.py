"""Flask web management interface."""

from __future__ import annotations

import logging
from pathlib import Path
from queue import Queue
from typing import Optional
from urllib.parse import unquote

from flask import Flask, redirect, render_template_string, request, url_for

from ..config import (
    AppConfig,
    get_db_path,
    get_recent_views,
    load_config,
    save_config,
)

logger = logging.getLogger(__name__)

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Kids Video Player - Dashboard</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
        h1 { font-size: 1.5rem; }
        .card { background: #f5f5f5; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .card h2 { margin-top: 0; font-size: 1rem; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #ddd; }
        th { font-weight: 600; }
        .btn { display: inline-block; padding: 0.5rem 1rem; background: #333; color: white;
            text-decoration: none; border-radius: 4px; margin-top: 0.5rem; }
        .btn:hover { background: #555; }
        .status { color: #0a0; }
    </style>
</head>
<body>
    <h1>Kids Video Player</h1>
    <div class="card">
        <h2>Status</h2>
        {% if request.args.get('queued') %}
        <p class="status">Video queued for playback.</p>
        {% else %}
        <p class="status">Running</p>
        {% endif %}
    </div>
    <div class="card">
        <h2>Play Video</h2>
        <form method="post" action="{{ url_for('play') }}" style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <input type="url" name="url" placeholder="Paste YouTube URL..." required
                style="flex: 1; min-width: 200px; padding: 0.5rem;">
            <button type="submit" class="btn">Play</button>
        </form>
    </div>
    <div class="card">
        <h2>Current Settings</h2>
        <p><strong>Max videos per period:</strong> {{ config.max_videos }}</p>
        <p><strong>Period (hours):</strong> {{ config.period_hours }}</p>
        <p><strong>Scanner device:</strong> {{ config.scanner_device_path or 'Auto-detect' }}</p>
        <p><strong>Web port:</strong> {{ config.web_port }}</p>
        <p><strong>Debug mode:</strong> {{ 'On' if config.debug_mode else 'Off' }}</p>
        <a href="{{ url_for('settings') }}" class="btn">Edit Settings</a>
    </div>
    <div class="card">
        <h2>Recent Views</h2>
        {% if recent_views %}
        <table>
            <tr><th>Time</th><th>Video ID</th><th>Platform</th></tr>
            {% for v in recent_views %}
            <tr>
                <td>{{ v.viewed_at_fmt }}</td>
                <td>{{ v.video_id }}</td>
                <td>{{ v.platform }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>No views yet.</p>
        {% endif %}
    </div>
</body>
</html>
"""

SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Kids Video Player - Settings</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 500px; margin: 2rem auto; padding: 0 1rem; }
        h1 { font-size: 1.5rem; }
        form { display: flex; flex-direction: column; gap: 1rem; }
        label { font-weight: 500; }
        input { padding: 0.5rem; font-size: 1rem; }
        .btn { padding: 0.5rem 1rem; background: #333; color: white; border: none;
            border-radius: 4px; cursor: pointer; font-size: 1rem; }
        .btn:hover { background: #555; }
        .back { display: inline-block; margin-top: 1rem; color: #666; }
    </style>
</head>
<body>
    <h1>Settings</h1>
    <form method="post">
        <label for="max_videos">Max videos per period</label>
        <input type="number" id="max_videos" name="max_videos" value="{{ config.max_videos }}" min="1" required>
        <label for="period_hours">Period (hours)</label>
        <input type="number" id="period_hours" name="period_hours"
            value="{{ config.period_hours }}" min="0.1" step="0.1" required>
        <label for="scanner_device_path">Scanner device path (optional, e.g. /dev/input/event0)</label>
        <input type="text" id="scanner_device_path" name="scanner_device_path"
            value="{{ config.scanner_device_path or '' }}" placeholder="Leave empty for auto-detect">
        <label for="web_port">Web interface port</label>
        <input type="number" id="web_port" name="web_port" value="{{ config.web_port }}" min="1024" max="65535">
        <label>
            <input type="checkbox" name="debug_mode" value="1" {{ 'checked' if config.debug_mode else '' }}>
            Debug mode (show log at bottom of screen)
        </label>
        <button type="submit" class="btn">Save</button>
    </form>
    <a href="{{ url_for('dashboard') }}" class="back">← Back to Dashboard</a>
</body>
</html>
"""


def _format_timestamp(ts: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def create_app(
    config_path: Optional[Path] = None,
    scan_queue: Optional[Queue] = None,
) -> Flask:
    """Create and configure the Flask app."""
    app = Flask(__name__)
    app.secret_key = "pi-videokiosk-secret"  # Fixed key for local kiosk use

    def _queue_url(url: str) -> bool:
        """Queue a URL for playback. Returns True if queued."""
        if not scan_queue or not url or not url.strip():
            return False
        scan_queue.put(url.strip())
        return True

    @app.route("/")
    def dashboard():
        config = load_config(config_path)
        recent = get_recent_views(50, config_path)
        for v in recent:
            v["viewed_at_fmt"] = _format_timestamp(v["viewed_at"])
        return render_template_string(
            DASHBOARD_TEMPLATE,
            config=config,
            recent_views=recent,
        )

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        config = load_config(config_path)
        if request.method == "POST":
            try:
                config = AppConfig(
                    max_videos=int(request.form.get("max_videos", config.max_videos)),
                    period_hours=float(request.form.get("period_hours", config.period_hours)),
                    scanner_device_path=request.form.get("scanner_device_path") or None,
                    web_port=int(request.form.get("web_port", config.web_port)),
                    debug_mode=request.form.get("debug_mode") == "1",
                )
                save_config(config, config_path)
                return redirect(url_for("dashboard"))
            except (ValueError, TypeError) as e:
                logger.warning("Invalid settings: %s", e)
        return render_template_string(SETTINGS_TEMPLATE, config=config)

    @app.route("/play", methods=["POST"])
    def play():
        """Queue a video URL from the paste form."""
        url = request.form.get("url", "").strip()
        if url and _queue_url(url):
            return redirect(url_for("dashboard", queued=1))
        return redirect(url_for("dashboard"))

    @app.route("/directplay/<path:video_url>")
    def directplay(video_url: str):
        """Queue a video from URL path.
        E.g. /directplay/https%3A%2F%2Fyoutube.com%2Fwatch%3Fv%3DVIDEOID
        Or:  /directplay/http://youtube.com/watch?v=VIDEOID (query string preserved)
        """
        decoded = unquote(video_url)
        if request.query_string:
            decoded = decoded + "?" + request.query_string.decode()
        if _queue_url(decoded):
            return "<!DOCTYPE html><html><body><p>Video queued for playback.</p></body></html>", 200
        return "<!DOCTYPE html><html><body><p>Invalid or missing URL.</p></body></html>", 400

    return app


def run_web_server(
    host: str = "0.0.0.0",
    port: Optional[int] = None,
    db_path: Optional[Path] = None,
    scan_queue: Optional[Queue] = None,
) -> None:
    """Run the Flask development server."""
    path = db_path or get_db_path()
    config = load_config(path)
    port = port or config.web_port
    app = create_app(config_path=path, scan_queue=scan_queue)
    app.run(host=host, port=port, threaded=True, use_reloader=False)
