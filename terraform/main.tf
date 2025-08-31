terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC and Networking
resource "aws_vpc" "sentiment_trading_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "sentiment-trading-vpc"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_subnet" "private_subnets" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.sentiment_trading_vpc.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "sentiment-trading-private-${count.index + 1}"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_subnet" "public_subnets" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.sentiment_trading_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "sentiment-trading-public-${count.index + 1}"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.sentiment_trading_vpc.id

  tags = {
    Name        = "sentiment-trading-igw"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name        = "sentiment-trading-nat-eip"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_subnets[0].id

  tags = {
    Name        = "sentiment-trading-nat"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.sentiment_trading_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "sentiment-trading-public-rt"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.sentiment_trading_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name        = "sentiment-trading-private-rt"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private_subnets[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "rds" {
  name_prefix = "sentiment-trading-rds-"
  vpc_id      = aws_vpc.sentiment_trading_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_worker.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "sentiment-trading-rds-sg"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_security_group" "elasticache" {
  name_prefix = "sentiment-trading-elasticache-"
  vpc_id      = aws_vpc.sentiment_trading_vpc.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_worker.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "sentiment-trading-elasticache-sg"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_security_group" "eks_worker" {
  name_prefix = "sentiment-trading-eks-worker-"
  vpc_id      = aws_vpc.sentiment_trading_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "sentiment-trading-eks-worker-sg"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "rds" {
  name       = "sentiment-trading-rds-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id

  tags = {
    Name        = "sentiment-trading-rds-subnet-group"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

resource "aws_db_instance" "postgresql" {
  identifier = "sentiment-trading-postgresql"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.rds_instance_class

  allocated_storage     = 20
  storage_type          = "gp2"
  storage_encrypted     = true
  multi_az              = false
  publicly_accessible   = false
  skip_final_snapshot   = true
  deletion_protection   = false

  db_name  = "sentiment_trading"
  username = "trading_user"
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  tags = {
    Name        = "sentiment-trading-postgresql"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "redis" {
  name       = "sentiment-trading-cache-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id
}

resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "sentiment-trading-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "sentiment-trading-redis"
  engine               = "redis"
  node_type            = var.elasticache_node_type
  num_cache_nodes      = 1
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.elasticache.id]

  tags = {
    Name        = "sentiment-trading-redis"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# ECR Repositories
resource "aws_ecr_repository" "services" {
  for_each = toset(["sentiment-service", "trading-service", "dashboard-service"])

  name                 = "sentiment-trading-${each.value}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "sentiment-trading-${each.value}"
    Project     = "sentiment-trading"
    Environment = var.environment
  }
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.sentiment_trading_vpc.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private_subnets[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public_subnets[*].id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgresql.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "ecr_repository_urls" {
  description = "ECR repository URLs"
  value = {
    for service, repo in aws_ecr_repository.services : service => repo.repository_url
  }
}
