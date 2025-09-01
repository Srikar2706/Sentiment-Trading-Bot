import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Sentiment Trading Dashboard - Demo",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Demo data generation
def generate_demo_data():
    """Generate demo data for the dashboard"""
    # Generate time series data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    dates = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Sentiment data
    sentiment_data = []
    symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
    
    for symbol in symbols:
        for date in dates:
            # Generate realistic sentiment scores
            base_sentiment = np.random.normal(0.1, 0.3)  # Slightly positive bias
            sentiment_score = np.clip(base_sentiment + np.random.normal(0, 0.1), -1, 1)
            confidence = np.random.uniform(0.6, 0.95)
            
            sentiment_data.append({
                'timestamp': date,
                'symbol': symbol,
                'sentiment_score': sentiment_score,
                'confidence_score': confidence,
                'source': np.random.choice(['twitter', 'reddit', 'news']),
                'text': f"Sample {symbol} sentiment data"
            })
    
    return pd.DataFrame(sentiment_data)

def generate_portfolio_data():
    """Generate demo portfolio data"""
    symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
    portfolio_data = []
    
    for symbol in symbols:
        quantity = np.random.randint(10, 100)
        avg_price = np.random.uniform(100, 500)
        current_price = avg_price * np.random.uniform(0.8, 1.3)
        total_value = quantity * current_price
        unrealized_pnl = (current_price - avg_price) * quantity
        
        portfolio_data.append({
            'symbol': symbol,
            'quantity': quantity,
            'average_price': round(avg_price, 2),
            'current_price': round(current_price, 2),
            'total_value': round(total_value, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'last_updated': datetime.now()
        })
    
    return pd.DataFrame(portfolio_data)

def generate_trade_history():
    """Generate demo trade history"""
    symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
    trades = []
    
    for i in range(20):
        symbol = np.random.choice(symbols)
        side = np.random.choice(['BUY', 'SELL'])
        quantity = np.random.randint(5, 50)
        price = np.random.uniform(100, 500)
        sentiment_score = np.random.uniform(-1, 1)
        
        trades.append({
            'timestamp': datetime.now() - timedelta(hours=i*2),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': round(price, 2),
            'sentiment_score': round(sentiment_score, 3),
            'status': 'FILLED'
        })
    
    return pd.DataFrame(trades)

# Main dashboard
st.title("📈 Sentiment Trading Dashboard")
st.markdown("**Demo Mode** - Showing mock data for demonstration purposes")

# Sidebar
st.sidebar.header("Dashboard Controls")
selected_symbol = st.sidebar.selectbox(
    "Select Symbol",
    ['ALL', 'AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
)

time_range = st.sidebar.selectbox(
    "Time Range",
    ['1 Hour', '6 Hours', '24 Hours', '7 Days']
)

# Generate demo data
sentiment_df = generate_demo_data()
portfolio_df = generate_portfolio_data()
trades_df = generate_trade_history()

# Filter data based on selection
if selected_symbol != 'ALL':
    sentiment_df = sentiment_df[sentiment_df['symbol'] == selected_symbol]

# Main dashboard layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Sentiment Analysis")
    
    # Sentiment over time
    fig_sentiment = px.line(
        sentiment_df, 
        x='timestamp', 
        y='sentiment_score',
        color='symbol',
        title='Sentiment Score Over Time'
    )
    fig_sentiment.update_layout(height=400)
    st.plotly_chart(fig_sentiment, use_container_width=True)
    
    # Sentiment by source
    col1a, col1b = st.columns(2)
    
    with col1a:
        source_sentiment = sentiment_df.groupby('source')['sentiment_score'].mean().reset_index()
        fig_source = px.bar(
            source_sentiment,
            x='source',
            y='sentiment_score',
            title='Average Sentiment by Source'
        )
        st.plotly_chart(fig_source, use_container_width=True)
    
    with col1b:
        symbol_sentiment = sentiment_df.groupby('symbol')['sentiment_score'].mean().reset_index()
        fig_symbol = px.bar(
            symbol_sentiment,
            x='symbol',
            y='sentiment_score',
            title='Average Sentiment by Symbol'
        )
        st.plotly_chart(fig_symbol, use_container_width=True)

with col2:
    st.subheader("💰 Portfolio Overview")
    
    # Portfolio summary
    total_value = portfolio_df['total_value'].sum()
    total_pnl = portfolio_df['unrealized_pnl'].sum()
    
    st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    st.metric("Unrealized P&L", f"${total_pnl:,.2f}", 
              delta=f"{'📈' if total_pnl > 0 else '📉'}")
    
    # Portfolio table
    st.dataframe(
        portfolio_df[['symbol', 'quantity', 'current_price', 'total_value', 'unrealized_pnl']],
        use_container_width=True
    )

# Recent trades
st.subheader("🔄 Recent Trades")
st.dataframe(
    trades_df[['timestamp', 'symbol', 'side', 'quantity', 'price', 'sentiment_score']],
    use_container_width=True
)

# Performance metrics
st.subheader("📈 Performance Metrics")

col3, col4, col5, col6 = st.columns(4)

with col3:
    st.metric("Win Rate", "65%", "📈")
with col4:
    st.metric("Total Trades", "20", "📊")
with col5:
    st.metric("Avg Sentiment", "0.12", "😊")
with col6:
    st.metric("Active Positions", "5", "💼")

# System status
st.subheader("🔧 System Status")
col7, col8, col9 = st.columns(3)

with col7:
    st.success("✅ Sentiment Service: Online")
with col8:
    st.success("✅ Trading Service: Online")
with col9:
    st.success("✅ Database: Connected")

# Footer
st.markdown("---")
st.markdown("*This is a demo dashboard showing mock data. In production, this would display real-time sentiment analysis and trading data.*")

# Auto-refresh
if st.button("🔄 Refresh Data"):
    st.rerun()

# Auto-refresh every 30 seconds
time.sleep(30)
st.rerun()
