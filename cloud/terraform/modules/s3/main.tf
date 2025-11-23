# S3 Module for ANC Platform
# Creates S3 buckets for audio storage and ML models

# Raw audio bucket
resource "aws_s3_bucket" "raw_audio" {
  bucket = "${var.environment}-anc-platform-audio-raw"

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-raw-audio"
      Purpose     = "Raw audio file storage"
      DataType    = "audio"
      Sensitivity = "medium"
    }
  )
}

# Versioning for raw audio
resource "aws_s3_bucket_versioning" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for raw audio
resource "aws_s3_bucket_server_side_encryption_configuration" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for raw audio
resource "aws_s3_bucket_lifecycle_configuration" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id

  rule {
    id     = "audio-lifecycle"
    status = "Enabled"

    # Transition to Intelligent-Tiering immediately
    transition {
      days          = 0
      storage_class = "INTELLIGENT_TIERING"
    }

    # Archive to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Deep Archive after 180 days
    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete after 365 days
    expiration {
      days = 365
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Block public access for raw audio
resource "aws_s3_bucket_public_access_block" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Processed audio bucket
resource "aws_s3_bucket" "processed_audio" {
  bucket = "${var.environment}-anc-platform-audio-processed"

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-processed-audio"
      Purpose     = "Processed audio file storage"
      DataType    = "audio"
      Sensitivity = "low"
    }
  )
}

# Encryption for processed audio
resource "aws_s3_bucket_server_side_encryption_configuration" "processed_audio" {
  bucket = aws_s3_bucket.processed_audio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for processed audio (shorter retention)
resource "aws_s3_bucket_lifecycle_configuration" "processed_audio" {
  bucket = aws_s3_bucket.processed_audio.id

  rule {
    id     = "processed-audio-lifecycle"
    status = "Enabled"

    # Delete after 30 days
    expiration {
      days = 30
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Block public access for processed audio
resource "aws_s3_bucket_public_access_block" "processed_audio" {
  bucket = aws_s3_bucket.processed_audio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ML models bucket
resource "aws_s3_bucket" "ml_models" {
  bucket = "${var.environment}-anc-platform-ml-models"

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-ml-models"
      Purpose     = "ML model artifacts storage"
      DataType    = "models"
      Sensitivity = "high"
    }
  )
}

# Versioning for ML models (critical for rollback)
resource "aws_s3_bucket_versioning" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for ML models with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
  }
}

# Block public access for ML models
resource "aws_s3_bucket_public_access_block" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for direct browser uploads
resource "aws_s3_bucket_cors_configuration" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Bucket policies
resource "aws_s3_bucket_policy" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaAccess"
        Effect = "Allow"
        Principal = {
          AWS = var.lambda_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.raw_audio.arn}/*"
      },
      {
        Sid    = "RequireEncryptedTransport"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.raw_audio.arn,
          "${aws_s3_bucket.raw_audio.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# CloudWatch metrics for S3
resource "aws_s3_bucket_metric" "raw_audio_metrics" {
  bucket = aws_s3_bucket.raw_audio.id
  name   = "EntireBucket"
}

# Intelligent-Tiering configuration
resource "aws_s3_bucket_intelligent_tiering_configuration" "raw_audio" {
  bucket = aws_s3_bucket.raw_audio.id
  name   = "EntireBucket"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}
