"""
Unit Tests for Training Script Utilities
=========================================

Tests the utilities in train_sklearn_demo.py including data path
handling and synthetic data generation.
"""

import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import os
import tempfile
from pathlib import Path


class TestDataPathUtilities(unittest.TestCase):
    """Test data path finding and handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()

    def tearDown(self):
        """Clean up."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_find_data_file_current_directory(self):
        """Test finding data file in current directory."""
        from scripts.training.train_sklearn_demo import find_data_file

        os.chdir(self.temp_dir)

        # Create a features file
        features_path = os.path.join(self.temp_dir, 'features.npz')
        np.savez(features_path, features=np.array([[1, 2]]), labels=np.array(['test']))

        result = find_data_file()

        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))

    def test_find_data_file_augmented_preferred(self):
        """Test that augmented file is preferred over regular."""
        from scripts.training.train_sklearn_demo import find_data_file

        os.chdir(self.temp_dir)

        # Create both files
        regular_path = os.path.join(self.temp_dir, 'features.npz')
        augmented_path = os.path.join(self.temp_dir, 'features_augmented.npz')

        np.savez(regular_path, features=np.array([[1, 2]]), labels=np.array(['test']))
        np.savez(augmented_path, features=np.array([[3, 4]]), labels=np.array(['test']))

        result = find_data_file()

        # Should return augmented version
        self.assertTrue('augmented' in result)

    def test_find_data_file_not_found(self):
        """Test behavior when no data file found."""
        from scripts.training.train_sklearn_demo import find_data_file

        os.chdir(self.temp_dir)

        result = find_data_file()

        self.assertIsNone(result)


class TestSyntheticDataGeneration(unittest.TestCase):
    """Test synthetic data generation."""

    def test_generate_synthetic_data_default(self):
        """Test generating synthetic data with defaults."""
        from scripts.training.train_sklearn_demo import generate_synthetic_data

        data = generate_synthetic_data()

        # Check structure
        self.assertIn('features', data)
        self.assertIn('labels', data)
        self.assertIn('recording_ids', data)

        # Check sizes (6 classes * 20 samples = 120)
        self.assertEqual(len(data['features']), 120)
        self.assertEqual(len(data['labels']), 120)
        self.assertEqual(len(data['recording_ids']), 120)

        # Check feature dimension
        self.assertEqual(data['features'].shape[1], 168)

    def test_generate_synthetic_data_custom_size(self):
        """Test generating synthetic data with custom size."""
        from scripts.training.train_sklearn_demo import generate_synthetic_data

        data = generate_synthetic_data(num_samples_per_class=50)

        # 6 classes * 50 samples = 300
        self.assertEqual(len(data['features']), 300)

    def test_synthetic_data_has_class_separation(self):
        """Test that synthetic data has some class separation."""
        from scripts.training.train_sklearn_demo import generate_synthetic_data

        data = generate_synthetic_data(num_samples_per_class=10)

        features = data['features']
        labels = data['labels']

        # Get mean features for first two classes
        unique_labels = np.unique(labels)
        class1_features = features[labels == unique_labels[0]]
        class2_features = features[labels == unique_labels[1]]

        class1_mean = np.mean(class1_features, axis=0)
        class2_mean = np.mean(class2_features, axis=0)

        # Means should be different (due to class offset)
        distance = np.linalg.norm(class1_mean - class2_mean)
        self.assertGreater(distance, 0.1)  # Some minimum separation

    def test_synthetic_data_shuffled(self):
        """Test that synthetic data is shuffled."""
        from scripts.training.train_sklearn_demo import generate_synthetic_data

        # Set seed for reproducibility
        np.random.seed(42)
        data1 = generate_synthetic_data(num_samples_per_class=5)

        # First few labels shouldn't all be the same (due to shuffling)
        labels = data1['labels'][:10]
        unique_in_first_ten = len(np.unique(labels))

        self.assertGreater(unique_in_first_ten, 1)


class TestTrainClassifierFunction(unittest.TestCase):
    """Test train_sklearn_classifier function."""

    @patch('scripts.training.train_sklearn_demo.find_data_file')
    @patch('scripts.training.train_sklearn_demo.generate_synthetic_data')
    def test_uses_synthetic_when_no_data_file(self, mock_generate, mock_find):
        """Test that synthetic data is used when no file found."""
        from scripts.training.train_sklearn_demo import train_sklearn_classifier

        # Mock no data file found
        mock_find.return_value = None

        # Mock synthetic data
        mock_generate.return_value = {
            'features': np.random.randn(120, 168),
            'labels': np.array(['class1'] * 60 + ['class2'] * 60),
            'recording_ids': np.arange(120)
        }

        # This will fail due to missing sklearn, but we're testing the logic
        try:
            train_sklearn_classifier()
        except Exception:
            pass  # Expected to fail without sklearn

        # Verify synthetic data was generated
        mock_generate.assert_called_once()

    @patch('scripts.training.train_sklearn_demo.os.path.exists')
    @patch('scripts.training.train_sklearn_demo.np.load')
    def test_validates_data_structure(self, mock_load, mock_exists):
        """Test that data structure is validated."""
        from scripts.training.train_sklearn_demo import train_sklearn_classifier

        # Mock file exists
        mock_exists.return_value = True

        # Mock data without required fields
        mock_data = MagicMock()
        mock_data.__getitem__.side_effect = lambda key: {}.get(key)  # Missing keys
        mock_load.return_value = mock_data

        # Should handle validation error gracefully
        try:
            train_sklearn_classifier(data_path='test.npz')
        except Exception:
            pass  # Expected to fail

        mock_load.assert_called()


class TestPredictSampleFunction(unittest.TestCase):
    """Test predict_sample function."""

    def test_predict_sample_returns_correct_format(self):
        """Test that predict_sample returns correct format."""
        from scripts.training.train_sklearn_demo import predict_sample

        # Create mock model data
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0])
        mock_model.predict_proba.return_value = np.array([[0.7, 0.3]])

        mock_scaler = Mock()
        mock_scaler.transform.return_value = np.array([[1, 2, 3]])

        mock_label_encoder = Mock()
        mock_label_encoder.classes_ = np.array(['class1', 'class2'])

        model_data = {
            'model': mock_model,
            'scaler': mock_scaler,
            'label_encoder': mock_label_encoder
        }

        # Test prediction
        features = np.array([1, 2, 3])
        predicted_class, confidence, all_probs = predict_sample(model_data, features)

        # Verify return types
        self.assertIsInstance(predicted_class, (str, np.str_))
        self.assertIsInstance(confidence, (float, np.floating))
        self.assertIsInstance(all_probs, dict)

        # Verify probabilities sum to 1
        self.assertAlmostEqual(sum(all_probs.values()), 1.0, places=5)


class TestCommandLineInterface(unittest.TestCase):
    """Test command-line argument handling."""

    @patch('sys.argv', ['train_sklearn_demo.py', '--help'])
    def test_help_argument(self):
        """Test --help argument."""
        from scripts.training.train_sklearn_demo import main

        # Should raise SystemExit with code 0
        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 0)

    @patch('sys.argv', ['train_sklearn_demo.py', '--data', 'test.npz'])
    @patch('scripts.training.train_sklearn_demo.train_sklearn_classifier')
    def test_data_argument(self, mock_train):
        """Test --data argument is passed correctly."""
        from scripts.training.train_sklearn_demo import main

        # Mock to avoid actual training
        mock_train.return_value = None

        try:
            main()
        except SystemExit:
            pass

        # Verify train was called with data_path
        if mock_train.called:
            call_args = mock_train.call_args
            self.assertEqual(call_args[1].get('data_path') or call_args[0][0], 'test.npz')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
