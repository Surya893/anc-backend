"""
EfficientNet-B3 Audio Classifier
PyTorch model for audio spectrogram classification
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy imports to avoid torch dependency in non-ML modules
_torch = None
_nn = None


def _ensure_torch():
    """Lazy load torch dependencies"""
    global _torch, _nn
    if _torch is None:
        import torch
        import torch.nn as nn
        _torch = torch
        _nn = nn


class EfficientNetAudioClassifier:
    """
    EfficientNet-B3 based audio classifier

    Architecture:
    - EfficientNet-B3 backbone (pretrained on ImageNet)
    - Custom classification head
    - Dropout for regularization
    - Batch normalization
    """

    def __new__(cls, num_classes: int = 58, pretrained: bool = True, dropout: float = 0.3):
        """
        Create EfficientNet audio classifier model
        
        Args:
            num_classes: Number of output classes
            pretrained: Use pretrained ImageNet weights
            dropout: Dropout probability
            
        Returns:
            nn.Module: PyTorch model
        """
        _ensure_torch()
        
        # Import torchvision inside the method to avoid dependency issues
        from torchvision.models import efficientnet_b3, EfficientNet_B3_Weights

        if pretrained:
            model = efficientnet_b3(weights=EfficientNet_B3_Weights.DEFAULT)
        else:
            model = efficientnet_b3(weights=None)

        # Modify first conv layer to accept 1-channel spectrograms
        original_conv = model.features[0][0]
        model.features[0][0] = _nn.Conv2d(
            1,  # 1 channel (grayscale spectrogram)
            original_conv.out_channels,
            kernel_size=original_conv.kernel_size,
            stride=original_conv.stride,
            padding=original_conv.padding,
            bias=False
        )

        # Get feature dimension
        in_features = model.classifier[1].in_features

        # Custom classification head
        model.classifier = _nn.Sequential(
            _nn.Dropout(p=dropout, inplace=True),
            _nn.Linear(in_features, 512),
            _nn.ReLU(inplace=True),
            _nn.BatchNorm1d(512),
            _nn.Dropout(p=dropout / 2, inplace=True),
            _nn.Linear(512, 256),
            _nn.ReLU(inplace=True),
            _nn.BatchNorm1d(256),
            _nn.Linear(256, num_classes)
        )

        # Store metadata
        model.num_classes = num_classes

        logger.info(f"Initialized EfficientNet-B3 classifier: {num_classes} classes, "
                   f"pretrained: {pretrained}, dropout: {dropout}")

        return model


def load_model_weights(model, checkpoint_path: str, device: str = 'cpu'):
    """
    Load model weights from checkpoint
    
    Args:
        model: PyTorch model
        checkpoint_path: Path to checkpoint file
        device: Device to load model on
        
    Returns:
        dict: Checkpoint metadata
    """
    _ensure_torch()
    
    try:
        checkpoint = _torch.load(checkpoint_path, map_location=device)

        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
            logger.info(f"Loaded model from {checkpoint_path} "
                       f"(epoch {checkpoint.get('epoch', 'unknown')})")
            return checkpoint
        else:
            model.load_state_dict(checkpoint)
            logger.info(f"Loaded model weights from {checkpoint_path}")
            return {}

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def save_model_checkpoint(model, path: str, metadata: Optional[dict] = None):
    """
    Save model checkpoint with metadata
    
    Args:
        model: PyTorch model
        path: Save path
        metadata: Optional metadata to save
    """
    _ensure_torch()
    
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'num_classes': getattr(model, 'num_classes', None),
        'metadata': metadata or {}
    }

    _torch.save(checkpoint, path)
    logger.info(f"Saved model checkpoint to {path}")
