"""
Real-time Audio Capture System
Captures noise from microphone, records as WAV, and stores in database as frequent noise definitions.
"""

import pyaudio
import wave
import numpy as np
import os
from datetime import datetime
from database_schema import ANCDatabase
import time
import signal
import sys


class AudioCapture:
    """
    Real-time audio capture system using PyAudio.
    Records audio, saves as WAV files, and stores in database.
    """

    def __init__(self, db_path="anc_system.db", output_dir="recordings"):
        # Audio configuration
        self.CHUNK = 1024  # Frames per buffer
        self.FORMAT = pyaudio.paInt16  # 16-bit audio
        self.CHANNELS = 1  # Mono audio
        self.RATE = 44100  # Sample rate (Hz)

        # Recording state
        self.frames = []
        self.is_recording = False
        self.recording_start_time = None

        # PyAudio instance
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Database connection
        self.db = ANCDatabase(db_path)

        # Output directory for WAV files
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created output directory: {self.output_dir}")

        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)

        print("Audio Capture System initialized")
        self.print_audio_devices()

    def print_audio_devices(self):
        """Display available audio input devices."""
        print("\n" + "=" * 70)
        print("Available Audio Devices:")
        print("=" * 70)
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:
                print(f"  [{i}] {dev_info['name']}")
                print(f"      Channels: {dev_info['maxInputChannels']}, "
                      f"Sample Rate: {int(dev_info['defaultSampleRate'])} Hz")
        print("=" * 70)

    def start_recording(self, duration_seconds=None, device_index=None):
        """
        Start recording audio from microphone.

        Args:
            duration_seconds: Recording duration (None for continuous until stopped)
            device_index: Specific audio device index (None for default)
        """
        self.frames = []
        self.is_recording = True
        self.recording_start_time = time.time()

        print(f"\n{'─' * 70}")
        print("Starting audio recording...")
        print(f"Format: {self.CHANNELS} channel(s), {self.RATE} Hz, 16-bit")
        if duration_seconds:
            print(f"Duration: {duration_seconds} seconds")
        else:
            print("Duration: Continuous (press Ctrl+C to stop)")
        print(f"{'─' * 70}\n")

        # Open audio stream
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.CHUNK
        )

        # Calculate total chunks for duration-based recording
        if duration_seconds:
            total_chunks = int(self.RATE / self.CHUNK * duration_seconds)
        else:
            total_chunks = None

        # Record audio
        try:
            chunk_count = 0
            while self.is_recording:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.frames.append(data)
                chunk_count += 1

                # Show progress every second
                if chunk_count % (self.RATE // self.CHUNK) == 0:
                    elapsed = int(time.time() - self.recording_start_time)
                    print(f"  Recording... {elapsed}s elapsed", end='\r')

                # Stop if duration reached
                if total_chunks and chunk_count >= total_chunks:
                    break

        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")

        finally:
            self.stop_recording()

    def stop_recording(self):
        """Stop recording and close the stream."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        self.is_recording = False
        elapsed_time = time.time() - self.recording_start_time if self.recording_start_time else 0
        print(f"\n\n✓ Recording stopped. Duration: {elapsed_time:.2f}s")
        print(f"  Captured {len(self.frames)} audio chunks")

    def save_wav(self, filename=None):
        """
        Save recorded audio as WAV file.

        Returns:
            str: Path to the saved WAV file
        """
        if not self.frames:
            print("Error: No audio data to save")
            return None

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"

        # Ensure .wav extension
        if not filename.endswith('.wav'):
            filename += '.wav'

        filepath = os.path.join(self.output_dir, filename)

        # Write WAV file
        wf = wave.open(filepath, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        file_size = os.path.getsize(filepath) / 1024  # KB
        print(f"\n✓ WAV file saved: {filepath}")
        print(f"  File size: {file_size:.2f} KB")

        return filepath

    def get_audio_array(self):
        """
        Convert recorded audio frames to numpy array.

        Returns:
            np.ndarray: Audio data as float array
        """
        if not self.frames:
            return np.array([])

        # Convert bytes to numpy array
        audio_bytes = b''.join(self.frames)
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

        # Normalize to float [-1, 1]
        audio_float = audio_int16.astype(np.float64) / 32768.0

        return audio_float

    def calculate_noise_level(self, audio_data):
        """
        Calculate noise level in decibels (dB).

        Args:
            audio_data: numpy array of audio samples

        Returns:
            float: Noise level in dB
        """
        # Calculate RMS (Root Mean Square)
        rms = np.sqrt(np.mean(audio_data ** 2))

        # Convert to dB (with reference to prevent log(0))
        if rms > 0:
            db = 20 * np.log10(rms)
        else:
            db = -np.inf

        return db

    def save_to_database(self, environment_type=None, location=None,
                        description=None, save_wav=True, wav_filename=None):
        """
        Save recording to database with metadata and waveform data.

        Args:
            environment_type: Type of environment (e.g., "office", "street", "home")
            location: Physical location of recording
            description: Description of the noise
            save_wav: Whether to save WAV file
            wav_filename: Custom WAV filename

        Returns:
            int: Recording ID from database
        """
        if not self.frames:
            print("Error: No audio data to save")
            return None

        print(f"\n{'─' * 70}")
        print("Saving to database...")
        print(f"{'─' * 70}")

        # Get audio array
        audio_data = self.get_audio_array()
        num_samples = len(audio_data)
        duration_seconds = num_samples / self.RATE

        # Calculate noise level
        noise_level_db = self.calculate_noise_level(audio_data)

        # Save WAV file if requested
        wav_path = None
        if save_wav:
            wav_path = self.save_wav(wav_filename)

        # Insert recording metadata
        recording_id = self.db.insert_noise_recording(
            duration_seconds=duration_seconds,
            sampling_rate=self.RATE,
            num_samples=num_samples,
            environment_type=environment_type,
            noise_level_db=noise_level_db,
            location=location,
            description=description,
            metadata={
                "channels": self.CHANNELS,
                "sample_width": self.audio.get_sample_size(self.FORMAT),
                "format": "PCM_16",
                "wav_file": wav_path,
                "captured_at": datetime.now().isoformat()
            }
        )

        print(f"\n✓ Recording metadata saved (ID: {recording_id})")
        print(f"  Duration: {duration_seconds:.2f}s")
        print(f"  Samples: {num_samples}")
        print(f"  Noise Level: {noise_level_db:.2f} dB")

        # Store waveform data
        waveform_id = self.db.insert_waveform(
            recording_id=recording_id,
            waveform_type="ambient_noise",
            waveform_array=audio_data
        )

        print(f"✓ Waveform data saved (ID: {waveform_id})")

        # Calculate and store spectral analysis (optional)
        self._save_spectral_analysis(recording_id, audio_data)

        print(f"{'─' * 70}\n")

        return recording_id

    def _save_spectral_analysis(self, recording_id, audio_data):
        """
        Perform FFT analysis and save to database.

        Args:
            recording_id: Database recording ID
            audio_data: Audio data array
        """
        # Perform FFT
        fft_size = min(2048, len(audio_data))
        fft_data = np.fft.rfft(audio_data[:fft_size])

        # Get frequency bins
        freqs = np.fft.rfftfreq(fft_size, 1.0 / self.RATE)

        # Get magnitude and phase
        magnitude = np.abs(fft_data)
        phase = np.angle(fft_data)

        # Store in database
        analysis_id = self.db.insert_spectral_analysis(
            recording_id=recording_id,
            waveform_type="ambient_noise",
            frequency_data=freqs,
            magnitude_data=magnitude,
            phase_data=phase,
            fft_size=fft_size,
            window_function="none"
        )

        print(f"✓ Spectral analysis saved (ID: {analysis_id})")

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully."""
        print("\n\nShutdown signal received...")
        self.is_recording = False
        if self.stream:
            self.stop_recording()
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        self.db.close()
        print("✓ Resources cleaned up")


def record_noise_sample(duration=5, environment="unknown", location="unknown",
                       description="Noise sample", save_wav=True):
    """
    Quick function to record a noise sample.

    Args:
        duration: Recording duration in seconds
        environment: Environment type
        location: Recording location
        description: Description of the noise
        save_wav: Whether to save WAV file

    Returns:
        int: Recording ID from database
    """
    capture = AudioCapture()

    try:
        # Record audio
        capture.start_recording(duration_seconds=duration)

        # Save to database
        recording_id = capture.save_to_database(
            environment_type=environment,
            location=location,
            description=description,
            save_wav=save_wav
        )

        return recording_id

    finally:
        capture.cleanup()


def interactive_recording():
    """
    Interactive mode for recording multiple noise samples.
    """
    print("=" * 70)
    print("INTERACTIVE NOISE RECORDING SYSTEM")
    print("=" * 70)

    capture = AudioCapture()

    try:
        while True:
            print("\nOptions:")
            print("  1. Record noise sample")
            print("  2. View recording statistics")
            print("  3. Exit")

            choice = input("\nEnter choice (1-3): ").strip()

            if choice == "1":
                # Get recording parameters
                print("\n" + "─" * 70)
                duration = input("Duration (seconds) [default: 5]: ").strip()
                duration = int(duration) if duration else 5

                environment = input("Environment type (e.g., office, street, home): ").strip()
                environment = environment if environment else "unknown"

                location = input("Location: ").strip()
                location = location if location else "unknown"

                description = input("Description: ").strip()
                description = description if description else "Noise sample"

                save_wav = input("Save WAV file? (y/n) [default: y]: ").strip().lower()
                save_wav = save_wav != 'n'

                # Record
                capture.start_recording(duration_seconds=duration)

                # Save to database
                capture.save_to_database(
                    environment_type=environment,
                    location=location,
                    description=description,
                    save_wav=save_wav
                )

                print("\n✓ Recording completed and saved!")

            elif choice == "2":
                # Show statistics
                recordings = capture.db.get_all_recordings()
                print(f"\n{'─' * 70}")
                print(f"Total recordings in database: {len(recordings)}")
                print(f"{'─' * 70}")

                if recordings:
                    for rec in recordings[-5:]:  # Show last 5
                        print(f"\nRecording ID: {rec[0]}")
                        print(f"  Time: {rec[1]}")
                        print(f"  Duration: {rec[2]:.2f}s")
                        print(f"  Environment: {rec[5]}")
                        print(f"  Location: {rec[7]}")

            elif choice == "3":
                print("\nExiting...")
                break

            else:
                print("\nInvalid choice. Please try again.")

    finally:
        capture.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Command-line mode
        if sys.argv[1] == "quick":
            # Quick recording with default settings
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            print(f"Quick recording: {duration} seconds")
            record_noise_sample(duration=duration)

        elif sys.argv[1] == "interactive":
            # Interactive mode
            interactive_recording()

        else:
            print("Usage:")
            print("  python audio_capture.py quick [duration]  - Quick recording")
            print("  python audio_capture.py interactive       - Interactive mode")

    else:
        # Default: interactive mode
        interactive_recording()
