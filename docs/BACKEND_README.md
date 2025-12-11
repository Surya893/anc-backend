# ANC Platform - Comprehensive Backend

Enterprise-grade Active Noise Cancellation Platform with real-time audio processing, ML classification, and WebSocket streaming.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  (Web UI, Mobile Apps, API Clients)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      API Gateway                                │
│  - REST API (Flask)                                            │
│  - WebSocket (SocketIO)                                        │
│  - Authentication (JWT + API Keys)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼────────┐
│   Audio      │  │  Database   │  │   Cache      │
│  Processor   │  │ (SQLAlchemy)│  │  (Redis)     │
│              │  │             │  │              │
│ - Real-time  │  │ - Users     │  │ - Sessions   │
│ - ANC Engine │  │ - Sessions  │  │ - Metrics    │
│ - ML Models  │  │ - Metrics   │  │ - Pub/Sub    │
└───────┬──────┘  └─────────────┘  └──────────────┘
        │
┌───────▼──────────────────────────────────────────┐
│           Background Tasks (Celery)               │
│  - File Processing                               │
│  - Model Training                                │
│  - Analytics                                     │
│  - Cleanup                                       │
└──────────────────────────────────────────────────┘
```

## 📂 Project Structure

```
anc-with-ai/
├── server.py                    # Main API server
├── config.py                    # Configuration management
├── models.py                    # SQLAlchemy database models
├── audio_processor.py           # Real-time audio processing
├── websocket_server.py          # WebSocket handlers
├── tasks.py                     # Celery background tasks
├── wsgi.py                      # Production WSGI entry point
├── advanced_anc_algorithms.py   # ANC algorithms (LMS, NLMS, RLS)
├── feature_extraction.py        # Audio feature extraction
├── predict_sklearn.py           # ML noise classification
├── emergency_noise_detector.py  # Emergency sound detection
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Local development stack
├── Dockerfile                   # Container image
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Redis server
- PostgreSQL (optional, uses SQLite by default)
- PortAudio (for PyAudio)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd anc-with-ai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask --app server init-db

# Create admin user
flask --app server create-admin
```

### Running Locally

#### Development Mode

```bash
# Start Redis (in separate terminal)
redis-server

# Start Celery worker (in separate terminal)
celery -A tasks.celery_app worker --loglevel=info

# Start Flask server
python server.py
```

Server will be available at `http://localhost:5000`

#### Production Mode

```bash
# Using Gunicorn with Gevent workers
gunicorn --worker-class gevent \
         --workers 4 \
         --bind 0.0.0.0:5000 \
         --timeout 120 \
         wsgi:application

# Or using eventlet
gunicorn --worker-class eventlet \
         --workers 1 \
         --bind 0.0.0.0:5000 \
         wsgi:application
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f anc-api

# Stop services
docker-compose down
```

## 🔐 Authentication

### API Key Authentication

```bash
# Register a new user
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "secure_password"
  }'

# Response includes API key
{
  "message": "User created successfully",
  "user": {...},
  "api_key": "abc123..."
}

# Use API key in requests
curl -H "X-API-Key: abc123..." \
  http://localhost:5000/api/v1/sessions
```

### JWT Token Authentication

```bash
# Login to get JWT token
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "secure_password"
  }'

# Response includes token
{
  "token": "eyJ0eXAi...",
  "user": {...},
  "expires_in": 86400
}

# Use token in requests
curl -H "Authorization: Bearer eyJ0eXAi..." \
  http://localhost:5000/api/v1/sessions
```

## 📡 API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/refresh-api-key` - Refresh API key

### Audio Processing Sessions

- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions/<id>` - Get session details
- `PATCH /api/v1/sessions/<id>` - Update session settings
- `POST /api/v1/sessions/<id>/end` - End session

### Audio Processing

- `POST /api/v1/audio/process` - Process audio chunk (sync)
- `POST /api/v1/audio/process-file` - Process audio file (async)

### Statistics

- `GET /api/v1/stats/sessions` - Get session statistics
- `GET /api/v1/stats/detections` - Get detection statistics

### General

- `GET /` - Web UI homepage
- `GET /demo` - Premium demo page
- `GET /health` - Health check
- `GET /api/v1/info` - API information

## 🔌 WebSocket API

### Connect

```javascript
const socket = io('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected:', socket.id);
});
```

### Start Session

```javascript
socket.emit('start_session', {
  session_id: 'my-session',
  config: {
    anc_enabled: true,
    anc_intensity: 1.0,
    anc_algorithm: 'lms'
  }
});

socket.on('session_started', (data) => {
  console.log('Session started:', data);
});
```

### Process Audio

```javascript
// Convert audio to base64
const audioBase64 = btoa(String.fromCharCode.apply(null, audioArray));

socket.emit('process_audio', {
  session_id: 'my-session',
  audio_data: audioBase64,
  apply_anc: true
});

socket.on('audio_processed', (result) => {
  console.log('Processed:', result);
  // result includes:
  // - processed_audio (base64)
  // - anc_metrics
  // - noise_detection
  // - performance metrics
});
```

### Update ANC Settings

```javascript
socket.emit('update_anc_settings', {
  session_id: 'my-session',
  anc_enabled: true,
  anc_intensity: 0.8,
  anc_algorithm: 'nlms'
});
```

### End Session

```javascript
socket.emit('end_session', {
  session_id: 'my-session'
});

socket.on('session_ended', (data) => {
  console.log('Session ended:', data.stats);
});
```

## 🗄️ Database Models

### User
- User accounts with authentication
- API keys for programmatic access
- Admin/user roles

### AudioSession
- Audio processing sessions
- ANC configuration
- Performance metrics

### NoiseDetection
- Detected noise events
- Classification results
- Emergency flags

### ProcessingMetric
- Real-time performance data
- Latency, cancellation, SNR
- System resources

### NoiseProfile
- Stored noise signatures
- Training data
- Feature vectors

### APIRequest
- API usage logging
- Response times
- Analytics

## ⚙️ Configuration

Configuration is managed through `config.py` with environment-specific classes:

### Environment Variables

```bash
# Application
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
export JWT_SECRET_KEY=your-jwt-secret

# Database
export DATABASE_URL=postgresql://user:pass@localhost/anc_platform

# Redis
export REDIS_URL=redis://localhost:6379/0

# Celery
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS
export CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Logging
export LOG_LEVEL=INFO
```

### Configuration Classes

- `DevelopmentConfig` - Debug mode, verbose logging
- `StagingConfig` - Testing environment
- `ProductionConfig` - Optimized for production
- `TestingConfig` - Unit testing

## 🔄 Background Tasks (Celery)

### Available Tasks

1. **process_audio_file** - Process audio file asynchronously
2. **batch_process_files** - Process multiple files
3. **train_noise_classifier** - Train/retrain ML model
4. **analyze_session_data** - Generate session analytics
5. **cleanup_old_sessions** - Remove old data
6. **generate_daily_report** - Create usage reports

### Running Celery

```bash
# Worker
celery -A tasks.celery_app worker --loglevel=info

# Beat (scheduler for periodic tasks)
celery -A tasks.celery_app beat --loglevel=info

# Flower (monitoring UI)
celery -A tasks.celery_app flower
# Access at http://localhost:5555
```

## 📊 Monitoring

### Prometheus Metrics

Metrics exposed at `/metrics`:

- Request count and latency
- Session statistics
- Processing metrics
- System resources

### Logging

Logs written to `logs/anc_platform.log` with rotation:

- Request/response logging
- Error tracking
- Performance metrics
- Audit trail

## 📋 Background Tasks (Celery)

### Architecture

The Celery task system has been refactored into a modular structure:

```
src/api/
├── celery_app.py              # Celery app initialization
└── tasks/
    ├── __init__.py            # Task exports and periodic task setup
    ├── utils.py               # Shared utilities (logging, DB, validation)
    ├── audio_processing.py    # Audio file processing tasks
    ├── model_training.py      # Model training tasks
    ├── analytics.py           # Analytics and reporting tasks
    └── maintenance.py         # System maintenance tasks
```

### Task Categories

#### Audio Processing Tasks
- `process_audio_file`: Process single audio file with chunk-based streaming
- `batch_process_files`: Process multiple files with progress tracking

**Key improvements:**
- Replaced `asyncio.run` per-chunk with sync adapter (`process_chunk_sync`)
- Proper chunk size validation and management
- Structured progress tracking

#### Model Training Tasks
- `train_noise_classifier`: Train RF classifier from organized audio data
- `validate_model`: Verify trained model is loadable

#### Analytics Tasks
- `analyze_session_data`: Comprehensive session analysis with noise distribution
- `generate_daily_report`: Daily usage and performance metrics
- `export_session_data`: Export session data (JSON/CSV)

#### Maintenance Tasks
- `cleanup_old_sessions`: Remove sessions older than N days
- `cleanup_failed_sessions`: Remove failed/incomplete sessions
- `vacuum_database`: Database optimization
- `health_check`: System health monitoring

### Running Tasks

#### Development (Eager Mode)
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
cd /home/engine/project
celery -A src.api.tasks worker --loglevel=debug

# Terminal 3: Start Flask app
python -c "from src.api.server import app; app.run(debug=True)"
```

#### Production
```bash
# Using systemd or supervisor
celery -A src.api.tasks worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100

# With beat scheduler for periodic tasks
celery -A src.api.tasks beat --loglevel=info
```

### Task Configuration

Configure in environment variables:
```bash
# Broker and result backend
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Audio processing
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=16000  # 1 second at 16kHz

# Model paths
ML_MODEL_PATH=models/noise_classifier.joblib
ML_SCALER_PATH=models/feature_scaler.joblib
```

### Periodic Task Schedule

Configured in `src/api/tasks/__init__.py`:

- **Daily Report** (1:00 AM UTC): `generate_daily_report`
- **Cleanup Old Sessions** (Sunday 2:00 AM UTC): `cleanup_old_sessions` (30+ days)
- **Cleanup Failed Sessions** (3:00 AM UTC): `cleanup_failed_sessions` (24+ hours)
- **Database Vacuum** (Saturday 4:00 AM UTC): `vacuum_database`
- **Health Check** (Every hour): `health_check`

### Testing Tasks

```bash
# Run task unit tests
pytest tests/unit/test_tasks_audio_processing.py -v
pytest tests/unit/test_tasks_maintenance.py -v

# Test with eager mode (synchronous execution)
# Configured in pytest fixtures
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest tests/test_api.py

# With verbose output
pytest -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t anc-platform:latest .

# Run container
docker run -d \
  -p 5000:5000 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  --name anc-platform \
  anc-platform:latest
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n anc-platform

# View logs
kubectl logs -f deployment/anc-system -n anc-platform
```

### Cloud Platforms

Scripts provided for:
- AWS EKS (`deploy/aws/`)
- Google GKE (`deploy/gcp/`)
- Azure AKS (`deploy/azure/`)

## 🔧 Advanced Features

### Custom ANC Algorithms

Add new algorithms in `advanced_anc_algorithms.py`:

```python
class CustomANCFilter:
    def __init__(self, **kwargs):
        # Initialize
        pass

    def process(self, reference, desired):
        # Process audio
        return anti_noise, metrics
```

Register in `AdvancedANCSystem`:

```python
self.algorithms['custom'] = CustomANCFilter
```

### Custom Noise Profiles

Train custom noise classifiers:

```bash
# Organize training data
data/
  noise_types/
    traffic/
      sample1.wav
      sample2.wav
    office/
      sample1.wav

# Trigger training
curl -X POST http://localhost:5000/api/v1/models/train \
  -H "X-API-Key: ..." \
  -d '{"training_data_dir": "data/noise_types"}'
```

## 📈 Performance

- **Latency**: <30ms average processing time
- **Throughput**: 1000+ chunks/second per worker
- **Cancellation**: 35-45dB noise reduction
- **Accuracy**: 95.83% classification accuracy

## 🛠️ Troubleshooting

### Common Issues

**PyAudio Installation Error**
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# macOS
brew install portaudio

# Then reinstall
pip install pyaudio
```

**Redis Connection Error**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Start Redis
redis-server
```

**Database Migration Issues**
```bash
# Reset database
flask --app server init-db

# Or use Alembic for migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 📚 Additional Documentation

- [API Reference](./docs/API.md)
- [WebSocket Protocol](./docs/WEBSOCKET.md)
- [ANC Algorithms](./docs/ALGORITHMS.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## 👥 Support

- Email: support@ancplatform.com
- Issues: GitHub Issues
- Docs: https://docs.ancplatform.com

---

**Built with ❤️ for the future of noise cancellation**
