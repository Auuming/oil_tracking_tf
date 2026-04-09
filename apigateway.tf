resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }

  tags          = local.tags
}

resource "aws_apigatewayv2_integration" "lambda_api" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_prices" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /prices"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_api.id}"
}

resource "aws_apigatewayv2_route" "create_subscription" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /alerts"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_api.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
  tags        = local.tags
}

resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
