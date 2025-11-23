"""
Frequent Noise Pattern Manager
Analyzes and manages common noise patterns from database recordings.
Helps identify and categorize frequently occurring noise types.
"""

import numpy as np
from database_schema import ANCDatabase
from collections import defaultdict
import json


class FrequentNoiseManager:
    """
    Manages frequent noise definitions and patterns.
    Analyzes noise recordings to identify common patterns.
    """

    def __init__(self, db_path="anc_system.db"):
        self.db = ANCDatabase(db_path)

    def get_noise_statistics(self):
        """
        Get statistics about all recorded noise samples.

        Returns:
            dict: Statistics including counts by environment, location, etc.
        """
        recordings = self.db.get_all_recordings()

        stats = {
            'total_recordings': len(recordings),
            'by_environment': defaultdict(int),
            'by_location': defaultdict(int),
            'noise_levels': [],
            'durations': [],
            'timestamps': []
        }

        for rec in recordings:
            rec_id, timestamp, duration, sample_rate, num_samples, env_type, noise_db, location = rec

            # Count by environment
            if env_type:
                stats['by_environment'][env_type] += 1

            # Count by location
            if location:
                stats['by_location'][location] += 1

            # Collect noise levels
            if noise_db is not None:
                stats['noise_levels'].append(noise_db)

            # Collect durations
            stats['durations'].append(duration)

            # Collect timestamps
            stats['timestamps'].append(timestamp)

        return stats

    def identify_frequent_patterns(self, min_occurrences=2):
        """
        Identify frequently occurring noise patterns.

        Args:
            min_occurrences: Minimum number of occurrences to be considered frequent

        Returns:
            dict: Frequent patterns with counts
        """
        stats = self.get_noise_statistics()

        frequent_patterns = {
            'environments': {},
            'locations': {},
            'noise_level_ranges': {}
        }

        # Filter environments by frequency
        for env, count in stats['by_environment'].items():
            if count >= min_occurrences:
                frequent_patterns['environments'][env] = count

        # Filter locations by frequency
        for loc, count in stats['by_location'].items():
            if count >= min_occurrences:
                frequent_patterns['locations'][loc] = count

        # Categorize noise levels into ranges
        if stats['noise_levels']:
            noise_ranges = {
                'very_quiet': (-np.inf, -40),
                'quiet': (-40, -20),
                'moderate': (-20, 0),
                'loud': (0, 20),
                'very_loud': (20, np.inf)
            }

            range_counts = defaultdict(int)
            for db_level in stats['noise_levels']:
                for range_name, (min_db, max_db) in noise_ranges.items():
                    if min_db <= db_level < max_db:
                        range_counts[range_name] += 1
                        break

            for range_name, count in range_counts.items():
                if count >= min_occurrences:
                    frequent_patterns['noise_level_ranges'][range_name] = count

        return frequent_patterns

    def get_noise_definition(self, recording_id):
        """
        Get detailed noise definition for a recording.

        Args:
            recording_id: Database recording ID

        Returns:
            dict: Complete noise definition with waveform statistics
        """
        # Get recording metadata
        self.db.cursor.execute("""
            SELECT recording_id, timestamp, duration_seconds, sampling_rate,
                   num_samples, environment_type, noise_level_db, location,
                   description, metadata_json
            FROM noise_recordings
            WHERE recording_id = ?
        """, (recording_id,))

        rec = self.db.cursor.fetchone()
        if not rec:
            return None

        # Get waveform statistics
        self.db.cursor.execute("""
            SELECT waveform_type, num_samples, min_amplitude, max_amplitude,
                   mean_amplitude, std_amplitude
            FROM audio_waveforms
            WHERE recording_id = ?
        """, (recording_id,))

        waveforms = self.db.cursor.fetchall()

        # Build definition
        definition = {
            'recording_id': rec[0],
            'timestamp': rec[1],
            'duration_seconds': rec[2],
            'sampling_rate': rec[3],
            'num_samples': rec[4],
            'environment_type': rec[5],
            'noise_level_db': rec[6],
            'location': rec[7],
            'description': rec[8],
            'metadata': json.loads(rec[9]) if rec[9] else {},
            'waveforms': []
        }

        for wf in waveforms:
            definition['waveforms'].append({
                'type': wf[0],
                'num_samples': wf[1],
                'min_amplitude': wf[2],
                'max_amplitude': wf[3],
                'mean_amplitude': wf[4],
                'std_amplitude': wf[5]
            })

        return definition

    def get_similar_noise_recordings(self, recording_id, tolerance=5.0):
        """
        Find recordings with similar noise characteristics.

        Args:
            recording_id: Reference recording ID
            tolerance: Tolerance in dB for similarity

        Returns:
            list: Similar recording IDs with similarity scores
        """
        # Get reference recording
        ref_def = self.get_noise_definition(recording_id)
        if not ref_def:
            return []

        ref_noise_db = ref_def['noise_level_db']
        ref_env = ref_def['environment_type']

        # Find similar recordings
        self.db.cursor.execute("""
            SELECT recording_id, noise_level_db, environment_type
            FROM noise_recordings
            WHERE recording_id != ?
        """, (recording_id,))

        similar = []
        for rec in self.db.cursor.fetchall():
            rec_id, noise_db, env_type = rec

            # Calculate similarity score
            score = 100.0

            # Noise level similarity
            if ref_noise_db is not None and noise_db is not None:
                db_diff = abs(ref_noise_db - noise_db)
                if db_diff <= tolerance:
                    db_similarity = (tolerance - db_diff) / tolerance * 50
                    score += db_similarity

            # Environment similarity
            if ref_env and env_type and ref_env == env_type:
                score += 50

            # Consider it similar if score is high enough
            if score >= 60:
                similar.append({
                    'recording_id': rec_id,
                    'similarity_score': score,
                    'noise_level_db': noise_db,
                    'environment_type': env_type
                })

        # Sort by similarity score
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)

        return similar

    def create_noise_profile(self, environment_type):
        """
        Create an average noise profile for a specific environment.

        Args:
            environment_type: Type of environment (e.g., "office", "street")

        Returns:
            dict: Average noise profile with statistics
        """
        # Get all recordings for this environment
        self.db.cursor.execute("""
            SELECT recording_id, duration_seconds, noise_level_db
            FROM noise_recordings
            WHERE environment_type = ?
        """, (environment_type,))

        recordings = self.db.cursor.fetchall()

        if not recordings:
            return None

        # Calculate averages
        durations = [r[1] for r in recordings]
        noise_levels = [r[2] for r in recordings if r[2] is not None]

        profile = {
            'environment_type': environment_type,
            'sample_count': len(recordings),
            'avg_duration': np.mean(durations),
            'avg_noise_level_db': np.mean(noise_levels) if noise_levels else None,
            'std_noise_level_db': np.std(noise_levels) if noise_levels else None,
            'min_noise_level_db': np.min(noise_levels) if noise_levels else None,
            'max_noise_level_db': np.max(noise_levels) if noise_levels else None,
            'recording_ids': [r[0] for r in recordings]
        }

        return profile

    def export_frequent_definitions(self, output_file="frequent_noise_definitions.json"):
        """
        Export frequent noise definitions to JSON file.

        Args:
            output_file: Output filename
        """
        # Get statistics and patterns
        stats = self.get_noise_statistics()
        patterns = self.identify_frequent_patterns()

        # Create profiles for each frequent environment
        environment_profiles = {}
        for env in patterns['environments'].keys():
            profile = self.create_noise_profile(env)
            if profile:
                environment_profiles[env] = profile

        # Compile export data
        export_data = {
            'statistics': {
                'total_recordings': stats['total_recordings'],
                'environments': dict(stats['by_environment']),
                'locations': dict(stats['by_location']),
                'avg_noise_level_db': np.mean(stats['noise_levels']) if stats['noise_levels'] else None,
                'avg_duration': np.mean(stats['durations']) if stats['durations'] else None
            },
            'frequent_patterns': patterns,
            'environment_profiles': environment_profiles
        }

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"✓ Frequent noise definitions exported to: {output_file}")

    def print_report(self):
        """Print a comprehensive report of frequent noise patterns."""
        print("=" * 80)
        print("FREQUENT NOISE PATTERNS REPORT")
        print("=" * 80)

        stats = self.get_noise_statistics()
        patterns = self.identify_frequent_patterns()

        # Overall statistics
        print(f"\nOverall Statistics:")
        print(f"  Total Recordings: {stats['total_recordings']}")

        if stats['noise_levels']:
            print(f"  Average Noise Level: {np.mean(stats['noise_levels']):.2f} dB")
            print(f"  Noise Level Range: {np.min(stats['noise_levels']):.2f} to "
                  f"{np.max(stats['noise_levels']):.2f} dB")

        if stats['durations']:
            print(f"  Average Duration: {np.mean(stats['durations']):.2f} seconds")
            print(f"  Total Recording Time: {np.sum(stats['durations']):.2f} seconds")

        # Frequent environments
        print(f"\n{'─' * 80}")
        print("Frequent Environments:")
        print(f"{'─' * 80}")
        if patterns['environments']:
            for env, count in sorted(patterns['environments'].items(),
                                    key=lambda x: x[1], reverse=True):
                percentage = (count / stats['total_recordings']) * 100
                print(f"  {env:<20} {count:>3} recordings ({percentage:>5.1f}%)")

                # Show profile for this environment
                profile = self.create_noise_profile(env)
                if profile and profile['avg_noise_level_db'] is not None:
                    print(f"    Average Noise Level: {profile['avg_noise_level_db']:.2f} dB "
                          f"(±{profile['std_noise_level_db']:.2f})")
        else:
            print("  No frequent patterns detected")

        # Frequent locations
        print(f"\n{'─' * 80}")
        print("Frequent Locations:")
        print(f"{'─' * 80}")
        if patterns['locations']:
            for loc, count in sorted(patterns['locations'].items(),
                                    key=lambda x: x[1], reverse=True):
                percentage = (count / stats['total_recordings']) * 100
                print(f"  {loc:<20} {count:>3} recordings ({percentage:>5.1f}%)")
        else:
            print("  No frequent patterns detected")

        # Noise level distribution
        print(f"\n{'─' * 80}")
        print("Noise Level Distribution:")
        print(f"{'─' * 80}")
        if patterns['noise_level_ranges']:
            for range_name, count in sorted(patterns['noise_level_ranges'].items(),
                                           key=lambda x: x[1], reverse=True):
                percentage = (count / len(stats['noise_levels'])) * 100 if stats['noise_levels'] else 0
                print(f"  {range_name:<15} {count:>3} recordings ({percentage:>5.1f}%)")
        else:
            print("  Insufficient data")

        print("\n" + "=" * 80)

    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main function for command-line usage."""
    import sys

    manager = FrequentNoiseManager()

    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "report":
                manager.print_report()

            elif command == "export":
                output_file = sys.argv[2] if len(sys.argv) > 2 else "frequent_noise_definitions.json"
                manager.export_frequent_definitions(output_file)

            elif command == "profile":
                if len(sys.argv) < 3:
                    print("Usage: python frequent_noise_manager.py profile <environment_type>")
                    return

                env_type = sys.argv[2]
                profile = manager.create_noise_profile(env_type)

                if profile:
                    print(f"\nNoise Profile for '{env_type}':")
                    print(f"  Sample Count: {profile['sample_count']}")
                    print(f"  Average Duration: {profile['avg_duration']:.2f}s")
                    if profile['avg_noise_level_db']:
                        print(f"  Average Noise Level: {profile['avg_noise_level_db']:.2f} dB")
                        print(f"  Std Dev: {profile['std_noise_level_db']:.2f} dB")
                        print(f"  Range: {profile['min_noise_level_db']:.2f} to "
                              f"{profile['max_noise_level_db']:.2f} dB")
                else:
                    print(f"No recordings found for environment: {env_type}")

            elif command == "similar":
                if len(sys.argv) < 3:
                    print("Usage: python frequent_noise_manager.py similar <recording_id>")
                    return

                recording_id = int(sys.argv[2])
                similar = manager.get_similar_noise_recordings(recording_id)

                print(f"\nSimilar recordings to ID {recording_id}:")
                for sim in similar[:10]:  # Show top 10
                    print(f"  Recording {sim['recording_id']}: "
                          f"Similarity {sim['similarity_score']:.1f}%, "
                          f"Env: {sim['environment_type']}, "
                          f"Noise: {sim['noise_level_db']:.2f} dB")

            else:
                print("Unknown command. Available commands:")
                print("  report   - Display comprehensive report")
                print("  export   - Export definitions to JSON")
                print("  profile  - Show profile for specific environment")
                print("  similar  - Find similar recordings")

        else:
            # Default: show report
            manager.print_report()

    finally:
        manager.close()


if __name__ == "__main__":
    main()
