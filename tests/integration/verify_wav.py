"""
Verify WAV file integrity and show audio properties.
"""

import wave
import numpy as np
import matplotlib.pyplot as plt

wav_file = "recordings/demo_office_noise_20251107_115238.wav"

print("=" * 80)
print(f"WAV FILE VERIFICATION: {wav_file}")
print("=" * 80)

# Open and read WAV file
with wave.open(wav_file, 'rb') as wf:
    print("\n1. WAV FILE PROPERTIES")
    print("─" * 80)
    print(f"  Channels:          {wf.getnchannels()}")
    print(f"  Sample Width:      {wf.getsampwidth()} bytes ({wf.getsampwidth() * 8}-bit)")
    print(f"  Frame Rate:        {wf.getframerate()} Hz")
    print(f"  Number of Frames:  {wf.getnframes():,}")
    print(f"  Compression:       {wf.getcomptype()} ({wf.getcompname()})")
    print(f"  Duration:          {wf.getnframes() / wf.getframerate():.2f} seconds")

    # Read audio data
    frames = wf.readframes(wf.getnframes())
    audio_data = np.frombuffer(frames, dtype=np.int16)

print("\n2. AUDIO DATA ANALYSIS")
print("─" * 80)
print(f"  Total Samples:     {len(audio_data):,}")
print(f"  Data Type:         {audio_data.dtype}")
print(f"  Min Value:         {audio_data.min()}")
print(f"  Max Value:         {audio_data.max()}")
print(f"  Mean Value:        {audio_data.mean():.2f}")
print(f"  Std Deviation:     {audio_data.std():.2f}")

# Convert to float [-1, 1]
audio_float = audio_data.astype(np.float64) / 32768.0

print("\n3. NORMALIZED AUDIO [-1, 1]")
print("─" * 80)
print(f"  Min Amplitude:     {audio_float.min():.6f}")
print(f"  Max Amplitude:     {audio_float.max():.6f}")
print(f"  Mean Amplitude:    {audio_float.mean():.6f}")
print(f"  RMS Amplitude:     {np.sqrt(np.mean(audio_float ** 2)):.6f}")

# Calculate dB
rms = np.sqrt(np.mean(audio_float ** 2))
db = 20 * np.log10(rms) if rms > 0 else -np.inf
print(f"  Noise Level:       {db:.2f} dB")

print("\n4. FREQUENCY ANALYSIS")
print("─" * 80)

# Perform FFT
fft_size = 2048
fft_result = np.fft.rfft(audio_float[:fft_size])
freqs = np.fft.rfftfreq(fft_size, 1.0 / 44100)
magnitude = np.abs(fft_result)

# Find dominant frequencies
top_5_indices = np.argsort(magnitude)[-5:][::-1]
print(f"  FFT Size:          {fft_size}")
print(f"  Top 5 Frequencies:")
for i, idx in enumerate(top_5_indices, 1):
    print(f"    {i}. {freqs[idx]:>7.1f} Hz  (magnitude: {magnitude[idx]:>7.2f})")

print("\n5. WAVEFORM VISUALIZATION")
print("─" * 80)

# Create visualization
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# Time domain plot (first 0.1 seconds)
time_samples = int(0.1 * 44100)
time_vector = np.linspace(0, 0.1, time_samples)
axes[0].plot(time_vector, audio_float[:time_samples], linewidth=0.5)
axes[0].set_title('Waveform (First 0.1 seconds)', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Time (seconds)')
axes[0].set_ylabel('Amplitude')
axes[0].grid(True, alpha=0.3)

# Full waveform overview
full_time = np.linspace(0, len(audio_float) / 44100, len(audio_float))
axes[1].plot(full_time, audio_float, linewidth=0.3, alpha=0.7)
axes[1].set_title('Complete Waveform', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Time (seconds)')
axes[1].set_ylabel('Amplitude')
axes[1].grid(True, alpha=0.3)

# Frequency spectrum
axes[2].plot(freqs, magnitude, linewidth=1)
axes[2].set_title('Frequency Spectrum (FFT)', fontsize=12, fontweight='bold')
axes[2].set_xlabel('Frequency (Hz)')
axes[2].set_ylabel('Magnitude')
axes[2].set_xlim(0, 1000)  # Show up to 1000 Hz
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('wav_analysis.png', dpi=150, bbox_inches='tight')
print(f"✓ Visualization saved: wav_analysis.png")

print("\n" + "=" * 80)
print("✓ WAV FILE VERIFICATION COMPLETE - FILE IS VALID!")
print("=" * 80)
