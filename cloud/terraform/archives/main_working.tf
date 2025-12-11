# SIMPLIFIED WORKING Terraform Configuration for ANC Platform
# This is a production-ready, deployable configuration using only implemented modules
# For full architecture, see main_full.tf (requires additional modules)

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Comment out backend for first run - will create state locally
  # After first apply, uncomment and run terraform init -migrate-state
  # backend "s3" {
  #   bucket         = "anc-platform-terraform-state"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ANC-Platform"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local variables
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  common_tags = {
    Project     = "ANC-Platform"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==============================================================================
# NETWORKING
# ==============================================================================

module "vpc" {
  source = "./modules/vpc"

  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  aws_region         = var.aws_region

  tags = local.common_tags
}

# ==============================================================================
# STORAGE
# ==============================================================================

module "s3" {
  source = "./modules/s3"

  environment = var.environment

  # Optional: Pass KMS key if encryption required
  # kms_key_id = aws_kms_key.main.id

  # Optional: Restrict CORS to specific domains
  allowed_origins = var.allowed_origins

  # Optional: Specify Lambda role for bucket access
  # lambda_role_arn = module.lambda.role_arn

  tags = local.common_tags
}

module "dynamodb" {
  source = "./modules/dynamodb"

  environment = var.environment

  tags = local.common_tags
}

# ==============================================================================
# IOT CORE
# ==============================================================================

module "iot" {
  source = "./modules/iot"

  environment = var.environment
  aws_region  = var.aws_region
  account_id  = local.account_id

  # DynamoDB for telemetry
  telemetry_table_name = module.dynamodb.telemetry_table_name
  telemetry_table_arn  = module.dynamodb.telemetry_table_arn

  # S3 for metrics
  metrics_bucket_name = module.s3.raw_audio_bucket  # Reuse audio bucket or create dedicated
  metrics_bucket_arn  = module.s3.raw_audio_bucket_arn

  # Optional: Lambda for emergency detection
  # emergency_lambda_arn = module.lambda.emergency_detector_arn

  # Optional: SNS for alerts
  # alerts_sns_topic_arn = aws_sns_topic.alerts.arn

  tags = local.common_tags
}

# ==============================================================================
# WEB APPLICATION FIREWALL (Optional)
# ==============================================================================

module "waf" {
  source = "./modules/waf"

  environment = var.environment

  # WAF rules configuration
  rate_limit = var.waf_rate_limit

  tags = local.common_tags
}

# ==============================================================================
# OUTPUTS
# ==============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "iot_endpoint" {
  description = "AWS IoT Core endpoint"
  value       = module.iot.iot_endpoint
}

output "iot_policy_name" {
  description = "IoT device policy name"
  value       = module.iot.device_policy_name
}

output "raw_audio_bucket" {
  description = "S3 bucket for raw audio"
  value       = module.s3.raw_audio_bucket
}

output "processed_audio_bucket" {
  description = "S3 bucket for processed audio"
  value       = module.s3.processed_audio_bucket
}

output "telemetry_table" {
  description = "DynamoDB table for telemetry"
  value       = module.dynamodb.telemetry_table_name
}

output "sessions_table" {
  description = "DynamoDB table for sessions"
  value       = module.dynamodb.sessions_table_name
}

# ==============================================================================
# DEPLOYMENT INSTRUCTIONS
# ==============================================================================

# This configuration includes:
# ✅ VPC with public/private subnets
# ✅ S3 buckets for audio storage
# ✅ DynamoDB tables for data
# ✅ AWS IoT Core for device connectivity
# ✅ WAF for security
#
# Missing modules (for full architecture, create these):
# ❌ ElastiCache (Redis) - for caching
# ❌ RDS (PostgreSQL) - for relational data
# ❌ Lambda - for serverless functions
# ❌ API Gateway - for REST/WebSocket APIs
# ❌ SageMaker - for ML model hosting
# ❌ CloudWatch - for monitoring (partial - basic metrics included)
# ❌ CloudFront - for CDN
# ❌ IAM - for centralized role management
#
# To deploy:
# 1. terraform init
# 2. terraform plan
# 3. terraform apply
#
# To enable S3 backend (after first apply):
# 1. Uncomment backend configuration above
# 2. terraform init -migrate-state
