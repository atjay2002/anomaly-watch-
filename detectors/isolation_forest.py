"""
Isolation Forest anomaly detection implementation.

Uses scikit-learn's IsolationForest for unsupervised anomaly detection.
"""

from pathlib import Path
from typing import Optional, List
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

from config import settings, get_logger

logger = get_logger(__name__)


class IsolationForestDetector:
    """
    Isolation Forest-based anomaly detector.

    Detects anomalies by isolating outliers in feature space.
    """

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        """
        Initialize the Isolation Forest detector.

        Args:
            contamination: Expected proportion of outliers (0.0 to 0.5).
            random_state: Random seed for reproducibility.
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None
        self.is_trained = False

    def train(self, X: np.ndarray) -> 'IsolationForestDetector':
        """
        Train the Isolation Forest model on baseline data.

        Args:
            X: Training data matrix (n_samples, n_features).

        Returns:
            Self for method chaining.
        """
        if X.shape[0] < 10:
            logger.warning(
                f"Training with only {X.shape[0]} samples. "
                "Consider collecting more baseline data for better accuracy."
            )

        logger.info(
            f"Training Isolation Forest with {X.shape[0]} samples, "
            f"{X.shape[1]} features, contamination={self.contamination}"
        )

        try:
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100,
                max_samples='auto',
                max_features=1.0,
                bootstrap=False,
                n_jobs=-1,
                verbose=0
            )

            self.model.fit(X)
            self.is_trained = True
            logger.info("Isolation Forest training completed successfully")

        except Exception as e:
            logger.error(f"Isolation Forest training failed: {e}", exc_info=True)
            raise

        return self

    def predict_anomaly_score(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomaly scores for input samples.

        Args:
            X: Input data matrix (n_samples, n_features) or (n_features,).

        Returns:
            Anomaly scores in range [0, 1], where higher is more anomalous.
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained, returning default scores")
            if X.ndim == 1:
                return np.array([0.0])
            return np.zeros(X.shape[0])

        try:
            # Ensure 2D input
            if X.ndim == 1:
                X = X.reshape(1, -1)

            # Get anomaly scores (negative, lower is more anomalous)
            raw_scores = self.model.decision_function(X)

            # Normalize to [0, 1] range
            # Scores are typically in range [-0.5, 0.5]
            # Negative scores indicate anomalies
            normalized_scores = np.clip(-raw_scores, 0, 1)

            return normalized_scores

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            if X.ndim == 1:
                return np.array([0.0])
            return np.zeros(X.shape[0])

    def predict_is_anomaly(self, X: np.ndarray) -> np.ndarray:
        """
        Predict binary anomaly labels.

        Args:
            X: Input data matrix (n_samples, n_features) or (n_features,).

        Returns:
            Boolean array where True indicates anomaly.
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained, returning False")
            if X.ndim == 1:
                return np.array([False])
            return np.zeros(X.shape[0], dtype=bool)

        try:
            # Ensure 2D input
            if X.ndim == 1:
                X = X.reshape(1, -1)

            # Predict (-1 for outliers, 1 for inliers)
            predictions = self.model.predict(X)
            return predictions == -1

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            if X.ndim == 1:
                return np.array([False])
            return np.zeros(X.shape[0], dtype=bool)

    def save(self, path: Optional[str] = None) -> str:
        """
        Save the trained model to disk.

        Args:
            path: File path for model. If None, uses default from settings.

        Returns:
            Path where model was saved.
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Cannot save untrained model")

        if path is None:
            path = settings.models.isolation_forest_path

        model_path = Path(path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            joblib.dump(self.model, path)
            logger.info(f"Isolation Forest model saved to {path}")
            return str(path)

        except Exception as e:
            logger.error(f"Failed to save model: {e}", exc_info=True)
            raise

    def load(self, path: Optional[str] = None) -> 'IsolationForestDetector':
        """
        Load a trained model from disk.

        Args:
            path: File path for model. If None, uses default from settings.

        Returns:
            Self for method chaining.
        """
        if path is None:
            path = settings.models.isolation_forest_path

        model_path = Path(path)

        if not model_path.exists():
            logger.warning(f"Model file not found: {path}")
            return self

        try:
            self.model = joblib.load(path)
            self.is_trained = True
            logger.info(f"Isolation Forest model loaded from {path}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise

        return self

    def get_feature_importances(self) -> Optional[np.ndarray]:
        """
        Get feature importance scores (not available for Isolation Forest).

        Returns:
            None (Isolation Forest doesn't provide feature importances).
        """
        logger.info("Isolation Forest does not provide feature importances")
        return None
