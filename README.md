# AnomalyWatch

## Real-Time System Anomaly Detection Platform for Edge Devices

AnomalyWatch is a real-time system anomaly detection platform designed for edge and embedded Linux devices. It continuously monitors system resources, learns normal operating behavior using machine learning and statistical analysis, and automatically detects abnormal conditions through live anomaly scoring and alerting.

Built with Python and Flask, the platform combines real-time monitoring, anomaly detection, historical analytics, and automated testing in a lightweight dashboard optimized for resource-constrained edge hardware.

---

## Screenshots

### Live Monitoring Dashboard

screenshots/live-dashboard.png

Real-time monitoring of CPU, memory, disk I/O, network traffic, temperature, and anomaly score from a unified dashboard.

### Anomaly Detection & Alerts

screenshots/anomaly-alerts.png

Instant anomaly detection with live scoring, warning notifications, and alert tracking.

### Testing & Baseline Analysis

screenshots/testing-dashboard.png

Built-in anomaly generators and baseline learning for validating detection behavior.

---

## Highlights

✅ Real-time anomaly detection

✅ Isolation Forest + Statistical Analysis

✅ Live Dashboard with SSE Streaming

✅ SQLite-Based Historical Analytics

✅ Desktop & GPIO Alerting

✅ Built-in Anomaly Testing Framework

✅ Edge Device Optimized

✅ Fully Offline Operation

✅ Zero Cloud Dependency

---

## Features

### Machine Learning-Based Detection

- Hybrid anomaly detection using Isolation Forest and Z-score analysis
- Automatic baseline learning and normalization
- 0-100 anomaly scoring
- Configurable warning and critical thresholds
- Model persistence across restarts

### Real-Time Monitoring

- 5-second metric collection interval
- CPU utilization monitoring
- Memory and swap tracking
- Disk I/O statistics
- Network traffic monitoring
- Temperature monitoring
- Process and thread analysis
- System load average tracking

### Dashboard & Analytics

- Dark-themed responsive dashboard
- Live Chart.js visualizations
- Anomaly score trends
- Baseline statistics viewer
- Historical anomaly tracking
- Anomaly overlays on charts

### Alerting

- Live dashboard notifications
- Desktop notifications using Plyer
- SQLite alert logging
- Optional GPIO LEDs and buzzer support
- Alert acknowledgement workflow

### Testing & Validation

- CPU spike generator
- Memory spike generator
- Disk I/O workload generator
- Network activity generator
- Thread spike generator
- Demo mode for validation

---

## Technology Stack

### Backend

- Python
- Flask
- SQLite
- psutil
- Scikit-learn

### Frontend

- TailwindCSS
- Chart.js
- JavaScript

### Machine Learning

- Isolation Forest
- Z-Score Statistical Analysis

### Real-Time Communication

- Server-Sent Events (SSE)

### Hardware Support

- Ubuntu Linux
- ARM64 Edge Devices
- Rubik Pi 3
- Raspberry Pi

---

## Use Cases

- Edge Device Health Monitoring
- Embedded Linux Diagnostics
- System Performance Analysis
- Resource Anomaly Detection
- AI Workload Monitoring
- Industrial IoT Monitoring
- Preventive Maintenance
- Infrastructure Health Monitoring

---

## Quick Start

### Clone Repository

```bash
git clone https://github.com/<your-username>/AnomalyWatch.git
cd AnomalyWatch
```

### Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

### Open Dashboard

```text
http://localhost:5000
```

The system will automatically begin collecting baseline data before switching to anomaly detection mode.

---

## Dashboard Overview

### Live Monitoring

- CPU Metrics
- Memory Usage
- Disk I/O
- Network Traffic
- Anomaly Score
- Live Alert Feed

### History

- Alert History
- Anomaly Events
- Score Analysis

### Baseline

- Learned Normal Behavior
- Metric Statistics
- Detection Thresholds

### Testing

- Generate Synthetic Anomalies
- Validate Detection Logic
- Benchmark System Response

### Settings

- Current Configuration
- Detection Parameters
- Alert Settings

---

## REST API

### Metrics

```http
GET /api/metrics/latest
```

```http
GET /api/metrics/history?metric=cpu_percent&duration=300
```

### Baseline

```http
GET /api/baseline/stats
```

```http
POST /api/baseline/train
```

### Alerts

```http
GET /api/alerts
```

```http
POST /api/alerts/{id}/acknowledge
```

### System

```http
GET /api/system/status
```

### Testing

```http
POST /api/testing/generate-anomaly
```

---

## SSE Event Streaming

Real-time updates are delivered through Server-Sent Events.

```http
GET /stream/metrics
```

Supported event types:

- metric
- anomaly
- alert
- status
- heartbeat

---

## Architecture

```text
┌─────────────────┐
│   Web Dashboard │
│ TailwindCSS     │
│ Chart.js        │
└────────┬────────┘
         │
         │ REST API + SSE
         ▼
┌─────────────────┐
│ Flask Backend   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Monitoring Core │
├─────────────────┤
│ Metric Collector│
│ Baseline Engine │
│ Alert Service   │
│ SSE Service     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Detection Engine│
├─────────────────┤
│ IsolationForest │
│ Z-Score Analysis│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SQLite Storage  │
└─────────────────┘
```

---

## Project Structure

```text
AnomalyWatch/
│
├── app.py
├── requirements.txt
├── anomalywatch.db
│
├── collectors/
├── detectors/
├── services/
├── routes/
├── database/
├── config/
├── testing/
├── gpio/
│
├── templates/
├── static/
├── screenshots/
├── docs/
└── deploy/
```

---

## Testing Anomaly Detection

### CPU Spike

```bash
curl -X POST http://localhost:5000/api/testing/generate-anomaly \
-H "Content-Type: application/json" \
-d '{"type":"cpu","duration":10,"intensity":7}'
```

### Memory Spike

```bash
curl -X POST http://localhost:5000/api/testing/generate-anomaly \
-H "Content-Type: application/json" \
-d '{"type":"memory","duration":15,"intensity":5}'
```

### Supported Anomaly Types

- cpu
- memory
- disk
- network
- thread

---

## Raspberry Pi / GPIO Support

Optional hardware alerting is supported through GPIO outputs.

### Supported Outputs

- Green LED (Normal)
- Yellow LED (Warning)
- Red LED (Critical)
- Buzzer (Critical)

### GPIO Mapping

| Component | GPIO Pin |
|------------|-----------|
| Green LED | GPIO 17 |
| Yellow LED | GPIO 27 |
| Red LED | GPIO 22 |
| Buzzer | GPIO 23 |

---

## Performance

Typical resource consumption:

| Resource | Usage |
|-----------|---------|
| CPU | 2-5% |
| Memory | 150-300 MB |
| Database Growth | ~1 MB/hour |
| Monitoring Interval | 5 seconds |

### Tested Capacity

- 10+ concurrent dashboard clients
- Millions of stored metric records
- Fully local deployment

---

## Future Enhancements

- Multi-device monitoring
- Prometheus integration
- Grafana export
- WebSocket support
- Model retraining automation
- Docker deployment

---

## Resume Summary

Built a real-time anomaly detection platform using Isolation Forest, Flask, SQLite, and psutil for monitoring CPU, memory, disk, network, and thermal metrics on edge Linux systems with automated anomaly scoring and alerting.

---

## License

MIT License

---

## Author

**Manikandan M**

GitHub: https://github.com/atjay2002

LinkedIn: https://www.linkedin.com/in/mani2002

---

## Star the Repository

If you find this project useful, consider giving it a ⭐ on GitHub.
