/**
 * SSE Client for real-time updates.
 */

let eventSource = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }

    console.log('Connecting to SSE stream...');

    eventSource = new EventSource('/stream/metrics');

    eventSource.addEventListener('connected', (e) => {
        const data = JSON.parse(e.data);
        console.log('SSE connected:', data.client_id);
        reconnectAttempts = 0;
        showStatus('Connected to real-time stream', 'success');
    });

    eventSource.addEventListener('metric', (e) => {
        const data = JSON.parse(e.data);
        handleMetricUpdate(data);
    });

    eventSource.addEventListener('anomaly', (e) => {
        const data = JSON.parse(e.data);
        handleAnomalyDetected(data);
    });

    eventSource.addEventListener('alert', (e) => {
        const data = JSON.parse(e.data);
        handleAlert(data);
    });

    eventSource.addEventListener('status', (e) => {
        const data = JSON.parse(e.data);
        handleStatusUpdate(data);
    });

    eventSource.addEventListener('heartbeat', (e) => {
        console.debug('Heartbeat received');
    });

    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        eventSource.close();

        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
            showStatus(`Connection lost, reconnecting...`, 'warning');
            setTimeout(connectSSE, delay);
        } else {
            showStatus('Connection failed. Please refresh the page.', 'error');
        }
    };
}

function handleMetricUpdate(data) {
    updateCharts(data.timestamp, data.metrics, data.anomaly_score);
    updateSystemStatus(data.anomaly_score);
}

function handleAnomalyDetected(data) {
    console.warn('Anomaly detected:', data);

    const severity = data.severity;
    const score = data.score.toFixed(1);
    const metrics = data.anomalous_metrics.slice(0, 3).map(m => m.name).join(', ');

    showAlert(
        `${severity.toUpperCase()} Anomaly`,
        `Score: ${score} | Metrics: ${metrics}`,
        severity
    );
}

function handleAlert(data) {
    showAlert(
        data.severity.toUpperCase(),
        data.message,
        data.severity
    );
}

function handleStatusUpdate(data) {
    showStatus(data.message, 'info');

    if (data.status === 'baseline_learning') {
        document.getElementById('status-bar').classList.remove('hidden');
    } else if (data.status === 'baseline_complete') {
        document.getElementById('status-bar').classList.add('hidden');
    }
}

function updateSystemStatus(anomalyScore) {
    const statusEl = document.getElementById('system-status');

    if (anomalyScore >= 70) {
        statusEl.innerHTML = '<span class="severity-critical">● CRITICAL ANOMALY</span>';
    } else if (anomalyScore >= 30) {
        statusEl.innerHTML = '<span class="severity-warning">● Warning</span>';
    } else {
        statusEl.innerHTML = '<span class="severity-normal">● System Healthy</span>';
    }
}

function showAlert(title, message, severity) {
    const panel = document.getElementById('alert-panel');

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert-card p-4 rounded-lg shadow-lg ${getSeverityBg(severity)}`;
    alertDiv.innerHTML = `
        <div class="flex justify-between items-start">
            <div>
                <h4 class="font-bold">${title}</h4>
                <p class="text-sm mt-1">${message}</p>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" class="text-gray-300 hover:text-white">×</button>
        </div>
    `;

    panel.insertBefore(alertDiv, panel.firstChild);

    setTimeout(() => alertDiv.remove(), 10000);
}

function showStatus(message, type) {
    const statusBar = document.getElementById('status-bar');
    const statusMessage = document.getElementById('status-message');

    statusMessage.textContent = message;
    statusBar.classList.remove('hidden');

    if (type === 'success') {
        setTimeout(() => statusBar.classList.add('hidden'), 3000);
    }
}

function getSeverityBg(severity) {
    const map = {
        'critical': 'bg-red-900 border-l-4 border-red-500',
        'warning': 'bg-yellow-900 border-l-4 border-yellow-500',
        'normal': 'bg-green-900 border-l-4 border-green-500',
        'info': 'bg-blue-900 border-l-4 border-blue-500'
    };
    return map[severity] || map['info'];
}

// Connect on page load
document.addEventListener('DOMContentLoaded', () => {
    connectSSE();
});
