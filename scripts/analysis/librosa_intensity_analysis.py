"""
Librosa-based Audio Intensity Analysis
Uses librosa library to analyze audio intensity and compare with known values.
"""

import numpy as np
import librosa
import sys
import os


class LibrosaIntensityAnalyzer:
    """Analyze audio intensity using librosa features."""

    def __init__(self, audio_path):
        """
        Initialize analyzer with audio file.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
        """
        self.audio_path = audio_path
        self.audio_data = None
        self.sample_rate = None

        self._load_audio()

    def _load_audio(self):
        """Load audio file using librosa."""
        if not os.path.exists(self.audio_path):
            raise FileNotFoundError(f"Audio file not found: {self.audio_path}")

        # Load audio with librosa (automatically resamples to 22050 Hz by default)
        self.audio_data, self.sample_rate = librosa.load(self.audio_path, sr=None)

        print(f"Loaded: {self.audio_path}")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Duration: {len(self.audio_data) / self.sample_rate:.2f}s")
        print(f"  Samples: {len(self.audio_data):,}")

    def calculate_rms_energy(self, frame_length=2048, hop_length=512):
        """
        Calculate RMS energy using librosa.

        Args:
            frame_length: Frame length for analysis
            hop_length: Hop length for frames

        Returns:
            RMS energy array
        """
        rms = librosa.feature.rms(
            y=self.audio_data,
            frame_length=frame_length,
            hop_length=hop_length
        )[0]

        return rms

    def calculate_spectral_centroid(self):
        """
        Calculate spectral centroid (brightness measure).

        Returns:
            Spectral centroid array
        """
        centroid = librosa.feature.spectral_centroid(
            y=self.audio_data,
            sr=self.sample_rate
        )[0]

        return centroid

    def calculate_zcr(self):
        """
        Calculate zero-crossing rate.

        Returns:
            Zero-crossing rate array
        """
        zcr = librosa.feature.zero_crossing_rate(self.audio_data)[0]
        return zcr

    def calculate_db_metrics(self):
        """
        Calculate comprehensive dB metrics.

        Returns:
            Dictionary with dB measurements
        """
        # Overall RMS
        overall_rms = np.sqrt(np.mean(self.audio_data ** 2))

        # Peak amplitude
        peak_amplitude = np.max(np.abs(self.audio_data))

        # RMS in dBFS
        if overall_rms > 0:
            rms_dbfs = 20 * np.log10(overall_rms)
        else:
            rms_dbfs = -np.inf

        # Peak in dBFS
        if peak_amplitude > 0:
            peak_dbfs = 20 * np.log10(peak_amplitude)
        else:
            peak_dbfs = -np.inf

        # Frame-wise RMS
        frame_rms = self.calculate_rms_energy()
        mean_frame_rms = np.mean(frame_rms)
        max_frame_rms = np.max(frame_rms)

        # Frame RMS in dB
        if mean_frame_rms > 0:
            mean_frame_rms_db = 20 * np.log10(mean_frame_rms)
        else:
            mean_frame_rms_db = -np.inf

        if max_frame_rms > 0:
            max_frame_rms_db = 20 * np.log10(max_frame_rms)
        else:
            max_frame_rms_db = -np.inf

        # Estimate SPL (assuming 94 dB SPL = 0 dBFS calibration)
        spl_estimate = 94.0 + rms_dbfs

        # Dynamic range
        noise_floor = np.percentile(np.abs(self.audio_data), 0.1)
        if noise_floor > 0:
            noise_floor_db = 20 * np.log10(noise_floor)
            dynamic_range = peak_dbfs - noise_floor_db
        else:
            dynamic_range = np.inf

        return {
            'overall_rms': overall_rms,
            'peak_amplitude': peak_amplitude,
            'rms_dbfs': rms_dbfs,
            'peak_dbfs': peak_dbfs,
            'mean_frame_rms_db': mean_frame_rms_db,
            'max_frame_rms_db': max_frame_rms_db,
            'spl_estimate': spl_estimate,
            'dynamic_range': dynamic_range
        }

    def calculate_loudness_lufs_style(self):
        """
        Calculate loudness similar to LUFS (perceptual loudness).
        This is a simplified version using frequency weighting.

        Returns:
            Estimated loudness in LUFS-like units
        """
        # Compute power spectrogram
        S = np.abs(librosa.stft(self.audio_data)) ** 2

        # Frequency bins
        freqs = librosa.fft_frequencies(sr=self.sample_rate)

        # K-weighting approximation (simplified)
        # Emphasize mid frequencies (1-4 kHz) which are important for perception
        k_weight = np.ones_like(freqs)
        k_weight[(freqs >= 1000) & (freqs <= 4000)] = 2.0

        # Apply weighting
        S_weighted = S * k_weight[:, np.newaxis]

        # Mean power
        mean_power = np.mean(S_weighted)

        # Convert to loudness (LUFS-like)
        if mean_power > 0:
            loudness = -0.691 + 10 * np.log10(mean_power)
        else:
            loudness = -np.inf

        return loudness

    def classify_loudness(self, spl_db):
        """
        Classify loudness level based on SPL.

        Args:
            spl_db: Sound pressure level in dB

        Returns:
            Loudness classification string
        """
        if spl_db < 30:
            return "Very Quiet"
        elif spl_db < 50:
            return "Quiet"
        elif spl_db < 70:
            return "Moderate"
        elif spl_db < 85:
            return "Loud"
        elif spl_db < 100:
            return "Very Loud (Hearing risk)"
        elif spl_db < 120:
            return "Extremely Loud (Immediate damage)"
        else:
            return "Painful (Severe damage)"

    def analyze(self):
        """
        Perform comprehensive analysis and return results.

        Returns:
            Dictionary with all analysis results
        """
        db_metrics = self.calculate_db_metrics()
        loudness = self.calculate_loudness_lufs_style()

        # Additional features
        spectral_centroid = self.calculate_spectral_centroid()
        zcr = self.calculate_zcr()

        results = {
            'db_metrics': db_metrics,
            'loudness_lufs': loudness,
            'spectral_centroid_mean': np.mean(spectral_centroid),
            'spectral_centroid_std': np.std(spectral_centroid),
            'zcr_mean': np.mean(zcr),
            'zcr_std': np.std(zcr),
            'classification': self.classify_loudness(db_metrics['spl_estimate'])
        }

        return results

    def print_analysis(self):
        """Print comprehensive analysis."""
        results = self.analyze()
        db = results['db_metrics']

        print("\n" + "=" * 80)
        print("LIBROSA INTENSITY ANALYSIS")
        print("=" * 80)

        print(f"\nFile: {os.path.basename(self.audio_path)}")

        print(f"\nAmplitude Metrics:")
        print(f"  Overall RMS: {db['overall_rms']:.6f}")
        print(f"  Peak Amplitude: {db['peak_amplitude']:.6f}")

        print(f"\nDecibel Metrics (dBFS):")
        print(f"  Overall RMS: {db['rms_dbfs']:.2f} dBFS")
        print(f"  Peak Level: {db['peak_dbfs']:.2f} dBFS")
        print(f"  Mean Frame RMS: {db['mean_frame_rms_db']:.2f} dBFS")
        print(f"  Max Frame RMS: {db['max_frame_rms_db']:.2f} dBFS")
        print(f"  Dynamic Range: {db['dynamic_range']:.2f} dB")

        print(f"\nSound Pressure Level (SPL) Estimate:")
        print(f"  SPL: {db['spl_estimate']:.2f} dB SPL")
        print(f"  Classification: {results['classification']}")

        print(f"\nPerceptual Loudness:")
        print(f"  LUFS-style: {results['loudness_lufs']:.2f} LUFS")

        print(f"\nSpectral Features:")
        print(f"  Spectral Centroid: {results['spectral_centroid_mean']:.2f} Hz (±{results['spectral_centroid_std']:.2f})")
        print(f"  Zero-Crossing Rate: {results['zcr_mean']:.4f} (±{results['zcr_std']:.4f})")

        # Visual bar
        self._print_intensity_bar(db['rms_dbfs'])

        print("=" * 80)

        return results

    def _print_intensity_bar(self, db_level):
        """Print visual bar for intensity level."""
        # Map dBFS (-60 to 0) to bar (0 to 50 chars)
        normalized = max(0, min(60, db_level + 60)) / 60
        bar_length = int(normalized * 50)
        bar = '█' * bar_length + '░' * (50 - bar_length)

        print(f"\nIntensity Visualization:")
        print(f"  {db_level:>6.2f} dBFS  |{bar}|")
        print(f"  {'Quiet':<13} {'│':<20} {'│':<15} {'Loud':>13}")


def compare_with_expected(audio_path, expected_db, tolerance=5.0):
    """
    Analyze audio and compare with expected dB value.

    Args:
        audio_path: Path to audio file
        expected_db: Expected SPL in dB
        tolerance: Acceptable tolerance in dB

    Returns:
        Boolean indicating if measured value is within tolerance
    """
    analyzer = LibrosaIntensityAnalyzer(audio_path)
    results = analyzer.print_analysis()

    measured_spl = results['db_metrics']['spl_estimate']
    difference = abs(measured_spl - expected_db)

    print("\n" + "=" * 80)
    print("COMPARISON WITH EXPECTED VALUE")
    print("=" * 80)
    print(f"  Expected SPL: {expected_db:.2f} dB")
    print(f"  Measured SPL: {measured_spl:.2f} dB")
    print(f"  Difference: {difference:.2f} dB")
    print(f"  Tolerance: ±{tolerance:.2f} dB")

    if difference <= tolerance:
        print(f"\n  ✓ PASS: Measured value within tolerance")
        status = True
    else:
        print(f"\n  ✗ FAIL: Measured value outside tolerance")
        status = False

    print("=" * 80)

    return status, measured_spl


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python librosa_intensity_analysis.py <audio_file>")
        print("  python librosa_intensity_analysis.py <audio_file> <expected_db>")
        print("\nExample:")
        print("  python librosa_intensity_analysis.py test_loud.wav 85")
        sys.exit(1)

    audio_path = sys.argv[1]

    if not os.path.exists(audio_path):
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        # Compare with expected value
        try:
            expected_db = float(sys.argv[2])
            compare_with_expected(audio_path, expected_db)
        except ValueError:
            print(f"Error: Invalid expected dB value: {sys.argv[2]}")
            sys.exit(1)
    else:
        # Just analyze
        analyzer = LibrosaIntensityAnalyzer(audio_path)
        analyzer.print_analysis()


if __name__ == "__main__":
    main()
