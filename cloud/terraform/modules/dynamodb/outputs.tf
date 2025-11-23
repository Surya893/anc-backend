# DynamoDB Module Outputs

output "connections_table_name" {
  description = "Connections table name"
  value       = aws_dynamodb_table.connections.name
}

output "connections_table_arn" {
  description = "Connections table ARN"
  value       = aws_dynamodb_table.connections.arn
}

output "connections_table_stream_arn" {
  description = "Connections table stream ARN"
  value       = aws_dynamodb_table.connections.stream_arn
}

output "sessions_table_name" {
  description = "Sessions table name"
  value       = aws_dynamodb_table.sessions.name
}

output "sessions_table_arn" {
  description = "Sessions table ARN"
  value       = aws_dynamodb_table.sessions.arn
}

output "sessions_table_stream_arn" {
  description = "Sessions table stream ARN"
  value       = aws_dynamodb_table.sessions.stream_arn
}
