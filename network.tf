# Elastic IP for the NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.tags, { Name = "${local.name}-eip" })
}

# NAT Gateway in existing public (default) subnet
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = data.aws_subnets.default.ids[0]
  tags          = merge(local.tags, { Name = "${local.name}-nat" })
}

# NEW Private Subnet for the Lambda function
resource "aws_subnet" "private" {
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = "172.31.128.0/20" 
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = merge(local.tags, { Name = "${local.name}-private-subnet" })
}

# Private Route Table that points internet traffic to the NAT Gateway
resource "aws_route_table" "private" {
  vpc_id = data.aws_vpc.default.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  tags = merge(local.tags, { Name = "${local.name}-private-rt" })
}

# 5. New Private Subnet for private route table association
resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}