"""
Z-score based anomaly detection.

Statistical anomaly detection using standardized scores.
"""

from typing import Dict, Optional
import numpy as np

from config import settings, get_logger

logger = get_logger(__name__)


class ZScoreDetector:
    """
    Z-score based anomaly detector.

    Detects anomalies using statistical deviation from baseline.
    """

    def __init__(self, threshold: float = 3.0):
        """
        Initialize the Z-score detector.

        Args:
            threshold: Number of standard deviations for anomaly threshold.
        """
        self.threshold = threshold
        self.baseline_stats: Optional[Dict[str, Dict[str, float]]] = None
        self.is_trained = False

    def train(self, metrics: Dict[str, np.ndarray]) -> 'ZScoreDetector':
        """
        Train the detector by calculating baseline statistics.

        Args:
            metrics: Dictionary mapping metric names to arrays of values.

        Returns:
            Self for method chaining.
        """
        logger.info(f"Training Z-score detector with {len(metrics)} metrics")

        self.baseline_stats = {}

        for metric_name, values in metrics.items():
            if len(values) == 0:
                logger.warning(f"No values for metric {metric_name}, skipping")
                continue

            try:
                mean = np.mean(values)
                std_dev = np.std(values)
                min_val = np.min(values)
                max_val = np.max(values)

                self.baseline_stats[metric_name] = {
                    'mean': float(mean),
                    'std_dev': float(std_dev),
                    'min': float(min_val),
                    'max': float(max_val),
                    'sample_count': len(values)
                }

            except Exception as e:
                logger.warning(f"Failed to compute stats for {metric_name}: {e}")
                continue

        self.is_trained = True
        logger.info(f"Z-score training completed for {len(self.baseline_stats)} metrics")

        return self

    def predict_anomaly_scores(
        self,
        metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate Z-scores for each metric.

        Args:
            metrics: Dictionary of metric names to current values.

        Returns:
            Dictionary of metric names to anomaly scores [0, 1].
        """
        if not self.is_trained or self.baseline_stats is None:
            logger.warning("Detector not trained, returning default scores")
            return {name: 0.0 for name in metrics.keys()}

        anomaly_scores = {}

        for metric_name, current_value in metrics.items():
            if metric_name not in self.baseline_stats:
                logger.debug(f"No baseline for metric {metric_name}")
                anomaly_scores[metric_name] = 0.0
                continue

            stats = self.baseline_stats[metric_name]
            mean = stats['mean']
            std_dev = stats['std_dev']

            if std_dev == 0:
                anomaly_scores[metric_name] = 0.0
                continue

            try:
                z_score = abs((current_value - mean) / std_dev)

                # Normalize to [0, 1] range
                # z_score of threshold maps to 1.0
                normalized_score = min(z_score / self.threshold, 1.0)
                anomaly_scores[metric_name] = float(normalized_score)

            except Exception as e:
                logger.warning(f"Failed to calculate z-score for {metric_name}: {e}")
                anomaly_scores[metric_name] = 0.0

        return anomaly_scores

    def predict_overall_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate overall anomaly score across all metrics.

        Args:
            metrics: Dictionary of metric names to current values.

        Returns:
            Overall anomaly score in range [0, 1].
        """
        individual_scores = self.predict_anomaly_scores(metrics)

        if not individual_scores:
            return 0.0

        # Use maximum z-score as overall indicator
        max_score = max(individual_scores.values())

        return float(max_score)

    def predict_is_anomaly(
        self,
        metrics: Dict[str, float]
    ) -> Dict[str, bool]:
        """
        Predict binary anomaly labels for each metric.

        Args:
            metrics: Dictionary of metric names to current values.

        Returns:
            Dictionary of metric names to anomaly flags.
        """
        anomaly_scores = self.predict_anomaly_scores(metrics)

        return {
            name: score >= 1.0
            for name, score in anomaly_scores.items()
        }

    def get_baseline_stats(self) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Get baseline statistics.

        Returns:
            Dictionary of baseline stats or None if not trained.
        """
        return self.baseline_stats

    def set_baseline_stats(
        self,
        baseline_stats: Dict[str, Dict[str, float]]
    ) -> 'ZScoreDetector':
        """
        Set baseline statistics (for loading from persistence).

        Args:
            baseline_stats: Dictionary of baseline statistics.

        Returns:
            Self for method chaining.
        """
        self.baseline_stats = baseline_stats
        self.is_trained = True
        logger.info(f"Loaded baseline stats for {len(baseline_stats)} metrics")

        return self

    def get_anomalous_metrics(
        self,
        metrics: Dict[str, float],
        score_threshold: float = 0.5
    ) -> Dict[str, float]:
        """
        Get metrics with anomaly scores above threshold.

        Args:
            metrics: Dictionary of metric names to current values.
            score_threshold: Minimum score to be considered anomalous.

        Returns:
            Dictionary of anomalous metric names to their scores.
        """
        anomaly_scores = self.predict_anomaly_scores(metrics)

        return {
            name: score
            for name, score in anomaly_scores.items()
            if score >= score_threshold
        }

    def update_baseline(
        self,
        metric_name: str,
        new_values: np.ndarray
    ):
        """
        Update baseline statistics for a specific metric (incremental learning).

        Args:
            metric_name: Name of the metric to update.
            new_values: New observations to incorporate.
        """
        if not self.is_trained or self.baseline_stats is None:
            logger.warning("Cannot update untrained detector")
            return

        if metric_name not in self.baseline_stats:
            logger.warning(f"Metric {metric_name} not in baseline, adding it")
            self.baseline_stats[metric_name] = {}

        try:
            old_stats = self.baseline_stats.get(metric_name, {})
            old_mean = old_stats.get('mean', 0.0)
            old_std = old_stats.get('std_dev', 0.0)
            old_count = old_stats.get('sample_count', 0)

            new_count = len(new_values)
            total_count = old_count + new_count

            if total_count == 0:
                return

            # Calculate updated mean
            new_mean = (old_mean * old_count + np.sum(new_values)) / total_count

            # Calculate updated std dev (simplified approach)
            combined_values = np.concatenate([
                np.full(old_count, old_mean),
                new_values
            ])
            new_std = np.std(combined_values)

            self.baseline_stats[metric_name] = {
                'mean': float(new_mean),
                'std_dev': float(new_std),
                'min': float(min(old_stats.get('min', float('inf')), np.min(new_values))),
                'max': float(max(old_stats.get('max', float('-inf')), np.max(new_values))),
                'sample_count': total_count
            }

            logger.info(f"Updated baseline for {metric_name}")

        except Exception as e:
            logger.error(f"Failed to update baseline for {metric_name}: {e}", exc_info=True)
