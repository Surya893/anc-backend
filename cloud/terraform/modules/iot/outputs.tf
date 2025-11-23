# Outputs for AWS IoT Module

output "iot_endpoint" {
  description = "AWS IoT Core endpoint URL"
  value       = data.aws_iot_endpoint.iot_endpoint.endpoint_address
}

output "iot_endpoint_type" {
  description = "AWS IoT endpoint type"
  value       = "iot:Data-ATS"
}

output "device_policy_name" {
  description = "Name of the IoT policy for devices"
  value       = aws_iot_policy.device_policy.name
}

output "device_policy_arn" {
  description = "ARN of the IoT policy for devices"
  value       = aws_iot_policy.device_policy.arn
}

output "thing_type_name" {
  description = "Name of the thing type for ANC devices"
  value       = aws_iot_thing_type.anc_device.name
}

output "thing_type_arn" {
  description = "ARN of the thing type for ANC devices"
  value       = aws_iot_thing_type.anc_device.arn
}

output "analytics_channel_name" {
  description = "IoT Analytics channel name"
  value       = aws_iot_analytics_channel.anc_data.name
}

output "analytics_datastore_name" {
  description = "IoT Analytics datastore name"
  value       = aws_iot_analytics_datastore.anc_data.name
}

output "iot_rules_role_arn" {
  description = "IAM role ARN for IoT rules"
  value       = aws_iam_role.iot_rules_role.arn
}

# Data source for IoT endpoint
data "aws_iot_endpoint" "iot_endpoint" {
  endpoint_type = "iot:Data-ATS"
}
