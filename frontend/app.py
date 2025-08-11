#!/usr/bin/env python3
"""
FBREAPERV1 Frontend Dashboard
Streamlit-based UI for Facebook OSINT dashboard
"""

import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import networkx as nx
from streamlit_agraph import agraph, Node, Edge, Config
import asyncio
from typing import Dict, List, Optional, Any

# Page configuration
st.set_page_config(
    page_title="FBREAPERV1 - Facebook OSINT Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stApp {
        background-color: #0e1117;
    }
    .stButton > button {
        background-color: #1f2937;
        color: #f9fafb;
        border: 1px solid #374151;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #374151;
        border-color: #6b7280;
    }
    .stSelectbox > div > div > select {
        background-color: #1f2937;
        color: #f9fafb;
        border: 1px solid #374151;
    }
    .stTextInput > div > div > input {
        background-color: #1f2937;
        color: #f9fafb;
        border: 1px solid #374151;
    }
    .stNumberInput > div > div > input {
        background-color: #1f2937;
        color: #f9fafb;
        border: 1px solid #374151;
    }
    .stCheckbox > div > div > label {
        color: #f9fafb;
    }
    .metric-container {
        background-color: #1f2937;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #374151;
        margin: 0.5rem 0;
    }
    .status-running {
        color: #10b981;
        font-weight: bold;
    }
    .status-stopped {
        color: #ef4444;
        font-weight: bold;
    }
    .status-idle {
        color: #f59e0b;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
BACKEND_URL = "http://localhost:8000"
REFRESH_INTERVAL = 5  # seconds

class FBREAPERFrontend:
    """Frontend application for FBREAPERV1"""
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.session = requests.Session()
    
    def check_backend_health(self) -> bool:
        """Check if backend is healthy"""
        try:
            response = self.session.get(f"{self.backend_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_scraper_status(self) -> Dict:
        """Get current scraper status"""
        try:
            response = self.session.get(f"{self.backend_url}/api/scraper/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {"is_running": False, "current_task": None, "last_activity": None, "errors": []}
        except:
            return {"is_running": False, "current_task": None, "last_activity": None, "errors": []}
    
    def start_scraping(self, search_type: str, query: str, max_posts: int, enable_likes: bool) -> Dict:
        """Start scraping task"""
        try:
            payload = {
                "search_type": search_type,
                "query": query,
                "max_posts": max_posts,
                "enable_likes": enable_likes
            }
            response = self.session.post(f"{self.backend_url}/api/scrape", json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to start scraping: {response.text}"}
        except Exception as e:
            return {"error": f"Error starting scraping: {str(e)}"}
    
    def stop_scraping(self) -> Dict:
        """Stop current scraping task"""
        try:
            response = self.session.post(f"{self.backend_url}/api/scrape/stop", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to stop scraping: {response.text}"}
        except Exception as e:
            return {"error": f"Error stopping scraping: {str(e)}"}
    
    def get_posts(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get scraped posts"""
        try:
            response = self.session.get(f"{self.backend_url}/api/posts?limit={limit}&offset={offset}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    def get_network_graph(self, limit: int = 100) -> Dict:
        """Get network graph data"""
        try:
            response = self.session.get(f"{self.backend_url}/api/network?limit={limit}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"nodes": [], "edges": []}
        except:
            return {"nodes": [], "edges": []}
    
    def get_sentiment_analytics(self) -> Dict:
        """Get sentiment analytics"""
        try:
            response = self.session.get(f"{self.backend_url}/api/analytics/sentiment", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}
    
    def get_language_analytics(self) -> Dict:
        """Get language analytics"""
        try:
            response = self.session.get(f"{self.backend_url}/api/analytics/languages", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"languages": []}
        except:
            return {"languages": []}
    
    def get_hashtag_analytics(self) -> Dict:
        """Get hashtag analytics"""
        try:
            response = self.session.get(f"{self.backend_url}/api/analytics/hashtags", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"hashtags": []}
        except:
            return {"hashtags": []}

def main():
    """Main application"""
    st.title("🔍 FBREAPERV1 - Facebook OSINT Dashboard")
    st.markdown("---")
    
    # Initialize frontend
    frontend = FBREAPERFrontend()
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        # Backend status
        backend_healthy = frontend.check_backend_health()
        if backend_healthy:
            st.success("✅ Backend Connected")
        else:
            st.error("❌ Backend Disconnected")
            st.stop()
        
        st.markdown("---")
        
        # Scraper controls
        st.subheader("🚀 Scraper Controls")
        
        search_type = st.selectbox(
            "Search Type",
            ["feed", "keyword", "user", "group", "page"],
            help="Select the type of content to scrape"
        )
        
        if search_type == "feed":
            query = "Facebook Feed"
            query_disabled = True
        else:
            query = st.text_input("Search Query", placeholder="Enter search term...")
            query_disabled = False
        
        max_posts = st.number_input("Max Posts", min_value=1, max_value=200, value=50)
        enable_likes = st.checkbox("Enable Random Likes", value=True, help="Simulate human behavior by randomly liking posts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Start Scraping", disabled=query_disabled and not query):
                if query or search_type == "feed":
                    result = frontend.start_scraping(search_type, query, max_posts, enable_likes)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(f"Started scraping: {result['message']}")
        
        with col2:
            if st.button("⏹️ Stop Scraping"):
                result = frontend.stop_scraping()
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("Scraping stopped")
        
        st.markdown("---")
        
        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
        if auto_refresh:
            st.info(f"Auto-refreshing every {REFRESH_INTERVAL} seconds")
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📝 Posts", "🕸️ Network", "📈 Analytics"])
    
    with tab1:
        st.header("📊 Live Dashboard")
        
        # Scraper status
        scraper_status = frontend.get_scraper_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if scraper_status["is_running"]:
                st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                st.markdown('<p class="status-running">🟢 Scraper Running</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                st.markdown('<p class="status-stopped">🔴 Scraper Stopped</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Current Task", scraper_status.get("current_task", "None"))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            last_activity = scraper_status.get("last_activity", "Never")
            if last_activity != "Never":
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).strftime('%H:%M:%S')
            st.metric("Last Activity", last_activity)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Recent posts preview
        st.subheader("📝 Recent Posts")
        posts = frontend.get_posts(limit=10)
        
        if posts:
            for post in posts:
                with st.expander(f"📄 {post['author']} - {post['timestamp'][:19]}"):
                    st.write(f"**Content:** {post['content']}")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Likes", post['likes'])
                    with col2:
                        st.metric("Comments", post['comments'])
                    with col3:
                        st.metric("Shares", post['shares'])
                    with col4:
                        if post.get('sentiment') is not None:
                            sentiment_color = "🟢" if post['sentiment'] > 0 else "🔴" if post['sentiment'] < 0 else "🟡"
                            st.metric("Sentiment", f"{sentiment_color} {post['sentiment']:.2f}")
                        else:
                            st.metric("Sentiment", "N/A")
                    
                    if post.get('hashtags'):
                        st.write(f"**Hashtags:** {', '.join(post['hashtags'])}")
                    if post.get('entities'):
                        st.write(f"**Entities:** {', '.join(post['entities'])}")
        else:
            st.info("No posts found. Start scraping to see data.")
    
    with tab2:
        st.header("📝 All Posts")
        
        # Posts table
        posts = frontend.get_posts(limit=100)
        
        if posts:
            # Convert to DataFrame
            df = pd.DataFrame(posts)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp', ascending=False)
            
            # Display table
            st.dataframe(
                df[['author', 'content', 'timestamp', 'likes', 'comments', 'shares', 'sentiment', 'language']],
                use_container_width=True
            )
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"fbreaper_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No posts found. Start scraping to see data.")
    
    with tab3:
        st.header("🕸️ Social Network Graph")
        
        # Network graph
        network_data = frontend.get_network_graph(limit=50)
        
        if network_data["nodes"]:
            # Create nodes for agraph
            nodes = []
            for node in network_data["nodes"]:
                color = "#1f77b4" if node["type"] == "User" else "#ff7f0e" if node["type"] == "Post" else "#2ca02c"
                nodes.append(
                    Node(
                        id=node["id"],
                        label=node["label"][:20] + "..." if len(node["label"]) > 20 else node["label"],
                        size=20,
                        color=color
                    )
                )
            
            # Create edges for agraph
            edges = []
            for edge in network_data["edges"]:
                edges.append(
                    Edge(
                        source=edge["source"],
                        target=edge["target"],
                        label=edge["type"]
                    )
                )
            
            # Graph configuration
            config = Config(
                height=600,
                width=800,
                directed=True,
                physics=True,
                hierarchical=False
            )
            
            # Display graph
            agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.info("No network data found. Start scraping to see relationships.")
    
    with tab4:
        st.header("📈 Analytics Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sentiment analytics
            st.subheader("😊 Sentiment Analysis")
            sentiment_data = frontend.get_sentiment_analytics()
            
            if sentiment_data:
                st.metric("Average Sentiment", f"{sentiment_data.get('average_sentiment', 0):.3f}")
                st.metric("Total Posts", sentiment_data.get('total_posts', 0))
                
                # Sentiment distribution chart
                posts = frontend.get_posts(limit=1000)
                if posts:
                    df = pd.DataFrame(posts)
                    df = df[df['sentiment'].notna()]
                    
                    if not df.empty:
                        fig = px.histogram(
                            df, 
                            x='sentiment', 
                            nbins=20,
                            title="Sentiment Distribution",
                            color_discrete_sequence=['#1f77b4']
                        )
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#f9fafb')
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sentiment data available.")
        
        with col2:
            # Language analytics
            st.subheader("🌍 Language Distribution")
            language_data = frontend.get_language_analytics()
            
            if language_data.get("languages"):
                df_lang = pd.DataFrame(language_data["languages"])
                fig = px.pie(
                    df_lang, 
                    values='count', 
                    names='language',
                    title="Posts by Language"
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f9fafb')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No language data available.")
        
        # Hashtag analytics
        st.subheader("🏷️ Top Hashtags")
        hashtag_data = frontend.get_hashtag_analytics()
        
        if hashtag_data.get("hashtags"):
            df_hashtags = pd.DataFrame(hashtag_data["hashtags"])
            fig = px.bar(
                df_hashtags.head(15), 
                x='hashtag', 
                y='count',
                title="Top 15 Hashtags",
                color_discrete_sequence=['#ff7f0e']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f9fafb'),
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hashtag data available.")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.experimental_rerun()

if __name__ == "__main__":
    main()