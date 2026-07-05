"""
AnomalyWatch Flask Application.

Main application entry point.
"""

import sys
import signal
from flask import Flask
from pathlib import Path

from config import settings, get_logger
from routes import dashboard_bp, api_bp, stream_bp
from services import monitoring_service
from database import db

logger = get_logger(__name__)


def create_app():
    """
    Flask application factory.

    Returns:
        Configured Flask application.
    """
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )

    # Configure app
    app.config['SECRET_KEY'] = settings.flask.secret_key
    app.config['DEBUG'] = settings.flask.debug

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stream_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}", exc_info=True)
        return "Internal server error", 500

    # Health check endpoint
    @app.route('/health')
    def health():
        is_healthy = monitoring_service.is_healthy()
        status_code = 200 if is_healthy else 503

        return {
            'status': 'healthy' if is_healthy else 'unhealthy',
            'monitoring_running': monitoring_service.is_running
        }, status_code

    logger.info("Flask application created")

    return app


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        monitoring_service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main application entry point."""
    logger.info("=" * 60)
    logger.info("AnomalyWatch - Real-Time System Anomaly Detection")
    logger.info("=" * 60)

    # Ensure required directories exist
    models_dir = Path(settings.models.model_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Models directory: {models_dir}")

    # Initialize database
    logger.info(f"Database: {settings.database.path}")

    # Setup signal handlers
    setup_signal_handlers()

    # Create Flask app
    app = create_app()

    # Start monitoring service
    try:
        monitoring_service.start()
    except Exception as e:
        logger.error(f"Failed to start monitoring service: {e}", exc_info=True)
        sys.exit(1)

    # Start Flask server
    logger.info(
        f"Starting Flask server on {settings.flask.host}:{settings.flask.port}"
    )

    try:
        app.run(
            host=settings.flask.host,
            port=settings.flask.port,
            debug=settings.flask.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Flask server error: {e}", exc_info=True)
    finally:
        monitoring_service.stop()
        logger.info("Application shutdown complete")


if __name__ == '__main__':
    main()
