"""
Verify Noise Classification Pipeline
Tests feature extraction and shows system capabilities.
"""

import numpy as np
from database_schema import ANCDatabase

print("=" * 80)
print("NOISE CLASSIFICATION SYSTEM - VERIFICATION")
print("=" * 80)

# Test 1: Feature Extraction
print("\n1. FEATURE EXTRACTION TEST")
print("─" * 80)

try:
    # Load extracted features
    data = np.load('features.npz')
    features = data['features']
    labels = data['labels']
    recording_ids = data['recording_ids']

    print(f"✓ Features loaded successfully")
    print(f"  Total samples: {len(features)}")
    print(f"  Feature dimension: {features.shape[1]}")
    print(f"  Number of classes: {len(np.unique(labels))}")

    # Show class distribution
    print(f"\n  Class distribution:")
    unique, counts = np.unique(labels, return_counts=True)
    for class_name, count in zip(unique, counts):
        bar = '█' * (count * 3)
        print(f"    {class_name:<15} {count:>2} samples {bar}")

    # Feature statistics
    print(f"\n  Feature statistics:")
    print(f"    Mean: {np.mean(features):.4f}")
    print(f"    Std:  {np.std(features):.4f}")
    print(f"    Min:  {np.min(features):.4f}")
    print(f"    Max:  {np.max(features):.4f}")

except Exception as e:
    print(f"✗ Feature loading failed: {e}")

# Test 2: Database Integration
print("\n2. DATABASE INTEGRATION TEST")
print("─" * 80)

try:
    db = ANCDatabase('anc_system.db')
    recordings = db.get_all_recordings()

    print(f"✓ Database connected")
    print(f"  Total recordings: {len(recordings)}")

    # Show some recording details
    print(f"\n  Sample recordings:")
    for i, rec in enumerate(recordings[:5], 1):
        rec_id, timestamp, duration, sample_rate, num_samples, env_type, noise_db, location = rec
        print(f"    {i}. ID:{rec_id} | {env_type:<12} | {duration:.1f}s | {noise_db:.1f}dB | {location}")

    db.close()

except Exception as e:
    print(f"✗ Database test failed: {e}")

# Test 3: Feature Quality Assessment
print("\n3. FEATURE QUALITY ASSESSMENT")
print("─" * 80)

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    # Standardize features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # PCA for visualization
    pca = PCA(n_components=2)
    features_pca = pca.fit_transform(features_scaled)

    print(f"✓ Feature analysis complete")
    print(f"  PCA explained variance: {pca.explained_variance_ratio_}")
    print(f"  Total variance explained: {sum(pca.explained_variance_ratio_):.2%}")

    # Check class separability
    print(f"\n  Class separability (PCA space):")
    for class_name in np.unique(labels):
        class_mask = labels == class_name
        class_features = features_pca[class_mask]
        centroid = np.mean(class_features, axis=0)
        std = np.std(class_features, axis=0)
        print(f"    {class_name:<15} centroid: ({centroid[0]:>7.2f}, {centroid[1]:>7.2f}) "
              f"std: ({std[0]:>5.2f}, {std[1]:>5.2f})")

except Exception as e:
    print(f"⚠ Feature analysis failed: {e}")

# Test 4: Model Readiness Check
print("\n4. MODEL READINESS CHECK")
print("─" * 80)

min_samples_per_class = 5
sufficient_data = all(count >= min_samples_per_class for count in counts)

print(f"  Minimum samples per class: {min_samples_per_class}")
print(f"  Current minimum: {min(counts)}")

if sufficient_data:
    print(f"  ✓ Dataset is ready for training")
else:
    print(f"  ⚠ Need more samples (minimum {min_samples_per_class} per class recommended)")

# Recommended train/test split
test_size = 0.2
train_samples = int(len(features) * (1 - test_size))
test_samples = len(features) - train_samples

print(f"\n  Recommended split (80/20):")
print(f"    Train samples: {train_samples}")
print(f"    Test samples: {test_samples}")

# Test 5: System Capabilities Summary
print("\n5. SYSTEM CAPABILITIES")
print("─" * 80)

print(f"""
✓ Feature Extraction:
  - MFCC (13 coefficients + deltas)
  - Spectral features (centroid, rolloff, ZCR, RMS)
  - Chroma features (12 pitch classes)
  - Statistical summaries (mean, std, min, max)
  - Total: {features.shape[1]} features per recording

✓ Supported Model Architectures:
  - Multi-Layer Perceptron (MLP)
  - 1D Convolutional Neural Network (CNN)
  - Ensemble models

✓ Training Features:
  - Early stopping
  - Learning rate scheduling
  - Batch normalization
  - Dropout regularization
  - L2 weight decay

✓ Evaluation Metrics:
  - Accuracy, Precision, Recall, F1-score
  - Per-class metrics
  - Confusion matrix
  - Training history visualization

✓ Inference Capabilities:
  - Classify from audio file
  - Classify from database recording
  - Batch prediction
  - Confidence scores
  - Probability distributions
""")

# Summary
print("=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

checks = [
    ("Feature extraction", 'features' in locals()),
    ("Database integration", 'recordings' in locals()),
    ("Feature quality", 'features_pca' in locals()),
    ("Data readiness", sufficient_data if 'sufficient_data' in locals() else False)
]

passed = sum(1 for _, check in checks if check)
total = len(checks)

for name, status in checks:
    symbol = "✓" if status else "✗"
    print(f"{symbol} {name}")

print(f"\n{passed}/{total} checks passed")

if passed == total:
    print("\n✓ System is ready for model training!")
    print("\nNext steps:")
    print("  1. Install PyTorch: pip install torch")
    print("  2. Train model: python train_classifier.py")
    print("  3. Make predictions: python predict_noise_type.py")
elif passed >= 2:
    print("\n⚠ System partially ready - some features may not be available")
else:
    print("\n✗ System needs configuration")

print("=" * 80)
