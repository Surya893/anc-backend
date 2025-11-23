# Scripts Directory

Utility scripts for the ANC Platform organized by function.

## Directory Structure

```
scripts/
├── quick_start.sh              # Quick start script
├── start.sh                    # Start the ANC platform
├── stop.sh                     # Stop the ANC platform
├── monitoring/                 # Monitoring scripts
│   └── monitor_anc.sh         # Monitor ANC system performance
├── testing/                    # Testing scripts
│   └── run_local_test.sh      # Run local integration tests
├── training/                   # ML training scripts
│   ├── train_classifier.py
│   ├── train_sklearn_demo.py
│   ├── collect_training_data.py
│   ├── generate_synthetic_data.py
│   └── finetune_emergency_classifier.py
├── database/                   # Database utilities
│   ├── inspect_database.py
│   ├── list_tables.py
│   ├── query_latest_recording.py
│   └── query_sample_data.py
├── diagnostics/                # Diagnostic tools
│   ├── diagnostic_check.py
│   ├── check_audio_devices.py
│   ├── setup_and_verify.py
│   └── run_librosa_comparison.py
└── analysis/                   # Analysis scripts
    ├── intensity_analysis.py
    └── librosa_intensity_analysis.py
```

---

## Quick Start Scripts

### `quick_start.sh`

**Purpose:** Rapidly set up and start the ANC platform for first-time users.

**Usage:**
```bash
./scripts/quick_start.sh
```

**What it does:**
- Checks system dependencies
- Installs required packages
- Configures database
- Starts the platform

**Prerequisites:**
- Python 3.9+
- Audio devices available
- Sufficient disk space

---

### `start.sh`

**Purpose:** Start the ANC platform services.

**Usage:**
```bash
./scripts/start.sh
```

**Services started:**
- Flask API server
- WebSocket server
- Celery workers
- Database connections

**Environment:**
- Reads from `.env` file
- Uses production configuration by default

---

### `stop.sh`

**Purpose:** Gracefully stop all ANC platform services.

**Usage:**
```bash
./scripts/stop.sh
```

**What it stops:**
- Flask server processes
- WebSocket connections
- Celery workers
- Background tasks

---

## Monitoring Scripts

### `monitoring/monitor_anc.sh`

**Purpose:** Real-time monitoring of ANC system performance.

**Usage:**
```bash
./scripts/monitoring/monitor_anc.sh
```

**Metrics monitored:**
- Audio processing latency
- Noise cancellation effectiveness
- System resource usage (CPU, memory)
- Active connections
- Error rates

**Output:**
- Console output with real-time metrics
- Optional log file

---

## Testing Scripts

### `testing/run_local_test.sh`

**Purpose:** Comprehensive local integration testing.

**Usage:**
```bash
./scripts/testing/run_local_test.sh
```

**Tests included:**
- Audio capture and playback
- NLMS filter processing
- API endpoints
- WebSocket connections
- Database operations
- ML classifier predictions

**Reports:**
- Test results printed to console
- Coverage report generated
- Failure logs if issues found

---

## Training Scripts

Located in `training/` subdirectory.

### `train_classifier.py`

Train the noise classifier model.

```bash
python scripts/training/train_classifier.py --data data/ --epochs 50
```

### `collect_training_data.py`

Collect audio samples for training.

```bash
python scripts/training/collect_training_data.py --duration 300 --output data/training/
```

### `generate_synthetic_data.py`

Generate synthetic noise data for augmentation.

```bash
python scripts/training/generate_synthetic_data.py --count 1000 --output data/synthetic/
```

See [Training Documentation](../docs/TRAINING_RESULTS.md) for details.

---

## Database Scripts

Located in `database/` subdirectory.

### `inspect_database.py`

Inspect database contents and schema.

```bash
python scripts/database/inspect_database.py
```

### `query_latest_recording.py`

Query the most recent audio recordings.

```bash
python scripts/database/query_latest_recording.py --limit 10
```

See [Database Documentation](../docs/architecture/DATABASE_SCHEMA.md) for schema details.

---

## Diagnostic Scripts

Located in `diagnostics/` subdirectory.

### `diagnostic_check.py`

Comprehensive system diagnostics.

```bash
python scripts/diagnostics/diagnostic_check.py
```

**Checks:**
- Audio device availability
- Python dependencies
- Database connectivity
- API endpoints
- ML model files

### `check_audio_devices.py`

List and test available audio devices.

```bash
python scripts/diagnostics/check_audio_devices.py
```

---

## Analysis Scripts

Located in `analysis/` subdirectory.

### `intensity_analysis.py`

Analyze audio signal intensity.

```bash
python scripts/analysis/intensity_analysis.py --input audio.wav
```

### `librosa_intensity_analysis.py`

Advanced audio analysis using librosa.

```bash
python scripts/analysis/librosa_intensity_analysis.py --input audio.wav --plot
```

---

## Script Conventions

### Naming
- Shell scripts: `lowercase_with_underscores.sh`
- Python scripts: `lowercase_with_underscores.py`
- Directories: `lowercase` (no underscores unless necessary)

### Location
- Top-level scripts (`start.sh`, `stop.sh`): Common operations
- Subdirectories: Specialized scripts grouped by function

### Execution
- All shell scripts are executable (`chmod +x`)
- Python scripts executed via `python script_name.py`

### Environment
- Scripts read from `.env` file in project root
- Use environment variables for configuration
- Default to safe/production settings

---

## Adding New Scripts

When adding new scripts:

1. **Choose the right directory:**
   - Monitoring → `monitoring/`
   - Testing → `testing/`
   - ML Training → `training/`
   - Database → `database/`
   - Diagnostics → `diagnostics/`
   - Analysis → `analysis/`

2. **Follow conventions:**
   - Use descriptive names
   - Add usage documentation
   - Include error handling
   - Make executable if shell script

3. **Update this README:**
   - Add script to appropriate section
   - Document usage and purpose
   - Include example commands

---

## Quick Reference

| Task | Script | Location |
|------|--------|----------|
| Start platform | `start.sh` | `scripts/` |
| Stop platform | `stop.sh` | `scripts/` |
| Quick setup | `quick_start.sh` | `scripts/` |
| Monitor performance | `monitor_anc.sh` | `scripts/monitoring/` |
| Run tests | `run_local_test.sh` | `scripts/testing/` |
| Train ML model | `train_classifier.py` | `scripts/training/` |
| Check audio devices | `check_audio_devices.py` | `scripts/diagnostics/` |
| System diagnostics | `diagnostic_check.py` | `scripts/diagnostics/` |
| Inspect database | `inspect_database.py` | `scripts/database/` |
| Analyze audio | `intensity_analysis.py` | `scripts/analysis/` |

---

## See Also

- [Main README](../README.md) - Project overview
- [Documentation Index](../docs/README.md) - Complete documentation
- [Quick Start Guide](../docs/guides/QUICK_START_GUIDE.md) - Getting started
- [Deployment Guide](../docs/guides/DEPLOYMENT_GUIDE.md) - Production deployment

---

**Last Updated:** 2025-11-16
