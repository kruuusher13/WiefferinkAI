# 🚀 GarageAI - Quick Start Guide

Welcome to **GarageAI**, the voice-enabled assistant for Dutch automotive workshops. This guide will get you up and running in minutes.

---

## 📋 Prerequisites

Before you begin, ensure you have:
- **Python 3.12+** (tested on Python 3.14)
- **pip** or **uv** package manager
- **Git** (for cloning the repository)
- **Google Gemini API Key** ([Get one here](https://aistudio.google.com/app/apikey))
- **Twilio Account** (optional, only for phone integration)

---

## ⚙️ Step 1: Setting Up the Virtual Environment

### Option A: Using `venv` (Standard Python)

```bash
# Navigate to the project directory
cd /path/to/GarageAI

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Option B: Using `uv` (Faster Alternative)

```bash
# Install uv if you don't have it
pip install uv

# Create and activate environment in one step
uv venv
source .venv/bin/activate  # macOS/Linux
```

---

## 📦 Step 2: Installing Dependencies

With your virtual environment activated:

```bash
# Install all required packages
pip install -r requirements.txt

# Or using uv for faster installation:
uv pip install -r requirements.txt
```

**Expected packages:**
- FastAPI & Uvicorn (web framework)
- WebSockets (real-time communication)
- Google Gemini AI SDK
- LangChain & LangGraph (agent framework)
- Pydantic v2 (Python 3.14 compatible)
- Audio processing libraries (NumPy, SciPy)

---

## 🔑 Step 3: Configure Environment Variables

1. **Create/Edit the `.env` file** in the project root:

```bash
# Copy the example or edit directly
nano .env
```

2. **Add your credentials:**

```env
# Google Gemini API Configuration
GOOGLE_API_KEY=your_actual_api_key_here

# Twilio Configuration (optional for phone integration)
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

# Python Path (auto-set)
PYTHONPATH=/path/to/GarageAI
```

3. **Save and close** the file.

⚠️ **IMPORTANT:** Never commit your `.env` file to Git! It's already in `.gitignore`.

---

## 🎤 Step 4: Running the Local Web Microphone Test

This is the **fastest way** to test GarageAI with your laptop microphone.

### Start the Server

```bash
# Make sure your virtual environment is activated
# Make sure you're in the project root directory

# Start the FastAPI server with auto-reload
python -m uvicorn bridge.api:app --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Open the Web Test Interface

1. **Open your browser** and navigate to:
   ```
   http://localhost:8000/web/index.html
   ```

2. **You'll see** the GarageAI Voice interface with:
   - A "Start Conversation" button
   - A status indicator (initially gray/disconnected)

3. **Click "Start Conversation"**
   - Browser will ask for microphone permissions → **Allow**
   - Status should turn **green** and show "Connected (Voice Active)"
   - Button will change to "Listening..."

4. **Speak in Dutch!** Try:
   > *"Hallo GarageAI, ik wil graag een afspraak maken voor een kleine beurt aanstaande vrijdag."*
   
   Or in English:
   > *"Hello, I need to check the status of my car."*

5. **Listen** for the AI's response in the "Puck" Dutch voice.

### Troubleshooting Web Test

| Issue | Solution |
|-------|----------|
| Status stays "Disconnected" | Check console logs (F12) for errors. Verify `GOOGLE_API_KEY` is set correctly. |
| Microphone not working | Check browser permissions. Try Chrome/Edge (best compatibility). |
| No audio response | Check system volume. Verify `speech_rate` is set in `bridge/telephony.py`. |
| Server error on startup | Run `pip install -r requirements.txt` again. Check for port conflicts: `lsof -ti:8000`. |

---

## 📞 Step 5: Running the Twilio Phone Bridge (Production)

For **real phone call integration** via Twilio:

### Prerequisites

1. **Twilio Account** with:
   - A phone number (preferably Dutch: +31...)
   - Account SID and Auth Token in your `.env` file

2. **Public URL** for webhooks. Use one of:
   - **ngrok** (easiest for local testing)
   - **Cloudflare Tunnel**
   - **Google Cloud Run** (production deployment)

### Option A: Using ngrok (Local Testing)

1. **Install ngrok:**
   ```bash
   # macOS (Homebrew)
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Start the server** (same as Step 4):
   ```bash
   python -m uvicorn bridge.api:app --port 8000 --reload
   ```

3. **In a new terminal**, expose your local server:
   ```bash
   ngrok http 8000
   ```

4. **Copy the HTTPS URL** shown (e.g., `https://abc123.ngrok-free.app`)

5. **Configure Twilio:**
   - Go to your [Twilio Console](https://console.twilio.com/)
   - Navigate to **Phone Numbers** → Select your number
   - Under **Voice Configuration**, set:
     - **A Call Comes In:** Webhook
     - **URL:** `https://abc123.ngrok-free.app/ws/twilio`
     - **HTTP Method:** POST
   - **Save**

6. **Call your Twilio number** and test!

### Option B: Production Deployment (Cloud Run)

See `deployment/cloud_run.sh` for Docker-based deployment instructions.

---

## 🧪 Step 6: Testing & Verification

### Health Check

```bash
# With the server running, test the health endpoint:
curl http://localhost:8000/

# Expected response:
# {"status":"online","system":"GarageAI WinCar Integration"}
```

### Speed Test (Time to First Byte)

```bash
# Install httpie (optional, for timing):
pip install httpie

# Test latency:
time curl -s http://localhost:8000/ > /dev/null
```

**Target Performance:**
- **TTFB:** < 100ms (local health check)
- **Voice Latency:** < 800ms (speech to first AI word)
- **Speech Rate:** 1.2x (configured in `bridge/telephony.py`)

### Test Tool Execution

The AI can call these functions:
- `identify_customer` → Looks up customer by phone number
- `check_werkorder_status` → Checks repair order status
- `check_part_stock` → Checks parts inventory
- `schedule_appointment` → Books service appointments

To test, say something like:
> *"Ik wil de status van mijn auto met kenteken AB-123-CD controleren."*

---

## 🛠 Common Commands Reference

```bash
# Start Server (Local Web Test)
python -m uvicorn bridge.api:app --port 8000 --reload

# Start Server (Production Mode)
python -m uvicorn bridge.api:app --host 0.0.0.0 --port 8000

# Kill Server on Port 8000
kill -9 $(lsof -ti:8000)

# Install Dependencies
pip install -r requirements.txt

# Update Dependencies
pip install --upgrade -r requirements.txt

# Run Tests (if you have pytest)
pytest test_telephony_integration.py
```

---

## 📁 Project Structure

```
GarageAI/
├── bridge/
│   ├── api.py         # Main FastAPI app (Vapi integration)
│   ├── telephony.py   # WebSocket bridge (Twilio <-> Gemini)
│   └── audio.py       # Audio resampling utilities
├── app/
│   ├── graph.py       # LangGraph agent logic
│   ├── tools.py       # WinCar database tools
│   └── init_db.py     # Database initialization
├── web_test/
│   ├── index.html     # Web microphone test UI
│   └── static/
│       └── client.js  # WebSocket client for browser
├── deployment/
│   └── cloud_run.sh   # Google Cloud Run deployment
├── .env               # Environment variables (DO NOT COMMIT!)
├── requirements.txt   # Python dependencies
└── RUN_ME.md         # This file! 👋
```

---

## 📖 Next Steps

1. **Customize the System Prompt**
   - Edit `SYSTEM_PROMPT` in `app/graph.py`
   - Adjust Dutch garage-specific jargon

2. **Add More Tools**
   - Create new functions in `app/tools.py`
   - Register them in `bridge/telephony.py` under `TOOLS_SCHEMA`

3. **Deploy to Production**
   - Use `deployment/cloud_run.sh` for Google Cloud
   - Or deploy to Railway, Render, or Fly.io

4. **Monitor Performance**
   - Check `logs/` directory for detailed logs
   - Use Google Cloud Logging for production

---

## ❓ Troubleshooting

### "ModuleNotFoundError: No module named 'app.graph'"

**Solution:** Make sure `PYTHONPATH` is set:
```bash
export PYTHONPATH=/path/to/GarageAI
# Or add it to your .env file
```

### "Connection Refused" when testing WebSocket

**Solution:** 
1. Verify server is running: `curl http://localhost:8000/`
2. Check firewall settings
3. Try restarting the server

### "API key required for Gemini"

**Solution:**
1. Check your `.env` file has `GOOGLE_API_KEY=...`
2. Restart the server (Uvicorn must reload `.env`)
3. Verify the key is valid at [Google AI Studio](https://aistudio.google.com/)

### "Pydantic validation error" on Python 3.14

**Solution:** Make sure you have Pydantic v2:
```bash
pip install --upgrade "pydantic>=2.0" pydantic-settings
```

---

## 🎯 Success Criteria

You're ready when:
- ✅ Server starts without errors
- ✅ Web test interface shows "Connected (Voice Active)"
- ✅ You can speak and hear the Dutch "Puck" voice respond
- ✅ Response latency is < 800ms
- ✅ Tool calls appear in server logs

---

## 📞 Support & Documentation

- **Full Architecture:** See `docs/ARCHITECTURE.md`
- **PRD:** See `docs/PRD.md`
- **WinCar Integration:** See `WinCar-informatiepakket-2026.pdf`

**Maintained by:** GarageAI Development Team  
**License:** Proprietary

---

**Ready to revolutionize garage customer service? Let's go! 🚗💨**
