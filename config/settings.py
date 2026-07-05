"""
Configuration management for AnomalyWatch.

This module provides centralized configuration using environment variables
with sensible defaults for local deployment.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = os.getenv('ANOMALY_DB_PATH', str(PROJECT_ROOT / 'anomalywatch.db'))
    retention_days: int = int(os.getenv('ANOMALY_DB_RETENTION_DAYS', '7'))


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    interval_seconds: int = int(os.getenv('ANOMALY_MONITOR_INTERVAL', '5'))
    baseline_minutes: int = int(os.getenv('ANOMALY_BASELINE_MINUTES', '15'))
    enable_baseline_learning: bool = os.getenv('ANOMALY_ENABLE_BASELINE', 'true').lower() == 'true'


@dataclass
class DetectionConfig:
    """Anomaly detection configuration."""
    isolation_forest_contamination: float = float(os.getenv('ANOMALY_IF_CONTAMINATION', '0.1'))
    zscore_threshold: float = float(os.getenv('ANOMALY_ZSCORE_THRESHOLD', '3.0'))
    hybrid_if_weight: float = float(os.getenv('ANOMALY_IF_WEIGHT', '0.6'))
    hybrid_zscore_weight: float = float(os.getenv('ANOMALY_ZSCORE_WEIGHT', '0.4'))

    # Severity thresholds (0-100 scale)
    severity_warning_threshold: int = int(os.getenv('ANOMALY_WARNING_THRESHOLD', '30'))
    severity_critical_threshold: int = int(os.getenv('ANOMALY_CRITICAL_THRESHOLD', '70'))


@dataclass
class AlertConfig:
    """Alert configuration."""
    enable_desktop_notifications: bool = os.getenv('ANOMALY_ENABLE_DESKTOP', 'true').lower() == 'true'
    enable_gpio_alerts: bool = os.getenv('ANOMALY_ENABLE_GPIO', 'false').lower() == 'true'
    alert_cooldown_seconds: int = int(os.getenv('ANOMALY_ALERT_COOLDOWN', '60'))


@dataclass
class ModelConfig:
    """ML model persistence configuration."""
    model_dir: str = os.getenv('ANOMALY_MODEL_DIR', str(PROJECT_ROOT / 'models'))
    isolation_forest_path: Optional[str] = None
    baseline_stats_path: Optional[str] = None

    def __post_init__(self):
        model_dir = Path(self.model_dir)
        self.isolation_forest_path = str(model_dir / 'isolation_forest.pkl')
        self.baseline_stats_path = str(model_dir / 'baseline_stats.json')


@dataclass
class FlaskConfig:
    """Flask application configuration."""
    host: str = os.getenv('FLASK_HOST', '0.0.0.0')
    port: int = int(os.getenv('FLASK_PORT', '5000'))
    debug: bool = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    secret_key: str = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_dir: str = os.getenv('LOG_DIR', str(PROJECT_ROOT / 'logs'))
    max_bytes: int = int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
    backup_count: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))


@dataclass
class Settings:
    """Global application settings."""
    database: DatabaseConfig
    monitoring: MonitoringConfig
    detection: DetectionConfig
    alerts: AlertConfig
    models: ModelConfig
    flask: FlaskConfig
    logging: LoggingConfig

    @classmethod
    def load(cls) -> 'Settings':
        """Load settings from environment variables with defaults."""
        return cls(
            database=DatabaseConfig(),
            monitoring=MonitoringConfig(),
            detection=DetectionConfig(),
            alerts=AlertConfig(),
            models=ModelConfig(),
            flask=FlaskConfig(),
            logging=LoggingConfig()
        )


# Global settings instance
settings = Settings.load()
