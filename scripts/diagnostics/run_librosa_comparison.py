"""
Compare intensity analysis results: Standard vs Librosa methods
"""

import subprocess
import sys


def run_analysis(script, audio_file):
    """Run analysis script and extract SPL value."""
    try:
        result = subprocess.run(
            [sys.executable, script, audio_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Extract SPL from output
        for line in result.stdout.split('\n'):
            if 'SPL:' in line or 'SPL Estimate:' in line:
                # Extract number
                parts = line.split(':')
                if len(parts) >= 2:
                    spl_str = parts[1].strip().split()[0]
                    try:
                        return float(spl_str)
                    except ValueError:
                        pass

        return None

    except Exception as e:
        print(f"Error analyzing {audio_file}: {e}")
        return None


def main():
    """Run comparison across all test samples."""
    print("=" * 80)
    print("INTENSITY ANALYSIS COMPARISON: Standard vs Librosa")
    print("=" * 80)

    test_files = [
        ('test_quiet.wav', 'Very Quiet', 40),
        ('test_moderate.wav', 'Moderate', 68),
        ('test_loud.wav', 'Loud', 77),
        ('test_very_loud.wav', 'Very Loud', 85),
        ('test_extreme.wav', 'Extremely Loud', 89),
        ('recordings/demo_office_noise_20251107_115238.wav', 'Office (Real)', 71),
        ('recordings/sim_recording_20251107_114815.wav', 'Park (Real)', 67),
    ]

    print(f"\n{'Sample':<45} {'Expected':<12} {'Standard':<12} {'Librosa':<12} {'Match':<8}")
    print("-" * 80)

    total_tests = 0
    matches = 0

    for audio_file, description, expected_db in test_files:
        # Run standard analysis
        standard_spl = run_analysis('intensity_analysis.py', audio_file)

        # Run librosa analysis
        librosa_spl = run_analysis('librosa_intensity_analysis.py', audio_file)

        if standard_spl and librosa_spl:
            difference = abs(standard_spl - librosa_spl)
            match = "✓" if difference < 0.5 else "✗"

            if difference < 0.5:
                matches += 1
            total_tests += 1

            print(f"{description:<45} {expected_db:<12.1f} {standard_spl:<12.2f} {librosa_spl:<12.2f} {match:<8}")
        else:
            print(f"{description:<45} {'N/A':<12} {'ERROR':<12} {'ERROR':<12} {'✗':<8}")

    print("-" * 80)
    print(f"\nMatching Results: {matches}/{total_tests} ({100*matches/total_tests:.1f}%)")

    if matches == total_tests:
        print("\n✓ All methods agree - Verification successful!")
    else:
        print(f"\n⚠ {total_tests - matches} discrepancies found")

    print("=" * 80)


if __name__ == "__main__":
    main()
