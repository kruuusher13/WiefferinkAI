#!/bin/bash

# TorxFlow Full-Stack Startup Script

echo "Starting TorxFlow..."

# 0. Load .env (supports values with spaces)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 1. Check for API Keys
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GOOGLE_API_KEY is not set."
    echo "  export GOOGLE_API_KEY='your_key' && ./start_all.sh"
    exit 1
fi
echo "Google API Key: OK"

# 2. Kill old processes
echo "Cleaning up old processes..."
lsof -i :8000 -t | xargs kill -9 2>/dev/null || true
lsof -i :3000 -t | xargs kill -9 2>/dev/null || true

# 3. Start FastAPI backend
echo "Starting FastAPI backend on :8000..."
nohup python -m uvicorn bridge.api:app --port 8000 --host 0.0.0.0 --reload > server.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# 4. Start Next.js frontend
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

# 5. Summary
echo ""
echo "=================================================="
echo "TorxFlow ONLINE"
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
