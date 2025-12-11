"""
Audio encoding/decoding utilities for Lambda functions
Handles base64 conversion and numpy array serialization
"""

import base64
import numpy as np
import logging

logger = logging.getLogger(__name__)


def encode_audio(audio_array, dtype=np.float32):
    """
    Encode numpy audio array to base64 string
    
    Args:
        audio_array: numpy array of audio samples
        dtype: numpy dtype for conversion (default: float32)
        
    Returns:
        str: Base64-encoded audio
        
    Raises:
        ValueError: If encoding fails
    """
    try:
        if not isinstance(audio_array, np.ndarray):
            audio_array = np.array(audio_array, dtype=dtype)
        
        audio_bytes = audio_array.astype(dtype).tobytes()
        return base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode audio: {str(e)}")
        raise ValueError(f"Audio encoding failed: {str(e)}")


def decode_audio(audio_base64, dtype=np.float32, num_channels=1):
    """
    Decode base64-encoded audio to numpy array
    
    Args:
        audio_base64: Base64-encoded audio string
        dtype: numpy dtype for decoding (default: float32)
        num_channels: Number of audio channels (for reshaping)
        
    Returns:
        numpy.ndarray: Audio samples
        
    Raises:
        ValueError: If decoding fails
    """
    try:
        audio_bytes = base64.b64decode(audio_base64)
        audio_array = np.frombuffer(audio_bytes, dtype=dtype)
        
        if num_channels > 1:
            num_samples = len(audio_array) // num_channels
            audio_array = audio_array.reshape(num_channels, num_samples)
        
        return audio_array
    except Exception as e:
        logger.error(f"Failed to decode audio: {str(e)}")
        raise ValueError(f"Audio decoding failed: {str(e)}")


def audio_to_base64(audio_array, dtype=np.float32):
    """Alias for encode_audio for backwards compatibility"""
    return encode_audio(audio_array, dtype)


def base64_to_audio(audio_base64, dtype=np.float32):
    """Alias for decode_audio for backwards compatibility"""
    return decode_audio(audio_base64, dtype)


def validate_audio_chunk(audio_array, max_size=4096, sample_rate=48000):
    """
    Validate audio chunk dimensions and values
    
    Args:
        audio_array: Audio to validate
        max_size: Maximum allowed samples per chunk
        sample_rate: Expected sample rate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(audio_array, np.ndarray):
        return False, "Audio must be numpy array"
    
    if audio_array.dtype not in [np.float32, np.float64]:
        return False, f"Audio dtype must be float32 or float64, got {audio_array.dtype}"
    
    if audio_array.ndim > 2:
        return False, f"Audio must be 1D or 2D array, got shape {audio_array.shape}"
    
    num_samples = audio_array.shape[-1] if audio_array.ndim == 2 else len(audio_array)
    if num_samples > max_size:
        return False, f"Chunk too large: {num_samples} samples (max: {max_size})"
    
    if np.any(np.isnan(audio_array)) or np.any(np.isinf(audio_array)):
        return False, "Audio contains NaN or Inf values"
    
    # Check amplitude (warn if clipped)
    if np.max(np.abs(audio_array)) > 1.0:
        logger.warning(f"Audio amplitude exceeds 1.0: {np.max(np.abs(audio_array)):.2f}")
    
    return True, None
