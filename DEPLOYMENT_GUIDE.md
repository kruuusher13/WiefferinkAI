# GarageAI Deployment Guide

Step-by-step guide to deploy GarageAI on Google Cloud for pilot validation with a live garage.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     GOOGLE CLOUD (europe-west4)              │
│                                                              │
│  ┌──────────────────────┐     ┌──────────────────────────┐   │
│  │  Cloud Run            │     │  Cloud Run                │   │
│  │  garageai-dashboard   │────▶│  garageai-bridge          │   │
│  │  (Next.js :3000)      │ WS  │  (FastAPI :8080)          │   │
│  └──────────┬───────────┘     │                            │   │
│             │                  │  Gemini Live API           │   │
│          Browser               │  Twilio WebSocket          │   │
│        (mic/speaker)           │  Tool execution            │   │
│                                └──────────┬─────────────────┘   │
│                                           │                     │
└───────────────────────────────────────────┼─────────────────────┘
                                            │ SQL (port 1433)
                                 ┌──────────▼──────────┐
                                 │  ngrok TCP tunnel   │
                                 └──────────┬──────────┘
                                            │
                              ┌─────────────▼───────────────┐
                              │  GARAGE LAN                 │
                              │  WinCar Server              │
                              │  SQL Server :1433           │
                              └─────────────────────────────┘
```

**Two Cloud Run services:**
- **garageai-bridge** — Python backend (FastAPI, Gemini Live, Twilio WS, tool execution)
- **garageai-dashboard** — Next.js frontend (Command Center UI, voice widget, mic capture)

---

## Prerequisites

### Accounts & Keys
- [ ] **Google Cloud** account with billing enabled
- [ ] **Google AI Studio** API key ([get one here](https://aistudio.google.com/app/apikey))
- [ ] **Twilio** account with a Dutch phone number (optional — web mic works without it)
- [ ] **ngrok** account (free tier works for testing)

### Tools (on your laptop)
```bash
# Google Cloud CLI
brew install google-cloud-sdk

# ngrok (for testing locally or as backup at the garage)
brew install ngrok/ngrok/ngrok
```

---

## Phase 1: GCP Project Setup

```bash
# Create project (or use existing)
gcloud projects create garageai-pilot --name="GarageAI Pilot"
gcloud config set project garageai-pilot

# Enable required services
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

# Set default region (Netherlands)
gcloud config set run/region europe-west4
```

---

## Phase 2: Deploy the Backend (garageai-bridge)

### 2.1 Build & Push

From the project root:
```bash
gcloud builds submit --tag gcr.io/garageai-pilot/garageai-bridge
```

This builds the Dockerfile (Python 3.12 + ODBC Driver 17 + all deps) in the cloud. Takes ~5 minutes on first build.

### 2.2 Deploy to Cloud Run

```bash
gcloud run deploy garageai-bridge \
  --image gcr.io/garageai-pilot/garageai-bridge \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --timeout 300 \
  --session-affinity \
  --set-env-vars "\
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY"
```

> **Note:** We'll add the DB connection and CORS vars after deploying the dashboard and setting up the tunnel.

> **`--session-affinity`** is important for WebSocket connections — it ensures a client's requests go to the same container instance.

**Save the Service URL:**
```
https://garageai-bridge-xxxxx-ew.a.run.app
```

### 2.3 Verify

```bash
curl https://garageai-bridge-xxxxx-ew.a.run.app/
# → {"status":"online","system":"GarageAI WinCar Integration"}
```

---

## Phase 3: Deploy the Dashboard (garageai-dashboard)

### 3.1 Build & Push

The `NEXT_PUBLIC_BRIDGE_URL` must be set at **build time** because Next.js inlines it into the JavaScript bundle.

```bash
cd garage-ai-command-center

gcloud builds submit \
  --tag gcr.io/garageai-pilot/garageai-dashboard \
  --build-arg NEXT_PUBLIC_BRIDGE_URL=https://garageai-bridge-xxxxx-ew.a.run.app
```

> Replace `xxxxx` with your actual backend Cloud Run URL from Phase 2.

### 3.2 Deploy to Cloud Run

```bash
gcloud run deploy garageai-dashboard \
  --image gcr.io/garageai-pilot/garageai-dashboard \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi
```

**Save the Dashboard URL:**
```
https://garageai-dashboard-xxxxx-ew.a.run.app
```

### 3.3 Update Backend CORS

Now that you have the dashboard URL, update the backend to accept requests from it:

```bash
gcloud run services update garageai-bridge \
  --region europe-west4 \
  --update-env-vars "CORS_ORIGIN=https://garageai-dashboard-xxxxx-ew.a.run.app"
```

### 3.4 Verify

Open the dashboard URL in your browser. It should load the Command Center. The status bar will show "OFFLINE" until you connect — that's expected.

---

## Phase 4: Connect the Garage Database (ngrok tunnel)

This is done **on-site at the garage** on the WinCar server.

### 4.1 Install ngrok on the WinCar Server

Download from [ngrok.com/download](https://ngrok.com/download) (Windows).

Authenticate:
```cmd
ngrok config add-authtoken YOUR_NGROK_AUTH_TOKEN
```

### 4.2 Start the TCP Tunnel

```cmd
ngrok tcp 1433
```

Output will show:
```
Forwarding  tcp://0.tcp.eu.ngrok.io:12345 -> localhost:1433
```

**Save the host and port** (e.g., `0.tcp.eu.ngrok.io` and `12345`).

### 4.3 Update Cloud Run with the Tunnel Address

From your laptop:
```bash
gcloud run services update garageai-bridge \
  --region europe-west4 \
  --update-env-vars "\
WINCAR_DB_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=0.tcp.eu.ngrok.io\,12345;DATABASE=WinCarLive;UID=sa;PWD=ACTUAL_SA_PASSWORD,\
WINCAR_DB_MASTER_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=0.tcp.eu.ngrok.io\,12345;DATABASE=master;UID=sa;PWD=ACTUAL_SA_PASSWORD;Connection Timeout=3"
```

> **Important:** SQL Server uses comma for port: `SERVER=host,port`. Escape the comma with `\,` in the gcloud command to prevent it being parsed as an env var separator.

### 4.4 Verify Database Connection

```bash
curl https://garageai-bridge-xxxxx-ew.a.run.app/api/db/customers
# → Should return customer data from the live WinCar database
```

---

## Phase 5: Twilio Phone Integration (Optional)

Skip this if you only want to test via the web dashboard microphone.

### 5.1 Create a TwiML Bin

1. Go to **Twilio Console** > **Developer Tools** > **TwiML Bins**
2. Create new with name: `GarageAI Stream`
3. Paste (replace with your backend URL):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://garageai-bridge-xxxxx-ew.a.run.app/ws/twilio" />
    </Connect>
</Response>
```

### 5.2 Point Your Phone Number

1. Go to **Phone Numbers** > **Active Numbers**
2. Click your Dutch number
3. Under **Voice** > **A Call Comes In**: select **TwiML Bin** > `GarageAI Stream`
4. Save

### 5.3 Test

Call your Twilio number. Harry should answer in Dutch.

---

## Phase 6: Testing via Web Dashboard (No Twilio needed)

The dashboard has a built-in voice widget with microphone support.

1. Open the dashboard URL on any device with a microphone
2. Click **Connect** — opens a WebSocket to the backend
3. Click **Unmute** — mic starts streaming 16kHz PCM to Gemini
4. Speak to Harry — he responds via your speakers
5. The **Live Stream** panel shows the transcript in real-time
6. The **Vehicle Context** panel populates when a kenteken is mentioned
7. The **Action Queue** shows pending werkorders from the conversation

### Troubleshooting
- **Browser blocks mic**: Cloud Run serves HTTPS by default — should work. Check browser permissions.
- **No audio playback**: Click anywhere on the page first (browser autoplay policy)
- **"OFFLINE" status**: Check that the backend URL is correct in the build. Rebuild the dashboard image if needed.
- **WebSocket drops**: Cloud Run has a 5-minute idle timeout by default. The `--timeout 300` flag on the backend helps. For longer calls, consider keeping a heartbeat.

---

## On-Site at the Garage — Day 1 Checklist

### Before Arriving
- [ ] Backend Cloud Run deployed and returning health check
- [ ] Dashboard Cloud Run deployed and loading
- [ ] Twilio TwiML Bin configured (if using phone)
- [ ] ngrok installed on your laptop as backup
- [ ] Tested the full flow with mock data locally

### At the Garage

1. **Access the WinCar server**
   - [ ] Confirm SQL Server is running on port 1433
   - [ ] Get the `sa` password (or a read-only SQL user)
   - [ ] Install ngrok on the server (or your laptop on the same network)

2. **Start the tunnel**
   ```cmd
   ngrok tcp 1433
   ```
   - [ ] Note the forwarding address

3. **Update Cloud Run env vars** with the tunnel address (from your phone/laptop)
   ```bash
   gcloud run services update garageai-bridge --region europe-west4 \
     --update-env-vars "WINCAR_DB_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=HOST\,PORT;DATABASE=WinCarLive;UID=sa;PWD=PASSWORD"
   ```

4. **Test the connection**
   ```bash
   curl https://YOUR_BRIDGE_URL/api/db/customers
   ```
   - [ ] Verify customer data appears

5. **Demo to the garage owner**
   - [ ] Open dashboard on a tablet/laptop
   - [ ] Click **Connect** + **Unmute**
   - [ ] Say: _"Hallo, ik bel over mijn auto met kenteken XX-YY-ZZ"_
   - [ ] Observe Harry identifying the customer and vehicle in the dashboard
   - [ ] Ask: _"Wat is de status van mijn werkorder?"_
   - [ ] Show the live transcript, vehicle context, and action queue

6. **Phone test** (if Twilio is set up)
   - [ ] Call the Twilio number
   - [ ] Observe the dashboard updating with the call
   - [ ] Verify Harry responds in Dutch

### If ngrok Disconnects
Free tier gives a random URL each restart. After restarting:
1. Copy the new forwarding address
2. Update Cloud Run env vars
3. Wait ~30 seconds for Cloud Run to redeploy

**Tip:** Upgrade to ngrok paid plan ($8/mo) for a fixed TCP address.

---

## Updating After Code Changes

### Backend changes
```bash
# From project root
gcloud builds submit --tag gcr.io/garageai-pilot/garageai-bridge
gcloud run deploy garageai-bridge \
  --image gcr.io/garageai-pilot/garageai-bridge \
  --region europe-west4
```

### Dashboard changes
```bash
# From garage-ai-command-center/
gcloud builds submit \
  --tag gcr.io/garageai-pilot/garageai-dashboard \
  --build-arg NEXT_PUBLIC_BRIDGE_URL=https://garageai-bridge-xxxxx-ew.a.run.app

gcloud run deploy garageai-dashboard \
  --image gcr.io/garageai-pilot/garageai-dashboard \
  --region europe-west4
```

---

## Environment Variables Reference

### garageai-bridge (backend)
| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `WINCAR_DB_CONNECTION` | Yes | SQL Server connection string for WinCarLive |
| `WINCAR_DB_MASTER_CONNECTION` | No | SQL Server connection to `master` DB (for DB init only) |
| `CORS_ORIGIN` | Yes | Dashboard Cloud Run URL |
| `TWILIO_ACCOUNT_SID` | No | Twilio SID (for phone integration) |
| `TWILIO_AUTH_TOKEN` | No | Twilio auth token |

### garageai-dashboard (frontend)
| Variable | Set At | Description |
|---|---|---|
| `NEXT_PUBLIC_BRIDGE_URL` | Build time | Backend Cloud Run URL (passed as `--build-arg`) |

---

## Cost Estimate (Pilot)

| Service | Free Tier | Expected Cost |
|---|---|---|
| Cloud Run (backend) | 2M requests/month free | ~$0 for pilot |
| Cloud Run (dashboard) | 2M requests/month free | ~$0 for pilot |
| Cloud Build | 120 min/day free | ~$0 |
| Gemini API | Free tier available | ~$5-10/month for testing |
| ngrok | Free tier (random URLs) | $0 (or $8/mo for fixed address) |
| Twilio | Pay-as-you-go | ~$1/mo for number + ~$0.02/min |

**Total estimated pilot cost: $5-20/month**
