#!/bin/bash

# Deploy Sentiment Trading MVP to Kubernetes
set -e

echo "🚀 Deploying Sentiment Trading MVP to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if we have a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ No Kubernetes cluster found. Please start your cluster first."
    echo "   For local development, you can use:"
    echo "   - minikube start"
    echo "   - kind create cluster"
    echo "   - docker-desktop (if enabled)"
    exit 1
fi

echo "📋 Creating namespace..."
kubectl apply -f ../k8s-manifests/namespace.yaml

echo "🔧 Creating ConfigMap..."
kubectl apply -f ../k8s-manifests/configmap.yaml

echo "🔐 Creating API secrets..."
kubectl apply -f ../k8s-manifests/api-secrets.yaml

echo "🗄️ Deploying Redis..."
kubectl apply -f ../k8s-manifests/redis-deployment.yaml

echo "💾 Deploying PostgreSQL..."
kubectl apply -f ../k8s-manifests/postgres-deployment.yaml

echo "⏳ Waiting for database services to be ready..."
kubectl wait --for=condition=ready pod -l app=cache-service -n sentiment-trading --timeout=300s
kubectl wait --for=condition=ready pod -l app=db-service -n sentiment-trading --timeout=300s

echo "📊 Deploying sentiment service..."
kubectl apply -f ../k8s-manifests/sentiment-service-deployment.yaml

echo "🤖 Deploying trading service..."
kubectl apply -f ../k8s-manifests/trading-service-deployment.yaml

echo "📈 Deploying dashboard service..."
kubectl apply -f ../k8s-manifests/dashboard-service-deployment.yaml

echo "⏳ Waiting for all services to be ready..."
kubectl wait --for=condition=ready pod -l app=sentiment-service -n sentiment-trading --timeout=300s
kubectl wait --for=condition=ready pod -l app=trading-service -n sentiment-trading --timeout=300s
kubectl wait --for=condition=ready pod -l app=dashboard-service -n sentiment-trading --timeout=300s

echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
kubectl get pods -n sentiment-trading

echo ""
echo "🌐 Access Dashboard:"
echo "   kubectl port-forward -n sentiment-trading svc/dashboard-service 8501:8501"
echo "   Then open: http://localhost:8501"

echo ""
echo "📋 Useful Commands:"
echo "   kubectl logs -f -l app=sentiment-service -n sentiment-trading"
echo "   kubectl logs -f -l app=trading-service -n sentiment-trading"
echo "   kubectl logs -f -l app=dashboard-service -n sentiment-trading"
echo "   kubectl get svc -n sentiment-trading"
echo "   kubectl describe pod <pod-name> -n sentiment-trading"
