resource "aws_cloudwatch_event_rule" "price_fetch_schedule" {
  name                = "${local.name}-fetch-schedule"
  schedule_expression = "cron(0 2 * * ? *)" # Every day at 2 AM UTC -> 9 AM in Bangkok(UTC+7)
  tags                = local.tags
}

resource "aws_cloudwatch_event_target" "fetch_lambda" {
  rule      = aws_cloudwatch_event_rule.price_fetch_schedule.name
  target_id = "FetchOilPricesLambda"
  arn       = aws_lambda_function.fetch.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fetch.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.price_fetch_schedule.arn
}

# Trigger the Lambda right after creating it
resource "aws_lambda_invocation" "trigger_fetch_on_deploy" {
  function_name = aws_lambda_function.fetch.function_name
  
  # Send a dummy payload that mimics an EventBridge trigger
  input = jsonencode({
    "source": "opentofu.deploy",
    "detail-type": "Initial Tofu Deployment Fetch"
  })

  # Ensures this only runs on the initial creation, or when you update the fetch Python script.
  triggers = {
    redeployment = aws_lambda_function.fetch.source_code_hash
  }

  # Ensure the Lambda and EventBridge permissions are fully set up before invoking
  depends_on = [
    aws_lambda_function.fetch,
    aws_lambda_permission.allow_eventbridge
  ]
}