"""
Audio Intensity Analysis Script
Analyzes audio files and computes dB levels (RMS, peak, LUFS-style).
"""

import numpy as np
import wave
import sys
import os


class AudioIntensityAnalyzer:
    """Analyze audio intensity and compute various dB metrics."""

    # Reference values for dB calculations
    REF_AMPLITUDE = 1.0  # Reference for digital audio (full scale)
    REF_PRESSURE_PASCALS = 20e-6  # 20 micropascals (standard SPL reference)

    def __init__(self, wav_path):
        """
        Initialize analyzer with WAV file.

        Args:
            wav_path: Path to WAV file
        """
        self.wav_path = wav_path
        self.audio_data = None
        self.sample_rate = None
        self.num_channels = None
        self.duration = None

        self._load_wav()

    def _load_wav(self):
        """Load WAV file and extract audio data."""
        if not os.path.exists(self.wav_path):
            raise FileNotFoundError(f"WAV file not found: {self.wav_path}")

        with wave.open(self.wav_path, 'rb') as wav_file:
            self.num_channels = wav_file.getnchannels()
            self.sample_rate = wav_file.getframerate()
            num_frames = wav_file.getnframes()
            sample_width = wav_file.getsampwidth()

            # Read audio data
            audio_bytes = wav_file.readframes(num_frames)

            # Convert to numpy array based on sample width
            if sample_width == 1:  # 8-bit
                dtype = np.uint8
                self.audio_data = np.frombuffer(audio_bytes, dtype=dtype)
                self.audio_data = (self.audio_data.astype(np.float64) - 128) / 128.0
            elif sample_width == 2:  # 16-bit
                dtype = np.int16
                self.audio_data = np.frombuffer(audio_bytes, dtype=dtype)
                self.audio_data = self.audio_data.astype(np.float64) / 32768.0
            elif sample_width == 4:  # 32-bit
                dtype = np.int32
                self.audio_data = np.frombuffer(audio_bytes, dtype=dtype)
                self.audio_data = self.audio_data.astype(np.float64) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width}")

            # Handle multi-channel audio (convert to mono)
            if self.num_channels > 1:
                self.audio_data = self.audio_data.reshape(-1, self.num_channels)
                self.audio_data = np.mean(self.audio_data, axis=1)

            self.duration = len(self.audio_data) / self.sample_rate

    def calculate_rms(self):
        """
        Calculate RMS (Root Mean Square) amplitude.

        Returns:
            RMS amplitude (0.0 to 1.0 for normalized audio)
        """
        return np.sqrt(np.mean(self.audio_data ** 2))

    def calculate_peak(self):
        """
        Calculate peak amplitude.

        Returns:
            Peak amplitude (0.0 to 1.0 for normalized audio)
        """
        return np.max(np.abs(self.audio_data))

    def calculate_rms_db(self):
        """
        Calculate RMS level in dBFS (decibels relative to full scale).

        Returns:
            RMS level in dBFS
        """
        rms = self.calculate_rms()
        if rms > 0:
            return 20 * np.log10(rms / self.REF_AMPLITUDE)
        else:
            return -np.inf

    def calculate_peak_db(self):
        """
        Calculate peak level in dBFS.

        Returns:
            Peak level in dBFS
        """
        peak = self.calculate_peak()
        if peak > 0:
            return 20 * np.log10(peak / self.REF_AMPLITUDE)
        else:
            return -np.inf

    def calculate_spl_estimate(self, calibration_offset=94.0):
        """
        Estimate SPL (Sound Pressure Level) in dB.

        This is an estimate assuming a calibration reference.
        Standard calibration: 94 dB SPL = 1 Pa RMS = digital full scale

        Args:
            calibration_offset: Calibration offset in dB (default 94 dB)

        Returns:
            Estimated SPL in dB
        """
        rms_dbfs = self.calculate_rms_db()

        # Estimate SPL assuming calibration
        # If digital full scale (0 dBFS) corresponds to 94 dB SPL
        spl_estimate = calibration_offset + rms_dbfs

        return spl_estimate

    def calculate_crest_factor(self):
        """
        Calculate crest factor (peak-to-RMS ratio).

        Returns:
            Crest factor in dB
        """
        peak = self.calculate_peak()
        rms = self.calculate_rms()

        if rms > 0:
            return 20 * np.log10(peak / rms)
        else:
            return np.inf

    def calculate_dynamic_range(self, percentile=0.1):
        """
        Calculate dynamic range (difference between peak and noise floor).

        Args:
            percentile: Percentile for noise floor estimate (default 0.1%)

        Returns:
            Dynamic range in dB
        """
        peak_db = self.calculate_peak_db()

        # Estimate noise floor from low percentile
        noise_floor_amplitude = np.percentile(np.abs(self.audio_data), percentile)

        if noise_floor_amplitude > 0:
            noise_floor_db = 20 * np.log10(noise_floor_amplitude / self.REF_AMPLITUDE)
            dynamic_range = peak_db - noise_floor_db
        else:
            dynamic_range = np.inf

        return dynamic_range

    def analyze_windowed(self, window_size_ms=100):
        """
        Analyze audio in windows to find loudest and quietest segments.

        Args:
            window_size_ms: Window size in milliseconds

        Returns:
            Dictionary with windowed analysis results
        """
        window_samples = int(window_size_ms * self.sample_rate / 1000)
        num_windows = len(self.audio_data) // window_samples

        if num_windows == 0:
            return None

        rms_values = []

        for i in range(num_windows):
            start = i * window_samples
            end = start + window_samples
            window = self.audio_data[start:end]

            rms = np.sqrt(np.mean(window ** 2))
            rms_values.append(rms)

        rms_values = np.array(rms_values)
        rms_db_values = 20 * np.log10(rms_values + 1e-10)  # Add small value to avoid log(0)

        loudest_idx = np.argmax(rms_values)
        quietest_idx = np.argmin(rms_values)

        return {
            'window_size_ms': window_size_ms,
            'num_windows': num_windows,
            'mean_rms_db': np.mean(rms_db_values),
            'max_rms_db': rms_db_values[loudest_idx],
            'min_rms_db': rms_db_values[quietest_idx],
            'loudest_time_ms': loudest_idx * window_size_ms,
            'quietest_time_ms': quietest_idx * window_size_ms
        }

    def classify_loudness(self, spl_db):
        """
        Classify loudness level based on SPL.

        Args:
            spl_db: Sound pressure level in dB

        Returns:
            Loudness classification string
        """
        if spl_db < 30:
            return "Very Quiet (whisper, library)"
        elif spl_db < 50:
            return "Quiet (quiet room, moderate rainfall)"
        elif spl_db < 70:
            return "Moderate (normal conversation, background music)"
        elif spl_db < 85:
            return "Loud (busy traffic, alarm clock)"
        elif spl_db < 100:
            return "Very Loud (motorcycle, power tools) - Hearing damage risk"
        elif spl_db < 120:
            return "Extremely Loud (rock concert, chainsaw) - Immediate hearing damage risk"
        else:
            return "Painful (jet engine, gunshot) - Severe hearing damage"

    def print_analysis(self):
        """Print comprehensive intensity analysis."""
        print("=" * 80)
        print("AUDIO INTENSITY ANALYSIS")
        print("=" * 80)

        print(f"\nFile Information:")
        print(f"  Path: {self.wav_path}")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Channels: {self.num_channels}")
        print(f"  Duration: {self.duration:.2f} seconds")
        print(f"  Samples: {len(self.audio_data):,}")

        # Basic metrics
        rms = self.calculate_rms()
        peak = self.calculate_peak()
        rms_db = self.calculate_rms_db()
        peak_db = self.calculate_peak_db()

        print(f"\nAmplitude Metrics:")
        print(f"  RMS Amplitude: {rms:.6f}")
        print(f"  Peak Amplitude: {peak:.6f}")

        print(f"\nDecibel Metrics (dBFS - relative to digital full scale):")
        print(f"  RMS Level: {rms_db:.2f} dBFS")
        print(f"  Peak Level: {peak_db:.2f} dBFS")
        print(f"  Crest Factor: {self.calculate_crest_factor():.2f} dB")
        print(f"  Dynamic Range: {self.calculate_dynamic_range():.2f} dB")

        # SPL estimate
        spl_estimate = self.calculate_spl_estimate()

        print(f"\nEstimated Sound Pressure Level (SPL):")
        print(f"  SPL Estimate: {spl_estimate:.2f} dB SPL")
        print(f"  Classification: {self.classify_loudness(spl_estimate)}")
        print(f"  (Note: Assumes 94 dB SPL calibration at 0 dBFS)")

        # Windowed analysis
        windowed = self.analyze_windowed(window_size_ms=100)

        if windowed:
            print(f"\nWindowed Analysis (100ms windows):")
            print(f"  Number of Windows: {windowed['num_windows']}")
            print(f"  Mean RMS: {windowed['mean_rms_db']:.2f} dBFS")
            print(f"  Loudest Segment: {windowed['max_rms_db']:.2f} dBFS at {windowed['loudest_time_ms']:.0f}ms")
            print(f"  Quietest Segment: {windowed['min_rms_db']:.2f} dBFS at {windowed['quietest_time_ms']:.0f}ms")

        # Visual representation
        print(f"\nIntensity Visualization:")
        self._print_intensity_bar(rms_db)

        print("=" * 80)

    def _print_intensity_bar(self, db_level):
        """Print visual bar for intensity level."""
        # Map dBFS (-60 to 0) to bar (0 to 50 chars)
        normalized = max(0, min(60, db_level + 60)) / 60  # -60 to 0 dBFS -> 0 to 1
        bar_length = int(normalized * 50)
        bar = '█' * bar_length + '░' * (50 - bar_length)

        print(f"  {db_level:>6.2f} dBFS  |{bar}|")
        print(f"  {'Quiet':<13} {'│':<20} {'│':<15} {'Loud':>13}")


def analyze_audio_file(wav_path):
    """
    Analyze audio file and print results.

    Args:
        wav_path: Path to WAV file
    """
    try:
        analyzer = AudioIntensityAnalyzer(wav_path)
        analyzer.print_analysis()

        return {
            'rms_db': analyzer.calculate_rms_db(),
            'peak_db': analyzer.calculate_peak_db(),
            'spl_estimate': analyzer.calculate_spl_estimate()
        }

    except Exception as e:
        print(f"Error analyzing audio file: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python intensity_analysis.py <audio_file.wav>")
        print("\nExample:")
        print("  python intensity_analysis.py recordings/demo_office_noise_20251107_115238.wav")
        sys.exit(1)

    wav_path = sys.argv[1]

    if not os.path.exists(wav_path):
        print(f"Error: File not found: {wav_path}")
        sys.exit(1)

    analyze_audio_file(wav_path)


if __name__ == "__main__":
    main()
