-- AnomalyWatch Database Schema
-- SQLite schema for metrics, baselines, and alerts

-- Metrics table: stores all collected system metrics with anomaly scores
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    anomaly_score REAL DEFAULT 0.0,
    is_anomaly INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient time-based queries
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC);

-- Index for metric-specific queries
CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, timestamp DESC);

-- Index for anomaly queries
CREATE INDEX IF NOT EXISTS idx_metrics_anomaly ON metrics(is_anomaly, timestamp DESC);


-- Baselines table: stores statistical baselines for each metric
CREATE TABLE IF NOT EXISTS baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT UNIQUE NOT NULL,
    mean REAL,
    std_dev REAL,
    min_value REAL,
    max_value REAL,
    p25 REAL,
    p50 REAL,
    p75 REAL,
    p95 REAL,
    sample_count INTEGER,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for baseline lookups
CREATE INDEX IF NOT EXISTS idx_baselines_name ON baselines(metric_name);


-- Alerts table: stores alert history
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    severity TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    anomaly_score REAL,
    message TEXT NOT NULL,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for active alerts
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged, timestamp DESC);

-- Index for severity queries
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity, timestamp DESC);


-- System metadata table: stores application state
CREATE TABLE IF NOT EXISTS system_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial metadata
INSERT OR IGNORE INTO system_metadata (key, value) VALUES
    ('schema_version', '1.0'),
    ('baseline_trained', 'false'),
    ('baseline_trained_at', NULL);
