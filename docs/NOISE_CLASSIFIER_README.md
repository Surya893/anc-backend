# Noise Classification System with PyTorch

## Overview

A comprehensive PyTorch-based machine learning system for classifying different types of environmental noise (traffic, alarms, office, etc.) using audio features extracted from stored noise recordings.

## Features

- **MFCC Feature Extraction**: Mel-Frequency Cepstral Coefficients and derivatives
- **Multi-Feature Analysis**: Spectral, temporal, and chroma features
- **Multiple Model Architectures**: MLP, CNN, and Ensemble models
- **Complete Training Pipeline**: Training, validation, early stopping, and learning rate scheduling
- **Comprehensive Evaluation**: Precision, recall, F1-score, confusion matrix
- **Real-time Prediction**: Classify new recordings or database entries
- **Database Integration**: Seamless integration with existing noise database

## Architecture

```
┌──────────────────┐
│   Audio Data     │ (Database or WAV files)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│Feature Extraction│ (MFCC, Spectral, Chroma)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Preprocessing   │ (Normalization, Scaling)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Neural Network  │ (MLP/CNN/Ensemble)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Classification  │ (Noise Type Prediction)
└──────────────────┘
```

## Installation

### Prerequisites

```bash
pip install -r requirements.txt
```

Required packages:
- `torch>=2.0.0` - PyTorch deep learning framework
- `librosa>=0.10.0` - Audio feature extraction
- `scikit-learn>=1.0.0` - Preprocessing and metrics
- `tqdm>=4.65.0` - Progress bars
- `numpy`, `matplotlib` - Data processing and visualization

## Quick Start

### 1. Extract Features from Database

```bash
python feature_extraction.py
```

This will:
- Load all recordings from the database
- Extract MFCC, spectral, and chroma features
- Save features to `features.npz`

### 2. Train the Model

```bash
python train_classifier.py
```

This will:
- Load extracted features
- Split into train/test sets
- Train a neural network classifier
- Evaluate and save the model
- Generate training history plots

### 3. Make Predictions

```bash
# Predict single recording
python predict_noise_type.py 9

# Predict all recordings
python predict_noise_type.py batch
```

## Module Documentation

### 1. feature_extraction.py

Extracts audio features for classification.

#### AudioFeatureExtractor Class

```python
from feature_extraction import AudioFeatureExtractor

extractor = AudioFeatureExtractor(
    sample_rate=44100,
    n_mfcc=13,
    n_fft=2048,
    hop_length=512
)

# Extract MFCC features
mfccs = extractor.extract_mfcc(audio_data)

# Extract all features
features = extractor.extract_all_features(audio_data)

# Get fixed-length feature vector
feature_vector = extractor.extract_feature_vector(audio_data)
```

#### Features Extracted

1. **MFCC** (13 coefficients)
   - Mel-frequency cepstral coefficients
   - Delta MFCC (first derivative)

2. **Spectral Features**
   - Spectral centroid
   - Spectral rolloff
   - Zero crossing rate
   - RMS energy

3. **Chroma Features** (12 pitch classes)
   - Pitch class profiles

4. **Statistical Summaries**
   - Mean, std, min, max for each feature
   - Creates fixed-length vector (~200 dimensions)

#### Batch Feature Extraction

```python
from feature_extraction import batch_extract_features

data = batch_extract_features(
    db_path="anc_system.db",
    output_file="features.npz"
)

# Returns: {'features': array, 'labels': array, 'recording_ids': array}
```

### 2. noise_classifier_model.py

PyTorch model architectures and dataset loaders.

#### Model Architectures

##### MLP (Multi-Layer Perceptron)

```python
from noise_classifier_model import NoiseClassifierMLP

model = NoiseClassifierMLP(
    input_dim=200,
    num_classes=5,
    hidden_dims=[256, 128, 64],
    dropout=0.3
)
```

Architecture:
```
Input (200) → Linear(256) → BatchNorm → ReLU → Dropout
           → Linear(128) → BatchNorm → ReLU → Dropout
           → Linear(64)  → BatchNorm → ReLU → Dropout
           → Linear(5)   → Output
```

##### CNN (1D Convolutional Network)

```python
from noise_classifier_model import NoiseClassifierCNN

model = NoiseClassifierCNN(
    input_dim=200,
    num_classes=5,
    num_channels=[64, 128, 256],
    kernel_size=3,
    dropout=0.3
)
```

Architecture:
```
Input (200) → Conv1d → BatchNorm → ReLU → MaxPool → Dropout
           → Conv1d → BatchNorm → ReLU → MaxPool → Dropout
           → Conv1d → BatchNorm → ReLU → MaxPool → Dropout
           → Flatten → FC(128) → ReLU → Dropout
           → FC(5) → Output
```

##### Ensemble

```python
from noise_classifier_model import NoiseClassifierEnsemble

model = NoiseClassifierEnsemble(
    input_dim=200,
    num_classes=5,
    num_models=3
)
```

Combines predictions from multiple MLP models.

#### Dataset and DataLoader

```python
from noise_classifier_model import create_data_loaders

train_loader, test_loader, train_dataset, test_dataset = create_data_loaders(
    features_file='features.npz',
    batch_size=32,
    test_size=0.2,
    random_state=42
)
```

### 3. train_classifier.py

Training pipeline with evaluation.

#### NoiseClassifierTrainer Class

```python
from train_classifier import NoiseClassifierTrainer

trainer = NoiseClassifierTrainer(
    model=model,
    device='cpu',  # or 'cuda'
    learning_rate=0.001,
    weight_decay=1e-5
)

# Train model
history = trainer.train(
    train_loader=train_loader,
    val_loader=test_loader,
    epochs=100,
    early_stopping_patience=15
)

# Detailed evaluation
metrics = trainer.evaluate_detailed(test_loader, label_encoder)

# Plot training history
trainer.plot_training_history('training_history.png')
```

#### Training Features

- **Early Stopping**: Stops training when validation loss stops improving
- **Learning Rate Scheduling**: Reduces LR when validation loss plateaus
- **Batch Normalization**: Stabilizes training
- **Dropout**: Prevents overfitting
- **L2 Regularization**: Weight decay for regularization

#### Evaluation Metrics

- Overall accuracy
- Per-class precision, recall, F1-score
- Confusion matrix
- Support (samples per class)

### 4. predict_noise_type.py

Inference and prediction on new data.

#### NoisePredictor Class

```python
from predict_noise_type import NoisePredictor

predictor = NoisePredictor(
    model_path='noise_classifier.pth',
    device='cpu'
)

# Predict from audio data
predicted_class, confidence, all_probs = predictor.predict_from_audio(audio_data)

# Predict from WAV file
predicted_class, confidence, all_probs = predictor.predict_from_file('recording.wav')

# Predict from database
db = ANCDatabase('anc_system.db')
predicted_class, confidence, all_probs = predictor.predict_from_database(db, recording_id=9)
```

#### Batch Prediction

```python
predictions = predictor.batch_predict_database('anc_system.db')

# Returns list of:
# {
#   'recording_id': int,
#   'true_label': str,
#   'predicted_label': str,
#   'confidence': float,
#   'probabilities': dict
# }
```

## Usage Examples

### Example 1: Complete Workflow

```python
# Step 1: Extract features
from feature_extraction import batch_extract_features
data = batch_extract_features()

# Step 2: Create model and train
from noise_classifier_model import NoiseClassifierMLP, create_data_loaders
from train_classifier import NoiseClassifierTrainer

train_loader, test_loader, train_dataset, test_dataset = create_data_loaders()

model = NoiseClassifierMLP(
    input_dim=train_dataset.get_feature_dim(),
    num_classes=train_dataset.get_num_classes()
)

trainer = NoiseClassifierTrainer(model)
history = trainer.train(train_loader, test_loader, epochs=50)

# Step 3: Evaluate
metrics = trainer.evaluate_detailed(test_loader, train_dataset.label_encoder)

# Step 4: Save model
from noise_classifier_model import save_model
save_model(model, train_dataset.label_encoder, train_dataset.scaler)

# Step 5: Make predictions
from predict_noise_type import NoisePredictor
predictor = NoisePredictor()
predictor.batch_predict_database()
```

### Example 2: Classify New Recording

```python
from audio_capture import AudioCapture
from predict_noise_type import NoisePredictor
from database_schema import ANCDatabase

# Capture new audio
capture = AudioCapture()
capture.start_recording(duration_seconds=5)
recording_id = capture.save_to_database(
    environment_type="unknown",
    description="New recording to classify"
)
audio_data = capture.get_audio_array()
capture.cleanup()

# Predict
predictor = NoisePredictor()
predicted_class, confidence, all_probs = predictor.predict_from_audio(audio_data)

print(f"Predicted: {predicted_class} (confidence: {confidence:.2%})")
for class_name, prob in sorted(all_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"  {class_name}: {prob:.2%}")
```

### Example 3: Custom Feature Extraction

```python
from feature_extraction import AudioFeatureExtractor
import numpy as np

extractor = AudioFeatureExtractor()

# Extract specific features
audio_data = np.random.randn(44100)  # 1 second at 44.1kHz

# MFCC only
mfccs = extractor.extract_mfcc(audio_data)
print(f"MFCC shape: {mfccs.shape}")  # (13, time_frames)

# MFCC + Delta
mfccs, delta_mfccs = extractor.extract_mfcc_delta(audio_data)

# Spectral features
spectral_features = extractor.extract_spectral_features(audio_data)
for name, feat in spectral_features.items():
    print(f"{name}: {feat.shape}")

# All features as fixed vector
feature_vector = extractor.extract_feature_vector(audio_data)
print(f"Feature vector length: {len(feature_vector)}")
```

## Model Performance

### Expected Results

With sufficient training data (50+ samples per class):

- **Accuracy**: 85-95%
- **Training time**: 2-5 minutes (CPU)
- **Inference time**: < 10ms per recording

### Improving Performance

1. **More training data**: Collect more diverse samples per environment
2. **Data augmentation**: Add noise, pitch shift, time stretch
3. **Feature engineering**: Experiment with different features
4. **Model architecture**: Try CNN or ensemble models
5. **Hyperparameter tuning**: Adjust learning rate, dropout, hidden layers

## File Outputs

After running the complete pipeline:

```
anc-with-ai/
├── features.npz                 # Extracted features
├── noise_classifier.pth         # Trained model
├── training_history.png         # Training plots
├── training_metrics.npz         # Evaluation metrics
└── predictions.json             # Batch predictions
```

## Troubleshooting

### Issue: Low accuracy

**Solution**:
- Collect more training samples (aim for 20+ per class)
- Ensure balanced dataset
- Check for label errors in database

### Issue: Overfitting (train acc >> val acc)

**Solution**:
- Increase dropout (try 0.4-0.5)
- Increase weight decay (try 1e-4)
- Reduce model complexity
- Add more training data

### Issue: Underfitting (both acc low)

**Solution**:
- Increase model capacity (more/larger hidden layers)
- Train for more epochs
- Reduce regularization
- Check if features are informative

### Issue: PyTorch not available

**Solution**:
```bash
# CPU version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# CUDA version (for GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Issue: librosa import error

**Solution**:
```bash
pip install librosa soundfile
```

## Integration with ANC System

The noise classifier can be integrated with the ANC system for adaptive noise cancellation:

```python
from anc_with_database import OpenAirNoiseCancellationDB
from predict_noise_type import NoisePredictor

# Classify noise type
predictor = NoisePredictor()
noise_type, confidence, _ = predictor.predict_from_file('ambient.wav')

# Load appropriate ANC model for that noise type
anc = OpenAirNoiseCancellationDB()
anc.load_noise_profile(noise_type)  # Custom method to load profile

# Process with optimized parameters
noise_cancelled = anc.cancel_noise(input_signal)
```

## Integration with Flask Blueprint Architecture

The noise classifier is now integrated with the refactored Flask blueprint API:

### Using the MLService

```python
from backend.services.ml_service import MLService

# Initialize the ML service
ml_service = MLService()

# Classify noise from audio data
result = ml_service.classify_noise(
    audio_data=base64_encoded_audio,
    sample_rate=48000
)

# Result structure:
# {
#     'noise_type': 'office',           # Predicted noise class
#     'confidence': 0.95,               # Confidence score
#     'all_predictions': {              # All class probabilities
#         'office': 0.95,
#         'traffic': 0.03,
#         'music': 0.02
#     }
# }
```

### Flask API Endpoint

The classifier is exposed via the Flask blueprint API:

```bash
# Classify noise type
curl -X POST http://localhost:5000/api/audio/classify \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64encodedaudio",
    "sample_rate": 48000
  }'
```

### Testing the Classifier

The test suite includes comprehensive tests for the classifier:

```bash
# Run classifier tests
pytest tests/unit/test_flask_blueprints.py::TestAudioBlueprint::test_classify_noise_success -v

# Run ML service tests
pytest -m ml
```

## Advanced Usage

### Custom Model Architecture

```python
import torch.nn as nn

class CustomNoiseClassifier(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

        self.network = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        return self.network(x)

# Use with trainer
model = CustomNoiseClassifier(200, 5)
trainer = NoiseClassifierTrainer(model)
```

### Feature Selection

```python
from sklearn.feature_selection import SelectKBest, f_classif

# Select top K features
selector = SelectKBest(f_classif, k=100)
X_selected = selector.fit_transform(features, labels)

# Get selected feature indices
selected_indices = selector.get_support(indices=True)
```

## References

- **MFCC**: Davis & Mermelstein (1980) - "Comparison of parametric representations for monosyllabic word recognition"
- **Librosa**: McFee et al. (2015) - "librosa: Audio and Music Signal Analysis in Python"
- **PyTorch**: Paszke et al. (2019) - "PyTorch: An Imperative Style, High-Performance Deep Learning Library"

## License

Part of the ANC system patent implementation.

## Support

For issues or questions, refer to:
- Feature extraction: `feature_extraction.py`
- Model architecture: `noise_classifier_model.py`
- Training: `train_classifier.py`
- Prediction: `predict_noise_type.py`
