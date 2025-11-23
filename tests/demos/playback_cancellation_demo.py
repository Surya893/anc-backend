"""
PyAudio Playback Demonstration for Active Noise Cancellation
Listen to noise, anti-noise, and the cancellation effect.
"""

import numpy as np
import pyaudio
import wave
import time
from pathlib import Path
from anti_noise_generator import AntiNoiseGenerator


class CancellationPlayback:
    """Playback demonstration for ANC cancellation."""

    def __init__(self, sample_rate=44100):
        """Initialize playback system."""
        self.sample_rate = sample_rate
        self.p = pyaudio.PyAudio()
        self.generator = AntiNoiseGenerator(sample_rate=sample_rate)

        # Audio format
        self.format = pyaudio.paFloat32
        self.channels = 1

    def __del__(self):
        """Cleanup PyAudio."""
        if hasattr(self, 'p'):
            self.p.terminate()

    def play_audio(self, audio_data, description="Audio"):
        """
        Play audio through speakers.

        Args:
            audio_data: Audio waveform (numpy array)
            description: Description for user
        """
        print(f"\n▶ Playing: {description}")
        print(f"  Duration: {len(audio_data)/self.sample_rate:.2f}s")
        print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")

        # Normalize to prevent clipping
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            normalized = audio_data / max_val * 0.9  # 90% to prevent clipping
        else:
            normalized = audio_data

        # Convert to float32
        audio_float32 = normalized.astype(np.float32)

        # Open stream
        stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            output=True
        )

        # Play audio
        stream.write(audio_float32.tobytes())

        # Cleanup
        stream.stop_stream()
        stream.close()

        print(f"  ✓ Playback complete")

    def play_cancellation_sequence(self, noise_signal, pause_duration=1.0):
        """
        Play cancellation demonstration sequence:
        1. Original noise
        2. Anti-noise (phase inverted)
        3. Combined (should be silent or very quiet)

        Args:
            noise_signal: Original noise waveform
            pause_duration: Pause between playbacks (seconds)
        """
        print("\n" + "="*80)
        print("ACTIVE NOISE CANCELLATION PLAYBACK DEMONSTRATION")
        print("="*80)

        # Generate anti-noise
        anti_noise = self.generator.generate_anti_noise(noise_signal)

        # Combine for cancellation
        combined = noise_signal + anti_noise

        # Verify cancellation
        is_cancelled, metrics = self.generator.verify_cancellation(
            noise_signal, anti_noise
        )

        print(f"\nCancellation Metrics:")
        print(f"  Original RMS: {metrics['original_rms']:.6f}")
        print(f"  Anti-Noise RMS: {metrics['anti_noise_rms']:.6f}")
        print(f"  Combined RMS: {metrics['result_rms']:.6e}")
        print(f"  Noise Reduction: {metrics['noise_reduction_db']:.2f} dB")
        print(f"  Perfect Cancellation: {'✓ YES' if is_cancelled else '✗ NO'}")

        print("\n" + "="*80)
        print("PLAYBACK SEQUENCE")
        print("="*80)

        # 1. Play original noise
        print(f"\n[1/3] Original Noise")
        print("─"*80)
        self.play_audio(noise_signal, "Original Noise")

        print(f"\nPausing {pause_duration}s...")
        time.sleep(pause_duration)

        # 2. Play anti-noise
        print(f"\n[2/3] Anti-Noise (Phase Inverted)")
        print("─"*80)
        print("NOTE: Anti-noise should sound identical to original")
        print("      (Same amplitude, but 180° out of phase)")
        self.play_audio(anti_noise, "Anti-Noise (Phase Inverted)")

        print(f"\nPausing {pause_duration}s...")
        time.sleep(pause_duration)

        # 3. Play combined (cancelled)
        print(f"\n[3/3] Combined Signal (Noise + Anti-Noise)")
        print("─"*80)
        print("NOTE: This should be SILENT or very quiet")
        print("      (Destructive interference cancels the sound)")
        self.play_audio(combined, "Combined (Cancelled)")

        print("\n" + "="*80)
        print("PLAYBACK DEMONSTRATION COMPLETE")
        print("="*80)
        print(f"\nExpected result: Step 3 should be {metrics['noise_reduction_db']:.2f} dB quieter")
        print("                (Should hear silence or near-silence)")
        print("="*80)

    def load_and_play_wav(self, wav_path):
        """
        Load WAV file and demonstrate cancellation.

        Args:
            wav_path: Path to WAV file
        """
        print(f"\n{'='*80}")
        print(f"Loading: {wav_path}")
        print(f"{'='*80}")

        # Load WAV
        noise = self.generator.load_noise_from_wav(wav_path)

        print(f"✓ Loaded {len(noise)} samples at {self.generator.sample_rate} Hz")

        # Play cancellation sequence
        self.play_cancellation_sequence(noise)

    def play_generated_tones(self):
        """Generate and play test tones with cancellation."""
        print("\n" + "="*80)
        print("GENERATED TONE CANCELLATION TEST")
        print("="*80)

        # Test different frequencies
        frequencies = [
            (440, "A4 Note (Musical)"),
            (1000, "1 kHz Tone (Reference)"),
            (250, "Low Frequency Hum"),
        ]

        for freq, description in frequencies:
            print(f"\n{'─'*80}")
            print(f"Frequency: {freq} Hz - {description}")
            print(f"{'─'*80}")

            # Generate tone
            duration = 2.0
            t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
            noise = 0.5 * np.sin(2 * np.pi * freq * t)

            # Play cancellation sequence
            self.play_cancellation_sequence(noise, pause_duration=0.5)

            print(f"\nPausing 2s before next frequency...")
            time.sleep(2.0)

    def play_real_world_scenarios(self):
        """Play real-world noise scenarios with cancellation."""
        print("\n" + "="*80)
        print("REAL-WORLD SCENARIO CANCELLATION TEST")
        print("="*80)

        scenarios = [
            {
                'name': 'Office HVAC Hum (60 Hz + harmonics)',
                'generator': lambda: self._generate_hvac_noise()
            },
            {
                'name': 'Traffic Rumble (Low frequency)',
                'generator': lambda: self._generate_traffic_noise()
            },
            {
                'name': 'Aircraft Cabin Drone',
                'generator': lambda: self._generate_aircraft_noise()
            },
        ]

        for scenario in scenarios:
            print(f"\n{'─'*80}")
            print(f"Scenario: {scenario['name']}")
            print(f"{'─'*80}")

            noise = scenario['generator']()
            self.play_cancellation_sequence(noise, pause_duration=0.5)

            print(f"\nPausing 2s before next scenario...")
            time.sleep(2.0)

    def _generate_hvac_noise(self, duration=3.0):
        """Generate HVAC-like noise."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)

        # 60 Hz hum + harmonics
        noise = 0.5 * np.sin(2 * np.pi * 60 * t)
        noise += 0.3 * np.sin(2 * np.pi * 120 * t)
        noise += 0.2 * np.sin(2 * np.pi * 180 * t)
        noise += 0.1 * np.random.randn(len(t))

        return noise

    def _generate_traffic_noise(self, duration=3.0):
        """Generate traffic-like noise."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)

        # Low frequency rumble
        noise = 0.4 * np.sin(2 * np.pi * 80 * t)
        noise += 0.3 * np.sin(2 * np.pi * 120 * t)
        noise += 0.2 * np.sin(2 * np.pi * 150 * t)
        noise += 0.15 * np.random.randn(len(t))

        return noise

    def _generate_aircraft_noise(self, duration=3.0):
        """Generate aircraft cabin-like noise."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)

        # Constant drone
        noise = 0.4 * np.sin(2 * np.pi * 200 * t)
        noise += 0.2 * np.sin(2 * np.pi * 400 * t)
        noise += 0.15 * np.random.randn(len(t))

        return noise

    def interactive_demo(self):
        """Interactive demonstration menu."""
        print("\n" + "="*80)
        print("INTERACTIVE CANCELLATION PLAYBACK DEMO")
        print("="*80)
        print("\nThis demo will play:")
        print("  1. Original noise")
        print("  2. Anti-noise (phase inverted)")
        print("  3. Combined signal (should be silent)")
        print("\nExpected: Step 3 should be much quieter than steps 1 and 2")
        print("="*80)

        while True:
            print("\n" + "─"*80)
            print("Select demo:")
            print("  1. Test with WAV files")
            print("  2. Generated tone tests (440 Hz, 1 kHz, 250 Hz)")
            print("  3. Real-world scenarios (HVAC, traffic, aircraft)")
            print("  4. Quick single tone test (440 Hz)")
            print("  0. Exit")
            print("─"*80)

            try:
                choice = input("\nEnter choice (0-4): ").strip()

                if choice == '0':
                    print("\nExiting demo...")
                    break

                elif choice == '1':
                    # Test with WAV files
                    wav_files = list(Path('.').glob('test_*.wav'))

                    if not wav_files:
                        print("\n⚠ No test WAV files found in current directory")
                        continue

                    print(f"\nFound {len(wav_files)} test WAV files:")
                    for i, wav in enumerate(wav_files, 1):
                        print(f"  {i}. {wav.name}")

                    wav_choice = input(f"\nSelect file (1-{len(wav_files)}): ").strip()
                    try:
                        idx = int(wav_choice) - 1
                        if 0 <= idx < len(wav_files):
                            self.load_and_play_wav(str(wav_files[idx]))
                        else:
                            print("Invalid selection")
                    except ValueError:
                        print("Invalid input")

                elif choice == '2':
                    self.play_generated_tones()

                elif choice == '3':
                    self.play_real_world_scenarios()

                elif choice == '4':
                    # Quick test
                    print("\n" + "="*80)
                    print("QUICK TEST: 440 Hz Tone (2 seconds)")
                    print("="*80)

                    t = np.linspace(0, 2, int(self.sample_rate * 2), endpoint=False)
                    noise = 0.5 * np.sin(2 * np.pi * 440 * t)

                    self.play_cancellation_sequence(noise, pause_duration=0.5)

                else:
                    print("Invalid choice. Please enter 0-4.")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Exiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                import traceback
                traceback.print_exc()


def automated_demo():
    """Run automated demonstration without user interaction."""
    print("\n" + "="*80)
    print("AUTOMATED CANCELLATION PLAYBACK DEMONSTRATION")
    print("="*80)
    print("\nRunning automated test sequence...")
    print("This will play several examples with pauses between them.")
    print("="*80)

    playback = CancellationPlayback()

    # Test 1: Simple tone
    print("\n\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TEST 1: 440 Hz Pure Tone" + " "*34 + "║")
    print("╚" + "="*78 + "╝")

    t = np.linspace(0, 2, int(playback.sample_rate * 2), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 440 * t)
    playback.play_cancellation_sequence(tone, pause_duration=1.0)

    print("\n\nPausing 3 seconds before next test...")
    time.sleep(3.0)

    # Test 2: HVAC noise
    print("\n\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TEST 2: Office HVAC Hum" + " "*35 + "║")
    print("╚" + "="*78 + "╝")

    hvac = playback._generate_hvac_noise(duration=2.0)
    playback.play_cancellation_sequence(hvac, pause_duration=1.0)

    print("\n\n" + "="*80)
    print("AUTOMATED DEMO COMPLETE")
    print("="*80)
    print("\nYou should have heard:")
    print("  Test 1: Clear 440 Hz tone → anti-noise → silence")
    print("  Test 2: HVAC hum → anti-noise → silence")
    print("\nIf step 3 was silent in each test, cancellation is working!")
    print("="*80)


def main():
    """Main entry point."""
    import sys

    print("\n" + "="*80)
    print("PYAUDIO CANCELLATION PLAYBACK - ACTIVE NOISE CANCELLATION")
    print("="*80)
    print("\nThis script demonstrates noise cancellation through audio playback.")
    print("You will hear the cancellation effect in real-time.")
    print("="*80)

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'auto':
            # Automated demo
            automated_demo()
        elif sys.argv[1].endswith('.wav'):
            # Play specific WAV file
            playback = CancellationPlayback()
            playback.load_and_play_wav(sys.argv[1])
        else:
            print(f"\nUsage:")
            print(f"  {sys.argv[0]}              # Interactive menu")
            print(f"  {sys.argv[0]} auto         # Automated demo")
            print(f"  {sys.argv[0]} file.wav     # Play specific WAV")
            sys.exit(1)
    else:
        # Interactive demo
        try:
            playback = CancellationPlayback()
            playback.interactive_demo()
        except KeyboardInterrupt:
            print("\n\nExiting...")

    print("\n" + "="*80)
    print("Thank you for testing the ANC cancellation system!")
    print("="*80)


if __name__ == "__main__":
    main()
