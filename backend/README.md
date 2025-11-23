# Backend Layer

## Overview

This is the backend API server for the ANC Platform. It provides REST and WebSocket APIs for the frontend and handles all business logic.

## Architecture

```
backend/
├── api/                    # API endpoints (routes)
│   ├── __init__.py
│   ├── audio.py           # Audio processing endpoints
│   ├── users.py           # User management
│   ├── sessions.py        # Session management
│   └── health.py          # Health checks
├── services/              # Business logic layer
│   ├── __init__.py
│   ├── anc_service.py     # ANC processing logic
│   ├── ml_service.py      # ML inference
│   ├── auth_service.py    # Authentication
│   └── cloud_service.py   # Cloud integration
├── middleware/            # Request/response middleware
│   ├── __init__.py
│   ├── auth.py           # JWT authentication
│   ├── logging.py        # Request logging
│   └── cors.py           # CORS handling
├── config/               # Configuration
│   ├── __init__.py
│   ├── settings.py       # App settings
│   └── database.py       # DB connection
├── utils/                # Utilities
│   ├── __init__.py
│   └── helpers.py
├── server.py             # Main entry point
├── websocket.py          # WebSocket server
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Technology Stack

- **Framework**: Flask 3.0+
- **WebSocket**: Flask-SocketIO
- **Database ORM**: SQLAlchemy
- **Cache**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT
- **Validation**: Marshmallow

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /api/status` - System status

### Authentication
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user

### Audio Processing
- `POST /api/audio/process` - Process audio file
- `POST /api/audio/stream` - Start streaming session
- `GET /api/audio/sessions` - List sessions
- `GET /api/audio/sessions/:id` - Get session details

### ML Classification
- `POST /api/ml/classify` - Classify noise type
- `GET /api/ml/models` - List available models

### Metrics
- `GET /api/metrics/sessions/:id` - Get session metrics
- `GET /api/metrics/summary` - Get summary statistics

### WebSocket Events
- `connect` - Client connection
- `disconnect` - Client disconnection
- `audio_chunk` - Receive audio chunk
- `processed_audio` - Send processed audio
- `metrics_update` - Send real-time metrics

## Configuration

Create a `.env` file in the backend directory:

```bash
# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Server
HOST=0.0.0.0
PORT=5000
WORKERS=4

# Database (PostgreSQL)
DATABASE_URL=postgresql://anc_user:anc_password@localhost:5432/anc_system

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600

# ANC Settings
ANC_FILTER_TAPS=512
ANC_SAMPLE_RATE=48000
ANC_BLOCK_SIZE=1024
ANC_DEFAULT_ALGORITHM=nlms

# ML Settings
ML_MODEL_PATH=../models/noise_classifier_sklearn.pkl
ML_CONFIDENCE_THRESHOLD=0.7

# Emergency Detection
EMERGENCY_DETECTION_ENABLED=True
EMERGENCY_CONFIDENCE_THRESHOLD=0.85

# AWS (Optional)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/backend.log
```

## Running the Backend

### Development Mode

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
python -c "from config.database import init_db; init_db()"

# Start the server
python server.py

# In another terminal, start Celery worker
celery -A server.celery worker --loglevel=info
```

### Production Mode

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 server:app

# Using Docker
docker build -t anc-backend .
docker run -p 5000:5000 anc-backend
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_api.py
```

## API Documentation

Full API documentation is available at:
- Development: http://localhost:5000/api/docs
- Swagger UI: http://localhost:5000/swagger

## Dependencies

Key Python packages:
- Flask 3.0+
- Flask-SocketIO
- Flask-CORS
- SQLAlchemy
- Redis
- Celery
- PyJWT
- Marshmallow
- NumPy
- SciPy
- scikit-learn
- librosa

See `requirements.txt` for complete list.
