# ANC Platform - Layered Architecture

## Architecture Overview

This document describes the separated architecture layers of the ANC Platform.

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                          │
│  Location: /frontend                                         │
│  Technology: React/HTML/CSS/JavaScript                       │
│  Port: 3000 (development)                                    │
│  • Web UI components                                         │
│  • Real-time audio visualization                            │
│  • WebSocket client                                          │
│  • REST API client                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓ HTTP/WebSocket (API Gateway)
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND LAYER                           │
│  Location: /backend                                          │
│  Technology: Python/Flask/Celery                             │
│  Port: 5000 (API), 5001 (WebSocket)                          │
│  • REST API endpoints                                        │
│  • WebSocket streaming                                       │
│  • Business logic                                            │
│  • Authentication/Authorization                              │
│  • Background tasks (Celery)                                 │
└────────────┬───────────────────────┬────────────────────────┘
             │                       │
             │                       ↓ IoT/Lambda
             ↓ SQL/Redis        ┌────────────────────────────┐
┌────────────────────────┐      │      CLOUD LAYER           │
│   DATABASE LAYER       │      │  Location: /cloud          │
│  Location: /database   │      │  Technology: AWS/Terraform │
│  Technology: PostgreSQL│      │  • Lambda functions        │
│  Port: 5432            │      │  • API Gateway             │
│  • Schema definitions  │      │  • IoT Core                │
│  • Models & migrations │      │  • S3, DynamoDB            │
│  • Seed data           │      │  • CloudWatch              │
└────────────────────────┘      └────────────────────────────┘
```

## Layer Responsibilities

### 1. Frontend Layer (`/frontend`)

**Purpose**: User interface and client-side logic

**Components**:
- React application (or vanilla HTML/JS)
- Audio visualization components
- WebSocket client for real-time streaming
- REST API client
- State management
- Routing

**Communication**:
- Calls Backend REST API over HTTP/HTTPS
- Connects to Backend WebSocket for real-time audio
- No direct database or cloud access

**Technology Stack**:
- HTML5, CSS3, JavaScript
- React (optional)
- Web Audio API
- WebSocket API
- Axios/Fetch for HTTP

**Ports**:
- Development: 3000
- Production: Served via nginx (80/443)

---

### 2. Backend Layer (`/backend`)

**Purpose**: API server, business logic, and orchestration

**Components**:
- Flask REST API server
- WebSocket server (Socket.IO)
- Authentication middleware
- Business logic
- ANC algorithm orchestration
- ML model inference
- Celery workers for background tasks

**Communication**:
- Receives requests from Frontend
- Queries Database layer
- Calls Cloud services (Lambda, IoT)
- Publishes to Redis/message queues

**Technology Stack**:
- Python 3.11+
- Flask, Flask-SocketIO
- SQLAlchemy (ORM)
- Redis (caching/queues)
- Celery (background tasks)
- JWT authentication

**Ports**:
- API: 5000
- WebSocket: 5001
- Celery: N/A (worker process)

**Key Files**:
- `server.py` - Main API server
- `websocket_server.py` - WebSocket handlers
- `api/` - REST endpoints
- `services/` - Business logic
- `middleware/` - Auth, logging

---

### 3. Database Layer (`/database`)

**Purpose**: Data persistence and schema management

**Components**:
- PostgreSQL database
- SQLAlchemy models
- Alembic migrations
- Seed data scripts

**Communication**:
- Accessed only by Backend layer
- No direct frontend or cloud access

**Technology Stack**:
- PostgreSQL 14+
- SQLAlchemy (ORM)
- Alembic (migrations)

**Port**: 5432

**Schema**:
- `users` - User accounts and API keys
- `audio_sessions` - Processing sessions
- `noise_detections` - ML classification results
- `processing_metrics` - Performance metrics
- `api_requests` - Request logs
- `device_calibrations` - Hardware calibration data
- `emergency_events` - Safety alerts

---

### 4. Cloud Layer (`/cloud`)

**Purpose**: Serverless processing and AWS infrastructure

**Components**:
- AWS Lambda functions
- API Gateway
- IoT Core
- S3 storage
- DynamoDB
- CloudWatch monitoring
- Terraform IaC

**Communication**:
- Called by Backend via AWS SDK
- IoT devices connect directly
- Lambda functions trigger on events

**Technology Stack**:
- AWS Lambda (Python 3.11)
- API Gateway (REST + WebSocket)
- AWS IoT Core (MQTT)
- S3, DynamoDB
- Terraform

**Services**:
- `lambda/audio_receiver` - Receive audio streams
- `lambda/anc_processor` - Process ANC in cloud
- `lambda/audio_sender` - Send processed audio
- `iot/` - Device connectivity
- `terraform/` - Infrastructure as Code

---

## Communication Flow

### 1. Audio Processing Flow

```
Frontend (Browser)
    ↓ WebSocket: send audio chunks
Backend (Flask)
    ↓ Process with ANC algorithms
    ↓ Classify noise with ML
    ↓ Store metrics in Database
Database (PostgreSQL)
    ↑ Return processed audio
Backend
    ↑ WebSocket: stream back
Frontend (Playback)
```

### 2. Cloud Processing Flow

```
Frontend
    ↓ Upload audio file
Backend
    ↓ Upload to S3
    ↓ Trigger Lambda
Cloud (Lambda)
    ↓ Process audio
    ↓ Store in DynamoDB
    ↓ Notify via SNS
Backend
    ↑ Poll for results
    ↑ Return to frontend
Frontend
```

### 3. IoT Device Flow

```
IoT Device (Firmware)
    ↓ MQTT: publish audio
Cloud (IoT Core)
    ↓ Route to Lambda
Cloud (Lambda)
    ↓ Process ANC
    ↓ Publish result
Cloud (IoT Core)
    ↑ MQTT: subscribe
IoT Device
```

---

## Environment Variables

### Frontend
```bash
REACT_APP_API_URL=http://localhost:5000
REACT_APP_WS_URL=ws://localhost:5001
REACT_APP_ENV=development
```

### Backend
```bash
# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/anc_system

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS (optional)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# ANC Configuration
ANC_FILTER_TAPS=512
ANC_SAMPLE_RATE=48000
```

### Database
```bash
POSTGRES_USER=anc_user
POSTGRES_PASSWORD=anc_password
POSTGRES_DB=anc_system
```

### Cloud
```bash
AWS_REGION=us-east-1
ENVIRONMENT=production
IOT_ENDPOINT=your-iot-endpoint.amazonaws.com
```

---

## Deployment

### Development

```bash
# Terminal 1: Database
docker-compose up -d postgres redis

# Terminal 2: Backend
cd backend
python server.py

# Terminal 3: Frontend
cd frontend
npm start

# Terminal 4: Celery worker
cd backend
celery -A tasks.celery worker
```

### Production

```bash
# Build and deploy all layers
docker-compose -f docker-compose.prod.yml up -d

# Deploy cloud infrastructure
cd cloud/terraform
terraform apply
```

---

## Security Boundaries

1. **Frontend ↔ Backend**: JWT authentication, CORS policies
2. **Backend ↔ Database**: Connection pooling, prepared statements
3. **Backend ↔ Cloud**: IAM roles, API keys, VPC
4. **Cloud ↔ IoT**: X.509 certificates, TLS 1.3

---

## Benefits of This Architecture

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Independent Scaling**: Scale each layer based on demand
3. **Technology Flexibility**: Can swap implementations per layer
4. **Security**: Clear boundaries with defined access patterns
5. **Testing**: Can test each layer independently
6. **Deployment**: Deploy layers separately (CI/CD friendly)
7. **Team Organization**: Different teams can own different layers

---

## Migration Plan

See `/docs/architecture/MIGRATION_GUIDE.md` for step-by-step migration from monolithic to layered architecture.
