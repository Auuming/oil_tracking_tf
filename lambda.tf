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

resource "aws_lambda_function" "api" {
  function_name    = "${local.name}-api"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "api_handler.lambda_handler"
  filename         = data.archive_file.api_lambda_zip.output_path
  source_code_hash = data.archive_file.api_lambda_zip.output_base64sha256
  
  layers = [var.pandas_layer_arn]
  
  timeout = 30

  vpc_config {
    # Move the Lambda to the new Private Subnet
    subnet_ids         = [aws_subnet.private.id]
    
    # Use already created dedicated Lambda Security Group
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      USERS_TABLE      = aws_dynamodb_table.users.name
      PRICES_TABLE     = aws_dynamodb_table.prices.name
      ALERTS_TOPIC_ARN = aws_sns_topic.alerts.arn
      REDIS_ENDPOINT   = aws_elasticache_cluster.redis.cache_nodes[0].address
      REDIS_PORT       = tostring(aws_elasticache_cluster.redis.cache_nodes[0].port)
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "fetch" {
  function_name    = "${local.name}-fetch-prices"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "fetch_prices.lambda_handler"
  filename         = data.archive_file.fetch_lambda_zip.output_path
  source_code_hash = data.archive_file.fetch_lambda_zip.output_base64sha256
  
  layers = [var.pandas_layer_arn]
  
  timeout = 60

  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      ALERTS_TOPIC_ARN = aws_sns_topic.alerts.arn
      USERS_TABLE      = aws_dynamodb_table.users.name
      PRICES_TABLE     = aws_dynamodb_table.prices.name
      REDIS_ENDPOINT   = aws_elasticache_cluster.redis.cache_nodes[0].address
      REDIS_PORT       = aws_elasticache_cluster.redis.cache_nodes[0].port
    }
  }

  tags = local.tags
}