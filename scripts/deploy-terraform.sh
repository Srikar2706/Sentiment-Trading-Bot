#!/bin/bash

# Terraform Deployment Script for AWS Infrastructure
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏗️  Starting Terraform deployment for AWS infrastructure${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Check if terraform.tfvars exists
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo -e "${YELLOW}Creating terraform.tfvars from example...${NC}"
    cp terraform/terraform.tfvars.example terraform/terraform.tfvars
    echo -e "${RED}⚠️  Please edit terraform/terraform.tfvars with your actual values before continuing${NC}"
    echo -e "${YELLOW}Especially update the db_password variable${NC}"
    exit 1
fi

# Navigate to terraform directory
cd terraform

# Initialize Terraform
echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init

# Plan deployment
echo -e "${YELLOW}Planning deployment...${NC}"
terraform plan -out=tfplan

# Ask for confirmation
echo -e "${YELLOW}Do you want to apply this plan? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}Applying Terraform plan...${NC}"
    terraform apply tfplan
else
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Get outputs
echo -e "${GREEN}✅ Infrastructure deployed successfully!${NC}"
echo -e "${YELLOW}Getting infrastructure outputs...${NC}"

VPC_ID=$(terraform output -raw vpc_id)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
PRIVATE_SUBNETS=$(terraform output -raw private_subnet_ids)
PUBLIC_SUBNETS=$(terraform output -raw public_subnet_ids)

echo -e "${GREEN}🎉 Infrastructure Summary:${NC}"
echo -e "${GREEN}VPC ID:${NC} $VPC_ID"
echo -e "${GREEN}RDS Endpoint:${NC} $RDS_ENDPOINT"
echo -e "${GREEN}Redis Endpoint:${NC} $REDIS_ENDPOINT"
echo -e "${GREEN}Private Subnets:${NC} $PRIVATE_SUBNETS"
echo -e "${GREEN}Public Subnets:${NC} $PUBLIC_SUBNETS"

# Update Kubernetes manifests with actual values
echo -e "${YELLOW}Updating Kubernetes manifests with infrastructure details...${NC}"
cd ..

# Update load balancer configs with subnet IDs
echo -e "${YELLOW}Please update the following files with the actual values:${NC}"
echo -e "${YELLOW}1. k8s-manifests/aws-load-balancer.yaml - Update subnet IDs${NC}"
echo -e "${YELLOW}2. k8s-manifests/aws-secrets.yaml - Update endpoints and credentials${NC}"
echo -e "${YELLOW}3. aws-configs/rds-config.json - Update security group IDs${NC}"
echo -e "${YELLOW}4. aws-configs/elasticache-config.json - Update security group IDs${NC}"

echo -e "${GREEN}🚀 Terraform deployment completed!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "${YELLOW}1. Create EKS cluster using eksctl or the provided config${NC}"
echo -e "${YELLOW}2. Update Kubernetes manifests with the actual values above${NC}"
echo -e "${YELLOW}3. Run the AWS deployment script: ./scripts/deploy-aws.sh${NC}"
