data "archive_file" "api_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/package_api"
  output_path = "${path.module}/lambda/api_handler.zip"
}

data "archive_file" "fetch_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/package_fetch"
  output_path = "${path.module}/lambda/fetch_prices.zip"
}

data "archive_file" "scrape_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/package_scrape"
  output_path = "${path.module}/lambda/latest_prices.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name}-api"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "api_handler.lambda_handler"
  filename      = data.archive_file.api_lambda_zip.output_path
  source_code_hash = data.archive_file.api_lambda_zip.output_base64sha256
  layers        = [var.pandas_layer_arn]
  timeout       = 30

  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      USERS_TABLE      = aws_dynamodb_table.users.name
      PRICES_TABLE     = aws_dynamodb_table.prices.name
      ALERTS_TOPIC_ARN = aws_sns_topic.alerts.arn
      # REDIS_ENDPOINT = aws_elasticache_cluster.redis.cache_nodes[0].address
      # REDIS_PORT     = tostring(aws_elasticache_cluster.redis.cache_nodes[0].port)
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "fetch" {
  function_name = "${local.name}-fetch-prices"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "fetch_prices.lambda_handler"
  filename      = data.archive_file.fetch_lambda_zip.output_path
  source_code_hash = data.archive_file.fetch_lambda_zip.output_base64sha256
  layers        = [var.pandas_layer_arn]
  timeout       = 60

  /*
  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
  */

  environment {
    variables = {
      ALERTS_TOPIC_ARN = aws_sns_topic.alerts.arn
      USERS_TABLE      = aws_dynamodb_table.users.name
      PRICES_TABLE     = aws_dynamodb_table.prices.name
      SCRAPER_API_URL  = "${aws_apigatewayv2_api.http.api_endpoint}/latest"
      # REDIS_ENDPOINT = aws_elasticache_cluster.redis.cache_nodes[0].address
      # REDIS_PORT     = tostring(aws_elasticache_cluster.redis.cache_nodes[0].port)
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "scrape" {
  function_name = "${local.name}-latest-prices"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "latest_prices.lambda_handler"
  filename      = data.archive_file.scrape_lambda_zip.output_path
  source_code_hash = data.archive_file.scrape_lambda_zip.output_base64sha256
  timeout       = 30

  # Keep this Lambda outside the VPC for now.
  # It only needs outbound HTTP access to Kapook and avoids NAT / Redis coupling.

  tags = local.tags
}
