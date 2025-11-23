# Audio Capture System Documentation

## Overview

Real-time audio capture system for the ANC (Active Noise Cancellation) project. This system captures noise from microphone, records as WAV files, and stores in SQLite database with comprehensive metadata for noise pattern analysis.

## Features

- **Real-time Audio Capture**: Record audio from microphone using PyAudio
- **WAV File Export**: Save recordings as standard WAV files
- **Database Integration**: Store recordings with metadata in SQLite
- **Spectral Analysis**: Automatic FFT analysis and storage
- **Noise Level Calculation**: Calculate dB levels for each recording
- **Frequent Pattern Analysis**: Identify and analyze common noise patterns
- **Interactive Mode**: User-friendly command-line interface
- **Batch Processing**: Support for multiple recordings

## Installation

### Prerequisites

```bash
# Install system dependencies (Linux/Ubuntu)
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio

# Install Python dependencies
pip install -r requirements.txt
```

### Requirements

```
numpy>=1.21.0
matplotlib>=3.4.0
pyaudio>=0.2.11
wave
```

## Usage

### 1. Quick Recording (5 seconds)

```bash
python audio_capture.py quick
```

### 2. Quick Recording with Custom Duration

```bash
python audio_capture.py quick 10  # Record for 10 seconds
```

### 3. Interactive Mode

```bash
python audio_capture.py interactive
```

This launches an interactive menu where you can:
- Record multiple noise samples
- View recording statistics
- Configure recording parameters

### 4. Programmatic Usage

```python
from audio_capture import AudioCapture, record_noise_sample

# Quick recording with default settings
recording_id = record_noise_sample(
    duration=5,
    environment="office",
    location="Desk Area",
    description="Keyboard typing noise"
)

# Or use the class for more control
capture = AudioCapture(db_path="anc_system.db", output_dir="recordings")

# Start recording
capture.start_recording(duration_seconds=10)

# Save to database
recording_id = capture.save_to_database(
    environment_type="office",
    location="Meeting Room",
    description="Conference call background noise",
    save_wav=True
)

# Cleanup
capture.cleanup()
```

## File Structure

```
anc-with-ai/
├── audio_capture.py              # Main audio capture module
├── frequent_noise_manager.py     # Noise pattern analysis
├── database_schema.py            # Database ORM
├── recordings/                   # WAV files directory (auto-created)
│   └── recording_YYYYMMDD_HHMMSS.wav
└── anc_system.db                # SQLite database
```

## Audio Capture Module

### AudioCapture Class

Main class for capturing and managing audio recordings.

#### Configuration

```python
AudioCapture(
    db_path="anc_system.db",    # Database file path
    output_dir="recordings"      # WAV output directory
)
```

#### Audio Settings

- **Format**: 16-bit PCM (pyaudio.paInt16)
- **Channels**: 1 (Mono)
- **Sample Rate**: 44100 Hz
- **Chunk Size**: 1024 frames

#### Key Methods

##### start_recording()
```python
capture.start_recording(
    duration_seconds=5,     # Recording duration (None for continuous)
    device_index=None       # Audio device index (None for default)
)
```

##### save_wav()
```python
filepath = capture.save_wav(
    filename="my_recording.wav"  # Optional custom filename
)
```

##### save_to_database()
```python
recording_id = capture.save_to_database(
    environment_type="office",    # Environment classification
    location="Building A",        # Physical location
    description="HVAC noise",     # Description
    save_wav=True,               # Save WAV file
    wav_filename=None            # Custom WAV filename
)
```

##### get_audio_array()
```python
# Get recorded audio as numpy array
audio_data = capture.get_audio_array()
# Returns: np.ndarray with float values in range [-1, 1]
```

### Example: Recording Multiple Samples

```python
from audio_capture import AudioCapture

capture = AudioCapture()

environments = ["office", "street", "home", "park"]

for env in environments:
    print(f"\nRecording {env} noise...")

    # Record 5 seconds
    capture.start_recording(duration_seconds=5)

    # Save to database
    recording_id = capture.save_to_database(
        environment_type=env,
        location=f"{env.capitalize()} Location",
        description=f"Ambient {env} noise sample",
        save_wav=True
    )

    print(f"✓ Saved as Recording ID: {recording_id}")

capture.cleanup()
```

## Frequent Noise Manager

Analyzes and manages common noise patterns from database.

### Command-Line Usage

#### 1. Display Comprehensive Report

```bash
python frequent_noise_manager.py report
```

Output:
```
===============================================================================
FREQUENT NOISE PATTERNS REPORT
===============================================================================

Overall Statistics:
  Total Recordings: 15
  Average Noise Level: -12.45 dB
  Noise Level Range: -25.30 to 5.20 dB
  Average Duration: 5.00 seconds
  Total Recording Time: 75.00 seconds

────────────────────────────────────────────────────────────────────────────────
Frequent Environments:
────────────────────────────────────────────────────────────────────────────────
  office                7 recordings ( 46.7%)
    Average Noise Level: -15.20 dB (±3.45)
  street                5 recordings ( 33.3%)
    Average Noise Level: -8.10 dB (±2.80)
```

#### 2. Export to JSON

```bash
python frequent_noise_manager.py export [output_file.json]
```

Creates JSON file with:
- Overall statistics
- Frequent patterns (environments, locations, noise levels)
- Environment-specific profiles

#### 3. Create Environment Profile

```bash
python frequent_noise_manager.py profile office
```

Output:
```
Noise Profile for 'office':
  Sample Count: 7
  Average Duration: 5.00s
  Average Noise Level: -15.20 dB
  Std Dev: 3.45 dB
  Range: -20.50 to -10.30 dB
```

#### 4. Find Similar Recordings

```bash
python frequent_noise_manager.py similar 5
```

Finds recordings similar to Recording ID 5 based on noise level and environment.

### Programmatic Usage

```python
from frequent_noise_manager import FrequentNoiseManager

manager = FrequentNoiseManager()

# Get statistics
stats = manager.get_noise_statistics()
print(f"Total recordings: {stats['total_recordings']}")

# Identify frequent patterns
patterns = manager.identify_frequent_patterns(min_occurrences=3)
print(f"Frequent environments: {patterns['environments']}")

# Create environment profile
profile = manager.create_noise_profile("office")
print(f"Office avg noise: {profile['avg_noise_level_db']} dB")

# Find similar recordings
similar = manager.get_similar_noise_recordings(recording_id=5, tolerance=5.0)
for rec in similar:
    print(f"Recording {rec['recording_id']}: {rec['similarity_score']}% similar")

# Export to JSON
manager.export_frequent_definitions("my_noise_patterns.json")

manager.close()
```

## Database Schema

Recordings are stored with comprehensive metadata:

### noise_recordings Table
- `recording_id`: Primary key
- `timestamp`: Recording timestamp
- `duration_seconds`: Duration
- `sampling_rate`: Sample rate (Hz)
- `num_samples`: Total samples
- `environment_type`: Environment classification
- `noise_level_db`: Measured dB level
- `location`: Physical location
- `description`: User description
- `metadata_json`: Additional metadata

### audio_waveforms Table
- `waveform_id`: Primary key
- `recording_id`: Foreign key
- `waveform_type`: ambient_noise, clean_signal, etc.
- `waveform_data`: Binary numpy array (BLOB)
- `num_samples`: Sample count
- `min/max/mean/std_amplitude`: Pre-calculated statistics

### spectral_analysis Table
- `analysis_id`: Primary key
- `recording_id`: Foreign key
- `frequency_data`: FFT frequency bins (BLOB)
- `magnitude_data`: FFT magnitudes (BLOB)
- `phase_data`: FFT phase data (BLOB)
- `fft_size`: FFT size used
- `window_function`: Window function applied

## Noise Level Categories

| Range | Category | Description |
|-------|----------|-------------|
| < -40 dB | Very Quiet | Near silence, ambient room noise |
| -40 to -20 dB | Quiet | Library, quiet office |
| -20 to 0 dB | Moderate | Normal conversation, light traffic |
| 0 to 20 dB | Loud | Busy office, busy street |
| > 20 dB | Very Loud | Heavy traffic, construction |

## Tips and Best Practices

### 1. Recording Quality
- Use a quality microphone
- Minimize microphone handling noise
- Keep consistent distance from noise source
- Record in stable acoustic environment

### 2. Noise Classification
- Be consistent with environment types
- Use descriptive names (e.g., "office_hvac" instead of just "noise")
- Include location details for spatial analysis
- Add detailed descriptions for later reference

### 3. Batch Recording
- Record multiple samples of same environment for better profiles
- Vary recording times (morning, afternoon, evening)
- Include different noise sources in same environment

### 4. Analysis
- Collect at least 5-10 samples per environment for reliable patterns
- Review frequent pattern reports regularly
- Export profiles for archival and comparison

## Troubleshooting

### PyAudio Installation Issues

**Linux:**
```bash
sudo apt-get install portaudio19-dev
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

### No Audio Device Found

```python
# List available devices
from audio_capture import AudioCapture
capture = AudioCapture()
# Devices are listed on initialization
```

### Permission Denied

On Linux, you may need to add user to audio group:
```bash
sudo usermod -a -G audio $USER
```

### Recording Too Quiet/Loud

Adjust your system's microphone gain settings before recording.

## Integration with ANC System

The audio capture system integrates seamlessly with the ANC processing pipeline:

```python
from audio_capture import AudioCapture
from anc_with_database import OpenAirNoiseCancellationDB

# Step 1: Capture ambient noise
capture = AudioCapture()
capture.start_recording(duration_seconds=5)
recording_id = capture.save_to_database(
    environment_type="test_environment",
    description="Ambient noise for ANC"
)
ambient_noise = capture.get_audio_array()
capture.cleanup()

# Step 2: Use in ANC system
anc = OpenAirNoiseCancellationDB()
anc.update_reference_noise(ambient_noise, save_to_db=True)

# Step 3: Process and cancel noise
# ... (continue with your signal processing)
```

## Example Workflows

### Workflow 1: Building Noise Library

```python
from audio_capture import AudioCapture

environments = {
    "office": ["Desk area", "Meeting room", "Hallway"],
    "home": ["Living room", "Kitchen", "Bedroom"],
    "outdoor": ["Park", "Street", "Parking lot"]
}

capture = AudioCapture()

for env_type, locations in environments.items():
    for location in locations:
        print(f"\nRecording: {env_type} - {location}")
        print("Press Enter when ready to start recording...")
        input()

        capture.start_recording(duration_seconds=10)
        capture.save_to_database(
            environment_type=env_type,
            location=location,
            description=f"Ambient noise in {location}"
        )

capture.cleanup()
```

### Workflow 2: Analyzing Patterns

```python
from frequent_noise_manager import FrequentNoiseManager

# Analyze and export
manager = FrequentNoiseManager()
manager.print_report()
manager.export_frequent_definitions("noise_library.json")

# Create profiles for each environment
for env in ["office", "home", "outdoor"]:
    profile = manager.create_noise_profile(env)
    if profile:
        print(f"\n{env.upper()} Profile:")
        print(f"  Recordings: {profile['sample_count']}")
        print(f"  Avg Noise: {profile['avg_noise_level_db']:.2f} dB")

manager.close()
```

## API Reference

See inline documentation in:
- `audio_capture.py` - AudioCapture class
- `frequent_noise_manager.py` - FrequentNoiseManager class
- `database_schema.py` - ANCDatabase class

## Contributing

When adding new features:
1. Update database schema if needed
2. Add corresponding methods to ANCDatabase class
3. Update this documentation
4. Add tests for new functionality

## License

Part of the ANC system patent implementation.
