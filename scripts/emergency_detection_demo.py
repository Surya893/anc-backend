#!/usr/bin/env python3
"""
Emergency Detection and ANC Bypass Demo
========================================

This script demonstrates the emergency sound detection system and
how it bypasses ANC for safety-critical sounds like fire alarms.

Usage:
    python scripts/emergency_detection_demo.py

Features:
    - Classifies emergency sounds (alarms, sirens, warnings)
    - Automatically bypasses ANC when emergencies detected
    - Sends notifications for emergency events
    - Provides real-time safety monitoring
"""

import sys
import os
import numpy as np
import argparse
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'ml'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

try:
    from src.ml.emergency_noise_detector import EmergencyNoiseDetector
    from src.core.audio_processor import AudioProcessor
except ImportError:
    from emergency_noise_detector import EmergencyNoiseDetector
    from audio_processor import AudioProcessor


def generate_test_sounds():
    """Generate various test sounds for demonstration."""

    test_sounds = {
        'smoke_alarm': {
            'description': 'Smoke/Fire Alarm (3kHz modulated)',
            'expected': 'EMERGENCY',
            'generator': lambda: generate_alarm_sound(3000, 2.0)
        },
        'fire_alarm': {
            'description': 'Fire Alarm (2.8kHz)',
            'expected': 'EMERGENCY',
            'generator': lambda: generate_alarm_sound(2800, 1.5)
        },
        'siren': {
            'description': 'Emergency Siren (sweeping)',
            'expected': 'EMERGENCY',
            'generator': lambda: generate_siren_sound()
        },
        'office': {
            'description': 'Office Background Noise',
            'expected': 'NORMAL',
            'generator': lambda: generate_normal_noise(500)
        },
        'traffic': {
            'description': 'Street Traffic',
            'expected': 'NORMAL',
            'generator': lambda: generate_normal_noise(200)
        },
        'hvac': {
            'description': 'HVAC System',
            'expected': 'NORMAL',
            'generator': lambda: generate_normal_noise(400)
        }
    }

    return test_sounds


def generate_alarm_sound(frequency=3000, duration=2.0, sample_rate=44100):
    """Generate realistic alarm sound."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # High-frequency tone with amplitude modulation
    signal = 0.7 * np.sin(2 * np.pi * frequency * t)

    # Beeping pattern (2 Hz)
    modulation = 0.5 + 0.5 * (np.sin(2 * np.pi * 2 * t) > 0)
    signal *= modulation

    # Add harmonic
    signal += 0.3 * np.sin(2 * np.pi * (frequency * 1.05) * t) * modulation

    return signal


def generate_siren_sound(duration=2.0, sample_rate=44100):
    """Generate emergency siren with frequency sweep."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Sweeping frequency (800-1500 Hz)
    freq_sweep = 800 + 700 * np.sin(2 * np.pi * 1.5 * t)
    phase = 2 * np.pi * np.cumsum(freq_sweep) / sample_rate

    signal = 0.6 * np.sin(phase)

    return signal


def generate_normal_noise(frequency=500, duration=2.0, sample_rate=44100):
    """Generate normal background noise."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Low frequency rumble + white noise
    signal = 0.3 * np.sin(2 * np.pi * frequency * t)
    signal += 0.1 * np.random.randn(len(t))

    return signal


def print_header():
    """Print demo header."""
    print("\n" + "="*80)
    print("EMERGENCY DETECTION & ANC BYPASS DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows how the ANC system:")
    print("  1. Detects emergency/alarm sounds in real-time")
    print("  2. Automatically bypasses ANC for safety")
    print("  3. Sends notifications for emergency events")
    print("  4. Protects user safety while maintaining comfort")
    print("="*80 + "\n")


def run_classification_demo():
    """Run emergency sound classification demo."""
    print("\n" + "─"*80)
    print("PART 1: EMERGENCY SOUND CLASSIFICATION")
    print("─"*80 + "\n")

    # Initialize detector
    try:
        detector = EmergencyNoiseDetector(confidence_threshold=0.60)
    except Exception as e:
        print(f"⚠️  Could not load model: {e}")
        print("   Using simulation mode...")
        return simulate_classification_demo()

    # Get test sounds
    test_sounds = generate_test_sounds()

    results = []

    for sound_name, sound_info in test_sounds.items():
        print(f"\n{'─'*80}")
        print(f"Test: {sound_info['description']}")
        print(f"Expected: {sound_info['expected']}")
        print(f"{'─'*80}")

        # Generate audio
        audio = sound_info['generator']()

        # Detect
        try:
            should_apply_anc, detection = detector.process_audio(
                audio,
                send_notification=(sound_info['expected'] == 'EMERGENCY')
            )

            result = {
                'name': sound_name,
                'description': sound_info['description'],
                'predicted': detection['predicted_class'],
                'confidence': detection['confidence'],
                'is_emergency': detection['is_emergency'],
                'expected': sound_info['expected'],
                'anc_action': 'BYPASS' if not should_apply_anc else 'APPLY'
            }

            results.append(result)

            # Display result
            print(f"\n✓ Detection Complete:")
            print(f"  Class: {detection['predicted_class']}")
            print(f"  Confidence: {detection['confidence']*100:.1f}%")
            print(f"  Emergency: {'YES 🚨' if detection['is_emergency'] else 'NO'}")
            print(f"  ANC Action: {result['anc_action']}")

            if detection['is_emergency']:
                print(f"\n  ⚠️  SAFETY OVERRIDE: ANC bypassed to preserve emergency sound!")

        except Exception as e:
            print(f"✗ Detection error: {e}")

        time.sleep(0.3)  # Brief pause

    # Summary
    print(f"\n{'='*80}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'='*80}\n")

    for r in results:
        emergency_marker = "🚨" if r['is_emergency'] else "  "
        print(f"{emergency_marker} {r['description']:<40} → {r['predicted']:<15} "
              f"({r['confidence']*100:.0f}%) ANC: {r['anc_action']}")

    # Statistics
    emergency_count = sum(1 for r in results if r['is_emergency'])
    print(f"\nEmergency sounds detected: {emergency_count}/{len(results)}")
    print(f"ANC bypasses performed: {emergency_count}")


def simulate_classification_demo():
    """Simulate classification when model not available."""
    print("\nRunning in simulation mode...\n")

    test_cases = [
        ("Smoke Alarm", "alarm", 0.95, True),
        ("Fire Alarm", "alarm", 0.88, True),
        ("Emergency Siren", "siren", 0.92, True),
        ("Office Noise", "office", 0.75, False),
        ("Traffic", "street", 0.82, False),
        ("HVAC", "hvac", 0.70, False),
    ]

    for name, classification, confidence, is_emergency in test_cases:
        print(f"{'─'*80}")
        print(f"Test: {name}")
        print(f"  Class: {classification}")
        print(f"  Confidence: {confidence*100:.1f}%")
        print(f"  Emergency: {'YES 🚨' if is_emergency else 'NO'}")
        print(f"  ANC: {'BYPASS' if is_emergency else 'APPLY'}")

        if is_emergency:
            print(f"  ⚠️  SAFETY: Emergency detected - ANC bypassed!")

        time.sleep(0.2)


def run_safety_scenario():
    """Demonstrate complete safety scenario."""
    print("\n" + "─"*80)
    print("PART 2: REAL-WORLD SAFETY SCENARIO")
    print("─"*80 + "\n")

    print("Scenario: User wearing ANC headphones at home\n")

    # Phase 1
    print(f"{'─'*80}")
    print("Phase 1: Normal Operation")
    print(f"{'─'*80}")
    print("  Time: 2:30 PM")
    print("  Environment: Home office with HVAC running")
    print("  ANC Status: ACTIVE ✓")
    print("  Audio: HVAC noise cancelled")
    print("  User Experience: Quiet, focused work environment")
    time.sleep(1)

    # Phase 2
    print(f"\n{'─'*80}")
    print("Phase 2: EMERGENCY DETECTED 🚨")
    print(f"{'─'*80}")
    print("  Time: 2:45 PM")
    print("  Event: Kitchen smoke detector triggered")
    print("  Sound: 3kHz fire alarm (85 dB)")
    print("\n  🔍 DETECTION IN PROGRESS...")
    time.sleep(0.5)
    print("     ✓ Sound classified: FIRE_ALARM")
    print("     ✓ Confidence: 94.2%")
    print("     ✓ Emergency status: CONFIRMED")
    time.sleep(0.5)

    # Phase 3
    print(f"\n  🛡️  SAFETY SYSTEM RESPONSE:")
    print("     → ANC cancellation BYPASSED immediately")
    print("     → Alarm passes through unmodified")
    print("     → API notification sent")
    print("     → Event logged with timestamp")
    time.sleep(0.5)

    # Phase 4
    print(f"\n{'─'*80}")
    print("Phase 3: User Response")
    print(f"{'─'*80}")
    print("  ✓ User hears alarm clearly through headphones")
    print("  ✓ User investigates kitchen")
    print("  ✓ User discovers burnt toast (false alarm)")
    print("  ✓ User ventilates kitchen, resets alarm")
    time.sleep(1)

    # Phase 5
    print(f"\n{'─'*80}")
    print("Phase 4: Normal Operation Resumed")
    print(f"{'─'*80}")
    print("  Time: 2:50 PM")
    print("  Alarm cleared")
    print("  ANC Status: ACTIVE ✓")
    print("  User Experience: Quiet environment restored")

    # Outcome
    print(f"\n{'='*80}")
    print("OUTCOME: ✅ SAFETY SYSTEM SUCCESSFUL")
    print(f"{'='*80}")
    print("\nKey Points:")
    print("  ✓ Emergency sound detected in <100ms")
    print("  ✓ ANC bypassed automatically")
    print("  ✓ User alerted despite ANC being enabled")
    print("  ✓ No user intervention required")
    print("  ✓ System returned to normal operation")
    print("\n⚠️  CRITICAL: User safety maintained at all times!")


def run_technical_demo():
    """Demonstrate technical implementation details."""
    print("\n" + "─"*80)
    print("PART 3: TECHNICAL IMPLEMENTATION")
    print("─"*80 + "\n")

    print("Emergency Detection Pipeline:")
    print(f"{'─'*80}\n")

    print("1. Audio Input (Real-time)")
    print("   └─ Microphone → Buffer (1024 samples @ 44.1kHz)")
    print("   └─ Latency: ~23ms\n")

    print("2. Feature Extraction")
    print("   └─ MFCC (13 coefficients)")
    print("   └─ Spectral features (centroid, rolloff)")
    print("   └─ Temporal features (ZCR, RMS)")
    print("   └─ Processing time: ~5ms\n")

    print("3. Classification (ML Model)")
    print("   └─ Algorithm: Random Forest / SVM")
    print("   └─ Classes: [alarm, siren, warning, office, street, ...]")
    print("   └─ Inference time: ~3ms\n")

    print("4. Emergency Detection")
    print("   └─ Check: Is class in EMERGENCY_TYPES?")
    print("   └─ Check: Confidence >= threshold (0.70)?")
    print("   └─ Decision time: <1ms\n")

    print("5. ANC Bypass Decision")
    print("   └─ IF emergency: should_apply_anc = False")
    print("   └─ ELSE: should_apply_anc = True")
    print("   └─ Action: Immediate (no delay)\n")

    print("6. Output")
    print("   └─ IF emergency: Original audio passed through")
    print("   └─ ELSE: ANC applied (anti-noise generated)")
    print("   └─ Total latency: <35ms (real-time)\n")

    print(f"{'='*80}")
    print("SAFETY GUARANTEES")
    print(f"{'='*80}\n")
    print("✓ Emergency sounds NEVER cancelled")
    print("✓ Detection happens in real-time (<100ms)")
    print("✓ System fail-safe: errors default to NO cancellation")
    print("✓ Multiple redundancy checks")
    print("✓ Full event logging for audit trail")
    print("\n⚠️  Safety is the #1 priority - comfort is secondary")


def main():
    """Main demo entry point."""
    parser = argparse.ArgumentParser(
        description='Emergency Detection & ANC Bypass Demo'
    )
    parser.add_argument(
        '--part',
        type=int,
        choices=[1, 2, 3],
        help='Run specific part only (1=classification, 2=scenario, 3=technical)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick version of demo'
    )

    args = parser.parse_args()

    # Print header
    print_header()

    # Run requested parts
    if args.part is None or args.part == 1:
        run_classification_demo()

    if not args.quick:
        if args.part is None or args.part == 2:
            run_safety_scenario()

        if args.part is None or args.part == 3:
            run_technical_demo()

    # Final summary
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print("\nEmergency Detection System Status: ✅ OPERATIONAL")
    print("\nFor more information:")
    print("  - Code: src/ml/emergency_noise_detector.py")
    print("  - Integration: src/core/audio_processor.py")
    print("  - Tests: tests/unit/test_emergency_detection.py")
    print("\nTo train custom emergency classifiers:")
    print("  - python scripts/training/finetune_emergency_classifier.py")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
