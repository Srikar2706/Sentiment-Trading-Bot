#!/bin/bash

# AWS Deployment Script for Sentiment Trading MVP
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="sentiment-trading-cluster"
REGION="us-west-2"
NAMESPACE="sentiment-trading"

echo -e "${GREEN}🚀 Starting AWS deployment for Sentiment Trading MVP${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v eksctl &> /dev/null; then
    echo -e "${RED}❌ eksctl not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Create EKS cluster
echo -e "${YELLOW}Creating EKS cluster...${NC}"
if ! eksctl get cluster --name $CLUSTER_NAME --region $REGION &> /dev/null; then
    eksctl create cluster -f aws-configs/eks-cluster-config.yaml
else
    echo -e "${GREEN}✅ Cluster already exists${NC}"
fi

# Update kubeconfig
echo -e "${YELLOW}Updating kubeconfig...${NC}"
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

# Create namespace
echo -e "${YELLOW}Creating namespace...${NC}"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create AWS resources (RDS, ElastiCache)
echo -e "${YELLOW}Creating AWS managed services...${NC}"
echo -e "${YELLOW}Note: You'll need to create RDS and ElastiCache manually or use Terraform/CloudFormation${NC}"

# Build and push Docker images to ECR
echo -e "${YELLOW}Setting up ECR repositories...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Create ECR repositories
for service in sentiment-service trading-service dashboard-service; do
    if ! aws ecr describe-repositories --repository-names sentiment-trading-$service --region $REGION &> /dev/null; then
        aws ecr create-repository --repository-name sentiment-trading-$service --region $REGION
    fi
done

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push images
echo -e "${YELLOW}Building and pushing Docker images...${NC}"
for service in sentiment-service trading-service dashboard-service; do
    echo -e "${YELLOW}Building $service...${NC}"
    docker build -t $ECR_REGISTRY/sentiment-trading-$service:latest ./$service/
    docker push $ECR_REGISTRY/sentiment-trading-$service:latest
done

# Update Kubernetes manifests with ECR images
echo -e "${YELLOW}Updating Kubernetes manifests...${NC}"
for deployment in k8s-manifests/*-deployment.yaml; do
    if [ -f "$deployment" ]; then
        sed -i.bak "s|image: .*|image: $ECR_REGISTRY/sentiment-trading-$(basename $deployment | sed 's/-deployment.yaml//'):latest|g" $deployment
    fi
done

# Apply Kubernetes manifests
echo -e "${YELLOW}Deploying to Kubernetes...${NC}"
kubectl apply -f k8s-manifests/namespace.yaml
kubectl apply -f k8s-manifests/configmap.yaml
kubectl apply -f k8s-manifests/aws-secrets.yaml
kubectl apply -f k8s-manifests/sentiment-service-deployment.yaml
kubectl apply -f k8s-manifests/trading-service-deployment.yaml
kubectl apply -f k8s-manifests/dashboard-service-deployment.yaml
kubectl apply -f k8s-manifests/aws-load-balancer.yaml

# Wait for deployments
echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/sentiment-service -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/trading-service -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/dashboard-service -n $NAMESPACE

# Get Load Balancer URLs
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${YELLOW}Getting Load Balancer URLs...${NC}"

# Wait for Load Balancer to be provisioned
sleep 30

DASHBOARD_LB=$(kubectl get svc dashboard-load-balancer -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Still provisioning...")
SENTIMENT_LB=$(kubectl get svc sentiment-api-load-balancer -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Still provisioning...")
TRADING_LB=$(kubectl get svc trading-api-load-balancer -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Still provisioning...")

echo -e "${GREEN}🎉 Deployment Summary:${NC}"
echo -e "${GREEN}Dashboard:${NC} http://$DASHBOARD_LB"
echo -e "${GREEN}Sentiment API:${NC} http://$SENTIMENT_LB"
echo -e "${GREEN}Trading API:${NC} http://$TRADING_LB"
echo -e "${GREEN}Cluster:${NC} $CLUSTER_NAME"
echo -e "${GREEN}Region:${NC} $REGION"

echo -e "${YELLOW}⚠️  Important:${NC}"
echo -e "${YELLOW}1. Update aws-secrets.yaml with your actual API keys and database credentials${NC}"
echo -e "${YELLOW}2. Create RDS PostgreSQL and ElastiCache Redis instances${NC}"
echo -e "${YELLOW}3. Update security groups and subnet IDs in load balancer configs${NC}"
echo -e "${YELLOW}4. Configure CloudWatch monitoring and logging${NC}"

echo -e "${GREEN}🚀 AWS deployment completed!${NC}"
