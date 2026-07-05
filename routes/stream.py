"""
Server-Sent Events (SSE) streaming routes.
"""

import time
import uuid
from flask import Blueprint, Response, stream_with_context

from services import sse_service
from services.sse_service import SSEEvent
from config import get_logger

logger = get_logger(__name__)

stream_bp = Blueprint('stream', __name__, url_prefix='/stream')


@stream_bp.route('/metrics')
def stream_metrics():
    """
    SSE endpoint for real-time metric updates.

    Streams events:
        - metric: New metric collection
        - anomaly: Anomaly detected
        - alert: Alert generated
        - status: Status update
        - heartbeat: Keep-alive ping

    Returns:
        SSE stream response.
    """
    client_id = str(uuid.uuid4())
    logger.info(f"New SSE client connected: {client_id}")

    def event_stream():
        """Generator function for SSE events."""
        client_queue = sse_service.register_client(client_id)

        try:
            # Send initial connection event
            yield sse_service.format_sse_message(
                SSEEvent(
                    event_type='connected',
                    data={'client_id': client_id, 'timestamp': time.time()}
                )
            )

            last_heartbeat = time.time()
            heartbeat_interval = 30

            while True:
                try:
                    # Check for new events with timeout
                    event = client_queue.get(timeout=1.0)
                    yield sse_service.format_sse_message(event)

                except Exception:
                    # Timeout or empty queue - send heartbeat if needed
                    current_time = time.time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        yield sse_service.format_sse_message(
                            SSEEvent(
                                event_type='heartbeat',
                                data={'timestamp': current_time}
                            )
                        )
                        last_heartbeat = current_time

        except GeneratorExit:
            logger.info(f"SSE client disconnected: {client_id}")

        finally:
            sse_service.unregister_client(client_id)

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@stream_bp.route('/test')
def test_stream():
    """
    Test SSE endpoint that sends events every second.

    Returns:
        SSE stream with test events.
    """
    def event_stream():
        """Generator for test events."""
        count = 0
        while count < 10:
            yield sse_service.format_sse_message(
                SSEEvent(
                    event_type='test',
                    data={'count': count, 'timestamp': time.time()}
                )
            )
            time.sleep(1)
            count += 1

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
