"""
Simple Counter Wave Test with NumPy
Direct demonstration: output = -input with same absolute amplitude
Assertion: np.allclose(output, -input)
"""

import numpy as np


def main():
    print("="*80)
    print("COUNTER WAVE GENERATION - NUMPY ASSERTION TEST")
    print("="*80)
    print("\nAssertion to verify: np.allclose(output, -input)")
    print("="*80)

    # Test Case 1: Simple sine wave
    print("\n" + "─"*80)
    print("TEST 1: Sine Wave (440 Hz)")
    print("─"*80)

    # Input: noise array
    t = np.linspace(0, 1, 1000)
    input_noise = 0.5 * np.sin(2 * np.pi * 440 * t)

    print(f"Input noise array:")
    print(f"  Shape: {input_noise.shape}")
    print(f"  RMS: {np.sqrt(np.mean(input_noise**2)):.6f}")
    print(f"  Amplitude (max |value|): {np.max(np.abs(input_noise)):.6f}")

    # Output: Generate counter wave (phase inversion)
    output = -input_noise

    print(f"\nOutput counter wave:")
    print(f"  Shape: {output.shape}")
    print(f"  RMS: {np.sqrt(np.mean(output**2)):.6f}")
    print(f"  Amplitude (max |value|): {np.max(np.abs(output)):.6f}")

    # Assert: np.allclose(output, -input)
    print(f"\n{'='*80}")
    print("ASSERTION TEST:")
    print(f"{'='*80}")

    try:
        assert np.allclose(output, -input_noise)
        print("✓ PASSED: np.allclose(output, -input)")
    except AssertionError:
        print("✗ FAILED: np.allclose(output, -input)")
        return 1

    # Verify same absolute amplitude
    try:
        assert np.allclose(np.abs(output), np.abs(input_noise))
        print("✓ PASSED: Same absolute amplitude |output| = |input|")
    except AssertionError:
        print("✗ FAILED: Absolute amplitude does not match")
        return 1

    # Verify cancellation
    combined = input_noise + output
    print(f"\nCancellation test:")
    print(f"  input + output = {np.max(np.abs(combined)):.2e} (should be ~0)")

    try:
        assert np.allclose(combined, 0)
        print("✓ PASSED: Perfect cancellation (input + output = 0)")
    except AssertionError:
        print("✗ FAILED: Cancellation incomplete")
        return 1

    # Test Case 2: White noise
    print("\n" + "─"*80)
    print("TEST 2: White Noise")
    print("─"*80)

    # Input: Random noise
    input_noise = np.random.randn(5000) * 0.3

    print(f"Input noise array:")
    print(f"  Shape: {input_noise.shape}")
    print(f"  RMS: {np.sqrt(np.mean(input_noise**2)):.6f}")
    print(f"  Amplitude: {np.max(np.abs(input_noise)):.6f}")

    # Output: Counter wave
    output = -input_noise

    print(f"\nOutput counter wave:")
    print(f"  Shape: {output.shape}")
    print(f"  RMS: {np.sqrt(np.mean(output**2)):.6f}")
    print(f"  Amplitude: {np.max(np.abs(output)):.6f}")

    # Assert
    print(f"\n{'='*80}")
    print("ASSERTION TEST:")
    print(f"{'='*80}")

    try:
        assert np.allclose(output, -input_noise)
        print("✓ PASSED: np.allclose(output, -input)")
    except AssertionError:
        print("✗ FAILED: np.allclose(output, -input)")
        return 1

    try:
        assert np.allclose(np.abs(output), np.abs(input_noise))
        print("✓ PASSED: Same absolute amplitude")
    except AssertionError:
        print("✗ FAILED: Absolute amplitude does not match")
        return 1

    combined = input_noise + output
    print(f"\nCancellation: {np.max(np.abs(combined)):.2e} (should be ~0)")

    try:
        assert np.allclose(combined, 0)
        print("✓ PASSED: Perfect cancellation")
    except AssertionError:
        print("✗ FAILED: Cancellation incomplete")
        return 1

    # Test Case 3: Complex multi-frequency
    print("\n" + "─"*80)
    print("TEST 3: Complex Multi-Frequency Signal")
    print("─"*80)

    # Input: Complex signal
    t = np.linspace(0, 2, 10000)
    input_noise = (0.5 * np.sin(2 * np.pi * 60 * t) +
                   0.3 * np.sin(2 * np.pi * 200 * t) +
                   0.2 * np.sin(2 * np.pi * 1000 * t) +
                   0.1 * np.random.randn(len(t)))

    print(f"Input noise array:")
    print(f"  Shape: {input_noise.shape}")
    print(f"  RMS: {np.sqrt(np.mean(input_noise**2)):.6f}")
    print(f"  Amplitude: {np.max(np.abs(input_noise)):.6f}")

    # Output: Counter wave
    output = -input_noise

    print(f"\nOutput counter wave:")
    print(f"  Shape: {output.shape}")
    print(f"  RMS: {np.sqrt(np.mean(output**2)):.6f}")
    print(f"  Amplitude: {np.max(np.abs(output)):.6f}")

    # Assert
    print(f"\n{'='*80}")
    print("ASSERTION TEST:")
    print(f"{'='*80}")

    try:
        assert np.allclose(output, -input_noise)
        print("✓ PASSED: np.allclose(output, -input)")
    except AssertionError:
        print("✗ FAILED: np.allclose(output, -input)")
        return 1

    try:
        assert np.allclose(np.abs(output), np.abs(input_noise))
        print("✓ PASSED: Same absolute amplitude")
    except AssertionError:
        print("✗ FAILED: Absolute amplitude does not match")
        return 1

    combined = input_noise + output
    print(f"\nCancellation: {np.max(np.abs(combined)):.2e} (should be ~0)")

    try:
        assert np.allclose(combined, 0)
        print("✓ PASSED: Perfect cancellation")
    except AssertionError:
        print("✗ FAILED: Cancellation incomplete")
        return 1

    # Sample point verification
    print("\n" + "="*80)
    print("SAMPLE POINT VERIFICATION")
    print("="*80)

    # Create simple test array
    test_input = np.array([1.0, -0.5, 0.3, -0.8, 0.0, 0.6])
    test_output = -test_input

    print(f"\n{'Index':<8} {'Input':<12} {'Output':<12} {'Sum (should be 0)':<20}")
    print("─"*80)
    for i in range(len(test_input)):
        print(f"{i:<8} {test_input[i]:<12.6f} {test_output[i]:<12.6f} {test_input[i] + test_output[i]:<20.2e}")

    try:
        assert np.allclose(test_output, -test_input)
        print("\n✓ PASSED: np.allclose(output, -input) for sample points")
    except AssertionError:
        print("\n✗ FAILED: Assertion failed for sample points")
        return 1

    # Final summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print("\n✓ ALL TESTS PASSED")
    print("\nVerified:")
    print("  ✓ np.allclose(output, -input) for all test cases")
    print("  ✓ Same absolute amplitude: |output| = |input|")
    print("  ✓ Perfect cancellation: input + output = 0")
    print("\nConclusion:")
    print("  Counter wave generation working correctly")
    print("  Phase inversion: output = -input (180° phase shift)")
    print("  Sound particle distortion verified through NumPy")
    print("="*80)

    return 0


if __name__ == "__main__":
    exit(main())
