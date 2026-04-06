variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "oil-price-tracker"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-northeast-1"
}

variable "notification_email" {
  description = "Email for SNS subscription"
  type        = string
  default     = "example@gmail.com"
}

variable "ec2_instance_type" {
  description = "EC2 instance type for frontend"
  type        = string
  default     = "t2.micro"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH into EC2"
  type        = string
  default     = "0.0.0.0/0"
}

variable "influxdb_organization" {
  description = "Organization name for InfluxDB"
  type        = string
  default     = "university_project"
}

variable "influxdb_bucket" {
  description = "Initial bucket name for InfluxDB"
  type        = string
  default     = "oil_prices"
}

variable "influxdb_username" {
  description = "Admin username for InfluxDB"
  type        = string
  default     = "admin"
}

variable "influxdb_password" {
  description = "Admin password for InfluxDB (Must be 8-32 characters)"
  type        = string
  sensitive   = true
  default     = "password"
}