# Variables for Development Environment
# This file references the shared variables from the parent directory

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# RDS Configuration
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = false
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "anc_platform"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "anc_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# ElastiCache Configuration
variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "elasticache_num_nodes" {
  description = "Number of ElastiCache nodes"
  type        = number
  default     = 1
}

# SageMaker Configuration
variable "sagemaker_model_url" {
  description = "S3 URL for SageMaker model artifacts"
  type        = string
}

variable "sagemaker_instance_type" {
  description = "SageMaker endpoint instance type"
  type        = string
  default     = "ml.t3.medium"
}

variable "sagemaker_initial_instances" {
  description = "Initial number of SageMaker instances"
  type        = number
  default     = 1
}

# Domain Configuration
variable "domain_name" {
  description = "Custom domain name for CloudFront"
  type        = string
  default     = "api-dev.anc-platform.com"
}

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = ""
}

# Monitoring Configuration
variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Use Spot instances for batch processing"
  type        = bool
  default     = false
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for Lambda and SageMaker"
  type        = bool
  default     = false
}

# WAF Configuration
variable "waf_rate_limit" {
  description = "WAF rate limit per 5 minutes"
  type        = number
  default     = 2000
}

# CORS Configuration
variable "allowed_origins" {
  description = "Allowed CORS origins for S3 buckets"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:5000"]
}
