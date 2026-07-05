# AnomalyWatch API Documentation

## REST API Endpoints

### Metrics

#### GET /api/metrics/latest
Get the latest value for each metric.

**Response**:
```json
{
  "timestamp": 1735000000.0,
  "metrics": {
    "cpu_percent": {
      "value": 45.2,
      "anomaly_score": 15.3,
      "is_anomaly": false,
      "timestamp": 1735000000.0
    }
  }
}
```

#### GET /api/metrics/history
Get historical data for a specific metric.

**Query Parameters**:
- `metric` (required): Metric name
- `duration` (optional): Duration in seconds (default: 300)

**Response**:
```json
{
  "metric_name": "cpu_percent",
  "start_time": 1735000000.0,
  "end_time": 1735000300.0,
  "data": [
    {
      "timestamp": 1735000005.0,
      "value": 42.1,
      "anomaly_score": 12.5,
      "is_anomaly": false
    }
  ]
}
```

### Baseline

#### GET /api/baseline/stats
Get current baseline statistics.

**Response**:
```json
{
  "baselines": {
    "cpu_percent": {
      "mean": 35.2,
      "std_dev": 12.5,
      "min": 5.0,
      "max": 95.3,
      "p25": 25.0,
      "p50": 32.1,
      "p75": 45.8,
      "p95": 72.3,
      "sample_count": 180
    }
  }
}
```

#### POST /api/baseline/train
Trigger baseline retraining.

**Response**:
```json
{
  "status": "success",
  "message": "Baseline retraining completed"
}
```

### Alerts

#### GET /api/alerts
Get recent alerts.

**Query Parameters**:
- `active_only` (optional): Return only unacknowledged (default: false)
- `limit` (optional): Maximum alerts (default: 50)

**Response**:
```json
{
  "alerts": [
    {
      "id": 1,
      "timestamp": 1735000000.0,
      "severity": "critical",
      "metric_name": "system_overall",
      "metric_value": null,
      "anomaly_score": 85.3,
      "message": "Critical anomaly detected",
      "acknowledged": false,
      "acknowledged_at": null
    }
  ]
}
```

#### POST /api/alerts/{id}/acknowledge
Acknowledge an alert.

**Response**:
```json
{
  "status": "success",
  "message": "Alert 1 acknowledged"
}
```

### System

#### GET /api/system/status
Get system health and status.

**Response**:
```json
{
  "status": "healthy",
  "monitoring": {
    "is_running": true,
    "cycle_count": 500,
    "error_count": 0,
    "last_cycle_time": 1735000000.0,
    "baseline": {
      "is_available": true,
      "is_learning": false,
      "trained_at": 1734999100.0
    },
    "interval_seconds": 5,
    "connected_clients": 2
  },
  "timestamp": 1735000000.0
}
```

### Testing

#### POST /api/testing/generate-anomaly
Trigger synthetic anomaly.

**Request Body**:
```json
{
  "type": "cpu",
  "duration": 10,
  "intensity": 7
}
```

**Types**: `cpu`, `memory`, `disk`, `network`, `thread`  
**Intensity**: 1-10 (higher = more intense)

**Response**:
```json
{
  "status": "success",
  "message": "cpu anomaly generation started",
  "duration": 10,
  "intensity": 7
}
```

## SSE Stream

### GET /stream/metrics
Server-Sent Events stream for real-time updates.

**Event Types**:

#### connected
```
event: connected
data: {"client_id": "uuid", "timestamp": 1735000000.0}
```

#### metric
```
event: metric
data: {
  "timestamp": 1735000000.0,
  "metrics": {"cpu_percent": 45.2, ...},
  "anomaly_score": 15.3
}
```

#### anomaly
```
event: anomaly
data: {
  "timestamp": 1735000000.0,
  "severity": "critical",
  "score": 85.3,
  "anomalous_metrics": [
    {"name": "cpu_percent", "score": 90.2}
  ]
}
```

#### alert
```
event: alert
data: {
  "timestamp": 1735000000.0,
  "severity": "warning",
  "metric_name": "system_overall",
  "message": "Anomaly detected"
}
```

#### status
```
event: status
data: {
  "status": "baseline_learning",
  "message": "Learning baseline for 15 minutes"
}
```

#### heartbeat
```
event: heartbeat
data: {"timestamp": 1735000000.0}
```

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": "Error description"
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Bad Request (invalid parameters)
- 404: Not Found
- 500: Internal Server Error
- 503: Service Unavailable (unhealthy)
