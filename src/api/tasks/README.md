# Celery Tasks Module

This package contains all background job definitions for the ANC Platform. Tasks are organized by domain for maintainability and testability.

## Structure

```
tasks/
├── __init__.py            # Task exports and periodic task configuration
├── utils.py               # Shared utilities (logging, DB, validation)
├── audio_processing.py    # Audio file processing tasks
├── model_training.py      # ML model training tasks
├── analytics.py           # Session analysis and reporting tasks
└── maintenance.py         # Database and system maintenance tasks
```

## Task Categories

### Audio Processing (`audio_processing.py`)
- **process_audio_file**: Process a single audio file with chunk-based streaming
  - Validates file exists before processing
  - Chunks audio to avoid blocking long computations
  - Tracks progress with metadata
  - Returns comprehensive statistics

- **batch_process_files**: Batch process multiple audio files
  - Processes files sequentially with progress tracking
  - Records failures without stopping the batch
  - Returns mixed success/failure report

### Model Training (`model_training.py`)
- **train_noise_classifier**: Train RandomForest classifier on audio categories
  - Organizes training data by category directories
  - Extracts audio features using AudioFeatureExtractor
  - Evaluates on test set before saving
  - Returns accuracy metrics and model paths

- **validate_model**: Verify trained models are loadable
  - Checks model and scaler files exist
  - Attempts to load models to validate integrity
  - Returns model metadata

### Analytics (`analytics.py`)
- **analyze_session_data**: Comprehensive analysis of recorded session
  - Analyzes noise detections by type
  - Aggregates performance metrics
  - Returns noise distribution and performance stats

- **generate_daily_report**: Daily usage and performance summary
  - Queries sessions, detections, and API metrics for period
  - Calculates aggregate statistics
  - Emergency event counting
  - Noise type distribution

- **export_session_data**: Export session data in various formats
  - Supports JSON and CSV formats
  - Uses analyze_session_data for data collection
  - Returns export result with timestamp

### Maintenance (`maintenance.py`)
- **cleanup_old_sessions**: Remove old session records
  - Deletes sessions older than N days
  - Cascades to related NoiseDetection and ProcessingMetric records
  - Handles deletion errors gracefully

- **cleanup_failed_sessions**: Remove incomplete/failed sessions
  - Deletes sessions marked as 'failed' or 'error'
  - Older than specified hours (default: 24 hours)
  - Safe transaction handling

- **vacuum_database**: Database optimization
  - Runs SQLite VACUUM to reclaim space
  - Optimizes table layout
  - Should run periodically (weekly)

- **health_check**: System health monitoring
  - Verifies database connectivity
  - Counts active sessions
  - Returns component health status

## Usage

### Direct Task Invocation

```python
from api.tasks import process_audio_file

# Call task synchronously (dev/test mode)
result = process_audio_file(
    file_path='/path/to/audio.wav',
    session_id='session_123',
    apply_anc=True
)

# Or via Celery delay (async)
result = process_audio_file.delay(
    file_path='/path/to/audio.wav',
    session_id='session_123',
    apply_anc=True
)
```

### Running Worker

```bash
# Development (eager mode - synchronous)
celery -A src.api.tasks worker --loglevel=debug

# Production (async with multiple workers)
celery -A src.api.tasks worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100

# With periodic task scheduler
celery -A src.api.tasks beat --loglevel=info
```

## Configuration

Environment variables (see config.py for defaults):

```bash
# Celery Broker
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Audio Processing
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=16000  # 1 second at 16kHz

# ML Models
ML_MODEL_PATH=models/noise_classifier.joblib
ML_SCALER_PATH=models/feature_scaler.joblib
```

## Testing

### Unit Tests

Tests use Celery's eager mode for synchronous execution:

```bash
# Audio processing tests
pytest tests/unit/test_tasks_audio_processing.py -v

# Maintenance tasks tests
pytest tests/unit/test_tasks_maintenance.py -v

# All task tests
pytest tests/unit/test_tasks_*.py -v
```

### Test Fixtures

- `temp_audio_file`: Creates temporary WAV file for testing
- `temp_audio_files`: Creates multiple temporary WAV files
- `app_context`: Flask application context

## Key Design Decisions

### Sync Audio Chunk Processing
Instead of `asyncio.run()` per chunk (creating new event loops repeatedly), tasks use the `audio_processor.process_chunk_sync()` adapter which:
1. Reuses existing event loops when available
2. Creates event loop only when necessary
3. Reduces overhead and improves testability

### Structured Logging
All tasks use the `@task_logger` decorator which:
1. Logs task start with arguments
2. Tracks execution duration
3. Logs success or failure with context
4. Supports metadata with structured logging

### Database Session Management
Database operations use context managers:
```python
with get_db_session() as session:
    # Automatic commit on success, rollback on error
    pass
```

### Error Handling
- Defensive error handling with `handle_task_error()`
- Supports max retries tracking
- Logs error type, message, and trace
- Critical logging after max retries reached

### Chunk Size Management
Audio chunking uses validated sizes:
- MIN_CHUNK: 8,000 samples (0.5 seconds at 16kHz)
- MAX_CHUNK: 80,000 samples (5 seconds at 16kHz)
- Never exceeds total audio length

## Periodic Task Schedule

Configured in `__init__.py`:

| Task | Schedule | Purpose |
|------|----------|---------|
| generate_daily_report | 1:00 AM UTC | Daily usage metrics |
| cleanup_old_sessions | Sunday 2:00 AM | Remove 30+ day old sessions |
| cleanup_failed_sessions | 3:00 AM UTC | Remove 24+ hour old failures |
| vacuum_database | Saturday 4:00 AM | Database optimization |
| health_check | Every hour | System status |

## Future Enhancements

- [ ] Task result backend persistence (e.g., PostgreSQL for durable results)
- [ ] Task state tracking improvements (pause/resume)
- [ ] Advanced retry policies with exponential backoff
- [ ] Task prioritization (high priority model training, low priority cleanup)
- [ ] Distributed task execution across multiple workers
- [ ] Task dependency chains and workflows
