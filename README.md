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
```bash
pip install -r requirements.txt
./setup.sh
# This installs Python deps, Playwright browser, spaCy model, and NLTK data
```

Create and edit your `.env`:
```bash
cp .env.example .env
# Set FACEBOOK_EMAIL and FACEBOOK_PASSWORD
# Optionally set Kafka/Neo4j connection values
```

## Running Services (without Docker)
- Ensure Kafka and Neo4j are running locally.
- Option A: One command to start everything (background):
```bash
./start_all.sh
```
- Option B: Start interactively in a terminal multiplexer not required:
```bash
# Backend API
python backend/main.py

# Scraper Service
python scraper/main.py

# Frontend UI
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

Stop background services:
```bash
./stop.sh
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
- This project no longer uses Docker or Docker Compose. Ensure Kafka and Neo4j are installed and running locally, or configure remote services via `.env`.
- For Playwright to work headlessly in some Linux environments, additional system libraries may be required; `playwright install chromium` is already handled in `setup.sh`.

## License
MIT License. See `LICENSE`.