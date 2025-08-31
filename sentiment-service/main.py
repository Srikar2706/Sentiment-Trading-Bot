import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import tweepy
import praw
from newsapi import NewsApiClient
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import structlog

# logging setup - keeping it simple for now
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# fastapi app
app = FastAPI(
    title="Sentiment Analysis Service",
    description="FinBERT sentiment analysis",
    version="1.0.0"
)

# Configuration
class Config:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.postgres_url = os.getenv("POSTGRES_URL", "postgresql://localhost:5432/sentiment_trading")
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "sentiment_trading_bot/1.0")
        self.news_api_key = os.getenv("NEWS_API_KEY")

config = Config()

# Initialize connections
redis_client = None
postgres_conn = None

# finbert stuff
tokenizer = None
model = None

# models
class SentimentRequest(BaseModel):
    text: str
    symbol: Optional[str] = None
    source: Optional[str] = None

class SentimentResponse(BaseModel):
    text: str
    sentiment_score: float
    confidence_score: float
    symbol: Optional[str] = None
    source: Optional[str] = None
    timestamp: datetime

class DataIngestionRequest(BaseModel):
    symbols: List[str]
    hours_back: int = 24  # TODO: make this configurable

# db connections
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

def init_finbert():
    global tokenizer, model
    try:
        # finbert for sentiment
        model_name = "ProsusAI/finbert"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        logger.info("finbert loaded")
    except Exception as e:
        logger.error(f"finbert failed: {e}")
        # try fallback model
        try:
            model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            logger.info("fallback model loaded")
        except Exception as e2:
            logger.error(f"fallback failed too: {e2}")

def init_twitter():
    if all([config.twitter_api_key, config.twitter_api_secret, 
            config.twitter_access_token, config.twitter_access_token_secret]):
        try:
            auth = tweepy.OAuthHandler(config.twitter_api_key, config.twitter_api_secret)
            auth.set_access_token(config.twitter_access_token, config.twitter_access_token_secret)
            api = tweepy.API(auth, wait_on_rate_limit=True)
            return api
        except Exception as e:
            logger.error("Failed to initialize Twitter API", error=str(e))
    return None

def init_reddit():
    if all([config.reddit_client_id, config.reddit_client_secret]):
        try:
            reddit = praw.Reddit(
                client_id=config.reddit_client_id,
                client_secret=config.reddit_client_secret,
                user_agent=config.reddit_user_agent
            )
            return reddit
        except Exception as e:
            logger.error("Failed to initialize Reddit API", error=str(e))
    return None

def init_news():
    if config.news_api_key:
        try:
            news_api = NewsApiClient(api_key=config.news_api_key)
            return news_api
        except Exception as e:
            logger.error("Failed to initialize News API", error=str(e))
    return None

# Sentiment analysis
def analyze_sentiment(text: str) -> tuple[float, float]:
    """Analyze sentiment using FinBERT or fallback model"""
    if tokenizer is None or model is None:
        raise HTTPException(status_code=500, detail="Sentiment model not available")
    
    try:
        # Tokenize and predict
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
        
        # Get sentiment score and confidence
        if model.config.num_labels == 3:  # FinBERT: negative, neutral, positive
            # Convert to -1 to 1 scale
            sentiment_score = (probabilities[0][2] - probabilities[0][0]).item()
            confidence_score = torch.max(probabilities).item()
        else:  # Fallback model
            sentiment_score = (probabilities[0][2] - probabilities[0][0]).item()
            confidence_score = torch.max(probabilities).item()
        
        return sentiment_score, confidence_score
    
    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e), text=text[:100])
        raise HTTPException(status_code=500, detail="Sentiment analysis failed")

# Data ingestion functions
async def ingest_twitter_data(symbols: List[str], hours_back: int = 24):
    """Ingest Twitter data for given symbols"""
    twitter_api = init_twitter()
    if not twitter_api:
        logger.warning("Twitter API not available")
        return
    
    try:
        for symbol in symbols:
            # Search for tweets containing the symbol
            query = f"${symbol} OR #{symbol} OR {symbol}"
            tweets = twitter_api.search_tweets(q=query, lang="en", count=100, tweet_mode="extended")
            
            for tweet in tweets:
                text = tweet.full_text
                sentiment_score, confidence_score = analyze_sentiment(text)
                
                # Store in Redis and PostgreSQL
                await store_sentiment_data(symbol, text, sentiment_score, confidence_score, "twitter", {
                    "tweet_id": tweet.id,
                    "user": tweet.user.screen_name,
                    "followers_count": tweet.user.followers_count,
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count
                })
                
            await asyncio.sleep(1)  # Rate limiting
            
    except Exception as e:
        logger.error("Twitter data ingestion failed", error=str(e))

async def ingest_reddit_data(symbols: List[str], hours_back: int = 24):
    """Ingest Reddit data for given symbols"""
    reddit_api = init_reddit()
    if not reddit_api:
        logger.warning("Reddit API not available")
        return
    
    try:
        subreddits = ["investing", "stocks", "wallstreetbets", "StockMarket"]
        
        for subreddit_name in subreddits:
            subreddit = reddit_api.subreddit(subreddit_name)
            
            for symbol in symbols:
                # Search for posts containing the symbol
                search_query = f"title:{symbol} OR selftext:{symbol}"
                posts = subreddit.search(search_query, sort="hot", limit=50)
                
                for post in posts:
                    text = f"{post.title} {post.selftext}"
                    if len(text.strip()) > 10:  # Only analyze posts with content
                        sentiment_score, confidence_score = analyze_sentiment(text)
                        
                        await store_sentiment_data(symbol, text, sentiment_score, confidence_score, "reddit", {
                            "post_id": post.id,
                            "subreddit": subreddit_name,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "author": str(post.author)
                        })
                
                await asyncio.sleep(1)  # Rate limiting
                
    except Exception as e:
        logger.error("Reddit data ingestion failed", error=str(e))

async def ingest_news_data(symbols: List[str], hours_back: int = 24):
    """Ingest news data for given symbols"""
    news_api = init_news()
    if not news_api:
        logger.warning("News API not available")
        return
    
    try:
        for symbol in symbols:
            # Search for news articles
            articles = news_api.get_everything(
                q=symbol,
                language='en',
                sort_by='relevancy',
                from_param=(datetime.now() - timedelta(hours=hours_back)).isoformat(),
                page_size=50
            )
            
            for article in articles['articles']:
                text = f"{article['title']} {article['description']}"
                if len(text.strip()) > 10:
                    sentiment_score, confidence_score = analyze_sentiment(text)
                    
                    await store_sentiment_data(symbol, text, sentiment_score, confidence_score, "news", {
                        "article_url": article['url'],
                        "source": article['source']['name'],
                        "published_at": article['publishedAt'],
                        "author": article['author']
                    })
            
            await asyncio.sleep(1)  # Rate limiting
            
    except Exception as e:
        logger.error("News data ingestion failed", error=str(e))

async def store_sentiment_data(symbol: str, content: str, sentiment_score: float, 
                             confidence_score: float, source: str, metadata: Dict[str, Any]):
    """Store sentiment data in Redis and PostgreSQL"""
    try:
        # Store in Redis for quick access
        if redis_client:
            redis_key = f"sentiment:{symbol}:{source}:{datetime.now().isoformat()}"
            redis_data = {
                "symbol": symbol,
                "content": content[:500],  # Truncate for Redis
                "sentiment_score": sentiment_score,
                "confidence_score": confidence_score,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "metadata": json.dumps(metadata)
            }
            redis_client.hmset(redis_key, redis_data)
            redis_client.expire(redis_key, 86400)  # Expire in 24 hours
        
        # Store in PostgreSQL for persistence
        if postgres_conn:
            with postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sentiment_data (symbol, source, content, sentiment_score, confidence_score, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (symbol, source, content, sentiment_score, confidence_score, json.dumps(metadata)))
                postgres_conn.commit()
        
        logger.info("Sentiment data stored", symbol=symbol, source=source, score=sentiment_score)
        
    except Exception as e:
        logger.error("Failed to store sentiment data", error=str(e), symbol=symbol, source=source)

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
            "finbert": tokenizer is not None and model is not None
        }
    }

@app.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment_endpoint(request: SentimentRequest):
    """Analyze sentiment of given text"""
    try:
        sentiment_score, confidence_score = analyze_sentiment(request.text)
        
        response = SentimentResponse(
            text=request.text,
            sentiment_score=sentiment_score,
            confidence_score=confidence_score,
            symbol=request.symbol,
            source=request.source,
            timestamp=datetime.now()
        )
        
        # Store if symbol is provided
        if request.symbol and request.source:
            await store_sentiment_data(
                request.symbol, 
                request.text, 
                sentiment_score, 
                confidence_score, 
                request.source, 
                {}
            )
        
        return response
        
    except Exception as e:
        logger.error("Sentiment analysis endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_data(request: DataIngestionRequest, background_tasks: BackgroundTasks):
    """Ingest data from multiple sources for given symbols"""
    try:
        # Add background tasks for data ingestion
        background_tasks.add_task(ingest_twitter_data, request.symbols, request.hours_back)
        background_tasks.add_task(ingest_reddit_data, request.symbols, request.hours_back)
        background_tasks.add_task(ingest_news_data, request.symbols, request.hours_back)
        
        return {
            "message": "Data ingestion started",
            "symbols": request.symbols,
            "sources": ["twitter", "reddit", "news"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Data ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sentiment/{symbol}")
async def get_symbol_sentiment(symbol: str, source: Optional[str] = None):
    """Get sentiment data for a specific symbol"""
    try:
        if redis_client:
            # Get from Redis cache
            pattern = f"sentiment:{symbol}:*"
            if source:
                pattern = f"sentiment:{symbol}:{source}:*"
            
            keys = redis_client.keys(pattern)
            if keys:
                data = []
                for key in keys[:100]:  # Limit to 100 entries
                    entry = redis_client.hgetall(key)
                    if entry:
                        data.append(entry)
                
                return {
                    "symbol": symbol,
                    "source": source,
                    "data": data,
                    "count": len(data)
                }
        
        # Fallback to PostgreSQL
        if postgres_conn:
            with postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT * FROM sentiment_data 
                    WHERE symbol = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 100
                """
                params = [symbol]
                
                if source:
                    query = query.replace("WHERE symbol = %s", "WHERE symbol = %s AND source = %s")
                    params.append(source)
                
                cursor.execute(query, params)
                data = cursor.fetchall()
                
                return {
                    "symbol": symbol,
                    "source": source,
                    "data": [dict(row) for row in data],
                    "count": len(data)
                }
        
        return {"symbol": symbol, "data": [], "count": 0}
        
    except Exception as e:
        logger.error("Failed to get symbol sentiment", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail=str(e))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting sentiment analysis service")
    init_redis()
    init_postgres()
    init_finbert()
    logger.info("Sentiment analysis service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down sentiment analysis service")
    if redis_client:
        redis_client.close()
    if postgres_conn:
        postgres_conn.close()
    logger.info("Sentiment analysis service shut down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
