#!/usr/bin/env python3
"""
FBREAPERV1 Scraper Microservice
Playwright-based Facebook scraper with NLP enrichment
"""

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import aiokafka
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger
from dotenv import load_dotenv
import spacy
from textblob import TextBlob
from langdetect import detect, LangDetectException
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk

# Load environment variables
load_dotenv()

# Configuration
FACEBOOK_EMAIL = os.getenv("FACEBOOK_EMAIL")
FACEBOOK_PASSWORD = os.getenv("FACEBOOK_PASSWORD")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_SCRAPER_CONTROL = os.getenv("KAFKA_TOPIC_SCRAPER_CONTROL", "scraper-control")
KAFKA_TOPIC_FBREAPER_DATA = os.getenv("KAFKA_TOPIC_FBREAPER_DATA", "fbreaper-topic")
SCRAPER_DELAY_MIN = int(os.getenv("SCRAPER_DELAY_MIN", "2"))
SCRAPER_DELAY_MAX = int(os.getenv("SCRAPER_DELAY_MAX", "5"))
SCRAPER_SCROLL_COUNT = int(os.getenv("SCRAPER_SCROLL_COUNT", "10"))
SCRAPER_MAX_POSTS_PER_SEARCH = int(os.getenv("SCRAPER_MAX_POSTS_PER_SEARCH", "50"))
SCRAPER_LIKE_PROBABILITY = float(os.getenv("SCRAPER_LIKE_PROBABILITY", "0.3"))

# Global variables
browser: Optional[Browser] = None
page: Optional[Page] = None
kafka_producer: Optional[aiokafka.AIOKafkaProducer] = None
kafka_consumer: Optional[aiokafka.AIOKafkaConsumer] = None
is_running = False
current_task = None

# Initialize NLP models
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found. Installing...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')
    nltk.download('words')

class FacebookScraper:
    """Facebook scraper using Playwright with NLP enrichment"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.is_logged_in = False
        
    async def initialize(self):
        """Initialize browser and page"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # Set to True for production
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            
            self.page = await self.browser.new_page()
            
            # Set user agent
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            raise
    
    async def login(self):
        """Login to Facebook"""
        try:
            if not FACEBOOK_EMAIL or not FACEBOOK_PASSWORD:
                raise ValueError("Facebook credentials not configured")
            
            await self.page.goto("https://www.facebook.com/")
            await self.page.wait_for_load_state("networkidle")
            
            # Fill login form
            await self.page.fill('input[name="email"]', FACEBOOK_EMAIL)
            await self.page.fill('input[name="pass"]', FACEBOOK_PASSWORD)
            
            # Click login button
            await self.page.click('button[name="login"]')
            
            # Wait for login to complete
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful
            if "login" not in self.page.url.lower():
                self.is_logged_in = True
                logger.info("Successfully logged into Facebook")
            else:
                raise Exception("Login failed - check credentials")
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise
    
    async def scrape_feed(self, max_posts: int = 50, enable_likes: bool = True):
        """Scrape posts from Facebook feed"""
        try:
            if not self.is_logged_in:
                await self.login()
            
            await self.page.goto("https://www.facebook.com/")
            await self.page.wait_for_load_state("networkidle")
            
            posts_scraped = 0
            scroll_count = 0
            
            while posts_scraped < max_posts and scroll_count < SCRAPER_SCROLL_COUNT:
                # Find post containers
                post_elements = await self.page.query_selector_all('[data-testid="post_message"]')
                
                for post_element in post_elements:
                    if posts_scraped >= max_posts:
                        break
                    
                    try:
                        post_data = await self.extract_post_data(post_element)
                        if post_data:
                            # Enrich with NLP
                            enriched_data = await self.enrich_post_data(post_data)
                            
                            # Randomly like posts if enabled
                            if enable_likes and random.random() < SCRAPER_LIKE_PROBABILITY:
                                await self.like_post(post_element)
                            
                            # Send to Kafka
                            await self.send_to_kafka(enriched_data)
                            
                            posts_scraped += 1
                            logger.info(f"Scraped post {posts_scraped}/{max_posts}")
                            
                            # Random delay
                            await asyncio.sleep(random.uniform(SCRAPER_DELAY_MIN, SCRAPER_DELAY_MAX))
                    
                    except Exception as e:
                        logger.error(f"Error processing post: {e}")
                        continue
                
                # Scroll down
                await self.page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
                scroll_count += 1
            
            logger.info(f"Feed scraping completed. Scraped {posts_scraped} posts")
            
        except Exception as e:
            logger.error(f"Error scraping feed: {e}")
            raise
    
    async def scrape_search(self, search_type: str, query: str, max_posts: int = 50, enable_likes: bool = True):
        """Scrape posts based on search query"""
        try:
            if not self.is_logged_in:
                await self.login()
            
            # Construct search URL based on type
            if search_type == "keyword":
                search_url = f"https://www.facebook.com/search/posts/?q={query}"
            elif search_type == "user":
                search_url = f"https://www.facebook.com/search/people/?q={query}"
            elif search_type == "group":
                search_url = f"https://www.facebook.com/search/groups/?q={query}"
            elif search_type == "page":
                search_url = f"https://www.facebook.com/search/pages/?q={query}"
            else:
                raise ValueError(f"Unsupported search type: {search_type}")
            
            await self.page.goto(search_url)
            await self.page.wait_for_load_state("networkidle")
            
            posts_scraped = 0
            scroll_count = 0
            
            while posts_scraped < max_posts and scroll_count < SCRAPER_SCROLL_COUNT:
                # Find post containers in search results
                post_elements = await self.page.query_selector_all('[data-testid="post_message"]')
                
                for post_element in post_elements:
                    if posts_scraped >= max_posts:
                        break
                    
                    try:
                        post_data = await self.extract_post_data(post_element)
                        if post_data:
                            # Enrich with NLP
                            enriched_data = await self.enrich_post_data(post_data)
                            
                            # Randomly like posts if enabled
                            if enable_likes and random.random() < SCRAPER_LIKE_PROBABILITY:
                                await self.like_post(post_element)
                            
                            # Send to Kafka
                            await self.send_to_kafka(enriched_data)
                            
                            posts_scraped += 1
                            logger.info(f"Scraped search post {posts_scraped}/{max_posts}")
                            
                            # Random delay
                            await asyncio.sleep(random.uniform(SCRAPER_DELAY_MIN, SCRAPER_DELAY_MAX))
                    
                    except Exception as e:
                        logger.error(f"Error processing search post: {e}")
                        continue
                
                # Scroll down
                await self.page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
                scroll_count += 1
            
            logger.info(f"Search scraping completed. Scraped {posts_scraped} posts for '{query}'")
            
        except Exception as e:
            logger.error(f"Error scraping search: {e}")
            raise
    
    async def extract_post_data(self, post_element) -> Optional[Dict]:
        """Extract data from a post element"""
        try:
            # Extract post content
            content_element = await post_element.query_selector('[data-testid="post_message"]')
            content = await content_element.inner_text() if content_element else ""
            
            if not content.strip():
                return None
            
            # Extract author
            author_element = await post_element.query_selector('a[role="link"]')
            author = await author_element.inner_text() if author_element else "Unknown"
            
            # Extract timestamp
            timestamp_element = await post_element.query_selector('a[role="link"] time')
            timestamp = await timestamp_element.get_attribute("datetime") if timestamp_element else datetime.now().isoformat()
            
            # Extract engagement metrics (approximate)
            likes_element = await post_element.query_selector('[data-testid="UFI2ReactionsCount/root"]')
            likes_text = await likes_element.inner_text() if likes_element else "0"
            likes = self.parse_engagement_count(likes_text)
            
            comments_element = await post_element.query_selector('[data-testid="UFI2CommentsCount/root"]')
            comments_text = await comments_element.inner_text() if comments_element else "0"
            comments = self.parse_engagement_count(comments_text)
            
            shares_element = await post_element.query_selector('[data-testid="UFI2SharesCount/root"]')
            shares_text = await shares_element.inner_text() if shares_element else "0"
            shares = self.parse_engagement_count(shares_text)
            
            # Generate post ID
            post_id = f"post_{int(time.time())}_{random.randint(1000, 9999)}"
            
            return {
                "post_id": post_id,
                "content": content,
                "author": author,
                "timestamp": timestamp,
                "likes": likes,
                "comments": comments,
                "shares": shares
            }
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None
    
    def parse_engagement_count(self, text: str) -> int:
        """Parse engagement count from text"""
        try:
            # Remove non-numeric characters except K, M, B
            text = text.strip().lower()
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            elif 'b' in text:
                return int(float(text.replace('b', '')) * 1000000000)
            else:
                return int(re.sub(r'[^\d]', '', text) or 0)
        except:
            return 0
    
    async def enrich_post_data(self, post_data: Dict) -> Dict:
        """Enrich post data with NLP analysis"""
        try:
            content = post_data["content"]
            
            # Language detection
            try:
                language = detect(content)
            except LangDetectException:
                language = "unknown"
            
            # Sentiment analysis
            blob = TextBlob(content)
            sentiment = blob.sentiment.polarity
            
            # Hashtag extraction
            hashtags = re.findall(r'#\w+', content)
            
            # Named Entity Recognition
            doc = nlp(content)
            entities = [ent.text for ent in doc.ents]
            
            # Add enriched data
            post_data.update({
                "sentiment": sentiment,
                "language": language,
                "hashtags": hashtags,
                "entities": entities,
                "enriched_at": datetime.now().isoformat()
            })
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error enriching post data: {e}")
            return post_data
    
    async def like_post(self, post_element):
        """Like a post (simulate human behavior)"""
        try:
            like_button = await post_element.query_selector('[data-testid="UFI2ReactionsCount/root"]')
            if like_button:
                await like_button.click()
                await asyncio.sleep(random.uniform(0.5, 1.5))
                logger.debug("Liked a post")
        except Exception as e:
            logger.debug(f"Error liking post: {e}")
    
    async def send_to_kafka(self, data: Dict):
        """Send enriched data to Kafka"""
        try:
            if kafka_producer:
                await kafka_producer.send_and_wait(KAFKA_TOPIC_FBREAPER_DATA, data)
                logger.debug(f"Sent data to Kafka: {data['post_id']}")
        except Exception as e:
            logger.error(f"Error sending to Kafka: {e}")
    
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()

# Kafka functions
async def get_kafka_producer():
    """Get Kafka producer"""
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await kafka_producer.start()
    return kafka_producer

async def start_kafka_consumer():
    """Start Kafka consumer for control messages"""
    global kafka_consumer
    if kafka_consumer is None:
        kafka_consumer = aiokafka.AIOKafkaConsumer(
            KAFKA_TOPIC_SCRAPER_CONTROL,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id="scraper-consumer"
        )
        await kafka_consumer.start()
        asyncio.create_task(consume_control_messages())

async def consume_control_messages():
    """Consume control messages from Kafka"""
    global is_running, current_task
    
    try:
        async for message in kafka_consumer:
            command = message.value
            
            if command["command"] == "start_scraping":
                is_running = True
                current_task = command.get("task_id")
                
                scraper = FacebookScraper()
                await scraper.initialize()
                
                try:
                    if command["search_type"] == "feed":
                        await scraper.scrape_feed(
                            max_posts=command.get("max_posts", 50),
                            enable_likes=command.get("enable_likes", True)
                        )
                    else:
                        await scraper.scrape_search(
                            search_type=command["search_type"],
                            query=command["query"],
                            max_posts=command.get("max_posts", 50),
                            enable_likes=command.get("enable_likes", True)
                        )
                finally:
                    await scraper.close()
                    is_running = False
                    current_task = None
            
            elif command["command"] == "stop_scraping":
                is_running = False
                current_task = None
                logger.info("Received stop command")
                
    except Exception as e:
        logger.error(f"Error consuming control messages: {e}")

async def main():
    """Main function"""
    try:
        # Configure logging
        logger.add("logs/scraper.log", rotation="1 day", retention="7 days")
        
        # Initialize Kafka
        await get_kafka_producer()
        await start_kafka_consumer()
        
        logger.info("Scraper microservice started successfully")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down scraper microservice")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Cleanup
        if kafka_producer:
            await kafka_producer.stop()
        if kafka_consumer:
            await kafka_consumer.stop()

if __name__ == "__main__":
    asyncio.run(main())