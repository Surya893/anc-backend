"""
Data Collection Script for Noise Classification Training
Helps collect 120+ balanced samples across all noise classes.
"""

import numpy as np
from audio_capture import AudioCapture
from database_schema import ANCDatabase
from collections import defaultdict
import os
import sys


class TrainingDataCollector:
    """Interactive data collection tool for building robust training dataset."""

    def __init__(self, db_path="anc_system.db", target_samples_per_class=20):
        """
        Initialize data collector.

        Args:
            db_path: Database path
            target_samples_per_class: Target number of samples per class
        """
        self.db_path = db_path
        self.target_samples_per_class = target_samples_per_class
        self.capture = AudioCapture(db_path=db_path)

        # Define noise classes with descriptions
        self.noise_classes = {
            'office': {
                'description': 'Office environment (HVAC, typing, conversation)',
                'examples': 'Open office, cubicle, conference room',
                'tips': 'Record during work hours, include keyboard/mouse clicks'
            },
            'street': {
                'description': 'Street traffic noise (cars, buses, motorcycles)',
                'examples': 'Busy street, highway, intersection',
                'tips': 'Vary distance from road, different times of day'
            },
            'home': {
                'description': 'Home environment (appliances, TV, quiet)',
                'examples': 'Living room, kitchen, bedroom',
                'tips': 'Include appliances running, quiet periods'
            },
            'alarm': {
                'description': 'Alarm sounds (fire, car, phone)',
                'examples': 'Fire alarm, car alarm, phone ringtone',
                'tips': 'Use recordings or simulations, vary volume'
            },
            'construction': {
                'description': 'Construction/tools (drilling, hammering, machinery)',
                'examples': 'Construction site, DIY work, power tools',
                'tips': 'Vary distance, different tools'
            },
            'nature': {
                'description': 'Natural sounds (birds, wind, rain, water)',
                'examples': 'Park, forest, rain, stream',
                'tips': 'Different weather, times of day'
            },
            'transport': {
                'description': 'Transportation (train, plane, bus interior)',
                'examples': 'Inside bus/train, airport, subway',
                'tips': 'Different vehicle types, moving vs stopped'
            },
            'crowd': {
                'description': 'Crowd noise (restaurant, mall, event)',
                'examples': 'Restaurant, shopping mall, sports event',
                'tips': 'Vary crowd density, indoor vs outdoor'
            }
        }

    def get_current_stats(self):
        """Get current dataset statistics."""
        db = ANCDatabase(self.db_path)
        recordings = db.get_all_recordings()

        stats = defaultdict(int)
        for rec in recordings:
            env_type = rec[5]  # environment_type
            if env_type:
                stats[env_type] += 1

        db.close()
        return dict(stats)

    def show_progress(self):
        """Display data collection progress."""
        stats = self.get_current_stats()
        total_samples = sum(stats.values())
        target_total = self.target_samples_per_class * len(self.noise_classes)

        print("\n" + "=" * 80)
        print("DATA COLLECTION PROGRESS")
        print("=" * 80)

        print(f"\nTarget: {self.target_samples_per_class} samples per class "
              f"({target_total} total)")
        print(f"Current: {total_samples} samples collected\n")

        # Show progress by class
        print(f"{'Class':<15} {'Count':<8} {'Progress':<30} {'Status':<15}")
        print("─" * 80)

        all_classes_ready = True
        for class_name, class_info in sorted(self.noise_classes.items()):
            count = stats.get(class_name, 0)
            percentage = (count / self.target_samples_per_class) * 100
            percentage = min(percentage, 100)

            # Progress bar
            filled = int(percentage / 100 * 25)
            bar = '█' * filled + '░' * (25 - filled)

            # Status
            if count >= self.target_samples_per_class:
                status = "✓ Complete"
            elif count >= self.target_samples_per_class * 0.5:
                status = "⚠ Halfway"
                all_classes_ready = False
            else:
                status = "○ Needs more"
                all_classes_ready = False

            print(f"{class_name:<15} {count:>3}/{self.target_samples_per_class:<3} {bar} {percentage:>5.1f}%  {status}")

        print("─" * 80)
        overall_percentage = (total_samples / target_total) * 100
        print(f"Overall: {total_samples}/{target_total} samples ({overall_percentage:.1f}%)")

        if all_classes_ready:
            print("\n✓ Dataset is ready for robust training!")
        else:
            needed = target_total - total_samples
            print(f"\n⚠ Need {needed} more samples for balanced dataset")

        return stats, all_classes_ready

    def show_class_info(self, class_name):
        """Show detailed information about a noise class."""
        if class_name not in self.noise_classes:
            print(f"Unknown class: {class_name}")
            return

        info = self.noise_classes[class_name]
        print(f"\n{'═' * 80}")
        print(f"CLASS: {class_name.upper()}")
        print(f"{'═' * 80}")
        print(f"\nDescription: {info['description']}")
        print(f"Examples: {info['examples']}")
        print(f"Recording Tips: {info['tips']}")
        print(f"\nRecommended duration: 5-10 seconds per sample")
        print(f"Recommended variety: Different locations, times, volumes")
        print(f"{'═' * 80}\n")

    def record_samples(self, class_name, num_samples=1, duration=5):
        """
        Record multiple samples for a class.

        Args:
            class_name: Noise class name
            num_samples: Number of samples to record
            duration: Duration per sample (seconds)
        """
        if class_name not in self.noise_classes:
            print(f"Error: Unknown class '{class_name}'")
            print(f"Available classes: {', '.join(self.noise_classes.keys())}")
            return

        print(f"\n{'─' * 80}")
        print(f"Recording {num_samples} sample(s) for class: {class_name}")
        print(f"Duration: {duration} seconds per sample")
        print(f"{'─' * 80}\n")

        successful = 0
        for i in range(num_samples):
            print(f"\nSample {i+1}/{num_samples}")
            print("─" * 40)

            # Get description
            description = input(f"Description (optional, press Enter to skip): ").strip()
            if not description:
                description = f"{class_name} noise sample {i+1}"

            # Get location
            location = input(f"Location (optional): ").strip()
            if not location:
                location = "Unknown"

            print(f"\nReady to record {duration} seconds...")
            input("Press Enter to start recording...")

            try:
                # Record
                self.capture.start_recording(duration_seconds=duration)

                # Save to database
                recording_id = self.capture.save_to_database(
                    environment_type=class_name,
                    location=location,
                    description=description,
                    save_wav=True
                )

                print(f"✓ Recorded and saved (ID: {recording_id})")
                successful += 1

            except Exception as e:
                print(f"✗ Recording failed: {e}")

            # Wait before next recording
            if i < num_samples - 1:
                print("\nGet ready for next recording...")
                import time
                time.sleep(2)

        print(f"\n{'─' * 80}")
        print(f"Completed: {successful}/{num_samples} samples recorded successfully")
        print(f"{'─' * 80}\n")

    def quick_collect(self):
        """Quick collection mode - record for classes that need more samples."""
        stats, ready = self.show_progress()

        if ready:
            print("\n✓ All classes have sufficient samples!")
            return

        print("\n" + "=" * 80)
        print("QUICK COLLECTION MODE")
        print("=" * 80)

        # Find classes that need more samples
        needed_classes = []
        for class_name in self.noise_classes.keys():
            count = stats.get(class_name, 0)
            if count < self.target_samples_per_class:
                needed_classes.append((class_name, self.target_samples_per_class - count))

        # Sort by how many more samples needed
        needed_classes.sort(key=lambda x: x[1], reverse=True)

        print("\nClasses needing more samples:")
        for i, (class_name, needed) in enumerate(needed_classes, 1):
            print(f"  {i}. {class_name:<15} needs {needed} more samples")

        print("\nRecommended workflow:")
        print("  1. Record 5-10 samples for each class")
        print("  2. Vary locations and conditions")
        print("  3. Run this script again to check progress")

    def interactive_menu(self):
        """Interactive menu for data collection."""
        while True:
            print("\n" + "=" * 80)
            print("NOISE CLASSIFICATION - DATA COLLECTION MENU")
            print("=" * 80)
            print("\n1. Show progress")
            print("2. Record samples for a class")
            print("3. Show class information")
            print("4. Quick collect (guided mode)")
            print("5. List all classes")
            print("6. Exit")

            choice = input("\nSelect option (1-6): ").strip()

            if choice == '1':
                self.show_progress()

            elif choice == '2':
                print("\nAvailable classes:")
                for i, class_name in enumerate(sorted(self.noise_classes.keys()), 1):
                    count = self.get_current_stats().get(class_name, 0)
                    print(f"  {i}. {class_name:<15} (current: {count})")

                class_name = input("\nEnter class name: ").strip().lower()
                if class_name in self.noise_classes:
                    try:
                        num_samples = int(input("Number of samples to record (default 1): ") or "1")
                        duration = int(input("Duration per sample in seconds (default 5): ") or "5")
                        self.record_samples(class_name, num_samples, duration)
                    except ValueError:
                        print("Invalid number")
                else:
                    print(f"Unknown class: {class_name}")

            elif choice == '3':
                class_name = input("\nEnter class name: ").strip().lower()
                self.show_class_info(class_name)

            elif choice == '4':
                self.quick_collect()

            elif choice == '5':
                print("\nAvailable noise classes:")
                print("─" * 80)
                for class_name, info in sorted(self.noise_classes.items()):
                    count = self.get_current_stats().get(class_name, 0)
                    print(f"{class_name:<15} (current: {count:>3}) - {info['description']}")

            elif choice == '6':
                print("\nExiting data collection...")
                self.capture.cleanup()
                break

            else:
                print("Invalid choice. Please select 1-6.")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Collect training data for noise classification')
    parser.add_argument('--target', type=int, default=20,
                       help='Target samples per class (default: 20)')
    parser.add_argument('--class', dest='noise_class', type=str,
                       help='Specific class to record')
    parser.add_argument('--num', type=int, default=1,
                       help='Number of samples to record')
    parser.add_argument('--duration', type=int, default=5,
                       help='Duration per sample in seconds')

    args = parser.parse_args()

    collector = TrainingDataCollector(target_samples_per_class=args.target)

    if args.noise_class:
        # Direct recording mode
        collector.record_samples(args.noise_class, args.num, args.duration)
    else:
        # Interactive mode
        print("=" * 80)
        print("NOISE CLASSIFICATION TRAINING DATA COLLECTOR")
        print("=" * 80)
        print("\nThis tool helps you collect balanced training data for the")
        print("noise classification model.")
        print(f"\nTarget: {args.target} samples per class")
        print(f"Total needed: {args.target * len(collector.noise_classes)} samples")

        # Show current progress
        stats, ready = collector.show_progress()

        if not ready:
            print("\n💡 TIP: For best results:")
            print("   - Record in quiet environment with clear noise source")
            print("   - Vary recording conditions (distance, time, location)")
            print("   - Keep consistent recording duration (5-10 seconds)")
            print("   - Ensure balanced samples across all classes")

        # Start interactive menu
        collector.interactive_menu()


if __name__ == "__main__":
    main()
