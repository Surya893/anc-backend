# ANC Platform - AWS Cloud Infrastsructure

Complete cloud infrastructure for real-time Active Noise Cancellation processing on AWS.

## Architecture Overview

This infrastructure processes incoming audio in real-time, applies phase-inverted signals for noise cancellation, and streams processed audio back to clients with <40ms total latency.

### Key Features

- ✅ **Real-time Audio Processing**: WebSocket-based streaming with <10ms cloud latency
- ✅ **Hybrid NLMS+RLS Filtering**: Cloud-based adaptive noise cancellation algorithm
- ✅ **Phase Inversion**: Generate anti-noise signals in real-time
- ✅ **ML Classification**: Identify noise types for adaptive ANC (50+ noise categories)
- ✅ **Emergency Detection**: Automatic detection and alerting for emergency sounds
- ✅ **Auto-Scaling**: Handle 1000+ concurrent audio streams
- ✅ **Cost-Optimized**: Serverless architecture with intelligent instance selection
- ✅ **Production-Ready**: Monitoring, logging, alerting, and distributed tracing

## Infrastructure Components

### Compute Layer
- **Lambda Functions**: Serverless audio processing (Python 3.11)
  - `audio_receiver`: Receive and validate incoming audio chunks
  - `anc_processor_v2`: Apply hybrid NLMS+RLS filtering and phase inversion
  - `audio_sender`: Stream processed audio back to clients via WebSocket
  - `websocket_connect/disconnect`: WebSocket connection lifecycle management
  - Common helpers: Shared utilities for Redis, metrics, audio encoding

- **SageMaker**: ML endpoint for noise classification (50+ noise types)
- **ECS Fargate**: Batch processing and heavy ML jobs (optional)

### Storage Layer
- **S3 Buckets**: Raw and processed audio files with lifecycle policies
- **RDS PostgreSQL**: User data, session analytics, audit logs (Multi-AZ in production)
- **DynamoDB**: Real-time session state and connection management (auto-scaling)
- **ElastiCache Redis**: Filter coefficients cache and session state (Redis cluster)

### API Layer
- **API Gateway REST**: HTTP endpoints for metadata, session management, analytics
- **API Gateway WebSocket**: Real-time bidirectional audio streaming
- **CloudFront CDN**: Global edge locations for low-latency access

### IoT & Device Management
- **AWS IoT Core**: Device connectivity and secure messaging
- **Device Shadow**: State synchronization between edge devices and cloud
- **IoT Rules Engine**: Data routing and transformation to DynamoDB/S3
- **IoT Analytics**: Device telemetry and anomaly detection

### Monitoring & Observability
- **CloudWatch**: Logs, metrics, dashboards, and alarms
- **X-Ray**: Distributed tracing for end-to-end latency analysis
- **SNS**: Real-time alerts and notifications
- **Custom Metrics**: Processing latency, cancellation performance, error rates

## Directory Structure

```
cloud/
├── terraform/                    # Terraform Infrastructure as Code
│   ├── environments/
│   │   ├── dev/                 # Development environment
│   │   │   ├── main.tf          # Dev infrastructure
│   │   │   └── variables.tf     # Dev-specific variables
│   │   └── prod/                # Production environment
│   │       ├── main.tf          # Production infrastructure
│   │       └── variables.tf     # Production-specific variables
│   ├── modules/                 # Reusable Terraform modules
│   ├── archives/                # Legacy configurations
│   ├── terraform.tfvars.example # Variable template
│   └── README.md               # Detailed Terraform guide
├── lambda/                       # Lambda function source code
│   ├── common/                  # Shared utilities package
│   │   ├── __init__.py
│   │   ├── boto_config.py      # AWS client factory
│   │   ├── redis_client.py     # Redis cache utilities
│   │   ├── encoding.py         # Audio encoding/decoding
│   │   └── metrics.py          # CloudWatch metrics publishing
│   ├── anc_processor_v2/        # Main audio processing Lambda
│   │   ├── handler.py          # Hybrid NLMS+RLS implementation
│   │   └── requirements.txt
│   ├── audio_receiver/          # Audio input validation Lambda
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── audio_sender/            # WebSocket output Lambda
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── websocket_connect/       # WebSocket connect handler
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── websocket_disconnect/    # WebSocket disconnect handler
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── README.md               # Lambda deployment guide
├── iot/                         # AWS IoT Core configuration
│   ├── policies/
│   ├── rules/
│   └── README.md
├── docker/                      # Docker/OCI configurations
│   └── Dockerfile              # Multi-stage build
├── deploy.sh                    # Automated deployment script
├── AWS_ARCHITECTURE.md         # High-level architecture docs
├── ARCHITECTURE_REFINEMENTS.md # Technical design decisions
├── IMPLEMENTATION_SUMMARY.md   # Implementation details
├── README_LAYER.md             # Lambda layer guide
└── README.md                   # This file
```

## Quick Start

### Prerequisites

1. **Install Tools**
   ```bash
   # Terraform v1.0+
   terraform version
   
   # AWS CLI v2
   aws --version
   
   # Python 3.11+
   python3 --version
   
   # Docker (for local testing)
   docker --version
   ```

2. **Configure AWS Credentials**
   ```bash
   aws configure
   # Enter Access Key ID, Secret Key, region (us-east-1), output format (json)
   
   # Verify access
   aws sts get-caller-identity
   ```

### Deploy to Development

```bash
# Navigate to dev environment
cd terraform/environments/dev

# Create and edit configuration
cp ../../../terraform.tfvars.example terraform.tfvars
vi terraform.tfvars  # Update values for your environment

# Initialize and deploy
terraform init
terraform validate
terraform plan
terraform apply

# Show outputs (needed for application configuration)
terraform output -json > config.json
```

### Deploy to Production

```bash
# Same as dev, but use prod environment
cd terraform/environments/prod

# Copy and customize configuration
cp ../../../terraform.tfvars.example terraform.tfvars
vi terraform.tfvars  # Use production-grade values

# Review plan carefully before applying to production
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## Lambda Function Deployment

### Architecture

Lambda functions share common utilities through the `lambda/common/` package:

```python
# Lambda handlers import shared utilities
from common import get_redis_client, encode_audio, publish_metrics

# No more duplicated code across handlers!
```

### Shared Utilities

- **boto_config.py**: AWS client factory with timeout configuration
- **redis_client.py**: Redis connection pooling and caching
- **encoding.py**: Base64 audio encoding/decoding with validation
- **metrics.py**: CloudWatch metrics publishing with batching

### Packaging Lambda Functions

```bash
cd lambda/

# Create deployment package for a function
cd anc_processor_v2
pip install -r requirements.txt -t .
zip -r ../anc_processor_v2.zip . \
  --exclude="tests/*" "__pycache__/*" "*.pyc"
cd ..

# Upload to S3 (Terraform will reference)
aws s3 cp anc_processor_v2.zip s3://anc-lambda-code/
```

### Environment Variables

Lambda functions receive configuration via environment variables (set by Terraform):

```
# Redis
REDIS_ENDPOINT=elasticache.domain.com
REDIS_PORT=6379
REDIS_PASSWORD=<from Secrets Manager>

# DynamoDB
SESSIONS_TABLE=anc-sessions
CONNECTIONS_TABLE=anc-connections

# SQS
AUDIO_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../audio-queue
OUTPUT_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../output-queue

# S3
RAW_AUDIO_BUCKET=anc-raw-audio-<env>
PROCESSED_AUDIO_BUCKET=anc-processed-audio-<env>

# SageMaker
SAGEMAKER_ENDPOINT=anc-noise-classifier-<env>

# Algorithms
ALGORITHM=hybrid_nlms_rls
FILTER_LENGTH=512
SAMPLE_RATE=48000
ENABLE_SPATIAL_AUDIO=true
ENABLE_ADAPTIVE_LEARNING=true

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=dev|prod
```

### Cold Start Optimization

Lambda handlers initialize AWS clients at module level (outside handler function):

```python
# Initialized once per Lambda container, reused across invocations
redis_client = get_redis_client()
cloudwatch = get_aws_clients(['cloudwatch'])

def lambda_handler(event, context):
    # Fast access to pre-initialized clients
    metrics = publish_metrics({...}, redis_client=redis_client)
```

## Docker & Kubernetes

### Docker

The `Dockerfile` uses multi-stage builds for minimal image size:

```dockerfile
# Stage 1: Build - compile dependencies
# Stage 2: Runtime - include only necessary files
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "4", ...]
```

Build and run locally:

```bash
# Build image
docker build -t anc-system:latest .

# Run with docker-compose
docker-compose up -d
```

### Kubernetes

Deploy to Kubernetes cluster:

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets from Terraform outputs
kubectl create secret generic anc-secrets \
  --from-literal=database_url=$RDS_ENDPOINT \
  --from-literal=jwt_secret=$JWT_SECRET \
  -n anc-platform

# Create ConfigMap from Terraform outputs
kubectl create configmap anc-config \
  --from-literal=redis_endpoint=$REDIS_ENDPOINT \
  --from-literal=sessions_table=$SESSIONS_TABLE \
  -n anc-platform

# Deploy application
kubectl apply -f k8s/
```

Environment variables in K8s manifests reference ConfigMaps (non-sensitive) and Secrets (sensitive data).

## Terraform State Management

### S3 Backend Configuration

State is stored in S3 with encryption and DynamoDB locking:

```hcl
backend "s3" {
  bucket         = "anc-platform-terraform-state"
  key            = "dev/terraform.tfstate"      # dev or prod
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-lock"
}
```

### First-Time Setup

```bash
# Create state bucket
aws s3api create-bucket \
  --bucket anc-platform-terraform-state \
  --region us-east-1

# Enable versioning and encryption
aws s3api put-bucket-versioning \
  --bucket anc-platform-terraform-state \
  --versioning-configuration Status=Enabled

# Create lock table
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1
```

## Environment Comparison

| Feature | Dev | Production |
|---------|-----|------------|
| **Availability** | Single-AZ | Multi-AZ |
| **RDS Instance** | db.t3.micro | db.t3.large |
| **RDS Storage** | 20GB | 200GB |
| **RDS Multi-AZ** | No | Yes |
| **Redis Node** | cache.t3.micro | cache.r6g.xlarge |
| **Redis Nodes** | 1 | 3 |
| **SageMaker Instance** | ml.t3.medium (1) | ml.m5.xlarge (2) |
| **Spot Instances** | Enabled | Disabled |
| **Auto-Scaling** | Disabled | Enabled |
| **CloudFront** | Optional | Required |
| **WAF** | Optional | Required |

## Outputs

After deployment, Terraform exposes these outputs for application configuration:

```bash
terraform output -json
```

Key outputs:
- `api_gateway_rest_url`: REST API endpoint
- `api_gateway_websocket_url`: WebSocket endpoint
- `redis_endpoint`: ElastiCache endpoint
- `rds_endpoint`: PostgreSQL endpoint
- `sessions_table`: DynamoDB table name
- `audio_queue_url`: SQS input queue
- `output_queue_url`: SQS output queue

## Monitoring & Observability

### CloudWatch Dashboards

Custom dashboards aggregate metrics from:
- Lambda execution metrics (duration, errors, throttles)
- Audio processing metrics (cancellation dB, latency, samples)
- Database performance (queries, connections, replication lag)
- API Gateway (requests, latency, 4xx/5xx errors)

### Custom Metrics

Published to CloudWatch namespaces:
- `ANC/Processing`: NoiseReductionDB, ProcessingTimeMs, ErrorPower
- `ANC/Performance`: Latency, Throughput
- `ANC/Errors`: ErrorCount, ValidationErrors
- `ANC/Lambda`: AudioChunksProcessed, AudioSampleReceived

### Alarms

SNS topics alert on:
- Lambda errors or throttling
- Database failover or high latency
- API Gateway errors
- Redis evictions or connection issues

## Troubleshooting

### Lambda Cold Starts

Reduce impact with:
1. Provisioned concurrency (production)
2. Lambda layers for shared code
3. Right-sizing memory allocation
4. Regular invocation (keep warm)

### Redis Connection Issues

```bash
# Test Redis connectivity
aws elasticache describe-cache-clusters

# Check security groups
aws ec2 describe-security-groups \
  --filters Name=group-name,Values=anc-elasticache-sg

# View logs
kubectl logs -n anc-platform -l app=anc-api | grep redis
```

### Database Performance

```bash
# Check RDS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=anc-db-prod \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

## Cost Optimization

1. **Development**: Use spot instances, smaller instance sizes, single-AZ
2. **Production**: Reserve instances, appropriate sizing, multi-AZ for HA
3. **S3 Lifecycle**: Archive old audio to Glacier after 90 days
4. **Lambda**: Monitor memory usage, adjust allocation
5. **RDS**: Use read replicas for analytics queries
6. **CloudFront**: Cache API responses where appropriate

## Security Best Practices

1. **Secrets Management**: Use AWS Secrets Manager for passwords
2. **IAM Roles**: Least privilege access for Lambda, EC2, RDS
3. **VPC**: Private subnets for databases, Lambda in VPC
4. **Encryption**: Enable RDS encryption, S3 bucket encryption
5. **Monitoring**: CloudTrail for API auditing, VPC Flow Logs
6. **WAF**: Rate limiting and SQL injection protection

## Terraform Organization Guide

### Directory Structure

The Terraform configuration has been reorganized for modularity and maintainability:

```
cloud/terraform/
├── main.tf                      # Main provider and resource definitions
├── variables.tf                 # Input variables and default values
├── outputs.tf                   # Output values for cross-stack reference
├── terraform.tfvars             # Environment-specific variable values
│
├── modules/                     # Reusable Terraform modules
│   ├── api_gateway/            # API Gateway REST + WebSocket setup
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── lambda/                 # Lambda functions
│   │   ├── audio_processor/
│   │   ├── audio_receiver/
│   │   ├── audio_sender/
│   │   └── websocket_handlers/
│   ├── iot/                    # IoT Core and Device Shadow
│   │   ├── main.tf
│   │   └── variables.tf
│   ├── database/               # RDS PostgreSQL configuration
│   │   ├── main.tf
│   │   └── variables.tf
│   ├── storage/                # S3, DynamoDB, ElastiCache
│   │   ├── main.tf
│   │   └── variables.tf
│   └── monitoring/             # CloudWatch, X-Ray setup
│       ├── main.tf
│       └── variables.tf
│
└── environments/                # Environment-specific configs
    ├── dev/
    │   └── terraform.tfvars
    ├── staging/
    │   └── terraform.tfvars
    └── prod/
        └── terraform.tfvars
```

### Using Modules

To use the reorganized modules:

```bash
cd cloud/terraform/

# Deploy to development environment
terraform init -backend-config="environments/dev/backend.tf"
terraform plan -var-file="environments/dev/terraform.tfvars"
terraform apply -var-file="environments/dev/terraform.tfvars"

# Or for production (requires additional approvals)
terraform plan -var-file="environments/prod/terraform.tfvars"
terraform apply -var-file="environments/prod/terraform.tfvars"
```

### Module Documentation

Each module is self-contained with its own documentation. Example:

```
cloud/terraform/modules/api_gateway/
├── README.md                    # Module-specific documentation
├── main.tf                      # Resource definitions
├── variables.tf                 # Input variables
└── outputs.tf                   # Output values
```

To view module variables:
```bash
cd cloud/terraform
terraform providers
terraform init
terraform validate
```

### Adding New Modules

Create a new module for additional infrastructure:

```bash
# Create module directory
mkdir -p cloud/terraform/modules/my-service

# Create standard files
touch cloud/terraform/modules/my-service/{main,variables,outputs}.tf
touch cloud/terraform/modules/my-service/README.md

# Reference in main terraform config
# main.tf:
module "my_service" {
  source = "./modules/my-service"
  
  # Pass variables
  environment = var.environment
}
```

## Support

- **Documentation**: [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)
- **Terraform Registry**: https://registry.terraform.io/
- **Issues**: Create GitHub issue
- **Email**: support@anc-platform.com

## Support

For issues or questions:
1. Check CloudWatch logs: `aws logs tail /aws/lambda/<function-name> --follow`
2. Review CloudWatch metrics: AWS Console → CloudWatch → Dashboards
3. Check AWS service health: https://status.aws.amazon.com/
4. Consult detailed architecture docs in `/docs` directory
