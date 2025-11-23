# AWS IoT Core Module for ANC Platform
# Provides device connectivity, data sync, and telemetry

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# IoT Policy for Device Access
# ============================================================================

resource "aws_iot_policy" "device_policy" {
  name = "${var.environment}-anc-device-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iot:Connect"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.account_id}:client/$${iot:Connection.Thing.ThingName}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iot:Publish"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topic/anc/devices/$${iot:Connection.Thing.ThingName}/*",
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topic/anc/telemetry/*",
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topic/$aws/things/$${iot:Connection.Thing.ThingName}/shadow/update"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iot:Subscribe"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topicfilter/anc/devices/$${iot:Connection.Thing.ThingName}/*",
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topicfilter/$aws/things/$${iot:Connection.Thing.ThingName}/shadow/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iot:Receive"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topic/anc/devices/$${iot:Connection.Thing.ThingName}/*",
          "arn:aws:iot:${var.aws_region}:${var.account_id}:topic/$aws/things/$${iot:Connection.Thing.ThingName}/shadow/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iot:GetThingShadow",
          "iot:UpdateThingShadow"
        ]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${var.account_id}:thing/$${iot:Connection.Thing.ThingName}"
        ]
      }
    ]
  })
}

# ============================================================================
# IoT Thing Type for ANC Devices
# ============================================================================

resource "aws_iot_thing_type" "anc_device" {
  name = "${var.environment}-anc-device"

  properties {
    description           = "ANC Device with real-time audio processing"
    searchable_attributes = ["deviceId", "firmwareVersion", "model"]
  }

  tags = var.tags
}

# ============================================================================
# IoT Topic Rules for Data Processing
# ============================================================================

# Rule: Forward telemetry to DynamoDB
resource "aws_iot_topic_rule" "telemetry_to_dynamodb" {
  name        = "${var.environment}_anc_telemetry_to_dynamodb"
  description = "Store device telemetry in DynamoDB"
  enabled     = true
  sql         = "SELECT * FROM 'anc/telemetry/#'"
  sql_version = "2016-03-23"

  dynamodb_v2 {
    role_arn = aws_iam_role.iot_rules_role.arn
    put_item {
      table_name = var.telemetry_table_name
    }
  }
}

# Rule: Forward audio metrics to S3
resource "aws_iot_topic_rule" "metrics_to_s3" {
  name        = "${var.environment}_anc_metrics_to_s3"
  description = "Archive device metrics to S3"
  enabled     = true
  sql         = "SELECT * FROM 'anc/devices/+/metrics'"
  sql_version = "2016-03-23"

  s3 {
    role_arn   = aws_iam_role.iot_rules_role.arn
    bucket_name = var.metrics_bucket_name
    key        = "metrics/$${topic()}/year=$${parse_time('yyyy', timestamp())}/ month=$${parse_time('MM', timestamp())}/day=$${parse_time('dd', timestamp())}/$${timestamp()}.json"
  }
}

# Rule: Trigger Lambda for emergency detection events
resource "aws_iot_topic_rule" "emergency_to_lambda" {
  name        = "${var.environment}_anc_emergency_to_lambda"
  description = "Process emergency detection events"
  enabled     = true
  sql         = "SELECT * FROM 'anc/devices/+/emergency' WHERE is_emergency = true"
  sql_version = "2016-03-23"

  lambda {
    function_arn = var.emergency_lambda_arn
  }
}

# Rule: Send high-latency alerts to SNS
resource "aws_iot_topic_rule" "latency_alert" {
  name        = "${var.environment}_anc_latency_alert"
  description = "Alert on high latency"
  enabled     = true
  sql         = "SELECT * FROM 'anc/telemetry/+' WHERE latency_ms > 100"
  sql_version = "2016-03-23"

  sns {
    role_arn   = aws_iam_role.iot_rules_role.arn
    target_arn = var.alerts_sns_topic_arn
    message_format = "RAW"
  }
}

# ============================================================================
# IAM Role for IoT Rules Engine
# ============================================================================

resource "aws_iam_role" "iot_rules_role" {
  name = "${var.environment}-anc-iot-rules-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "iot.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "iot_rules_policy" {
  name = "${var.environment}-anc-iot-rules-policy"
  role = aws_iam_role.iot_rules_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = var.telemetry_table_arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${var.metrics_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = var.emergency_lambda_arn
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.alerts_sns_topic_arn
      }
    ]
  })
}

# ============================================================================
# IoT Analytics (Optional - for advanced analytics)
# ============================================================================

resource "aws_iot_analytics_channel" "anc_data" {
  name = "${var.environment}-anc-data-channel"

  retention_period {
    number_of_days = 30
  }

  tags = var.tags
}

resource "aws_iot_analytics_datastore" "anc_data" {
  name = "${var.environment}-anc-datastore"

  retention_period {
    number_of_days = 90
  }

  tags = var.tags
}

resource "aws_iot_analytics_pipeline" "anc_data" {
  pipeline_name = "${var.environment}-anc-pipeline"

  pipeline_activities {
    channel {
      name         = "channel_activity"
      channel_name = aws_iot_analytics_channel.anc_data.name
      next         = "datastore_activity"
    }

    datastore {
      name           = "datastore_activity"
      datastore_name = aws_iot_analytics_datastore.anc_data.name
    }
  }

  tags = var.tags
}

# ============================================================================
# CloudWatch Logs for IoT
# ============================================================================

resource "aws_cloudwatch_log_group" "iot_logs" {
  name              = "/aws/iot/${var.environment}/anc-devices"
  retention_in_days = 30

  tags = var.tags
}

# ============================================================================
# Outputs
# ============================================================================

output "iot_endpoint" {
  description = "AWS IoT Core endpoint"
  value       = "https://iot.${var.aws_region}.amazonaws.com"
}

output "device_policy_name" {
  description = "IoT policy name for devices"
  value       = aws_iot_policy.device_policy.name
}

output "thing_type_name" {
  description = "Thing type for ANC devices"
  value       = aws_iot_thing_type.anc_device.name
}

output "analytics_channel_name" {
  description = "IoT Analytics channel name"
  value       = aws_iot_analytics_channel.anc_data.name
}
