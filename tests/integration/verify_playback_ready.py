"""
Verify that audio files are ready for PyAudio playback.
This script can run in Claude environment without PyAudio.
"""

import numpy as np
import wave
from pathlib import Path
from anti_noise_generator import AntiNoiseGenerator


def prepare_cancellation_demo_files():
    """Prepare all files needed for playback demonstration."""
    print("="*80)
    print("PREPARING CANCELLATION DEMO FILES")
    print("="*80)

    generator = AntiNoiseGenerator(sample_rate=44100)

    # Test scenarios
    scenarios = [
        {
            'name': 'tone_440hz',
            'description': '440 Hz Pure Tone (A4 Note)',
            'generator': lambda: generate_tone(440, 2.0),
        },
        {
            'name': 'tone_1000hz',
            'description': '1000 Hz Reference Tone',
            'generator': lambda: generate_tone(1000, 2.0),
        },
        {
            'name': 'hvac_hum',
            'description': 'Office HVAC Hum (60 Hz + harmonics)',
            'generator': lambda: generate_hvac_noise(3.0),
        },
        {
            'name': 'traffic_rumble',
            'description': 'Traffic Rumble (Low frequency)',
            'generator': lambda: generate_traffic_noise(3.0),
        },
        {
            'name': 'aircraft_cabin',
            'description': 'Aircraft Cabin Drone',
            'generator': lambda: generate_aircraft_noise(3.0),
        },
    ]

    print("\nGenerating audio files for playback testing...\n")

    for scenario in scenarios:
        print(f"{'─'*80}")
        print(f"Scenario: {scenario['description']}")
        print(f"{'─'*80}")

        # Generate noise
        noise = scenario['generator']()
        noise_rms = np.sqrt(np.mean(noise**2))

        print(f"  Original noise RMS: {noise_rms:.6f}")

        # Generate anti-noise
        anti_noise = generator.generate_anti_noise(noise)
        anti_rms = np.sqrt(np.mean(anti_noise**2))

        print(f"  Anti-noise RMS: {anti_rms:.6f}")

        # Create combined (cancelled)
        combined = noise + anti_noise
        combined_rms = np.sqrt(np.mean(combined**2))

        # Verify cancellation
        is_cancelled, metrics = generator.verify_cancellation(noise, anti_noise)

        print(f"  Combined RMS: {combined_rms:.6e}")
        print(f"  Noise reduction: {metrics['noise_reduction_db']:.2f} dB")
        print(f"  Cancellation: {'✓ PERFECT' if is_cancelled else '✗ PARTIAL'}")

        # Save files
        base_name = scenario['name']

        # 1. Original noise
        noise_file = f"demo_{base_name}_noise.wav"
        save_wav(noise, noise_file, 44100)
        print(f"  → Saved: {noise_file}")

        # 2. Anti-noise
        anti_file = f"demo_{base_name}_antinoise.wav"
        save_wav(anti_noise, anti_file, 44100)
        print(f"  → Saved: {anti_file}")

        # 3. Combined (cancelled)
        combined_file = f"demo_{base_name}_cancelled.wav"
        save_wav(combined, combined_file, 44100)
        print(f"  → Saved: {combined_file}")

        print()

    print("="*80)
    print("FILE PREPARATION COMPLETE")
    print("="*80)
    print("\nGenerated 15 WAV files (5 scenarios × 3 files each):")
    print("  - *_noise.wav: Original noise")
    print("  - *_antinoise.wav: Phase-inverted anti-noise")
    print("  - *_cancelled.wav: Combined (should be silent)")
    print("\nYou can play these files with any audio player to hear:")
    print("  1. The original noise")
    print("  2. The anti-noise (sounds same as noise)")
    print("  3. The cancellation (should be silent)")
    print("="*80)


def generate_tone(frequency, duration, sample_rate=44100):
    """Generate pure tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * frequency * t)


def generate_hvac_noise(duration, sample_rate=44100):
    """Generate HVAC-like noise."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    noise = 0.5 * np.sin(2 * np.pi * 60 * t)
    noise += 0.3 * np.sin(2 * np.pi * 120 * t)
    noise += 0.2 * np.sin(2 * np.pi * 180 * t)
    noise += 0.1 * np.random.randn(len(t))
    return noise


def generate_traffic_noise(duration, sample_rate=44100):
    """Generate traffic-like noise."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    noise = 0.4 * np.sin(2 * np.pi * 80 * t)
    noise += 0.3 * np.sin(2 * np.pi * 120 * t)
    noise += 0.2 * np.sin(2 * np.pi * 150 * t)
    noise += 0.15 * np.random.randn(len(t))
    return noise


def generate_aircraft_noise(duration, sample_rate=44100):
    """Generate aircraft cabin-like noise."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    noise = 0.4 * np.sin(2 * np.pi * 200 * t)
    noise += 0.2 * np.sin(2 * np.pi * 400 * t)
    noise += 0.15 * np.random.randn(len(t))
    return noise


def save_wav(audio_data, filename, sample_rate, bit_depth=16):
    """Save audio as WAV file."""
    # Normalize
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        normalized = audio_data / max_val
    else:
        normalized = audio_data

    # Convert to int16
    audio_int = (normalized * 32767).astype(np.int16)

    # Write WAV
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(audio_int.tobytes())


def verify_existing_files():
    """Verify existing test WAV files and prepare anti-noise versions."""
    print("\n" + "="*80)
    print("CHECKING EXISTING TEST FILES")
    print("="*80)

    test_files = list(Path('.').glob('test_*.wav'))

    if test_files:
        print(f"\nFound {len(test_files)} existing test files:")

        generator = AntiNoiseGenerator()

        for wav_file in test_files:
            print(f"\n{'─'*80}")
            print(f"File: {wav_file.name}")
            print(f"{'─'*80}")

            try:
                # Load
                noise = generator.load_noise_from_wav(str(wav_file))

                # Generate anti-noise
                anti_noise = generator.generate_anti_noise(noise)

                # Verify
                is_cancelled, metrics = generator.verify_cancellation(noise, anti_noise)

                print(f"  ✓ Loaded: {len(noise)} samples")
                print(f"  Original RMS: {metrics['original_rms']:.6f}")
                print(f"  Cancellation: {metrics['noise_reduction_db']:.2f} dB")

                # Save anti-noise
                anti_file = f"anti_{wav_file.name}"
                generator.save_anti_noise(anti_noise, anti_file)

                # Save combined
                combined = noise + anti_noise
                combined_file = f"cancelled_{wav_file.name}"
                save_wav(combined, combined_file, generator.sample_rate)
                print(f"  → Saved: {combined_file} (cancelled version)")

            except Exception as e:
                print(f"  ✗ Error: {e}")

        print("\n" + "="*80)
    else:
        print("\n⚠ No test_*.wav files found in current directory")


def print_playback_instructions():
    """Print instructions for local playback testing."""
    print("\n" + "="*80)
    print("LOCAL PLAYBACK TESTING INSTRUCTIONS")
    print("="*80)

    print("""
To test cancellation with actual audio playback on your local machine:

1. INSTALL PYAUDIO:
   pip install pyaudio

   Note: On some systems you may need:
   - Linux: sudo apt-get install portaudio19-dev python3-pyaudio
   - Mac: brew install portaudio
   - Windows: pip install pyaudio should work directly

2. RUN INTERACTIVE DEMO:
   python playback_cancellation_demo.py

   This will give you a menu to choose:
   - Test with WAV files
   - Generated tone tests
   - Real-world scenarios
   - Quick single tone test

3. RUN AUTOMATED DEMO:
   python playback_cancellation_demo.py auto

   This will automatically play test sequences.

4. PLAY SPECIFIC FILE:
   python playback_cancellation_demo.py test_loud.wav

   This will play the cancellation sequence for a specific file.

5. MANUALLY PLAY GENERATED FILES:
   You can also use any audio player to play the demo_*.wav files:

   For each scenario, play in order:
   a) demo_*_noise.wav      → Hear the original noise
   b) demo_*_antinoise.wav  → Hear the anti-noise (sounds same)
   c) demo_*_cancelled.wav  → Should be SILENT (cancelled)

   Examples:
   - demo_tone_440hz_noise.wav
   - demo_tone_440hz_antinoise.wav
   - demo_tone_440hz_cancelled.wav (← should be silent!)

WHAT TO EXPECT:
- Step 1 (noise): You'll hear the sound clearly
- Step 2 (anti-noise): Sounds identical to step 1
- Step 3 (cancelled): Should be SILENT or very quiet
  (This proves the cancellation is working!)

If step 3 is silent, the phase inversion is working perfectly!
""")

    print("="*80)


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("CANCELLATION PLAYBACK PREPARATION")
    print("="*80)

    # Prepare demo files
    prepare_cancellation_demo_files()

    # Check existing files
    verify_existing_files()

    # Print instructions
    print_playback_instructions()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n✓ Audio files prepared for playback testing")
    print("✓ Anti-noise and cancelled versions generated")
    print("✓ Ready for local PyAudio playback")
    print("\nNext step: Run playback_cancellation_demo.py on your local machine")
    print("           with speakers/headphones to HEAR the cancellation!")
    print("="*80)


if __name__ == "__main__":
    main()
