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

### Modular Flask Blueprint Architecture

```
backend/
├── server.py                    # Flask app factory + main entry point
├── api/                         # API blueprint modules
│   ├── __init__.py
│   ├── audio.py                 # Audio processing endpoints (process, classify, emergency-detect)
│   ├── health.py                # Health check endpoints
│   ├── sessions.py              # Session management endpoints
│   └── users.py                 # User management endpoints
├── services/                    # Business logic services
│   ├── anc_service.py           # ANC processing service (NLMS, LMS, RLS filters)
│   └── ml_service.py            # ML inference service (classification, emergency detection)
├── middleware/                  # Request/response middleware
│   ├── auth.py                  # JWT + API key authentication
│   └── logging.py               # Request logging middleware
└── websocket.py                 # WebSocket event handlers

src/api/
├── server.py                    # Main production API server
├── api_server.py                # Additional API implementations
├── tasks.py                     # Celery background task definitions
├── websocket_server.py          # WebSocket server implementation
└── websocket_streaming.py       # Real-time audio streaming

src/ml/
├── noise_classifier_v2.py       # ML noise classification model
├── emergency_noise_detector.py  # Emergency sound detector
└── feature_extraction.py        # Audio feature extraction

src/utils/
└── audio_capture.py             # Audio capture utilities

src/web/
├── app.py                       # Flask web UI application
└── main.py                      # Web UI entry point
```

### Celery Task Structure

```
src/api/tasks.py                 # All Celery task definitions
├── process_audio_file()         # Async audio file processing
├── process_audio_chunk()        # Individual chunk processing
├── classify_audio_batch()       # Batch noise classification
├── detect_emergency_batch()     # Batch emergency detection
├── train_model()                # Background model training
├── cleanup_old_sessions()       # Maintenance: cleanup sessions
└── generate_report()            # Analytics: report generation
```

### Core Dependencies

- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Local development stack
- `Dockerfile` - Container image
- `wsgi.py` - Production WSGI entry point

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

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=backend --cov=src --cov-report=html

# Flask blueprint tests
pytest tests/unit/test_flask_blueprints.py -v

# Celery task tests (eager mode)
pytest tests/unit/test_celery_tasks.py -v

# Run tests by marker
pytest -m flask       # API endpoint tests
pytest -m celery      # Background task tests
pytest -m auth        # Authentication tests
pytest -m audio       # Audio processing tests

# Specific test file
pytest tests/test_api.py

# With verbose output
pytest -v
```

### Test Fixtures and conftest.py

The test suite provides comprehensive fixtures in `tests/conftest.py`:

**Flask Testing:**
```python
def test_audio_endpoint(client, mock_user, mock_anc_service):
    """Test audio processing endpoint."""
    with patch('backend.api.audio.anc_service', mock_anc_service):
        response = client.post(
            '/api/audio/process',
            data=json.dumps({'audio_data': 'base64...'}),
            headers={'Authorization': 'Bearer token'}
        )
        assert response.status_code == 200
```

**Celery Task Testing (Eager Mode):**
```python
@pytest.mark.celery
def test_audio_processing_task(mock_celery_task):
    """Test Celery task with eager mode."""
    mock_celery_task.update_state(
        state='PROGRESS',
        meta={'current': 1, 'total': 100}
    )
    assert mock_celery_task.update_state.called
```

See [tests/README.md](../tests/README.md) for detailed testing documentation.

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
