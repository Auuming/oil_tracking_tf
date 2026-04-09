resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
  tags = local.tags
}
