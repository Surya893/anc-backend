"""
Generate test audio files with known intensity levels for verification.
"""

import numpy as np
import wave
import struct


def generate_tone(frequency=1000, duration=2.0, sample_rate=44100, amplitude=0.5):
    """
    Generate a sine wave tone.

    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Amplitude (0.0 to 1.0)

    Returns:
        Audio data as numpy array
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = amplitude * np.sin(2 * np.pi * frequency * t)
    return audio


def save_wav(filename, audio_data, sample_rate=44100):
    """
    Save audio data to WAV file.

    Args:
        filename: Output filename
        audio_data: Audio data (numpy array, -1.0 to 1.0)
        sample_rate: Sample rate in Hz
    """
    # Convert to 16-bit PCM
    audio_int16 = np.int16(audio_data * 32767)

    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    print(f"✓ Saved: {filename}")


def generate_test_samples():
    """Generate test audio samples with various intensity levels."""
    print("=" * 80)
    print("GENERATING TEST AUDIO SAMPLES")
    print("=" * 80)

    # Test 1: Very quiet (whisper-like, ~30 dB SPL)
    # RMS amplitude 0.002 -> -54 dBFS -> ~40 dB SPL estimated
    quiet = generate_tone(1000, 2.0, 44100, 0.002)
    save_wav('test_quiet.wav', quiet)
    print(f"  Amplitude: 0.002, Expected: ~-54 dBFS, ~40 dB SPL (Very Quiet)")

    # Test 2: Moderate (conversation-like, ~60 dB SPL)
    # RMS amplitude 0.05 -> -26 dBFS -> ~68 dB SPL estimated
    moderate = generate_tone(1000, 2.0, 44100, 0.05)
    save_wav('test_moderate.wav', moderate)
    print(f"  Amplitude: 0.05, Expected: ~-26 dBFS, ~68 dB SPL (Moderate)")

    # Test 3: Loud (traffic-like, ~80 dB SPL)
    # RMS amplitude 0.2 -> -14 dBFS -> ~80 dB SPL estimated
    loud = generate_tone(1000, 2.0, 44100, 0.2)
    save_wav('test_loud.wav', loud)
    print(f"  Amplitude: 0.2, Expected: ~-14 dBFS, ~80 dB SPL (Loud)")

    # Test 4: Very loud (power tools-like, ~90 dB SPL)
    # RMS amplitude 0.5 -> -6 dBFS -> ~88 dB SPL estimated
    very_loud = generate_tone(1000, 2.0, 44100, 0.5)
    save_wav('test_very_loud.wav', very_loud)
    print(f"  Amplitude: 0.5, Expected: ~-6 dBFS, ~88 dB SPL (Very Loud)")

    # Test 5: Extremely loud (near full scale, ~100 dB SPL)
    # RMS amplitude 0.8 -> -2 dBFS -> ~92 dB SPL estimated
    extreme = generate_tone(1000, 2.0, 44100, 0.8)
    save_wav('test_extreme.wav', extreme)
    print(f"  Amplitude: 0.8, Expected: ~-2 dBFS, ~92 dB SPL (Extremely Loud)")

    # Test 6: Pink noise (more realistic)
    # Generate pink noise at moderate level
    duration = 2.0
    sample_rate = 44100
    num_samples = int(duration * sample_rate)

    # Generate white noise
    white_noise = np.random.randn(num_samples)

    # Apply pink noise filter (1/f spectrum approximation)
    # Simple method: apply moving average
    window = 10
    pink_noise = np.convolve(white_noise, np.ones(window)/window, mode='same')

    # Normalize and scale
    pink_noise = pink_noise / np.max(np.abs(pink_noise))
    pink_noise = pink_noise * 0.15  # Scale to moderate level

    save_wav('test_pink_noise.wav', pink_noise)
    print(f"  Pink noise at 0.15 amplitude, Expected: ~-16 dBFS, ~78 dB SPL")

    print("\n" + "=" * 80)
    print("✓ Test samples generated successfully!")
    print("=" * 80)


if __name__ == "__main__":
    generate_test_samples()
