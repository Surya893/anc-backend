"""
Test Suite for Noise Classifier V2 (Refactored)
Tests the new modular ML pipeline structure
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import sys
from pathlib import Path


class TestNoiseClassifierModules(unittest.TestCase):
    """Test the refactored noise classifier modules"""

    def test_config_imports(self):
        """Test that config classes can be imported"""
        from src.ml.config import (
            AudioFeatureConfig,
            ModelConfig,
            TrainingConfig,
            InferenceConfig
        )
        
        # Test instantiation
        audio_config = AudioFeatureConfig()
        self.assertEqual(audio_config.sample_rate, 48000)
        self.assertEqual(audio_config.n_mels, 128)
        
        model_config = ModelConfig()
        self.assertEqual(model_config.num_classes, 58)
        
        train_config = TrainingConfig()
        self.assertEqual(train_config.batch_size, 32)
        
        inference_config = InferenceConfig()
        self.assertEqual(inference_config.return_top_k, 5)

    def test_feature_base_imports(self):
        """Test feature base module imports"""
        from src.ml.features.base import AudioFeatureConfig, FeatureExtractorProtocol
        
        config = AudioFeatureConfig()
        self.assertIsNotNone(config)

    @patch('src.ml.features.torch_extractor._torch')
    @patch('src.ml.features.torch_extractor._torchaudio')
    def test_torch_feature_extractor_lazy_loading(self, mock_torchaudio, mock_torch):
        """Test that torch dependencies are lazily loaded"""
        # Before importing, torch should not be loaded
        from src.ml.features import torch_extractor
        
        # The module should import without errors even if torch is not available
        self.assertIsNotNone(torch_extractor)

    def test_noise_categories_export(self):
        """Test that noise categories are exported correctly"""
        from src.ml.pipelines.noise_classifier import NOISE_CATEGORIES_V2, NUM_CLASSES_V2
        
        self.assertEqual(len(NOISE_CATEGORIES_V2), NUM_CLASSES_V2)
        self.assertEqual(NUM_CLASSES_V2, 58)
        self.assertIn('white_noise', NOISE_CATEGORIES_V2)
        self.assertIn('traffic_highway', NOISE_CATEGORIES_V2)
        self.assertIn('baby_crying', NOISE_CATEGORIES_V2)

    def test_backward_compatibility(self):
        """Test backward compatibility with old import paths"""
        with patch('sys.modules', {'torch': MagicMock(), 'torchaudio': MagicMock(), 'torchvision': MagicMock()}):
            # Should be able to import from old module
            from src.ml.noise_classifier_v2 import (
                NOISE_CATEGORIES_V2,
                NUM_CLASSES_V2
            )
            
            self.assertEqual(NUM_CLASSES_V2, 58)


class TestMLService(unittest.TestCase):
    """Test ML service integration"""

    @patch('backend.services.ml_service.Path')
    def test_ml_service_init(self, mock_path):
        """Test ML service initialization"""
        mock_path.return_value.exists.return_value = False
        
        from backend.services.ml_service import MLService
        
        # Should initialize without errors even if models not found
        service = MLService()
        self.assertIsNotNone(service)

    @patch('backend.services.ml_service.Path')
    @patch('backend.services.ml_service.pickle')
    def test_ml_service_classify_without_model(self, mock_pickle, mock_path):
        """Test classification when no model is loaded"""
        mock_path.return_value.exists.return_value = False
        
        from backend.services.ml_service import MLService
        
        service = MLService()
        
        # Should return unknown classification
        audio_data = np.random.randn(1000).astype(np.float32)
        import base64
        audio_base64 = base64.b64encode(audio_data.tobytes()).decode('utf-8')
        
        result = service.classify_noise(audio_base64)
        
        self.assertEqual(result['noise_type'], 'unknown')
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['model_version'], 'none')


class TestFeatureExtraction(unittest.TestCase):
    """Test feature extraction modules"""

    def test_librosa_extractor_still_works(self):
        """Test that the original librosa-based extractor still works"""
        from src.ml.feature_extraction import AudioFeatureExtractor
        
        extractor = AudioFeatureExtractor(sample_rate=44100, n_mfcc=13)
        self.assertEqual(extractor.sample_rate, 44100)
        self.assertEqual(extractor.n_mfcc, 13)
        
        # Test with dummy audio
        audio = np.random.randn(44100)  # 1 second
        mfccs = extractor.extract_mfcc(audio)
        
        self.assertEqual(mfccs.shape[0], 13)  # 13 MFCC coefficients


class TestModuleStructure(unittest.TestCase):
    """Test that the module structure is correct"""

    def test_ml_directory_structure(self):
        """Test that new directories exist"""
        ml_dir = Path('src/ml')
        
        self.assertTrue((ml_dir / 'config.py').exists())
        self.assertTrue((ml_dir / 'features').is_dir())
        self.assertTrue((ml_dir / 'models').is_dir())
        self.assertTrue((ml_dir / 'pipelines').is_dir())
        
        self.assertTrue((ml_dir / 'features' / '__init__.py').exists())
        self.assertTrue((ml_dir / 'features' / 'base.py').exists())
        self.assertTrue((ml_dir / 'features' / 'torch_extractor.py').exists())
        
        self.assertTrue((ml_dir / 'models' / '__init__.py').exists())
        self.assertTrue((ml_dir / 'models' / 'efficientnet_audio.py').exists())
        
        self.assertTrue((ml_dir / 'pipelines' / '__init__.py').exists())
        self.assertTrue((ml_dir / 'pipelines' / 'noise_classifier.py').exists())

    def test_no_duplicate_audiofeatureconfig(self):
        """Test that AudioFeatureConfig is only defined once"""
        from src.ml.config import AudioFeatureConfig as ConfigVersion
        from src.ml.features.base import AudioFeatureConfig as BaseVersion
        
        # They should be the same class
        self.assertIs(ConfigVersion, BaseVersion)


if __name__ == '__main__':
    unittest.main()
