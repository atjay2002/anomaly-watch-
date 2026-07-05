"""
Database models and connection management for AnomalyWatch.

Provides lightweight ORM-like access to SQLite database.
"""

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import settings, get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """Represents a system metric record."""
    timestamp: float
    metric_name: str
    value: float
    anomaly_score: float = 0.0
    is_anomaly: bool = False
    id: Optional[int] = None


@dataclass
class Baseline:
    """Represents baseline statistics for a metric."""
    metric_name: str
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    p25: float
    p50: float
    p75: float
    p95: float
    sample_count: int
    id: Optional[int] = None


@dataclass
class Alert:
    """Represents an alert record."""
    timestamp: float
    severity: str
    metric_name: str
    message: str
    metric_value: Optional[float] = None
    anomaly_score: Optional[float] = None
    acknowledged: bool = False
    acknowledged_at: Optional[float] = None
    id: Optional[int] = None


class DatabaseConnection:
    """
    Manages SQLite database connection and initialization.

    Provides connection pooling and automatic schema initialization.
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection manager.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Create database and initialize schema if it doesn't exist."""
        db_file = Path(self.db_path)
        is_new = not db_file.exists()

        if is_new:
            logger.info(f"Creating new database at {self.db_path}")
            db_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self.get_connection() as conn:
                if is_new:
                    self._initialize_schema(conn)
                    logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def _initialize_schema(self, conn: sqlite3.Connection):
        """
        Initialize database schema from SQL file.

        Args:
            conn: SQLite connection.
        """
        schema_path = Path(__file__).parent / 'schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            SQLite connection with row factory enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dicts.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            List of row dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            Number of affected rows or last inserted row ID.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    def cleanup_old_data(self, retention_days: int):
        """
        Remove old metric and alert data beyond retention period.

        Args:
            retention_days: Number of days to retain data.
        """
        cutoff_timestamp = time.time() - (retention_days * 86400)

        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM metrics WHERE timestamp < ?",
                    (cutoff_timestamp,)
                )
                metrics_deleted = cursor.rowcount

                cursor = conn.execute(
                    "DELETE FROM alerts WHERE timestamp < ?",
                    (cutoff_timestamp,)
                )
                alerts_deleted = cursor.rowcount

                conn.commit()
                logger.info(
                    f"Cleaned up old data: {metrics_deleted} metrics, "
                    f"{alerts_deleted} alerts removed"
                )
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}", exc_info=True)


# Global database instance
db = DatabaseConnection(settings.database.path)
