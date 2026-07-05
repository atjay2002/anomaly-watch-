"""
Core monitoring service orchestration.

Coordinates metric collection, anomaly detection, and alerting.
"""

import time
import threading
from typing import Optional

from collectors import SystemMetricsCollector, MetricAggregator
from detectors import BaselineManager
from database import MetricRepository, Metric, AlertRepository, Alert, db
from services.sse_service import sse_service
from services.alert_service import alert_service
from config import settings, get_logger

logger = get_logger(__name__)


class MonitoringService:
    """
    Core monitoring service that orchestrates the entire monitoring pipeline.

    Runs a background loop that:
    1. Collects system metrics
    2. Computes anomaly scores
    3. Stores metrics in database
    4. Triggers alerts if needed
    5. Broadcasts updates via SSE
    """

    def __init__(self):
        """Initialize the monitoring service."""
        self.collector = SystemMetricsCollector()
        self.aggregator = MetricAggregator()
        self.baseline_manager = BaselineManager()

        self.is_running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self.cycle_count = 0
        self.error_count = 0
        self.last_cycle_time = None

    def start(self):
        """Start the monitoring service in a background thread."""
        if self.is_running:
            logger.warning("Monitoring service already running")
            return

        logger.info("Starting monitoring service")

        # Try to load existing baseline
        logger.info("Loading baseline models...")
        self.baseline_manager.load_baseline()

        # If no baseline exists and auto-learning enabled, start learning
        if not self.baseline_manager.is_baseline_available():
            if settings.monitoring.enable_baseline_learning:
                logger.info("No baseline found, starting baseline learning")
                self.baseline_manager.start_baseline_learning()
                sse_service.status_update(
                    'baseline_learning',
                    f'Learning baseline for {settings.monitoring.baseline_minutes} minutes'
                )
            else:
                logger.warning(
                    "No baseline available and learning disabled. "
                    "Anomaly detection will not work until baseline is trained."
                )

        # Start monitoring loop
        self.is_running = True
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        logger.info("Monitoring service started successfully")

    def stop(self):
        """Stop the monitoring service gracefully."""
        if not self.is_running:
            return

        logger.info("Stopping monitoring service")

        self.stop_event.set()

        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)

        self.is_running = False

        # Cleanup
        alert_service.cleanup()

        logger.info("Monitoring service stopped")

    def _monitoring_loop(self):
        """Main monitoring loop (runs in background thread)."""
        logger.info("Monitoring loop started")

        while not self.stop_event.is_set():
            cycle_start = time.time()

            try:
                self._execute_monitoring_cycle()
                self.cycle_count += 1

            except Exception as e:
                self.error_count += 1
                logger.error(f"Monitoring cycle failed: {e}", exc_info=True)

            # Calculate sleep time to maintain interval
            cycle_duration = time.time() - cycle_start
            sleep_time = max(0, settings.monitoring.interval_seconds - cycle_duration)

            if sleep_time > 0:
                self.stop_event.wait(sleep_time)

            self.last_cycle_time = time.time()

        logger.info("Monitoring loop exited")

    def _execute_monitoring_cycle(self):
        """Execute a single monitoring cycle."""
        # Collect metrics
        metrics = self.collector.collect_all()
        timestamp = metrics['timestamp']

        # Flatten metrics
        flattened_metrics = self.aggregator.flatten_metrics(metrics)

        # Handle baseline learning
        if self.baseline_manager.is_learning:
            self.baseline_manager.add_baseline_sample(flattened_metrics)

            if self.baseline_manager.is_baseline_complete():
                logger.info("Baseline learning period complete, training models...")
                self.baseline_manager.complete_baseline_learning()
                logger.info("Baseline training completed, starting anomaly detection")

                sse_service.status_update(
                    'baseline_complete',
                    'Baseline learning complete, monitoring active'
                )

            else:
                # During learning, just store metrics without anomaly detection
                self._store_metrics(timestamp, flattened_metrics, 0.0, 'normal')
                return

        # Anomaly detection (if baseline available)
        if self.baseline_manager.is_baseline_available():
            anomaly_score, severity = self._detect_anomaly(flattened_metrics)

            # Store metrics with anomaly scores
            self._store_metrics(timestamp, flattened_metrics, anomaly_score, severity)

            # Broadcast metrics via SSE
            sse_service.new_metric(timestamp, flattened_metrics, anomaly_score)

            # Handle alerts
            if severity != 'normal':
                self._handle_anomaly_alert(timestamp, severity, anomaly_score, flattened_metrics)

            # Clear GPIO if returning to normal
            if severity == 'normal':
                alert_service.clear_gpio_alert()

        else:
            # No baseline available, store without detection
            self._store_metrics(timestamp, flattened_metrics, 0.0, 'normal')

    def _detect_anomaly(self, metrics: dict) -> tuple:
        """
        Detect anomalies in metrics.

        Args:
            metrics: Flattened metrics dictionary.

        Returns:
            Tuple of (anomaly_score, severity).
        """
        try:
            scorer = self.baseline_manager.scorer
            if scorer is None:
                return 0.0, 'normal'

            # Prepare feature vector
            feature_vector = self.aggregator.to_feature_vector(metrics)

            # Get detailed prediction
            prediction = scorer.predict_with_details(feature_vector, metrics)

            return prediction['score'], prediction['severity']

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}", exc_info=True)
            return 0.0, 'normal'

    def _store_metrics(self, timestamp: float, metrics: dict, anomaly_score: float, severity: str):
        """
        Store metrics in database.

        Args:
            timestamp: Metric timestamp.
            metrics: Flattened metrics dictionary.
            anomaly_score: Overall anomaly score.
            severity: Severity level.
        """
        try:
            metric_objects = []

            for metric_name, value in metrics.items():
                metric = Metric(
                    timestamp=timestamp,
                    metric_name=metric_name,
                    value=value,
                    anomaly_score=anomaly_score,
                    is_anomaly=(severity != 'normal')
                )
                metric_objects.append(metric)

            # Batch insert
            MetricRepository.insert_metrics_batch(metric_objects)

        except Exception as e:
            logger.error(f"Failed to store metrics: {e}", exc_info=True)

    def _handle_anomaly_alert(
        self,
        timestamp: float,
        severity: str,
        anomaly_score: float,
        metrics: dict
    ):
        """
        Handle anomaly alert generation and routing.

        Args:
            timestamp: Detection timestamp.
            severity: Severity level.
            anomaly_score: Anomaly score.
            metrics: Current metrics.
        """
        try:
            # Get anomalous metrics details
            scorer = self.baseline_manager.scorer
            if scorer:
                feature_vector = self.aggregator.to_feature_vector(metrics)
                details = scorer.predict_with_details(feature_vector, metrics)
                anomalous_metrics = details.get('anomalous_metrics', [])
            else:
                anomalous_metrics = []

            # Broadcast anomaly via SSE
            sse_service.anomaly_detected(
                timestamp=timestamp,
                severity=severity,
                score=anomaly_score,
                anomalous_metrics=anomalous_metrics
            )

            # Generate alert message
            if anomalous_metrics:
                top_metric = anomalous_metrics[0]['name']
                message = (
                    f"{severity.capitalize()} anomaly detected "
                    f"(score: {anomaly_score:.1f}). "
                    f"Top anomalous metric: {top_metric}"
                )
            else:
                message = f"{severity.capitalize()} anomaly detected (score: {anomaly_score:.1f})"

            # Send alert through alert service
            alert_sent = alert_service.send_alert(
                metric_name='system_overall',
                severity=severity,
                score=anomaly_score,
                message=message
            )

            # Store alert in database if sent
            if alert_sent:
                alert = Alert(
                    timestamp=timestamp,
                    severity=severity,
                    metric_name='system_overall',
                    metric_value=None,
                    anomaly_score=anomaly_score,
                    message=message
                )
                AlertRepository.insert_alert(alert)

                # Broadcast alert via SSE
                sse_service.alert(
                    timestamp=timestamp,
                    severity=severity,
                    metric_name='system_overall',
                    message=message
                )

        except Exception as e:
            logger.error(f"Failed to handle anomaly alert: {e}", exc_info=True)

    def get_status(self) -> dict:
        """
        Get monitoring service status.

        Returns:
            Status dictionary.
        """
        baseline_info = self.baseline_manager.get_baseline_info()

        return {
            'is_running': self.is_running,
            'cycle_count': self.cycle_count,
            'error_count': self.error_count,
            'last_cycle_time': self.last_cycle_time,
            'baseline': baseline_info,
            'interval_seconds': settings.monitoring.interval_seconds,
            'connected_clients': sse_service.get_client_count()
        }

    def trigger_baseline_retraining(self):
        """Trigger baseline retraining using recent historical data."""
        if self.baseline_manager.is_learning:
            raise ValueError("Cannot retrain during baseline learning")

        logger.info("Triggering baseline retraining")

        try:
            # Use last 15 minutes of data
            window_seconds = settings.monitoring.baseline_minutes * 60
            self.baseline_manager.retrain_baseline(window_seconds)

            logger.info("Baseline retraining completed successfully")

            sse_service.status_update(
                'baseline_retrained',
                'Baseline has been retrained with recent data'
            )

        except Exception as e:
            logger.error(f"Baseline retraining failed: {e}", exc_info=True)
            raise

    def is_healthy(self) -> bool:
        """
        Check if monitoring service is healthy.

        Returns:
            True if healthy.
        """
        if not self.is_running:
            return False

        # Check if monitoring loop is stalled
        if self.last_cycle_time:
            time_since_last_cycle = time.time() - self.last_cycle_time
            max_interval = settings.monitoring.interval_seconds * 3

            if time_since_last_cycle > max_interval:
                logger.warning("Monitoring loop appears stalled")
                return False

        # Check error rate
        if self.cycle_count > 0:
            error_rate = self.error_count / self.cycle_count
            if error_rate > 0.5:
                logger.warning(f"High error rate: {error_rate:.2%}")
                return False

        return True


# Global monitoring service instance
monitoring_service = MonitoringService()
