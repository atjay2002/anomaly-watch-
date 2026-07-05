"""
Data access layer for AnomalyWatch.

Provides repository pattern for database operations.
"""

import time
from typing import List, Optional, Dict, Any

from database.models import db, Metric, Baseline, Alert
from config import get_logger

logger = get_logger(__name__)


class MetricRepository:
    """Repository for metric data access."""

    @staticmethod
    def insert_metric(metric: Metric) -> int:
        """
        Insert a new metric record.

        Args:
            metric: Metric instance to insert.

        Returns:
            ID of inserted record.
        """
        query = """
            INSERT INTO metrics (timestamp, metric_name, value, anomaly_score, is_anomaly)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (
            metric.timestamp,
            metric.metric_name,
            metric.value,
            metric.anomaly_score,
            1 if metric.is_anomaly else 0
        )
        return db.execute_update(query, params)

    @staticmethod
    def insert_metrics_batch(metrics: List[Metric]) -> int:
        """
        Insert multiple metrics in a single transaction.

        Args:
            metrics: List of Metric instances.

        Returns:
            Number of inserted records.
        """
        if not metrics:
            return 0

        query = """
            INSERT INTO metrics (timestamp, metric_name, value, anomaly_score, is_anomaly)
            VALUES (?, ?, ?, ?, ?)
        """

        try:
            with db.get_connection() as conn:
                conn.executemany(
                    query,
                    [
                        (m.timestamp, m.metric_name, m.value, m.anomaly_score, 1 if m.is_anomaly else 0)
                        for m in metrics
                    ]
                )
                return len(metrics)
        except Exception as e:
            logger.error(f"Batch insert failed: {e}", exc_info=True)
            return 0

    @staticmethod
    def get_recent_metrics(metric_name: Optional[str] = None, limit: int = 100) -> List[Metric]:
        """
        Get recent metrics, optionally filtered by name.

        Args:
            metric_name: Filter by metric name (optional).
            limit: Maximum number of records to return.

        Returns:
            List of Metric instances.
        """
        if metric_name:
            query = """
                SELECT id, timestamp, metric_name, value, anomaly_score, is_anomaly
                FROM metrics
                WHERE metric_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params = (metric_name, limit)
        else:
            query = """
                SELECT id, timestamp, metric_name, value, anomaly_score, is_anomaly
                FROM metrics
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params = (limit,)

        rows = db.execute_query(query, params)
        return [
            Metric(
                id=row['id'],
                timestamp=row['timestamp'],
                metric_name=row['metric_name'],
                value=row['value'],
                anomaly_score=row['anomaly_score'],
                is_anomaly=bool(row['is_anomaly'])
            )
            for row in rows
        ]

    @staticmethod
    def get_metrics_in_range(
        metric_name: str,
        start_timestamp: float,
        end_timestamp: float
    ) -> List[Metric]:
        """
        Get metrics within a time range.

        Args:
            metric_name: Metric name.
            start_timestamp: Start time (Unix timestamp).
            end_timestamp: End time (Unix timestamp).

        Returns:
            List of Metric instances.
        """
        query = """
            SELECT id, timestamp, metric_name, value, anomaly_score, is_anomaly
            FROM metrics
            WHERE metric_name = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        rows = db.execute_query(query, (metric_name, start_timestamp, end_timestamp))
        return [
            Metric(
                id=row['id'],
                timestamp=row['timestamp'],
                metric_name=row['metric_name'],
                value=row['value'],
                anomaly_score=row['anomaly_score'],
                is_anomaly=bool(row['is_anomaly'])
            )
            for row in rows
        ]

    @staticmethod
    def get_latest_metrics() -> Dict[str, Metric]:
        """
        Get the most recent value for each metric.

        Returns:
            Dictionary mapping metric name to latest Metric.
        """
        query = """
            SELECT m1.id, m1.timestamp, m1.metric_name, m1.value, m1.anomaly_score, m1.is_anomaly
            FROM metrics m1
            INNER JOIN (
                SELECT metric_name, MAX(timestamp) as max_timestamp
                FROM metrics
                GROUP BY metric_name
            ) m2 ON m1.metric_name = m2.metric_name AND m1.timestamp = m2.max_timestamp
        """
        rows = db.execute_query(query)
        return {
            row['metric_name']: Metric(
                id=row['id'],
                timestamp=row['timestamp'],
                metric_name=row['metric_name'],
                value=row['value'],
                anomaly_score=row['anomaly_score'],
                is_anomaly=bool(row['is_anomaly'])
            )
            for row in rows
        }


class BaselineRepository:
    """Repository for baseline statistics."""

    @staticmethod
    def save_baseline(baseline: Baseline) -> int:
        """
        Save or update baseline statistics.

        Args:
            baseline: Baseline instance.

        Returns:
            ID of inserted/updated record.
        """
        query = """
            INSERT INTO baselines (
                metric_name, mean, std_dev, min_value, max_value,
                p25, p50, p75, p95, sample_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(metric_name) DO UPDATE SET
                mean = excluded.mean,
                std_dev = excluded.std_dev,
                min_value = excluded.min_value,
                max_value = excluded.max_value,
                p25 = excluded.p25,
                p50 = excluded.p50,
                p75 = excluded.p75,
                p95 = excluded.p95,
                sample_count = excluded.sample_count,
                updated_at = CURRENT_TIMESTAMP
        """
        params = (
            baseline.metric_name,
            baseline.mean,
            baseline.std_dev,
            baseline.min_value,
            baseline.max_value,
            baseline.p25,
            baseline.p50,
            baseline.p75,
            baseline.p95,
            baseline.sample_count
        )
        return db.execute_update(query, params)

    @staticmethod
    def get_baseline(metric_name: str) -> Optional[Baseline]:
        """
        Get baseline statistics for a metric.

        Args:
            metric_name: Metric name.

        Returns:
            Baseline instance or None if not found.
        """
        query = """
            SELECT id, metric_name, mean, std_dev, min_value, max_value,
                   p25, p50, p75, p95, sample_count
            FROM baselines
            WHERE metric_name = ?
        """
        rows = db.execute_query(query, (metric_name,))
        if not rows:
            return None

        row = rows[0]
        return Baseline(
            id=row['id'],
            metric_name=row['metric_name'],
            mean=row['mean'],
            std_dev=row['std_dev'],
            min_value=row['min_value'],
            max_value=row['max_value'],
            p25=row['p25'],
            p50=row['p50'],
            p75=row['p75'],
            p95=row['p95'],
            sample_count=row['sample_count']
        )

    @staticmethod
    def get_all_baselines() -> List[Baseline]:
        """
        Get all baseline statistics.

        Returns:
            List of Baseline instances.
        """
        query = """
            SELECT id, metric_name, mean, std_dev, min_value, max_value,
                   p25, p50, p75, p95, sample_count
            FROM baselines
        """
        rows = db.execute_query(query)
        return [
            Baseline(
                id=row['id'],
                metric_name=row['metric_name'],
                mean=row['mean'],
                std_dev=row['std_dev'],
                min_value=row['min_value'],
                max_value=row['max_value'],
                p25=row['p25'],
                p50=row['p50'],
                p75=row['p75'],
                p95=row['p95'],
                sample_count=row['sample_count']
            )
            for row in rows
        ]


class AlertRepository:
    """Repository for alert data."""

    @staticmethod
    def insert_alert(alert: Alert) -> int:
        """
        Insert a new alert.

        Args:
            alert: Alert instance.

        Returns:
            ID of inserted record.
        """
        query = """
            INSERT INTO alerts (
                timestamp, severity, metric_name, metric_value,
                anomaly_score, message, acknowledged
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            alert.timestamp,
            alert.severity,
            alert.metric_name,
            alert.metric_value,
            alert.anomaly_score,
            alert.message,
            1 if alert.acknowledged else 0
        )
        return db.execute_update(query, params)

    @staticmethod
    def get_active_alerts(limit: int = 50) -> List[Alert]:
        """
        Get unacknowledged alerts.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of Alert instances.
        """
        query = """
            SELECT id, timestamp, severity, metric_name, metric_value,
                   anomaly_score, message, acknowledged, acknowledged_at
            FROM alerts
            WHERE acknowledged = 0
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = db.execute_query(query, (limit,))
        return [
            Alert(
                id=row['id'],
                timestamp=row['timestamp'],
                severity=row['severity'],
                metric_name=row['metric_name'],
                metric_value=row['metric_value'],
                anomaly_score=row['anomaly_score'],
                message=row['message'],
                acknowledged=bool(row['acknowledged']),
                acknowledged_at=row['acknowledged_at']
            )
            for row in rows
        ]

    @staticmethod
    def acknowledge_alert(alert_id: int) -> bool:
        """
        Mark an alert as acknowledged.

        Args:
            alert_id: Alert ID.

        Returns:
            True if successful, False otherwise.
        """
        query = """
            UPDATE alerts
            SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        affected = db.execute_update(query, (alert_id,))
        return affected > 0

    @staticmethod
    def get_recent_alerts(limit: int = 100) -> List[Alert]:
        """
        Get recent alerts regardless of acknowledgment status.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of Alert instances.
        """
        query = """
            SELECT id, timestamp, severity, metric_name, metric_value,
                   anomaly_score, message, acknowledged, acknowledged_at
            FROM alerts
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = db.execute_query(query, (limit,))
        return [
            Alert(
                id=row['id'],
                timestamp=row['timestamp'],
                severity=row['severity'],
                metric_name=row['metric_name'],
                metric_value=row['metric_value'],
                anomaly_score=row['anomaly_score'],
                message=row['message'],
                acknowledged=bool(row['acknowledged']),
                acknowledged_at=row['acknowledged_at']
            )
            for row in rows
        ]


class SystemMetadataRepository:
    """Repository for system metadata."""

    @staticmethod
    def set_metadata(key: str, value: str):
        """
        Set a metadata key-value pair.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        query = """
            INSERT INTO system_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """
        db.execute_update(query, (key, value))

    @staticmethod
    def get_metadata(key: str) -> Optional[str]:
        """
        Get a metadata value by key.

        Args:
            key: Metadata key.

        Returns:
            Metadata value or None if not found.
        """
        query = "SELECT value FROM system_metadata WHERE key = ?"
        rows = db.execute_query(query, (key,))
        return rows[0]['value'] if rows else None
