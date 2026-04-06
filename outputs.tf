output "api_base_url" {
  value = aws_apigatewayv2_api.http.api_endpoint
}

output "frontend_public_ip" {
  value = aws_instance.frontend.public_ip
}

output "frontend_url" {
  value = "http://${aws_instance.frontend.public_ip}"
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "timestream_endpoint" {
  value = aws_timestreaminfluxdb_db_instance.oil_prices.endpoint
}

output "influxdb_token" {
  description = "The auto-generated API token for InfluxDB"
  value       = data.external.influx_token.result.token
  sensitive   = true
}