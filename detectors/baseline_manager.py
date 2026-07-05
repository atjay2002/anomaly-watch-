"""
Baseline learning and persistence management.

Manages the baseline learning phase and model persistence.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from collectors import MetricAggregator
from detectors.hybrid_scorer import HybridScorer
from database import MetricRepository, BaselineRepository, Baseline, SystemMetadataRepository
from config import settings, get_logger

logger = get_logger(__name__)


class BaselineManager:
    """
    Manages baseline learning and model persistence.

    Coordinates data collection, training, and persistence operations.
    """

    def __init__(self):
        """Initialize the baseline manager."""
        self.aggregator = MetricAggregator()
        self.scorer: Optional[HybridScorer] = None
        self.baseline_start_time: Optional[float] = None
        self.baseline_metrics: List[Dict] = []
        self.is_learning = False

    def start_baseline_learning(self):
        """Start the baseline learning phase."""
        if self.is_learning:
            logger.warning("Baseline learning already in progress")
            return

        self.is_learning = True
        self.baseline_start_time = time.time()
        self.baseline_metrics = []

        duration_minutes = settings.monitoring.baseline_minutes
        logger.info(
            f"Starting baseline learning phase ({duration_minutes} minutes)"
        )

    def add_baseline_sample(self, metrics: Dict):
        """
        Add a sample to the baseline dataset.

        Args:
            metrics: Raw metrics dictionary from collector.
        """
        if not self.is_learning:
            return

        flattened = self.aggregator.flatten_metrics(metrics)
        self.baseline_metrics.append(flattened)

        logger.debug(f"Baseline sample added (total: {len(self.baseline_metrics)})")

    def is_baseline_complete(self) -> bool:
        """
        Check if baseline learning period is complete.

        Returns:
            True if learning period has elapsed.
        """
        if not self.is_learning or self.baseline_start_time is None:
            return False

        elapsed_minutes = (time.time() - self.baseline_start_time) / 60.0
        target_minutes = settings.monitoring.baseline_minutes

        return elapsed_minutes >= target_minutes

    def train_models(self) -> HybridScorer:
        """
        Train anomaly detection models on collected baseline data.

        Returns:
            Trained HybridScorer instance.
        """
        if not self.baseline_metrics:
            raise ValueError("No baseline data collected")

        logger.info(f"Training models on {len(self.baseline_metrics)} baseline samples")

        # Prepare feature matrix for Isolation Forest
        feature_matrix = self.aggregator.to_feature_matrix(self.baseline_metrics)

        # Prepare per-metric arrays for Z-score
        metrics_dict = {}
        for metric_name in self.aggregator.METRIC_NAMES:
            values = [m[metric_name] for m in self.baseline_metrics]
            metrics_dict[metric_name] = np.array(values)

        # Train hybrid scorer
        self.scorer = HybridScorer(
            if_weight=settings.detection.hybrid_if_weight,
            zscore_weight=settings.detection.hybrid_zscore_weight
        )
        self.scorer.train(feature_matrix, metrics_dict)

        logger.info("Model training completed")

        return self.scorer

    def save_baseline(self):
        """Save baseline statistics and models to disk and database."""
        if self.scorer is None:
            raise ValueError("No trained scorer to save")

        logger.info("Saving baseline statistics and models")

        try:
            # Save Isolation Forest model
            self.scorer.save_models()

            # Save baseline statistics to JSON
            baseline_stats = self.scorer.get_baseline_stats()
            if baseline_stats:
                stats_path = Path(settings.models.baseline_stats_path)
                stats_path.parent.mkdir(parents=True, exist_ok=True)

                with open(stats_path, 'w') as f:
                    json.dump(baseline_stats, f, indent=2)

                logger.info(f"Baseline statistics saved to {stats_path}")

                # Also save to database
                for metric_name, stats in baseline_stats.items():
                    baseline = Baseline(
                        metric_name=metric_name,
                        mean=stats['mean'],
                        std_dev=stats['std_dev'],
                        min_value=stats['min'],
                        max_value=stats['max'],
                        p25=stats.get('p25', 0.0),
                        p50=stats.get('p50', 0.0),
                        p75=stats.get('p75', 0.0),
                        p95=stats.get('p95', 0.0),
                        sample_count=stats['sample_count']
                    )
                    BaselineRepository.save_baseline(baseline)

                logger.info("Baseline statistics saved to database")

            # Update system metadata
            SystemMetadataRepository.set_metadata('baseline_trained', 'true')
            SystemMetadataRepository.set_metadata(
                'baseline_trained_at',
                str(time.time())
            )

            logger.info("Baseline save completed successfully")

        except Exception as e:
            logger.error(f"Failed to save baseline: {e}", exc_info=True)
            raise

    def complete_baseline_learning(self) -> HybridScorer:
        """
        Complete the baseline learning phase and train models.

        Returns:
            Trained HybridScorer instance.
        """
        if not self.is_learning:
            raise ValueError("Baseline learning not in progress")

        logger.info("Completing baseline learning phase")

        try:
            # Train models
            scorer = self.train_models()

            # Save baseline
            self.save_baseline()

            # Reset learning state
            self.is_learning = False
            self.baseline_start_time = None
            self.baseline_metrics = []

            logger.info("Baseline learning completed successfully")

            return scorer

        except Exception as e:
            logger.error(f"Baseline learning completion failed: {e}", exc_info=True)
            raise

    def load_baseline(self) -> Optional[HybridScorer]:
        """
        Load baseline statistics and models from disk.

        Returns:
            Loaded HybridScorer instance or None if not found.
        """
        logger.info("Loading baseline from disk")

        try:
            # Check if baseline exists
            if_path = Path(settings.models.isolation_forest_path)
            stats_path = Path(settings.models.baseline_stats_path)

            if not if_path.exists() or not stats_path.exists():
                logger.info("No saved baseline found")
                return None

            # Load baseline statistics
            with open(stats_path, 'r') as f:
                baseline_stats = json.load(f)

            # Create and configure scorer
            self.scorer = HybridScorer(
                if_weight=settings.detection.hybrid_if_weight,
                zscore_weight=settings.detection.hybrid_zscore_weight
            )

            # Load models
            self.scorer.load_models()
            self.scorer.set_baseline_stats(baseline_stats)

            logger.info("Baseline loaded successfully")

            return self.scorer

        except Exception as e:
            logger.error(f"Failed to load baseline: {e}", exc_info=True)
            return None

    def is_baseline_available(self) -> bool:
        """
        Check if a trained baseline is available.

        Returns:
            True if baseline exists and is loaded.
        """
        return self.scorer is not None and self.scorer.is_trained

    def get_baseline_info(self) -> Dict:
        """
        Get information about the current baseline.

        Returns:
            Dictionary with baseline information.
        """
        trained_at = SystemMetadataRepository.get_metadata('baseline_trained_at')

        info = {
            'is_available': self.is_baseline_available(),
            'is_learning': self.is_learning,
            'trained_at': float(trained_at) if trained_at else None,
            'sample_count': len(self.baseline_metrics) if self.is_learning else 0
        }

        if self.is_learning and self.baseline_start_time:
            elapsed = time.time() - self.baseline_start_time
            target = settings.monitoring.baseline_minutes * 60
            info['learning_progress_percent'] = min((elapsed / target) * 100, 100)
            info['learning_time_remaining_seconds'] = max(target - elapsed, 0)

        return info

    def retrain_baseline(self, metrics_window_seconds: int = 900) -> HybridScorer:
        """
        Retrain baseline using recent historical data.

        Args:
            metrics_window_seconds: Time window for historical data (default 15 min).

        Returns:
            Newly trained HybridScorer.
        """
        logger.info(f"Retraining baseline using last {metrics_window_seconds}s of data")

        cutoff_time = time.time() - metrics_window_seconds

        # Collect recent metrics from database
        recent_metrics_data = []
        for metric_name in self.aggregator.METRIC_NAMES:
            metrics = MetricRepository.get_metrics_in_range(
                metric_name,
                cutoff_time,
                time.time()
            )

            for metric in metrics:
                timestamp = metric.timestamp
                # Find or create entry for this timestamp
                entry = next(
                    (m for m in recent_metrics_data if m.get('timestamp') == timestamp),
                    None
                )
                if entry is None:
                    entry = {'timestamp': timestamp}
                    recent_metrics_data.append(entry)

                entry[metric_name] = metric.value

        if not recent_metrics_data:
            raise ValueError("No recent data available for retraining")

        # Fill in missing values
        for entry in recent_metrics_data:
            for metric_name in self.aggregator.METRIC_NAMES:
                if metric_name not in entry:
                    entry[metric_name] = 0.0

        logger.info(f"Collected {len(recent_metrics_data)} samples for retraining")

        # Prepare data and train
        feature_matrix = self.aggregator.to_feature_matrix(recent_metrics_data)

        metrics_dict = {}
        for metric_name in self.aggregator.METRIC_NAMES:
            values = [m.get(metric_name, 0.0) for m in recent_metrics_data]
            metrics_dict[metric_name] = np.array(values)

        self.scorer = HybridScorer(
            if_weight=settings.detection.hybrid_if_weight,
            zscore_weight=settings.detection.hybrid_zscore_weight
        )
        self.scorer.train(feature_matrix, metrics_dict)

        # Save the retrained baseline
        self.save_baseline()

        logger.info("Baseline retraining completed")

        return self.scorer
