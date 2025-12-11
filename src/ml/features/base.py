"""
Base Feature Extraction Module
Shared configuration and interfaces for audio preprocessing
"""

import numpy as np
from typing import Dict, Protocol, runtime_checkable
from ..config import AudioFeatureConfig


__all__ = ['AudioFeatureConfig', 'FeatureExtractorProtocol']


@runtime_checkable
class FeatureExtractorProtocol(Protocol):
    """Protocol for feature extractors to ensure consistent interface"""
    
    config: AudioFeatureConfig
    
    def extract_mel_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract mel spectrogram from audio
        
        Args:
            audio: Audio samples
            
        Returns:
            Mel spectrogram features
        """
        ...
    
    def extract_mfcc(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract MFCC features from audio
        
        Args:
            audio: Audio samples
            
        Returns:
            MFCC features
        """
        ...
