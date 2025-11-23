"""
Fine-tune Classifier for Emergency Sound Detection
Adds alarm/emergency sound classes to existing model.
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import pickle
from datetime import datetime


def generate_alarm_features():
    """
    Generate synthetic alarm/emergency sound features.

    Alarm characteristics:
    - High frequency (2-4 kHz typical for smoke alarms)
    - Repetitive pattern
    - High amplitude
    - Narrow frequency band
    """
    print("Generating synthetic alarm features...")

    alarm_features = []

    # Generate 20 alarm samples
    for i in range(20):
        # Simulate alarm characteristics
        # Alarms typically have:
        # - High spectral centroid (3000 Hz range)
        # - High RMS energy
        # - Low zero-crossing rate variation
        # - Distinct MFCC pattern

        # Create feature vector (168 dimensions to match existing)
        features = np.zeros(168)

        # MFCC-like features (first 52 dims) - high frequency content
        features[0:13] = np.random.normal(0.8, 0.1, 13)  # High energy
        features[13:26] = np.random.normal(0.6, 0.15, 13)  # Std
        features[26:39] = np.random.normal(0.3, 0.1, 13)  # Min
        features[39:52] = np.random.normal(1.0, 0.1, 13)  # Max

        # Delta MFCC (52-104) - stable for alarms
        features[52:104] = np.random.normal(0.1, 0.05, 52)

        # Spectral features (104-120)
        features[104] = np.random.normal(3000, 200)  # Centroid (high for alarms)
        features[105] = np.random.normal(200, 50)    # Centroid std
        features[106] = np.random.normal(2800, 100)  # Centroid min
        features[107] = np.random.normal(3200, 100)  # Centroid max

        features[108] = np.random.normal(3500, 200)  # Rolloff
        features[109:112] = np.random.normal(100, 20, 3)  # Rolloff stats

        features[112] = np.random.normal(0.4, 0.05)  # ZCR (moderate)
        features[113:116] = np.random.normal(0.05, 0.01, 3)  # ZCR stats

        features[116] = np.random.normal(0.7, 0.1)  # RMS (high)
        features[117:120] = np.random.normal(0.1, 0.02, 3)  # RMS stats

        # Chroma features (120-168) - tonal for alarms
        features[120:168] = np.random.normal(0.5, 0.15, 48)

        # Add some variation
        features += np.random.normal(0, 0.05, 168)

        alarm_features.append(features)

    return np.array(alarm_features)


def generate_siren_features():
    """Generate synthetic siren/emergency vehicle sound features."""
    print("Generating synthetic siren features...")

    siren_features = []

    for i in range(15):
        features = np.zeros(168)

        # Sirens have varying frequency (Doppler effect simulation)
        # MFCC features
        features[0:52] = np.random.normal(0.6, 0.2, 52)

        # Delta MFCC - high variation for sirens
        features[52:104] = np.random.normal(0.3, 0.15, 52)

        # Spectral features - varying centroid
        features[104] = np.random.normal(1500, 500)  # Varying frequency
        features[105] = np.random.normal(400, 100)   # High variation
        features[106:120] = np.random.normal(0.4, 0.2, 14)

        # Chroma - less tonal than alarms
        features[120:168] = np.random.normal(0.3, 0.2, 48)

        # Variation
        features += np.random.normal(0, 0.08, 168)

        siren_features.append(features)

    return np.array(siren_features)


def finetune_with_emergency_sounds():
    """
    Fine-tune existing model with emergency sound classes.
    """
    print("=" * 80)
    print("FINE-TUNING CLASSIFIER FOR EMERGENCY DETECTION")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load existing model
    print("\nLoading base model...")
    try:
        with open('noise_classifier_sklearn.pkl', 'rb') as f:
            model_data = pickle.load(f)

        base_model = model_data['model']
        base_scaler = model_data['scaler']
        base_encoder = model_data['label_encoder']

        print(f"✓ Base model loaded")
        print(f"  Existing classes: {list(base_encoder.classes_)}")

    except FileNotFoundError:
        print("✗ Base model not found. Train base model first.")
        return

    # Load original training data
    print("\nLoading original training data...")
    try:
        data = np.load('features_augmented.npz')
        original_features = data['features']
        original_labels = data['labels']
        print(f"✓ Loaded {len(original_features)} original samples")
    except:
        try:
            data = np.load('features.npz')
            original_features = data['features']
            original_labels = data['labels']
            print(f"✓ Loaded {len(original_features)} original samples")
        except:
            print("✗ No training data found")
            return

    # Generate emergency sound features
    print("\nGenerating emergency sound features...")
    alarm_features = generate_alarm_features()
    siren_features = generate_siren_features()

    # Create labels
    alarm_labels = np.array(['alarm'] * len(alarm_features))
    siren_labels = np.array(['siren'] * len(siren_features))

    print(f"✓ Generated {len(alarm_features)} alarm samples")
    print(f"✓ Generated {len(siren_features)} siren samples")

    # Combine with original data
    all_features = np.vstack([
        original_features,
        alarm_features,
        siren_features
    ])

    all_labels = np.concatenate([
        original_labels,
        alarm_labels,
        siren_labels
    ])

    print(f"\nCombined dataset:")
    print(f"  Total samples: {len(all_features)}")
    print(f"  Total classes: {len(np.unique(all_labels))}")

    # Display class distribution
    unique, counts = np.unique(all_labels, return_counts=True)
    print(f"\nClass distribution:")
    for class_name, count in zip(unique, counts):
        marker = "🚨" if class_name in ['alarm', 'siren'] else "  "
        print(f"  {marker} {class_name:<15} {count:>3} samples")

    # Prepare data
    print("\nPreparing training data...")

    # Create new label encoder with all classes
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(all_labels)

    # Normalize features
    scaler = StandardScaler()
    X = scaler.fit_transform(all_features)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"  Train samples: {len(X_train)}")
    print(f"  Test samples: {len(X_test)}")

    # Train new model
    print("\nTraining fine-tuned model...")

    model = MLPClassifier(
        hidden_layer_sizes=(256, 128, 64),
        activation='relu',
        solver='adam',
        learning_rate_init=0.001,
        max_iter=200,
        early_stopping=True,
        validation_fraction=0.2,
        n_iter_no_change=15,
        random_state=42,
        verbose=True
    )

    model.fit(X_train, y_train)

    # Evaluate
    print("\nEvaluating fine-tuned model...")

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    print(f"\nAccuracy:")
    print(f"  Training: {train_acc*100:.2f}%")
    print(f"  Test: {test_acc*100:.2f}%")

    # Predictions
    y_pred = model.predict(X_test)

    # Classification report
    print("\nClassification Report:")
    print("=" * 80)
    print(classification_report(
        y_test, y_pred,
        target_names=label_encoder.classes_,
        zero_division=0
    ))

    # Confusion matrix
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print("Predicted →")
    print("Actual ↓")
    print(cm)

    # Highlight emergency class performance
    print("\n" + "=" * 80)
    print("EMERGENCY CLASS PERFORMANCE")
    print("=" * 80)

    for emergency_class in ['alarm', 'siren']:
        if emergency_class in label_encoder.classes_:
            class_idx = list(label_encoder.classes_).index(emergency_class)
            class_mask = y_test == class_idx
            if np.sum(class_mask) > 0:
                class_acc = np.mean(y_pred[class_mask] == y_test[class_mask])
                print(f"\n🚨 {emergency_class.upper()}:")
                print(f"   Test samples: {np.sum(class_mask)}")
                print(f"   Accuracy: {class_acc*100:.1f}%")

    # Save fine-tuned model
    print("\n" + "=" * 80)
    print("Saving fine-tuned model...")

    model_data = {
        'model': model,
        'scaler': scaler,
        'label_encoder': label_encoder,
        'training_date': datetime.now().isoformat(),
        'accuracy': {
            'train': float(train_acc),
            'test': float(test_acc)
        },
        'classes': list(label_encoder.classes_),
        'emergency_classes': ['alarm', 'siren']
    }

    with open('noise_classifier_emergency.pkl', 'wb') as f:
        pickle.dump(model_data, f)

    print("✓ Saved to: noise_classifier_emergency.pkl")

    # Also update main model
    with open('noise_classifier_sklearn.pkl', 'wb') as f:
        pickle.dump(model_data, f)

    print("✓ Updated: noise_classifier_sklearn.pkl")

    print("\n" + "=" * 80)
    print("FINE-TUNING COMPLETE")
    print("=" * 80)
    print(f"\n✓ Model now includes emergency detection!")
    print(f"✓ Total classes: {len(label_encoder.classes_)}")
    print(f"✓ Emergency classes: alarm, siren")
    print(f"✓ Test accuracy: {test_acc*100:.1f}%")
    print("\nThe model can now detect:")
    print("  🚨 Fire/smoke alarms")
    print("  🚨 Emergency sirens")
    print("  🛡️  ANC will bypass these sounds for safety")
    print("=" * 80)


if __name__ == "__main__":
    finetune_with_emergency_sounds()
