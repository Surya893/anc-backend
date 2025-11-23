# WAF Module Variables

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "api_gateway_arn" {
  description = "API Gateway ARN to associate with WAF"
  type        = string
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for WAF alarms"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "blocked_countries" {
  description = "List of country codes to block (e.g., ['CN', 'RU'])"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
