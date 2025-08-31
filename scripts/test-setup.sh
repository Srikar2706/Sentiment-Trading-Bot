#!/bin/bash

# Test script for Sentiment Trading MVP
set -e

echo "🧪 Testing Sentiment Trading MVP Setup..."

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker Compose is available"

# Check if kubectl is available
if command -v kubectl &> /dev/null; then
    echo "✅ kubectl is available"
    
    # Check if we have a cluster
    if kubectl cluster-info &> /dev/null; then
        echo "✅ Kubernetes cluster is accessible"
        echo "   Cluster: $(kubectl cluster-info | head -n1)"
    else
        echo "⚠️  No Kubernetes cluster found (this is okay for local development)"
    fi
else
    echo "⚠️  kubectl is not installed (this is okay for local development)"
fi

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python is available: $PYTHON_VERSION"
else
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Check if required Python packages can be installed
echo "📦 Testing Python package installation..."
python3 -c "
import sys
if sys.version_info < (3, 11):
    print('❌ Python 3.11+ is required')
    sys.exit(1)
print('✅ Python version is compatible')
"

# Check project structure
echo "📁 Checking project structure..."
REQUIRED_DIRS=("sentiment-service" "trading-service" "dashboard-service" "db-service" "cache-service" "k8s-manifests" "configs" "scripts")
REQUIRED_FILES=("docker-compose.yml" "env.example" "requirements.txt" "README.md")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ Directory exists: $dir"
    else
        echo "❌ Missing directory: $dir"
    fi
done

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ File exists: $file"
    else
        echo "❌ Missing file: $file"
    fi
done

# Check Docker images
echo "🐳 Checking Docker images..."
if docker images | grep -q "sentiment-service\|trading-service\|dashboard-service"; then
    echo "✅ Some Docker images are built"
    docker images | grep -E "(sentiment-service|trading-service|dashboard-service)"
else
    echo "⚠️  No Docker images built yet. Run './scripts/build-images.sh' to build them."
fi

# Check environment file
if [ -f ".env" ]; then
    echo "✅ Environment file (.env) exists"
    
    # Check if API keys are configured
    if grep -q "your_.*_here" .env; then
        echo "⚠️  Some API keys still have placeholder values. Please update .env with your actual API keys."
    else
        echo "✅ Environment file appears to be configured"
    fi
else
    echo "⚠️  Environment file (.env) not found. Copy env.example to .env and configure your API keys."
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Configure your API keys in .env file"
echo "2. Build Docker images: ./scripts/build-images.sh"
echo "3. Start services locally: docker-compose up -d"
echo "4. Or deploy to Kubernetes: ./scripts/deploy-k8s.sh"
echo ""
echo "📚 For more information, see README.md"
echo ""
echo "🧪 Setup test completed!"
