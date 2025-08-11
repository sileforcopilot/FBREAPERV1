#!/usr/bin/env python3
"""
FBREAPERV1 Backend API
FastAPI backend for Facebook OSINT dashboard
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger
import aiokafka
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="FBREAPERV1 Backend API",
    description="Backend API for Facebook OSINT Dashboard",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "fbreaper123")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_SCRAPER_CONTROL = os.getenv("KAFKA_TOPIC_SCRAPER_CONTROL", "scraper-control")
KAFKA_TOPIC_FBREAPER_DATA = os.getenv("KAFKA_TOPIC_FBREAPER_DATA", "fbreaper-topic")

# Global variables
neo4j_driver = None
kafka_producer = None
kafka_consumer = None
scraper_status = {
    "is_running": False,
    "current_task": None,
    "last_activity": None,
    "errors": []
}

# Pydantic models
class ScrapeRequest(BaseModel):
    search_type: str = Field(..., description="Type of search: 'keyword', 'user', 'group', 'page', 'feed'")
    query: str = Field(..., description="Search query or target")
    max_posts: int = Field(default=50, description="Maximum number of posts to scrape")
    enable_likes: bool = Field(default=True, description="Enable random liking of posts")

class ScrapeResponse(BaseModel):
    task_id: str
    status: str
    message: str

class PostData(BaseModel):
    post_id: str
    content: str
    author: str
    timestamp: str
    likes: int
    comments: int
    shares: int
    sentiment: Optional[float] = None
    language: Optional[str] = None
    hashtags: List[str] = []
    entities: List[str] = []

class NetworkNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any]

class NetworkEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]

class NetworkGraph(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]

# Database connection
def get_neo4j_driver():
    global neo4j_driver
    if neo4j_driver is None:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return neo4j_driver

# Kafka producer
async def get_kafka_producer():
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await kafka_producer.start()
    return kafka_producer

# Kafka consumer for enriched data
async def start_kafka_consumer():
    import aiokafka
    from aiokafka.errors import KafkaConnectionError
    global kafka_consumer
    max_retries = 5
    for attempt in range(max_retries):
        try:
            if kafka_consumer is None:
                kafka_consumer = aiokafka.AIOKafkaConsumer(
                    KAFKA_TOPIC_FBREAPER_DATA,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    group_id="backend-consumer"
                )
                await kafka_consumer.start()
                asyncio.create_task(consume_enriched_data())
            print("✅ Kafka consumer started successfully.")
            return
        except KafkaConnectionError as e:
            print(f"⚠️ Kafka connection failed (attempt {attempt+1}/{max_retries}): {e}")
            await asyncio.sleep(5)
    raise RuntimeError("❌ Could not connect to Kafka after retries")

async def consume_enriched_data():
    """Consume enriched data from Kafka and store in Neo4j"""
    try:
        async for message in kafka_consumer:
            data = message.value
            await store_enriched_data(data)
    except Exception as e:
        logger.error(f"Error consuming Kafka messages: {e}")

async def store_enriched_data(data: Dict):
    """Store enriched Facebook data in Neo4j"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            # Create post node
            post_query = """
            MERGE (p:Post {post_id: $post_id})
            SET p.content = $content,
                p.timestamp = $timestamp,
                p.likes = $likes,
                p.comments = $comments,
                p.shares = $shares,
                p.sentiment = $sentiment,
                p.language = $language,
                p.hashtags = $hashtags,
                p.entities = $entities,
                p.created_at = datetime()
            """
            
            session.run(post_query, **data)
            
            # Create user node and relationship
            user_query = """
            MERGE (u:User {username: $author})
            MERGE (u)-[:POSTED]->(p:Post {post_id: $post_id})
            """
            
            session.run(user_query, author=data['author'], post_id=data['post_id'])
            
            # Create hashtag relationships
            for hashtag in data.get('hashtags', []):
                hashtag_query = """
                MERGE (h:Hashtag {name: $hashtag})
                MERGE (p:Post {post_id: $post_id})-[:CONTAINS]->(h)
                """
                session.run(hashtag_query, hashtag=hashtag, post_id=data['post_id'])
            
            logger.info(f"Stored enriched data for post {data['post_id']}")
            
    except Exception as e:
        logger.error(f"Error storing enriched data: {e}")

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await start_kafka_consumer()
    logger.info("Backend API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections on shutdown"""
    global neo4j_driver, kafka_producer, kafka_consumer
    
    if neo4j_driver:
        neo4j_driver.close()
    
    if kafka_producer:
        await kafka_producer.stop()
    
    if kafka_consumer:
        await kafka_consumer.stop()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "FBREAPERV1 Backend API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            session.run("RETURN 1")
        
        return {
            "status": "healthy",
            "neo4j": "connected",
            "kafka": "connected" if kafka_producer else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/api/scrape", response_model=ScrapeResponse)
async def start_scraping(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start Facebook scraping task"""
    try:
        producer = await get_kafka_producer()
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Update scraper status
        scraper_status["is_running"] = True
        scraper_status["current_task"] = task_id
        scraper_status["last_activity"] = datetime.now().isoformat()
        
        # Send scrape command to Kafka
        command = {
            "task_id": task_id,
            "command": "start_scraping",
            "search_type": request.search_type,
            "query": request.query,
            "max_posts": request.max_posts,
            "enable_likes": request.enable_likes,
            "timestamp": datetime.now().isoformat()
        }
        
        await producer.send_and_wait(KAFKA_TOPIC_SCRAPER_CONTROL, command)
        
        logger.info(f"Started scraping task {task_id} for {request.search_type}: {request.query}")
        
        return ScrapeResponse(
            task_id=task_id,
            status="started",
            message=f"Scraping task started for {request.search_type}: {request.query}"
        )
        
    except Exception as e:
        logger.error(f"Error starting scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scrape/stop")
async def stop_scraping():
    """Stop current scraping task"""
    try:
        producer = await get_kafka_producer()
        
        command = {
            "command": "stop_scraping",
            "timestamp": datetime.now().isoformat()
        }
        
        await producer.send_and_wait(KAFKA_TOPIC_SCRAPER_CONTROL, command)
        
        scraper_status["is_running"] = False
        scraper_status["current_task"] = None
        
        logger.info("Stopped scraping task")
        
        return {"status": "stopped", "message": "Scraping task stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scraper/status")
async def get_scraper_status():
    """Get current scraper status"""
    return scraper_status

@app.get("/api/posts", response_model=List[PostData])
async def get_posts(limit: int = 50, offset: int = 0):
    """Get scraped posts from Neo4j"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            query = """
            MATCH (p:Post)
            OPTIONAL MATCH (u:User)-[:POSTED]->(p)
            RETURN p, u.username as author
            ORDER BY p.created_at DESC
            SKIP $offset LIMIT $limit
            """
            
            result = session.run(query, limit=limit, offset=offset)
            
            posts = []
            for record in result:
                post_data = record["p"]
                posts.append(PostData(
                    post_id=post_data["post_id"],
                    content=post_data["content"],
                    author=record["author"] or "Unknown",
                    timestamp=post_data["timestamp"],
                    likes=post_data.get("likes", 0),
                    comments=post_data.get("comments", 0),
                    shares=post_data.get("shares", 0),
                    sentiment=post_data.get("sentiment"),
                    language=post_data.get("language"),
                    hashtags=post_data.get("hashtags", []),
                    entities=post_data.get("entities", [])
                ))
            
            return posts
            
    except Exception as e:
        logger.error(f"Error retrieving posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/network", response_model=NetworkGraph)
async def get_network_graph(limit: int = 100):
    """Get social network graph data"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            # Get nodes
            nodes_query = """
            MATCH (n)
            WHERE n:User OR n:Post OR n:Hashtag
            RETURN n, labels(n)[0] as type
            LIMIT $limit
            """
            
            nodes_result = session.run(nodes_query, limit=limit)
            
            nodes = []
            for record in nodes_result:
                node_data = record["n"]
                node_type = record["type"]
                
                if node_type == "User":
                    label = node_data.get("username", "Unknown User")
                elif node_type == "Post":
                    label = node_data.get("content", "")[:50] + "..."
                else:
                    label = node_data.get("name", "Unknown")
                
                nodes.append(NetworkNode(
                    id=str(node_data.identity),
                    label=label,
                    type=node_type,
                    properties=dict(node_data)
                ))
            
            # Get edges
            edges_query = """
            MATCH (a)-[r]->(b)
            WHERE a:User OR a:Post OR a:Hashtag
            AND b:User OR b:Post OR b:Hashtag
            RETURN a, b, type(r) as relationship_type, r
            LIMIT $limit
            """
            
            edges_result = session.run(edges_query, limit=limit)
            
            edges = []
            for record in edges_result:
                edges.append(NetworkEdge(
                    source=str(record["a"].identity),
                    target=str(record["b"].identity),
                    type=record["relationship_type"],
                    properties=dict(record["r"])
                ))
            
            return NetworkGraph(nodes=nodes, edges=edges)
            
    except Exception as e:
        logger.error(f"Error retrieving network graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/sentiment")
async def get_sentiment_analytics():
    """Get sentiment analysis statistics"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            query = """
            MATCH (p:Post)
            WHERE p.sentiment IS NOT NULL
            RETURN 
                avg(p.sentiment) as avg_sentiment,
                min(p.sentiment) as min_sentiment,
                max(p.sentiment) as max_sentiment,
                count(p) as total_posts
            """
            
            result = session.run(query)
            record = result.single()
            
            return {
                "average_sentiment": record["avg_sentiment"],
                "min_sentiment": record["min_sentiment"],
                "max_sentiment": record["max_sentiment"],
                "total_posts": record["total_posts"]
            }
            
    except Exception as e:
        logger.error(f"Error retrieving sentiment analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/languages")
async def get_language_analytics():
    """Get language distribution statistics"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            query = """
            MATCH (p:Post)
            WHERE p.language IS NOT NULL
            RETURN p.language, count(p) as count
            ORDER BY count DESC
            """
            
            result = session.run(query)
            
            languages = []
            for record in result:
                languages.append({
                    "language": record["p.language"],
                    "count": record["count"]
                })
            
            return {"languages": languages}
            
    except Exception as e:
        logger.error(f"Error retrieving language analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/hashtags")
async def get_hashtag_analytics():
    """Get top hashtags statistics"""
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            query = """
            MATCH (h:Hashtag)<-[:CONTAINS]-(p:Post)
            RETURN h.name as hashtag, count(p) as count
            ORDER BY count DESC
            LIMIT 20
            """
            
            result = session.run(query)
            
            hashtags = []
            for record in result:
                hashtags.append({
                    "hashtag": record["hashtag"],
                    "count": record["count"]
                })
            
            return {"hashtags": hashtags}
            
    except Exception as e:
        logger.error(f"Error retrieving hashtag analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Configure logging
    logger.add("logs/backend.log", rotation="1 day", retention="7 days")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )