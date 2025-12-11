"""
ML Service for Noise Classification
"""

import numpy as np
import base64
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class MLService:
    """Service for ML-based noise classification"""

    def __init__(self):
        """Initialize ML service and load model"""
        from config import get_config
        self.config = get_config()
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load trained ML model"""
        try:
            model_path = Path(self.config.MODEL_PATH) / self.config.NOISE_CLASSIFIER_MODEL
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"ML model loaded from {model_path}")
            else:
                logger.warning(f"ML model not found at {model_path}")
        except Exception as e:
            logger.error(f"Error loading ML model: {e}")

    def classify_noise(self, audio_data, sample_rate=48000):
        """
        Classify noise type

        Args:
            audio_data: Base64-encoded audio
            sample_rate: Sample rate

        Returns:
            dict: Classification results
        """
        try:
            # Decode audio
            audio_bytes = base64.b64decode(audio_data)
            audio = np.frombuffer(audio_bytes, dtype=np.float32)

            # Extract features
            features = self._extract_features(audio, sample_rate)

            # Classify (placeholder if model not loaded)
            if self.model:
                prediction = self.model.predict([features])[0]
                probabilities = self.model.predict_proba([features])[0]
            else:
                prediction = 'unknown'
                probabilities = [0.5, 0.5]

            # Get all predictions
            noise_types = ['white', 'pink', 'traffic', 'office', 'construction', 'café']
            all_predictions = {
                noise_types[i]: float(probabilities[i])
                for i in range(min(len(noise_types), len(probabilities)))
            }

            return {
                'noise_type': prediction,
                'confidence': float(max(probabilities)),
                'all_predictions': all_predictions
            }

        except Exception as e:
            logger.error(f"Error classifying noise: {e}")
            raise

    def detect_emergency(self, audio_data, sample_rate=48000):
        """
        Detect emergency sounds

        Args:
            audio_data: Base64-encoded audio
            sample_rate: Sample rate

        Returns:
            dict: Emergency detection results
        """
        try:
            # Decode audio
            audio_bytes = base64.b64decode(audio_data)
            audio = np.frombuffer(audio_bytes, dtype=np.float32)

            # Extract features
            features = self._extract_features(audio, sample_rate)

            # Detect emergency (placeholder)
            # TODO: Integrate with src/ml/emergency_noise_detector.py
            is_emergency = False
            confidence = 0.0
            emergency_type = None

            return {
                'is_emergency': is_emergency,
                'confidence': confidence,
                'emergency_type': emergency_type
            }

        except Exception as e:
            logger.error(f"Error detecting emergency: {e}")
            raise

    def _extract_features(self, audio, sample_rate):
        """Extract audio features for ML"""
        # Placeholder - integrate with src/ml/feature_extraction.py
        features = []

        # RMS energy
        rms = np.sqrt(np.mean(audio**2))
        features.append(rms)

        # Zero crossing rate
        zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        features.append(zcr)

        # Spectral features (placeholder)
        features.extend([0.0] * 10)

        return np.array(features)
