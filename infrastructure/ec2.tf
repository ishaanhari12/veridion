# SSH Key Pair
resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = file("~/.ssh/veridion.pub")
}

# EC2 Instance
resource "aws_instance" "main" {
  ami                    = "ami-0b45ae66668865cd6"  # Ubuntu 24.04 LTS eu-west-2
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  key_name               = aws_key_pair.main.key_name

  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io docker-compose-plugin awscli
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu

    # Download ML models from S3
    aws s3 cp s3://${var.project_name}-models-${var.environment}/isolation_forest.joblib /home/ubuntu/models/
    aws s3 cp s3://${var.project_name}-models-${var.environment}/xgboost_model.joblib /home/ubuntu/models/
  EOF

  tags = {
    Name        = "${var.project_name}-api"
    Environment = var.environment
  }
}

# Elastic IP so the server has a fixed public IP
resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"

  tags = { Name = "${var.project_name}-eip" }
}