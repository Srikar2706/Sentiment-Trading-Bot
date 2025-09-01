#!/bin/bash

# Local Deployment Script for Sentiment Trading MVP
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting local deployment for Sentiment Trading MVP${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose first.${NC}"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo -e "${YELLOW}⚠️  Terraform not found. Will use Docker Compose only.${NC}"
    USE_TERRAFORM=false
else
    USE_TERRAFORM=true
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp env.example .env
    echo -e "${YELLOW}Please edit .env with your API keys (optional for demo)${NC}"
fi

# Build Docker images
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose -f docker-compose.production.yml build

# Choose deployment method
if [ "$USE_TERRAFORM" = true ]; then
    echo -e "${YELLOW}Using Terraform for deployment...${NC}"
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform/local/terraform.tfvars" ]; then
        echo -e "${YELLOW}Creating terraform.tfvars from template...${NC}"
        cp terraform/local/terraform.tfvars.example terraform/local/terraform.tfvars
        echo -e "${YELLOW}Please edit terraform/local/terraform.tfvars with your values${NC}"
    fi
    
    # Deploy with Terraform
    cd terraform/local
    terraform init
    terraform plan -out=tfplan
    
    echo -e "${YELLOW}Do you want to apply this plan? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}Applying Terraform plan...${NC}"
        terraform apply tfplan
    else
        echo -e "${YELLOW}Deployment cancelled${NC}"
        exit 0
    fi
    
    cd ../..
else
    echo -e "${YELLOW}Using Docker Compose for deployment...${NC}"
    
    # Start services with Docker Compose
    docker-compose -f docker-compose.production.yml up -d
    
    # Wait for services to be ready
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 30
    
    # Check service health
    echo -e "${YELLOW}Checking service health...${NC}"
    docker-compose -f docker-compose.production.yml ps
fi

# Get service URLs
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${YELLOW}Getting service URLs...${NC}"

echo -e "${GREEN}🎉 Service URLs:${NC}"
echo -e "${GREEN}Dashboard:${NC} http://localhost:8501"
echo -e "${GREEN}Sentiment API:${NC} http://localhost:8001"
echo -e "${GREEN}Trading API:${NC} http://localhost:8002"
echo -e "${GREEN}Prometheus:${NC} http://localhost:9090"
echo -e "${GREEN}Grafana:${NC} http://localhost:3000"
echo -e "${GREEN}Nginx (Load Balancer):${NC} http://localhost:80"

echo -e "${YELLOW}📊 Monitoring:${NC}"
echo -e "${YELLOW}Grafana Login:${NC} admin / admin"
echo -e "${YELLOW}Prometheus:${NC} http://localhost:9090"

echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo -e "${YELLOW}1. For production, update passwords in .env or terraform.tfvars${NC}"
echo -e "${YELLOW}2. Add your API keys to enable real trading functionality${NC}"
echo -e "${YELLOW}3. Configure SSL certificates for production use${NC}"
echo -e "${YELLOW}4. Set up proper monitoring and alerting${NC}"

echo -e "${GREEN}🚀 Local deployment completed!${NC}"
echo -e "${GREEN}Your sentiment trading system is now running locally!${NC}"
