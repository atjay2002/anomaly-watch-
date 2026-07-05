"""
REST API routes for AnomalyWatch.
"""

import time
from flask import Blueprint, jsonify, request

from database import MetricRepository, BaselineRepository, AlertRepository
from services import monitoring_service
from config import get_logger

logger = get_logger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/metrics/latest', methods=['GET'])
def get_latest_metrics():
    """
    Get the latest value for each metric.

    Returns:
        JSON with latest metric values.
    """
    try:
        latest_metrics = MetricRepository.get_latest_metrics()

        response = {
            'timestamp': time.time(),
            'metrics': {
                name: {
                    'value': metric.value,
                    'anomaly_score': metric.anomaly_score,
                    'is_anomaly': metric.is_anomaly,
                    'timestamp': metric.timestamp
                }
                for name, metric in latest_metrics.items()
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to get latest metrics: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/metrics/history', methods=['GET'])
def get_metric_history():
    """
    Get historical data for a specific metric.

    Query params:
        metric: Metric name (required)
        duration: Duration in seconds (default: 300)

    Returns:
        JSON with historical metric data.
    """
    try:
        metric_name = request.args.get('metric')
        if not metric_name:
            return jsonify({'error': 'metric parameter required'}), 400

        duration = int(request.args.get('duration', 300))

        end_time = time.time()
        start_time = end_time - duration

        metrics = MetricRepository.get_metrics_in_range(
            metric_name,
            start_time,
            end_time
        )

        response = {
            'metric_name': metric_name,
            'start_time': start_time,
            'end_time': end_time,
            'data': [
                {
                    'timestamp': m.timestamp,
                    'value': m.value,
                    'anomaly_score': m.anomaly_score,
                    'is_anomaly': m.is_anomaly
                }
                for m in metrics
            ]
        }

        return jsonify(response), 200

    except ValueError:
        return jsonify({'error': 'Invalid duration parameter'}), 400
    except Exception as e:
        logger.error(f"Failed to get metric history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/baseline/stats', methods=['GET'])
def get_baseline_stats():
    """
    Get current baseline statistics.

    Returns:
        JSON with baseline statistics for all metrics.
    """
    try:
        baselines = BaselineRepository.get_all_baselines()

        response = {
            'baselines': {
                b.metric_name: {
                    'mean': b.mean,
                    'std_dev': b.std_dev,
                    'min': b.min_value,
                    'max': b.max_value,
                    'p25': b.p25,
                    'p50': b.p50,
                    'p75': b.p75,
                    'p95': b.p95,
                    'sample_count': b.sample_count
                }
                for b in baselines
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to get baseline stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/baseline/train', methods=['POST'])
def trigger_baseline_training():
    """
    Trigger baseline retraining using recent historical data.

    Returns:
        JSON with training status.
    """
    try:
        monitoring_service.trigger_baseline_retraining()

        return jsonify({
            'status': 'success',
            'message': 'Baseline retraining completed'
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Baseline training failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Get recent alerts.

    Query params:
        active_only: Return only unacknowledged alerts (default: false)
        limit: Maximum number of alerts (default: 50)

    Returns:
        JSON with alert list.
    """
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))

        if active_only:
            alerts = AlertRepository.get_active_alerts(limit)
        else:
            alerts = AlertRepository.get_recent_alerts(limit)

        response = {
            'alerts': [
                {
                    'id': a.id,
                    'timestamp': a.timestamp,
                    'severity': a.severity,
                    'metric_name': a.metric_name,
                    'metric_value': a.metric_value,
                    'anomaly_score': a.anomaly_score,
                    'message': a.message,
                    'acknowledged': a.acknowledged,
                    'acknowledged_at': a.acknowledged_at
                }
                for a in alerts
            ]
        }

        return jsonify(response), 200

    except ValueError:
        return jsonify({'error': 'Invalid parameter'}), 400
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id: int):
    """
    Acknowledge an alert.

    Args:
        alert_id: Alert ID to acknowledge.

    Returns:
        JSON with acknowledgment status.
    """
    try:
        success = AlertRepository.acknowledge_alert(alert_id)

        if success:
            return jsonify({
                'status': 'success',
                'message': f'Alert {alert_id} acknowledged'
            }), 200
        else:
            return jsonify({'error': 'Alert not found'}), 404

    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """
    Get overall system status and health.

    Returns:
        JSON with system status.
    """
    try:
        status = monitoring_service.get_status()
        is_healthy = monitoring_service.is_healthy()

        response = {
            'status': 'healthy' if is_healthy else 'unhealthy',
            'monitoring': status,
            'timestamp': time.time()
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to get system status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/testing/generate-anomaly', methods=['POST'])
def generate_anomaly():
    """
    Trigger an anomaly generator for testing.

    JSON body:
        type: Anomaly type (cpu/memory/disk/network/thread)
        duration: Duration in seconds (default: 10)
        intensity: Intensity level 1-10 (default: 5)

    Returns:
        JSON with generator status.
    """
    try:
        data = request.get_json() or {}

        anomaly_type = data.get('type', 'cpu')
        duration = int(data.get('duration', 10))
        intensity = int(data.get('intensity', 5))

        # Import and use anomaly generator
        from testing import AnomalyGenerator

        generator = AnomalyGenerator()

        if anomaly_type == 'cpu':
            generator.generate_cpu_spike(duration, intensity)
        elif anomaly_type == 'memory':
            generator.generate_memory_spike(duration, intensity)
        elif anomaly_type == 'disk':
            generator.generate_disk_spike(duration, intensity)
        elif anomaly_type == 'network':
            generator.generate_network_spike(duration, intensity)
        elif anomaly_type == 'thread':
            generator.generate_thread_bomb(duration, intensity)
        else:
            return jsonify({'error': f'Unknown anomaly type: {anomaly_type}'}), 400

        return jsonify({
            'status': 'success',
            'message': f'{anomaly_type} anomaly generation started',
            'duration': duration,
            'intensity': intensity
        }), 200

    except ValueError:
        return jsonify({'error': 'Invalid parameter values'}), 400
    except Exception as e:
        logger.error(f"Anomaly generation failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes."""
    return jsonify({'error': 'Endpoint not found'}), 404


@api_bp.errorhandler(500)
def api_server_error(error):
    """Handle 500 errors for API routes."""
    return jsonify({'error': 'Internal server error'}), 500
