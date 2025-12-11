# ANC Platform - Terraform Infrastructure as Code

Unified Infrastructure as Code for deploying ANC Platform to AWS with environment-specific configurations.

## Directory Structure

```
terraform/
├── environments/
│   ├── dev/                 # Development environment configuration
│   │   ├── main.tf         # Dev infrastructure definition
│   │   └── variables.tf    # Dev-specific variables
│   └── prod/               # Production environment configuration
│       ├── main.tf         # Production infrastructure definition
│       └── variables.tf    # Production-specific variables
├── modules/                # Reusable Terraform modules
│   ├── vpc/
│   ├── s3/
│   ├── dynamodb/
│   ├── elasticache/
│   ├── rds/
│   ├── lambda/
│   ├── api_gateway_rest/
│   ├── api_gateway_websocket/
│   ├── sqs/
│   ├── sagemaker/
│   ├── cloudwatch/
│   ├── cloudfront/
│   ├── iam/
│   └── waf/
├── archives/               # Legacy/deprecated configurations
├── terraform.tfvars.example # Variable template
└── README.md             # This file
```

## Quick Start

### Prerequisites

1. **Install Terraform** (v1.0+)
   ```bash
   terraform version
   ```

2. **Configure AWS Credentials**
   ```bash
   aws configure
   # Enter AWS Access Key ID
   # Enter AWS Secret Access Key
   # Default region: us-east-1
   # Default output: json
   ```

3. **Verify AWS Access**
   ```bash
   aws sts get-caller-identity
   ```

### Deploy Development Environment

```bash
# Navigate to dev environment
cd cloud/terraform/environments/dev

# Create terraform.tfvars from template
cp ../../../terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your dev values
vi terraform.tfvars

# Initialize Terraform (downloads modules and configures backend)
terraform init

# Validate configuration
terraform validate

# Preview changes
terraform plan

# Apply infrastructure
terraform apply
```

### Deploy Production Environment

```bash
# Navigate to prod environment
cd cloud/terraform/environments/prod

# Create terraform.tfvars from template
cp ../../../terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your production values
vi terraform.tfvars

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Preview changes (review carefully!)
terraform plan -out=tfplan

# Apply infrastructure (requires approval)
terraform apply tfplan
```

## Configuration

### terraform.tfvars Variables

Key variables to configure for your environment:

```hcl
# General
aws_region = "us-east-1"
environment = "dev"  # or "production"

# Database
db_password = "CHANGE-ME"  # Use AWS Secrets Manager in production
rds_instance_class = "db.t3.micro"  # "db.t3.medium" or larger for prod

# Redis Cache
elasticache_node_type = "cache.t3.micro"
elasticache_num_nodes = 1

# Machine Learning
sagemaker_model_url = "s3://bucket/path/to/model.tar.gz"

# Domain & SSL
domain_name = "api.anc-platform.com"
acm_certificate_arn = "arn:aws:acm:..."

# Notifications
alarm_email = "ops@example.com"

# CORS
allowed_origins = ["https://app.anc-platform.com"]
```

### Environment Differences

**Development** (`environments/dev/`):
- Single-AZ deployment (cost savings)
- Smaller instance sizes (t3.micro)
- No multi-AZ replication
- Spot instances enabled (batch jobs)
- Minimal monitoring

**Production** (`environments/prod/`):
- Multi-AZ deployment (fault tolerance)
- Larger instance sizes (r6g.xlarge)
- Full RDS replication
- No spot instances
- Enhanced monitoring and alerts

## State Management

Terraform state is stored in S3 with DynamoDB locking:

```
Bucket: anc-platform-terraform-state
Keys:
  - dev/terraform.tfstate
  - prod/terraform.tfstate
  - staging/terraform.tfstate
```

**Important**: Never commit `.tfstate` files locally. The S3 backend ensures state is centralized and locked during modifications.

### Initialize S3 Backend

```bash
# Create state bucket (one-time setup)
aws s3api create-bucket \
  --bucket anc-platform-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket anc-platform-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket anc-platform-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1
```

## Common Tasks

### View Outputs

```bash
cd environments/dev  # or prod

# Show all outputs
terraform output

# Show specific output
terraform output api_gateway_rest_url

# Export outputs as environment variables
export REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
export RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
```

### Update Configuration

```bash
# Modify terraform.tfvars
vi terraform.tfvars

# Plan changes
terraform plan

# Apply changes
terraform apply
```

### Destroy Infrastructure

```bash
# Warn: This deletes all AWS resources!
# Backup data first!

cd environments/dev  # or prod

# Confirm what will be deleted
terraform plan -destroy

# Destroy resources
terraform destroy
```

### Migrate State

```bash
# Backup current state
terraform state pull > backup.tfstate

# Move from local to S3 backend
terraform init  # Prompts to move state to backend

# Verify new state
terraform state list
```

## Outputs & Application Configuration

After deployment, Terraform outputs important values needed by the application:

```bash
cd environments/dev
terraform output -json > ../../../config/terraform-outputs.json
```

Key outputs:
- `api_gateway_rest_url`: REST API endpoint
- `api_gateway_websocket_url`: WebSocket endpoint
- `redis_endpoint`: ElastiCache Redis hostname
- `rds_endpoint`: RDS PostgreSQL hostname
- `sessions_table`: DynamoDB sessions table name
- `audio_queue_url`: SQS audio input queue
- `output_queue_url`: SQS output queue

These values should be passed to Docker/Kubernetes as environment variables.

## Troubleshooting

### State Lock Stuck

If Terraform is stuck waiting for a lock:

```bash
# List locks
aws dynamodb scan --table-name terraform-lock

# Force unlock (use with caution)
terraform force-unlock LOCK_ID
```

### Plan Differences

If `terraform plan` shows unexpected changes:

```bash
# Refresh state from AWS
terraform refresh

# Re-plan
terraform plan
```

### AWS Credentials Error

```bash
# Verify credentials
aws sts get-caller-identity

# Check configured profile
echo $AWS_PROFILE

# Reconfigure credentials
aws configure --profile default
export AWS_PROFILE=default
```

## Modules

All infrastructure is organized into reusable modules:

- **vpc**: Virtual Private Cloud with public/private subnets
- **s3**: S3 buckets for audio files
- **dynamodb**: DynamoDB tables for sessions and telemetry
- **elasticache**: Redis cluster for caching
- **rds**: PostgreSQL database
- **lambda**: Lambda functions for audio processing
- **api_gateway_rest**: REST API Gateway
- **api_gateway_websocket**: WebSocket API Gateway
- **sqs**: SQS queues for async processing
- **sagemaker**: SageMaker ML endpoint
- **cloudwatch**: CloudWatch monitoring and alarms
- **cloudfront**: CloudFront CDN distribution
- **iam**: IAM roles and policies
- **waf**: Web Application Firewall rules

See individual module READMEs for detailed documentation.

## Best Practices

1. **Always Plan Before Apply**: Review `terraform plan` output before `terraform apply`
2. **Use terraform.tfvars for Secrets**: Never commit passwords to git; use AWS Secrets Manager in production
3. **Enable State Locking**: S3 backend with DynamoDB prevents concurrent modifications
4. **Backup State**: Regularly backup terraform state file
5. **Code Review**: Have someone review Terraform changes before applying
6. **Test in Dev First**: Deploy to dev environment before production
7. **Document Changes**: Add comments explaining non-obvious configurations
8. **Monitor Costs**: Use AWS Cost Explorer to track resource spending

## Getting Help

- Check module-specific READMEs for detailed configuration
- Review AWS documentation for service limitations
- See [../cloud/AWS_ARCHITECTURE.md](../AWS_ARCHITECTURE.md) for high-level design
- Check [../cloud/README.md](../README.md) for deployment workflows

## Related Documentation

- [Lambda deployment guide](../README.md#lambda-packaging)
- [Docker/Kubernetes deployment](../../docs/deployment/)
- [AWS Architecture](../AWS_ARCHITECTURE.md)
