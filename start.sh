#!/bin/bash

# FBREAPERV1 Startup Script
# This script starts all services for the Facebook OSINT Dashboard

echo "🔍 Starting FBREAPERV1 - Facebook OSINT Dashboard"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your Facebook credentials before continuing."
    echo "   You can run this script again after configuring credentials."
    exit 1
fi

# Start infrastructure services
echo "🚀 Starting infrastructure services (Neo4j, Kafka, Zookeeper)..."
docker-compose up -d neo4j kafka zookeeper kafka-ui


# Wait for all required Docker services and Kafka port
echo "⏳ Waiting for infrastructure services (neo4j, kafka, zookeeper, kafka-ui) to be ready..."
MAX_WAIT=90
WAITED=0
ALL_UP=0
while [ $WAITED -lt $MAX_WAIT ]; do
    NEO4J=$(docker-compose ps | grep -c 'neo4j.*Up')
    KAFKA=$(docker-compose ps | grep -c 'kafka.*Up')
    ZOOKEEPER=$(docker-compose ps | grep -c 'zookeeper.*Up')
    KAFKA_UI=$(docker-compose ps | grep -c 'kafka-ui.*Up')
    if [ $NEO4J -ge 1 ] && [ $KAFKA -ge 1 ] && [ $ZOOKEEPER -ge 1 ] && [ $KAFKA_UI -ge 1 ]; then
        # Check if Kafka port is open
        if nc -z localhost 9092; then
            ALL_UP=1
            break
        fi
    fi
    sleep 2
    WAITED=$((WAITED+2))
    echo "  ...waiting ($WAITED/$MAX_WAIT sec)"
done

if [ $ALL_UP -eq 1 ]; then
    echo "✅ All infrastructure services are running and Kafka is reachable on port 9092."
else
    echo "❌ One or more infrastructure services did not start properly or Kafka is not reachable on port 9092."
    echo "   Please check 'docker-compose ps' and 'docker-compose logs' for details."
    exit 1
fi

echo ""
echo "🎉 Infrastructure services started successfully!"
echo ""
echo "📋 Service URLs:"
echo "   - Neo4j Browser: http://localhost:7474 (neo4j/fbreaper123)"
echo "   - Kafka UI: http://localhost:8081"
echo ""
echo "🚀 Starting Python services..."
echo "   (You can stop them with Ctrl+C in their respective terminals)"
echo ""

# Function to start backend
start_backend() {
    echo "🔧 Starting Backend API..."
    cd backend
    python main.py
}

# Function to start scraper
start_scraper() {
    echo "🕷️  Starting Scraper Microservice..."
    cd scraper
    python main.py
}

# Function to start frontend
start_frontend() {
    echo "🎨 Starting Frontend UI..."
    cd frontend
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0
}

# Start services in background
echo "📝 Starting services in separate terminals..."
echo "   You can also start them manually:"
echo "   - Backend: cd backend && python main.py"
echo "   - Scraper: cd scraper && python main.py"
echo "   - Frontend: cd frontend && streamlit run app.py"
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "🐧 Using tmux to start services..."
    
    # Create new tmux session
    tmux new-session -d -s fbreaper
    
    # Start backend in first window
    tmux send-keys -t fbreaper "cd backend && python main.py" C-m
    
    # Create new window for scraper
    tmux new-window -t fbreaper -n scraper
    tmux send-keys -t fbreaper:scraper "cd scraper && python main.py" C-m
    
    # Create new window for frontend
    tmux new-window -t fbreaper -n frontend
    tmux send-keys -t fbreaper:frontend "cd frontend && streamlit run app.py --server.port 8501 --server.address 0.0.0.0" C-m
    
    echo "✅ Services started in tmux session 'fbreaper'"
    echo "   To attach to the session: tmux attach-session -t fbreaper"
    echo "   To detach: Ctrl+B, then D"
    echo "   To kill session: tmux kill-session -t fbreaper"
    
else
    echo "⚠️  tmux not available. Please start services manually:"
    echo ""
    echo "Terminal 1 (Backend):"
    echo "  cd backend && python main.py"
    echo ""
    echo "Terminal 2 (Scraper):"
    echo "  cd scraper && python main.py"
    echo ""
    echo "Terminal 3 (Frontend):"
    echo "  cd frontend && streamlit run app.py"
fi

echo ""
echo "🎯 Once all services are running, access the dashboard at:"
echo "   http://localhost:8501"
echo ""
echo "📚 API Documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "🔍 Happy OSINT gathering! 🕵️‍♂️"