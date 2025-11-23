"""
Phase Inversion Test for Active Noise Cancellation
Tests that phase-inverted signal equals -input for noise cancellation.
"""

import numpy as np
import sys


def phase_invert(signal):
    """
    Perform phase inversion on input signal.

    Phase inversion is the core of ANC - inverting the signal by 180 degrees
    (multiplying by -1) creates a cancellation signal.

    Args:
        signal: Input signal array (noise)

    Returns:
        Phase-inverted signal (anti-noise)
    """
    return -signal


def generate_test_signals():
    """
    Generate various test signals for phase inversion testing.

    Returns:
        Dictionary of test signals
    """
    signals = {}

    # 1. Simple sine wave (pure tone)
    t = np.linspace(0, 1, 1000, endpoint=False)
    signals['sine_wave'] = np.sin(2 * np.pi * 440 * t)  # 440 Hz (A note)

    # 2. White noise
    signals['white_noise'] = np.random.randn(1000)

    # 3. Complex signal (sum of multiple frequencies)
    signals['complex_signal'] = (
        0.5 * np.sin(2 * np.pi * 440 * t) +
        0.3 * np.sin(2 * np.pi * 880 * t) +
        0.2 * np.sin(2 * np.pi * 1320 * t)
    )

    # 4. Square wave
    signals['square_wave'] = np.sign(np.sin(2 * np.pi * 100 * t))

    # 5. Impulse (spike)
    impulse = np.zeros(1000)
    impulse[500] = 1.0
    signals['impulse'] = impulse

    # 6. Decaying exponential (transient)
    signals['exponential'] = np.exp(-5 * t) * np.sin(2 * np.pi * 200 * t)

    # 7. Real-world-like noise (pink noise approximation)
    white = np.random.randn(1000)
    # Apply simple low-pass filter
    pink = np.convolve(white, np.ones(10)/10, mode='same')
    signals['pink_noise'] = pink

    # 8. Zero signal
    signals['zero_signal'] = np.zeros(1000)

    return signals


def test_phase_inversion(signal, signal_name, tolerance=1e-10):
    """
    Test phase inversion and verify output equals -input.

    Args:
        signal: Input signal array
        signal_name: Name of the signal for reporting
        tolerance: Tolerance for np.allclose

    Returns:
        Boolean indicating test pass/fail
    """
    print(f"\nTesting: {signal_name}")
    print(f"  Input shape: {signal.shape}")
    print(f"  Input range: [{np.min(signal):.6f}, {np.max(signal):.6f}]")
    print(f"  Input RMS: {np.sqrt(np.mean(signal**2)):.6f}")

    # Perform phase inversion
    inverted = phase_invert(signal)

    print(f"  Output range: [{np.min(inverted):.6f}, {np.max(inverted):.6f}]")
    print(f"  Output RMS: {np.sqrt(np.mean(inverted**2)):.6f}")

    # Expected output
    expected = -signal

    # Test using np.allclose
    try:
        assert np.allclose(inverted, expected, rtol=tolerance, atol=tolerance), \
            f"Phase inversion failed: output != -input"

        # Additional checks
        assert np.allclose(inverted, -signal, rtol=tolerance, atol=tolerance), \
            f"Direct comparison failed: inverted != -signal"

        # Verify cancellation property: signal + inverted should be ~0
        cancelled = signal + inverted
        assert np.allclose(cancelled, 0, rtol=tolerance, atol=tolerance), \
            f"Cancellation failed: signal + inverted != 0"

        print(f"  ✓ PASS: np.allclose(output, -input) = True")
        print(f"  ✓ Cancellation: sum(signal + inverted) = {np.sum(cancelled):.2e}")

        return True

    except AssertionError as e:
        print(f"  ✗ FAIL: {e}")

        # Show differences
        diff = inverted - expected
        print(f"  Max difference: {np.max(np.abs(diff)):.2e}")
        print(f"  Mean difference: {np.mean(np.abs(diff)):.2e}")

        return False


def demonstrate_noise_cancellation():
    """
    Demonstrate noise cancellation with phase-inverted signal.
    """
    print("\n" + "=" * 80)
    print("NOISE CANCELLATION DEMONSTRATION")
    print("=" * 80)

    # Generate a noise signal
    t = np.linspace(0, 0.1, 1000, endpoint=False)
    original_noise = 0.5 * np.sin(2 * np.pi * 1000 * t) + 0.3 * np.random.randn(1000)

    print(f"\nOriginal Noise:")
    print(f"  RMS: {np.sqrt(np.mean(original_noise**2)):.6f}")
    print(f"  Peak: {np.max(np.abs(original_noise)):.6f}")

    # Generate anti-noise (phase inverted)
    anti_noise = phase_invert(original_noise)

    print(f"\nAnti-Noise (Phase Inverted):")
    print(f"  RMS: {np.sqrt(np.mean(anti_noise**2)):.6f}")
    print(f"  Peak: {np.max(np.abs(anti_noise)):.6f}")

    # Combine signals (simulating ANC)
    result = original_noise + anti_noise

    print(f"\nResult (Noise + Anti-Noise):")
    print(f"  RMS: {np.sqrt(np.mean(result**2)):.6e}")
    print(f"  Peak: {np.max(np.abs(result)):.6e}")
    print(f"  Sum: {np.sum(result):.6e}")

    # Calculate noise reduction
    noise_reduction_db = 20 * np.log10(
        np.sqrt(np.mean(result**2)) / np.sqrt(np.mean(original_noise**2))
    )

    print(f"\n  Noise Reduction: {noise_reduction_db:.2f} dB")

    # Verify perfect cancellation
    assert np.allclose(result, 0, atol=1e-10), "Perfect cancellation not achieved"
    print(f"  ✓ Perfect cancellation verified (within 1e-10 tolerance)")

    print("=" * 80)


def run_comprehensive_tests():
    """
    Run comprehensive phase inversion tests on various signals.
    """
    print("=" * 80)
    print("PHASE INVERSION TEST SUITE")
    print("=" * 80)
    print("\nTesting: np.allclose(output, -input) for phase inversion")
    print("=" * 80)

    # Generate test signals
    test_signals = generate_test_signals()

    results = {}

    # Test each signal
    for signal_name, signal in test_signals.items():
        passed = test_phase_inversion(signal, signal_name)
        results[signal_name] = passed

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"\nTest Results:")
    for signal_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {signal_name:<20} {status}")

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed ({100*passed_tests/total_tests:.1f}%)")

    if passed_tests == total_tests:
        print("\n✓ ALL TESTS PASSED - Phase inversion verified!")
    else:
        print(f"\n✗ {total_tests - passed_tests} tests failed")

    print("=" * 80)

    return passed_tests == total_tests


def verify_mathematical_properties():
    """
    Verify mathematical properties of phase inversion.
    """
    print("\n" + "=" * 80)
    print("MATHEMATICAL PROPERTY VERIFICATION")
    print("=" * 80)

    # Generate test signal
    signal = np.random.randn(1000)
    inverted = phase_invert(signal)

    print("\n1. Double Inversion Property:")
    print("   phase_invert(phase_invert(x)) == x")
    double_inverted = phase_invert(inverted)
    assert np.allclose(double_inverted, signal), "Double inversion failed"
    print("   ✓ Verified")

    print("\n2. Cancellation Property:")
    print("   signal + phase_invert(signal) == 0")
    cancelled = signal + inverted
    assert np.allclose(cancelled, 0), "Cancellation property failed"
    print(f"   ✓ Verified (max residual: {np.max(np.abs(cancelled)):.2e})")

    print("\n3. Magnitude Preservation:")
    print("   |phase_invert(x)| == |x|")
    assert np.allclose(np.abs(inverted), np.abs(signal)), "Magnitude not preserved"
    print("   ✓ Verified")

    print("\n4. Energy Preservation:")
    print("   sum(phase_invert(x)^2) == sum(x^2)")
    assert np.allclose(np.sum(inverted**2), np.sum(signal**2)), "Energy not preserved"
    print(f"   ✓ Verified (original: {np.sum(signal**2):.6f}, inverted: {np.sum(inverted**2):.6f})")

    print("\n5. Linearity:")
    print("   phase_invert(a*x + b*y) == a*phase_invert(x) + b*phase_invert(y)")
    signal2 = np.random.randn(1000)
    a, b = 2.5, 1.7

    left = phase_invert(a * signal + b * signal2)
    right = a * phase_invert(signal) + b * phase_invert(signal2)

    assert np.allclose(left, right), "Linearity property failed"
    print("   ✓ Verified")

    print("\n✓ All mathematical properties verified!")
    print("=" * 80)


def test_with_database_audio():
    """
    Test phase inversion with real audio from database.
    """
    print("\n" + "=" * 80)
    print("PHASE INVERSION TEST WITH DATABASE AUDIO")
    print("=" * 80)

    try:
        from database_schema import ANCDatabase

        db = ANCDatabase('anc_system.db')

        # Get a recording
        db.cursor.execute("""
            SELECT waveform_id
            FROM audio_waveforms
            LIMIT 1
        """)

        result = db.cursor.fetchone()

        if result:
            waveform_id = result[0]
            audio_data = db.get_waveform(waveform_id)

            if audio_data is not None:
                print(f"\nLoaded waveform from database:")
                print(f"  Waveform ID: {waveform_id}")
                print(f"  Samples: {len(audio_data)}")
                print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")

                # Test phase inversion
                inverted = phase_invert(audio_data)

                # Verify
                assert np.allclose(inverted, -audio_data), "Phase inversion failed on real audio"

                # Verify cancellation
                cancelled = audio_data + inverted
                cancellation_rms = np.sqrt(np.mean(cancelled**2))

                print(f"\n  Phase inverted signal:")
                print(f"    RMS: {np.sqrt(np.mean(inverted**2)):.6f}")

                print(f"\n  Cancellation result:")
                print(f"    RMS: {cancellation_rms:.6e}")
                print(f"    Max residual: {np.max(np.abs(cancelled)):.6e}")

                noise_reduction = 20 * np.log10(cancellation_rms / np.sqrt(np.mean(audio_data**2)))
                print(f"    Noise reduction: {noise_reduction:.2f} dB")

                print(f"\n  ✓ PASS: Real audio phase inversion verified")
            else:
                print("  ⚠ Could not load waveform data")
        else:
            print("  ⚠ No waveforms found in database")

        db.close()

    except Exception as e:
        print(f"  ⚠ Database test skipped: {e}")

    print("=" * 80)


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("ACTIVE NOISE CANCELLATION - PHASE INVERSION TEST")
    print("=" * 80)
    print("\nThis script verifies that phase inversion produces -input")
    print("using np.allclose() assertions for ANC signal processing.")
    print("=" * 80)

    # Run comprehensive tests
    all_passed = run_comprehensive_tests()

    # Demonstrate noise cancellation
    demonstrate_noise_cancellation()

    # Verify mathematical properties
    verify_mathematical_properties()

    # Test with database audio if available
    test_with_database_audio()

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    if all_passed:
        print("\n✓ SUCCESS: All phase inversion tests passed!")
        print("  - np.allclose(output, -input) verified for all signals")
        print("  - Noise cancellation demonstrated")
        print("  - Mathematical properties confirmed")
        print("\nPhase inversion is working correctly for ANC system.")
    else:
        print("\n✗ FAILURE: Some tests failed")
        sys.exit(1)

    print("=" * 80)


if __name__ == "__main__":
    main()
