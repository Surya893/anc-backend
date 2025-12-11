"""
ML Configuration Classes
Shared configuration for feature extraction, training, and inference
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional


@dataclass
class AudioFeatureConfig:
    """Configuration for audio feature extraction"""
    sample_rate: int = 48000
    n_fft: int = 2048
    hop_length: int = 512
    n_mels: int = 128
    n_mfcc: int = 40
    window_length_ms: int = 100
    spectrogram_height: int = 128
    spectrogram_width: int = 128

    # Data augmentation
    enable_augmentation: bool = True
    time_stretch_range: Tuple[float, float] = (0.9, 1.1)
    pitch_shift_range: Tuple[int, int] = (-2, 2)
    noise_injection_prob: float = 0.3
    noise_injection_level: float = 0.01


@dataclass
class ModelConfig:
    """Configuration for model architecture"""
    num_classes: int = 58
    dropout: float = 0.3
    pretrained: bool = True
    architecture: str = 'efficientnet_b3'


@dataclass
class TrainingConfig:
    """Configuration for model training"""
    num_epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    
    # Early stopping
    early_stopping_patience: int = 15
    early_stopping_min_delta: float = 1e-4
    
    # Learning rate scheduling
    lr_scheduler_factor: float = 0.5
    lr_scheduler_patience: int = 5
    lr_scheduler_min_lr: float = 1e-7
    
    # Validation
    validation_split: float = 0.2
    test_split: float = 0.1
    
    # Hardware
    device: str = 'cpu'
    num_workers: int = 4
    pin_memory: bool = True
    
    # Checkpointing
    save_best_only: bool = True
    checkpoint_dir: str = 'checkpoints'


@dataclass
class InferenceConfig:
    """Configuration for inference"""
    device: str = 'cpu'
    batch_size: int = 1
    confidence_threshold: float = 0.5
    return_top_k: int = 5
    model_path: Optional[str] = None
