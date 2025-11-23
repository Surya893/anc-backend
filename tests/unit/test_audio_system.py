"""
Test script for audio capture system (without requiring real audio hardware).
Simulates audio recordings and tests database integration.
"""

import numpy as np
import wave
import os
from datetime import datetime
from database_schema import ANCDatabase


class SimulatedAudioCapture:
    """
    Simulated audio capture for testing purposes.
    Generates synthetic audio data instead of recording from microphone.
    """

    def __init__(self, db_path="anc_system.db", output_dir="recordings"):
        self.CHUNK = 1024
        self.FORMAT = 16  # 16-bit
        self.CHANNELS = 1
        self.RATE = 44100

        self.frames = []
        self.db = ANCDatabase(db_path)
        self.output_dir = output_dir

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        print("✓ Simulated Audio Capture initialized")

    def generate_noise_sample(self, duration_seconds, noise_type="ambient"):
        """
        Generate synthetic noise for testing.

        Args:
            duration_seconds: Duration of sample
            noise_type: Type of noise (ambient, white, pink, office, street)
        """
        num_samples = int(self.RATE * duration_seconds)
        time_vector = np.linspace(0, duration_seconds, num_samples)

        if noise_type == "ambient":
            # Low-frequency ambient noise
            signal = 0.1 * np.sin(2 * np.pi * 60 * time_vector)  # 60 Hz hum
            signal += 0.05 * np.random.randn(num_samples)  # Random noise
            signal += 0.02 * np.sin(2 * np.pi * 120 * time_vector)  # 120 Hz harmonic

        elif noise_type == "white":
            # White noise
            signal = 0.3 * np.random.randn(num_samples)

        elif noise_type == "pink":
            # Pink noise (1/f noise) - simplified version
            white = np.random.randn(num_samples)
            # Simple low-pass filter approximation
            signal = np.zeros(num_samples)
            signal[0] = white[0]
            for i in range(1, num_samples):
                signal[i] = 0.9 * signal[i-1] + 0.1 * white[i]
            signal *= 0.2

        elif noise_type == "office":
            # Office environment: HVAC + computer fans + occasional activity
            signal = 0.08 * np.sin(2 * np.pi * 60 * time_vector)  # HVAC hum
            signal += 0.03 * np.random.randn(num_samples)  # Background noise
            # Random typing sounds
            for _ in range(int(duration_seconds * 5)):
                pos = np.random.randint(0, num_samples - 100)
                signal[pos:pos+100] += 0.5 * np.random.rand() * np.exp(-np.linspace(0, 5, 100))

        elif noise_type == "street":
            # Street environment: traffic + wind + occasional honks
            signal = 0.15 * np.random.randn(num_samples)  # Wind and general noise
            # Low-frequency traffic rumble
            for freq in [50, 100, 150]:
                signal += 0.05 * np.sin(2 * np.pi * freq * time_vector)
            # Random car passes
            for _ in range(int(duration_seconds * 2)):
                pos = np.random.randint(0, num_samples - 1000)
                envelope = np.concatenate([
                    np.linspace(0, 1, 500),
                    np.linspace(1, 0, 500)
                ])
                signal[pos:pos+1000] += 0.3 * envelope * np.sin(2 * np.pi * 200 * time_vector[pos:pos+1000])

        else:
            # Default: simple random noise
            signal = 0.2 * np.random.randn(num_samples)

        # Normalize to prevent clipping
        signal = np.clip(signal, -1.0, 1.0)

        # Convert to 16-bit PCM
        signal_int16 = (signal * 32767).astype(np.int16)

        # Convert to bytes and store in frames
        self.frames = [signal_int16.tobytes()]

        return signal

    def get_audio_array(self):
        """Get audio data as numpy array."""
        if not self.frames:
            return np.array([])

        audio_bytes = b''.join(self.frames)
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float = audio_int16.astype(np.float64) / 32768.0

        return audio_float

    def save_wav(self, filename=None):
        """Save as WAV file."""
        if not self.frames:
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sim_recording_{timestamp}.wav"

        if not filename.endswith('.wav'):
            filename += '.wav'

        filepath = os.path.join(self.output_dir, filename)

        wf = wave.open(filepath, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        print(f"  WAV saved: {filepath}")
        return filepath

    def calculate_noise_level(self, audio_data):
        """Calculate noise level in dB."""
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms > 0:
            db = 20 * np.log10(rms)
        else:
            db = -np.inf
        return db

    def save_to_database(self, environment_type, location, description, save_wav=True):
        """Save to database."""
        if not self.frames:
            return None

        audio_data = self.get_audio_array()
        num_samples = len(audio_data)
        duration_seconds = num_samples / self.RATE
        noise_level_db = self.calculate_noise_level(audio_data)

        wav_path = None
        if save_wav:
            wav_path = self.save_wav()

        recording_id = self.db.insert_noise_recording(
            duration_seconds=duration_seconds,
            sampling_rate=self.RATE,
            num_samples=num_samples,
            environment_type=environment_type,
            noise_level_db=noise_level_db,
            location=location,
            description=description,
            metadata={
                "simulated": True,
                "wav_file": wav_path,
                "captured_at": datetime.now().isoformat()
            }
        )

        waveform_id = self.db.insert_waveform(
            recording_id=recording_id,
            waveform_type="ambient_noise",
            waveform_array=audio_data
        )

        # Save spectral analysis
        fft_size = min(2048, len(audio_data))
        fft_data = np.fft.rfft(audio_data[:fft_size])
        freqs = np.fft.rfftfreq(fft_size, 1.0 / self.RATE)
        magnitude = np.abs(fft_data)
        phase = np.angle(fft_data)

        self.db.insert_spectral_analysis(
            recording_id=recording_id,
            waveform_type="ambient_noise",
            frequency_data=freqs,
            magnitude_data=magnitude,
            phase_data=phase,
            fft_size=fft_size,
            window_function="none"
        )

        return recording_id

    def cleanup(self):
        """Cleanup resources."""
        self.db.close()


def test_basic_capture():
    """Test 1: Basic audio capture and storage."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Audio Capture")
    print("=" * 80)

    capture = SimulatedAudioCapture()

    # Generate and save a simple recording
    print("\nGenerating 3-second ambient noise sample...")
    capture.generate_noise_sample(duration_seconds=3, noise_type="ambient")

    print("Saving to database...")
    recording_id = capture.save_to_database(
        environment_type="test_lab",
        location="Test Environment",
        description="Test recording - ambient noise",
        save_wav=True
    )

    print(f"\n✓ Test 1 passed! Recording ID: {recording_id}")
    capture.cleanup()


def test_multiple_environments():
    """Test 2: Multiple environment recordings."""
    print("\n" + "=" * 80)
    print("TEST 2: Multiple Environment Recordings")
    print("=" * 80)

    capture = SimulatedAudioCapture()

    environments = [
        ("office", "Office Building A", "ambient", "HVAC and computer noise"),
        ("office", "Office Building A", "office", "Typical office environment"),
        ("street", "Main Street", "street", "Traffic and pedestrian noise"),
        ("home", "Living Room", "ambient", "Quiet home environment"),
        ("park", "Central Park", "pink", "Natural ambient noise"),
    ]

    recording_ids = []

    for env_type, location, noise_type, description in environments:
        print(f"\nRecording: {env_type} - {location}")
        capture.generate_noise_sample(duration_seconds=2, noise_type=noise_type)

        recording_id = capture.save_to_database(
            environment_type=env_type,
            location=location,
            description=description,
            save_wav=True
        )

        recording_ids.append(recording_id)
        print(f"  ✓ Saved as Recording ID: {recording_id}")

    print(f"\n✓ Test 2 passed! Created {len(recording_ids)} recordings")
    capture.cleanup()

    return recording_ids


def test_frequent_patterns():
    """Test 3: Frequent pattern analysis."""
    print("\n" + "=" * 80)
    print("TEST 3: Frequent Pattern Analysis")
    print("=" * 80)

    from frequent_noise_manager import FrequentNoiseManager

    manager = FrequentNoiseManager()

    # Get statistics
    stats = manager.get_noise_statistics()
    print(f"\nTotal recordings in database: {stats['total_recordings']}")

    # Get frequent patterns
    patterns = manager.identify_frequent_patterns(min_occurrences=2)

    print("\nFrequent environments:")
    for env, count in patterns['environments'].items():
        print(f"  {env}: {count} recordings")

    print("\nFrequent locations:")
    for loc, count in patterns['locations'].items():
        print(f"  {loc}: {count} recordings")

    # Create profile for office environment
    if 'office' in patterns['environments']:
        print("\nOffice environment profile:")
        profile = manager.create_noise_profile('office')
        print(f"  Sample count: {profile['sample_count']}")
        print(f"  Avg duration: {profile['avg_duration']:.2f}s")
        if profile['avg_noise_level_db']:
            print(f"  Avg noise level: {profile['avg_noise_level_db']:.2f} dB")

    print(f"\n✓ Test 3 passed!")
    manager.close()


def test_database_queries():
    """Test 4: Database query operations."""
    print("\n" + "=" * 80)
    print("TEST 4: Database Queries")
    print("=" * 80)

    db = ANCDatabase("anc_system.db")

    # Get all recordings
    recordings = db.get_all_recordings()
    print(f"\nTotal recordings: {len(recordings)}")

    if recordings:
        # Show latest recording
        latest = recordings[0]
        print(f"\nLatest recording:")
        print(f"  ID: {latest[0]}")
        print(f"  Timestamp: {latest[1]}")
        print(f"  Duration: {latest[2]:.2f}s")
        print(f"  Sample rate: {latest[3]} Hz")
        print(f"  Environment: {latest[5]}")
        print(f"  Location: {latest[7]}")

        # Get waveform data for latest recording
        db.cursor.execute("""
            SELECT waveform_id, waveform_type, num_samples, mean_amplitude
            FROM audio_waveforms
            WHERE recording_id = ?
        """, (latest[0],))
        waveforms = db.cursor.fetchall()

        print(f"\nWaveforms for this recording: {len(waveforms)}")
        for wf in waveforms:
            print(f"  {wf[1]}: {wf[2]} samples, mean={wf[3]:.6f}")

    print(f"\n✓ Test 4 passed!")
    db.close()


def run_all_tests():
    """Run all tests."""
    print("=" * 80)
    print("AUDIO CAPTURE SYSTEM - TEST SUITE")
    print("=" * 80)

    try:
        test_basic_capture()
        test_multiple_environments()
        test_frequent_patterns()
        test_database_queries()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✓")
        print("=" * 80)

        # Show summary
        from frequent_noise_manager import FrequentNoiseManager
        manager = FrequentNoiseManager()
        manager.print_report()
        manager.close()

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
