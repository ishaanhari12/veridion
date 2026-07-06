output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_eip.main.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket for ML models"
  value       = aws_s3_bucket.models.bucket
}

output "api_url" {
  description = "FastAPI backend URL"
  value       = "http://${aws_eip.main.public_ip}:8000"
}