resource "aws_cloudwatch_log_group" "application" {
  name              = "/jalos/${var.environment}"
  retention_in_days = 14
}
