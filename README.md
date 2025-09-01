# Sentiment Trading Bot

A trading bot that analyzes social media and news sentiment to make automated trades. Built with Python, FastAPI, and FinBERT.

## What it does

- Scrapes Twitter, Reddit, and news for stock mentions
- Analyzes sentiment using FinBERT (financial BERT model)
- Makes trading decisions based on sentiment scores
- Shows everything in a real-time dashboard

## Services

- **Sentiment Service** - Handles sentiment analysis and data collection
- **Trading Service** - Makes the actual trades via Alpaca API
- **Dashboard** - Streamlit app to monitor everything
- **Database** - PostgreSQL to store data
- **Cache** - Redis for fast data access

## Tech Stack

- **Backend**: FastAPI, Python
- **ML**: FinBERT, PyTorch
- **Trading**: Alpaca API
- **Database**: PostgreSQL, Redis
- **Frontend**: Streamlit, Plotly
- **Infrastructure**: Docker, Terraform

## Prerequisites

- Docker
- Python 3.11+
- API keys (optional for demo):
  - Twitter API
  - Reddit API
  - News API
  - Alpaca Trading API

## Quick Start

### 1. Setup

```bash
git clone <repository-url>
cd sentiment-trading-mvp
cp env.example .env
# Add your API keys to .env (optional)
```

### 2. Run Locally

```bash
# Start everything with Docker
docker-compose up -d

# Or use the deployment script
./scripts/deploy-local.sh
```

### 3. Access Dashboard

Open http://localhost:8501 in your browser

## Configuration

### Trading Settings

Edit `configs/trading_config.json` to change:
- Sentiment thresholds for different stocks
- Weights for Twitter vs Reddit vs News
- Position size limits
- Risk settings

### Environment Variables

Add your API keys to `.env`:

```bash
# API Keys (get these from the respective platforms)
TWITTER_API_KEY=
TWITTER_API_SECRET=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
NEWS_API_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
```

## API Endpoints

### Sentiment Service (Port 8001)
- `GET /health` - Health check
- `POST /analyze` - Analyze text sentiment
- `POST /ingest` - Start data ingestion

### Trading Service (Port 8002)
- `GET /health` - Health check
- `POST /trade` - Execute manual trade
- `GET /portfolio` - Get portfolio positions
- `POST /bot/start` - Start trading bot

### Dashboard (Port 8501)
- Web dashboard at `http://localhost:8501`

## Monitoring

### Health Checks

```bash
# Check if services are running
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Logs

```bash
# View logs
docker-compose logs -f [service-name]
```

## How it Works

1. **Data Collection**: Gets data from Twitter, Reddit, and news
2. **Sentiment Analysis**: FinBERT analyzes text sentiment (-1 to +1)
3. **Aggregation**: Combines sentiment scores for each stock
4. **Trading**: Buys on positive sentiment, sells on negative
5. **Risk Management**: Limits position sizes and losses

## Disclaimer

**This is a demo project. Don't use it for real trading without proper testing.**

- Use paper trading only
- Test thoroughly first
- Add proper risk controls

## Security

- API keys stored in environment variables
- No hardcoded credentials
- Health checks and monitoring

## Development

### Project Structure

```
sentiment-trading-mvp/
├── sentiment-service/     # Sentiment analysis
├── trading-service/       # Trading bot
├── dashboard-service/     # Dashboard
├── configs/              # Config files
├── scripts/              # Deploy scripts
└── docker-compose.yml    # Local setup
```

### Adding Features

1. Add new data sources in `sentiment-service/main.py`
2. Update config in `trading_config.json`
3. Test with sample data

### Customizing Trading

1. Modify `run_trading_bot()` in `trading-service/main.py`
2. Adjust sentiment thresholds
3. Add your own risk management

## Deployment

### Local Setup (Recommended)

```bash
# Quick start
./scripts/deploy-local.sh

# Or manually
docker-compose up -d
```

Access dashboard at http://localhost:8501

### AWS Setup (Full Cloud)

```bash
# Deploy to AWS
./scripts/deploy-terraform.sh
./scripts/deploy-aws.sh
```

## Roadmap

- [ ] More sentiment models
- [ ] Technical analysis
- [ ] Backtesting
- [ ] Better risk management
- [ ] More exchanges
