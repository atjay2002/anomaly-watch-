/**
 * Chart.js visualization setup and update logic.
 */

const MAX_DATA_POINTS = 60;
const charts = {};

const chartConfig = {
    type: 'line',
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
            legend: { display: true, labels: { color: '#e2e8f0' } }
        },
        scales: {
            x: {
                display: true,
                grid: { color: '#374151' },
                ticks: { color: '#9ca3af' }
            },
            y: {
                display: true,
                grid: { color: '#374151' },
                ticks: { color: '#9ca3af' }
            }
        }
    }
};

function initCharts() {
    const darkTheme = {
        borderColor: 'rgba(59, 130, 246, 0.8)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        pointBackgroundColor: '#3b82f6'
    };

    charts.cpu = new Chart(document.getElementById('chart-cpu'), {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [
                { label: 'CPU %', data: [], ...darkTheme, borderColor: 'rgba(59, 130, 246, 0.8)' },
                { label: 'Temp °C', data: [], ...darkTheme, borderColor: 'rgba(239, 68, 68, 0.8)', backgroundColor: 'rgba(239, 68, 68, 0.1)' }
            ]
        }
    });

    charts.memory = new Chart(document.getElementById('chart-memory'), {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [
                { label: 'Memory %', data: [], ...darkTheme, borderColor: 'rgba(16, 185, 129, 0.8)', backgroundColor: 'rgba(16, 185, 129, 0.1)' },
                { label: 'Swap %', data: [], ...darkTheme, borderColor: 'rgba(245, 158, 11, 0.8)', backgroundColor: 'rgba(245, 158, 11, 0.1)' }
            ]
        }
    });

    charts.disk = new Chart(document.getElementById('chart-disk'), {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [
                { label: 'Read KB/s', data: [], ...darkTheme, borderColor: 'rgba(139, 92, 246, 0.8)' },
                { label: 'Write KB/s', data: [], ...darkTheme, borderColor: 'rgba(236, 72, 153, 0.8)', backgroundColor: 'rgba(236, 72, 153, 0.1)' }
            ]
        }
    });

    charts.network = new Chart(document.getElementById('chart-network'), {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [
                { label: 'Sent KB/s', data: [], ...darkTheme, borderColor: 'rgba(6, 182, 212, 0.8)' },
                { label: 'Recv KB/s', data: [], ...darkTheme, borderColor: 'rgba(251, 146, 60, 0.8)', backgroundColor: 'rgba(251, 146, 60, 0.1)' }
            ]
        }
    });

    charts.anomaly = new Chart(document.getElementById('chart-anomaly'), {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                label: 'Anomaly Score',
                data: [],
                borderColor: 'rgba(239, 68, 68, 0.8)',
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                pointBackgroundColor: '#ef4444',
                fill: true
            }]
        },
        options: {
            ...chartConfig.options,
            scales: {
                ...chartConfig.options.scales,
                y: {
                    ...chartConfig.options.scales.y,
                    min: 0,
                    max: 100,
                    ticks: {
                        ...chartConfig.options.scales.y.ticks,
                        callback: (value) => value + '%'
                    }
                }
            },
            plugins: {
                ...chartConfig.options.plugins,
                annotation: {
                    annotations: {
                        warningLine: {
                            type: 'line',
                            yMin: 30,
                            yMax: 30,
                            borderColor: 'rgba(245, 158, 11, 0.5)',
                            borderWidth: 1,
                            borderDash: [5, 5]
                        },
                        criticalLine: {
                            type: 'line',
                            yMin: 70,
                            yMax: 70,
                            borderColor: 'rgba(239, 68, 68, 0.5)',
                            borderWidth: 1,
                            borderDash: [5, 5]
                        }
                    }
                }
            }
        }
    });
}

function updateCharts(timestamp, metrics, anomalyScore) {
    const timeLabel = new Date(timestamp * 1000).toLocaleTimeString();

    updateChart(charts.cpu, timeLabel, [
        metrics.cpu_percent,
        metrics.cpu_temperature
    ]);

    updateChart(charts.memory, timeLabel, [
        metrics.memory_percent,
        metrics.swap_percent
    ]);

    updateChart(charts.disk, timeLabel, [
        metrics.disk_read_bytes_per_sec / 1024,
        metrics.disk_write_bytes_per_sec / 1024
    ]);

    updateChart(charts.network, timeLabel, [
        metrics.network_sent_bytes_per_sec / 1024,
        metrics.network_recv_bytes_per_sec / 1024
    ]);

    updateChart(charts.anomaly, timeLabel, [anomalyScore]);
}

function updateChart(chart, label, dataValues) {
    chart.data.labels.push(label);

    if (chart.data.labels.length > MAX_DATA_POINTS) {
        chart.data.labels.shift();
    }

    dataValues.forEach((value, i) => {
        if (chart.data.datasets[i]) {
            chart.data.datasets[i].data.push(value);

            if (chart.data.datasets[i].data.length > MAX_DATA_POINTS) {
                chart.data.datasets[i].data.shift();
            }
        }
    });

    chart.update('none');
}

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
});
