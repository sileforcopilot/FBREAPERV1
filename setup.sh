#!/bin/bash

# FBREAPERV1 Setup Script
# This script sets up the initial installation

echo "🔧 FBREAPERV1 Setup Script"
echo "=========================="

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version is compatible"
else
    echo "❌ Python $python_version is too old. Please install Python 3.9+"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

if [ $? -eq 0 ]; then
    echo "✅ Playwright browsers installed successfully"
else
    echo "❌ Failed to install Playwright browsers"
    exit 1
fi

# Download spaCy model
echo "🧠 Downloading spaCy model..."
python3 -m spacy download en_core_web_sm

if [ $? -eq 0 ]; then
    echo "✅ spaCy model downloaded successfully"
else
    echo "❌ Failed to download spaCy model"
    exit 1
fi

# Download NLTK data
echo "📚 Downloading NLTK data..."
python3 -c "
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')
print('NLTK data downloaded')
"

if [ $? -eq 0 ]; then
    echo "✅ NLTK data downloaded successfully"
else
    echo "❌ Failed to download NLTK data"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env file with your Facebook credentials"
else
    echo "ℹ️  .env file already exists"
fi

# Create logs directory
mkdir -p logs
echo "✅ Logs directory created"

# Note on infrastructure
echo "ℹ️  Docker and Docker Compose are not required. Ensure Kafka and Neo4j are installed and running locally, or set remote endpoints via environment variables."

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your Facebook credentials"
echo "2. Run ./start.sh to start all services"
echo "3. Access the dashboard at http://localhost:8501"
echo ""
echo "📚 For more information, see README.md"