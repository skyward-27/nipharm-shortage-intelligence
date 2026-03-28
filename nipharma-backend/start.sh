#!/bin/bash

# Nipharma Backend Startup Script
# Usage: ./start.sh

set -e

echo "=========================================="
echo "Nipharma Backend - Local Development"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your GROQ_API_KEY and NEWS_API_KEY"
    echo ""
fi

# Start the server
echo ""
echo "Starting Nipharma Backend..."
echo "----------------------------------------"
echo "Server will be available at:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - ReDoc: http://localhost:8000/redoc"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"
echo ""

uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
