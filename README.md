# GarageAI v2.0 - Voice-Enabled Garage Assistant

GarageAI is a cutting-edge voice assistant designed for automotive workshops. It serves as a bridge between **Twilio** (telephony) and **Google Gemini Live** (multimodal AI), enabling real-time, low-latency (<800ms) conversation with customers about appointments, vehicle status, and parts.

## 🚀 New in v2.0

- **🤖 Harry AI Persona** - The AI introduces itself as "Harry" and greets the user first.
- **📊 Real-time Dashboard** - A premium glassmorphism web interface for monitoring and testing.
- **🗄️ Database Insight** - Direct visualization of WinCar tables (Klanten, Werkorders, Voorraad) in the web app.
- **✍️ Prototype Prompt Window** - Live-inject new system instructions without restarting the server.
- **⚙️ Auto-Initialization** - The database is automatically seeded and initialized on every server run.
- **🔊 Sample Rate Optimization** - Fixed slow-motion audio by handling 16kHz input and 24kHz output paths correctly.

## 📋 Quick Start

### Fast Setup

```bash
# 1. Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies  
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env  # Then add your GOOGLE_API_KEY

# 4. Start server (This will automatically initialize the DB)
python -m uvicorn bridge.api:app --port 8000 --reload

# 5. Open Dashboard
open http://localhost:8000/web/index.html
```

## 🏗️ Architecture

```
GarageAI/
├── app/                    # Core Logic
│   ├── graph.py           # LangGraph agent
│   ├── tools.py           # WinCar database tools
│   ├── init_db.py         # Database initialization logic
│   └── mock_wincar_db.sql # SQL Seed script
├── bridge/                 # Interface Layer
│   ├── api.py             # FastAPI & DB Visualization Endpoints
│   ├── telephony.py       # WebSocket bridges (Twilio + Web)
│   └── audio.py           # Audio resampling (16k in / 24k out)
├── web_test/               # Browser Dashboard v2
│   ├── index.html         # Premium Dashboard UI
│   └── static/client.js   # Advanced WebSocket & UI Logic
├── deployment/             # Production Deployment
│   ├── deploy_cloudrun.sh # Google Cloud Run script
│   └── TWILIO_SETUP.md    # Twilio configuration guide
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md    # System design
│   ├── PRD.md             # Product requirements
│   └── API_REFERENCE.md   # Endpoint documentation
├── .env                    # Environment variables (not committed)
├── requirements.txt        # Python dependencies
└── RUN_ME.md              # Quick start guide
```

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `identify_customer` | Look up customer by phone number |
| `check_werkorder_status` | Check repair order status |
| `check_part_stock` | Query parts inventory |
| `schedule_appointment` | Book service appointments |

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/db/{name}` | GET | Fetch database table rows for visualization |
| `/ws/web` | WebSocket | Web dashboard interface (PCM 16k/24k) |
| `/ws/twilio` | WebSocket | Twilio media stream (mu-law 8k) |
| `/web/index.html` | GET | Dashboard UI |

## 🔧 Configuration

### Required Environment Variables

```env
GOOGLE_API_KEY=your_gemini_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

## 📈 Mission Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Voice Latency | < 800ms | ✅ Optimized |
| Audio Quality | Clear | ✅ Resampling Corrected |
| DB Sync | Real-time | ✅ Visualizer Added |

---

**Built with ❤️ for Garage Wiefferink**
