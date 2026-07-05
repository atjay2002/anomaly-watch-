"""
System metrics collection using psutil.

Collects CPU, memory, disk, network, and process metrics from the system.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional

import psutil

from config import get_logger

logger = get_logger(__name__)


class SystemMetricsCollector:
    """
    Collects system metrics using psutil.

    Handles partial failures gracefully to ensure continuous monitoring.
    """

    def __init__(self):
        """Initialize the metrics collector."""
        self._last_disk_io = None
        self._last_network_io = None
        self._last_collection_time = None

    def collect_all(self) -> Dict[str, Any]:
        """
        Collect all system metrics.

        Returns:
            Dictionary containing all collected metrics with timestamp.
        """
        current_time = time.time()
        metrics = {'timestamp': current_time}

        # Collect each metric category with individual error handling
        metrics.update(self._collect_cpu())
        metrics.update(self._collect_memory())
        metrics.update(self._collect_disk())
        metrics.update(self._collect_network())
        metrics.update(self._collect_processes())
        metrics.update(self._collect_system())

        self._last_collection_time = current_time
        return metrics

    def _collect_cpu(self) -> Dict[str, float]:
        """
        Collect CPU metrics.

        Returns:
            Dictionary with CPU metrics.
        """
        metrics = {}

        try:
            metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to collect CPU percent: {e}")
            metrics['cpu_percent'] = 0.0

        try:
            cpu_freq = psutil.cpu_freq()
            metrics['cpu_freq_mhz'] = cpu_freq.current if cpu_freq else 0.0
        except Exception as e:
            logger.warning(f"Failed to collect CPU frequency: {e}")
            metrics['cpu_freq_mhz'] = 0.0

        try:
            metrics['cpu_temperature'] = self._get_cpu_temperature()
        except Exception as e:
            logger.warning(f"Failed to collect CPU temperature: {e}")
            metrics['cpu_temperature'] = 0.0

        return metrics

    def _get_cpu_temperature(self) -> float:
        """
        Get CPU temperature from thermal zone (Linux-specific).

        Returns:
            Temperature in Celsius, or 0.0 if unavailable.
        """
        try:
            # Try psutil sensors_temperatures first
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try common sensor names
                    for sensor_name in ['coretemp', 'cpu_thermal', 'k10temp', 'zenpower']:
                        if sensor_name in temps and temps[sensor_name]:
                            return temps[sensor_name][0].current

            # Fallback: read from /sys/class/thermal
            thermal_zones = list(Path('/sys/class/thermal').glob('thermal_zone*/temp'))
            if thermal_zones:
                with open(thermal_zones[0], 'r') as f:
                    # Temperature is in millidegrees Celsius
                    return float(f.read().strip()) / 1000.0
        except Exception as e:
            logger.debug(f"Temperature reading failed: {e}")

        return 0.0

    def _collect_memory(self) -> Dict[str, float]:
        """
        Collect memory metrics.

        Returns:
            Dictionary with memory metrics.
        """
        metrics = {}

        try:
            mem = psutil.virtual_memory()
            metrics['memory_used_mb'] = mem.used / (1024 * 1024)
            metrics['memory_available_mb'] = mem.available / (1024 * 1024)
            metrics['memory_percent'] = mem.percent
        except Exception as e:
            logger.warning(f"Failed to collect memory metrics: {e}")
            metrics['memory_used_mb'] = 0.0
            metrics['memory_available_mb'] = 0.0
            metrics['memory_percent'] = 0.0

        try:
            swap = psutil.swap_memory()
            metrics['swap_percent'] = swap.percent
        except Exception as e:
            logger.warning(f"Failed to collect swap metrics: {e}")
            metrics['swap_percent'] = 0.0

        return metrics

    def _collect_disk(self) -> Dict[str, float]:
        """
        Collect disk metrics.

        Returns:
            Dictionary with disk metrics.
        """
        metrics = {}

        try:
            disk_usage = psutil.disk_usage('/')
            metrics['disk_usage_percent'] = disk_usage.percent
        except Exception as e:
            logger.warning(f"Failed to collect disk usage: {e}")
            metrics['disk_usage_percent'] = 0.0

        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                current_read = disk_io.read_bytes
                current_write = disk_io.write_bytes

                if self._last_disk_io and self._last_collection_time:
                    time_delta = time.time() - self._last_collection_time
                    if time_delta > 0:
                        metrics['disk_read_bytes_per_sec'] = (
                            current_read - self._last_disk_io[0]
                        ) / time_delta
                        metrics['disk_write_bytes_per_sec'] = (
                            current_write - self._last_disk_io[1]
                        ) / time_delta
                    else:
                        metrics['disk_read_bytes_per_sec'] = 0.0
                        metrics['disk_write_bytes_per_sec'] = 0.0
                else:
                    metrics['disk_read_bytes_per_sec'] = 0.0
                    metrics['disk_write_bytes_per_sec'] = 0.0

                self._last_disk_io = (current_read, current_write)
            else:
                metrics['disk_read_bytes_per_sec'] = 0.0
                metrics['disk_write_bytes_per_sec'] = 0.0
        except Exception as e:
            logger.warning(f"Failed to collect disk I/O: {e}")
            metrics['disk_read_bytes_per_sec'] = 0.0
            metrics['disk_write_bytes_per_sec'] = 0.0

        return metrics

    def _collect_network(self) -> Dict[str, float]:
        """
        Collect network metrics.

        Returns:
            Dictionary with network metrics.
        """
        metrics = {}

        try:
            net_io = psutil.net_io_counters()
            if net_io:
                current_sent = net_io.bytes_sent
                current_recv = net_io.bytes_recv
                current_packets_sent = net_io.packets_sent
                current_packets_recv = net_io.packets_recv

                if self._last_network_io and self._last_collection_time:
                    time_delta = time.time() - self._last_collection_time
                    if time_delta > 0:
                        metrics['network_sent_bytes_per_sec'] = (
                            current_sent - self._last_network_io[0]
                        ) / time_delta
                        metrics['network_recv_bytes_per_sec'] = (
                            current_recv - self._last_network_io[1]
                        ) / time_delta
                        metrics['network_packets_sent_per_sec'] = (
                            current_packets_sent - self._last_network_io[2]
                        ) / time_delta
                        metrics['network_packets_recv_per_sec'] = (
                            current_packets_recv - self._last_network_io[3]
                        ) / time_delta
                    else:
                        metrics['network_sent_bytes_per_sec'] = 0.0
                        metrics['network_recv_bytes_per_sec'] = 0.0
                        metrics['network_packets_sent_per_sec'] = 0.0
                        metrics['network_packets_recv_per_sec'] = 0.0
                else:
                    metrics['network_sent_bytes_per_sec'] = 0.0
                    metrics['network_recv_bytes_per_sec'] = 0.0
                    metrics['network_packets_sent_per_sec'] = 0.0
                    metrics['network_packets_recv_per_sec'] = 0.0

                self._last_network_io = (
                    current_sent, current_recv,
                    current_packets_sent, current_packets_recv
                )
            else:
                metrics['network_sent_bytes_per_sec'] = 0.0
                metrics['network_recv_bytes_per_sec'] = 0.0
                metrics['network_packets_sent_per_sec'] = 0.0
                metrics['network_packets_recv_per_sec'] = 0.0
        except Exception as e:
            logger.warning(f"Failed to collect network metrics: {e}")
            metrics['network_sent_bytes_per_sec'] = 0.0
            metrics['network_recv_bytes_per_sec'] = 0.0
            metrics['network_packets_sent_per_sec'] = 0.0
            metrics['network_packets_recv_per_sec'] = 0.0

        return metrics

    def _collect_processes(self) -> Dict[str, int]:
        """
        Collect process and thread metrics.

        Returns:
            Dictionary with process metrics.
        """
        metrics = {}

        try:
            pids = psutil.pids()
            metrics['process_count'] = len(pids)

            thread_count = 0
            for pid in pids:
                try:
                    proc = psutil.Process(pid)
                    thread_count += proc.num_threads()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            metrics['thread_count'] = thread_count
        except Exception as e:
            logger.warning(f"Failed to collect process metrics: {e}")
            metrics['process_count'] = 0
            metrics['thread_count'] = 0

        return metrics

    def _collect_system(self) -> Dict[str, float]:
        """
        Collect system-wide metrics.

        Returns:
            Dictionary with system metrics.
        """
        metrics = {}

        try:
            load_avg = psutil.getloadavg()
            metrics['load_average_1min'] = load_avg[0]
            metrics['load_average_5min'] = load_avg[1]
            metrics['load_average_15min'] = load_avg[2]
        except Exception as e:
            logger.warning(f"Failed to collect load average: {e}")
            metrics['load_average_1min'] = 0.0
            metrics['load_average_5min'] = 0.0
            metrics['load_average_15min'] = 0.0

        try:
            metrics['uptime_seconds'] = time.time() - psutil.boot_time()
        except Exception as e:
            logger.warning(f"Failed to collect uptime: {e}")
            metrics['uptime_seconds'] = 0.0

        return metrics
