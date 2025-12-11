"""
PyTorch-based Audio Feature Extractor
Uses torchaudio for fast GPU-accelerated feature extraction
"""

import numpy as np
import logging
from typing import Optional

# Lazy imports for torch to avoid dependency in non-ML modules
_torch = None
_torchaudio = None
_T = None
_F = None

from ..config import AudioFeatureConfig

logger = logging.getLogger(__name__)


def _ensure_torch():
    """Lazy load torch dependencies"""
    global _torch, _torchaudio, _T, _F
    if _torch is None:
        import torch
        import torchaudio
        import torchaudio.transforms as T
        import torch.nn.functional as F
        _torch = torch
        _torchaudio = torchaudio
        _T = T
        _F = F


class TorchAudioFeatureExtractor:
    """
    Extract audio features using PyTorch/torchaudio for deep learning classification

    Features:
    - Mel spectrograms (for EfficientNet input)
    - MFCCs (for traditional ML)
    - Data augmentation (time stretch, pitch shift, noise injection)
    - GPU acceleration support
    """

    def __init__(self, config: Optional[AudioFeatureConfig] = None):
        """
        Initialize the feature extractor
        
        Args:
            config: Feature extraction configuration
        """
        _ensure_torch()
        
        self.config = config or AudioFeatureConfig()

        # Mel spectrogram transform
        self.mel_spectrogram = _T.MelSpectrogram(
            sample_rate=self.config.sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            n_mels=self.config.n_mels,
            power=2.0
        )

        # MFCC transform
        self.mfcc_transform = _T.MFCC(
            sample_rate=self.config.sample_rate,
            n_mfcc=self.config.n_mfcc,
            melkwargs={
                'n_fft': self.config.n_fft,
                'hop_length': self.config.hop_length,
                'n_mels': self.config.n_mels
            }
        )

        # Amplitude to DB
        self.amplitude_to_db = _T.AmplitudeToDB()

        logger.info(f"Initialized TorchAudioFeatureExtractor: {self.config.n_mels} mels, "
                   f"{self.config.n_mfcc} MFCCs, {self.config.sample_rate} Hz")

    def extract_mel_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract mel spectrogram from audio

        Args:
            audio: Audio array (samples,) or (batch, samples)

        Returns:
            Mel spectrogram (channels, height, width) as numpy array
        """
        _ensure_torch()
        
        # Convert to torch tensor if needed
        if isinstance(audio, np.ndarray):
            audio = _torch.from_numpy(audio).float()

        # Ensure batch dimension
        if audio.ndim == 1:
            audio = audio.unsqueeze(0)

        # Compute mel spectrogram
        mel_spec = self.mel_spectrogram(audio)

        # Convert to dB scale
        mel_spec_db = self.amplitude_to_db(mel_spec)

        # Normalize
        mel_spec_db = (mel_spec_db - mel_spec_db.mean()) / (mel_spec_db.std() + 1e-8)

        # Resize to fixed size
        mel_spec_resized = _F.interpolate(
            mel_spec_db.unsqueeze(1),
            size=(self.config.spectrogram_height, self.config.spectrogram_width),
            mode='bilinear',
            align_corners=False
        )

        # Convert back to numpy
        result = mel_spec_resized.squeeze(0).cpu().numpy()
        return result

    def extract_mfcc(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract MFCC features
        
        Args:
            audio: Audio array
            
        Returns:
            MFCC features as numpy array
        """
        _ensure_torch()
        
        # Convert to torch tensor if needed
        if isinstance(audio, np.ndarray):
            audio = _torch.from_numpy(audio).float()
            
        if audio.ndim == 1:
            audio = audio.unsqueeze(0)

        mfcc = self.mfcc_transform(audio)

        # Normalize
        mfcc = (mfcc - mfcc.mean()) / (mfcc.std() + 1e-8)

        return mfcc.cpu().numpy()

    def augment_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply data augmentation to audio

        Techniques:
        - Time stretching
        - Pitch shifting
        - Noise injection
        
        Args:
            audio: Audio array
            
        Returns:
            Augmented audio as numpy array
        """
        _ensure_torch()
        
        if not self.config.enable_augmentation:
            return audio

        # Convert to torch tensor if needed
        if isinstance(audio, np.ndarray):
            audio = _torch.from_numpy(audio).float()

        # Time stretch
        if np.random.rand() < 0.5:
            rate = np.random.uniform(*self.config.time_stretch_range)
            try:
                audio = _torchaudio.functional.time_stretch(
                    audio.unsqueeze(0), n_freq=self.config.n_fft // 2 + 1, rate=rate
                ).squeeze(0)
            except Exception as e:
                logger.debug(f"Time stretch failed: {e}")

        # Pitch shift
        if np.random.rand() < 0.5:
            n_steps = np.random.randint(*self.config.pitch_shift_range)
            try:
                audio = _torchaudio.functional.pitch_shift(
                    audio, self.config.sample_rate, n_steps
                )
            except Exception as e:
                logger.debug(f"Pitch shift failed: {e}")

        # Noise injection
        if np.random.rand() < self.config.noise_injection_prob:
            noise = _torch.randn_like(audio) * self.config.noise_injection_level
            audio = audio + noise

        # Convert back to numpy
        if isinstance(audio, _torch.Tensor):
            audio = audio.cpu().numpy()
            
        return audio
