output "api_base_url" {
  value = aws_apigatewayv2_api.http.api_endpoint
}

output "frontend_url" {
  description = "The public CloudFront URL for your frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}