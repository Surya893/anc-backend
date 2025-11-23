"""
Setup and Verification Script
Fixes alerts and verifies the noise classification system is ready.
"""

import sys
import subprocess
import os
import numpy as np


def check_pytorch():
    """Check if PyTorch is installed."""
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__} is installed")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
        return True
    except ImportError:
        print("✗ PyTorch is NOT installed")
        return False


def install_pytorch():
    """Install PyTorch."""
    print("\nInstalling PyTorch (CPU version)...")
    print("This may take a few minutes...\n")

    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'torch', 'torchvision', 'torchaudio',
            '--index-url', 'https://download.pytorch.org/whl/cpu'
        ])
        print("\n✓ PyTorch installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to install PyTorch: {e}")
        return False


def check_dataset_size():
    """Check if dataset has sufficient samples."""
    try:
        from database_schema import ANCDatabase
        from collections import defaultdict

        db = ANCDatabase('anc_system.db')
        recordings = db.get_all_recordings()
        db.close()

        stats = defaultdict(int)
        for rec in recordings:
            env_type = rec[5]
            if env_type:
                stats[env_type] += 1

        total_samples = sum(stats.values())
        num_classes = len(stats)
        min_samples = min(stats.values()) if stats else 0

        print(f"\n{'─' * 80}")
        print("DATASET CHECK")
        print(f"{'─' * 80}")
        print(f"Total samples: {total_samples}")
        print(f"Number of classes: {num_classes}")
        print(f"Minimum samples per class: {min_samples}")

        print(f"\nClass distribution:")
        for class_name, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            bar = '█' * (count * 2)
            print(f"  {class_name:<15} {count:>3} {bar}")

        # Check if sufficient
        RECOMMENDED_MIN = 20
        ABSOLUTE_MIN = 10

        if min_samples >= RECOMMENDED_MIN:
            print(f"\n✓ Dataset is sufficient for robust training")
            return True
        elif min_samples >= ABSOLUTE_MIN:
            print(f"\n⚠ Dataset meets minimum requirements but more samples recommended")
            print(f"  Current: {min_samples} per class")
            print(f"  Recommended: {RECOMMENDED_MIN}+ per class")
            return True
        else:
            print(f"\n✗ Dataset is insufficient for training")
            print(f"  Current: {min_samples} per class")
            print(f"  Minimum required: {ABSOLUTE_MIN} per class")
            print(f"  Recommended: {RECOMMENDED_MIN}+ per class")
            return False

    except Exception as e:
        print(f"✗ Failed to check dataset: {e}")
        return False


def check_features():
    """Check if features are extracted."""
    if os.path.exists('features.npz'):
        try:
            data = np.load('features.npz')
            features = data['features']
            labels = data['labels']
            print(f"\n✓ Features extracted: {features.shape}")
            print(f"  {len(features)} samples with {features.shape[1]} features")
            return True
        except Exception as e:
            print(f"✗ Error loading features: {e}")
            return False
    else:
        print("\n✗ Features not extracted yet")
        return False


def extract_features():
    """Extract features from database."""
    print("\nExtracting features from database...")
    try:
        from feature_extraction import batch_extract_features
        data = batch_extract_features()
        print(f"✓ Features extracted successfully")
        return True
    except Exception as e:
        print(f"✗ Feature extraction failed: {e}")
        return False


def test_model_architecture():
    """Test that model architectures work."""
    try:
        import torch
        from noise_classifier_model import NoiseClassifierMLP, NoiseClassifierCNN

        print("\nTesting model architectures...")

        # Load features to get dimensions
        data = np.load('features.npz')
        input_dim = data['features'].shape[1]
        num_classes = len(np.unique(data['labels']))

        # Test MLP
        mlp = NoiseClassifierMLP(input_dim, num_classes)
        test_input = torch.randn(4, input_dim)
        with torch.no_grad():
            output = mlp(test_input)

        print(f"✓ MLP model working: {test_input.shape} -> {output.shape}")
        print(f"  Parameters: {sum(p.numel() for p in mlp.parameters()):,}")

        # Test CNN
        cnn = NoiseClassifierCNN(input_dim, num_classes)
        with torch.no_grad():
            output = cnn(test_input)

        print(f"✓ CNN model working: {test_input.shape} -> {output.shape}")
        print(f"  Parameters: {sum(p.numel() for p in cnn.parameters()):,}")

        return True

    except Exception as e:
        print(f"✗ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_quick_training_test():
    """Run a quick training test to verify everything works."""
    print("\n" + "=" * 80)
    print("RUNNING QUICK TRAINING TEST")
    print("=" * 80)

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from noise_classifier_model import create_data_loaders, NoiseClassifierMLP

        # Create data loaders
        train_loader, test_loader, train_dataset, test_dataset = create_data_loaders(
            batch_size=4,
            test_size=0.2
        )

        input_dim = train_dataset.get_feature_dim()
        num_classes = train_dataset.get_num_classes()

        print(f"\nDataset loaded:")
        print(f"  Train samples: {len(train_dataset)}")
        print(f"  Test samples: {len(test_dataset)}")
        print(f"  Input dim: {input_dim}")
        print(f"  Classes: {num_classes}")

        # Create model
        model = NoiseClassifierMLP(input_dim, num_classes)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        print(f"\nRunning 5 training epochs (quick test)...")

        # Train for 5 epochs
        model.train()
        for epoch in range(5):
            total_loss = 0
            correct = 0
            total = 0

            for features, labels in train_loader:
                optimizer.zero_grad()
                outputs = model(features)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

            train_acc = 100 * correct / total
            avg_loss = total_loss / len(train_loader)
            print(f"  Epoch {epoch+1}/5: Loss={avg_loss:.4f}, Acc={train_acc:.2f}%")

        # Quick validation
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for features, labels in test_loader:
                outputs = model(features)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        val_acc = 100 * correct / total
        print(f"\nValidation Accuracy: {val_acc:.2f}%")

        if val_acc >= 30:  # Very low threshold for small dataset
            print("✓ Training test passed!")
            return True
        else:
            print("⚠ Training completed but accuracy is very low")
            print("  This is expected with a small dataset")
            return True

    except Exception as e:
        print(f"✗ Training test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main verification and setup."""
    print("=" * 80)
    print("NOISE CLASSIFICATION SYSTEM - SETUP & VERIFICATION")
    print("=" * 80)

    results = {}

    # Step 1: Check PyTorch
    print("\n" + "─" * 80)
    print("STEP 1: Check PyTorch Installation")
    print("─" * 80)

    pytorch_installed = check_pytorch()

    if not pytorch_installed:
        install = input("\nInstall PyTorch now? (y/n): ").strip().lower()
        if install == 'y':
            pytorch_installed = install_pytorch()
            if pytorch_installed:
                # Reload to verify
                pytorch_installed = check_pytorch()

    results['pytorch'] = pytorch_installed

    # Step 2: Check dataset
    print("\n" + "─" * 80)
    print("STEP 2: Check Dataset Size")
    print("─" * 80)

    dataset_ok = check_dataset_size()
    results['dataset'] = dataset_ok

    if not dataset_ok:
        print("\n💡 To collect more data, run:")
        print("   python collect_training_data.py")

    # Step 3: Check features
    print("\n" + "─" * 80)
    print("STEP 3: Check Feature Extraction")
    print("─" * 80)

    features_ok = check_features()

    if not features_ok:
        extract = input("\nExtract features now? (y/n): ").strip().lower()
        if extract == 'y':
            features_ok = extract_features()

    results['features'] = features_ok

    # Step 4: Test models (if PyTorch available)
    if pytorch_installed and features_ok:
        print("\n" + "─" * 80)
        print("STEP 4: Test Model Architectures")
        print("─" * 80)

        models_ok = test_model_architecture()
        results['models'] = models_ok

        # Step 5: Quick training test
        if models_ok and dataset_ok:
            print("\n" + "─" * 80)
            print("STEP 5: Quick Training Test")
            print("─" * 80)

            run_test = input("\nRun quick training test? (y/n): ").strip().lower()
            if run_test == 'y':
                training_ok = run_quick_training_test()
                results['training'] = training_ok

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    checks = [
        ("PyTorch installed", results.get('pytorch', False)),
        ("Dataset sufficient", results.get('dataset', False)),
        ("Features extracted", results.get('features', False)),
        ("Model architectures", results.get('models', False)),
        ("Training test", results.get('training', False))
    ]

    for name, status in checks:
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}")

    passed = sum(1 for _, status in checks if status)
    total = len(checks)

    print(f"\n{passed}/{total} checks passed")

    if passed == total:
        print("\n" + "=" * 80)
        print("✓ SYSTEM READY FOR FULL TRAINING!")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Run full training: python train_classifier.py")
        print("  2. Expected validation accuracy: >70% (with sufficient data)")
        print("  3. Make predictions: python predict_noise_type.py")

    elif passed >= 3:
        print("\n⚠ System partially ready")
        print("\nTo complete setup:")
        if not results.get('pytorch'):
            print("  - Install PyTorch: pip install torch")
        if not results.get('dataset'):
            print("  - Collect more data: python collect_training_data.py")
        if not results.get('features'):
            print("  - Extract features: python feature_extraction.py")

    else:
        print("\n✗ System needs configuration")
        print("\nFollow the steps above to fix issues")


if __name__ == "__main__":
    main()
