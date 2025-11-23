# Main Terraform configuration for ANC Platform on AWS
# This deploys the complete cloud infrastructure for real-time audio processing

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "anc-platform-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
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

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"

  environment      = var.environment
  vpc_cidr         = var.vpc_cidr
  availability_zones = var.availability_zones

  tags = local.common_tags
}

# S3 Buckets for audio storage
module "s3" {
  source = "./modules/s3"

  environment = var.environment

  tags = local.common_tags
}

# DynamoDB tables for session management
module "dynamodb" {
  source = "./modules/dynamodb"

  environment = var.environment

  tags = local.common_tags
}

# ElastiCache Redis for caching
module "elasticache" {
  source = "./modules/elasticache"

  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.elasticache_security_group_id]

  node_type          = var.elasticache_node_type
  num_cache_nodes    = var.elasticache_num_nodes

  tags = local.common_tags
}

# RDS PostgreSQL database
module "rds" {
  source = "./modules/rds"

  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  security_group_ids  = [module.vpc.rds_security_group_id]

  instance_class      = var.rds_instance_class
  allocated_storage   = var.rds_allocated_storage
  multi_az            = var.rds_multi_az

  db_name             = var.db_name
  db_username         = var.db_username
  db_password         = var.db_password

  tags = local.common_tags
}

# Lambda functions for audio processing
module "lambda" {
  source = "./modules/lambda"

  environment = var.environment

  # VPC configuration for Lambda functions
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.lambda_security_group_id]

  # Environment variables for Lambda
  redis_endpoint     = module.elasticache.redis_endpoint
  db_endpoint        = module.rds.db_endpoint
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password

  # S3 buckets
  raw_audio_bucket       = module.s3.raw_audio_bucket
  processed_audio_bucket = module.s3.processed_audio_bucket

  # DynamoDB tables
  connections_table  = module.dynamodb.connections_table_name
  sessions_table     = module.dynamodb.sessions_table_name

  tags = local.common_tags
}

# API Gateway (REST)
module "api_gateway_rest" {
  source = "./modules/api_gateway_rest"

  environment = var.environment

  # Lambda function ARNs
  lambda_functions = module.lambda.function_arns

  tags = local.common_tags
}

# API Gateway (WebSocket)
module "api_gateway_websocket" {
  source = "./modules/api_gateway_websocket"

  environment = var.environment

  # Lambda function ARNs
  lambda_on_connect    = module.lambda.websocket_on_connect_arn
  lambda_on_disconnect = module.lambda.websocket_on_disconnect_arn
  lambda_start_stream  = module.lambda.websocket_start_stream_arn
  lambda_audio_chunk   = module.lambda.websocket_audio_chunk_arn
  lambda_stop_stream   = module.lambda.websocket_stop_stream_arn

  tags = local.common_tags
}

# SQS queues for async processing
module "sqs" {
  source = "./modules/sqs"

  environment = var.environment

  tags = local.common_tags
}

# SageMaker ML model endpoint
module "sagemaker" {
  source = "./modules/sagemaker"

  environment = var.environment

  model_data_url     = var.sagemaker_model_url
  instance_type      = var.sagemaker_instance_type
  initial_instances  = var.sagemaker_initial_instances

  tags = local.common_tags
}

# CloudWatch monitoring and alarms
module "cloudwatch" {
  source = "./modules/cloudwatch"

  environment = var.environment

  # Resources to monitor
  lambda_functions        = module.lambda.function_names
  api_gateway_rest_id     = module.api_gateway_rest.api_id
  api_gateway_websocket_id = module.api_gateway_websocket.api_id
  sagemaker_endpoint      = module.sagemaker.endpoint_name

  # Alert configuration
  alarm_email = var.alarm_email

  tags = local.common_tags
}

# CloudFront CDN
module "cloudfront" {
  source = "./modules/cloudfront"

  environment = var.environment

  # Origin configurations
  rest_api_domain    = module.api_gateway_rest.invoke_url
  websocket_api_domain = module.api_gateway_websocket.invoke_url

  # SSL certificate
  acm_certificate_arn = var.acm_certificate_arn
  domain_name         = var.domain_name

  tags = local.common_tags
}

# IAM roles and policies
module "iam" {
  source = "./modules/iam"

  environment = var.environment
  account_id  = local.account_id

  # S3 bucket names
  s3_bucket_arns = [
    module.s3.raw_audio_bucket_arn,
    module.s3.processed_audio_bucket_arn,
    module.s3.ml_models_bucket_arn
  ]

  # DynamoDB table ARNs
  dynamodb_table_arns = [
    module.dynamodb.connections_table_arn,
    module.dynamodb.sessions_table_arn
  ]

  tags = local.common_tags
}

# Outputs
output "api_gateway_rest_url" {
  description = "REST API endpoint URL"
  value       = module.api_gateway_rest.invoke_url
}

output "api_gateway_websocket_url" {
  description = "WebSocket API endpoint URL"
  value       = module.api_gateway_websocket.invoke_url
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = module.cloudfront.domain_name
}

output "sagemaker_endpoint" {
  description = "SageMaker endpoint name"
  value       = module.sagemaker.endpoint_name
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = module.rds.db_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.redis_endpoint
  sensitive   = true
}
