import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any, Optional

# Page configuration
st.set_page_config(
    page_title="Sentiment Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# config stuff
class Config:
    def __init__(self):
        self.redis_url = st.secrets.get("REDIS_URL", "redis://localhost:6379")
        self.postgres_url = st.secrets.get("POSTGRES_URL", "postgresql://localhost:5432/sentiment_trading")
        self.sentiment_service_url = st.secrets.get("SENTIMENT_SERVICE_URL", "http://sentiment-service:8001")
        self.trading_service_url = st.secrets.get("TRADING_SERVICE_URL", "http://trading-service:8002")

config = Config()

# Initialize connections
@st.cache_resource
def init_redis():
    try:
        redis_client = redis.from_url(config.redis_url)
        redis_client.ping()
        return redis_client
    except Exception as e:
        st.error(f"redis failed: {e}")
        return None

@st.cache_resource
def init_postgres():
    try:
        conn = psycopg2.connect(config.postgres_url)
        return conn
    except Exception as e:
        st.error(f"postgres failed: {e}")
        return None

# Data fetching functions
def fetch_sentiment_data(symbol: str, source: Optional[str] = None) -> pd.DataFrame:
    """Fetch sentiment data from Redis or PostgreSQL"""
    try:
        # Try Redis first
        redis_client = init_redis()
        if redis_client:
            pattern = f"sentiment:{symbol}:*"
            if source:
                pattern = f"sentiment:{symbol}:{source}:*"
            
            keys = redis_client.keys(pattern)
            if keys:
                data = []
                for key in keys[:100]:  # Limit to 100 entries
                    entry = redis_client.hgetall(key)
                    if entry:
                        # Convert bytes to strings
                        entry_dict = {}
                        for k, v in entry.items():
                            if isinstance(k, bytes):
                                k = k.decode('utf-8')
                            if isinstance(v, bytes):
                                v = v.decode('utf-8')
                            entry_dict[k] = v
                        
                        # Parse metadata
                        if 'metadata' in entry_dict:
                            try:
                                entry_dict['metadata'] = json.loads(entry_dict['metadata'])
                            except:
                                entry_dict['metadata'] = {}
                        
                        data.append(entry_dict)
                
                if data:
                    df = pd.DataFrame(data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df['sentiment_score'] = pd.to_numeric(df['sentiment_score'], errors='coerce')
                    df['confidence_score'] = pd.to_numeric(df['confidence_score'], errors='coerce')
                    return df
        
        # Fallback to PostgreSQL
        conn = init_postgres()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
                
                if data:
                    df = pd.DataFrame([dict(row) for row in data])
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching sentiment data: {e}")
        return pd.DataFrame()

def fetch_portfolio_data() -> pd.DataFrame:
    """Fetch portfolio positions from trading service or database"""
    try:
        # Try trading service first
        response = requests.get(f"{config.trading_service_url}/portfolio", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'positions' in data:
                df = pd.DataFrame(data['positions'])
                df['last_updated'] = pd.to_datetime(df['last_updated'])
                return df
        
        # Fallback to database
        conn = init_postgres()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM portfolio_positions ORDER BY last_updated DESC")
                data = cursor.fetchall()
                
                if data:
                    df = pd.DataFrame([dict(row) for row in data])
                    df['last_updated'] = pd.to_datetime(df['last_updated'])
                    return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching portfolio data: {e}")
        return pd.DataFrame()

def fetch_trade_history(limit: int = 100) -> pd.DataFrame:
    """Fetch trade history from database"""
    try:
        conn = init_postgres()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM trades 
                    ORDER BY executed_at DESC 
                    LIMIT %s
                """, (limit,))
                data = cursor.fetchall()
                
                if data:
                    df = pd.DataFrame([dict(row) for row in data])
                    df['executed_at'] = pd.to_datetime(df['executed_at'])
                    df['created_at'] = pd.to_datetime(df['created_at'])
                    return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching trade history: {e}")
        return pd.DataFrame()

def fetch_aggregated_sentiment() -> pd.DataFrame:
    """Fetch aggregated sentiment data"""
    try:
        conn = init_postgres()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM sentiment_overview 
                    ORDER BY avg_sentiment DESC
                """)
                data = cursor.fetchall()
                
                if data:
                    df = pd.DataFrame([dict(row) for row in data])
                    df['last_update'] = pd.to_datetime(df['last_update'])
                    return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching aggregated sentiment: {e}")
        return pd.DataFrame()

# Visualization functions
def create_sentiment_timeline(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create sentiment timeline chart"""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Group by source and plot
    for source in df['source'].unique():
        source_df = df[df['source'] == source]
        fig.add_trace(go.Scatter(
            x=source_df['timestamp'],
            y=source_df['sentiment_score'],
            mode='lines+markers',
            name=f"{source.title()}",
            line=dict(width=2),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title=f"Sentiment Timeline for {symbol}",
        xaxis_title="Time",
        yaxis_title="Sentiment Score",
        hovermode='x unified',
        height=400
    )
    
    return fig

def create_sentiment_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create sentiment heatmap by source and time"""
    if df.empty:
        return go.Figure()
    
    # Resample data to hourly intervals
    df_resampled = df.set_index('timestamp').resample('H').mean().reset_index()
    
    # Pivot data for heatmap
    pivot_df = df_resampled.pivot_table(
        values='sentiment_score',
        index=df_resampled['timestamp'].dt.hour,
        columns='source',
        aggfunc='mean'
    ).fillna(0)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='RdYlGn',
        zmid=0
    ))
    
    fig.update_layout(
        title="Sentiment Heatmap by Hour and Source",
        xaxis_title="Data Source",
        yaxis_title="Hour of Day",
        height=400
    )
    
    return fig

def create_portfolio_chart(df: pd.DataFrame) -> go.Figure:
    """Create portfolio positions chart"""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure(data=[
        go.Bar(
            x=df['symbol'],
            y=df['total_value'],
            text=df['total_value'].round(2),
            textposition='auto',
            name='Position Value'
        )
    ])
    
    fig.update_layout(
        title="Portfolio Positions",
        xaxis_title="Symbol",
        yaxis_title="Position Value ($)",
        height=400
    )
    
    return fig

def create_pnl_chart(df: pd.DataFrame) -> go.Figure:
    """Create P&L chart"""
    if df.empty:
        return go.Figure()
    
    colors = ['green' if x >= 0 else 'red' for x in df['unrealized_pnl']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=df['symbol'],
            y=df['unrealized_pnl'],
            text=df['unrealized_pnl'].round(2),
            textposition='auto',
            marker_color=colors,
            name='Unrealized P&L'
        )
    ])
    
    fig.update_layout(
        title="Unrealized P&L by Position",
        xaxis_title="Symbol",
        yaxis_title="P&L ($)",
        height=400
    )
    
    return fig

# Main dashboard
def main():
    st.title("📈 Sentiment Trading Dashboard")
    st.markdown("Real-time monitoring of sentiment analysis and trading performance")
    
    # Sidebar
    st.sidebar.header("Dashboard Controls")
    
    # Symbol selection
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX']
    selected_symbol = st.sidebar.selectbox("Select Symbol", symbols)
    
    # Data source selection
    sources = ['All', 'twitter', 'reddit', 'news']
    selected_source = st.sidebar.selectbox("Select Data Source", sources)
    
    # Time range selection
    time_ranges = ['1 Hour', '6 Hours', '24 Hours', '7 Days']
    selected_time = st.sidebar.selectbox("Select Time Range", time_ranges)
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    # Auto-refresh
    if st.sidebar.checkbox("Auto-refresh (30s)"):
        time.sleep(30)
        st.rerun()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Sentiment Analysis")
        
        # Fetch sentiment data
        source_filter = None if selected_source == 'All' else selected_source
        sentiment_df = fetch_sentiment_data(selected_symbol, source_filter)
        
        if not sentiment_df.empty:
            # Sentiment timeline
            st.plotly_chart(create_sentiment_timeline(sentiment_df, selected_symbol), use_container_width=True)
            
            # Sentiment statistics
            col1_1, col1_2, col1_3 = st.columns(3)
            
            with col1_1:
                avg_sentiment = sentiment_df['sentiment_score'].mean()
                st.metric("Average Sentiment", f"{avg_sentiment:.3f}")
            
            with col1_2:
                sentiment_std = sentiment_df['sentiment_score'].std()
                st.metric("Sentiment Volatility", f"{sentiment_std:.3f}")
            
            with col1_3:
                data_points = len(sentiment_df)
                st.metric("Data Points", data_points)
            
            # Sentiment heatmap
            st.plotly_chart(create_sentiment_heatmap(sentiment_df), use_container_width=True)
            
        else:
            st.warning(f"No sentiment data available for {selected_symbol}")
    
    with col2:
        st.header("📈 Quick Stats")
        
        # Portfolio summary
        portfolio_df = fetch_portfolio_data()
        if not portfolio_df.empty:
            total_value = portfolio_df['total_value'].sum()
            total_pnl = portfolio_df['unrealized_pnl'].sum()
            
            st.metric("Total Portfolio Value", f"${total_value:,.2f}")
            st.metric("Total Unrealized P&L", f"${total_pnl:,.2f}", 
                     delta=f"{'📈' if total_pnl >= 0 else '📉'}")
            
            # Top performers
            if len(portfolio_df) > 0:
                top_performer = portfolio_df.loc[portfolio_df['unrealized_pnl'].idxmax()]
                st.metric("Top Performer", top_performer['symbol'], 
                         delta=f"${top_performer['unrealized_pnl']:.2f}")
        else:
            st.info("No portfolio data available")
    
    # Portfolio section
    st.header("💼 Portfolio Overview")
    
    if not portfolio_df.empty:
        col2_1, col2_2 = st.columns(2)
        
        with col2_1:
            st.plotly_chart(create_portfolio_chart(portfolio_df), use_container_width=True)
        
        with col2_2:
            st.plotly_chart(create_pnl_chart(portfolio_df), use_container_width=True)
        
        # Portfolio table
        st.subheader("Position Details")
        st.dataframe(
            portfolio_df[['symbol', 'quantity', 'average_price', 'current_price', 'total_value', 'unrealized_pnl']]
            .round(2),
            use_container_width=True
        )
    else:
        st.info("No portfolio positions found")
    
    # Trading History
    st.header("📋 Trading History")
    
    trade_df = fetch_trade_history(50)
    if not trade_df.empty:
        # Trade summary
        col3_1, col3_2, col3_3, col3_4 = st.columns(4)
        
        with col3_1:
            total_trades = len(trade_df)
            st.metric("Total Trades", total_trades)
        
        with col3_2:
            buy_trades = len(trade_df[trade_df['side'] == 'BUY'])
            st.metric("Buy Trades", buy_trades)
        
        with col3_3:
            sell_trades = len(trade_df[trade_df['side'] == 'SELL'])
            st.metric("Sell Trades", sell_trades)
        
        with col3_4:
            total_volume = trade_df['total_amount'].sum()
            st.metric("Total Volume", f"${total_volume:,.2f}")
        
        # Recent trades table
        st.subheader("Recent Trades")
        st.dataframe(
            trade_df[['symbol', 'side', 'quantity', 'price', 'total_amount', 'sentiment_score', 'executed_at']]
            .head(20)
            .round(2),
            use_container_width=True
        )
        
        # Trade timeline
        fig = go.Figure()
        
        for side in ['BUY', 'SELL']:
            side_df = trade_df[trade_df['side'] == side]
            if not side_df.empty:
                fig.add_trace(go.Scatter(
                    x=side_df['executed_at'],
                    y=side_df['total_amount'],
                    mode='markers',
                    name=side,
                    marker=dict(
                        size=8,
                        color='green' if side == 'BUY' else 'red'
                    )
                ))
        
        fig.update_layout(
            title="Trade Timeline",
            xaxis_title="Time",
            yaxis_title="Trade Amount ($)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("No trading history available")
    
    # Market Sentiment Overview
    st.header("🌍 Market Sentiment Overview")
    
    agg_sentiment_df = fetch_aggregated_sentiment()
    if not agg_sentiment_df.empty:
        # Sentiment overview table
        st.dataframe(
            agg_sentiment_df[['symbol', 'avg_sentiment', 'data_points', 'last_update', 'is_active']]
            .round(3),
            use_container_width=True
        )
        
        # Sentiment comparison chart
        fig = go.Figure(data=[
            go.Bar(
                x=agg_sentiment_df['symbol'],
                y=agg_sentiment_df['avg_sentiment'],
                text=agg_sentiment_df['avg_sentiment'].round(3),
                textposition='auto',
                marker_color='lightblue'
            )
        ])
        
        fig.update_layout(
            title="Average Sentiment by Symbol",
            xaxis_title="Symbol",
            yaxis_title="Average Sentiment Score",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("No aggregated sentiment data available")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>Sentiment Trading Dashboard | Built with Streamlit</p>
            <p>Last updated: {}</p>
        </div>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
