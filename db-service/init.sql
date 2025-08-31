-- Initialize sentiment trading database
CREATE DATABASE IF NOT EXISTS sentiment_trading;

-- Connect to the database
\c sentiment_trading;

-- Create tables for sentiment data
CREATE TABLE IF NOT EXISTS sentiment_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'twitter', 'reddit', 'news'
    content TEXT NOT NULL,
    sentiment_score DECIMAL(3,2) NOT NULL, -- -1.0 to 1.0
    confidence_score DECIMAL(3,2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create table for aggregated sentiment
CREATE TABLE IF NOT EXISTS aggregated_sentiment (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    weighted_score DECIMAL(3,2) NOT NULL,
    source_count INTEGER NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create table for trades
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(4) NOT NULL, -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    sentiment_score DECIMAL(3,2),
    alpaca_order_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'FILLED', 'CANCELLED'
    executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create table for portfolio positions
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    average_price DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    total_value DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create table for trading configuration
CREATE TABLE IF NOT EXISTS trading_config (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    weight_twitter DECIMAL(3,2) DEFAULT 0.4,
    weight_reddit DECIMAL(3,2) DEFAULT 0.3,
    weight_news DECIMAL(3,2) DEFAULT 0.3,
    sentiment_threshold DECIMAL(3,2) DEFAULT 0.6,
    max_position_size DECIMAL(12,2) DEFAULT 10000.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sentiment_data_symbol ON sentiment_data(symbol);
CREATE INDEX IF NOT EXISTS idx_sentiment_data_timestamp ON sentiment_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_sentiment_data_source ON sentiment_data(source);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at);
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_symbol ON portfolio_positions(symbol);

-- Insert default trading configuration for some popular stocks
INSERT INTO trading_config (symbol, weight_twitter, weight_reddit, weight_news, sentiment_threshold, max_position_size) VALUES
('AAPL', 0.4, 0.3, 0.3, 0.6, 10000.00),
('GOOGL', 0.4, 0.3, 0.3, 0.6, 10000.00),
('MSFT', 0.4, 0.3, 0.3, 0.6, 10000.00),
('TSLA', 0.5, 0.3, 0.2, 0.7, 15000.00),
('NVDA', 0.4, 0.3, 0.3, 0.6, 12000.00),
('AMZN', 0.4, 0.3, 0.3, 0.6, 10000.00),
('META', 0.4, 0.3, 0.3, 0.6, 10000.00),
('NFLX', 0.4, 0.3, 0.3, 0.6, 8000.00)
ON CONFLICT (symbol) DO NOTHING;

-- Create a view for current sentiment overview
CREATE OR REPLACE VIEW sentiment_overview AS
SELECT 
    s.symbol,
    AVG(s.sentiment_score) as avg_sentiment,
    COUNT(*) as data_points,
    MAX(s.timestamp) as last_update,
    tc.sentiment_threshold,
    tc.is_active
FROM sentiment_data s
JOIN trading_config tc ON s.symbol = tc.symbol
WHERE s.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY s.symbol, tc.sentiment_threshold, tc.is_active;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user;
