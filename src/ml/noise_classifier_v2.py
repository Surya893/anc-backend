"""
Noise Classifier v2.0 - Deep Learning Model for 50+ Noise Categories

DEPRECATED: This module has been refactored for better modularity.
Please use the new modular structure:

- src.ml.config: Configuration classes
- src.ml.features.torch_extractor: TorchAudioFeatureExtractor
- src.ml.models.efficientnet_audio: EfficientNetAudioClassifier
- src.ml.pipelines.noise_classifier: NoiseClassifierService

This file provides backward compatibility by re-exporting the new APIs.

Version: 2.0.0
Date: 2025-11-19
"""

import warnings
import logging

# Re-export new APIs for backward compatibility
from .config import AudioFeatureConfig, ModelConfig, TrainingConfig
from .features.torch_extractor import TorchAudioFeatureExtractor as AudioFeatureExtractor
from .models.efficientnet_audio import EfficientNetAudioClassifier
from .pipelines.noise_classifier import (
    NoiseClassifierService as NoiseClassifierV2,
    NoiseDataset,
    NOISE_CATEGORIES_V2,
    NUM_CLASSES_V2
)

logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "noise_classifier_v2.py is deprecated. Please use the new modular structure:\n"
    "  - from src.ml.config import AudioFeatureConfig\n"
    "  - from src.ml.features.torch_extractor import TorchAudioFeatureExtractor\n"
    "  - from src.ml.models.efficientnet_audio import EfficientNetAudioClassifier\n"
    "  - from src.ml.pipelines.noise_classifier import NoiseClassifierService\n",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'AudioFeatureConfig',
    'AudioFeatureExtractor',
    'EfficientNetAudioClassifier',
    'NoiseClassifierV2',
    'NoiseDataset',
    'NOISE_CATEGORIES_V2',
    'NUM_CLASSES_V2'
]


if __name__ == "__main__":
    import numpy as np
    
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Create classifier
    classifier = NoiseClassifierV2()

    # Generate test audio (white noise)
    test_audio = np.random.randn(48000) * 0.5  # 1 second at 48kHz

    # Classify
    result = classifier.classify(test_audio, sample_rate=48000)

    print("\nClassification Result:")
    print(f"Predicted Class: {result['predicted_class']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print("\nTop 5 Predictions:")
    for category, prob in result['top_k']:
        print(f"  {category}: {prob:.2%}")

    # Export for deployment
    classifier.export('noise_classifier_v2.onnx', format='onnx')
    classifier.export('noise_classifier_v2.pt', format='torchscript')
    print("\nModels exported for deployment")
