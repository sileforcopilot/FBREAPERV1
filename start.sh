#!/bin/bash

# FBREAPERV1 Startup Script
# This script starts all services for the Facebook OSINT Dashboard

echo "🔍 Starting FBREAPERV1 - Facebook OSINT Dashboard"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your Facebook credentials before continuing."
    echo "   You can run this script again after configuring credentials."
    exit 1
fi

# Check local infrastructure availability (Kafka, Neo4j)
echo "🔎 Checking local infrastructure (Kafka at localhost:9092, Neo4j at localhost:7687)..."
if nc -z localhost 9092; then
    echo "✅ Kafka reachable on localhost:9092"
else
    echo "⚠️  Kafka not reachable on localhost:9092. Start Kafka locally or set KAFKA_BOOTSTRAP_SERVERS in your .env."
fi

if nc -z localhost 7687; then
    echo "✅ Neo4j reachable on localhost:7687"
else
    echo "⚠️  Neo4j not reachable on localhost:7687. Start Neo4j locally or set NEO4J_URI in your .env."
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