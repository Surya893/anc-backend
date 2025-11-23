"""
Test Script for Noise Classification Pipeline
Demonstrates feature extraction, model architecture, and prediction workflow.
"""

import numpy as np
import sys
import os

print("=" * 80)
print("NOISE CLASSIFICATION SYSTEM - COMPLETE PIPELINE TEST")
print("=" * 80)

# Test 1: Feature Extraction
print("\n" + "="*80)
print("TEST 1: Feature Extraction from Database")
print("="*80)

try:
    from feature_extraction import batch_extract_features, AudioFeatureExtractor
    from database_schema import ANCDatabase

    print("\n✓ Modules imported successfully")

    # Extract features
    print("\nExtracting features from database recordings...")
    data = batch_extract_features(db_path='anc_system.db', output_file='features.npz')

    print(f"\n✓ Feature extraction complete!")
    print(f"  Total samples: {len(data['features'])}")
    print(f"  Feature dimension: {data['features'].shape[1]}")
    print(f"  Unique classes: {np.unique(data['labels'])}")

    # Show feature statistics
    print(f"\nFeature statistics:")
    print(f"  Mean: {np.mean(data['features']):.4f}")
    print(f"  Std: {np.std(data['features']):.4f}")
    print(f"  Min: {np.min(data['features']):.4f}")
    print(f"  Max: {np.max(data['features']):.4f}")

    # Class distribution
    print(f"\nClass distribution:")
    unique, counts = np.unique(data['labels'], return_counts=True)
    for class_name, count in zip(unique, counts):
        print(f"  {class_name:<15} {count:>3} samples")

except Exception as e:
    print(f"✗ Feature extraction failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Model Architecture
print("\n" + "="*80)
print("TEST 2: Model Architecture")
print("="*80)

try:
    # Try to import PyTorch
    import torch
    import torch.nn as nn
    from noise_classifier_model import NoiseClassifierMLP, NoiseClassifierCNN

    print("\n✓ PyTorch imported successfully")
    print(f"  PyTorch version: {torch.__version__}")
    print(f"  CUDA available: {torch.cuda.is_available()}")

    # Create model
    input_dim = data['features'].shape[1]
    num_classes = len(np.unique(data['labels']))

    print(f"\nCreating models...")
    print(f"  Input dimension: {input_dim}")
    print(f"  Number of classes: {num_classes}")

    # MLP model
    mlp_model = NoiseClassifierMLP(input_dim, num_classes)
    mlp_params = sum(p.numel() for p in mlp_model.parameters())
    print(f"\n✓ MLP Model created")
    print(f"  Parameters: {mlp_params:,}")

    # Test forward pass
    test_input = torch.randn(8, input_dim)
    with torch.no_grad():
        output = mlp_model(test_input)

    print(f"  Test forward pass: {test_input.shape} -> {output.shape}")

    # CNN model
    cnn_model = NoiseClassifierCNN(input_dim, num_classes)
    cnn_params = sum(p.numel() for p in cnn_model.parameters())
    print(f"\n✓ CNN Model created")
    print(f"  Parameters: {cnn_params:,}")

    with torch.no_grad():
        cnn_output = cnn_model(test_input)
    print(f"  Test forward pass: {test_input.shape} -> {cnn_output.shape}")

except ImportError:
    print("\n⚠ PyTorch not installed - skipping model tests")
    print("  Install with: pip install torch")
except Exception as e:
    print(f"✗ Model test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Data Loading
print("\n" + "="*80)
print("TEST 3: Data Loading and Preprocessing")
print("="*80)

try:
    from noise_classifier_model import NoiseDataset, create_data_loaders
    from sklearn.preprocessing import LabelEncoder, StandardScaler

    print("\n✓ Data processing modules imported")

    # Create dataset
    print("\nCreating datasets...")
    dataset = NoiseDataset(data['features'], data['labels'], fit_transform=True)

    print(f"✓ Dataset created")
    print(f"  Total samples: {len(dataset)}")
    print(f"  Feature dim: {dataset.get_feature_dim()}")
    print(f"  Num classes: {dataset.get_num_classes()}")
    print(f"  Classes: {dataset.label_encoder.classes_}")

    # Test data loader
    print("\nCreating data loaders...")
    train_loader, test_loader, train_dataset, test_dataset = create_data_loaders(
        features_file='features.npz',
        batch_size=4,
        test_size=0.2
    )

    print(f"✓ Data loaders created")
    print(f"  Train samples: {len(train_dataset)}")
    print(f"  Test samples: {len(test_dataset)}")
    print(f"  Batch size: {train_loader.batch_size}")

    # Test batch
    features_batch, labels_batch = next(iter(train_loader))
    print(f"  Sample batch: features={features_batch.shape}, labels={labels_batch.shape}")

except Exception as e:
    print(f"✗ Data loading test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Training Simulation (without actual training)
print("\n" + "="*80)
print("TEST 4: Training Pipeline Components")
print("="*80)

try:
    from train_classifier import NoiseClassifierTrainer

    print("\n✓ Training module imported")

    if 'torch' in sys.modules and 'mlp_model' in locals():
        # Create trainer
        trainer = NoiseClassifierTrainer(
            model=mlp_model,
            device='cpu',
            learning_rate=0.001
        )

        print(f"✓ Trainer created")
        print(f"  Optimizer: {type(trainer.optimizer).__name__}")
        print(f"  Loss function: {type(trainer.criterion).__name__}")
        print(f"  Scheduler: {type(trainer.scheduler).__name__}")

        # Simulate one training step
        print("\nSimulating one training step...")
        features_batch, labels_batch = next(iter(train_loader))

        trainer.model.train()
        trainer.optimizer.zero_grad()
        outputs = trainer.model(features_batch)
        loss = trainer.criterion(outputs, labels_batch)
        loss.backward()
        trainer.optimizer.step()

        _, predicted = torch.max(outputs.data, 1)
        correct = (predicted == labels_batch).sum().item()
        accuracy = 100 * correct / len(labels_batch)

        print(f"✓ Training step completed")
        print(f"  Loss: {loss.item():.4f}")
        print(f"  Batch accuracy: {accuracy:.2f}%")

    else:
        print("⚠ Skipping training test (PyTorch not available)")

except Exception as e:
    print(f"✗ Training test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Feature Extraction Details
print("\n" + "="*80)
print("TEST 5: Detailed Feature Analysis")
print("="*80)

try:
    # Load a sample recording
    db = ANCDatabase('anc_system.db')
    recordings = db.get_all_recordings()

    if recordings:
        rec_id = recordings[0][0]
        print(f"\nAnalyzing Recording {rec_id}...")

        # Get waveform
        db.cursor.execute("""
            SELECT waveform_id
            FROM audio_waveforms
            WHERE recording_id = ?
            LIMIT 1
        """, (rec_id,))

        result = db.cursor.fetchone()
        if result:
            waveform_id = result[0]
            audio_data = db.get_waveform(waveform_id)

            print(f"✓ Waveform loaded")
            print(f"  Samples: {len(audio_data)}")
            print(f"  Duration: {len(audio_data) / 44100:.2f}s")

            # Extract all features
            extractor = AudioFeatureExtractor()
            features = extractor.extract_all_features(audio_data)

            print(f"\n✓ Features extracted:")
            for name, feat in features.items():
                if feat.ndim == 1:
                    shape = (feat.shape[0],)
                else:
                    shape = feat.shape
                print(f"  {name:<20} shape: {shape}")

            # Get feature vector
            feature_vector = extractor.extract_feature_vector(audio_data)
            print(f"\n✓ Feature vector created")
            print(f"  Dimension: {len(feature_vector)}")

    db.close()

except Exception as e:
    print(f"✗ Feature analysis failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

tests_passed = 0
tests_total = 5

if 'data' in locals():
    tests_passed += 1
    print("✓ Test 1: Feature Extraction - PASSED")
else:
    print("✗ Test 1: Feature Extraction - FAILED")

if 'mlp_model' in locals():
    tests_passed += 1
    print("✓ Test 2: Model Architecture - PASSED")
else:
    print("✗ Test 2: Model Architecture - SKIPPED/FAILED")

if 'dataset' in locals():
    tests_passed += 1
    print("✓ Test 3: Data Loading - PASSED")
else:
    print("✗ Test 3: Data Loading - FAILED")

if 'trainer' in locals():
    tests_passed += 1
    print("✓ Test 4: Training Pipeline - PASSED")
else:
    print("✗ Test 4: Training Pipeline - SKIPPED/FAILED")

if 'feature_vector' in locals():
    tests_passed += 1
    print("✓ Test 5: Feature Analysis - PASSED")
else:
    print("✗ Test 5: Feature Analysis - FAILED")

print(f"\n{'─' * 80}")
print(f"Total: {tests_passed}/{tests_total} tests passed")

if tests_passed == tests_total:
    print("\n✓ ALL TESTS PASSED!")
elif tests_passed >= 3:
    print(f"\n⚠ PARTIAL SUCCESS ({tests_passed}/{tests_total} passed)")
else:
    print(f"\n✗ TESTS FAILED ({tests_passed}/{tests_total} passed)")

print("=" * 80)
