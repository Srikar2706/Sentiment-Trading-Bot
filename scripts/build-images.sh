#!/bin/bash

# Build Docker images for Sentiment Trading MVP
set -e

echo "🚀 Building Docker images for Sentiment Trading MVP..."

# Build sentiment service
echo "📊 Building sentiment service..."
cd ../sentiment-service
docker build -t sentiment-service:latest .
echo "✅ Sentiment service built successfully"

# Build trading service
echo "🤖 Building trading service..."
cd ../trading-service
docker build -t trading-service:latest .
echo "✅ Trading service built successfully"

# Build dashboard service
echo "📈 Building dashboard service..."
cd ../dashboard-service
docker build -t dashboard-service:latest .
echo "✅ Dashboard service built successfully"

echo "🎉 All Docker images built successfully!"
echo ""
echo "Available images:"
docker images | grep -E "(sentiment-service|trading-service|dashboard-service)"

echo ""
echo "Next steps:"
echo "1. Copy env.example to .env and fill in your API keys"
echo "2. Run: docker-compose up -d"
echo "3. Or deploy to Kubernetes: kubectl apply -f k8s-manifests/"
