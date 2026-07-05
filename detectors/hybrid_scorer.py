"""
Hybrid anomaly scoring combining Isolation Forest and Z-score methods.

Provides unified anomaly scoring and severity classification.
"""

from typing import Dict, Tuple, Optional
import numpy as np

from detectors.isolation_forest import IsolationForestDetector
from detectors.zscore import ZScoreDetector
from config import settings, get_logger

logger = get_logger(__name__)


class HybridScorer:
    """
    Hybrid anomaly scorer combining multiple detection methods.

    Combines Isolation Forest (unsupervised) and Z-score (statistical) approaches.
    """

    def __init__(
        self,
        if_weight: float = 0.6,
        zscore_weight: float = 0.4
    ):
        """
        Initialize the hybrid scorer.

        Args:
            if_weight: Weight for Isolation Forest score.
            zscore_weight: Weight for Z-score.
        """
        self.if_weight = if_weight
        self.zscore_weight = zscore_weight

        # Normalize weights
        total_weight = if_weight + zscore_weight
        self.if_weight = if_weight / total_weight
        self.zscore_weight = zscore_weight / total_weight

        self.if_detector = IsolationForestDetector(
            contamination=settings.detection.isolation_forest_contamination
        )
        self.zscore_detector = ZScoreDetector(
            threshold=settings.detection.zscore_threshold
        )

        self.is_trained = False

    def train(
        self,
        feature_matrix: np.ndarray,
        metrics_dict: Dict[str, np.ndarray]
    ) -> 'HybridScorer':
        """
        Train both detectors on baseline data.

        Args:
            feature_matrix: Feature matrix for Isolation Forest (n_samples, n_features).
            metrics_dict: Dictionary mapping metric names to value arrays for Z-score.

        Returns:
            Self for method chaining.
        """
        logger.info("Training hybrid scorer")

        try:
            # Train Isolation Forest
            self.if_detector.train(feature_matrix)

            # Train Z-score detector
            self.zscore_detector.train(metrics_dict)

            self.is_trained = True
            logger.info("Hybrid scorer training completed")

        except Exception as e:
            logger.error(f"Hybrid scorer training failed: {e}", exc_info=True)
            raise

        return self

    def predict_anomaly_score(
        self,
        feature_vector: np.ndarray,
        metrics: Dict[str, float]
    ) -> float:
        """
        Calculate hybrid anomaly score.

        Args:
            feature_vector: Feature vector for Isolation Forest.
            metrics: Dictionary of metric values for Z-score.

        Returns:
            Anomaly score in range [0, 100].
        """
        if not self.is_trained:
            logger.warning("Scorer not trained, returning default score")
            return 0.0

        try:
            # Get Isolation Forest score [0, 1]
            if_score = self.if_detector.predict_anomaly_score(feature_vector)
            if isinstance(if_score, np.ndarray):
                if_score = if_score[0]

            # Get Z-score overall score [0, 1]
            zscore_score = self.zscore_detector.predict_overall_score(metrics)

            # Calculate weighted hybrid score [0, 1]
            hybrid_score = (
                self.if_weight * if_score +
                self.zscore_weight * zscore_score
            )

            # Scale to [0, 100]
            final_score = hybrid_score * 100.0

            return float(np.clip(final_score, 0.0, 100.0))

        except Exception as e:
            logger.error(f"Anomaly score prediction failed: {e}", exc_info=True)
            return 0.0

    def predict_severity(
        self,
        feature_vector: np.ndarray,
        metrics: Dict[str, float]
    ) -> str:
        """
        Predict severity level based on anomaly score.

        Args:
            feature_vector: Feature vector for Isolation Forest.
            metrics: Dictionary of metric values for Z-score.

        Returns:
            Severity level: 'normal', 'warning', or 'critical'.
        """
        score = self.predict_anomaly_score(feature_vector, metrics)

        if score >= settings.detection.severity_critical_threshold:
            return 'critical'
        elif score >= settings.detection.severity_warning_threshold:
            return 'warning'
        else:
            return 'normal'

    def predict_with_details(
        self,
        feature_vector: np.ndarray,
        metrics: Dict[str, float]
    ) -> Dict[str, any]:
        """
        Predict anomaly with detailed breakdown.

        Args:
            feature_vector: Feature vector for Isolation Forest.
            metrics: Dictionary of metric values for Z-score.

        Returns:
            Dictionary with detailed prediction results.
        """
        if not self.is_trained:
            return {
                'score': 0.0,
                'severity': 'normal',
                'is_anomaly': False,
                'if_score': 0.0,
                'zscore_overall': 0.0,
                'zscore_per_metric': {},
                'anomalous_metrics': []
            }

        try:
            # Get individual scores
            if_score = self.if_detector.predict_anomaly_score(feature_vector)
            if isinstance(if_score, np.ndarray):
                if_score = if_score[0]

            zscore_overall = self.zscore_detector.predict_overall_score(metrics)
            zscore_per_metric = self.zscore_detector.predict_anomaly_scores(metrics)

            # Calculate hybrid score
            hybrid_score = self.predict_anomaly_score(feature_vector, metrics)
            severity = self.predict_severity(feature_vector, metrics)

            # Identify anomalous metrics
            anomalous_metrics = [
                {'name': name, 'score': score}
                for name, score in zscore_per_metric.items()
                if score >= 0.5
            ]
            anomalous_metrics.sort(key=lambda x: x['score'], reverse=True)

            return {
                'score': float(hybrid_score),
                'severity': severity,
                'is_anomaly': severity != 'normal',
                'if_score': float(if_score) * 100.0,
                'zscore_overall': float(zscore_overall) * 100.0,
                'zscore_per_metric': {k: float(v) * 100.0 for k, v in zscore_per_metric.items()},
                'anomalous_metrics': anomalous_metrics
            }

        except Exception as e:
            logger.error(f"Detailed prediction failed: {e}", exc_info=True)
            return {
                'score': 0.0,
                'severity': 'normal',
                'is_anomaly': False,
                'if_score': 0.0,
                'zscore_overall': 0.0,
                'zscore_per_metric': {},
                'anomalous_metrics': []
            }

    def save_models(self):
        """Save both models to disk."""
        if not self.is_trained:
            logger.warning("Cannot save untrained models")
            return

        try:
            self.if_detector.save()
            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Failed to save models: {e}", exc_info=True)

    def load_models(self) -> 'HybridScorer':
        """
        Load both models from disk.

        Returns:
            Self for method chaining.
        """
        try:
            self.if_detector.load()
            self.is_trained = self.if_detector.is_trained
            logger.info("Models loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load models: {e}", exc_info=True)

        return self

    def get_baseline_stats(self) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Get Z-score baseline statistics.

        Returns:
            Baseline statistics dictionary or None.
        """
        return self.zscore_detector.get_baseline_stats()

    def set_baseline_stats(
        self,
        baseline_stats: Dict[str, Dict[str, float]]
    ) -> 'HybridScorer':
        """
        Set Z-score baseline statistics.

        Args:
            baseline_stats: Baseline statistics dictionary.

        Returns:
            Self for method chaining.
        """
        self.zscore_detector.set_baseline_stats(baseline_stats)
        return self
