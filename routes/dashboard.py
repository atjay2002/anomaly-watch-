"""
Dashboard routes for the web interface.
"""

from flask import Blueprint, render_template

from services import monitoring_service
from config import settings, get_logger

logger = get_logger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """
    Render the main dashboard page.

    Returns:
        Rendered dashboard template.
    """
    try:
        status = monitoring_service.get_status()

        context = {
            'title': 'AnomalyWatch Dashboard',
            'monitoring_interval': settings.monitoring.interval_seconds,
            'baseline_duration_minutes': settings.monitoring.baseline_minutes,
            'status': status
        }

        return render_template('dashboard.html', **context)

    except Exception as e:
        logger.error(f"Dashboard rendering failed: {e}", exc_info=True)
        return f"Error loading dashboard: {str(e)}", 500
