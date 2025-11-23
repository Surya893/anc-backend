# ANC System Database Schema Documentation

## Overview

This document describes the SQLite database schema for the Active Noise Cancellation (ANC) system. The database stores noise recordings, sound wave data, and AI model artifacts as specified in the patent documentation.

## Database Architecture

The database consists of 9 interconnected tables designed to capture all aspects of the noise cancellation process:

### Entity Relationship Diagram

```
noise_recordings (1) ──< (N) audio_waveforms
                 (1) ──< (N) audio_samples
                 (1) ──< (N) spectral_analysis
                 (1) ──< (N) model_coefficients
                 (1) ──< (N) processing_sessions

model_versions (1) ──< (N) model_coefficients
               (1) ──< (N) processing_sessions
               (1) ──< (N) training_history

processing_sessions (1) ──< (N) performance_metrics
```

## Table Schemas

### 1. noise_recordings
Stores metadata about each noise recording session.

| Column | Type | Description |
|--------|------|-------------|
| recording_id | INTEGER PRIMARY KEY | Unique recording identifier |
| timestamp | DATETIME | Recording timestamp |
| duration_seconds | REAL | Total recording duration |
| sampling_rate | INTEGER | Sample rate (e.g., 44100 Hz) |
| num_samples | INTEGER | Total number of samples |
| environment_type | TEXT | Environment classification (office, lab, outdoor, etc.) |
| noise_level_db | REAL | Measured noise level in decibels |
| location | TEXT | Physical location of recording |
| device_id | TEXT | Recording device identifier |
| description | TEXT | User-provided description |
| metadata_json | TEXT | Additional metadata in JSON format |
| created_at | DATETIME | Record creation timestamp |

### 2. audio_samples
Stores individual audio data points (for detailed analysis).

| Column | Type | Description |
|--------|------|-------------|
| sample_id | INTEGER PRIMARY KEY | Unique sample identifier |
| recording_id | INTEGER FK | Reference to noise_recordings |
| sample_type | TEXT | Type: ambient_noise, clean_signal, noise_cancelled, error_signal, reference_noise |
| sample_index | INTEGER | Sample position in time series |
| amplitude | REAL | Sample amplitude value |
| timestamp_offset | REAL | Time offset from recording start |
| created_at | DATETIME | Record creation timestamp |

**Indexes:**
- `idx_audio_samples_recording` on (recording_id, sample_type, sample_index)

### 3. audio_waveforms
Stores complete waveforms as compressed binary data (more efficient than individual samples).

| Column | Type | Description |
|--------|------|-------------|
| waveform_id | INTEGER PRIMARY KEY | Unique waveform identifier |
| recording_id | INTEGER FK | Reference to noise_recordings |
| waveform_type | TEXT | Type: ambient_noise, clean_signal, noise_cancelled, error_signal, reference_noise |
| waveform_data | BLOB | Binary numpy array data |
| num_samples | INTEGER | Number of samples in waveform |
| min_amplitude | REAL | Minimum amplitude value |
| max_amplitude | REAL | Maximum amplitude value |
| mean_amplitude | REAL | Mean amplitude |
| std_amplitude | REAL | Standard deviation of amplitude |
| created_at | DATETIME | Record creation timestamp |

### 4. model_versions
Tracks different versions of the AI model/algorithm.

| Column | Type | Description |
|--------|------|-------------|
| model_id | INTEGER PRIMARY KEY | Unique model identifier |
| version_name | TEXT UNIQUE | Human-readable version name |
| version_number | TEXT | Semantic version number (e.g., "1.0.0") |
| filter_length | INTEGER | Adaptive filter length |
| adaptation_rate | REAL | Learning rate (mu parameter) |
| algorithm_type | TEXT | Algorithm type (LMS, NLMS, RLS, etc.) |
| description | TEXT | Model description |
| is_active | BOOLEAN | Whether this is the active model |
| created_at | DATETIME | Record creation timestamp |
| updated_at | DATETIME | Last update timestamp |

### 5. model_coefficients
Stores adaptive filter coefficients over time.

| Column | Type | Description |
|--------|------|-------------|
| coefficient_id | INTEGER PRIMARY KEY | Unique coefficient set identifier |
| model_id | INTEGER FK | Reference to model_versions |
| recording_id | INTEGER FK | Reference to noise_recordings (nullable) |
| coefficient_data | BLOB | Binary numpy array of coefficients |
| coefficient_length | INTEGER | Number of coefficients |
| iteration_number | INTEGER | Training iteration number |
| convergence_score | REAL | Convergence metric (0-1) |
| timestamp | DATETIME | Record creation timestamp |

### 6. processing_sessions
Tracks noise cancellation processing sessions.

| Column | Type | Description |
|--------|------|-------------|
| session_id | INTEGER PRIMARY KEY | Unique session identifier |
| model_id | INTEGER FK | Reference to model_versions |
| recording_id | INTEGER FK | Reference to noise_recordings |
| start_time | DATETIME | Session start time |
| end_time | DATETIME | Session end time |
| processing_duration_ms | REAL | Total processing time in milliseconds |
| iterations_count | INTEGER | Number of iterations performed |
| final_error | REAL | Final error value |
| convergence_achieved | BOOLEAN | Whether convergence was achieved |
| configuration_json | TEXT | Session configuration in JSON format |

### 7. performance_metrics
Stores performance measurements for each session.

| Column | Type | Description |
|--------|------|-------------|
| metric_id | INTEGER PRIMARY KEY | Unique metric identifier |
| session_id | INTEGER FK | Reference to processing_sessions |
| metric_type | TEXT | Type: snr_improvement, noise_reduction_db, convergence_rate, mse, rmse, processing_latency, custom |
| metric_value | REAL | Metric value |
| metric_unit | TEXT | Unit of measurement |
| timestamp | DATETIME | Record creation timestamp |
| notes | TEXT | Additional notes |

### 8. training_history
Records training iteration history for model convergence analysis.

| Column | Type | Description |
|--------|------|-------------|
| history_id | INTEGER PRIMARY KEY | Unique history entry identifier |
| model_id | INTEGER FK | Reference to model_versions |
| epoch_number | INTEGER | Training epoch number |
| iteration_number | INTEGER | Iteration within epoch |
| loss_value | REAL | Loss function value |
| error_value | REAL | Error metric value |
| learning_rate | REAL | Learning rate used |
| coefficient_snapshot | BLOB | Binary snapshot of coefficients at this iteration |
| timestamp | DATETIME | Record creation timestamp |

### 9. spectral_analysis
Stores FFT and frequency domain analysis results.

| Column | Type | Description |
|--------|------|-------------|
| analysis_id | INTEGER PRIMARY KEY | Unique analysis identifier |
| recording_id | INTEGER FK | Reference to noise_recordings |
| waveform_type | TEXT | Type of waveform analyzed |
| frequency_data | BLOB | Binary frequency array |
| magnitude_data | BLOB | Binary magnitude array |
| phase_data | BLOB | Binary phase array (nullable) |
| fft_size | INTEGER | FFT size used |
| window_function | TEXT | Window function applied (e.g., Hamming, Hann) |
| timestamp | DATETIME | Record creation timestamp |

## Usage Examples

### 1. Initialize Database

```python
from database_schema import ANCDatabase

# Create database connection
db = ANCDatabase("anc_system.db")
```

### 2. Create a Recording

```python
recording_id = db.insert_noise_recording(
    duration_seconds=1.0,
    sampling_rate=44100,
    num_samples=44100,
    environment_type="office",
    noise_level_db=65.5,
    location="Lab Room A",
    description="Morning ambient noise recording"
)
```

### 3. Store Waveform Data

```python
import numpy as np

# Generate or capture waveform
ambient_noise = np.random.randn(1000)

# Store in database
waveform_id = db.insert_waveform(
    recording_id=recording_id,
    waveform_type="ambient_noise",
    waveform_array=ambient_noise
)

# Retrieve waveform
retrieved_waveform = db.get_waveform(waveform_id)
```

### 4. Register Model Version

```python
model_id = db.insert_model_version(
    version_name="LMS_v1.0",
    version_number="1.0.0",
    filter_length=1024,
    adaptation_rate=0.01,
    algorithm_type="LMS",
    description="Adaptive LMS filter",
    is_active=True
)
```

### 5. Store Filter Coefficients

```python
coefficients = np.random.randn(1024)

coeff_id = db.insert_model_coefficients(
    model_id=model_id,
    coefficients=coefficients,
    recording_id=recording_id,
    iteration_number=100,
    convergence_score=0.95
)
```

### 6. Track Processing Session

```python
# Start session
session_id = db.insert_processing_session(
    model_id=model_id,
    recording_id=recording_id,
    configuration={"algorithm": "LMS", "mu": 0.01}
)

# ... perform processing ...

# End session
db.update_processing_session(
    session_id=session_id,
    processing_duration_ms=150.5,
    final_error=0.002,
    convergence_achieved=True
)
```

### 7. Store Performance Metrics

```python
db.insert_performance_metric(
    session_id=session_id,
    metric_type="snr_improvement",
    metric_value=12.5,
    metric_unit="dB",
    notes="Significant improvement in SNR"
)
```

## Integration with ANC System

See `anc_with_database.py` for a complete integration example that combines the OpenAirNoiseCancellation algorithm with database persistence.

### Key Features:
- Automatic recording session management
- Real-time waveform storage
- Coefficient versioning and tracking
- Performance metric collection
- Training history logging

### Usage:

```python
from anc_with_database import OpenAirNoiseCancellationDB

# Initialize with database persistence
anc = OpenAirNoiseCancellationDB(
    sampling_rate=44100,
    filter_length=1024,
    db_path="anc_system.db"
)

# Start recording
anc.start_recording(
    duration_seconds=1.0,
    environment_type="laboratory"
)

# Process audio
noise_cancelled, proc_time = anc.cancel_noise(input_signal)

# Metrics are automatically saved
anc.save_performance_metrics(
    snr_improvement=10.5,
    noise_reduction_db=8.2
)
```

## Data Access Queries

### Get All Recordings

```python
recordings = db.get_all_recordings()
for rec in recordings:
    print(f"Recording {rec[0]}: {rec[1]}, {rec[2]}s, {rec[3]} Hz")
```

### Get Active Model

```python
active_model = db.get_active_model()
if active_model:
    model_id, name, version, filter_len, mu, algo = active_model
    print(f"Active Model: {name} v{version}")
```

### Get Session Metrics

```python
metrics = db.get_session_metrics(session_id)
for metric in metrics:
    metric_type, value, unit, timestamp = metric
    print(f"{metric_type}: {value} {unit}")
```

## File Structure

```
anc-with-ai/
├── database_schema.py       # Database schema and ORM
├── anc_with_database.py     # Integration example
├── anc-with-air-code        # Original ANC algorithm
├── requirements.txt         # Python dependencies
├── DATABASE_SCHEMA.md       # This documentation
└── anc_system.db           # SQLite database (created at runtime)
```

## Requirements

```
numpy>=1.21.0
matplotlib>=3.4.0
```

Install with:
```bash
pip install -r requirements.txt
```

## Testing

Run the database schema test:
```bash
python database_schema.py
```

Run the full integration example:
```bash
python anc_with_database.py
```

## Best Practices

1. **Use Context Managers**: Always use `with` statements or call `close()` to ensure proper database cleanup.

2. **Batch Operations**: For large datasets, consider batching inserts within transactions for better performance.

3. **Data Types**: Store numpy arrays as BLOB for efficiency. Use `tobytes()` to serialize and `frombuffer()` to deserialize.

4. **Indexing**: The schema includes indexes on frequently queried columns. Add additional indexes as needed for your queries.

5. **Version Control**: Use the `model_versions` table to track algorithm changes over time.

6. **Metadata**: Store additional information in JSON fields for flexibility without schema changes.

## Performance Considerations

- **Waveform Storage**: Use `audio_waveforms` table for complete waveforms (more efficient) and `audio_samples` table only when you need sample-level granularity.
- **Binary Data**: NumPy arrays are stored as BLOB data for space efficiency.
- **Indexes**: Indexes are created on foreign keys and frequently queried columns.
- **Statistics**: Waveform statistics (min, max, mean, std) are pre-calculated and stored for quick access.

## License

This database schema is designed for the ANC system patent implementation.
