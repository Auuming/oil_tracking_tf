resource "aws_dynamodb_table" "users" {
  name         = "${local.name}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = local.tags
}

resource "aws_dynamodb_table" "subscriptions" {
  name         = "${local.name}-subscriptions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "subscription_id"

  attribute {
    name = "subscription_id"
    type = "S"
  }

  tags = local.tags
}
