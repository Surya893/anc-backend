# S3 Module Outputs

output "raw_audio_bucket" {
  description = "Raw audio bucket name"
  value       = aws_s3_bucket.raw_audio.id
}

output "raw_audio_bucket_arn" {
  description = "Raw audio bucket ARN"
  value       = aws_s3_bucket.raw_audio.arn
}

output "processed_audio_bucket" {
  description = "Processed audio bucket name"
  value       = aws_s3_bucket.processed_audio.id
}

output "processed_audio_bucket_arn" {
  description = "Processed audio bucket ARN"
  value       = aws_s3_bucket.processed_audio.arn
}

output "ml_models_bucket" {
  description = "ML models bucket name"
  value       = aws_s3_bucket.ml_models.id
}

output "ml_models_bucket_arn" {
  description = "ML models bucket ARN"
  value       = aws_s3_bucket.ml_models.arn
}
