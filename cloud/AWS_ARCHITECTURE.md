# AWS Cloud Architecture for Real-Time ANC Processing

## Architecture Overview

This cloud architecture processes incoming audio in real-time, applies Active Noise Cancellation algorithms, and streams back phase-inverted audio for noise reduction.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Web Client  │    │ Mobile App   │    │  Hardware    │          │
│  │  (Browser)   │    │  (iOS/And)   │    │  Device      │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                    │                    │                  │
│         └────────────────────┼────────────────────┘                  │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │ HTTPS/WSS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS EDGE LAYER                                  │
│  ┌─────────────────────────────────────────────────────┐            │
│  │  Amazon CloudFront (CDN)                            │            │
│  │  • Global edge locations for low latency           │            │
│  │  • HTTPS/WSS termination                           │            │
│  │  • DDoS protection with AWS Shield                 │            │
│  └─────────────────┬───────────────────────────────────┘            │
└────────────────────┼────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AWS API GATEWAY LAYER                            │
│                                                                      │
│  ┌────────────────────────────┐  ┌─────────────────────────────┐   │
│  │  API Gateway (REST)        │  │  API Gateway (WebSocket)    │   │
│  │  • Authentication (JWT)    │  │  • Real-time bidirectional  │   │
│  │  • Rate limiting           │  │  • Connection management    │   │
│  │  • Request validation      │  │  • Message routing          │   │
│  └────────────┬───────────────┘  └────────────┬────────────────┘   │
└───────────────┼──────────────────────────────┼────────────────────┘
                │                               │
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS COMPUTE LAYER                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  AWS Lambda Functions (Serverless)                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │  │
│  │  │ Audio Receiver  │  │ ANC Processor   │  │ ML Classifier│ │  │
│  │  │ • Decode audio  │  │ • NLMS filter   │  │ • Noise type │ │  │
│  │  │ • Validate      │  │ • Phase invert  │  │ • 95.8% acc  │ │  │
│  │  │ • Queue         │  │ • Apply gain    │  │ • Real-time  │ │  │
│  │  └─────────────────┘  └─────────────────┘  └──────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Amazon ECS Fargate (Containerized)                          │  │
│  │  • Heavy processing for complex audio                        │  │
│  │  • Auto-scaling based on CPU/memory                          │  │
│  │  • Spot instances for cost optimization                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Amazon SageMaker (ML Inference)                             │  │
│  │  • Real-time endpoint for noise classification               │  │
│  │  • Batch transform for historical analysis                   │  │
│  │  • Auto-scaling with target tracking                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS STORAGE & DATA LAYER                          │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │  Amazon S3     │  │  Amazon RDS    │  │  Amazon DynamoDB   │   │
│  │  (Audio Store) │  │  (PostgreSQL)  │  │  (Sessions/State)  │   │
│  │  • Raw audio   │  │  • User data   │  │  • Real-time data  │   │
│  │  • Processed   │  │  • Analytics   │  │  • Low latency     │   │
│  │  • ML models   │  │  • Audit logs  │  │  • Auto-scaling    │   │
│  └────────────────┘  └────────────────┘  └────────────────────┘   │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │ Amazon ElastiC │  │  Amazon SQS    │  │  Amazon Kinesis    │   │
│  │ ache (Redis)   │  │  (Queues)      │  │  (Streaming)       │   │
│  │  • Session     │  │  • Async proc. │  │  • Real-time data  │   │
│  │  • Cache       │  │  • Decoupling  │  │  • Analytics       │   │
│  └────────────────┘  └────────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  AWS MONITORING & LOGGING LAYER                      │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │  CloudWatch    │  │  CloudWatch    │  │  AWS X-Ray         │   │
│  │  Logs          │  │  Metrics       │  │  (Tracing)         │   │
│  │  • Centralized │  │  • Dashboards  │  │  • Performance     │   │
│  │  • Searchable  │  │  • Alarms      │  │  • Bottlenecks     │   │
│  └────────────────┘  └────────────────┘  └────────────────────┘   │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐                            │
│  │  AWS CloudTrail│  │  SNS Topics    │                            │
│  │  (Audit)       │  │  (Alerts)      │                            │
│  └────────────────┘  └────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow - Real-Time Audio Processing

### 1. Audio Upload Flow

```
Client                                                        AWS Cloud
  │
  ├─> 1. Connect WebSocket
  │     wss://api.anc-platform.com/ws
  │                                                              │
  │                                                    ┌─────────▼────────┐
  │                                                    │ API Gateway (WSS)│
  │                                                    │ • Authenticate   │
  │                                                    │ • Rate limit     │
  │                                                    └─────────┬────────┘
  │                                                              │
  ├─> 2. Send Audio Chunk                                       │
  │     Base64(Float32Array)                          ┌─────────▼────────┐
  │     48kHz, 512 samples                            │ Lambda: Receiver │
  │                                                    │ • Decode base64  │
  │                                                    │ • Validate       │
  │                                                    └─────────┬────────┘
  │                                                              │
  │                                                    ┌─────────▼────────┐
  │                                                    │ Amazon SQS       │
  │                                                    │ • Buffer chunks  │
  │                                                    └─────────┬────────┘
  │                                                              │
  │                                                    ┌─────────▼────────┐
  │                                                    │ Lambda: ANC Proc │
  │                                                    │ • NLMS filter    │
  │                                                    │ • Phase invert   │
  │                                                    │ • Apply gain     │
  │                                                    └─────────┬────────┘
  │                                                              │
  │                                                    ┌─────────▼────────┐
  │                                                    │ SageMaker        │
  │                                                    │ • Classify noise │
  │                                                    │ • Adapt params   │
  │                                                    └─────────┬────────┘
  │                                                              │
  │                                                    ┌─────────▼────────┐
  ├<─ 3. Receive Processed Audio                      │ Lambda: Sender   │
  │     Base64(Processed)                             │ • Encode result  │
  │     ~5-8ms latency                                │ • Send via WSS   │
  │                                                    └──────────────────┘
  │
  ├─> 4. Play Processed Audio
  │     Through speakers
  │
```

### 2. Batch Processing Flow

```
Client Upload                                         AWS Cloud
  │
  ├─> Upload Audio File                               ┌─────────────────┐
  │   POST /api/v1/audio/upload                       │ API Gateway     │
  │                                                    │ (REST)          │
  │                                                    └────────┬────────┘
  │                                                             │
  │                                                    ┌────────▼────────┐
  │                                                    │ Lambda: Upload  │
  │                                                    │ • Generate S3   │
  │                                                    │   presigned URL │
  │                                                    └────────┬────────┘
  │                                                             │
  ├─> Upload to S3                                    ┌────────▼────────┐
  │   PUT presigned URL                               │ S3: Raw Audio   │
  │                                                    │ • Trigger event │
  │                                                    └────────┬────────┘
  │                                                             │
  │                                                    ┌────────▼────────┐
  │                                                    │ Lambda: Process │
  │                                                    │ • Stream read   │
  │                                                    │ • Apply ANC     │
  │                                                    │ • Write S3      │
  │                                                    └────────┬────────┘
  │                                                             │
  │                                                    ┌────────▼────────┐
  │                                                    │ S3: Processed   │
  │                                                    │ • Generate URL  │
  │                                                    └────────┬────────┘
  │                                                             │
  ├<─ Download Processed                              ┌────────▼────────┐
  │   GET /api/v1/audio/:id                           │ Lambda: Download│
  │                                                    │ • Presigned URL │
  │                                                    └─────────────────┘
```

## Component Details

### API Gateway Configuration

#### REST API Endpoints

```yaml
Endpoints:
  - POST /auth/register
    - Lambda: UserRegistration
    - RDS: Write user
    - Response: JWT token

  - POST /auth/login
    - Lambda: UserLogin
    - RDS: Verify credentials
    - Response: JWT token

  - POST /audio/upload
    - Lambda: GenerateUploadURL
    - S3: Presigned URL
    - Response: Upload URL + ID

  - POST /audio/process
    - Lambda: TriggerBatchProcess
    - SQS: Queue job
    - Response: Job ID

  - GET /audio/{id}
    - Lambda: GetAudioStatus
    - DynamoDB: Query status
    - Response: Status + Download URL

  - GET /sessions/{id}/stats
    - Lambda: GetSessionStats
    - RDS: Query metrics
    - Response: Statistics
```

#### WebSocket API Routes

```yaml
Routes:
  $connect:
    - Lambda: OnConnect
    - DynamoDB: Create connection record
    - Response: Connection ID

  $disconnect:
    - Lambda: OnDisconnect
    - DynamoDB: Delete connection record
    - Cleanup: Stop processing

  startStream:
    - Lambda: StartAudioStream
    - ElastiCache: Create session
    - DynamoDB: Initialize state
    - Response: Session ID

  audioChunk:
    - Lambda: ReceiveAudioChunk
    - SQS: Enqueue for processing
    - Async processing pipeline

  stopStream:
    - Lambda: StopAudioStream
    - ElastiCache: Delete session
    - S3: Save session recording
    - Response: Summary stats
```

### Lambda Functions

#### 1. Audio Receiver (`lambda_audio_receiver.py`)

**Purpose**: Receive and validate incoming audio chunks

**Configuration**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 10 seconds
- Concurrency: 1000
- Layers: NumPy, Audio processing libs

**Process**:
1. Decode Base64 audio data
2. Validate format (Float32, 48kHz)
3. Store in SQS for processing
4. Return acknowledgment

#### 2. ANC Processor (`lambda_anc_processor.py`)

**Purpose**: Apply NLMS filtering and phase inversion

**Configuration**:
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 30 seconds
- Concurrency: 500
- Layers: NumPy, SciPy, Custom ANC library

**Process**:
1. Read audio chunk from SQS
2. Load filter coefficients from ElastiCache
3. Apply NLMS adaptive filtering
4. Generate phase-inverted signal
5. Mix with original (if needed)
6. Send to output queue

#### 3. ML Classifier (`lambda_ml_classifier.py`)

**Purpose**: Classify noise type for adaptive ANC

**Configuration**:
- Runtime: Python 3.11
- Memory: 2048 MB
- Timeout: 10 seconds
- Concurrency: 200

**Process**:
1. Extract audio features
2. Call SageMaker endpoint
3. Get noise classification
4. Update ANC parameters
5. Cache classification result

#### 4. Audio Sender (`lambda_audio_sender.py`)

**Purpose**: Send processed audio back to client

**Configuration**:
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 5 seconds
- Concurrency: 1000

**Process**:
1. Read processed audio from queue
2. Encode to Base64
3. Send via WebSocket connection
4. Track delivery metrics

### SageMaker ML Model

#### Model Training

**Dataset**:
- Location: `s3://anc-platform-ml/datasets/noise-classification/`
- Format: Parquet
- Size: 1M samples across 6 noise types

**Training**:
- Algorithm: Random Forest (scikit-learn)
- Instance: ml.m5.xlarge
- Training time: ~30 minutes
- Accuracy: 95.83%

**Hyperparameters**:
```python
{
    'n_estimators': 200,
    'max_depth': 20,
    'min_samples_split': 5,
    'min_samples_leaf': 2
}
```

#### Real-Time Endpoint

**Configuration**:
- Instance: ml.t3.medium (for real-time)
- Auto-scaling: 1-10 instances
- Target: 70% CPU utilization
- Latency: <10ms

**Input Format**:
```json
{
    "instances": [
        {
            "features": [0.123, 0.456, ...],  // 40 MFCC features
            "sample_rate": 48000
        }
    ]
}
```

**Output Format**:
```json
{
    "predictions": [
        {
            "class": "traffic",
            "confidence": 0.94,
            "probabilities": {
                "white": 0.01,
                "pink": 0.02,
                "traffic": 0.94,
                "office": 0.01,
                "construction": 0.01,
                "cafe": 0.01
            }
        }
    ]
}
```

### Storage Configuration

#### S3 Buckets

```yaml
Buckets:
  anc-platform-audio-raw:
    - Purpose: Raw uploaded audio files
    - Lifecycle: Archive to Glacier after 90 days
    - Encryption: AES-256
    - Versioning: Enabled

  anc-platform-audio-processed:
    - Purpose: ANC-processed audio files
    - Lifecycle: Delete after 30 days
    - Encryption: AES-256
    - Versioning: Disabled

  anc-platform-ml-models:
    - Purpose: SageMaker model artifacts
    - Lifecycle: Retain indefinitely
    - Encryption: KMS
    - Versioning: Enabled

  anc-platform-ml-datasets:
    - Purpose: Training and test datasets
    - Lifecycle: Archive to Glacier after 180 days
    - Encryption: KMS
    - Versioning: Enabled

  anc-platform-logs:
    - Purpose: Application logs and audit trails
    - Lifecycle: Archive to Glacier after 90 days, delete after 365 days
    - Encryption: AES-256
    - Versioning: Disabled
```

#### RDS PostgreSQL

**Configuration**:
- Engine: PostgreSQL 15
- Instance: db.t3.medium
- Storage: 100 GB SSD (auto-scaling to 1TB)
- Multi-AZ: Yes (production)
- Backups: Daily, 7-day retention
- Encryption: At rest with KMS

**Schema**:
```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audio Sessions
CREATE TABLE audio_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    sample_rate INTEGER NOT NULL,
    anc_enabled BOOLEAN DEFAULT TRUE,
    anc_intensity REAL DEFAULT 1.0,
    total_samples BIGINT DEFAULT 0,
    avg_cancellation_db REAL DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'active'
);

-- Noise Detections
CREATE TABLE noise_detections (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES audio_sessions(id),
    timestamp TIMESTAMP NOT NULL,
    noise_type VARCHAR(50) NOT NULL,
    confidence REAL NOT NULL,
    avg_power_db REAL,
    peak_frequency_hz REAL
);

-- Processing Metrics
CREATE TABLE processing_metrics (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES audio_sessions(id),
    timestamp TIMESTAMP NOT NULL,
    latency_ms INTEGER,
    cpu_utilization REAL,
    memory_mb INTEGER,
    cancellation_db REAL,
    algorithm VARCHAR(50)
);
```

#### DynamoDB Tables

**Table: ConnectionsTable**
```yaml
TableName: anc-connections
Attributes:
  - connectionId (S) - Hash key
  - userId (S)
  - connectedAt (N)
  - lastActivity (N)
TTL: lastActivity + 1 hour
Capacity: On-demand
```

**Table: SessionsTable**
```yaml
TableName: anc-sessions
Attributes:
  - sessionId (S) - Hash key
  - userId (S) - Range key
  - connectionId (S)
  - status (S)
  - config (M)  # Map of session configuration
  - createdAt (N)
  - updatedAt (N)
GSI:
  - userId-createdAt-index
Capacity: On-demand
```

#### ElastiCache Redis

**Configuration**:
- Engine: Redis 7.0
- Node type: cache.t3.medium
- Cluster mode: Enabled
- Nodes: 3 (1 primary, 2 replicas)
- Encryption: In-transit and at-rest

**Data Structures**:
```
Session cache:
  KEY: session:{sessionId}
  TYPE: Hash
  FIELDS:
    - filter_coefficients (Binary)
    - filter_state (Binary)
    - noise_type (String)
    - anc_intensity (Float)
    - last_update (Timestamp)
  TTL: 1 hour

Connection mapping:
  KEY: connection:{connectionId}
  TYPE: String
  VALUE: sessionId
  TTL: 1 hour

User sessions:
  KEY: user:{userId}:sessions
  TYPE: Set
  MEMBERS: [sessionId1, sessionId2, ...]
  TTL: 24 hours
```

### Monitoring & Alerting

#### CloudWatch Dashboards

**1. Real-Time Processing Dashboard**
- WebSocket connections (active, new, closed)
- Lambda invocations and errors
- Processing latency (p50, p95, p99)
- SageMaker endpoint invocations
- SQS queue depth

**2. Cost Dashboard**
- Lambda costs by function
- SageMaker endpoint costs
- Data transfer costs
- Storage costs (S3, RDS, ElastiCache)

**3. ML Model Performance Dashboard**
- Inference latency
- Model accuracy (online evaluation)
- Feature drift detection
- Data quality metrics

#### CloudWatch Alarms

```yaml
Alarms:
  HighLatency:
    Metric: Lambda Duration
    Threshold: > 500ms (p95)
    Period: 5 minutes
    Action: SNS notification

  HighErrorRate:
    Metric: Lambda Errors
    Threshold: > 1% of invocations
    Period: 5 minutes
    Action: SNS + Auto-scaling

  QueueBacklog:
    Metric: SQS ApproximateNumberOfMessages
    Threshold: > 1000
    Period: 1 minute
    Action: Scale out Lambda concurrency

  ModelDrift:
    Metric: SageMaker Model Quality
    Threshold: Accuracy < 90%
    Period: 1 hour
    Action: SNS notification + Retrain trigger

  HighCost:
    Metric: Estimated charges
    Threshold: > $100/day
    Period: 24 hours
    Action: SNS notification
```

## Cost Optimization

### Free Tier Utilization

**Always Free**:
- Lambda: 1M requests/month, 400K GB-seconds compute
- API Gateway: 1M REST API calls/month
- S3: 5GB storage, 20K GET, 2K PUT requests
- CloudWatch: 10 custom metrics, 10 alarms
- DynamoDB: 25 GB storage, 25 read/write capacity units

**12 Months Free**:
- RDS: 750 hours of db.t3.micro
- ElastiCache: 750 hours of cache.t3.micro
- CloudFront: 50 GB data transfer
- SageMaker: 250 hours of ml.t3.medium notebooks

### Cost Optimization Strategies

1. **Serverless First**: Use Lambda for variable workloads
2. **Spot Instances**: 70% discount for batch processing
3. **Reserved Capacity**: 40-60% discount for RDS/ElastiCache (production)
4. **S3 Lifecycle**: Auto-archive to Glacier
5. **Right-sizing**: Match instance types to workload
6. **Auto-scaling**: Scale down during low usage
7. **Caching**: Reduce database and SageMaker calls

### Estimated Monthly Costs

**Development Environment** (using free tier):
- Lambda: $0 (within free tier)
- API Gateway: $0 (within free tier)
- S3: $0 (within free tier)
- RDS (db.t3.micro): $0 (free tier)
- ElastiCache (cache.t3.micro): $0 (free tier)
- **Total: ~$0-$10/month**

**Production Environment** (1000 concurrent users):
- Lambda: $50/month
- API Gateway: $35/month
- S3: $20/month
- RDS (db.t3.medium, Multi-AZ): $120/month
- ElastiCache (3 nodes): $80/month
- SageMaker endpoint: $100/month
- Data transfer: $50/month
- CloudWatch: $30/month
- **Total: ~$485/month**

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | <25ms | CloudWatch p95 |
| WebSocket Latency | <10ms | Custom metric |
| Audio Processing | <8ms | Lambda duration |
| End-to-End Latency | <40ms | Client measurement |
| Throughput | 1000 concurrent streams | Load testing |
| Availability | 99.9% | CloudWatch uptime |
| Error Rate | <0.1% | CloudWatch errors |

## Deployment Regions

**Primary**: us-east-1 (N. Virginia)
- Lowest cost
- Most services available
- Largest capacity

**Secondary**: eu-west-1 (Ireland)
- European users
- GDPR compliance
- Disaster recovery

**Tertiary**: ap-southeast-1 (Singapore)
- Asian users
- Low latency for APAC

## Security

### Authentication & Authorization
- JWT tokens for API access
- API keys for programmatic access
- AWS IAM roles for service-to-service
- MFA for admin access

### Encryption
- TLS 1.3 for data in transit
- AES-256 for S3 data at rest
- KMS for sensitive data (models, credentials)
- Field-level encryption for PII

### Network Security
- VPC with private subnets for RDS/ElastiCache
- Security groups with least privilege
- NACLs for network isolation
- AWS WAF for API Gateway

### Compliance
- GDPR: Data residency, right to deletion
- HIPAA: PHI encryption and audit logging
- SOC 2: Access controls and monitoring
- ISO 27001: Information security management

## Next Steps

1. **Deploy Infrastructure**: Run Terraform scripts
2. **Upload ML Model**: Deploy trained model to SageMaker
3. **Configure Monitoring**: Set up dashboards and alarms
4. **Load Testing**: Validate performance targets
5. **Cost Monitoring**: Track actual vs estimated costs
