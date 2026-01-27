#!/bin/bash

# GarageAI Startup Script (Fool-proof)

echo "🚗 Starting GarageAI System..."

# 1. Check for API Keys
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: GOOGLE_API_KEY is not set!"
    echo "Usage: export GOOGLE_API_KEY='your_key' && ./start_all.sh"
    exit 1
else
    echo "✅ Google API Key found."
fi

# 2. Check Docker (DB)
echo "📦 Checking Database..."
if ! docker ps | grep -q "wincar_sql"; then
    echo "⚠️  Database container not found. Starting it..."
    if ! command -v docker-compose &> /dev/null; then
         echo "❌ Docker Compose not found. Please install Docker Desktop."
         exit 1
    fi
    docker-compose up -d
     echo "⏳ Waiting 10s for DB to initialize..."
    sleep 10
    echo "🔄 Initializing Schema..."
    python init_db.py
else
    echo "✅ Database Container (wincar_sql) is running."
fi

# 3. Kill old servers
echo "🧹 Cleaning up old processes..."
lsof -i :8000 -t | xargs kill -9 2>/dev/null || true

# 4. Start Server
echo "🚀 Starting FastAPI Server on Port 8000..."
# Run in background
nohup python main.py > server.log 2>&1 &
SERVER_PID=$!
echo "✅ Server started (PID: $SERVER_PID). Logs are in 'server.log'."

# 5. Ngrok Instructions
echo ""
echo "=================================================="
echo "🌐 SYSTEM ONLINE"
echo "=================================================="
echo "1. Your local server is running at http://localhost:8000"
echo "2. PLEASE RUN NGROK MANUALLY IN A NEW TERMINAL:"
echo "   ngrok http 8000"
echo "3. Copy the https URL from ngrok (e.g. https://xyz.ngrok-free.app)"
echo "4. Paste it into Vapi Dashboard -> Assistant -> Server URL:"
echo "   <your-ngrok-url>/chat"
echo "=================================================="
echo "Press Ctrl+C to stop the server when done."

# Keep script running to maintain user focus or handle cleanup
trap "kill $SERVER_PID" EXIT
wait $SERVER_PID
