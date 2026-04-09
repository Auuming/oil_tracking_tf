# dynamodb.tf

# 1. Table for tracking Oil Prices
resource "aws_dynamodb_table" "prices" {
  name         = "${local.name}-prices"
  billing_mode = "PAY_PER_REQUEST"
  
  # Partition Key: Combining Retailer and Oil Type (e.g., "PTT#Gasohol95")
  hash_key     = "RetailerOilType"
  # Sort Key: The date of the price (e.g., "2023-10-25")
  range_key    = "Date"

  attribute {
    name = "RetailerOilType"
    type = "S"
  }
  attribute {
    name = "Date"
    type = "S"
  }

  tags = local.tags
}

# 2. Table for tracking Users/Emails for SNS
resource "aws_dynamodb_table" "users" {
  name         = "${local.name}-users"
  billing_mode = "PAY_PER_REQUEST"
  
  hash_key     = "Email"

  attribute {
    name = "Email"
    type = "S"
  }

  tags = local.tags
}