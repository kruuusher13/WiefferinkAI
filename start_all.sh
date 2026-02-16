#!/bin/bash

# GarageAI Full-Stack Startup Script

echo "Starting GarageAI..."

# 0. Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 1. Check for API Keys
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GOOGLE_API_KEY is not set."
    echo "  export GOOGLE_API_KEY='your_key' && ./start_all.sh"
    exit 1
fi
echo "Google API Key: OK"

# 2. Start Database
echo "Checking database..."
if ! docker ps | grep -q "wincar_sql"; then
    echo "Starting database container..."
    if ! command -v docker-compose &> /dev/null; then
        echo "Error: Docker Compose not found. Install Docker Desktop."
        exit 1
    fi
    docker-compose up -d
    echo "Waiting for DB to initialize..."
    sleep 10
    python app/init_db.py
else
    echo "Database (wincar_sql): running"
fi

# 3. Kill old processes
echo "Cleaning up old processes..."
lsof -i :8000 -t | xargs kill -9 2>/dev/null || true
lsof -i :3000 -t | xargs kill -9 2>/dev/null || true

# 4. Start FastAPI backend
echo "Starting FastAPI backend on :8000..."
nohup python -m uvicorn bridge.api:app --port 8000 --host 0.0.0.0 > server.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# 5. Start Next.js frontend
echo "Starting Next.js frontend on :3000..."
cd garage-ai-command-center

# Install dependencies if node_modules is missing
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (pnpm install)..."
    pnpm install
fi

nohup pnpm dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend started (PID: $FRONTEND_PID)"

# 6. Summary
echo ""
echo "=================================================="
echo "GarageAI ONLINE"
echo "=================================================="
echo "  Dashboard : http://localhost:3000"
echo "  Backend   : http://localhost:8000"
echo "  API docs  : http://localhost:8000/docs"
echo "  Logs      : server.log / frontend.log"
echo ""
echo "For Twilio: run  ngrok http 8000  in a new terminal"
echo "=================================================="
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait $BACKEND_PID
