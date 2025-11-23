# DynamoDB Module for ANC Platform
# Creates tables for session management and connection tracking

# Connections table (WebSocket connections)
resource "aws_dynamodb_table" "connections" {
  name           = "${var.environment}-anc-connections"
  billing_mode   = "PAY_PER_REQUEST"  # Auto-scaling
  hash_key       = "connectionId"

  attribute {
    name = "connectionId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "lastActivity"
    type = "N"
  }

  # GSI for user lookups
  global_secondary_index {
    name            = "userId-lastActivity-index"
    hash_key        = "userId"
    range_key       = "lastActivity"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # Stream for replication
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = merge(
    var.tags,
    {
      Name    = "${var.environment}-connections"
      Purpose = "WebSocket connection tracking"
    }
  )
}

# Sessions table (ANC processing sessions)
resource "aws_dynamodb_table" "sessions" {
  name           = "${var.environment}-anc-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "sessionId"
  range_key      = "userId"

  attribute {
    name = "sessionId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "N"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # GSI for user session queries
  global_secondary_index {
    name            = "userId-createdAt-index"
    hash_key        = "userId"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI for status queries
  global_secondary_index {
    name            = "status-createdAt-index"
    hash_key        = "status"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup of old sessions
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # DynamoDB Streams for cross-region replication
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = merge(
    var.tags,
    {
      Name    = "${var.environment}-sessions"
      Purpose = "ANC processing session state"
    }
  )
}

# Global Tables Configuration (for multi-region)
resource "aws_dynamodb_global_table" "sessions_global" {
  count = var.enable_global_tables ? 1 : 0
  name  = aws_dynamodb_table.sessions.name

  replica {
    region_name = var.primary_region
  }

  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name = replica.value
    }
  }

  depends_on = [
    aws_dynamodb_table.sessions
  ]
}

# Auto Scaling for provisioned capacity (if not using PAY_PER_REQUEST)
# Uncomment if switching to PROVISIONED billing mode

# resource "aws_appautoscaling_target" "sessions_read" {
#   max_capacity       = var.read_capacity_max
#   min_capacity       = var.read_capacity_min
#   resource_id        = "table/${aws_dynamodb_table.sessions.name}"
#   scalable_dimension = "dynamodb:table:ReadCapacityUnits"
#   service_namespace  = "dynamodb"
# }

# resource "aws_appautoscaling_policy" "sessions_read" {
#   name               = "${var.environment}-sessions-read-autoscaling"
#   policy_type        = "TargetTrackingScaling"
#   resource_id        = aws_appautoscaling_target.sessions_read.resource_id
#   scalable_dimension = aws_appautoscaling_target.sessions_read.scalable_dimension
#   service_namespace  = aws_appautoscaling_target.sessions_read.service_namespace

#   target_tracking_scaling_policy_configuration {
#     predefined_metric_specification {
#       predefined_metric_type = "DynamoDBReadCapacityUtilization"
#     }
#     target_value = 70.0
#   }
# }

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "connections_throttle" {
  alarm_name          = "${var.environment}-dynamodb-connections-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when DynamoDB throttles requests"
  alarm_actions       = [var.sns_topic_arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.connections.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "sessions_throttle" {
  alarm_name          = "${var.environment}-dynamodb-sessions-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when DynamoDB throttles requests"
  alarm_actions       = [var.sns_topic_arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.sessions.name
  }

  tags = var.tags
}
