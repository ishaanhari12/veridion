variable "project_name" {
  description = "Project name used for resource naming"
  default     = "veridion"
}

variable "environment" {
  description = "Deployment environment"
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  default     = "eu-west-2"
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "FastAPI JWT secret key"
  type        = string
  sensitive   = true
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  default     = "t3.micro"
}

variable "db_instance_class" {
  description = "RDS instance class"
  default     = "db.t3.micro"
}