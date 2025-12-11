"""
Model training tasks for Celery
Handles noise classifier training and model management
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import joblib
import librosa

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config import get_config
from ml.feature_extraction import AudioFeatureExtractor
from celery_app import celery_app

from .utils import task_logger, handle_task_error

logger = logging.getLogger(__name__)
config = get_config()


@celery_app.task(name='tasks.train_noise_classifier')
@task_logger
def train_noise_classifier(training_data_dir: str) -> Dict[str, Any]:
    """
    Train or retrain the noise classification model
    Uses improved feature extraction and model persistence

    Args:
        training_data_dir: Directory containing training audio files
                          Expected structure: training_data_dir/category_name/*.wav

    Returns:
        dict: Training results and metrics including accuracies and model paths

    Raises:
        ValueError: If training data is invalid or insufficient
        FileNotFoundError: If training directory doesn't exist
    """
    try:
        logger.info(f"Training noise classifier from: {training_data_dir}")

        training_path = Path(training_data_dir)
        if not training_path.exists():
            raise FileNotFoundError(f"Training directory not found: {training_data_dir}")

        # Initialize feature extractor
        feature_extractor = AudioFeatureExtractor()

        # Load training data
        X = []
        y = []
        category_counts = {}

        for category_dir in training_path.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name
            logger.info(f"Loading category: {category}")

            audio_files = list(category_dir.glob('*.wav'))
            if not audio_files:
                logger.warning(f"No audio files found in {category_dir}")
                continue

            category_counts[category] = 0

            for audio_file in audio_files:
                try:
                    # Load audio
                    audio, sr = librosa.load(
                        str(audio_file),
                        sr=config.AUDIO_SAMPLE_RATE
                    )

                    # Extract features using the service
                    features = feature_extractor.extract_features(audio)

                    # Convert to feature vector
                    feature_vector = [
                        features.get('rms', 0.0),
                        features.get('zero_crossing_rate', 0.0),
                        features.get('spectral_centroid', 0.0),
                        features.get('spectral_rolloff', 0.0),
                        features.get('spectral_bandwidth', 0.0),
                    ]

                    X.append(feature_vector)
                    y.append(category)
                    category_counts[category] += 1

                except Exception as e:
                    logger.warning(
                        f"Failed to load audio file: {audio_file}",
                        exc_info=True
                    )
                    continue

        # Validate training data
        if len(X) == 0:
            raise ValueError("No valid training samples found")

        X = np.array(X)
        y = np.array(y)

        logger.info(
            f"Training data loaded",
            extra={
                'num_samples': X.shape[0],
                'num_features': X.shape[1],
                'categories': list(np.unique(y)),
                'category_counts': category_counts
            }
        )

        # Split data
        if len(np.unique(y)) < 2:
            raise ValueError("Need at least 2 categories for classification training")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        logger.info("Training RandomForest classifier...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
            verbose=1
        )

        model.fit(X_train_scaled, y_train)

        # Evaluate
        train_accuracy = model.score(X_train_scaled, y_train)
        test_accuracy = model.score(X_test_scaled, y_test)

        logger.info(
            f"Model training completed",
            extra={
                'train_accuracy': train_accuracy,
                'test_accuracy': test_accuracy
            }
        )

        # Save model
        model_path = config.ML_MODEL_PATH
        scaler_path = config.ML_SCALER_PATH

        # Ensure directories exist
        model_path.parent.mkdir(parents=True, exist_ok=True)
        scaler_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(model, str(model_path))
        joblib.dump(scaler, str(scaler_path))

        logger.info(f"Model saved to: {model_path}")
        logger.info(f"Scaler saved to: {scaler_path}")

        return {
            'status': 'completed',
            'train_accuracy': float(train_accuracy),
            'test_accuracy': float(test_accuracy),
            'num_samples': len(X),
            'num_features': X.shape[1],
            'categories': list(np.unique(y)),
            'category_counts': category_counts,
            'model_path': str(model_path),
            'scaler_path': str(scaler_path)
        }

    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Training data error: {e}", exc_info=True)
        raise
    except Exception as e:
        handle_task_error('train_noise_classifier', e)
        raise


@celery_app.task(name='tasks.validate_model')
@task_logger
def validate_model() -> Dict[str, Any]:
    """
    Validate that the trained model exists and is loadable
    
    Returns:
        dict: Validation results
        
    Raises:
        FileNotFoundError: If model files don't exist
    """
    try:
        model_path = config.ML_MODEL_PATH
        scaler_path = config.ML_SCALER_PATH

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at: {model_path}")

        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler not found at: {scaler_path}")

        # Try to load
        model = joblib.load(str(model_path))
        scaler = joblib.load(str(scaler_path))

        logger.info("Model validation successful")

        return {
            'status': 'valid',
            'model_path': str(model_path),
            'scaler_path': str(scaler_path),
            'model_type': type(model).__name__,
            'scaler_type': type(scaler).__name__
        }

    except FileNotFoundError as e:
        logger.error(f"Model validation failed: {e}")
        raise
    except Exception as e:
        handle_task_error('validate_model', e)
        raise
