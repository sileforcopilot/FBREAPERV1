
#!/bin/bash
# Start docker-compose services, then wait for Kafka to be ready, then start backend and scraper
docker-compose up -d

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

# Start backend (in background)
echo "Starting backend..."
cd backend && nohup python3 main.py > ../logs/backend.log 2>&1 &
cd ..

# Start scraper (in background)
echo "Starting scraper..."
cd scraper && nohup python3 main.py > ../logs/scraper.log 2>&1 &
cd ..

echo "All services started. Check logs in logs/ directory."
