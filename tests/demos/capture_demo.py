"""
Demo script to capture audio and verify database storage.
Uses simulated audio for demonstration in Claude environment.
"""

import numpy as np
import wave
import os
from datetime import datetime
from database_schema import ANCDatabase

print("=" * 80)
print("AUDIO CAPTURE DEMONSTRATION")
print("=" * 80)

# Initialize database
db = ANCDatabase("anc_system.db")

# Audio configuration
RATE = 44100
CHANNELS = 1
DURATION = 3  # seconds

print(f"\nConfiguration:")
print(f"  Sample Rate: {RATE} Hz")
print(f"  Channels: {CHANNELS} (Mono)")
print(f"  Duration: {DURATION} seconds")
print(f"  Format: 16-bit PCM")

# Generate simulated office noise (HVAC + typing + ambient)
print(f"\n{'─' * 80}")
print("Generating simulated office noise...")
print(f"{'─' * 80}")

num_samples = int(RATE * DURATION)
time_vector = np.linspace(0, DURATION, num_samples)

# Create realistic office environment noise
signal = 0.08 * np.sin(2 * np.pi * 60 * time_vector)  # 60 Hz HVAC hum
signal += 0.05 * np.sin(2 * np.pi * 120 * time_vector)  # 120 Hz harmonic
signal += 0.03 * np.random.randn(num_samples)  # Background ambient noise

# Add occasional typing sounds
np.random.seed(42)
for _ in range(8):  # 8 typing events
    pos = np.random.randint(0, num_samples - 200)
    envelope = np.exp(-np.linspace(0, 8, 200))
    signal[pos:pos+200] += 0.4 * np.random.rand() * envelope

# Normalize and convert to 16-bit PCM
signal = np.clip(signal, -1.0, 1.0)
signal_int16 = (signal * 32767).astype(np.int16)

print(f"✓ Generated {num_samples} samples ({DURATION}s)")
print(f"  Signal range: [{signal.min():.4f}, {signal.max():.4f}]")

# Save as WAV file
output_dir = "recordings"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
wav_filename = f"demo_office_noise_{timestamp}.wav"
wav_filepath = os.path.join(output_dir, wav_filename)

print(f"\n{'─' * 80}")
print("Saving WAV file...")
print(f"{'─' * 80}")

wf = wave.open(wav_filepath, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(2)  # 16-bit = 2 bytes
wf.setframerate(RATE)
wf.writeframes(signal_int16.tobytes())
wf.close()

file_size = os.path.getsize(wav_filepath)
print(f"✓ WAV file saved: {wav_filepath}")
print(f"  File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")

# Verify WAV file can be read
print(f"\n{'─' * 80}")
print("Verifying WAV file...")
print(f"{'─' * 80}")

wf_verify = wave.open(wav_filepath, 'rb')
print(f"✓ WAV file verification:")
print(f"  Channels: {wf_verify.getnchannels()}")
print(f"  Sample width: {wf_verify.getsampwidth()} bytes")
print(f"  Frame rate: {wf_verify.getframerate()} Hz")
print(f"  Frames: {wf_verify.getnframes()}")
print(f"  Duration: {wf_verify.getnframes() / wf_verify.getframerate():.2f}s")
wf_verify.close()

# Calculate noise level in dB
print(f"\n{'─' * 80}")
print("Calculating noise metrics...")
print(f"{'─' * 80}")

rms = np.sqrt(np.mean(signal ** 2))
noise_level_db = 20 * np.log10(rms) if rms > 0 else -np.inf
print(f"✓ Noise level: {noise_level_db:.2f} dB")
print(f"  RMS amplitude: {rms:.6f}")

# Insert into database
print(f"\n{'─' * 80}")
print("Inserting into database...")
print(f"{'─' * 80}")

recording_id = db.insert_noise_recording(
    duration_seconds=DURATION,
    sampling_rate=RATE,
    num_samples=num_samples,
    environment_type="office",
    noise_level_db=noise_level_db,
    location="Demo Office Building",
    device_id="simulated_device_001",
    description="Simulated office environment with HVAC and keyboard typing",
    metadata={
        "wav_file": wav_filepath,
        "channels": CHANNELS,
        "sample_width": 2,
        "format": "PCM_16",
        "simulated": True,
        "noise_sources": ["HVAC", "typing", "ambient"],
        "captured_at": datetime.now().isoformat()
    }
)

print(f"✓ Recording metadata saved")
print(f"  Recording ID: {recording_id}")

# Store waveform data
waveform_id = db.insert_waveform(
    recording_id=recording_id,
    waveform_type="ambient_noise",
    waveform_array=signal
)

print(f"✓ Waveform data saved")
print(f"  Waveform ID: {waveform_id}")
print(f"  Stored {len(signal)} samples as BLOB")

# Perform and store spectral analysis
print(f"\n{'─' * 80}")
print("Performing spectral analysis (FFT)...")
print(f"{'─' * 80}")

fft_size = 2048
fft_data = np.fft.rfft(signal[:fft_size])
freqs = np.fft.rfftfreq(fft_size, 1.0 / RATE)
magnitude = np.abs(fft_data)
phase = np.angle(fft_data)

# Find dominant frequencies
top_indices = np.argsort(magnitude)[-5:][::-1]
print(f"✓ FFT completed (size: {fft_size})")
print(f"  Top 5 frequency components:")
for i, idx in enumerate(top_indices, 1):
    print(f"    {i}. {freqs[idx]:.1f} Hz (magnitude: {magnitude[idx]:.2f})")

analysis_id = db.insert_spectral_analysis(
    recording_id=recording_id,
    waveform_type="ambient_noise",
    frequency_data=freqs,
    magnitude_data=magnitude,
    phase_data=phase,
    fft_size=fft_size,
    window_function="none"
)

print(f"✓ Spectral analysis saved")
print(f"  Analysis ID: {analysis_id}")

db.close()

print(f"\n{'═' * 80}")
print("CAPTURE COMPLETED SUCCESSFULLY!")
print(f"{'═' * 80}")
print(f"\nSummary:")
print(f"  Recording ID: {recording_id}")
print(f"  WAV File: {wav_filepath}")
print(f"  Duration: {DURATION}s")
print(f"  Samples: {num_samples:,}")
print(f"  Noise Level: {noise_level_db:.2f} dB")
print(f"  Database: anc_system.db")
print(f"\n✓ All data stored in database and ready for analysis!")
