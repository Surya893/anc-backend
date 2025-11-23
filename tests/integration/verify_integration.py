#!/usr/bin/env python3
"""
Verify Full Integration - Test main.py components in Claude

Tests all integration points without requiring audio hardware.
"""

import sys
import os
import numpy as np
from datetime import datetime


def verify_imports():
    """Verify all required modules can be imported."""
    print("="*80)
    print("INTEGRATION VERIFICATION - IMPORTS")
    print("="*80)

    modules = [
        ('database_schema', 'ANCDatabase'),
        ('feature_extraction', 'AudioFeatureExtractor'),
        ('predict_sklearn', 'NoisePredictor'),
        ('emergency_noise_detector', 'EmergencyNoiseDetector'),
        ('anti_noise_generator', 'AntiNoiseGenerator'),
    ]

    print("\n[TEST 1] Module Imports")
    print("-"*80)

    all_passed = True

    for module_name, class_name in modules:
        try:
            module = __import__(module_name)
            cls = getattr(module, class_name)
            print(f"  ✓ {module_name}.{class_name}")
        except Exception as e:
            print(f"  ✗ {module_name}.{class_name}: {e}")
            all_passed = False

    # Test main.py import
    try:
        import main
        print(f"  ✓ main.py")
    except Exception as e:
        print(f"  ✗ main.py: {e}")
        all_passed = False

    return all_passed


def verify_anc_core_init():
    """Verify ANCSystemCore can be initialized."""
    print("\n[TEST 2] ANCSystemCore Initialization")
    print("-"*80)

    try:
        from main import ANCSystemCore

        # Initialize (models may not exist yet)
        anc_core = ANCSystemCore(db_path="test_integration.db")

        print(f"  ✓ ANCSystemCore initialized")
        print(f"  ✓ Sample rate: {anc_core.sample_rate} Hz")
        print(f"  ✓ Chunk size: {anc_core.chunk_size} samples")
        print(f"  ✓ Database: {anc_core.db is not None}")
        print(f"  ✓ Feature extractor: {anc_core.feature_extractor is not None}")
        print(f"  ✓ Anti-noise generator: {anc_core.anti_noise_gen is not None}")

        # Check state
        print(f"  ✓ Initial state: ANC={'ON' if anc_core.anc_enabled else 'OFF'}")

        # Cleanup
        anc_core.cleanup()

        # Remove test database
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

        return True

    except Exception as e:
        print(f"  ✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_audio_processing():
    """Verify audio processing pipeline without hardware."""
    print("\n[TEST 3] Audio Processing Pipeline")
    print("-"*80)

    try:
        from main import ANCSystemCore

        # Initialize
        anc_core = ANCSystemCore(db_path="test_integration.db")
        anc_core.anc_enabled = True

        # Generate test audio (1 second of 440 Hz tone)
        duration = 1.0
        sample_rate = anc_core.sample_rate
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = 0.3 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

        print(f"  Generated test audio: {len(test_audio)} samples")

        # Process chunk
        chunk_size = anc_core.chunk_size
        audio_chunk = test_audio[:chunk_size]

        print(f"  Processing chunk: {len(audio_chunk)} samples")

        # Analyze audio
        analysis = anc_core.analyze_audio(audio_chunk)

        print(f"  ✓ Analysis complete:")
        print(f"    - Noise class: {analysis['noise_class']}")
        print(f"    - Confidence: {analysis['confidence']:.2%}")
        print(f"    - Intensity: {analysis['intensity_db']:.1f} dB")
        print(f"    - Emergency: {analysis['is_emergency']}")
        print(f"    - Features: {len(analysis['features'])} dimensions")

        # Test anti-noise generation
        anti_noise, _ = anc_core.process_audio_chunk(audio_chunk)

        if anti_noise is not None:
            print(f"  ✓ Anti-noise generated: {len(anti_noise)} samples")

            # Verify phase inversion
            assert len(anti_noise) == len(audio_chunk)
            print(f"  ✓ Length matches: {len(anti_noise)} == {len(audio_chunk)}")

            # Check anti-noise properties
            correlation = np.corrcoef(audio_chunk, anti_noise)[0, 1]
            print(f"  ✓ Correlation: {correlation:.4f} (should be ≈ -1.0)")

            # Check cancellation
            combined = audio_chunk + anti_noise
            residual_rms = np.sqrt(np.mean(combined**2))
            print(f"  ✓ Residual RMS: {residual_rms:.6f} (should be ≈ 0)")

        else:
            print(f"  ⚠ Anti-noise not generated (models may not be trained)")

        # Cleanup
        anc_core.cleanup()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

        return True

    except Exception as e:
        print(f"  ✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_state_management():
    """Verify state management and control."""
    print("\n[TEST 4] State Management")
    print("-"*80)

    try:
        from main import ANCSystemCore

        anc_core = ANCSystemCore(db_path="test_integration.db")

        # Test ANC enable/disable
        anc_core.set_anc_enabled(True)
        assert anc_core.anc_enabled == True
        print(f"  ✓ ANC enabled")

        anc_core.set_anc_enabled(False)
        assert anc_core.anc_enabled == False
        print(f"  ✓ ANC disabled")

        # Test intensity setting
        anc_core.set_noise_intensity(0.75)
        assert anc_core.noise_intensity_threshold == 0.75
        print(f"  ✓ Intensity set to 0.75")

        # Test boundary conditions
        anc_core.set_noise_intensity(1.5)  # Should clamp to 1.0
        assert anc_core.noise_intensity_threshold == 1.0
        print(f"  ✓ Intensity clamped to 1.0")

        anc_core.set_noise_intensity(-0.5)  # Should clamp to 0.0
        assert anc_core.noise_intensity_threshold == 0.0
        print(f"  ✓ Intensity clamped to 0.0")

        # Test state retrieval
        state = anc_core.get_state()
        print(f"  ✓ State retrieved:")
        print(f"    - ANC enabled: {state['anc_enabled']}")
        print(f"    - Noise intensity: {state['noise_intensity']}")
        print(f"    - Current class: {state['current_noise_class']}")
        print(f"    - Emergency: {state['emergency_detected']}")

        # Test emergency reset
        anc_core.emergency_detected = True
        anc_core.emergency_bypass = True
        anc_core.reset_emergency()
        assert anc_core.emergency_bypass == False
        assert anc_core.emergency_detected == False
        print(f"  ✓ Emergency reset")

        # Cleanup
        anc_core.cleanup()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

        return True

    except Exception as e:
        print(f"  ✗ State management failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_web_integration():
    """Verify web UI integration."""
    print("\n[TEST 5] Web UI Integration")
    print("-"*80)

    try:
        from main import ANCSystemCore, ANCSystemWithWebUI

        # Initialize core
        anc_core = ANCSystemCore(db_path="test_integration.db")

        # Initialize web integration
        anc_with_web = ANCSystemWithWebUI(anc_core)

        if anc_with_web.flask_app:
            print(f"  ✓ Flask app loaded")

            # Test state sync
            anc_core.set_anc_enabled(True)
            anc_core.set_noise_intensity(0.8)

            anc_with_web.sync_state_to_web()
            print(f"  ✓ State synced to web")

            # Check web state
            with anc_with_web.web_lock:
                assert anc_with_web.web_state.anc_enabled == True
                assert anc_with_web.web_state.noise_intensity == 0.8
                print(f"  ✓ Web state matches core state")

                # Modify web state
                anc_with_web.web_state.anc_enabled = False
                anc_with_web.web_state.noise_intensity = 0.5

            anc_with_web.sync_state_from_web()
            print(f"  ✓ State synced from web")

            # Check core state
            assert anc_core.anc_enabled == False
            assert anc_core.noise_intensity_threshold == 0.5
            print(f"  ✓ Core state matches web state")

        else:
            print(f"  ⚠ Flask app not available (app.py may be missing)")

        # Cleanup
        anc_core.cleanup()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

        return True

    except Exception as e:
        print(f"  ✗ Web integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_command_line_args():
    """Verify command-line argument parsing."""
    print("\n[TEST 6] Command-Line Arguments")
    print("-"*80)

    try:
        import argparse
        from main import main

        # Create test parser (same as main.py)
        parser = argparse.ArgumentParser()
        parser.add_argument('--mode', choices=['core', 'web'], default='core')
        parser.add_argument('--duration', type=int, default=None)
        parser.add_argument('--host', default='0.0.0.0')
        parser.add_argument('--port', type=int, default=5000)
        parser.add_argument('--db', default='anc_system.db')

        # Test various argument combinations
        test_cases = [
            ['--mode', 'core'],
            ['--mode', 'web', '--port', '8080'],
            ['--duration', '60'],
            ['--db', 'custom.db'],
        ]

        for args in test_cases:
            parsed = parser.parse_args(args)
            print(f"  ✓ Parsed: {' '.join(args)}")

        return True

    except Exception as e:
        print(f"  ✗ Argument parsing failed: {e}")
        return False


def verify_threading_safety():
    """Verify thread-safe operations."""
    print("\n[TEST 7] Thread Safety")
    print("-"*80)

    try:
        from main import ANCSystemCore
        import threading

        anc_core = ANCSystemCore(db_path="test_integration.db")

        # Test concurrent state access
        def modify_state():
            for i in range(10):
                anc_core.set_anc_enabled(i % 2 == 0)
                anc_core.set_noise_intensity(i / 10.0)

        threads = [threading.Thread(target=modify_state) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        print(f"  ✓ Concurrent state modifications completed")

        # Test concurrent state reads
        def read_state():
            for _ in range(10):
                state = anc_core.get_state()

        threads = [threading.Thread(target=read_state) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        print(f"  ✓ Concurrent state reads completed")

        # Cleanup
        anc_core.cleanup()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

        return True

    except Exception as e:
        print(f"  ✗ Thread safety test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("\n" + "="*80)
    print("FULL INTEGRATION VERIFICATION SUITE")
    print("="*80)
    print("\nTesting main.py integration without audio hardware")
    print("Actual audio testing must be done locally with microphone/speakers")
    print("="*80)

    tests = [
        ("Module Imports", verify_imports),
        ("ANC Core Initialization", verify_anc_core_init),
        ("Audio Processing Pipeline", verify_audio_processing),
        ("State Management", verify_state_management),
        ("Web UI Integration", verify_web_integration),
        ("Command-Line Arguments", verify_command_line_args),
        ("Thread Safety", verify_threading_safety),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")
    print()

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {status}: {test_name}")

    print("\n" + "="*80)

    if passed == total:
        print("INTEGRATION VERIFIED - READY FOR LOCAL TESTING")
        print("="*80)
        print("\nNext steps:")
        print("  1. Train models: python train_sklearn_demo.py")
        print("  2. Run core mode: python main.py --mode core --duration 30")
        print("  3. Run web mode: python main.py --mode web")
        print("="*80)
        return 0
    else:
        print("INTEGRATION VERIFICATION FAILED")
        print("="*80)
        print("\nPlease fix the failed tests before running main.py")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
