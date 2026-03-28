#!/bin/bash

# Nipharma Intelligence - Development Server Startup Script
# Starts both FastAPI backend and React frontend in parallel

set -e

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=================================================="
echo "🚀 Nipharma Intelligence - Development Server"
echo "=================================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi

echo "✅ Python and Node.js found"
echo ""

# Start Backend
echo "📋 Starting FastAPI Backend..."
cd "$BASE_DIR/nipharma-backend"

if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true

echo "  Backend starting at http://localhost:8000"
echo "  Swagger UI: http://localhost:8000/docs"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 2

# Start Frontend
echo ""
echo "📋 Starting React Frontend..."
cd "$BASE_DIR/nipharma-frontend"

if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install -q 2>/dev/null || yarn install -q 2>/dev/null
fi

echo "  Frontend starting at http://localhost:3000"
npm start &
FRONTEND_PID=$!

sleep 3

echo ""
echo "=================================================="
echo "✅ Both servers are running!"
echo "=================================================="
echo ""
echo "Dashboard:     http://localhost:3000"
echo "API Docs:      http://localhost:8000/docs"
echo "Backend:       http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Keep script running
wait $BACKEND_PID $FRONTEND_PID
