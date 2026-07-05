# AnomalyWatch Architecture

## System Overview

AnomalyWatch is a modular, event-driven system monitoring platform with real-time anomaly detection capabilities.

## Core Components

### 1. Data Collection Layer
- **SystemMetricsCollector**: psutil-based metric collection
- **MetricAggregator**: Normalization and feature engineering
- Collects 20+ metrics every 5 seconds with graceful degradation on partial failures

### 2. Detection Layer
- **IsolationForestDetector**: Unsupervised anomaly detection
- **ZScoreDetector**: Statistical outlier detection  
- **HybridScorer**: Weighted ensemble (60% IF, 40% Z-score)
- **BaselineManager**: Training orchestration and persistence

### 3. Services Layer
- **MonitoringService**: Core orchestration loop
- **AlertService**: Multi-channel alert routing (desktop, GPIO)
- **SSEService**: Real-time event broadcasting

### 4. API Layer
- **Flask Application**: REST API + SSE endpoints
- **Blueprints**: dashboard, api, stream
- JSON serialization with proper error handling

### 5. Presentation Layer
- **Dashboard**: Single-page app with 5 tabs
- **Chart.js**: Real-time visualizations
- **SSE Client**: Automatic reconnection logic

## Data Flow

```
Metrics Collection (5s) → Baseline Learning (15min)
                              ↓
                         ML Training
                              ↓
Real-time Monitoring → Feature Extraction → Anomaly Scoring
                              ↓
                    Severity Classification
                              ↓
         ├─────────────┬──────────────┬──────────────┐
         ↓             ↓              ↓              ↓
    Database      SSE Stream     Alerts          GPIO
```

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Flask 3.0, Python 3.10+ |
| ML | scikit-learn, NumPy |
| Monitoring | psutil |
| Database | SQLite3 |
| Frontend | Tailwind CSS, Chart.js |
| Notifications | plyer, RPi.GPIO |

## Design Decisions

### SQLite vs TimeSeries DB
**Choice**: SQLite  
**Rationale**: Local deployment, no external dependencies, adequate performance for 5s intervals  
**Trade-off**: Not suitable for sub-second monitoring at massive scale

### Synchronous Flask
**Choice**: Sync Flask with background thread  
**Rationale**: Simpler implementation, SSE works well synchronously  
**Trade-off**: Limited concurrent connections (acceptable for local dashboard)

### Hybrid Detection
**Choice**: Isolation Forest + Z-score ensemble  
**Rationale**: IF catches complex patterns, Z-score catches simple outliers  
**Trade-off**: Slightly higher computation cost

### Persistent Baseline
**Choice**: JSON + pickle persistence  
**Rationale**: Preserve learning across restarts  
**Trade-off**: Versioning complexity if metric schema changes

## Security Considerations

- No authentication (local-only deployment assumed)
- Input validation on all API endpoints
- Parameterized SQL queries (injection prevention)
- Template escaping (XSS prevention)
- No shell=True in subprocess calls
- Rate limiting recommended for production deployments

## Scalability

**Current Design Supports**:
- 1-10 concurrent dashboard clients
- 5s monitoring interval minimum
- 7-day data retention default
- 20+ concurrent metrics

**Future Improvements**:
- Async Flask with aiohttp for >100 concurrent clients
- InfluxDB for high-frequency time-series data
- Redis for distributed caching
- gRPC for high-performance metric ingestion
