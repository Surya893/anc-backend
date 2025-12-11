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
        self.noise_classifier_v2 = None
        self._load_model()

    def _load_model(self):
        """Load trained ML model"""
        # Try to load legacy sklearn model
        try:
            model_path = Path(self.config.MODEL_PATH) / self.config.NOISE_CLASSIFIER_MODEL
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"Legacy ML model loaded from {model_path}")
            else:
                logger.warning(f"Legacy ML model not found at {model_path}")
        except Exception as e:
            logger.error(f"Error loading legacy ML model: {e}")
        
        # Try to load v2 deep learning model (lazy)
        try:
            v2_model_path = getattr(self.config, 'ML_MODEL_V2_PATH', 'models/noise_classifier_v2.pth')
            if Path(v2_model_path).exists():
                from src.ml.pipelines.noise_classifier import NoiseClassifierService
                self.noise_classifier_v2 = NoiseClassifierService(model_path=v2_model_path)
                logger.info(f"Noise Classifier V2 loaded from {v2_model_path}")
        except Exception as e:
            logger.warning(f"Noise Classifier V2 not available: {e}")

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

            # Try V2 classifier first (more accurate with 57 classes)
            if self.noise_classifier_v2:
                result = self.noise_classifier_v2.classify(audio, sample_rate=sample_rate)
                return {
                    'noise_type': result['predicted_class'],
                    'confidence': result['confidence'],
                    'all_predictions': result['probabilities'],
                    'top_predictions': dict(result['top_k']),
                    'model_version': 'v2'
                }

            # Fall back to legacy model
            if self.model:
                features = self._extract_features(audio, sample_rate)
                prediction = self.model.predict([features])[0]
                probabilities = self.model.predict_proba([features])[0]
                
                noise_types = ['white', 'pink', 'traffic', 'office', 'construction', 'café']
                all_predictions = {
                    noise_types[i]: float(probabilities[i])
                    for i in range(min(len(noise_types), len(probabilities)))
                }

                return {
                    'noise_type': prediction,
                    'confidence': float(max(probabilities)),
                    'all_predictions': all_predictions,
                    'model_version': 'v1'
                }
            
            # No model available
            return {
                'noise_type': 'unknown',
                'confidence': 0.0,
                'all_predictions': {},
                'model_version': 'none'
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
