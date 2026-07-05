"""
Server-Sent Events (SSE) service for real-time updates.

Manages SSE client connections and broadcasts events.
"""

import json
import queue
import threading
from typing import Dict, Any, Set
from dataclasses import dataclass, asdict

from config import get_logger

logger = get_logger(__name__)


@dataclass
class SSEEvent:
    """Represents an SSE event."""
    event_type: str
    data: Dict[str, Any]
    event_id: str = None


class SSEService:
    """
    Manages Server-Sent Events for real-time dashboard updates.

    Handles client connections and broadcasts events to all connected clients.
    """

    def __init__(self):
        """Initialize the SSE service."""
        self._clients: Dict[str, queue.Queue] = {}
        self._client_lock = threading.Lock()
        self._event_counter = 0
        self._event_lock = threading.Lock()

    def register_client(self, client_id: str) -> queue.Queue:
        """
        Register a new SSE client.

        Args:
            client_id: Unique client identifier.

        Returns:
            Queue for client-specific events.
        """
        with self._client_lock:
            if client_id in self._clients:
                logger.warning(f"Client {client_id} already registered")
                return self._clients[client_id]

            client_queue = queue.Queue(maxsize=100)
            self._clients[client_id] = client_queue
            logger.info(f"Client {client_id} registered (total: {len(self._clients)})")

            return client_queue

    def unregister_client(self, client_id: str):
        """
        Unregister an SSE client.

        Args:
            client_id: Client identifier to remove.
        """
        with self._client_lock:
            if client_id in self._clients:
                del self._clients[client_id]
                logger.info(
                    f"Client {client_id} unregistered "
                    f"(remaining: {len(self._clients)})"
                )

    def get_client_count(self) -> int:
        """
        Get the number of connected clients.

        Returns:
            Number of active connections.
        """
        with self._client_lock:
            return len(self._clients)

    def broadcast(self, event_type: str, data: Dict[str, Any], event_id: str = None):
        """
        Broadcast an event to all connected clients.

        Args:
            event_type: Event type identifier.
            data: Event data dictionary.
            event_id: Optional event ID for client tracking.
        """
        if event_id is None:
            with self._event_lock:
                self._event_counter += 1
                event_id = str(self._event_counter)

        event = SSEEvent(event_type=event_type, data=data, event_id=event_id)

        with self._client_lock:
            dead_clients = []

            for client_id, client_queue in self._clients.items():
                try:
                    client_queue.put_nowait(event)
                except queue.Full:
                    logger.warning(f"Client {client_id} queue full, dropping event")
                    dead_clients.append(client_id)
                except Exception as e:
                    logger.error(f"Failed to send to client {client_id}: {e}")
                    dead_clients.append(client_id)

            # Remove dead clients
            for client_id in dead_clients:
                del self._clients[client_id]
                logger.info(f"Removed dead client {client_id}")

    def new_metric(self, timestamp: float, metrics: Dict[str, float], anomaly_score: float):
        """
        Broadcast a new metric collection event.

        Args:
            timestamp: Metric timestamp.
            metrics: Dictionary of metric values.
            anomaly_score: Overall anomaly score.
        """
        self.broadcast('metric', {
            'timestamp': timestamp,
            'metrics': metrics,
            'anomaly_score': anomaly_score
        })

    def anomaly_detected(
        self,
        timestamp: float,
        severity: str,
        score: float,
        anomalous_metrics: list
    ):
        """
        Broadcast an anomaly detection event.

        Args:
            timestamp: Detection timestamp.
            severity: Severity level (warning/critical).
            score: Anomaly score.
            anomalous_metrics: List of anomalous metrics.
        """
        self.broadcast('anomaly', {
            'timestamp': timestamp,
            'severity': severity,
            'score': score,
            'anomalous_metrics': anomalous_metrics
        })

    def alert(
        self,
        timestamp: float,
        severity: str,
        metric_name: str,
        message: str
    ):
        """
        Broadcast an alert event.

        Args:
            timestamp: Alert timestamp.
            severity: Severity level.
            metric_name: Affected metric.
            message: Alert message.
        """
        self.broadcast('alert', {
            'timestamp': timestamp,
            'severity': severity,
            'metric_name': metric_name,
            'message': message
        })

    def status_update(self, status: str, message: str):
        """
        Broadcast a system status update.

        Args:
            status: Status indicator (e.g., 'baseline_learning', 'monitoring').
            message: Status message.
        """
        self.broadcast('status', {
            'status': status,
            'message': message
        })

    def heartbeat(self):
        """Send a heartbeat event to keep connections alive."""
        self.broadcast('heartbeat', {'timestamp': __import__('time').time()})

    @staticmethod
    def format_sse_message(event: SSEEvent) -> str:
        """
        Format an SSE event for transmission.

        Args:
            event: SSE event object.

        Returns:
            Formatted SSE message string.
        """
        lines = []

        if event.event_id:
            lines.append(f"id: {event.event_id}")

        lines.append(f"event: {event.event_type}")

        data_json = json.dumps(event.data)
        lines.append(f"data: {data_json}")

        lines.append("")
        lines.append("")

        return "\n".join(lines)


# Global SSE service instance
sse_service = SSEService()
