/**
 * Dashboard UI logic and API interactions.
 */

// Tab switching
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.dataset.tab;
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('tab-active', 'text-blue-500');
        btn.classList.add('text-gray-400');
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });

    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    activeButton.classList.add('tab-active', 'text-blue-500');
    activeButton.classList.remove('text-gray-400');

    document.getElementById(`tab-${tabName}`).classList.remove('hidden');

    if (tabName === 'history') {
        loadAlertHistory();
    } else if (tabName === 'baseline') {
        loadBaselineStats();
    }
}

// API interactions
async function loadAlertHistory() {
    try {
        const response = await fetch('/api/alerts?limit=20');
        const data = await response.json();

        const container = document.getElementById('alert-history');
        container.innerHTML = '';

        if (data.alerts.length === 0) {
            container.innerHTML = '<p class="text-gray-500">No alerts recorded yet.</p>';
            return;
        }

        data.alerts.forEach(alert => {
            const alertDiv = document.createElement('div');
            alertDiv.className = `p-3 rounded ${getSeverityBg(alert.severity)}`;
            alertDiv.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <span class="font-semibold">${alert.severity.toUpperCase()}</span>
                        <span class="text-sm text-gray-400 ml-2">${new Date(alert.timestamp * 1000).toLocaleString()}</span>
                        <p class="mt-1 text-sm">${alert.message}</p>
                    </div>
                    ${!alert.acknowledged ? `<button onclick="acknowledgeAlert(${alert.id})" class="text-sm px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">Acknowledge</button>` : ''}
                </div>
            `;
            container.appendChild(alertDiv);
        });

    } catch (error) {
        console.error('Failed to load alert history:', error);
    }
}

async function loadBaselineStats() {
    try {
        const response = await fetch('/api/baseline/stats');
        const data = await response.json();

        const container = document.getElementById('baseline-stats');
        container.innerHTML = '';

        const baselines = data.baselines;
        const metricNames = Object.keys(baselines);

        if (metricNames.length === 0) {
            container.innerHTML = '<p class="text-gray-500 col-span-3">No baseline data available. Baseline learning may still be in progress.</p>';
            return;
        }

        metricNames.forEach(metricName => {
            const stats = baselines[metricName];
            const statDiv = document.createElement('div');
            statDiv.className = 'p-4 bg-gray-700 rounded';
            statDiv.innerHTML = `
                <h4 class="font-semibold mb-2">${metricName}</h4>
                <div class="text-sm space-y-1">
                    <div>Mean: <span class="text-blue-400">${stats.mean.toFixed(2)}</span></div>
                    <div>Std Dev: <span class="text-green-400">${stats.std_dev.toFixed(2)}</span></div>
                    <div>Range: <span class="text-yellow-400">${stats.min.toFixed(2)} - ${stats.max.toFixed(2)}</span></div>
                    <div class="text-xs text-gray-400 mt-2">Samples: ${stats.sample_count}</div>
                </div>
            `;
            container.appendChild(statDiv);
        });

    } catch (error) {
        console.error('Failed to load baseline stats:', error);
    }
}

async function retrainBaseline() {
    if (!confirm('Retrain baseline using recent historical data? This will replace the current baseline.')) {
        return;
    }

    try {
        showStatus('Retraining baseline...', 'info');

        const response = await fetch('/api/baseline/train', { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            showStatus('Baseline retrained successfully', 'success');
            loadBaselineStats();
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }

    } catch (error) {
        console.error('Baseline retraining failed:', error);
        showStatus('Baseline retraining failed', 'error');
    }
}

async function triggerAnomaly(type) {
    try {
        showStatus(`Triggering ${type} anomaly...`, 'info');

        const response = await fetch('/api/testing/generate-anomaly', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: type,
                duration: 10,
                intensity: 7
            })
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(`${type} anomaly generation started`, 'success');
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }

    } catch (error) {
        console.error('Anomaly generation failed:', error);
        showStatus('Anomaly generation failed', 'error');
    }
}

async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' });

        if (response.ok) {
            loadAlertHistory();
        }

    } catch (error) {
        console.error('Failed to acknowledge alert:', error);
    }
}

// Periodic status updates
async function updateClientCount() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        const clientCount = data.monitoring?.connected_clients || 0;
        document.getElementById('client-count').textContent = clientCount;

    } catch (error) {
        console.debug('Status update failed:', error);
    }
}

// Update client count every 10 seconds
setInterval(updateClientCount, 10000);
updateClientCount();
