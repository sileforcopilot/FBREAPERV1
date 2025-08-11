
#!/bin/bash
# Start local services without Docker Compose. Ensure Kafka and Neo4j are running locally.
mkdir -p logs

KAFKA_HOST="localhost"
KAFKA_PORT=9092
TIMEOUT=60

# Wait for Kafka
for i in $(seq 1 $TIMEOUT); do
  nc -z $KAFKA_HOST $KAFKA_PORT && echo "Kafka is up!" && break
  echo "Waiting for Kafka at $KAFKA_HOST:$KAFKA_PORT... ($i/$TIMEOUT)"
  sleep 1
done

if ! nc -z $KAFKA_HOST $KAFKA_PORT; then
  echo "Kafka did not start within $TIMEOUT seconds. Exiting."
  exit 1
fi

# Wait for Neo4j
NEO4J_HOST="localhost"
NEO4J_PORT=7687
for i in $(seq 1 $TIMEOUT); do
  nc -z $NEO4J_HOST $NEO4J_PORT && echo "Neo4j is up!" && break
  echo "Waiting for Neo4j at $NEO4J_HOST:$NEO4J_PORT... ($i/$TIMEOUT)"
  sleep 1
done

if ! nc -z $NEO4J_HOST $NEO4J_PORT; then
  echo "Neo4j did not start within $TIMEOUT seconds. Continuing, but backend may fail to connect."
fi

# Start backend (in background)
echo "Starting backend..."
cd backend && nohup python3 main.py > ../logs/backend.log 2>&1 &
cd ..

# Start scraper (in background)
echo "Starting scraper..."
cd scraper && nohup python3 main.py > ../logs/scraper.log 2>&1 &
cd ..

# Optionally start frontend via streamlit
if command -v streamlit &> /dev/null; then
  echo "Starting frontend (Streamlit)..."
  nohup streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 > logs/frontend.log 2>&1 &
else
  echo "⚠️  streamlit not found. Install it to run the frontend: pip install streamlit streamlit-agraph plotly networkx"
fi

echo "All services started. Check logs in logs/ directory."
