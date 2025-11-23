# Variables for AWS IoT Module

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "telemetry_table_name" {
  description = "DynamoDB table name for telemetry data"
  type        = string
}

variable "telemetry_table_arn" {
  description = "DynamoDB table ARN for telemetry data"
  type        = string
}

variable "metrics_bucket_name" {
  description = "S3 bucket name for metrics storage"
  type        = string
}

variable "metrics_bucket_arn" {
  description = "S3 bucket ARN for metrics storage"
  type        = string
}

variable "emergency_lambda_arn" {
  description = "Lambda function ARN for emergency detection"
  type        = string
  default     = ""
}

variable "alerts_sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
