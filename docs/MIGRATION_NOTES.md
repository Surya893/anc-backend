# Repository Reorganization - Migration Notes

## Overview

The repository has been reorganized from a flat structure (107 files in root) to a clean, modular structure. This document explains the changes and how to migrate.

## What Changed

### Directory Structure

**Before:**
```
anc-with-ai/
├── 107 files in root (messy!)
```

**After:**
```
anc-with-ai/
├── src/                    # Production source code
│   ├── core/              # ANC algorithms
│   ├── api/               # API servers
│   ├── ml/                # Machine learning
│   ├── database/          # Database models
│   ├── web/               # Web application
│   └── utils/             # Utilities
├── docs/                   # Documentation
├── tests/                  # Tests and demos
│   ├── unit/
│   ├── integration/
│   └── demos/
├── scripts/                # Utility scripts
│   ├── training/
│   ├── database/
│   ├── diagnostics/
│   └── analysis/
├── config/                 # Configuration
├── models/                 # ML models
├── data/                   # Data files
├── benchmarks/            # Performance benchmarks
├── cloud/                 # Cloud infrastructure
└── tools/                 # Hardware tools
```

## File Migrations

### Source Code (src/)

| Old Location | New Location |
|-------------|--------------|
| `advanced_anc_algorithms.py` | `src/core/advanced_anc_algorithms.py` |
| `anti_noise_generator.py` | `src/core/anti_noise_generator.py` |
| `audio_processor.py` | `src/core/audio_processor.py` |
| `realtime_audio_engine.py` | `src/core/realtime_audio_engine.py` |
| `server.py` | `src/api/server.py` |
| `api_server.py` | `src/api/api_server.py` |
| `websocket_server.py` | `src/api/websocket_server.py` |
| `websocket_streaming.py` | `src/api/websocket_streaming.py` |
| `tasks.py` | `src/api/tasks.py` |
| `feature_extraction.py` | `src/ml/feature_extraction.py` |
| `noise_classifier_model.py` | `src/ml/noise_classifier_model.py` |
| `emergency_noise_detector.py` | `src/ml/emergency_noise_detector.py` |
| `frequent_noise_manager.py` | `src/ml/frequent_noise_manager.py` |
| `predict_noise_type.py` | `src/ml/predict_noise_type.py` |
| `predict_sklearn.py` | `src/ml/predict_sklearn.py` |
| `models.py` | `src/database/models.py` |
| `database_schema.py` | `src/database/schema.py` |
| `app.py` | `src/web/app.py` |
| `main.py` | `src/web/main.py` |
| `audio_capture.py` | `src/utils/audio_capture.py` |
| `config.py` | `config/config.py` |

### Tests & Demos (tests/)

| Old Location | New Location |
|-------------|--------------|
| `test_*.py` | `tests/unit/test_*.py` |
| `verify_*.py` | `tests/integration/verify_*.py` |
| `*_demo.py`, `*_test.py` | `tests/demos/*` |

### Scripts (scripts/)

| Old Location | New Location |
|-------------|--------------|
| `train_*.py` | `scripts/training/` |
| `collect_training_data.py` | `scripts/training/` |
| `generate_synthetic_data.py` | `scripts/training/` |
| `inspect_database.py` | `scripts/database/` |
| `query_*.py` | `scripts/database/` |
| `list_tables.py` | `scripts/database/` |
| `diagnostic_check.py` | `scripts/diagnostics/` |
| `check_audio_devices.py` | `scripts/diagnostics/` |
| `setup_and_verify.py` | `scripts/diagnostics/` |
| `intensity_analysis.py` | `scripts/analysis/` |
| `librosa_intensity_analysis.py` | `scripts/analysis/` |

### Documentation (docs/)

All `.md` documentation files moved to appropriate subdirectories in `docs/`:
- Architecture docs → `docs/architecture/`
- Guides → `docs/guides/`
- Deployment docs → `docs/deployment/`
- Verification docs → `docs/verification/`

### Models & Data

| Old Location | New Location |
|-------------|--------------|
| `*.pkl` (model files) | `models/` |
| `anc_results.png` | `data/results/` |

## Running the Application

### Python Path Configuration

The `wsgi.py` entry point has been updated to automatically configure Python paths. For other entry points, you may need to:

**Option 1: Run from repository root**
```bash
cd /path/to/anc-with-ai
export PYTHONPATH="${PYTHONPATH}:${PWD}/src/api:${PWD}/src/core:${PWD}/src/ml:${PWD}/src/database:${PWD}/src/utils:${PWD}/src/web:${PWD}/config"
python src/web/main.py
```

**Option 2: Use the updated entry points**
```bash
python wsgi.py  # Paths are auto-configured
```

### Shell Scripts

Shell scripts in root (`*.sh`) may reference old file locations. You can either:

1. Run scripts that reference full paths (e.g., `python src/api/server.py`)
2. Update the scripts to use new locations

**Example update:**
```bash
# Old
python server.py

# New
python src/api/server.py
```

### Docker

Dockerfile and docker-compose.yml should work without changes, but verify PYTHONPATH is set correctly in the container.

## Import Statements

### For New Code

Use absolute imports from the new locations:

```python
# Core algorithms
from src.core.advanced_anc_algorithms import NLMSFilter

# API
from src.api.server import app

# ML
from src.ml.noise_classifier_model import NoiseClassifier

# Database
from src.database.models import db, User, AudioSession

# Utils
from src.utils.audio_capture import AudioCapture

# Config
from config.config import get_config
```

### For Existing Code

Existing code files may still use old import paths (e.g., `import models`). These will work if PYTHONPATH is configured correctly via `wsgi.py` or environment variables.

## Testing

After reorganization:

```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# Demos
cd tests/demos
python simple_anti_noise_demo.py
```

## Gradual Migration Strategy

You don't need to update everything at once:

1. **Entry Points**: Already updated (`wsgi.py`)
2. **New Code**: Use new import paths
3. **Existing Code**: Works with PYTHONPATH configuration
4. **Gradual Update**: Update imports in files as you modify them

## Benefits

- **Clean Root**: Only 12 essential files in root (vs 107 before)
- **Clear Organization**: Easy to find files by function
- **Scalability**: Easier to add new features
- **Professional**: Standard Python project structure
- **Better IDE Support**: IDEs can better understand project structure

## Rollback

If you need to rollback, use git:

```bash
git log --oneline  # Find commit before reorganization
git checkout <commit-hash>
```

## Questions?

See:
- [Cleanup Plan](CLEANUP_PLAN.md) - Detailed reorganization plan
- [Repository Cleanup Summary](REPOSITORY_CLEANUP_SUMMARY.md) - Summary of cleanup
- [Main README](../README.md) - Updated project documentation

---

**Migration Date:** 2025-11-16
**Status:** ✅ Complete
