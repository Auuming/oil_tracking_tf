# 1. Base Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${local.name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

# 2. Allow Lambda to write to CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 3. Allow Lambda to run inside the VPC (Required so it can reach Redis)
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# 4. Allow Lambda to read/write DynamoDB and publish to SNS
resource "aws_iam_policy" "lambda_data_policy" {
  name        = "${local.name}-lambda-data-policy"
  description = "Allow Lambda to access DynamoDB and send SNS alerts"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.prices.arn,
          aws_dynamodb_table.users.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "sns:Publish",
          "sns:Subscribe"
        ],
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_data_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_data_policy.arn
}