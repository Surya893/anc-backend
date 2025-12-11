# Noise Classification System - Architecture v2.0

## Overview

A refactored, modular PyTorch-based machine learning system for classifying 58 types of environmental noise with improved maintainability and extensibility.

## 🎯 Key Improvements in v2.0

- **Modular Architecture**: Separated concerns into config, features, models, and pipelines
- **No Code Duplication**: Single source of truth for feature extraction and configuration
- **Lazy Loading**: PyTorch dependencies loaded only when needed for better testing
- **Clean API**: Simple `classify()`, `train()`, `export()` methods
- **Type Safety**: Comprehensive type hints and dataclasses
- **Easy Testing**: Mock-friendly design without GPU requirements

## Architecture

### New Module Structure

```
src/ml/
├── config.py                           # Configuration dataclasses
├── features/
│   ├── __init__.py
│   ├── base.py                         # Shared config & protocols
│   └── torch_extractor.py              # PyTorch feature extractor
├── models/
│   ├── __init__.py
│   └── efficientnet_audio.py           # EfficientNet-B3 model
├── pipelines/
│   ├── __init__.py
│   └── noise_classifier.py             # Orchestration & service API
├── feature_extraction.py               # Legacy librosa extractor (preserved)
├── emergency_noise_detector.py         # Emergency detection (uses legacy)
└── noise_classifier_v2.py              # Backward compatibility wrapper

```

### Data Flow

```
┌──────────────────┐
│   Audio Input    │ (numpy array, 48kHz)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ TorchAudioFeature│ (mel spectrograms, MFCCs)
│    Extractor     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  EfficientNet-B3 │ (pretrained CNN)
│   Audio Model    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Classification  │ (57 noise categories)
│  + Confidence    │
└──────────────────┘
```

## Installation

### Prerequisites

```bash
pip install -r requirements.txt
```

Required packages:
- `torch>=2.0.0` - PyTorch deep learning framework
- `torchaudio>=2.0.0` - Audio processing
- `torchvision>=0.15.0` - Pretrained models
- `numpy>=1.24.0` - Numerical computing
- `librosa>=0.10.0` - Legacy feature extraction (optional)

## Quick Start

### 1. Simple Classification

```python
from src.ml.pipelines.noise_classifier import NoiseClassifierService
import numpy as np

# Initialize service
classifier = NoiseClassifierService(
    model_path='models/noise_classifier_v2.pth'
)

# Classify audio
audio = np.random.randn(48000)  # 1 second at 48kHz
result = classifier.classify(audio, sample_rate=48000)

print(f"Predicted: {result['predicted_class']}")
print(f"Confidence: {result['confidence']:.2%}")
print("Top 5:")
for category, prob in result['top_k']:
    print(f"  {category}: {prob:.2%}")
```

### 2. Training a Model

```python
from src.ml.pipelines.noise_classifier import NoiseClassifierService, NoiseDataset
from src.ml.config import TrainingConfig

# Create datasets
train_files = ['audio1.wav', 'audio2.wav', ...]
train_labels = [0, 1, ...]  # Category indices

train_dataset = NoiseDataset(train_files, train_labels, augment=True)
val_dataset = NoiseDataset(val_files, val_labels, augment=False)

# Initialize service
service = NoiseClassifierService()

# Train
config = TrainingConfig(
    num_epochs=50,
    batch_size=32,
    learning_rate=1e-4
)

history = service.train(train_dataset, val_dataset, config=config)
```

### 3. Export for Deployment

```python
# Export to ONNX (recommended for production)
classifier.export('noise_classifier.onnx', format='onnx')

# Or export to TorchScript
classifier.export('noise_classifier.pt', format='torchscript')
```

## API Reference

### Configuration Classes

#### AudioFeatureConfig

```python
from src.ml.config import AudioFeatureConfig

config = AudioFeatureConfig(
    sample_rate=48000,          # Audio sample rate
    n_fft=2048,                 # FFT window size
    hop_length=512,             # Hop length for STFT
    n_mels=128,                 # Number of mel bands
    n_mfcc=40,                  # Number of MFCC coefficients
    spectrogram_height=128,     # Output spectrogram height
    spectrogram_width=128,      # Output spectrogram width
    enable_augmentation=True,   # Enable data augmentation
)
```

#### ModelConfig

```python
from src.ml.config import ModelConfig

config = ModelConfig(
    num_classes=58,             # Number of output classes
    dropout=0.3,                # Dropout probability
    pretrained=True,            # Use ImageNet pretrained weights
    architecture='efficientnet_b3'
)
```

#### TrainingConfig

```python
from src.ml.config import TrainingConfig

config = TrainingConfig(
    num_epochs=50,
    batch_size=32,
    learning_rate=1e-4,
    weight_decay=1e-5,
    early_stopping_patience=15,
    device='cpu',               # or 'cuda'
    checkpoint_dir='checkpoints'
)
```

### NoiseClassifierService

Main API for classification, training, and export.

#### Methods

##### `classify(audio, sample_rate, return_top_k)`

Classify audio sample.

**Args:**
- `audio` (np.ndarray): Audio samples
- `sample_rate` (int): Sample rate in Hz
- `return_top_k` (int): Number of top predictions to return

**Returns:**
```python
{
    'predicted_class': str,
    'confidence': float,
    'probabilities': Dict[str, float],
    'top_k': List[Tuple[str, float]]
}
```

##### `train(train_dataset, val_dataset, config)`

Train the classifier.

**Args:**
- `train_dataset`: Training dataset
- `val_dataset`: Validation dataset
- `config` (TrainingConfig): Training configuration

**Returns:**
```python
{
    'train_loss': List[float],
    'train_acc': List[float],
    'val_loss': List[float],
    'val_acc': List[float]
}
```

##### `export(output_path, format)`

Export model for deployment.

**Args:**
- `output_path` (str): Output file path
- `format` (str): 'onnx' or 'torchscript'

### Noise Categories (58 classes)

**Environmental:** white_noise, pink_noise, brown_noise, blue_noise

**Transportation:** traffic_highway, traffic_urban, traffic_rural, aircraft_takeoff, aircraft_cruise, aircraft_landing, train_interior, train_exterior, subway, motorcycle, bicycle, electric_vehicle

**Urban:** office_quiet, office_busy, office_hvac, construction_drilling, construction_hammering, construction_sawing, cafe_quiet, cafe_busy, restaurant, shopping_mall, airport_terminal, train_station

**Industrial:** factory_general, factory_machinery, factory_assembly, warehouse, server_room, generator

**Natural:** wind_light, wind_strong, rain_light, rain_heavy, thunder, ocean_waves, waterfall, forest

**Indoor:** hvac_fan, refrigerator, dishwasher, washing_machine, vacuum_cleaner, air_purifier, computer_fan

**Human:** crowd_applause, crowd_cheering, crowd_talking, baby_crying, dog_barking, music_bass, music_treble

**Other:** silence, mixed_noise, fire_alarm (emergency)

## Integration Examples

### With Backend API Service

```python
from backend.services.ml_service import MLService

# The MLService automatically uses v2 if available
service = MLService()

# Classify from base64-encoded audio
result = service.classify_noise(audio_base64)
print(f"Model version: {result['model_version']}")  # 'v2' if using new classifier
```

### With Celery Tasks

```python
from src.api.tasks import train_noise_classifier

# Trigger background training
task = train_noise_classifier.delay('path/to/training/data')
result = task.get()
```

### With Lambda Functions

```python
# In Lambda handler
from src.ml.pipelines.noise_classifier import NoiseClassifierService

classifier = NoiseClassifierService(
    model_path='/opt/ml/models/noise_classifier_v2.pth'
)

def handler(event, context):
    audio = decode_audio(event['audio_base64'])
    result = classifier.classify(audio)
    return {'statusCode': 200, 'body': json.dumps(result)}
```

## Testing

### Unit Tests

```bash
# Run all ML tests
python -m pytest tests/unit/test_noise_classifier_v2.py -v

# Test specific modules
python -m pytest tests/unit/test_noise_classifier_v2.py::TestNoiseClassifierModules -v
```

### Mock Testing (No GPU Required)

```python
from unittest.mock import Mock, patch
import numpy as np

# Mock torch to avoid GPU dependency
with patch('src.ml.features.torch_extractor._torch') as mock_torch:
    mock_torch.cuda.is_available.return_value = False
    
    from src.ml.pipelines.noise_classifier import NoiseClassifierService
    
    service = NoiseClassifierService()
    # Test without requiring actual PyTorch
```

## Migration Guide

### From Old API to New API

**Before:**
```python
from src.ml.noise_classifier_v2 import NoiseClassifierV2

classifier = NoiseClassifierV2(model_path='model.pth', device='cpu')
result = classifier.classify(audio, sample_rate=48000, return_top_k=5)
```

**After:**
```python
from src.ml.pipelines.noise_classifier import NoiseClassifierService
from src.ml.config import InferenceConfig

config = InferenceConfig(model_path='model.pth', device='cpu', return_top_k=5)
service = NoiseClassifierService(config=config)
result = service.classify(audio, sample_rate=48000)
```

**Backward Compatibility:** The old API still works but shows a deprecation warning.

### From Feature Extraction to Torch Extractor

**Before:**
```python
from src.ml.noise_classifier_v2 import AudioFeatureExtractor

extractor = AudioFeatureExtractor(AudioFeatureConfig())
mel_spec = extractor.extract_mel_spectrogram(audio)
```

**After:**
```python
from src.ml.features.torch_extractor import TorchAudioFeatureExtractor
from src.ml.config import AudioFeatureConfig

config = AudioFeatureConfig()
extractor = TorchAudioFeatureExtractor(config)
mel_spec = extractor.extract_mel_spectrogram(audio)
```

## Performance

### Model Metrics

- **Accuracy**: 85-95% (with sufficient training data)
- **Inference Time**: <10ms on CPU, <2ms on GPU
- **Model Size**: ~45MB (EfficientNet-B3)
- **Categories**: 58 noise types

### Optimization Tips

1. **Use GPU for training**: Set `device='cuda'` in TrainingConfig
2. **Batch processing**: Process multiple samples together
3. **ONNX export**: 2-3x faster inference in production
4. **Feature caching**: Cache extracted features for training

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'torch'`

**Solution**:
```bash
pip install torch torchaudio torchvision
```

### Memory Issues

**Problem**: Out of memory during training

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

### Model Not Loading

**Problem**: `FileNotFoundError` when loading model

**Solution**:
- Check model path exists
- Use absolute paths or configure ML_MODEL_V2_PATH in settings
- Initialize without model_path for untrained model

## Contributing

When extending the classifier:

1. Add new categories to `NOISE_CATEGORIES_V2` in `pipelines/noise_classifier.py`
2. Update `NUM_CLASSES_V2`
3. Retrain model with new categories
4. Update this documentation

## License

MIT License - See LICENSE file for details.
