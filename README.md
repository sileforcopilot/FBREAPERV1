# FBREAPERV1 — Facebook OSINT Dashboard (Comprehensive Guide)

FBREAPERV1 is a modular Python platform for real‑time Facebook OSINT: scraping, enrichment, storage, and visualization. This README explains the full architecture, how to set up and run each component (without Docker or shell scripts), how data flows through the system, and operational best practices.

---

## 1) What This Project Does
- Collects live Facebook content based on user input (keywords, users, groups, pages, feed)
- Enriches text with NLP (language detection, sentiment, hashtags, NER, optional translation)
- Streams enriched data through Kafka
- Persists social entities and relationships in Neo4j
- Exposes a REST API via FastAPI
- Visualizes live data and network graphs via Streamlit

Intended for research and educational purposes. Ensure you comply with Facebook’s Terms of Service and applicable laws.

---

## 2) Architecture Overview

### Components
- Frontend UI: Streamlit (port 8501)
- Backend API: FastAPI + Uvicorn (port 8000)
- Scraper Service: Playwright + NLP (Kafka producer/consumer)
- Data Store: Neo4j (Bolt port 7687; Browser 7474)
- Messaging: Kafka (Broker port 9092; requires Zookeeper)

### High-Level Diagram (ASCII)
```
+----------------------+         +------------------+         +---------------------+
|   Streamlit UI       | <-----> |   FastAPI API    | <-----> |     Neo4j Graph     |
| (frontend/app.py)    |  REST   | (backend/main.py)|  Bolt   |  Database           |
+----------------------+         +------------------+         +---------------------+
            |                                 ^                         ^
            v                                 |                         |
    User commands                             |                         |
            |                                 |                         |
            v                                 |                         |
+----------------------+       Kafka topics    |                         |
|    Kafka Broker      | <---------------------+-------------------------+
| (localhost:9092)     |   - scraper-control (backend -> scraper)
|                      |   - fbreaper-topic  (scraper -> backend)
+----------------------+
            ^
            |
            v
+----------------------+
|  Scraper Service     |
| (scraper/main.py)    |
| Playwright + NLP     |
+----------------------+
```

### Runtime Flow Summary
1. User interacts with Streamlit UI.
2. UI calls FastAPI endpoints.
3. Backend publishes control messages to Kafka (`scraper-control`).
4. Scraper consumes control messages, drives Playwright to collect posts, applies NLP.
5. Scraper publishes enriched data to Kafka (`fbreaper-topic`).
6. Backend consumes enriched data and writes nodes/edges to Neo4j.
7. UI queries backend to display analytics and network graphs.

---

## 3) Repository Structure
```
/ (project root)
├─ backend/
│  └─ main.py            FastAPI app, Kafka producer/consumer, Neo4j integration
├─ frontend/
│  └─ app.py             Streamlit UI
├─ scraper/
│  └─ main.py            Playwright scraper, NLP enrichment, Kafka producer/consumer
├─ requirements.txt      Python dependencies
├─ .env.example          Example environment configuration
├─ LICENSE               MIT License
└─ README.md             This document
```

---

## 4) Prerequisites (No Docker)
- Python 3.9+
- Kafka and Zookeeper running locally
  - Broker default: localhost:9092
  - Ensure topics can be auto-created or create topics manually
- Neo4j running locally
  - Bolt: bolt://localhost:7687
  - Browser: http://localhost:7474
- Facebook account for scraping (credentials in `.env`)

Note: You may target remote Kafka/Neo4j hosts by setting environment variables.

---

## 5) Installation and Setup

### 5.1 Install Python dependencies and runtime assets
```bash
pip install -r requirements.txt

# Playwright browser (Chromium) for the scraper
playwright install chromium

# spaCy English model
python -m spacy download en_core_web_sm

# Optional (usually auto-downloaded on first run if missing): NLTK data
python - << 'PY'
import nltk
for pkg in ['punkt','stopwords','averaged_perceptron_tagger','maxent_ne_chunker','words']:
    nltk.download(pkg)
print('Downloaded NLTK data')
PY
```

### 5.2 Configure environment variables
```bash
cp .env.example .env
# Edit .env and set:
# - FACEBOOK_EMAIL / FACEBOOK_PASSWORD
# - Kafka and Neo4j endpoints if different from localhost defaults
# - Optional tuning flags (see below)
```

Key environment variables (defaults shown):
- NEO4J_URI=bolt://localhost:7687
- NEO4J_USER=neo4j
- NEO4J_PASSWORD=fbreaper123
- KAFKA_BOOTSTRAP_SERVERS=localhost:9092
- KAFKA_TOPIC_SCRAPER_CONTROL=scraper-control
- KAFKA_TOPIC_FBREAPER_DATA=fbreaper-topic
- FACEBOOK_EMAIL, FACEBOOK_PASSWORD
- SCRAPER_DELAY_MIN=2, SCRAPER_DELAY_MAX=5, SCRAPER_SCROLL_COUNT=10, SCRAPER_MAX_POSTS_PER_SEARCH=50, SCRAPER_LIKE_PROBABILITY=0.3

Security note: Keep your `.env` private. Do not commit credentials.

---

## 6) Running the System (No Shell Scripts)
Open three terminals:

Terminal 1 — Backend API
```bash
python backend/main.py
# API docs at http://localhost:8000/docs
```

Terminal 2 — Scraper Service
```bash
python scraper/main.py
```

Terminal 3 — Frontend UI
```bash
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
# UI at http://localhost:8501
```

Before starting, ensure Kafka and Neo4j are reachable. On Linux/macOS:
```bash
# Kafka
nc -z localhost 9092 && echo "Kafka is reachable" || echo "Kafka not reachable"
# Neo4j
nc -z localhost 7687 && echo "Neo4j is reachable" || echo "Neo4j not reachable"
```

---

## 7) Backend API Details
- Framework: FastAPI + Uvicorn
- Port: 8000
- Cross-Origin: CORS open to all by default (configure for production)
- Kafka: Produces control messages, consumes enriched data
- Neo4j: Writes/reads social graph

Common endpoints (see http://localhost:8000/docs):
- GET /health: Basic health check
- GET /api/scraper/status: Current scraper status
- POST /api/scraper/start: Start a scraping task
  - Body: { "search_type": "keyword|user|group|page|feed", "query": "...", "max_posts": 50, "enable_likes": true }
- Additional endpoints to query data and graphs from Neo4j are exposed by the backend for the UI.

Kafka topics:
- scraper-control: backend -> scraper (control tasks)
- fbreaper-topic: scraper -> backend (enriched data)

---

## 8) Scraper Service Details
- Playwright (Chromium) drives Facebook browsing
- Requires valid Facebook credentials (from `.env`)
- Two primary modes:
  - Feed mode: continuous scrolling
  - Targeted search: keyword/user/group/page
- NLP pipeline:
  - Language detection
  - Sentiment analysis
  - Hashtag extraction
  - Named Entity Recognition (NER)
  - Optional translation (configure in `.env`)
- Kafka producer: publishes enriched data to `fbreaper-topic`
- Kafka consumer: receives commands from `scraper-control`

Tuning parameters (env):
- SCRAPER_DELAY_MIN / SCRAPER_DELAY_MAX: human-like delays
- SCRAPER_SCROLL_COUNT: pagination depth
- SCRAPER_MAX_POSTS_PER_SEARCH: cap per task
- SCRAPER_LIKE_PROBABILITY: randomized likes when matches are found

---

## 9) Neo4j Data Model (Illustrative)

Nodes (labels):
- Post(id, content, timestamp, likes, comments, shares, sentiment, language, hashtags)
- User(id, name)
- Group(id, name)
- Page(id, name)
- Hashtag(tag)
- Entity(name, type)

Relationships (examples):
- (User)-[:AUTHORED]->(Post)
- (User)-[:COMMENTED]->(Post)
- (User)-[:REACTED {type}]->(Post)
- (Post)-[:MENTIONS]->(Entity)
- (Post)-[:TAGGED_WITH]->(Hashtag)
- (User)-[:MEMBER_OF]->(Group)
- (User)-[:FOLLOWS]->(Page)

Note: The exact model is created by backend queries when inserting data from Kafka. Use the Neo4j Browser to inspect (`MATCH (n) RETURN n LIMIT 50`).

---

## 10) Frontend (Streamlit) Features
- Live search controls: keywords, users, groups, pages, feed mode
- Scraper status and errors
- Live posts view and summaries
- Network graph visualization (via streamlit-agraph)
- Analytics panels (sentiment, languages, hashtags)

Configuration:
- The frontend targets the backend at http://localhost:8000 (fixed in code). If you need a different backend URL, change `BACKEND_URL` in `frontend/app.py`.

---

## 11) End-to-End Flow (ASCII)
```
 [User]
   |
   v
 Streamlit UI (frontend/app.py)
   |  REST: /api/scraper/start, /api/scraper/status, data queries
   v
 FastAPI Backend (backend/main.py)
   |  Produce control
   v
 Kafka (scraper-control)
   |  Consume control
   v
 Scraper (scraper/main.py)
   |  Scrape + NLP
   |  Produce enriched
   v
 Kafka (fbreaper-topic)
   |  Consume enriched
   v
 FastAPI Backend (Neo4j writes)
   |
   v
 Neo4j Graph DB  <-----  Streamlit UI fetches from Backend and renders
```

---

## 12) Operations & Observability
- Health checks:
  - Backend: GET http://localhost:8000/health
  - Kafka: Check broker with CLI or `nc -z localhost 9092`
  - Neo4j: Visit http://localhost:7474 and test Bolt connectivity
- Logs:
  - Services print logs to stdout; redirect to files as needed (e.g., `python backend/main.py > backend.log 2>&1`)
- Scaling:
  - Kafka enables horizontal scaling of consumers; use unique consumer groups if adding more processors

---

## 13) Security Considerations
- Protect `.env` with credentials; never commit real secrets
- Consider enabling stricter CORS and auth on the backend for production
- Rate limiting, retry backoff, and robust error handling are advisable for heavy scraping
- Respect legal and platform policies

---

## 14) Troubleshooting
- Backend cannot connect to Kafka:
  - Verify `KAFKA_BOOTSTRAP_SERVERS` is correct and reachable
  - Ensure broker allows auto topic creation or create topics manually
- Backend cannot connect to Neo4j:
  - Verify `NEO4J_URI`/credentials and Bolt port 7687
  - Check Neo4j logs and authentication status
- Scraper login issues:
  - Double-check `FACEBOOK_EMAIL`/`FACEBOOK_PASSWORD`
  - Review 2FA and session requirements
- Playwright errors:
  - Ensure `playwright install chromium` completed successfully
  - Some Linux envs need additional system libs for headless Chromium
- Frontend cannot reach backend:
  - Confirm backend is at http://localhost:8000 and reachable
  - Adjust `BACKEND_URL` in `frontend/app.py` if using a remote backend

---

## 15) Development Guide
- Code style: Black/Flake8 (optional), type hints encouraged
- Tests: pytest/pytest-asyncio (you can add tests under `tests/`)
- Suggested commands:
```bash
# Formatting & linting (optional if installed)
black .
flake8 .

# Run unit tests (if tests are added)
pytest -q
```

---

## 16) Roadmap Ideas (Optional)
- AuthN/Z for backend API
- Configurable backend URL for the Streamlit UI
- Retry/resume for scraper tasks
- Additional analytics dashboards
- Topic partitioning and scaling strategy

---

## 17) License
MIT License — see `LICENSE`.

---

## 18) Architecture Components (Detailed)

| Component | Technology | Purpose | Default Ports/Endpoints |
| --- | --- | --- | --- |
| Frontend UI | Streamlit | User interface for issuing commands and visualizing results | 8501 (`http://localhost:8501`) |
| Backend API | FastAPI + Uvicorn | REST API, Kafka producer/consumer, Neo4j integration | 8000 (`http://localhost:8000`, docs at `/docs`) |
| Scraper Service | Playwright + NLP | Automates Facebook browsing, enriches content, publishes to Kafka | N/A (runs as a process) |
| Kafka Broker | Apache Kafka | Asynchronous messaging between backend and scraper | 9092 (localhost) |
| Zookeeper | Apache Zookeeper | Kafka coordination service | 2181 (localhost) |
| Neo4j | Neo4j | Graph storage and analytics | 7687 (Bolt), 7474 (Browser) |

Responsibilities and interactions:
- Frontend calls Backend REST endpoints; never communicates directly with Kafka or Neo4j.
- Backend publishes control messages to Kafka and consumes enriched messages; reads/writes Neo4j.
- Scraper consumes control messages, scrapes/enriches, and publishes results to Kafka.
- Neo4j holds entities/relationships for graph queries driven by Backend.

---

## 19) Ports & URLs

| Service | URL/Host | Notes |
| --- | --- | --- |
| Frontend | `http://localhost:8501` | Streamlit app |
| Backend API | `http://localhost:8000` | OpenAPI docs at `/docs` |
| Neo4j Browser | `http://localhost:7474` | Default login: `neo4j` / password configured in `.env` |
| Neo4j Bolt | `bolt://localhost:7687` | Used by Backend |
| Kafka Broker | `localhost:9092` | Used by Backend and Scraper |

---

## 20) Kafka Topics & Message Schemas

Topics:
- `scraper-control` (Backend -> Scraper)
- `fbreaper-topic` (Scraper -> Backend)

Example control message (to `scraper-control`):
```json
{
  "task_id": "9a1e4f24-1c2d-4c8b-9b05-1f8f3a7e12ab",
  "search_type": "keyword",
  "query": "genai",
  "max_posts": 50,
  "enable_likes": true,
  "timestamp": "2025-08-11T10:00:00Z"
}
```

Example enriched data message (to `fbreaper-topic`):
```json
{
  "post_id": "pfbid02...",
  "content": "Sample post text about GenAI...",
  "author": "John Doe",
  "timestamp": "2025-08-11T10:03:21Z",
  "likes": 12,
  "comments": 3,
  "shares": 1,
  "sentiment": 0.62,
  "language": "en",
  "hashtags": ["genai", "ai"],
  "entities": ["OpenAI", "GPT"]
}
```

Notes:
- Ensure Kafka’s auto topic creation is enabled or pre-create topics.
- Consider partitioning and consumer groups for scale.

---

## 21) API Quickstart (Examples)

Start a scraping task:
```bash
curl -X POST http://localhost:8000/api/scraper/start \
  -H 'Content-Type: application/json' \
  -d '{
    "search_type": "keyword",
    "query": "genai",
    "max_posts": 25,
    "enable_likes": true
  }'
```

Check scraper status:
```bash
curl http://localhost:8000/api/scraper/status
```

Health check:
```bash
curl http://localhost:8000/health
```

Consult `http://localhost:8000/docs` for the full API.

---

## 22) Startup Order & Dependencies

Recommended order:
1. Start Kafka (and Zookeeper).
2. Start Neo4j.
3. Start Backend (`python backend/main.py`).
4. Start Scraper (`python scraper/main.py`).
5. Start Frontend (`streamlit run frontend/app.py`).

Dependency notes:
- Backend depends on Kafka and Neo4j availability.
- Scraper depends on Kafka and valid Facebook credentials.
- Frontend depends on Backend.

---

## 23) Sample Cypher Queries (Neo4j)

View some nodes:
```cypher
MATCH (n) RETURN n LIMIT 50;
```

Count posts by language:
```cypher
MATCH (p:Post)
RETURN p.language AS lang, count(*) AS cnt
ORDER BY cnt DESC;
```

Top hashtags:
```cypher
MATCH (p:Post)-[:TAGGED_WITH]->(h:Hashtag)
RETURN h.tag AS hashtag, count(*) AS cnt
ORDER BY cnt DESC LIMIT 10;
```

Graph around a user:
```cypher
MATCH (u:User {id: $userId})-[:AUTHORED|COMMENTED|REACTED]->(p:Post)
OPTIONAL MATCH (p)-[:MENTIONS]->(e:Entity)
OPTIONAL MATCH (p)-[:TAGGED_WITH]->(h:Hashtag)
RETURN u, p, e, h;
```

---

## 24) Detailed Sequence Diagram (ASCII)
```
User              Frontend(UI)          Backend(API)               Kafka                 Scraper               Neo4j
 |                      |                      |                      |                      |                    |
 | Search/Start ----->  |                      |                      |                      |                    |
 |                      |  POST /api/scraper/start ------------------> |                      |                    |
 |                      |                      |  produce(scraper-control) -----------------> |                    |
 |                      |                      |                      |   consume control -->|                    |
 |                      |                      |                      |                      | Playwright login    |
 |                      |                      |                      |                      | Scrape + NLP        |
 |                      |                      |                      |  produce(fbreaper-topic) <------------------|
 |                      |                      |  consume enriched <------------------------- |                    |
 |                      |                      |  write nodes/edges to Neo4j ------------------------------------->|
 |                      |  GET data/status --->|                      |                      |                    |
 |  Results/Graphs <----|                      |                      |                      |                    |
```

---

## 25) Operational Tips
- Use consumer groups if deploying multiple backend instances to balance enriched data consumption.
- Tune scraper delays and scroll counts to be respectful and reduce bans/blocks.
- Secure the backend (auth, CORS) for non-local deployments.
- Backup Neo4j data directories if running long-lived studies.