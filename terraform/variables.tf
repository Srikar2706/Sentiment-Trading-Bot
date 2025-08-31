variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "eks_cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "sentiment-trading-cluster"
}

variable "eks_node_group_instance_type" {
  description = "EKS node group instance type"
  type        = string
  default     = "t3.medium"
}

variable "eks_node_group_desired_capacity" {
  description = "EKS node group desired capacity"
  type        = number
  default     = 2
}

variable "eks_node_group_min_size" {
  description = "EKS node group minimum size"
  type        = number
  default     = 1
}

variable "eks_node_group_max_size" {
  description = "EKS node group maximum size"
  type        = number
  default     = 4
}
