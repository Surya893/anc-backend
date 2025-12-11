"""
ANC Processing Service
Business logic for Active Noise Cancellation
"""

import numpy as np
import base64
import io
from scipy import signal
import logging

logger = logging.getLogger(__name__)


class ANCService:
    """Service for ANC audio processing"""

    def __init__(self):
        """Initialize ANC service"""
        from config import get_config
        self.config = get_config()
        logger.info("ANC Service initialized")

    def process_audio(self, audio_data, sample_rate=48000, algorithm='nlms', intensity=1.0):
        """
        Process audio with ANC algorithm

        Args:
            audio_data: Base64-encoded audio data
            sample_rate: Audio sample rate
            algorithm: ANC algorithm ('nlms', 'lms', 'rls')
            intensity: ANC intensity (0.0-1.0)

        Returns:
            dict: Processed audio and metrics
        """
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)
            audio = np.frombuffer(audio_bytes, dtype=np.float32)

            # Apply ANC algorithm
            if algorithm == 'nlms':
                processed = self._nlms_filter(audio, intensity)
            elif algorithm == 'lms':
                processed = self._lms_filter(audio, intensity)
            elif algorithm == 'rls':
                processed = self._rls_filter(audio, intensity)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")

            # Calculate metrics
            metrics = self._calculate_metrics(audio, processed)

            # Encode processed audio
            processed_bytes = processed.astype(np.float32).tobytes()
            processed_b64 = base64.b64encode(processed_bytes).decode('utf-8')

            return {
                'processed_audio': processed_b64,
                'metrics': metrics
            }

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise

    def _nlms_filter(self, audio, intensity):
        """Apply NLMS adaptive filter"""
        # Placeholder - integrate with src/core/anc_algorithms_v2.py
        filter_length = self.config.ANC_FILTER_TAPS

        # Generate anti-noise (phase inversion for now)
        anti_noise = -audio * intensity

        # Combine original and anti-noise
        processed = audio + anti_noise

        return processed

    def _lms_filter(self, audio, intensity):
        """Apply LMS adaptive filter"""
        # Placeholder
        return -audio * intensity

    def _rls_filter(self, audio, intensity):
        """Apply RLS adaptive filter"""
        # Placeholder
        return -audio * intensity

    def _calculate_metrics(self, original, processed):
        """Calculate processing metrics"""
        # Calculate noise reduction in dB
        original_rms = np.sqrt(np.mean(original**2))
        processed_rms = np.sqrt(np.mean(processed**2))

        if processed_rms > 0:
            reduction_db = 20 * np.log10(original_rms / processed_rms)
        else:
            reduction_db = 0

        return {
            'reduction_db': float(reduction_db),
            'original_rms': float(original_rms),
            'processed_rms': float(processed_rms),
            'samples_processed': len(original)
        }
