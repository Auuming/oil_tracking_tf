resource "aws_timestreaminfluxdb_db_instance" "oil_prices" {
  # 1. Instance Configuration
  name             = replace("${local.name}influx", "-", "")
  db_instance_type = "db.influx.medium"
  allocated_storage = 20

  publicly_accessible = true

  # 2. Database Credentials & Setup
  organization      = var.influxdb_organization
  bucket            = var.influxdb_bucket
  username          = var.influxdb_username
  password          = var.influxdb_password

  # 3. Required Network Placement
  # Timestream for InfluxDB must be placed inside a VPC.
  # Replace these with your actual subnet and security group variables/data sources.
  vpc_subnet_ids = slice(data.aws_subnets.default.ids, 0, 3)
  vpc_security_group_ids = [aws_security_group.influx_sg.id] 

  tags = local.tags
}

data "aws_secretsmanager_secret_version" "influx_creds" {
  # OpenTofu automatically waits for the DB to be created because of this reference
  secret_id = aws_timestreaminfluxdb_db_instance.oil_prices.influx_auth_parameters_secret_arn
}

data "external" "influx_token" {
  program = ["python", "${path.module}/get_token.py"]

  query = {
    url      = "https://${aws_timestreaminfluxdb_db_instance.oil_prices.endpoint}:8086"
    username = jsondecode(data.aws_secretsmanager_secret_version.influx_creds.secret_string)["username"]
    password = jsondecode(data.aws_secretsmanager_secret_version.influx_creds.secret_string)["password"]
    org      = jsondecode(data.aws_secretsmanager_secret_version.influx_creds.secret_string)["organization"]
  }
}