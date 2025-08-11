# FBREAPERV1 — Facebook OSINT Dashboard

**Full Python Project (Live Data Only)**

---

## Project Overview

FBREAPERV1 is a sophisticated, modular OSINT platform built entirely in Python for **real-time Facebook data collection, enrichment, storage, and visualization**. Leveraging best-in-class Python frameworks and tools, FBREAPERV1 enables ethical, scalable, and extensible Facebook OSINT — powered exclusively by live data, with no test or mock data.

---

## Architecture Components

| Component                | Tech Stack                 | Port      | Description                                                        |
| ------------------------ | -------------------------- | --------- | ------------------------------------------------------------------ |
| **Frontend UI**          | Streamlit                  | 8501      | Interactive, dynamic dashboard for user commands & live data       |
| **Backend API**          | FastAPI + Uvicorn          | 8000      | REST API for scraper control, data ingestion, and Neo4j querying   |
| **Scraper Microservice** | Playwright + NLP           | 5000      | Live Facebook scraping, real-time text enrichment, Kafka messaging |
| **Graph Database**       | Neo4j (Dockerized)         | 7687      | Storage and relationship analytics of live Facebook data           |
| **Messaging Infra**      | Kafka + Zookeeper (Docker) | 9092/2181 | Reliable async communication between backend and scraper           |
| **Kafka Web UI**         | Kafka UI                   | 8081      | Kafka topics and message monitoring                                |

---

## Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Facebook account for scraping

### Installation

1. **Clone and setup:**
```bash
git clone <repository>
cd fbreaperv1
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start infrastructure services:**
```bash
docker-compose up -d neo4j kafka zookeeper kafka-ui
```

4. **Configure Facebook credentials:**
```bash
cp .env.example .env
# Edit .env with your Facebook credentials
```

5. **Start the services:**
```bash
# Terminal 1: Backend API
python backend/main.py

# Terminal 2: Scraper Microservice  
python scraper/main.py

# Terminal 3: Frontend UI
streamlit run frontend/app.py
```

6. **Access the dashboard:**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000/docs
- Kafka UI: http://localhost:8081
- Neo4j Browser: http://localhost:7474

---

## Functional Overview

### Streamlit Frontend
- Live search interface for keywords, users, groups, and pages
- Real-time scraper status, progress, and error displays
- Dynamic display of Facebook posts, comments, and reactions from live data
- Interactive network graph visualizing social relationships
- Live sentiment, language, and hashtag analytics
- Responsive dark mode UI with auto-refreshing views

### FastAPI Backend
- REST API endpoints to start scraping, submit keyword/user/group searches, and retrieve data
- Retrieves live data directly from the Neo4j graph database
- Consumes enriched data messages from the scraper microservice via Kafka
- Inserts live data into Neo4j and provides network analysis endpoints
- Health check and system metrics endpoints

### Python Scraper Microservice
- Uses Playwright for human-like Facebook browsing with persistent login sessions
- Operates in two modes:
  - Open browser and continuously scroll the live Facebook homepage feed
  - Search specified keywords/users/groups and scrape related posts
- Extracts posts, comments, reactions, timestamps, and metadata dynamically
- Applies a powerful NLP pipeline including:
  - Language detection
  - Sentiment analysis
  - Hashtag extraction
  - Named Entity Recognition (NER)
  - Automatic translation of foreign-language text
- Includes randomized liking of posts where keyword matches are found to simulate human behavior
- Communicates asynchronously with backend via Kafka:
  - Consumes scrape commands
  - Produces enriched data messages

### Neo4j Graph Database
- Stores Facebook entities (posts, users, groups, comments) as graph nodes
- Captures relationships such as authorship, commenting, reacting, and tagging
- Enables fast graph queries for interactive network visualization and analysis

### Kafka Messaging Infrastructure
- Enables decoupled, asynchronous inter-service communication
- Topics:
  - `scraper-control`: Backend commands scraper microservice
  - `fbreaper-topic`: Scraper streams enriched data to backend
- Supports reliable, scalable message processing and delivery

---

## Data Flow Summary

1. User interacts with the **Streamlit frontend** to issue searches or control commands
2. Frontend calls **FastAPI backend** REST APIs
3. Backend produces Kafka messages directing the scraper microservice
4. Scraper performs live Facebook data extraction and enrichment
5. Enriched live data flows back to backend through Kafka
6. Backend ingests and persists data in the **Neo4j** graph database
7. Frontend queries backend and visualizes live data on demand

---

## Security & Performance

- Scraper enforces Facebook's rate limiting and session management policies
- Backend implements CORS, input validation, and detailed logging for API security
- Kafka ensures reliable, scalable messaging between services
- Docker containerization for isolated, portable, and scalable deployments
- Real-time monitoring and comprehensive error handling throughout the system

---

## Key Features

- Live multi-entity Facebook OSINT scraping: users, groups, pages, keywords
- Persistent Playwright browser sessions and human-like dynamic scraping including **random liking of posts where keywords are found** to mimic natural behavior
- Real-time scraper status tracking with detailed error reporting
- Rich NLP-driven text enrichment including **automatic translation**
- Interactive, live-updating social network graph visualizations
- Modular and fully Python microservices architecture for ease of maintenance and extensibility

---

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

## Contributing

This project is for educational and research purposes. Please ensure compliance with Facebook's Terms of Service and applicable laws when using this tool.

## License

MIT License - see LICENSE file for details.