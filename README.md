# FBREAPERV1 — Facebook OSINT Dashboard (Non‑Docker)

## Overview
FBREAPERV1 is a modular Python platform for real‑time Facebook OSINT: scraping, enrichment, storage, and visualization.

Components:
- Frontend UI: Streamlit (port 8501)
- Backend API: FastAPI + Uvicorn (port 8000)
- Scraper Service: Playwright + NLP (Kafka producer/consumer)
- Data Store: Neo4j
- Messaging: Kafka (with Zookeeper)

## Prerequisites
- Python 3.9+
- Kafka and Zookeeper running locally (default: localhost:9092)
- Neo4j running locally (default: bolt://localhost:7687)
- Facebook account for scraping

You can override endpoints via environment variables in a `.env` file:
- NEO4J_URI (default: bolt://localhost:7687)
- NEO4J_USER (default: neo4j)
- NEO4J_PASSWORD (default: fbreaper123)
- KAFKA_BOOTSTRAP_SERVERS (default: localhost:9092)
- KAFKA_TOPIC_SCRAPER_CONTROL (default: scraper-control)
- KAFKA_TOPIC_FBREAPER_DATA (default: fbreaper-topic)
- FACEBOOK_EMAIL / FACEBOOK_PASSWORD

## Setup
Install dependencies and required runtime assets:
```bash
pip install -r requirements.txt
playwright install chromium
python -m spacy download en_core_web_sm
# Optional (usually auto-downloaded by the app if missing):
python - << 'PY'
import nltk
for pkg in [
  'punkt','stopwords','averaged_perceptron_tagger','maxent_ne_chunker','words'
]:
    nltk.download(pkg)
print('Downloaded NLTK data')
PY
```

Create and edit your `.env`:
```bash
cp .env.example .env
# Set FACEBOOK_EMAIL and FACEBOOK_PASSWORD
# Optionally set Kafka/Neo4j connection values
```

## Running Services (without Docker)
Ensure Kafka and Neo4j are running locally or provide remote endpoints via `.env`.

Run each service in separate terminals:
```bash
# Terminal 1: Backend API
python backend/main.py

# Terminal 2: Scraper Service
python scraper/main.py

# Terminal 3: Frontend UI
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

## URLs
- Frontend: http://localhost:8501
- Backend API docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

## Data Flow
1. Frontend sends commands to Backend.
2. Backend publishes control messages to Kafka (`scraper-control`).
3. Scraper consumes control messages, scrapes Facebook, enriches text, and publishes to Kafka (`fbreaper-topic`).
4. Backend consumes enriched data and writes it to Neo4j.
5. Frontend queries Backend to visualize live data and network graphs.

## Notes
- This project no longer uses Docker, Docker Compose, or shell helper scripts. All setup and run steps are listed above.
- Some Linux environments may require additional system libraries for Playwright.

## License
MIT License. See `LICENSE`.