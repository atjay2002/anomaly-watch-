"""Routes module for AnomalyWatch Flask application."""

from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.stream import stream_bp

__all__ = ['dashboard_bp', 'api_bp', 'stream_bp']
