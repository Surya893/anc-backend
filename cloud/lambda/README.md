# Lambda Functions - ANC Platform

Serverless audio processing Lambda functions with shared utilities and Python 3.11 support.

## Overview

Lambda functions are organized with a common utilities package to eliminate code duplication:

```
lambda/
├── common/                    # Shared utilities package
│   ├── __init__.py
│   ├── boto_config.py        # AWS client factory
│   ├── redis_client.py       # Redis utilities
│   ├── encoding.py           # Audio codec
│   └── metrics.py            # CloudWatch metrics
├── anc_processor_v2/         # Main audio processing
├── audio_receiver/           # Audio input handler
├── audio_sender/             # WebSocket output
├── websocket_connect/        # Connection lifecycle
└── websocket_disconnect/     # Disconnection handling
```

## Shared Utilities Package

### Installation

The `common/` package is automatically included in Lambda deployments via:

```bash
# Method 1: Include in function ZIP
cd lambda/anc_processor_v2
pip install -r requirements.txt -t .
cp -r ../common .
zip -r ../anc_processor_v2.zip .

# Method 2: Use Lambda layer (Terraform managed)
# Terraform bundles common/ as a Lambda layer
```

### Modules

#### boto_config.py

AWS client factory with timeout configuration:

```python
from common import get_boto_config, get_aws_clients, get_required_env

# Get standard Boto3 configuration
config = get_boto_config(
    connect_timeout=2,
    read_timeout=10,
    max_retries=3
)

# Create multiple clients with standard config
clients = get_aws_clients(['sqs', 'dynamodb', 'cloudwatch'], config=config)
sqs = clients['sqs']
dynamodb = clients['dynamodb']
cloudwatch = clients['cloudwatch']

# Get environment variable (required)
redis_endpoint = get_required_env('REDIS_ENDPOINT')
```

#### redis_client.py

Redis connection pooling and caching utilities:

```python
from common import (
    get_redis_client,
    redis_cache_get,
    redis_cache_set,
    redis_cache_hgetall,
    redis_cache_hset
)

# Get or create Redis client (singleton per Lambda container)
redis = get_redis_client()

# Simple cache operations
redis_cache_set('session:123:filter', filter_state, ttl=3600)
state = redis_cache_get('session:123:filter')

# Hash operations (useful for filter state)
redis_cache_hset('filter:123', {
    'weights': weights_bytes,
    'buffer': buffer_bytes,
    'index': '42'
}, ttl=3600)

data = redis_cache_hgetall('filter:123')
```

#### encoding.py

Base64 audio encoding/decoding with validation:

```python
from common import (
    encode_audio,
    decode_audio,
    validate_audio_chunk
)

import numpy as np

# Decode incoming audio
audio_array = decode_audio(audio_base64, dtype=np.float32, num_channels=1)

# Validate audio
is_valid, error_msg = validate_audio_chunk(
    audio_array,
    max_size=4096,
    sample_rate=48000
)

if not is_valid:
    raise ValueError(error_msg)

# Process audio...

# Encode output
output_base64 = encode_audio(processed_audio, dtype=np.float32)
```

#### metrics.py

CloudWatch metrics publishing:

```python
from common import (
    publish_metrics,
    publish_metric,
    publish_processing_metrics,
    publish_latency_metrics,
    publish_error_metric
)

# Publish multiple metrics at once
publish_metrics(
    {
        'NoiseReductionDB': 25.3,
        'ProcessingTimeMs': 5.2,
        'ErrorPower': 0.001
    },
    namespace='ANC/Processing',
    dimensions={'SessionId': session_id, 'Environment': 'dev'}
)

# Publish single metric
publish_metric(
    'TotalLatency',
    42.5,
    namespace='ANC/Performance',
    unit='Milliseconds',
    dimensions={'Component': 'AudioReceiver'}
)

# Convenience functions
publish_processing_metrics(
    session_id,
    noise_reduction_db=25.3,
    processing_time_ms=5.2,
    error_power=0.001,
    num_samples=2048
)

publish_latency_metrics(42.5, 'AudioReceiver', 'process')

publish_error_metric('TimeoutError', 'AudioProcessor')
```

## Lambda Functions

### anc_processor_v2

Main audio processing Lambda with hybrid NLMS+RLS algorithm.

**Triggers**: SQS (from audio_receiver)

**Input**:
```json
{
  "Records": [{
    "body": {
      "sessionId": "session-uuid",
      "connectionId": "conn-xyz",
      "userId": "user-123",
      "audioData": "base64-encoded-float32",
      "timestamp": 1234567890,
      "numChannels": 1,
      "sampleRate": 48000
    }
  }]
}
```

**Output**: Sends to SQS output queue for audio_sender:
```json
{
  "sessionId": "session-uuid",
  "connectionId": "conn-xyz",
  "userId": "user-123",
  "audioData": "base64-processed-audio",
  "timestamp": 1234567890,
  "metrics": {
    "noise_reduction_db": 25.3,
    "processing_time_ms": 5.2,
    "error_power": 0.001,
    "noise_type": "traffic",
    "classification_confidence": 0.95
  }
}
```

**Environment Variables**:
- `REDIS_ENDPOINT`: ElastiCache Redis endpoint
- `REDIS_PORT`: Redis port (default: 6379)
- `OUTPUT_QUEUE_URL`: SQS queue for output
- `SAGEMAKER_ENDPOINT`: SageMaker noise classifier
- `ALGORITHM`: Processing algorithm (default: hybrid_nlms_rls)
- `FILTER_LENGTH`: Filter length (default: 512)
- `SAMPLE_RATE`: Sample rate (default: 48000)
- `ENABLE_SPATIAL_AUDIO`: Enable spatial processing (default: false)
- `ENABLE_ADAPTIVE_LEARNING`: Enable adaptive tuning (default: true)
- `LOG_LEVEL`: Logging level (default: INFO)

### audio_receiver

Validates and queues incoming audio chunks from WebSocket clients.

**Triggers**: API Gateway WebSocket (audioChunk route)

**Input** (from WebSocket):
```json
{
  "sessionId": "session-uuid",
  "audioData": "base64-float32",
  "timestamp": 1234567890,
  "sampleRate": 48000
}
```

**Output**: Sends to SQS audio queue for anc_processor_v2

**Environment Variables**:
- `AUDIO_QUEUE_URL`: SQS queue URL for audio input
- `SESSIONS_TABLE`: DynamoDB sessions table
- `CONNECTIONS_TABLE`: DynamoDB connections table

### audio_sender

Sends processed audio back to connected WebSocket clients.

**Triggers**: SQS (from anc_processor_v2)

**Input** (from SQS):
```json
{
  "sessionId": "session-uuid",
  "connectionId": "conn-xyz",
  "audioData": "base64-processed",
  "metrics": { ... },
  "timestamp": 1234567890
}
```

**Output**: WebSocket message to client

**Environment Variables**:
- `WEBSOCKET_ENDPOINT`: API Gateway Management API endpoint
- `CONNECTIONS_TABLE`: DynamoDB connections table

### websocket_connect

Handles WebSocket $connect route with JWT validation.

**Triggers**: API Gateway WebSocket ($connect route)

**Event**:
```json
{
  "requestContext": {
    "connectionId": "abc123",
    "routeKey": "$connect"
  },
  "queryStringParameters": {
    "token": "jwt-token"
  }
}
```

**Environment Variables**:
- `CONNECTIONS_TABLE`: DynamoDB connections table
- `JWT_SECRET`: JWT signing secret
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_ISSUER`: Expected token issuer (optional)

### websocket_disconnect

Handles WebSocket $disconnect route for cleanup.

**Triggers**: API Gateway WebSocket ($disconnect route)

**Environment Variables**:
- `CONNECTIONS_TABLE`: DynamoDB connections table

## Packaging

### Individual Function

```bash
cd lambda/anc_processor_v2

# Install dependencies
pip install -r requirements.txt -t .

# Copy common utilities
cp -r ../common .

# Create deployment package
zip -r ../anc_processor_v2.zip . \
  --exclude="tests/*" "__pycache__/*" "*.pyc"

# Upload to S3
aws s3 cp ../anc_processor_v2.zip s3://anc-lambda-code/anc_processor_v2.zip
```

### All Functions (Batch)

```bash
#!/bin/bash
cd lambda/

for dir in anc_processor_v2 audio_receiver audio_sender websocket_connect websocket_disconnect; do
  cd "$dir"
  
  # Clean previous build
  find . -type d -name __pycache__ -exec rm -rf {} +
  find . -name "*.pyc" -delete
  rm -rf common
  
  # Install dependencies
  pip install -r requirements.txt -t . --quiet
  
  # Copy common utilities
  cp -r ../common .
  
  # Create ZIP
  zip -q -r "../${dir}.zip" . -x "tests/*" "__pycache__/*" "*.pyc"
  
  # Upload
  aws s3 cp "../${dir}.zip" "s3://anc-lambda-code/${dir}.zip"
  
  cd ..
done
```

### Lambda Layer (Recommended)

Create a layer containing common utilities and shared dependencies:

```bash
# Directory structure for layer
lambda-layer/
└── python/
    └── lib/
        └── python3.11/
            └── site-packages/
                ├── common/
                │   ├── __init__.py
                │   ├── boto_config.py
                │   ├── redis_client.py
                │   ├── encoding.py
                │   └── metrics.py
                ├── numpy/
                ├── redis/
                └── ... other shared deps

# Create layer ZIP
cd lambda-layer
zip -r ../lambda-common-layer.zip .

# Publish layer (Terraform handles this)
aws lambda publish-layer-version \
  --layer-name anc-common-layer \
  --zip-file fileb://../lambda-common-layer.zip \
  --compatible-runtimes python3.11
```

## Local Testing

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r ../requirements.txt

# Set up environment
export REDIS_ENDPOINT=localhost
export REDIS_PORT=6379
export SESSIONS_TABLE=sessions-local
export CONNECTIONS_TABLE=connections-local
export AUDIO_QUEUE_URL=http://localhost:9324/queue/audio-local
export OUTPUT_QUEUE_URL=http://localhost:9324/queue/output-local
```

### Test with LocalStack

Run AWS services locally for testing:

```bash
# Start LocalStack container
docker-compose -f docker-compose.localstack.yml up -d

# Run Lambda handler locally
python -c "
import json
from handler import lambda_handler

event = {
    'Records': [{
        'body': json.dumps({
            'sessionId': 'test-session',
            'connectionId': 'test-conn',
            'audioData': '...',  # base64 audio
            'timestamp': 1234567890
        })
    }]
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
"
```

### Unit Tests

```bash
# Run tests for a function
cd lambda/anc_processor_v2
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## Environment Configuration

### Development

```bash
cd terraform/environments/dev
terraform output -json | jq '
{
  REDIS_ENDPOINT: .redis_endpoint.value,
  SESSIONS_TABLE: .sessions_table.value,
  AUDIO_QUEUE_URL: .audio_queue_url.value,
  ...
}' > lambda-env.json
```

### Production

```bash
cd terraform/environments/prod
terraform output -json > ../../../config/lambda-env-prod.json
```

Pass environment to Lambda via Terraform:

```hcl
environment {
  variables = {
    REDIS_ENDPOINT = module.elasticache.redis_endpoint
    REDIS_PORT     = 6379
    SESSIONS_TABLE = module.dynamodb.sessions_table_name
    # ... other variables
  }
}
```

## Performance Optimization

### Cold Start Minimization

1. **Module-level initialization**:
   ```python
   # Initialized once per container, reused across invocations
   redis = get_redis_client()
   
   def handler(event, context):
       # Uses pre-initialized client
       redis_cache_get('key')
   ```

2. **Memory allocation**:
   - Minimum: 512 MB
   - Recommended: 1024 MB (balances cost and cold start)
   - Use 3008 MB for ML inference (full CPU allocation)

3. **Provisioned concurrency** (production):
   ```hcl
   provisioned_concurrent_executions = 10
   ```

4. **Lambda layers**:
   - Common utilities in layer (reused across functions)
   - Reduces function package size
   - Faster cold starts

### Concurrency

- **Reserved concurrency** (production): 100-500
- **Provisioned concurrency**: 10-50 per function
- **Timeout**: 30s for audio processing, 10s for WebSocket handlers

## Monitoring

### CloudWatch Logs

View function logs:

```bash
# Stream logs in real-time
aws logs tail /aws/lambda/anc_processor_v2 --follow

# Get specific invocation logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/
aws logs filter-log-events \
  --log-group-name /aws/lambda/anc_processor_v2 \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s%N)/1000000 - 3600000))
```

### Custom Metrics

All functions publish custom metrics to CloudWatch:

```bash
# View metric statistics
aws cloudwatch get-metric-statistics \
  --namespace ANC/Processing \
  --metric-name NoiseReductionDB \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average,Maximum,Minimum
```

### X-Ray Tracing

Enable X-Ray in Terraform:

```hcl
tracing_config {
  mode = "Active"
}
```

View traces:

```bash
aws xray get-service-graph --start-time 2024-01-01T00:00:00Z
```

## Troubleshooting

### Cold Starts

Symptoms: First invocation slow, subsequent fast

Solutions:
1. Increase memory allocation
2. Use provisioned concurrency
3. Use Lambda layer for common code
4. Optimize imports (lazy load if possible)

### Timeout Errors

Symptoms: Lambda execution aborts with "Task timed out"

Solutions:
1. Increase function timeout (default 30s)
2. Optimize code (profile with cProfile)
3. Reduce input data size
4. Use async processing (SNS/SQS)

### Redis Connection Issues

Symptoms: "Connection refused" or "timeout"

Solutions:
```bash
# Check security groups
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx

# Test Redis connection
redis-cli -h $REDIS_ENDPOINT -p 6379 ping

# Check Lambda VPC configuration
aws lambda get-function-concurrency --function-name anc_processor_v2
```

### Out of Memory

Symptoms: "Process terminated. Killed"

Solutions:
1. Increase function memory
2. Reduce batch size
3. Profile code for memory leaks
4. Stream large inputs instead of loading all

## Deployment

### Via Terraform

```bash
cd terraform/environments/dev
terraform apply
```

Terraform will:
1. Create Lambda functions from ZIP files
2. Configure environment variables
3. Set up event sources (SQS, API Gateway)
4. Create IAM roles and permissions
5. Enable CloudWatch logs and X-Ray

### Via AWS CLI

```bash
# Create function
aws lambda create-function \
  --function-name anc_processor_v2 \
  --runtime python3.11 \
  --role arn:aws:iam::123456789:role/lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://anc_processor_v2.zip \
  --timeout 30 \
  --memory-size 1024 \
  --environment Variables='{REDIS_ENDPOINT=...}'

# Update function code
aws lambda update-function-code \
  --function-name anc_processor_v2 \
  --zip-file fileb://anc_processor_v2.zip
```

## References

- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Lambda Performance Optimization](https://aws.amazon.com/blogs/compute/operating-lambda-performance-optimization-part-1/)
- [Python Runtime Guide](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
- [CloudWatch Logs Insights Queries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
