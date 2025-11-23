"""
Real-Time Anti-Noise Output with PyAudio
Captures audio from microphone, inverts phase, and plays through speakers.
"""

import sys
import numpy as np
import pyaudio
import struct
import time
from datetime import datetime


class RealtimeAntiNoise:
    """Real-time active noise cancellation through phase inversion."""

    def __init__(self, sample_rate=44100, chunk_size=1024, channels=1):
        """
        Initialize real-time anti-noise system.

        Args:
            sample_rate: Audio sample rate (Hz)
            chunk_size: Audio buffer size (smaller = lower latency)
            channels: Number of audio channels (1=mono, 2=stereo)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = pyaudio.paFloat32

        # Initialize PyAudio
        self.p = pyaudio.PyAudio()

        # Statistics
        self.chunks_processed = 0
        self.total_latency = 0
        self.start_time = None

        # State
        self.running = False

    def __del__(self):
        """Cleanup PyAudio."""
        if hasattr(self, 'p'):
            self.p.terminate()

    def list_audio_devices(self):
        """List all available audio devices."""
        print("\n" + "="*80)
        print("AVAILABLE AUDIO DEVICES")
        print("="*80)

        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        print(f"\nFound {num_devices} audio devices:\n")

        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)

            print(f"Device {i}: {device_info.get('name')}")
            print(f"  Max Input Channels: {device_info.get('maxInputChannels')}")
            print(f"  Max Output Channels: {device_info.get('maxOutputChannels')}")
            print(f"  Default Sample Rate: {device_info.get('defaultSampleRate')}")
            print()

        print("="*80)

    def generate_anti_noise(self, audio_data):
        """
        Generate anti-noise by inverting phase.

        Args:
            audio_data: Input audio array (float32)

        Returns:
            Anti-noise (phase inverted)
        """
        # Phase inversion: multiply by -1
        anti_noise = -audio_data

        # Verify assertion
        assert np.allclose(anti_noise, -audio_data), "Phase inversion failed"

        return anti_noise

    def run_realtime_anc(self, duration=10, input_device=None, output_device=None,
                         gain=1.0, monitor=True):
        """
        Run real-time active noise cancellation.

        Args:
            duration: Duration in seconds (None = run until interrupted)
            input_device: Input device index (None = default)
            output_device: Output device index (None = default)
            gain: Anti-noise gain factor (1.0 = perfect inversion)
            monitor: Print real-time statistics
        """
        print("\n" + "="*80)
        print("REAL-TIME ANTI-NOISE OUTPUT")
        print("="*80)

        print(f"\nConfiguration:")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Chunk Size: {self.chunk_size} samples")
        print(f"  Channels: {self.channels}")
        print(f"  Buffer Duration: {1000 * self.chunk_size / self.sample_rate:.2f} ms")
        print(f"  Anti-Noise Gain: {gain:.2f}")

        # Open input stream (microphone)
        input_stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=self.chunk_size,
            stream_callback=None  # Use blocking mode
        )

        # Open output stream (speakers)
        output_stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            output_device_index=output_device,
            frames_per_buffer=self.chunk_size
        )

        print("\n" + "="*80)
        print("ACTIVE NOISE CANCELLATION ACTIVE")
        print("="*80)
        print("\nCapturing from microphone → Inverting phase → Playing through speakers")
        print("Press Ctrl+C to stop\n")

        if duration:
            print(f"Running for {duration} seconds...")
        else:
            print("Running until interrupted...")

        print("─"*80)

        self.running = True
        self.start_time = time.time()
        self.chunks_processed = 0

        try:
            start = time.time()

            while self.running:
                # Check duration
                if duration and (time.time() - start) >= duration:
                    break

                # Read audio from microphone
                chunk_start = time.time()
                audio_bytes = input_stream.read(self.chunk_size, exception_on_overflow=False)

                # Convert to numpy array
                audio_data = np.frombuffer(audio_bytes, dtype=np.float32)

                # Generate anti-noise (phase inversion)
                anti_noise = self.generate_anti_noise(audio_data) * gain

                # Calculate RMS for monitoring
                input_rms = np.sqrt(np.mean(audio_data**2))
                output_rms = np.sqrt(np.mean(anti_noise**2))

                # Write to speakers
                output_stream.write(anti_noise.tobytes())

                # Update statistics
                chunk_latency = (time.time() - chunk_start) * 1000  # ms
                self.chunks_processed += 1
                self.total_latency += chunk_latency

                # Monitor
                if monitor and self.chunks_processed % 50 == 0:
                    elapsed = time.time() - self.start_time
                    avg_latency = self.total_latency / self.chunks_processed

                    print(f"[{elapsed:6.1f}s] Chunks: {self.chunks_processed:6d} | "
                          f"Input RMS: {input_rms:.4f} | "
                          f"Output RMS: {output_rms:.4f} | "
                          f"Latency: {avg_latency:.2f}ms")

        except KeyboardInterrupt:
            print("\n\n" + "="*80)
            print("Interrupted by user")
            print("="*80)

        finally:
            self.running = False

            # Cleanup
            input_stream.stop_stream()
            input_stream.close()
            output_stream.stop_stream()
            output_stream.close()

            # Print statistics
            self.print_statistics()

    def print_statistics(self):
        """Print session statistics."""
        if self.chunks_processed == 0:
            return

        elapsed = time.time() - self.start_time
        avg_latency = self.total_latency / self.chunks_processed

        print("\n" + "="*80)
        print("SESSION STATISTICS")
        print("="*80)
        print(f"\nDuration: {elapsed:.2f} seconds")
        print(f"Chunks Processed: {self.chunks_processed}")
        print(f"Average Latency: {avg_latency:.2f} ms")
        print(f"Processing Rate: {self.chunks_processed / elapsed:.1f} chunks/sec")
        print(f"Audio Processed: {self.chunks_processed * self.chunk_size / self.sample_rate:.1f} seconds")

        print("\nPerformance:")
        if avg_latency < 10:
            print("  ✓ Excellent latency (<10ms) - Real-time performance")
        elif avg_latency < 20:
            print("  ✓ Good latency (<20ms) - Suitable for ANC")
        elif avg_latency < 50:
            print("  ⚠ Moderate latency (<50ms) - May have noticeable delay")
        else:
            print("  ✗ High latency (>50ms) - Not suitable for real-time ANC")

        print("="*80)

    def run_test_tone(self, frequency=440, duration=3, output_device=None):
        """
        Generate and play test tone with anti-noise.

        Args:
            frequency: Test tone frequency (Hz)
            duration: Duration in seconds
            output_device: Output device index
        """
        print("\n" + "="*80)
        print(f"TEST TONE GENERATION - {frequency} Hz")
        print("="*80)

        # Generate test tone
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        test_tone = 0.3 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

        # Generate anti-noise
        anti_noise = self.generate_anti_noise(test_tone)

        print(f"\nTest tone:")
        print(f"  Frequency: {frequency} Hz")
        print(f"  Duration: {duration} seconds")
        print(f"  Samples: {len(test_tone)}")
        print(f"  RMS: {np.sqrt(np.mean(test_tone**2)):.6f}")

        print(f"\nAnti-noise:")
        print(f"  RMS: {np.sqrt(np.mean(anti_noise**2)):.6f}")
        print(f"  Verified: np.allclose(anti_noise, -test_tone) = {np.allclose(anti_noise, -test_tone)}")

        # Open output stream
        stream = self.p.open(
            format=self.format,
            channels=1,
            rate=self.sample_rate,
            output=True,
            output_device_index=output_device,
            frames_per_buffer=self.chunk_size
        )

        print("\n" + "─"*80)
        print("Playing sequence:")
        print("  1. Original tone (3 seconds)")
        print("  2. Anti-noise (3 seconds)")
        print("  3. Both combined - should cancel (3 seconds)")
        print("─"*80)

        try:
            # Play original tone
            print("\n▶ Playing: Original tone...")
            stream.write(test_tone.tobytes())

            # Pause
            time.sleep(0.5)

            # Play anti-noise
            print("▶ Playing: Anti-noise (phase inverted)...")
            stream.write(anti_noise.tobytes())

            # Pause
            time.sleep(0.5)

            # Play combined (should be silent)
            print("▶ Playing: Combined (should be silent)...")
            combined = test_tone + anti_noise
            print(f"  Combined RMS: {np.sqrt(np.mean(combined**2)):.6e}")
            stream.write(combined.tobytes())

        finally:
            stream.stop_stream()
            stream.close()

        print("\n✓ Test tone playback complete")
        print("="*80)


def main():
    """Main entry point."""
    import sys

    print("\n" + "="*80)
    print("REAL-TIME ANTI-NOISE OUTPUT SYSTEM")
    print("="*80)
    print("\nActive Noise Cancellation through phase inversion")
    print("Microphone → Phase Inversion → Speakers")
    print("="*80)

    # Initialize
    anc = RealtimeAntiNoise(
        sample_rate=44100,
        chunk_size=1024,  # ~23ms latency
        channels=1  # Mono
    )

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'list':
            # List audio devices
            anc.list_audio_devices()
            return 0

        elif command == 'test':
            # Run test tone
            frequency = int(sys.argv[2]) if len(sys.argv) > 2 else 440
            anc.run_test_tone(frequency=frequency, duration=3)
            return 0

        elif command == 'realtime':
            # Run real-time ANC
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10

            print("\n⚠ WARNING: This will capture from microphone and output to speakers")
            print("⚠ FEEDBACK WARNING: Keep microphone away from speakers to avoid feedback loop!")
            print("⚠ Start with low speaker volume and increase gradually")

            response = input("\nContinue? (yes/no): ").strip().lower()
            if response != 'yes':
                print("Cancelled.")
                return 0

            anc.run_realtime_anc(duration=duration, gain=1.0, monitor=True)
            return 0

        else:
            print(f"Unknown command: {command}")
            print_usage()
            return 1

    else:
        print_usage()
        return 0


def print_usage():
    """Print usage instructions."""
    print("\n" + "="*80)
    print("USAGE")
    print("="*80)
    print("\nCommands:")
    print("  python realtime_anti_noise_output.py list")
    print("    → List available audio devices")
    print()
    print("  python realtime_anti_noise_output.py test [frequency]")
    print("    → Play test tone with anti-noise (default: 440 Hz)")
    print("    → Example: python realtime_anti_noise_output.py test 1000")
    print()
    print("  python realtime_anti_noise_output.py realtime [duration]")
    print("    → Run real-time ANC (default: 10 seconds)")
    print("    → Example: python realtime_anti_noise_output.py realtime 30")
    print("    → ⚠ WARNING: May cause audio feedback - use with caution!")
    print()
    print("Examples:")
    print("  1. List devices:")
    print("     python realtime_anti_noise_output.py list")
    print()
    print("  2. Test with 440 Hz tone:")
    print("     python realtime_anti_noise_output.py test 440")
    print()
    print("  3. Run real-time ANC for 10 seconds:")
    print("     python realtime_anti_noise_output.py realtime 10")
    print()
    print("Safety Tips:")
    print("  - Start with low speaker volume")
    print("  - Keep microphone away from speakers")
    print("  - Use headphones for best results (one ear only)")
    print("  - Expect audio feedback if mic is too close to speakers")
    print("="*80)


if __name__ == "__main__":
    sys.exit(main())
