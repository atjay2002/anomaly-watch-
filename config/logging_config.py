"""
Centralized logging configuration for AnomalyWatch.

Provides structured logging with file rotation and console output.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from config.settings import settings


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a logger with file and console handlers.

    Args:
        name: Logger name. If None, returns root logger.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.logging.level.upper()))

    # Create logs directory if it doesn't exist
    log_dir = Path(settings.logging.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler with rotation
    log_file = log_dir / 'anomalywatch.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=settings.logging.max_bytes,
        backupCount=settings.logging.backup_count
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.logging.level.upper()))

    # Formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return setup_logging(name)
