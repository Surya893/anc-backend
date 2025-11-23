# Cloud Layer

## Overview

This layer contains all AWS cloud infrastructure for the ANC Platform, including Lambda functions, IoT connectivity, and Infrastructure as Code (Terraform).

## Architecture

```
cloud/
├── lambda/                    # Lambda functions
│   ├── audio_receiver/        # Receive audio via API Gateway
│   ├── audio_sender/          # Send processed audio
│   ├── anc_processor/         # ANC processing v1
│   ├── anc_processor_v2/      # ANC processing v2
│   ├── websocket_connect/     # WebSocket connection handler
│   └── websocket_disconnect/  # WebSocket disconnect handler
├── lambda_edge/               # Lambda@Edge functions
│   └── anc_processor_edge.py  # Edge processing
├── iot/                       # AWS IoT Core integration
│   ├── iot_connection.py      # MQTT connection
│   ├── device_shadow_sync.py  # Device shadow management
│   ├── telemetry_publisher.py # Telemetry streaming
│   └── data_sync_orchestrator.py
├── webrtc/                    # WebRTC signaling
│   └── signaling_server.py
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Main infrastructure
│   ├── variables.tf          # Configuration variables
│   ├── outputs.tf            # Output values
│   └── modules/              # Reusable modules
└── README_LAYER.md           # This file
```

## Services

### 1. Lambda Functions

**audio_receiver**
- Receives audio data from API Gateway
- Validates and preprocesses audio
- Triggers ANC processor
- Returns session ID

**anc_processor / anc_processor_v2**
- Applies ANC algorithms (NLMS, LMS, RLS)
- Processes audio in cloud
- Stores results in S3/DynamoDB
- Publishes metrics to CloudWatch

**audio_sender**
- Retrieves processed audio
- Streams back to client
- Handles chunking and buffering

**websocket_connect / websocket_disconnect**
- Manages WebSocket connections
- Stores connection IDs in DynamoDB
- Handles authentication

### 2. IoT Core

**iot_connection.py**
- Establishes MQTT connection
- Certificate-based authentication
- Subscribes to device topics

**device_shadow_sync.py**
- Synchronizes device state
- Reports current settings
- Receives desired state updates

**telemetry_publisher.py**
- Publishes device telemetry
- Real-time metrics streaming
- Event notifications

**data_sync_orchestrator.py**
- Coordinates data flow
- Routes messages to Lambda
- Manages persistence

### 3. Terraform Infrastructure

**Main Resources:**
- API Gateway (REST + WebSocket)
- Lambda functions
- DynamoDB tables
- S3 buckets
- IoT Core things/certificates
- CloudWatch logs and alarms
- VPC and security groups
- IAM roles and policies

## Communication Flow

### Backend → Cloud

```
Backend API
    ↓ Invoke Lambda (via AWS SDK)
Cloud Lambda
    ↓ Process audio
    ↓ Store in S3/DynamoDB
    ↑ Return results
Backend API
```

### IoT Device → Cloud

```
IoT Device (Firmware)
    ↓ MQTT publish
IoT Core
    ↓ Route to Lambda
Lambda (anc_processor)
    ↓ Process
    ↓ Store results
    ↓ Publish to topic
    ↑ MQTT subscribe
IoT Device
```

### Frontend → Cloud (Direct)

```
Frontend
    ↓ HTTPS/WebSocket
API Gateway
    ↓ Trigger Lambda
Lambda
    ↓ Process
    ↑ Response
API Gateway
    ↑ Return
Frontend
```

## Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id

# IoT Configuration
IOT_ENDPOINT=your-iot-endpoint.amazonaws.com
IOT_CERT_PATH=/path/to/certificate.pem
IOT_KEY_PATH=/path/to/private.key
IOT_ROOT_CA_PATH=/path/to/root-ca.pem

# Lambda Configuration
LAMBDA_MEMORY=512
LAMBDA_TIMEOUT=30
LAMBDA_RUNTIME=python3.11

# S3 Configuration
S3_BUCKET_AUDIO=anc-audio-data
S3_BUCKET_MODELS=anc-ml-models

# DynamoDB Tables
DYNAMODB_SESSIONS=anc-sessions
DYNAMODB_METRICS=anc-metrics
DYNAMODB_CONNECTIONS=anc-websocket-connections
```

## Deployment

### Prerequisites

```bash
# Install AWS CLI
aws --version

# Install Terraform
terraform --version

# Configure AWS credentials
aws configure
```

### Deploy Infrastructure

```bash
cd cloud/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="environment=production" \
  -var="aws_region=us-east-1"

# Apply infrastructure
terraform apply -auto-approve

# Get outputs
terraform output
```

### Deploy Lambda Functions

```bash
cd cloud/lambda

# Package and deploy each function
for dir in */; do
  cd "$dir"

  # Install dependencies
  pip install -r requirements.txt -t package/

  # Copy function code
  cp *.py package/

  # Create deployment package
  cd package && zip -r ../function.zip . && cd ..

  # Deploy to Lambda
  aws lambda update-function-code \
    --function-name "anc-${dir%/}" \
    --zip-file fileb://function.zip

  cd ..
done
```

### Setup IoT Devices

```bash
# Create IoT thing
aws iot create-thing --thing-name anc-device-001

# Create and attach certificate
aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile device.cert.pem \
  --public-key-outfile device.public.key \
  --private-key-outfile device.private.key

# Attach policy to certificate
aws iot attach-policy \
  --policy-name anc-device-policy \
  --target <certificate-arn>

# Test connection
python iot/iot_connection.py \
  --endpoint <iot-endpoint> \
  --cert device.cert.pem \
  --key device.private.key
```

## Monitoring

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/anc-audio-receiver --follow

# View IoT logs
aws logs tail AWSIotLogsV2 --follow
```

### CloudWatch Metrics

```bash
# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=anc-audio-receiver \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### CloudWatch Alarms

Configured alarms:
- Lambda errors > 10/minute
- API Gateway 5xx errors > 5%
- IoT disconnections > 100/hour
- DynamoDB throttling

## Cost Optimization

1. **Lambda**
   - Use ARM64 architecture (20% cheaper)
   - Enable provisioned concurrency only for critical functions
   - Set appropriate memory and timeout

2. **API Gateway**
   - Use caching for frequently accessed data
   - Enable compression
   - Use WebSocket for streaming (cheaper than HTTP)

3. **S3**
   - Lifecycle policies to archive to Glacier
   - Use Intelligent-Tiering
   - Enable versioning only when needed

4. **DynamoDB**
   - Use on-demand pricing for variable workloads
   - Enable auto-scaling
   - Use DAX for caching

5. **IoT Core**
   - Batch messages when possible
   - Use device shadows to reduce messages
   - Compress payloads

## Security

1. **IAM Roles**
   - Least privilege principle
   - Separate roles per Lambda
   - No hardcoded credentials

2. **Encryption**
   - TLS 1.3 for all connections
   - X.509 certificates for IoT
   - KMS encryption for S3/DynamoDB

3. **VPC**
   - Lambda in private subnets
   - NAT Gateway for internet access
   - Security groups restrict traffic

4. **API Gateway**
   - API keys for authentication
   - Rate limiting
   - Request validation

## Disaster Recovery

1. **Backups**
   - DynamoDB point-in-time recovery
   - S3 versioning and replication
   - Lambda code in S3

2. **Multi-Region**
   - Deploy to multiple regions
   - Route53 for failover
   - Cross-region replication

3. **Monitoring**
   - CloudWatch alarms
   - SNS notifications
   - Automated recovery

## Links to Existing Documentation

For more details, see:
- `/cloud/AWS_ARCHITECTURE.md` - Complete architecture
- `/cloud/terraform/README.md` - Terraform details
- `/docs/deployment/PRODUCTION_DEPLOYMENT.md` - Production deployment
