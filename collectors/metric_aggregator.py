"""
Metric aggregation and normalization for ML processing.

Prepares collected metrics for anomaly detection algorithms.
"""

from typing import Dict, List, Any
import numpy as np

from config import get_logger

logger = get_logger(__name__)


class MetricAggregator:
    """
    Aggregates and normalizes metrics for ML processing.

    Handles missing values and prepares feature vectors.
    """

    # Define metric names for consistent ordering
    METRIC_NAMES = [
        'cpu_percent',
        'cpu_freq_mhz',
        'cpu_temperature',
        'memory_used_mb',
        'memory_available_mb',
        'memory_percent',
        'swap_percent',
        'disk_usage_percent',
        'disk_read_bytes_per_sec',
        'disk_write_bytes_per_sec',
        'network_sent_bytes_per_sec',
        'network_recv_bytes_per_sec',
        'network_packets_sent_per_sec',
        'network_packets_recv_per_sec',
        'process_count',
        'thread_count',
        'load_average_1min',
        'load_average_5min',
        'load_average_15min',
        'uptime_seconds'
    ]

    def __init__(self):
        """Initialize the metric aggregator."""
        self.metric_count = len(self.METRIC_NAMES)

    def flatten_metrics(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Flatten nested metrics dictionary into a flat structure.

        Args:
            metrics: Raw metrics from SystemMetricsCollector.

        Returns:
            Flattened metrics dictionary.
        """
        flattened = {}

        for metric_name in self.METRIC_NAMES:
            value = metrics.get(metric_name, 0.0)

            # Handle missing or invalid values
            if value is None or (isinstance(value, float) and np.isnan(value)):
                value = 0.0

            flattened[metric_name] = float(value)

        return flattened

    def to_feature_vector(self, metrics: Dict[str, Any]) -> np.ndarray:
        """
        Convert metrics to a feature vector for ML models.

        Args:
            metrics: Raw or flattened metrics.

        Returns:
            NumPy array of metric values in consistent order.
        """
        flattened = self.flatten_metrics(metrics)
        vector = np.array([flattened[name] for name in self.METRIC_NAMES])

        # Replace any remaining NaN or inf values
        vector = np.nan_to_num(vector, nan=0.0, posinf=0.0, neginf=0.0)

        return vector

    def to_feature_matrix(self, metrics_list: List[Dict[str, Any]]) -> np.ndarray:
        """
        Convert a list of metrics to a feature matrix.

        Args:
            metrics_list: List of raw or flattened metrics.

        Returns:
            2D NumPy array where each row is a feature vector.
        """
        if not metrics_list:
            return np.array([]).reshape(0, self.metric_count)

        matrix = np.array([self.to_feature_vector(m) for m in metrics_list])
        return matrix

    def from_feature_vector(self, vector: np.ndarray) -> Dict[str, float]:
        """
        Convert a feature vector back to a metrics dictionary.

        Args:
            vector: NumPy array of metric values.

        Returns:
            Metrics dictionary.
        """
        if len(vector) != self.metric_count:
            raise ValueError(
                f"Expected vector of length {self.metric_count}, got {len(vector)}"
            )

        return {name: float(vector[i]) for i, name in enumerate(self.METRIC_NAMES)}

    def impute_missing_values(
        self,
        metrics_list: List[Dict[str, Any]],
        strategy: str = 'zero'
    ) -> List[Dict[str, float]]:
        """
        Impute missing values in metrics.

        Args:
            metrics_list: List of metrics dictionaries.
            strategy: Imputation strategy ('zero', 'mean', 'median').

        Returns:
            List of metrics with imputed values.
        """
        if not metrics_list:
            return []

        # Flatten all metrics
        flattened_list = [self.flatten_metrics(m) for m in metrics_list]

        if strategy == 'zero':
            return flattened_list

        # Build matrix for statistical imputation
        matrix = self.to_feature_matrix(flattened_list)

        if strategy == 'mean':
            imputed_matrix = self._impute_mean(matrix)
        elif strategy == 'median':
            imputed_matrix = self._impute_median(matrix)
        else:
            logger.warning(f"Unknown imputation strategy: {strategy}, using zero")
            return flattened_list

        # Convert back to dictionaries
        return [self.from_feature_vector(row) for row in imputed_matrix]

    def _impute_mean(self, matrix: np.ndarray) -> np.ndarray:
        """
        Impute missing values with column means.

        Args:
            matrix: Feature matrix.

        Returns:
            Imputed matrix.
        """
        col_means = np.nanmean(matrix, axis=0)
        col_means = np.nan_to_num(col_means, nan=0.0)

        imputed = matrix.copy()
        for i in range(matrix.shape[1]):
            mask = np.isnan(imputed[:, i]) | np.isinf(imputed[:, i])
            imputed[mask, i] = col_means[i]

        return imputed

    def _impute_median(self, matrix: np.ndarray) -> np.ndarray:
        """
        Impute missing values with column medians.

        Args:
            matrix: Feature matrix.

        Returns:
            Imputed matrix.
        """
        col_medians = np.nanmedian(matrix, axis=0)
        col_medians = np.nan_to_num(col_medians, nan=0.0)

        imputed = matrix.copy()
        for i in range(matrix.shape[1]):
            mask = np.isnan(imputed[:, i]) | np.isinf(imputed[:, i])
            imputed[mask, i] = col_medians[i]

        return imputed

    def normalize_metrics(
        self,
        metrics_list: List[Dict[str, Any]],
        baseline_stats: Dict[str, Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """
        Normalize metrics using baseline statistics.

        Args:
            metrics_list: List of raw metrics.
            baseline_stats: Dictionary mapping metric names to stats (mean, std_dev).

        Returns:
            List of normalized metrics.
        """
        if not metrics_list or not baseline_stats:
            return [self.flatten_metrics(m) for m in metrics_list]

        normalized_list = []

        for metrics in metrics_list:
            flattened = self.flatten_metrics(metrics)
            normalized = {}

            for metric_name, value in flattened.items():
                stats = baseline_stats.get(metric_name, {})
                mean = stats.get('mean', 0.0)
                std_dev = stats.get('std_dev', 1.0)

                if std_dev > 0:
                    normalized[metric_name] = (value - mean) / std_dev
                else:
                    normalized[metric_name] = 0.0

            normalized_list.append(normalized)

        return normalized_list
