import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import alpaca_trade_api as tradeapi
import yfinance as yf
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# fastapi app
app = FastAPI(
    title="Trading Service",
    description="Trading bot with sentiment",
    version="1.0.0"
)

# config
class Config:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.postgres_url = os.getenv("POSTGRES_URL", "postgresql://localhost:5432/sentiment_trading")
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.alpaca_base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        self.sentiment_service_url = os.getenv("SENTIMENT_SERVICE_URL", "http://sentiment-service:8001")
        self.trade_frequency = int(os.getenv("TRADE_FREQUENCY", "300"))  # 5 min
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "10000"))
        self.sentiment_threshold = float(os.getenv("SENTIMENT_THRESHOLD", "0.6"))

config = Config()

# Initialize connections
redis_client = None
postgres_conn = None
alpaca_api = None
scheduler = AsyncIOScheduler()

# Pydantic models
class TradeRequest(BaseModel):
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    sentiment_score: Optional[float] = None

class PortfolioPosition(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    total_value: float
    unrealized_pnl: float
    last_updated: datetime

class SentimentAggregation(BaseModel):
    symbol: str
    weighted_score: float
    source_count: int
    last_updated: datetime

# Initialize services
def init_redis():
    global redis_client
    try:
        redis_client = redis.from_url(config.redis_url)
        redis_client.ping()
        logger.info("redis connected")
    except Exception as e:
        logger.error(f"redis failed: {e}")
        redis_client = None

def init_postgres():
    global postgres_conn
    try:
        postgres_conn = psycopg2.connect(config.postgres_url)
        logger.info("postgres connected")
    except Exception as e:
        logger.error(f"postgres failed: {e}")
        postgres_conn = None

def init_alpaca():
    global alpaca_api
    if config.alpaca_api_key and config.alpaca_secret_key:
        try:
            alpaca_api = tradeapi.REST(
                config.alpaca_api_key,
                config.alpaca_secret_key,
                config.alpaca_base_url,
                api_version='v2'
            )
            # test connection
            account = alpaca_api.get_account()
            logger.info(f"alpaca connected: {account.id}")
        except Exception as e:
            logger.error(f"alpaca failed: {e}")
            alpaca_api = None
    else:
        logger.warning("no alpaca creds")

# Sentiment aggregation
async def aggregate_sentiment(symbol: str) -> Optional[float]:
    """Aggregate sentiment from multiple sources using weighted configuration"""
    try:
        # Load trading configuration
        config_data = load_trading_config()
        symbol_config = config_data.get("trading", {}).get("symbols", {}).get(symbol, {})
        
        if not symbol_config:
            logger.warning("No configuration found for symbol", symbol=symbol)
            return None
        
        weights = symbol_config.get("weights", config_data.get("trading", {}).get("sentiment_weights", {}))
        
        # Get sentiment data from Redis
        if not redis_client:
            return None
        
        total_weighted_score = 0
        total_weight = 0
        source_count = 0
        
        for source, weight in weights.items():
            pattern = f"sentiment:{symbol}:{source}:*"
            keys = redis_client.keys(pattern)
            
            if keys:
                source_scores = []
                for key in keys[:50]:  # Limit to 50 entries per source
                    entry = redis_client.hgetall(key)
                    if entry and b'sentiment_score' in entry:
                        try:
                            score = float(entry[b'sentiment_score'])
                            source_scores.append(score)
                        except (ValueError, TypeError):
                            continue
                
                if source_scores:
                    avg_score = np.mean(source_scores)
                    total_weighted_score += avg_score * weight
                    total_weight += weight
                    source_count += 1
        
        if total_weight > 0:
            weighted_score = total_weighted_score / total_weight
            logger.info("Sentiment aggregated", symbol=symbol, score=weighted_score, sources=source_count)
            return weighted_score
        
        return None
        
    except Exception as e:
        logger.error("Failed to aggregate sentiment", error=str(e), symbol=symbol)
        return None

def load_trading_config() -> Dict[str, Any]:
    """Load trading configuration from file"""
    try:
        config_path = "/app/configs/trading_config.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load trading config", error=str(e))
        # Return default configuration
        return {
            "trading": {
                "general": {
                    "max_position_size": 10000,
                    "sentiment_threshold": 0.6
                },
                "sentiment_weights": {
                    "twitter": 0.4,
                    "reddit": 0.3,
                    "news": 0.3
                }
            }
        }

# Trading logic
async def execute_trade(symbol: str, side: str, quantity: int, sentiment_score: Optional[float] = None):
    """Execute a trade via Alpaca API"""
    if not alpaca_api:
        logger.error("Alpaca API not available")
        return None
    
    try:
        # Get current market price
        ticker = yf.Ticker(symbol)
        current_price = ticker.info.get('regularMarketPrice', 0)
        
        if current_price == 0:
            logger.error("Unable to get current price", symbol=symbol)
            return None
        
        # Calculate total amount
        total_amount = quantity * current_price
        
        # Check position limits
        config_data = load_trading_config()
        symbol_config = config_data.get("trading", {}).get("symbols", {}).get(symbol, {})
        max_position_size = symbol_config.get("max_position_size", config.max_position_size)
        
        if total_amount > max_position_size:
            logger.warning("Trade exceeds max position size", 
                         symbol=symbol, amount=total_amount, max_size=max_position_size)
            return None
        
        # Execute trade
        order = alpaca_api.submit_order(
            symbol=symbol,
            qty=quantity,
            side=side.lower(),
            type='market',
            time_in_force='day'
        )
        
        # Wait for order to be filled
        order_status = alpaca_api.get_order(order.id)
        
        # Store trade in database
        await store_trade(symbol, side, quantity, current_price, total_amount, sentiment_score, order.id)
        
        logger.info("Trade executed successfully", 
                   symbol=symbol, side=side, quantity=quantity, order_id=order.id)
        
        return order_status
        
    except Exception as e:
        logger.error("Trade execution failed", error=str(e), symbol=symbol, side=side)
        return None

async def store_trade(symbol: str, side: str, quantity: int, price: float, 
                     total_amount: float, sentiment_score: Optional[float], alpaca_order_id: str):
    """Store trade execution in PostgreSQL"""
    try:
        if postgres_conn:
            with postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trades (symbol, side, quantity, price, total_amount, sentiment_score, alpaca_order_id, status, executed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (symbol, side, quantity, price, total_amount, sentiment_score, alpaca_order_id, 'FILLED', datetime.now()))
                postgres_conn.commit()
                
                logger.info("Trade stored in database", symbol=symbol, order_id=alpaca_order_id)
                
    except Exception as e:
        logger.error("Failed to store trade", error=str(e), symbol=symbol)

# Portfolio management
async def get_portfolio_positions() -> List[PortfolioPosition]:
    """Get current portfolio positions"""
    try:
        if not alpaca_api:
            return []
        
        positions = alpaca_api.list_positions()
        portfolio_positions = []
        
        for position in positions:
            symbol = position.symbol
            quantity = int(position.qty)
            avg_price = float(position.avg_entry_price)
            current_price = float(position.current_price)
            total_value = quantity * current_price
            unrealized_pnl = float(position.unrealized_pl)
            
            portfolio_positions.append(PortfolioPosition(
                symbol=symbol,
                quantity=quantity,
                average_price=avg_price,
                current_price=current_price,
                total_value=total_value,
                unrealized_pnl=unrealized_pnl,
                last_updated=datetime.now()
            ))
        
        return portfolio_positions
        
    except Exception as e:
        logger.error("Failed to get portfolio positions", error=str(e))
        return []

async def update_portfolio_positions():
    """Update portfolio positions in database"""
    try:
        positions = await get_portfolio_positions()
        
        if postgres_conn:
            with postgres_conn.cursor() as cursor:
                for position in positions:
                    cursor.execute("""
                        INSERT INTO portfolio_positions (symbol, quantity, average_price, current_price, total_value, unrealized_pnl, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol) DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            average_price = EXCLUDED.average_price,
                            current_price = EXCLUDED.current_price,
                            total_value = EXCLUDED.total_value,
                            unrealized_pnl = EXCLUDED.unrealized_pnl,
                            last_updated = EXCLUDED.last_updated
                    """, (position.symbol, position.quantity, position.average_price, 
                          position.current_price, position.total_value, position.unrealized_pnl, position.last_updated))
                
                postgres_conn.commit()
                logger.info("Portfolio positions updated", count=len(positions))
                
    except Exception as e:
        logger.error("Failed to update portfolio positions", error=str(e))

# Trading bot logic
async def run_trading_bot():
    """Main trading bot logic"""
    try:
        logger.info("Running trading bot iteration")
        
        # Load configuration
        config_data = load_trading_config()
        symbols = list(config_data.get("trading", {}).get("symbols", {}).keys())
        
        if not symbols:
            logger.warning("No symbols configured for trading")
            return
        
        # Get current portfolio positions
        current_positions = await get_portfolio_positions()
        position_symbols = {pos.symbol for pos in current_positions}
        
        # Analyze sentiment for each symbol
        for symbol in symbols:
            try:
                sentiment_score = await aggregate_sentiment(symbol)
                
                if sentiment_score is None:
                    continue
                
                symbol_config = config_data.get("trading", {}).get("symbols", {}).get(symbol, {})
                sentiment_threshold = symbol_config.get("sentiment_threshold", config.sentiment_threshold)
                
                # Trading logic based on sentiment
                if sentiment_score > sentiment_threshold:
                    # Positive sentiment - consider buying
                    if symbol not in position_symbols:
                        # Calculate position size
                        max_position_size = symbol_config.get("max_position_size", config.max_position_size)
                        current_price = yf.Ticker(symbol).info.get('regularMarketPrice', 0)
                        
                        if current_price > 0:
                            quantity = int(max_position_size / current_price)
                            if quantity > 0:
                                await execute_trade(symbol, "BUY", quantity, sentiment_score)
                                logger.info("Buy signal triggered", symbol=symbol, sentiment=sentiment_score)
                
                elif sentiment_score < -sentiment_threshold:
                    # Negative sentiment - consider selling
                    if symbol in position_symbols:
                        position = next((pos for pos in current_positions if pos.symbol == symbol), None)
                        if position and position.quantity > 0:
                            await execute_trade(symbol, "SELL", position.quantity, sentiment_score)
                            logger.info("Sell signal triggered", symbol=symbol, sentiment=sentiment_score)
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error("Error processing symbol", symbol=symbol, error=str(e))
                continue
        
        # Update portfolio positions
        await update_portfolio_positions()
        
        logger.info("Trading bot iteration completed")
        
    except Exception as e:
        logger.error("Trading bot failed", error=str(e))

# Scheduler setup
def setup_scheduler():
    """Setup scheduled tasks"""
    try:
        # Add trading bot task
        scheduler.add_job(
            run_trading_bot,
            trigger=IntervalTrigger(seconds=config.trade_frequency),
            id='trading_bot',
            name='Trading Bot',
            replace_existing=True
        )
        
        # Add portfolio update task
        scheduler.add_job(
            update_portfolio_positions,
            trigger=IntervalTrigger(seconds=60),  # Update every minute
            id='portfolio_update',
            name='Portfolio Update',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
        
    except Exception as e:
        logger.error("Failed to setup scheduler", error=str(e))

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "redis": redis_client is not None,
            "postgres": postgres_conn is not None,
            "alpaca": alpaca_api is not None,
            "scheduler": scheduler.running
        }
    }

@app.post("/trade")
async def execute_trade_endpoint(request: TradeRequest):
    """Execute a trade manually"""
    try:
        result = await execute_trade(
            request.symbol, 
            request.side, 
            request.quantity, 
            request.sentiment_score
        )
        
        if result:
            return {
                "message": "Trade executed successfully",
                "order_id": result.id,
                "status": result.status,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Trade execution failed")
            
    except Exception as e:
        logger.error("Trade endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio positions"""
    try:
        positions = await get_portfolio_positions()
        return {
            "positions": [pos.dict() for pos in positions],
            "total_positions": len(positions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Portfolio endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sentiment/{symbol}")
async def get_symbol_sentiment(symbol: str):
    """Get aggregated sentiment for a symbol"""
    try:
        sentiment_score = await aggregate_sentiment(symbol)
        
        if sentiment_score is not None:
            return {
                "symbol": symbol,
                "sentiment_score": sentiment_score,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "symbol": symbol,
                "sentiment_score": None,
                "message": "No sentiment data available",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error("Sentiment endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/start")
async def start_trading_bot():
    """Start the trading bot"""
    try:
        if not scheduler.running:
            setup_scheduler()
        
        return {
            "message": "Trading bot started",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to start trading bot", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/stop")
async def stop_trading_bot():
    """Stop the trading bot"""
    try:
        if scheduler.running:
            scheduler.shutdown()
        
        return {
            "message": "Trading bot stopped",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to stop trading bot", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bot/status")
async def get_bot_status():
    """Get trading bot status"""
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ],
        "timestamp": datetime.now().isoformat()
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting trading service")
    init_redis()
    init_postgres()
    init_alpaca()
    setup_scheduler()
    logger.info("Trading service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down trading service")
    if scheduler.running:
        scheduler.shutdown()
    if redis_client:
        redis_client.close()
    if postgres_conn:
        postgres_conn.close()
    logger.info("Trading service shut down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
