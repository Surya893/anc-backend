# ============================================================================
# SageMaker ML Inference Endpoints v2.0
# ============================================================================

# ============================================================================
# SAGEMAKER EXECUTION ROLE
# ============================================================================

resource "aws_iam_role" "sagemaker_execution" {
  name = "${var.project_name}-sagemaker-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-sagemaker-role"
  }
}

resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy" "sagemaker_s3_access" {
  name = "${var.project_name}-sagemaker-s3-access"
  role = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.ml_models.arn,
          "${aws_s3_bucket.ml_models.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# SAGEMAKER MODELS
# ============================================================================

# Noise Classifier Model (50+ categories, deep learning)
resource "aws_sagemaker_model" "noise_classifier" {
  name               = "${var.project_name}-noise-classifier-v2-${var.environment}"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    # Use PyTorch deep learning container
    image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/anc-noise-classifier:v2"

    model_data_url = "s3://${aws_s3_bucket.ml_models.id}/models/noise_classifier_v2/model.tar.gz"

    environment = {
      SAGEMAKER_PROGRAM         = "inference.py"
      SAGEMAKER_SUBMIT_DIRECTORY = "s3://${aws_s3_bucket.ml_models.id}/models/noise_classifier_v2/code"
      NUM_CLASSES               = "50"
      MODEL_TYPE                = "efficientnet_b3"
      SAMPLE_RATE               = "48000"
      INFERENCE_BATCH_SIZE      = "8"
    }
  }

  vpc_config {
    subnets            = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.sagemaker.id]
  }

  tags = {
    Name    = "${var.project_name}-noise-classifier"
    Purpose = "Deep learning model for 50+ noise categories"
    Version = "2.0"
  }
}

# Emergency Sound Detector Model
resource "aws_sagemaker_model" "emergency_detector" {
  name               = "${var.project_name}-emergency-detector-v2-${var.environment}"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/anc-emergency-detector:v2"

    model_data_url = "s3://${aws_s3_bucket.ml_models.id}/models/emergency_detector_v2/model.tar.gz"

    environment = {
      SAGEMAKER_PROGRAM         = "inference.py"
      SAGEMAKER_SUBMIT_DIRECTORY = "s3://${aws_s3_bucket.ml_models.id}/models/emergency_detector_v2/code"
      DETECTION_THRESHOLD       = "0.85"
      MAX_LATENCY_MS            = "100"
    }
  }

  vpc_config {
    subnets            = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.sagemaker.id]
  }

  tags = {
    Name    = "${var.project_name}-emergency-detector"
    Purpose = "Safety-critical emergency sound detection"
    Version = "2.0"
  }
}

# ANC Parameter Optimizer Model (reinforcement learning)
resource "aws_sagemaker_model" "anc_optimizer" {
  name               = "${var.project_name}-anc-optimizer-v2-${var.environment}"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/anc-optimizer:v2"

    model_data_url = "s3://${aws_s3_bucket.ml_models.id}/models/anc_optimizer_v2/model.tar.gz"

    environment = {
      SAGEMAKER_PROGRAM         = "inference.py"
      SAGEMAKER_SUBMIT_DIRECTORY = "s3://${aws_s3_bucket.ml_models.id}/models/anc_optimizer_v2/code"
      ALGORITHM_TYPE            = "ppo"  # Proximal Policy Optimization
      STATE_DIM                 = "128"
      ACTION_DIM                = "16"
    }
  }

  vpc_config {
    subnets            = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.sagemaker.id]
  }

  tags = {
    Name    = "${var.project_name}-anc-optimizer"
    Purpose = "RL-based ANC parameter optimization"
    Version = "2.0"
  }
}

# ============================================================================
# SAGEMAKER ENDPOINT CONFIGURATIONS
# ============================================================================

# Noise Classifier Endpoint Config
resource "aws_sagemaker_endpoint_configuration" "noise_classifier" {
  name = "${var.project_name}-noise-classifier-config-v2-${var.environment}"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.noise_classifier.name
    initial_instance_count = 2
    instance_type          = "ml.c5.xlarge"  # CPU inference, cost-effective

    initial_variant_weight = 1.0

    # Auto-scaling configuration
    serverless_config {
      max_concurrency   = 20
      memory_size_in_mb = 4096
    }
  }

  data_capture_config {
    enable_capture              = true
    initial_sampling_percentage = 10
    destination_s3_uri          = "s3://${aws_s3_bucket.ml_models.id}/data-capture/noise-classifier/"

    capture_options {
      capture_mode = "InputAndOutput"
    }

    capture_content_type_header {
      json_content_types = ["application/json"]
    }
  }

  tags = {
    Name = "${var.project_name}-noise-classifier-config"
  }
}

# Emergency Detector Endpoint Config (higher priority, lower latency)
resource "aws_sagemaker_endpoint_configuration" "emergency_detector" {
  name = "${var.project_name}-emergency-detector-config-v2-${var.environment}"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.emergency_detector.name
    initial_instance_count = 3  # Higher redundancy for safety-critical
    instance_type          = "ml.c5.2xlarge"

    initial_variant_weight = 1.0
  }

  data_capture_config {
    enable_capture              = true
    initial_sampling_percentage = 100  # Capture all for safety audit
    destination_s3_uri          = "s3://${aws_s3_bucket.ml_models.id}/data-capture/emergency-detector/"

    capture_options {
      capture_mode = "InputAndOutput"
    }

    capture_content_type_header {
      json_content_types = ["application/json"]
    }
  }

  tags = {
    Name    = "${var.project_name}-emergency-detector-config"
    Purpose = "Safety-critical endpoint"
  }
}

# ANC Optimizer Endpoint Config
resource "aws_sagemaker_endpoint_configuration" "anc_optimizer" {
  name = "${var.project_name}-anc-optimizer-config-v2-${var.environment}"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.anc_optimizer.name
    initial_instance_count = 1
    instance_type          = "ml.g4dn.xlarge"  # GPU for RL inference

    initial_variant_weight = 1.0
  }

  tags = {
    Name = "${var.project_name}-anc-optimizer-config"
  }
}

# ============================================================================
# SAGEMAKER ENDPOINTS
# ============================================================================

resource "aws_sagemaker_endpoint" "noise_classifier" {
  name                 = "${var.project_name}-noise-classifier-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.noise_classifier.name

  tags = {
    Name    = "${var.project_name}-noise-classifier-endpoint"
    Purpose = "Real-time noise classification (50+ categories)"
  }
}

resource "aws_sagemaker_endpoint" "emergency_detector" {
  name                 = "${var.project_name}-emergency-detector-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.emergency_detector.name

  tags = {
    Name     = "${var.project_name}-emergency-detector-endpoint"
    Purpose  = "Safety-critical emergency detection"
    Priority = "high"
  }
}

resource "aws_sagemaker_endpoint" "anc_optimizer" {
  name                 = "${var.project_name}-anc-optimizer-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.anc_optimizer.name

  tags = {
    Name    = "${var.project_name}-anc-optimizer-endpoint"
    Purpose = "RL-based ANC parameter optimization"
  }
}

# ============================================================================
# AUTO-SCALING FOR SAGEMAKER ENDPOINTS
# ============================================================================

# Auto-scaling target for noise classifier
resource "aws_appautoscaling_target" "noise_classifier" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "endpoint/${aws_sagemaker_endpoint.noise_classifier.name}/variant/AllTraffic"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"
}

resource "aws_appautoscaling_policy" "noise_classifier_scaling" {
  name               = "${var.project_name}-noise-classifier-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.noise_classifier.resource_id
  scalable_dimension = aws_appautoscaling_target.noise_classifier.scalable_dimension
  service_namespace  = aws_appautoscaling_target.noise_classifier.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }

    target_value       = 1000.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto-scaling target for emergency detector
resource "aws_appautoscaling_target" "emergency_detector" {
  max_capacity       = 10
  min_capacity       = 3
  resource_id        = "endpoint/${aws_sagemaker_endpoint.emergency_detector.name}/variant/AllTraffic"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"
}

resource "aws_appautoscaling_policy" "emergency_detector_scaling" {
  name               = "${var.project_name}-emergency-detector-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.emergency_detector.resource_id
  scalable_dimension = aws_appautoscaling_target.emergency_detector.scalable_dimension
  service_namespace  = aws_appautoscaling_target.emergency_detector.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }

    target_value       = 800.0  # Lower to ensure low latency
    scale_in_cooldown  = 600    # Longer cooldown for safety
    scale_out_cooldown = 30     # Faster scale-out
  }
}

# ============================================================================
# SAGEMAKER SECURITY GROUP
# ============================================================================

resource "aws_security_group" "sagemaker" {
  name_description = "Security group for SageMaker endpoints"
  vpc_id          = aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "Allow HTTPS from Lambda"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-sagemaker-sg"
  }
}

# ============================================================================
# CLOUDWATCH ALARMS FOR SAGEMAKER
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "emergency_detector_invocation_errors" {
  alarm_name          = "${var.project_name}-emergency-detector-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1  # Immediate alert for safety-critical
  metric_name         = "ModelInvocationErrors"
  namespace           = "AWS/SageMaker"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "CRITICAL: Emergency detector errors detected"
  alarm_actions       = [aws_sns_topic.emergency_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.emergency_detector.name
    VariantName  = "AllTraffic"
  }
}

resource "aws_cloudwatch_metric_alarm" "emergency_detector_latency" {
  alarm_name          = "${var.project_name}-emergency-detector-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 60
  statistic           = "Average"
  threshold           = 100000  # 100ms in microseconds
  alarm_description   = "Emergency detector latency too high"
  alarm_actions       = [aws_sns_topic.emergency_alerts.arn]

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.emergency_detector.name
    VariantName  = "AllTraffic"
  }
}

resource "aws_cloudwatch_metric_alarm" "noise_classifier_invocations" {
  alarm_name          = "${var.project_name}-noise-classifier-high-traffic"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Invocations"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10000
  alarm_description   = "High traffic on noise classifier"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.noise_classifier.name
    VariantName  = "AllTraffic"
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "sagemaker_endpoints" {
  description = "SageMaker endpoint names"
  value = {
    noise_classifier   = aws_sagemaker_endpoint.noise_classifier.name
    emergency_detector = aws_sagemaker_endpoint.emergency_detector.name
    anc_optimizer      = aws_sagemaker_endpoint.anc_optimizer.name
  }
}

output "sagemaker_endpoint_arns" {
  description = "SageMaker endpoint ARNs"
  value = {
    noise_classifier   = aws_sagemaker_endpoint.noise_classifier.arn
    emergency_detector = aws_sagemaker_endpoint.emergency_detector.arn
    anc_optimizer      = aws_sagemaker_endpoint.anc_optimizer.arn
  }
  sensitive = true
}
