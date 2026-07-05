"""
Alert routing and notification service.

Handles desktop notifications and GPIO alerts.
"""

import time
from typing import Dict, Optional
from threading import Lock

from config import settings, get_logger

logger = get_logger(__name__)


# Try to import notification library
try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    logger.warning("plyer not available, desktop notifications disabled")
    PLYER_AVAILABLE = False


class AlertService:
    """
    Manages alert routing and delivery.

    Handles desktop notifications, GPIO triggers, and alert deduplication.
    """

    def __init__(self):
        """Initialize the alert service."""
        self.last_alert_times: Dict[str, float] = {}
        self.alert_lock = Lock()
        self.gpio_controller = None

        # Try to initialize GPIO controller if enabled
        if settings.alerts.enable_gpio_alerts:
            try:
                from gpio import GPIOController
                self.gpio_controller = GPIOController()
                logger.info("GPIO controller initialized")
            except ImportError:
                logger.warning("GPIO module not available, GPIO alerts disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize GPIO: {e}")

    def send_alert(
        self,
        metric_name: str,
        severity: str,
        score: float,
        message: str
    ) -> bool:
        """
        Send an alert through configured channels.

        Args:
            metric_name: Name of the affected metric.
            severity: Alert severity (warning/critical).
            score: Anomaly score.
            message: Alert message.

        Returns:
            True if alert was sent, False if deduplicated.
        """
        # Check cooldown period
        if not self._should_send_alert(metric_name):
            logger.debug(f"Alert for {metric_name} suppressed (cooldown)")
            return False

        logger.info(f"Sending {severity} alert for {metric_name}: {message}")

        # Update last alert time
        with self.alert_lock:
            self.last_alert_times[metric_name] = time.time()

        # Send desktop notification
        if settings.alerts.enable_desktop_notifications:
            self._send_desktop_notification(severity, message)

        # Trigger GPIO alert
        if self.gpio_controller:
            self._trigger_gpio_alert(severity)

        return True

    def _should_send_alert(self, metric_name: str) -> bool:
        """
        Check if an alert should be sent (cooldown check).

        Args:
            metric_name: Metric name to check.

        Returns:
            True if alert should be sent.
        """
        with self.alert_lock:
            last_time = self.last_alert_times.get(metric_name, 0)
            elapsed = time.time() - last_time
            cooldown = settings.alerts.alert_cooldown_seconds

            return elapsed >= cooldown

    def _send_desktop_notification(self, severity: str, message: str):
        """
        Send a desktop notification.

        Args:
            severity: Alert severity.
            message: Alert message.
        """
        if not PLYER_AVAILABLE:
            return

        try:
            title = f"AnomalyWatch - {severity.upper()}"

            # Determine urgency
            if severity == 'critical':
                icon_name = 'dialog-error'
            else:
                icon_name = 'dialog-warning'

            plyer_notification.notify(
                title=title,
                message=message,
                app_name='AnomalyWatch',
                timeout=10
            )

            logger.debug(f"Desktop notification sent: {message}")

        except Exception as e:
            logger.warning(f"Failed to send desktop notification: {e}")

    def _trigger_gpio_alert(self, severity: str):
        """
        Trigger GPIO alert pattern.

        Args:
            severity: Alert severity.
        """
        if not self.gpio_controller:
            return

        try:
            self.gpio_controller.set_alert_level(severity)
            logger.debug(f"GPIO alert triggered: {severity}")

        except Exception as e:
            logger.warning(f"Failed to trigger GPIO alert: {e}")

    def clear_gpio_alert(self):
        """Clear GPIO alert (set to normal state)."""
        if self.gpio_controller:
            try:
                self.gpio_controller.set_alert_level('normal')
            except Exception as e:
                logger.warning(f"Failed to clear GPIO alert: {e}")

    def cleanup(self):
        """Cleanup resources."""
        if self.gpio_controller:
            try:
                self.gpio_controller.cleanup()
                logger.info("GPIO controller cleanup completed")
            except Exception as e:
                logger.error(f"GPIO cleanup failed: {e}")

    def get_alert_statistics(self) -> Dict:
        """
        Get alert statistics.

        Returns:
            Dictionary with alert stats.
        """
        with self.alert_lock:
            return {
                'total_metrics_alerted': len(self.last_alert_times),
                'recent_alerts': [
                    {
                        'metric': metric,
                        'last_alert_time': last_time
                    }
                    for metric, last_time in self.last_alert_times.items()
                ]
            }


# Global alert service instance
alert_service = AlertService()
