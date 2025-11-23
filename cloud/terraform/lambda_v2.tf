# ============================================================================
# Lambda Functions v2.0
# ============================================================================

# ============================================================================
# LAMBDA LAYERS
# ============================================================================

# NumPy/SciPy Layer for ANC processing
resource "aws_lambda_layer_version" "numpy_scipy" {
  filename            = "${path.module}/../lambda/layers/numpy-scipy.zip"
  layer_name          = "${var.project_name}-numpy-scipy"
  compatible_runtimes = ["python3.11"]
  description         = "NumPy and SciPy for ANC algorithms"

  lifecycle {
    create_before_destroy = true
  }
}

# Common utilities layer
resource "aws_lambda_layer_version" "common" {
  filename            = "${path.module}/../lambda/layers/common.zip"
  layer_name          = "${var.project_name}-common"
  compatible_runtimes = ["python3.11"]
  description         = "Common utilities and shared code"

  lifecycle {
    create_before_destroy = true
  }
}

# ============================================================================
# LAMBDA FUNCTIONS
# ============================================================================

# WebSocket Connect Handler
resource "aws_lambda_function" "websocket_connect" {
  filename         = "${path.module}/../lambda/websocket_connect/deployment.zip"
  function_name    = "${var.project_name}-websocket-connect-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/websocket_connect/deployment.zip")
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      CONNECTIONS_TABLE      = aws_dynamodb_table.connections.name
      JWT_SECRET_ARN         = aws_secretsmanager_secret.jwt_secret.arn
      REDIS_ENDPOINT         = aws_elasticache_replication_group.redis.primary_endpoint_address
      REDIS_PORT             = "6379"
      REDIS_AUTH_TOKEN_ARN   = aws_secretsmanager_secret.redis_auth_token.arn
      LOG_LEVEL              = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  layers = [aws_lambda_layer_version.common.arn]

  tags = {
    Name    = "${var.project_name}-websocket-connect"
    Purpose = "WebSocket connection handler with JWT auth"
  }
}

# WebSocket Disconnect Handler
resource "aws_lambda_function" "websocket_disconnect" {
  filename         = "${path.module}/../lambda/websocket_disconnect/deployment.zip"
  function_name    = "${var.project_name}-websocket-disconnect-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/websocket_disconnect/deployment.zip")
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      CONNECTIONS_TABLE = aws_dynamodb_table.connections.name
      SESSIONS_TABLE    = aws_dynamodb_table.sessions.name
      REDIS_ENDPOINT    = aws_elasticache_replication_group.redis.primary_endpoint_address
      REDIS_PORT        = "6379"
      REDIS_AUTH_TOKEN_ARN = aws_secretsmanager_secret.redis_auth_token.arn
      LOG_LEVEL         = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  layers = [aws_lambda_layer_version.common.arn]

  tags = {
    Name    = "${var.project_name}-websocket-disconnect"
    Purpose = "WebSocket disconnection handler with cleanup"
  }
}

# Audio Receiver (WebSocket message handler)
resource "aws_lambda_function" "audio_receiver" {
  filename         = "${path.module}/../lambda/audio_receiver/deployment.zip"
  function_name    = "${var.project_name}-audio-receiver-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/audio_receiver/deployment.zip")
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 512

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      CONNECTIONS_TABLE     = aws_dynamodb_table.connections.name
      SESSIONS_TABLE        = aws_dynamodb_table.sessions.name
      RAW_AUDIO_BUCKET      = aws_s3_bucket.raw_audio.id
      PROCESSING_QUEUE_URL  = aws_sqs_queue.audio_processing.url
      MAX_AUDIO_SIZE_BYTES  = "262144"  # 256 KB
      LOG_LEVEL             = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  reserved_concurrent_executions = var.max_concurrent_executions

  layers = [aws_lambda_layer_version.common.arn]

  tags = {
    Name    = "${var.project_name}-audio-receiver"
    Purpose = "Receive and validate audio chunks from WebSocket"
  }
}

# ANC Processor (Core algorithm)
resource "aws_lambda_function" "anc_processor" {
  filename         = "${path.module}/../lambda/anc_processor/deployment.zip"
  function_name    = "${var.project_name}-anc-processor-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/anc_processor/deployment.zip")
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 2048  # Increased for algorithm processing

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      REDIS_ENDPOINT       = aws_elasticache_replication_group.redis.primary_endpoint_address
      REDIS_PORT           = "6379"
      REDIS_AUTH_TOKEN_ARN = aws_secretsmanager_secret.redis_auth_token.arn
      RAW_AUDIO_BUCKET     = aws_s3_bucket.raw_audio.id
      PROCESSED_AUDIO_BUCKET = aws_s3_bucket.processed_audio.id
      OUTPUT_QUEUE_URL     = aws_sqs_queue.audio_output.url
      ML_MODELS_BUCKET     = aws_s3_bucket.ml_models.id
      SAGEMAKER_ENDPOINT   = aws_sagemaker_endpoint.noise_classifier.name
      ALGORITHM            = "hybrid_nlms_rls"  # v2.0 hybrid algorithm
      FILTER_LENGTH        = "512"
      SAMPLE_RATE          = "48000"
      LOG_LEVEL            = "INFO"
      ENABLE_SPATIAL_AUDIO = "true"
      ENABLE_ADAPTIVE_LEARNING = "true"
    }
  }

  tracing_config {
    mode = "Active"
  }

  reserved_concurrent_executions = var.max_concurrent_executions

  layers = [
    aws_lambda_layer_version.numpy_scipy.arn,
    aws_lambda_layer_version.common.arn
  ]

  tags = {
    Name    = "${var.project_name}-anc-processor"
    Purpose = "Core ANC processing with hybrid NLMS+RLS algorithm"
  }
}

# Audio Sender (Send processed audio back to client)
resource "aws_lambda_function" "audio_sender" {
  filename         = "${path.module}/../lambda/audio_sender/deployment.zip"
  function_name    = "${var.project_name}-audio-sender-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/audio_sender/deployment.zip")
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 512

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      CONNECTIONS_TABLE    = aws_dynamodb_table.connections.name
      WEBSOCKET_API_ENDPOINT = "https://${aws_apigatewayv2_api.websocket.id}.execute-api.${var.region}.amazonaws.com/${var.environment}"
      PROCESSED_AUDIO_BUCKET = aws_s3_bucket.processed_audio.id
      LOG_LEVEL            = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  reserved_concurrent_executions = var.max_concurrent_executions

  layers = [aws_lambda_layer_version.common.arn]

  tags = {
    Name    = "${var.project_name}-audio-sender"
    Purpose = "Send processed audio back via WebSocket"
  }
}

# ML Classifier (Noise classification)
resource "aws_lambda_function" "ml_classifier" {
  filename         = "${path.module}/../lambda/ml_classifier/deployment.zip"
  function_name    = "${var.project_name}-ml-classifier-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/ml_classifier/deployment.zip")
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 1536

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      ML_MODELS_BUCKET   = aws_s3_bucket.ml_models.id
      SAGEMAKER_ENDPOINT = aws_sagemaker_endpoint.noise_classifier.name
      NUM_CLASSES        = "50"  # v2.0 expanded from 6 to 50
      LOG_LEVEL          = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  layers = [
    aws_lambda_layer_version.numpy_scipy.arn,
    aws_lambda_layer_version.common.arn
  ]

  tags = {
    Name    = "${var.project_name}-ml-classifier"
    Purpose = "ML-powered noise classification (50 classes)"
  }
}

# Emergency Detector
resource "aws_lambda_function" "emergency_detector" {
  filename         = "${path.module}/../lambda/emergency_detector/deployment.zip"
  function_name    = "${var.project_name}-emergency-detector-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/emergency_detector/deployment.zip")
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 1024

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      ML_MODELS_BUCKET   = aws_s3_bucket.ml_models.id
      SAGEMAKER_ENDPOINT = aws_sagemaker_endpoint.emergency_detector.name
      NOTIFICATION_SNS_TOPIC = aws_sns_topic.emergency_alerts.arn
      LOG_LEVEL          = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  layers = [
    aws_lambda_layer_version.numpy_scipy.arn,
    aws_lambda_layer_version.common.arn
  ]

  tags = {
    Name    = "${var.project_name}-emergency-detector"
    Purpose = "Detect emergency sounds and bypass ANC"
  }
}

# ============================================================================
# SQS EVENT SOURCE MAPPINGS
# ============================================================================

# ANC Processor triggered by audio processing queue
resource "aws_lambda_event_source_mapping" "anc_processor" {
  event_source_arn = aws_sqs_queue.audio_processing.arn
  function_name    = aws_lambda_function.anc_processor.arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 1

  scaling_config {
    maximum_concurrency = var.max_concurrent_executions
  }
}

# Audio Sender triggered by output queue
resource "aws_lambda_event_source_mapping" "audio_sender" {
  event_source_arn = aws_sqs_queue.audio_output.arn
  function_name    = aws_lambda_function.audio_sender.arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 1

  scaling_config {
    maximum_concurrency = var.max_concurrent_executions
  }
}

# ============================================================================
# CLOUDWATCH ALARMS
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "anc_processor_errors" {
  alarm_name          = "${var.project_name}-anc-processor-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "ANC processor error rate too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.anc_processor.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "anc_processor_duration" {
  alarm_name          = "${var.project_name}-anc-processor-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 20000  # 20 seconds
  alarm_description   = "ANC processor duration too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.anc_processor.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "anc_processor_throttles" {
  alarm_name          = "${var.project_name}-anc-processor-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "ANC processor being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.anc_processor.function_name
  }
}

# ============================================================================
# SNS TOPICS FOR ALERTS
# ============================================================================

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-${var.environment}"

  tags = {
    Name = "${var.project_name}-alerts"
  }
}

resource "aws_sns_topic" "emergency_alerts" {
  name = "${var.project_name}-emergency-alerts-${var.environment}"

  tags = {
    Name    = "${var.project_name}-emergency-alerts"
    Purpose = "Critical emergency sound detection alerts"
  }
}

# ============================================================================
# LAMBDA INSIGHTS
# ============================================================================

resource "aws_lambda_layer_version" "lambda_insights" {
  layer_name          = "LambdaInsightsExtension"
  compatible_runtimes = ["python3.11"]

  # This ARN is for us-east-1, adjust for other regions
  # arn:aws:lambda:${var.region}:580247275435:layer:LambdaInsightsExtension:21
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "lambda_functions" {
  description = "Lambda function ARNs"
  value = {
    websocket_connect   = aws_lambda_function.websocket_connect.arn
    websocket_disconnect = aws_lambda_function.websocket_disconnect.arn
    audio_receiver      = aws_lambda_function.audio_receiver.arn
    anc_processor       = aws_lambda_function.anc_processor.arn
    audio_sender        = aws_lambda_function.audio_sender.arn
    ml_classifier       = aws_lambda_function.ml_classifier.arn
    emergency_detector  = aws_lambda_function.emergency_detector.arn
  }
}
