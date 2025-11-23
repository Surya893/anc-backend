"""
Simple Anti-Noise Demo
Generates a tone and plays it with anti-noise for demonstration.
"""

import numpy as np
import pyaudio
import time


def play_anti_noise_demo():
    """Play simple anti-noise demonstration."""
    print("="*80)
    print("ANTI-NOISE DEMONSTRATION")
    print("="*80)

    # Audio parameters
    SAMPLE_RATE = 44100
    DURATION = 2  # seconds
    FREQUENCY = 440  # Hz (A note)

    print(f"\nGenerating {FREQUENCY} Hz test tone...")

    # Generate test tone
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)
    tone = 0.3 * np.sin(2 * np.pi * FREQUENCY * t).astype(np.float32)

    # Generate anti-noise (phase inversion)
    anti_noise = -tone

    # Combined (should be silent)
    combined = tone + anti_noise

    print(f"  Original RMS: {np.sqrt(np.mean(tone**2)):.6f}")
    print(f"  Anti-noise RMS: {np.sqrt(np.mean(anti_noise**2)):.6f}")
    print(f"  Combined RMS: {np.sqrt(np.mean(combined**2)):.6e}")

    # Verify
    assert np.allclose(anti_noise, -tone), "Phase inversion failed!"
    assert np.allclose(combined, 0), "Cancellation failed!"
    print(f"\n✓ Verified: np.allclose(anti_noise, -tone)")
    print(f"✓ Verified: np.allclose(combined, 0)")

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Open stream
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=SAMPLE_RATE,
        output=True
    )

    print("\n" + "="*80)
    print("PLAYBACK SEQUENCE")
    print("="*80)

    try:
        # Play original tone
        print(f"\n[1/3] Playing: Original {FREQUENCY} Hz tone...")
        stream.write(tone.tobytes())
        print("      ✓ Done")

        # Pause
        time.sleep(0.5)

        # Play anti-noise
        print(f"\n[2/3] Playing: Anti-noise (phase inverted)...")
        print("      (Should sound identical to original)")
        stream.write(anti_noise.tobytes())
        print("      ✓ Done")

        # Pause
        time.sleep(0.5)

        # Play combined
        print(f"\n[3/3] Playing: Combined (tone + anti-noise)...")
        print("      (Should be SILENT or very quiet)")
        stream.write(combined.tobytes())
        print("      ✓ Done")

    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()

    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nYou should have heard:")
    print("  1. Clear 440 Hz tone")
    print("  2. Identical tone (anti-noise)")
    print("  3. Silence (cancellation)")
    print("\nIf step 3 was silent, phase inversion is working correctly!")
    print("="*80)


if __name__ == "__main__":
    try:
        play_anti_noise_demo()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nNote: PyAudio must be installed:")
        print("  pip install pyaudio")
        print("\nOn Linux, you may also need:")
        print("  sudo apt-get install portaudio19-dev python3-pyaudio")
