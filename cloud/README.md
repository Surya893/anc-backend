# ANC Platform - AWS Cloud Infrastructure

Complete cloud infrastructure for real-time Active Noise Cancellation processing on AWS.

## Architecture

This infrastructure processes incoming audio in real-time, applies phase-inverted signals for noise cancellation, and streams processed audio back to clients with <40ms total latency.

### Key Features

- ✅ **Real-time Audio Processing**: WebSocket-based streaming with <10ms cloud latency
- ✅ **NLMS Adaptive Filtering**: Cloud-based implementation of Normalized Least Mean Squares algorithm
- ✅ **Phase Inversion**: Generate anti-noise signals in real-time
- ✅ **ML Classification**: Identify noise types for adaptive ANC (95.83% accuracy)
- ✅ **Auto-Scaling**: Handle 1000+ concurrent audio streams
- ✅ **Cost-Optimized**: Serverless architecture with spot instances
- ✅ **Production-Ready**: Monitoring, logging, and alerting built-in

## Components

### Compute Layer
- **Lambda Functions**: Serverless audio processing
  - `audio_receiver`: Receive and validate incoming audio chunks
  - `anc_processor`: Apply NLMS filtering and phase inversion
  - `audio_sender`: Stream processed audio back to clients
  - `websocket_connect/disconnect`: Connection management

- **SageMaker**: ML model for noise classification
- **ECS Fargate**: Heavy processing tasks (batch jobs)

### Storage Layer
- **S3**: Raw and processed audio files
- **RDS PostgreSQL**: User data, analytics, audit logs
- **DynamoDB**: Real-time session state
- **ElastiCache Redis**: Filter coefficients cache

### API Layer
- **API Gateway REST**: HTTP endpoints for uploads/downloads
- **API Gateway WebSocket**: Real-time bidirectional audio streaming
- **CloudFront**: Global CDN for low-latency access

### IoT & Device Management
- **AWS IoT Core**: Device connectivity and messaging
- **Device Shadow**: State synchronization between devices and cloud
- **IoT Rules Engine**: Data routing and transformation
- **IoT Analytics**: Device telemetry analytics

### Monitoring Layer
- **CloudWatch**: Logs, metrics, dashboards
- **X-Ray**: Distributed tracing
- **SNS**: Alerts and notifications

## Prerequisites

### Required Tools

```bash
# Terraform
brew install terraform  # macOS
# or
sudo apt install terraform  # Linux

# AWS CLI
brew install awscli  # macOS
# or
pip install awscli

# Python 3.11+
python3 --version
```

### AWS Account Setup

1. **Create AWS Account** (if needed)
   - Sign up at https://aws.amazon.com/
   - Get $100 free credits for startups: https://aws.amazon.com/activate/

2. **Configure AWS Credentials**
   ```bash
   aws configure
   # AWS Access Key ID: <your-access-key>
   # AWS Secret Access Key: <your-secret-key>
   # Default region: us-east-1
   # Default output format: json
   ```

3. **Verify Credentials**
   ```bash
   aws sts get-caller-identity
   ```

## Deployment

### Quick Start (Automated)

```bash
# Clone repository
cd cloud/

# Run automated deployment
./deploy.sh
```

The script will:
1. Check prerequisites
2. Create Terraform backend (S3 + DynamoDB)
3. Package Lambda functions
4. Upload ML model to S3
5. Initialize Terraform
6. Deploy infrastructure
7. Configure monitoring

### Manual Deployment

#### Step 1: Setup Terraform Backend

```bash
# Create S3 bucket for state
aws s3 mb s3://anc-platform-terraform-state-<account-id>
aws s3api put-bucket-versioning \
  --bucket anc-platform-terraform-state-<account-id> \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

#### Step 2: Package Lambda Functions

```bash
cd lambda/

# For each Lambda function
for dir in */; do
  cd "$dir"
  pip install -r requirements.txt -t .
  zip -r "../$(basename $dir).zip" .
  cd ..
done
```

#### Step 3: Configure Terraform

```bash
cd terraform/

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
aws_region  = "us-east-1"
environment = "production"
db_password = "your-secure-password"
alarm_email = "your-email@example.com"
sagemaker_model_url = "s3://bucket/model.tar.gz"
EOF
```

#### Step 4: Deploy

```bash
# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

## Cost Estimation

### Free Tier (First Year)

Using AWS Free Tier, expected cost: **$0-$20/month**

- Lambda: 1M free requests/month
- API Gateway: 1M free API calls/month
- S3: 5GB free storage
- RDS: 750 hours of db.t3.micro free
- CloudWatch: 10 free custom metrics

### Production (1000 concurrent users)

Expected monthly cost: **~$485/month**

| Service | Cost/Month |
|---------|------------|
| Lambda (10M invocations) | $50 |
| API Gateway | $35 |
| S3 (1TB storage + transfer) | $20 |
| RDS (db.t3.medium, Multi-AZ) | $120 |
| ElastiCache (3 nodes) | $80 |
| SageMaker endpoint | $100 |
| Data transfer | $50 |
| CloudWatch | $30 |
| **Total** | **$485** |

### Cost Optimization Tips

1. **Use Spot Instances**: 70% discount for batch processing
2. **Enable Auto-Scaling**: Scale down during low usage
3. **S3 Lifecycle Policies**: Auto-archive to Glacier
4. **Reserved Capacity**: 40-60% discount for RDS (1-year commitment)
5. **Lambda Power Tuning**: Optimize memory/cost ratio

## Testing

### Health Check

```bash
# Get API URL from Terraform outputs
API_URL=$(terraform output -raw api_gateway_rest_url)

# Test health endpoint
curl ${API_URL}/health
```

### WebSocket Connection

```javascript
// Test WebSocket connection
const ws = new WebSocket('wss://your-websocket-url');

ws.onopen = () => {
  console.log('Connected');

  // Start streaming
  ws.send(JSON.stringify({
    action: 'startStream',
    config: {
      sampleRate: 48000,
      ancEnabled: true,
      ancIntensity: 1.0
    }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data.type);

  if (data.type === 'processedChunk') {
    // Play processed audio
    const audioData = atob(data.audioData);
    // ... decode and play
  }
};
```

### Load Testing

```bash
# Install artillery
npm install -g artillery

# Run load test
artillery run tests/load-test.yml
```

## Monitoring

### CloudWatch Dashboards

Access dashboards at:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

**Key Metrics**:
- WebSocket connections (active, new, closed)
- Lambda invocations and errors
- Processing latency (p50, p95, p99)
- SageMaker endpoint requests
- Cost metrics

### Alarms

Pre-configured alarms will notify via SNS when:
- Processing latency > 500ms (p95)
- Error rate > 1%
- SQS queue depth > 1000
- Daily cost > $100

### Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/anc-processor --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/anc-processor \
  --filter-pattern "ERROR"
```

## ML Model

### Training

```bash
# Train noise classification model
cd ../ml/

python train_model.py \
  --data s3://bucket/datasets/ \
  --output s3://bucket/models/

# Deploy to SageMaker
python deploy_model.py \
  --model-url s3://bucket/models/model.tar.gz \
  --instance-type ml.t3.medium
```

### Inference

```python
import boto3
import json

runtime = boto3.client('sagemaker-runtime')

# Extract audio features
features = extract_mfcc_features(audio_data)

# Call SageMaker endpoint
response = runtime.invoke_endpoint(
    EndpointName='noise-classifier-endpoint',
    Body=json.dumps({'instances': [features]}),
    ContentType='application/json'
)

result = json.loads(response['Body'].read())
noise_type = result['predictions'][0]['class']
confidence = result['predictions'][0]['confidence']

print(f"Detected: {noise_type} ({confidence:.2%})")
```

## Troubleshooting

### Issue: Lambda Timeout

**Solution**: Increase memory allocation or timeout
```bash
aws lambda update-function-configuration \
  --function-name anc-processor \
  --timeout 30 \
  --memory-size 1024
```

### Issue: High Latency

**Solutions**:
1. Check ElastiCache hit rate - increase cache size if needed
2. Enable Lambda SnapStart for faster cold starts
3. Use provisioned concurrency for Lambda
4. Optimize filter coefficient serialization

### Issue: Cost Too High

**Solutions**:
1. Enable auto-scaling down during low usage
2. Use Spot instances for batch processing
3. Reduce SageMaker endpoint size or use serverless inference
4. Implement S3 lifecycle policies

### Issue: WebSocket Disconnections

**Solutions**:
1. Increase API Gateway timeout (max 29 minutes)
2. Implement client-side reconnection logic
3. Use heartbeat messages to keep connection alive
4. Check Lambda concurrency limits

## Security

### Best Practices

1. **Encryption**
   - TLS 1.3 for data in transit
   - AES-256 for S3 data at rest
   - KMS for sensitive data

2. **Authentication**
   - JWT tokens for API access
   - API keys for programmatic access
   - IAM roles for service-to-service

3. **Network Security**
   - VPC with private subnets
   - Security groups with least privilege
   - AWS WAF for API Gateway

4. **Compliance**
   - Enable CloudTrail for audit logging
   - Encrypt PII with field-level encryption
   - GDPR: Implement data deletion policies

## Disaster Recovery

### Backup Strategy

- **RDS**: Automated daily backups, 7-day retention
- **DynamoDB**: Point-in-time recovery enabled
- **S3**: Versioning enabled, cross-region replication (optional)

### Recovery Procedures

```bash
# Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier anc-db-restored \
  --db-snapshot-identifier rds:anc-db-2024-01-01

# Restore DynamoDB table
aws dynamodb restore-table-from-backup \
  --target-table-name anc-sessions-restored \
  --backup-arn arn:aws:dynamodb:...
```

## Cleanup

### Destroy Infrastructure

```bash
cd terraform/

# Destroy all resources
terraform destroy

# Confirm destruction
# Type: yes
```

**Warning**: This will delete:
- All Lambda functions
- DynamoDB tables (and data)
- RDS databases (and data)
- S3 buckets (and data)
- CloudWatch logs

### Manual Cleanup

```bash
# Empty S3 buckets first
aws s3 rm s3://anc-platform-audio-raw --recursive
aws s3 rm s3://anc-platform-audio-processed --recursive

# Then run terraform destroy
terraform destroy
```

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

## License

Copyright (c) 2024 ANC Platform. All rights reserved.
