resource "aws_security_group" "lambda_sg" {
  name        = "${local.name}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = data.aws_vpc.default.id
  tags        = merge(local.tags, { Name = "${local.name}-lambda-sg" })
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis-sg"
  description = "Allow Redis from Lambda"
  vpc_id      = data.aws_vpc.default.id
  tags        = merge(local.tags, { Name = "${local.name}-redis-sg" })
}

# Allow Lambda to reach the Internet
resource "aws_vpc_security_group_egress_rule" "lambda_to_internet" {
  security_group_id = aws_security_group.lambda_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

# Allow Lambda to send data to Redis
resource "aws_vpc_security_group_egress_rule" "lambda_to_redis" {
  security_group_id            = aws_security_group.lambda_sg.id
  referenced_security_group_id = aws_security_group.redis.id
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
}

# Allow Redis to accept data from Lambda
resource "aws_vpc_security_group_ingress_rule" "redis_from_lambda" {
  security_group_id            = aws_security_group.redis.id
  referenced_security_group_id = aws_security_group.lambda_sg.id
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
}