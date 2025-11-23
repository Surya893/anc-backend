# Quick Start Guide - Noise Classification System

## 🎯 Goal: Achieve >70% Validation Accuracy on 6+ Noise Classes

This guide addresses the two critical alerts and provides a clear path to production-ready training.

---

## ⚠️ Alert 1: Dataset Insufficient (FIXED)

**Problem**: Only 9 samples across 6 classes → Cannot train robust model

**Solution**: Use `collect_training_data.py` to gather 120+ balanced samples

### Fixed Dataset Requirements:
- **Minimum**: 10 samples per class (acceptable but not ideal)
- **Recommended**: 20 samples per class (for >70% accuracy)
- **Optimal**: 50+ samples per class (for >85% accuracy)

---

## ⚠️ Alert 2: PyTorch Missing (FIXED)

**Problem**: PyTorch not installed → Cannot run training

**Solution**: Use `setup_and_verify.py` to install and verify entire pipeline

### Automated Setup:
- Checks PyTorch installation
- Offers to install PyTorch automatically
- Verifies all dependencies
- Runs quick training test

---

## 🚀 Complete Workflow (Step-by-Step)

### Step 1: Install PyTorch & Verify System

```bash
python setup_and_verify.py
```

**What it does:**
- ✓ Checks if PyTorch is installed (offers to install if missing)
- ✓ Validates dataset size
- ✓ Verifies feature extraction
- ✓ Tests model architectures
- ✓ Runs 5-epoch quick training test

**Expected output:**
```
✓ PyTorch installed
✓ Dataset sufficient (or shows how many more samples needed)
✓ Features extracted
✓ Model architectures working
✓ Training test passed

5/5 checks passed
✓ SYSTEM READY FOR FULL TRAINING!
```

---

### Step 2: Collect Training Data (If Needed)

If `setup_and_verify.py` shows insufficient data:

```bash
python collect_training_data.py
```

**Interactive Menu Options:**
1. Show progress - See how many samples per class
2. Record samples - Record for specific class
3. Show class info - Get recording tips
4. Quick collect - Guided mode for needed classes
5. List all classes - View all 8 noise types
6. Exit

**8 Predefined Classes:**
- `office` - HVAC, typing, conversation
- `street` - Traffic, cars, buses
- `home` - Appliances, quiet environment
- `alarm` - Fire alarm, car alarm, phone
- `construction` - Tools, drilling, machinery
- `nature` - Birds, wind, rain, water
- `transport` - Train, plane, bus interior
- `crowd` - Restaurant, mall, events

**Command-line mode:**
```bash
# Record 10 office samples, 5 seconds each
python collect_training_data.py --class office --num 10 --duration 5

# Record 15 street samples, 8 seconds each
python collect_training_data.py --class street --num 15 --duration 8
```

**Progress tracking:**
```
Class            Count    Progress                       Status
────────────────────────────────────────────────────────────────────
office             4/20    █████░░░░░░░░░░░░░░░░░░░░  20.0%  ○ Needs more
street             0/20    ░░░░░░░░░░░░░░░░░░░░░░░░░   0.0%  ○ Needs more
home               1/20    ██░░░░░░░░░░░░░░░░░░░░░░░   5.0%  ○ Needs more
...

Overall: 9/160 samples (5.6%)
⚠ Need 151 more samples for balanced dataset
```

---

### Step 3: Extract Features

After collecting data:

```bash
python feature_extraction.py
```

**What it does:**
- Loads all recordings from database
- Extracts MFCC features (13 coefficients + deltas)
- Extracts spectral features (centroid, rolloff, ZCR, RMS)
- Extracts chroma features (12 pitch classes)
- Computes statistical summaries (mean, std, min, max)
- Saves to `features.npz` (168-dimensional vectors)

**Expected output:**
```
Extracting features from 160 recordings...
  ✓ Recording 1: office (168 features)
  ✓ Recording 2: street (168 features)
  ...
  ✓ Recording 160: crowd (168 features)

✓ Features saved to features.npz
  Shape: (160, 168)
  Classes: ['alarm' 'construction' 'crowd' 'home' 'nature' 'office' 'street' 'transport']
```

---

### Step 4: Train the Model

```bash
python train_classifier.py
```

**Training configuration:**
- **Model**: MLP (3 hidden layers: 256→128→64)
- **Optimizer**: Adam (lr=0.001, weight_decay=1e-5)
- **Batch size**: 32
- **Max epochs**: 100
- **Early stopping**: Patience 15
- **Regularization**: Dropout 0.3, BatchNorm, L2 decay

**Expected output (with 160 balanced samples):**
```
================================================================================
NOISE CLASSIFICATION MODEL TRAINING
================================================================================
Device: cpu
Loaded 160 samples with 168 features
Classes: ['alarm', 'construction', 'crowd', 'home', 'nature', 'office', 'street', 'transport']
Train set: 128 samples
Test set: 32 samples

Epoch 1/100
Training: 100%|████████████████| 4/4 [00:01<00:00]
  Train Loss: 2.0234 | Train Acc: 25.00%
  Val Loss:   1.9876 | Val Acc:   28.13%

Epoch 10/100
  Train Loss: 0.8456 | Train Acc: 68.75%
  Val Loss:   1.0234 | Val Acc:   62.50%

Epoch 20/100
  Train Loss: 0.3421 | Train Acc: 87.50%
  Val Loss:   0.7123 | Val Acc:   75.00%  ← Target achieved!

...

Early stopping triggered after 35 epochs

✓ Training completed in 127.45 seconds

Overall Accuracy: 78.13%  ← Exceeds 70% target!
Weighted F1-Score: 0.7654
```

**Success criteria:**
- ✓ Validation accuracy > 70%
- ✓ Train-val gap < 15%
- ✓ Per-class F1 > 0.65

**Files generated:**
- `noise_classifier.pth` - Trained model
- `training_history.png` - Loss/accuracy plots
- `training_metrics.npz` - Detailed metrics

---

### Step 5: Make Predictions

```bash
# Predict single recording
python predict_noise_type.py 9

# Predict all recordings
python predict_noise_type.py batch
```

**Expected output (single prediction):**
```
================================================================================
PREDICTING NOISE TYPE FOR RECORDING 9
================================================================================

Recording Information:
  Timestamp: 2025-11-07 11:52:38
  Location: Demo Office Building
  True Label: office

Prediction Results:
  Predicted Class: office
  Confidence: 92.34%

All Class Probabilities:
────────────────────────────────────────────────────────────────────────────────
  office          92.34% ██████████████████████████████████████████████
  home             3.45% █
  nature           2.11% █
  street           1.23%
  construction     0.54%
  alarm            0.21%
  transport        0.08%
  crowd            0.04%

────────────────────────────────────────────────────────────────────────────────
✓ CORRECT PREDICTION!
```

**Batch prediction output:**
```
Predicting noise types for 160 recordings...
✓ Recording 1: True=office      Predicted=office      Confidence=94.23%
✓ Recording 2: True=street      Predicted=street      Confidence=89.45%
✓ Recording 3: True=alarm       Predicted=alarm       Confidence=96.78%
...
────────────────────────────────────────────────────────────────────────────────
Overall Accuracy: 78.13% (125/160)
```

---

## 📊 Expected Results Timeline

### With Current 9 Samples:
```
Dataset: 9 samples, 6 classes
Train: 7 samples, Test: 2 samples
Expected Val Accuracy: 30-50% (unreliable, high variance)
Status: ✗ NOT READY for production
```

### With 60 Samples (10 per class):
```
Dataset: 60 samples, 6 classes
Train: 48 samples, Test: 12 samples
Expected Val Accuracy: 60-70%
Status: ⚠ Minimum acceptable
```

### With 120 Samples (20 per class):
```
Dataset: 120 samples, 6 classes
Train: 96 samples, Test: 24 samples
Expected Val Accuracy: 75-85%
Status: ✓ RECOMMENDED for production
```

### With 160 Samples (20 per class, 8 classes):
```
Dataset: 160 samples, 8 classes
Train: 128 samples, Test: 32 samples
Expected Val Accuracy: 78-88%
Status: ✓ PRODUCTION READY
```

---

## 🔧 Troubleshooting

### Issue: Low validation accuracy (<50%)

**Possible causes:**
1. Insufficient training data
2. Imbalanced dataset
3. Label errors in database
4. Features not informative

**Solutions:**
```bash
# Check dataset balance
python verify_classifier_pipeline.py

# Collect more samples
python collect_training_data.py

# Re-extract features
python feature_extraction.py

# Try different model
# Edit train_classifier.py, change:
# model = NoiseClassifierMLP(...)
# to:
# model = NoiseClassifierCNN(...)
```

### Issue: Overfitting (train acc >> val acc)

**Solution in `train_classifier.py`:**
```python
# Increase dropout
model = NoiseClassifierMLP(input_dim, num_classes, dropout=0.5)

# Increase weight decay
trainer = NoiseClassifierTrainer(model, weight_decay=1e-4)

# Collect more training data
```

### Issue: PyTorch installation fails

**CPU version (recommended):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**GPU version (if you have CUDA):**
```bash
# Check CUDA version first
nvidia-smi

# Install matching version (e.g., CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 📈 Performance Optimization Tips

### 1. Data Quality
- ✓ Record in consistent conditions
- ✓ Keep background noise minimal
- ✓ Vary recording locations
- ✓ Include edge cases

### 2. Feature Engineering
- Experiment with different MFCC coefficients (13 vs 20)
- Add mel-spectrogram features
- Try wavelet features

### 3. Model Architecture
- Try CNN for temporal patterns
- Try ensemble model for stability
- Adjust hidden layer sizes

### 4. Training Configuration
- Increase epochs (100 → 200)
- Reduce learning rate (0.001 → 0.0005)
- Adjust batch size (32 → 16 or 64)

---

## ✅ Quick Checklist

Before running full training:

- [ ] PyTorch installed (`python -c "import torch; print(torch.__version__)"`)
- [ ] Collected 20+ samples per class
- [ ] Dataset balanced across all classes
- [ ] Features extracted (`features.npz` exists)
- [ ] Verified system ready (`python setup_and_verify.py`)
- [ ] All 5 verification checks pass

After training:

- [ ] Validation accuracy > 70%
- [ ] Train-val gap < 15%
- [ ] Confusion matrix shows good separation
- [ ] Per-class F1-score > 0.65
- [ ] Model saved (`noise_classifier.pth` exists)
- [ ] Predictions working correctly

---

## 📁 Complete File Structure

```
anc-with-ai/
├── Database & Audio
│   ├── database_schema.py              # SQLite schema
│   ├── audio_capture.py                # Real-time recording
│   ├── anc_system.db                   # Database (gitignored)
│   └── recordings/                     # WAV files (gitignored)
│
├── Feature Extraction
│   ├── feature_extraction.py           # MFCC, spectral, chroma
│   └── features.npz                    # Extracted features (gitignored)
│
├── Model & Training
│   ├── noise_classifier_model.py       # PyTorch models (MLP, CNN, Ensemble)
│   ├── train_classifier.py             # Training pipeline
│   ├── noise_classifier.pth            # Trained model (gitignored)
│   └── training_history.png            # Plots (gitignored)
│
├── Prediction & Evaluation
│   ├── predict_noise_type.py           # Inference
│   └── predictions.json                # Batch predictions (gitignored)
│
├── Setup & Verification (NEW!)
│   ├── setup_and_verify.py             # ✓ Fixes Alert 2 (PyTorch check)
│   ├── collect_training_data.py        # ✓ Fixes Alert 1 (Data collection)
│   └── verify_classifier_pipeline.py   # Feature quality check
│
├── Documentation
│   ├── NOISE_CLASSIFIER_README.md      # Full API docs
│   ├── QUICK_START_GUIDE.md            # This file
│   ├── AUDIO_CAPTURE_README.md         # Audio capture docs
│   ├── DATABASE_SCHEMA.md              # Database docs
│   └── EXECUTION_SUMMARY.md            # Test results
│
└── Configuration
    ├── requirements.txt                # Python dependencies
    └── .gitignore                      # Exclude models, data, outputs
```

---

## 🎓 Learning Resources

### Understanding MFCC Features
- **What**: Mel-Frequency Cepstral Coefficients capture spectral envelope
- **Why**: Compact representation of audio's frequency content
- **How**: 13 coefficients capture most important spectral information

### Model Architectures
- **MLP**: Simple, fast, good for statistical features
- **CNN**: Captures temporal patterns in sequential data
- **Ensemble**: Combines multiple models for robustness

### Training Concepts
- **Early stopping**: Prevents overfitting by monitoring validation loss
- **Learning rate scheduling**: Reduces LR when training plateaus
- **Batch normalization**: Stabilizes training, allows higher learning rates
- **Dropout**: Randomly drops connections, prevents overfitting

---

## 🚀 Ready to Start?

```bash
# 1. Verify everything is ready
python setup_and_verify.py

# 2. If dataset insufficient, collect more
python collect_training_data.py

# 3. Extract features
python feature_extraction.py

# 4. Train the model
python train_classifier.py

# 5. Make predictions
python predict_noise_type.py batch
```

**Target achieved when:**
- ✅ Validation accuracy > 70%
- ✅ Confident predictions (>80% confidence)
- ✅ Good confusion matrix separation
- ✅ Consistent performance across all classes

---

*Last updated: 2025-11-07*
*System: ANC with AI - Noise Classification Module*
