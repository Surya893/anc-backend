"""
Noise Classifier Pipeline
Orchestration for training, inference, and export
"""

import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ..config import AudioFeatureConfig, ModelConfig, TrainingConfig, InferenceConfig
from ..features.torch_extractor import TorchAudioFeatureExtractor
from ..models.efficientnet_audio import (
    EfficientNetAudioClassifier,
    load_model_weights,
    save_model_checkpoint
)

logger = logging.getLogger(__name__)

# Lazy imports
_torch = None
_nn = None
_F = None
_T = None
_DataLoader = None
_Dataset = None


def _ensure_torch():
    """Lazy load torch dependencies"""
    global _torch, _nn, _F, _T, _DataLoader, _Dataset
    if _torch is None:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        import torchaudio.transforms as T
        from torch.utils.data import Dataset, DataLoader
        _torch = torch
        _nn = nn
        _F = F
        _T = T
        _Dataset = Dataset
        _DataLoader = DataLoader


# 50+ Noise Categories (v2.0)
NOISE_CATEGORIES_V2 = [
    # Environmental
    'white_noise', 'pink_noise', 'brown_noise', 'blue_noise',

    # Transportation
    'traffic_highway', 'traffic_urban', 'traffic_rural',
    'aircraft_takeoff', 'aircraft_cruise', 'aircraft_landing',
    'train_interior', 'train_exterior', 'subway',
    'motorcycle', 'bicycle', 'electric_vehicle',

    # Urban
    'office_quiet', 'office_busy', 'office_hvac',
    'construction_drilling', 'construction_hammering', 'construction_sawing',
    'cafe_quiet', 'cafe_busy', 'restaurant',
    'shopping_mall', 'airport_terminal', 'train_station',

    # Industrial
    'factory_general', 'factory_machinery', 'factory_assembly',
    'warehouse', 'server_room', 'generator',

    # Natural
    'wind_light', 'wind_strong', 'rain_light', 'rain_heavy',
    'thunder', 'ocean_waves', 'waterfall', 'forest',

    # Indoor
    'hvac_fan', 'refrigerator', 'dishwasher', 'washing_machine',
    'vacuum_cleaner', 'air_purifier', 'computer_fan',

    # Human
    'crowd_applause', 'crowd_cheering', 'crowd_talking',
    'baby_crying', 'dog_barking', 'music_bass', 'music_treble',

    # Other
    'silence', 'mixed_noise'
]

NUM_CLASSES_V2 = len(NOISE_CATEGORIES_V2)  # 58 classes


class NoiseDataset:
    """
    Dataset for training noise classifier

    Supports:
    - Audio file loading
    - On-the-fly feature extraction
    - Data augmentation
    """

    def __new__(cls, audio_files: List[str], labels: List[int],
                feature_config: Optional[AudioFeatureConfig] = None,
                augment: bool = True):
        """
        Create noise dataset
        
        Args:
            audio_files: List of audio file paths
            labels: List of label indices
            feature_config: Feature extraction configuration
            augment: Enable data augmentation
            
        Returns:
            torch Dataset
        """
        _ensure_torch()
        
        class _NoiseDataset(_Dataset):
            def __init__(self, audio_files, labels, feature_config, augment):
                self.audio_files = audio_files
                self.labels = labels
                self.feature_config = feature_config or AudioFeatureConfig()
                self.augment = augment
                self.feature_extractor = TorchAudioFeatureExtractor(self.feature_config)

            def __len__(self) -> int:
                return len(self.audio_files)

            def __getitem__(self, idx: int) -> Tuple:
                import torchaudio
                
                # Load audio
                audio, sample_rate = torchaudio.load(self.audio_files[idx])

                # Convert to mono if stereo
                if audio.shape[0] > 1:
                    audio = audio.mean(dim=0)
                else:
                    audio = audio.squeeze(0)

                # Resample if needed
                if sample_rate != self.feature_config.sample_rate:
                    resampler = _T.Resample(sample_rate, self.feature_config.sample_rate)
                    audio = resampler(audio)

                # Convert to numpy for augmentation
                audio_np = audio.numpy()

                # Augmentation
                if self.augment:
                    audio_np = self.feature_extractor.augment_audio(audio_np)

                # Extract features
                mel_spec = self.feature_extractor.extract_mel_spectrogram(audio_np)

                # Convert to torch tensor
                mel_spec = _torch.from_numpy(mel_spec).float()
                label = self.labels[idx]

                return mel_spec, label
        
        return _NoiseDataset(audio_files, labels, feature_config, augment)


class NoiseClassifierService:
    """
    Complete noise classification service

    Features:
    - Feature extraction
    - Deep learning inference
    - Confidence thresholding
    - Model versioning
    - Export for deployment (ONNX, TorchScript)
    """

    def __init__(self, 
                 model_path: Optional[str] = None,
                 device: Optional[str] = None,
                 config: Optional[InferenceConfig] = None):
        """
        Initialize noise classifier service
        
        Args:
            model_path: Path to trained model
            device: Device (cuda/cpu)
            config: Inference configuration
        """
        _ensure_torch()
        
        self.config = config or InferenceConfig()
        if device:
            self.config.device = device
        if model_path:
            self.config.model_path = model_path
            
        self.device = self.config.device if self.config.device != 'cuda' else (
            'cuda' if _torch.cuda.is_available() else 'cpu'
        )
        
        self.feature_config = AudioFeatureConfig()
        self.feature_extractor = TorchAudioFeatureExtractor(self.feature_config)

        # Load model
        self.model = EfficientNetAudioClassifier(num_classes=NUM_CLASSES_V2)
        self.model.to(self.device)

        if self.config.model_path and Path(self.config.model_path).exists():
            load_model_weights(self.model, self.config.model_path, self.device)
        else:
            logger.warning("No model path provided or file not found, using untrained model")

        self.model.eval()

        # Category mapping
        self.idx_to_category = {i: cat for i, cat in enumerate(NOISE_CATEGORIES_V2)}
        self.category_to_idx = {cat: i for i, cat in enumerate(NOISE_CATEGORIES_V2)}

        logger.info(f"Initialized NoiseClassifierService on {self.device}: "
                   f"{NUM_CLASSES_V2} categories")

    def classify(self, audio: np.ndarray, sample_rate: int = 48000,
                 return_top_k: Optional[int] = None) -> Dict:
        """
        Classify noise type from audio

        Args:
            audio: Audio samples (numpy array)
            sample_rate: Sample rate (Hz)
            return_top_k: Return top K predictions (default from config)

        Returns:
            {
                'predicted_class': str,
                'confidence': float,
                'probabilities': Dict[str, float],
                'top_k': List[Tuple[str, float]]
            }
        """
        _ensure_torch()
        
        if return_top_k is None:
            return_top_k = self.config.return_top_k

        with _torch.no_grad():
            # Resample if needed
            if sample_rate != self.feature_config.sample_rate:
                resampler = _T.Resample(sample_rate, self.feature_config.sample_rate)
                audio_tensor = _torch.from_numpy(audio).float()
                audio_tensor = resampler(audio_tensor)
                audio = audio_tensor.numpy()

            # Extract mel spectrogram
            mel_spec = self.feature_extractor.extract_mel_spectrogram(audio)

            # Add batch dimension and convert to tensor
            mel_spec = _torch.from_numpy(mel_spec).float().unsqueeze(0).to(self.device)

            # Inference
            logits = self.model(mel_spec)
            probabilities = _F.softmax(logits, dim=1)

            # Get predictions
            probs_np = probabilities.cpu().numpy()[0]
            predicted_idx = np.argmax(probs_np)
            predicted_class = self.idx_to_category[predicted_idx]
            confidence = float(probs_np[predicted_idx])

            # Top-K predictions
            top_k_indices = np.argsort(probs_np)[-return_top_k:][::-1]
            top_k = [(self.idx_to_category[idx], float(probs_np[idx]))
                     for idx in top_k_indices]

            # All probabilities
            prob_dict = {self.idx_to_category[i]: float(probs_np[i])
                        for i in range(len(probs_np))}

            return {
                'predicted_class': predicted_class,
                'confidence': confidence,
                'probabilities': prob_dict,
                'top_k': top_k
            }

    def train(self, train_dataset, val_dataset, config: Optional[TrainingConfig] = None) -> Dict:
        """
        Train the noise classifier
        
        Args:
            train_dataset: Training dataset
            val_dataset: Validation dataset
            config: Training configuration
            
        Returns:
            Training history and metrics
        """
        _ensure_torch()
        
        config = config or TrainingConfig()
        
        # Data loaders
        train_loader = _DataLoader(
            train_dataset, 
            batch_size=config.batch_size,
            shuffle=True, 
            num_workers=config.num_workers,
            pin_memory=config.pin_memory
        )
        val_loader = _DataLoader(
            val_dataset, 
            batch_size=config.batch_size,
            shuffle=False, 
            num_workers=config.num_workers,
            pin_memory=config.pin_memory
        )

        # Optimizer and scheduler
        optimizer = _torch.optim.AdamW(
            self.model.parameters(), 
            lr=config.learning_rate,
            weight_decay=config.weight_decay
        )
        scheduler = _torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=config.lr_scheduler_factor,
            patience=config.lr_scheduler_patience,
            min_lr=config.lr_scheduler_min_lr
        )

        # Loss function
        criterion = _nn.CrossEntropyLoss()

        best_val_loss = float('inf')
        patience_counter = 0
        history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }

        for epoch in range(config.num_epochs):
            # Training
            self.model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            for spectrograms, labels in train_loader:
                spectrograms = spectrograms.to(self.device)
                labels = labels.to(self.device)

                optimizer.zero_grad()

                logits = self.model(spectrograms)
                loss = criterion(logits, labels)

                loss.backward()
                optimizer.step()

                train_loss += loss.item()

                _, predicted = logits.max(1)
                train_total += labels.size(0)
                train_correct += predicted.eq(labels).sum().item()

            train_acc = 100.0 * train_correct / train_total
            avg_train_loss = train_loss / len(train_loader)

            # Validation
            self.model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0

            with _torch.no_grad():
                for spectrograms, labels in val_loader:
                    spectrograms = spectrograms.to(self.device)
                    labels = labels.to(self.device)

                    logits = self.model(spectrograms)
                    loss = criterion(logits, labels)

                    val_loss += loss.item()

                    _, predicted = logits.max(1)
                    val_total += labels.size(0)
                    val_correct += predicted.eq(labels).sum().item()

            val_acc = 100.0 * val_correct / val_total
            avg_val_loss = val_loss / len(val_loader)

            # Update history
            history['train_loss'].append(avg_train_loss)
            history['train_acc'].append(train_acc)
            history['val_loss'].append(avg_val_loss)
            history['val_acc'].append(val_acc)

            # Save best model
            if avg_val_loss < best_val_loss - config.early_stopping_min_delta:
                best_val_loss = avg_val_loss
                patience_counter = 0
                
                if config.save_best_only:
                    checkpoint_path = Path(config.checkpoint_dir) / 'best_model.pth'
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    save_model_checkpoint(self.model, str(checkpoint_path), {
                        'epoch': epoch,
                        'val_acc': val_acc,
                        'val_loss': avg_val_loss
                    })
            else:
                patience_counter += 1

            # Learning rate scheduling
            scheduler.step(avg_val_loss)

            logger.info(f"Epoch {epoch+1}/{config.num_epochs}: "
                       f"Train Loss: {avg_train_loss:.4f}, "
                       f"Train Acc: {train_acc:.2f}%, "
                       f"Val Loss: {avg_val_loss:.4f}, "
                       f"Val Acc: {val_acc:.2f}%")

            # Early stopping
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"Early stopping triggered at epoch {epoch+1}")
                break

        return history

    def export(self, output_path: str, format: str = 'onnx'):
        """
        Export model for deployment
        
        Args:
            output_path: Output file path
            format: Export format ('onnx' or 'torchscript')
        """
        _ensure_torch()
        
        self.model.eval()
        
        if format == 'onnx':
            self._export_onnx(output_path)
        elif format == 'torchscript':
            self._export_torchscript(output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_onnx(self, output_path: str, input_shape: Tuple[int, int, int, int] = (1, 1, 128, 128)):
        """Export model to ONNX format"""
        _ensure_torch()
        
        dummy_input = _torch.randn(*input_shape).to(self.device)

        _torch.onnx.export(
            self.model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['spectrogram'],
            output_names=['logits'],
            dynamic_axes={
                'spectrogram': {0: 'batch_size'},
                'logits': {0: 'batch_size'}
            }
        )

        logger.info(f"Exported ONNX model to {output_path}")

    def _export_torchscript(self, output_path: str):
        """Export model to TorchScript"""
        _ensure_torch()
        
        scripted_model = _torch.jit.script(self.model)
        scripted_model.save(output_path)
        logger.info(f"Exported TorchScript model to {output_path}")
