# Sentiment Trading MVP

Trading bot that uses sentiment analysis on social media/news to make trades. Uses FinBERT and Alpaca API.

## Architecture

5 services:

1. **Sentiment Service** - FinBERT sentiment analysis + gets data from Twitter/Reddit/News
2. **Trading Service** - trading bot that uses sentiment to make trades
3. **Dashboard Service** - Streamlit dashboard to see what's happening
4. **Database Service** - PostgreSQL for data
5. **Cache Service** - Redis for caching

## Features

- Sentiment analysis from Twitter, Reddit, News APIs
- FinBERT for financial sentiment
- Automated trading with Alpaca API
- Real-time dashboard
- Configurable weights for different data sources
- Basic risk management
- Docker/K8s ready

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Sentiment Analysis**: FinBERT, Transformers, PyTorch
- **Trading**: Alpaca API, yfinance
- **Database**: PostgreSQL, Redis
- **Dashboard**: Streamlit, Plotly
- **Infrastructure**: Docker, Kubernetes
- **Monitoring**: Health checks, structured logging

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Kubernetes cluster (minikube, kind, or cloud)
- API keys for:
  - Twitter API
  - Reddit API
  - News API
  - Alpaca Trading API

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd sentiment-trading-mvp
cp env.example .env
# Edit .env with your API keys
```

### 2. Local Development with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f sentiment-service
```

### 3. Kubernetes Deployment

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Build Docker images
./scripts/build-images.sh

# Deploy to Kubernetes
./scripts/deploy-k8s.sh

# Access dashboard
kubectl port-forward -n sentiment-trading svc/dashboard-service 8501:8501
```

## 🔧 Configuration

### Trading Configuration

Edit `configs/trading_config.json` to customize:

- Symbol-specific sentiment thresholds
- Data source weights (Twitter, Reddit, News)
- Position size limits
- Risk management parameters

### Environment Variables

Key environment variables in `.env`:

```bash
# API Keys
TWITTER_API_KEY=your_key_here
REDDIT_CLIENT_ID=your_id_here
NEWS_API_KEY=your_key_here
ALPACA_API_KEY=your_key_here

# Service URLs
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://localhost:5432/sentiment_trading
```

## 📊 API Endpoints

### Sentiment Service (Port 8001)

- `GET /health` - Health check
- `POST /analyze` - Analyze text sentiment
- `POST /ingest` - Start data ingestion
- `GET /sentiment/{symbol}` - Get symbol sentiment

### Trading Service (Port 8002)

- `GET /health` - Health check
- `POST /trade` - Execute manual trade
- `GET /portfolio` - Get portfolio positions
- `GET /sentiment/{symbol}` - Get aggregated sentiment
- `POST /bot/start` - Start trading bot
- `POST /bot/stop` - Stop trading bot

### Dashboard Service (Port 8501)

- Web-based dashboard accessible at `http://localhost:8501`

## 🔍 Monitoring

### Health Checks

All services include health check endpoints:

```bash
# Check sentiment service
curl http://localhost:8001/health

# Check trading service
curl http://localhost:8002/health

# Check dashboard
curl http://localhost:8501/_stcore/health
```

### Logs

```bash
# Docker Compose
docker-compose logs -f [service-name]

# Kubernetes
kubectl logs -f -l app=[service-name] -n sentiment-trading
```

## 📈 Trading Strategy

The system implements a sentiment-driven trading strategy:

1. **Data Collection**: Continuously ingests data from multiple sources
2. **Sentiment Analysis**: FinBERT analyzes text sentiment (-1 to +1 scale)
3. **Aggregation**: Weighted sentiment scores per symbol
4. **Decision Making**: Buy signals on positive sentiment, sell on negative
5. **Risk Management**: Position sizing and loss limits
6. **Execution**: Automated trades via Alpaca API

## 🚨 Risk Disclaimer

⚠️ **This is a demonstration MVP and should NOT be used for actual trading without proper risk assessment and testing.**

- Use paper trading accounts only
- Test thoroughly before live deployment
- Implement additional risk controls
- Monitor performance continuously
- Consider regulatory compliance

## 🔒 Security

- API keys stored in Kubernetes secrets
- Environment-based configuration
- No hardcoded credentials
- Health checks and monitoring
- Structured logging for audit trails

## 📚 Development

### Project Structure

```
sentiment-trading-mvp/
├── sentiment-service/     # FinBERT + data ingestion
├── trading-service/       # Trading bot + Alpaca
├── dashboard-service/     # Streamlit dashboard
├── db-service/           # PostgreSQL setup
├── cache-service/        # Redis setup
├── k8s-manifests/       # Kubernetes deployments
├── configs/             # Configuration files
├── scripts/             # Build/deploy scripts
└── docker-compose.yml   # Local development
```

### Adding New Data Sources

1. Implement ingestion function in `sentiment-service/main.py`
2. Add to configuration in `trading_config.json`
3. Update weights and thresholds
4. Test with sample data

### Customizing Trading Logic

1. Modify `run_trading_bot()` in `trading-service/main.py`
2. Adjust sentiment thresholds
3. Implement custom risk management
4. Add technical indicators

## 🚀 Production Deployment

### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster --name sentiment-trading --region us-west-2

# Deploy to EKS
kubectl apply -f k8s-manifests/

# Use AWS Load Balancer
kubectl patch svc dashboard-service -p '{"spec":{"type":"LoadBalancer"}}'
```

### Cloud Services

- **Database**: AWS RDS PostgreSQL
- **Cache**: AWS ElastiCache Redis
- **Monitoring**: CloudWatch + Prometheus
- **Logging**: CloudWatch Logs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## 📄 License

This project is for educational and demonstration purposes. Please ensure compliance with all applicable laws and regulations before using in production.

## 🆘 Support

For issues and questions:

1. Check the logs and health endpoints
2. Review configuration files
3. Verify API keys and connectivity
4. Check Kubernetes pod status
5. Open an issue with detailed error information

## 🔮 Roadmap

- [ ] Additional sentiment models
- [ ] Technical analysis integration
- [ ] Backtesting framework
- [ ] Advanced risk management
- [ ] Multi-exchange support
- [ ] Machine learning optimization
- [ ] Real-time alerts
- [ ] Performance analytics

---

**Happy Trading! 📈💰**
