# GarageAI Deployment Guide

Step-by-step guide to deploy GarageAI for pilot validation with a live garage.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                        INTERNET                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐     ┌─────────────────────────┐        │
│  │   Vercel     │     │  Google Cloud Run        │        │
│  │  Dashboard   │────▶│  (garageai-bridge)       │        │
│  │  :443        │ API │  europe-west4            │        │
│  └─────────────┘     │                           │        │
│        ▲              │  FastAPI + Gemini Live    │        │
│        │              │  Twilio WS + Web WS      │        │
│     Browser           └────────┬──────────────────┘        │
│     (mic/speaker)              │                           │
│                                │ SQL (port 1433)           │
│                     ┌──────────▼──────────┐                │
│                     │  ngrok TCP tunnel   │                │
│                     └──────────┬──────────┘                │
│                                │                           │
├────────────────────────────────┼───────────────────────────┤
│              GARAGE LAN        │                           │
│                     ┌──────────▼──────────┐                │
│                     │  WinCar Server      │                │
│                     │  SQL Server :1433   │                │
│                     └─────────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Accounts & Keys
- [ ] **Google Cloud** account with billing enabled
- [ ] **Google AI Studio** API key ([get one here](https://aistudio.google.com/app/apikey))
- [ ] **Vercel** account (free tier works)
- [ ] **Twilio** account with a Dutch phone number (optional — web mic works without it)
- [ ] **ngrok** account (free tier works for testing)

### Tools (on your laptop)
```bash
# Google Cloud CLI
brew install google-cloud-sdk

# Vercel CLI
npm i -g vercel

# ngrok
brew install ngrok/ngrok/ngrok
```

---

## Phase 1: Deploy the Backend (Google Cloud Run)

### 1.1 Create a GCP Project

```bash
gcloud projects create garageai-pilot --name="GarageAI Pilot"
gcloud config set project garageai-pilot
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 1.2 Build & Push the Docker Image

From the project root:
```bash
gcloud builds submit --tag gcr.io/garageai-pilot/garageai-bridge
```

This builds the Dockerfile (Python 3.12 + ODBC Driver 17 + all deps) in the cloud.

### 1.3 Deploy to Cloud Run

```bash
gcloud run deploy garageai-bridge \
  --image gcr.io/garageai-pilot/garageai-bridge \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --timeout 300 \
  --set-env-vars "\
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY,\
WINCAR_DB_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=NGROK_TCP_HOST;PORT=NGROK_TCP_PORT;DATABASE=WinCarLive;UID=sa;PWD=GARAGE_SA_PASSWORD,\
WINCAR_DB_MASTER_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=NGROK_TCP_HOST;PORT=NGROK_TCP_PORT;DATABASE=master;UID=sa;PWD=GARAGE_SA_PASSWORD;Connection Timeout=3,\
CORS_ORIGIN=https://YOUR_VERCEL_DOMAIN"
```

> **Note:** Replace placeholder values. The ngrok values come from Phase 3.
> You'll update these env vars after setting up the tunnel.

**Save the Service URL** — it will look like:
```
https://garageai-bridge-xxxxx-ew.a.run.app
```

### 1.4 Verify Deployment

```bash
curl https://garageai-bridge-xxxxx-ew.a.run.app/
# Should return: {"status":"online","system":"GarageAI WinCar Integration"}
```

---

## Phase 2: Deploy the Dashboard (Vercel)

### 2.1 Deploy

```bash
cd garage-ai-command-center
vercel
```

Follow the prompts. When asked for the framework, select **Next.js**.

### 2.2 Set Environment Variables

In the Vercel dashboard (or CLI):
```bash
vercel env add NEXT_PUBLIC_BRIDGE_URL
# Value: https://garageai-bridge-xxxxx-ew.a.run.app
```

Then redeploy:
```bash
vercel --prod
```

### 2.3 Verify

Open your Vercel URL. The dashboard should load. The status bar will show "offline" until the backend + database are connected.

### 2.4 Update Cloud Run CORS

Now that you have the Vercel domain, update Cloud Run:
```bash
gcloud run services update garageai-bridge \
  --region europe-west4 \
  --update-env-vars "CORS_ORIGIN=https://your-app.vercel.app"
```

---

## Phase 3: Connect the Garage Database (ngrok tunnel)

This is done **on-site at the garage** on the WinCar server.

### 3.1 Install ngrok on the WinCar Server

Download from [ngrok.com/download](https://ngrok.com/download) (Windows).

Authenticate:
```cmd
ngrok config add-authtoken YOUR_NGROK_AUTH_TOKEN
```

### 3.2 Start the TCP Tunnel

```cmd
ngrok tcp 1433
```

Output will show:
```
Forwarding  tcp://0.tcp.eu.ngrok.io:12345 -> localhost:1433
```

**Save the host and port** (e.g., `0.tcp.eu.ngrok.io` and `12345`).

### 3.3 Update Cloud Run with the Tunnel Address

```bash
gcloud run services update garageai-bridge \
  --region europe-west4 \
  --update-env-vars "\
WINCAR_DB_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=0.tcp.eu.ngrok.io,12345;DATABASE=WinCarLive;UID=sa;PWD=ACTUAL_SA_PASSWORD,\
WINCAR_DB_MASTER_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=0.tcp.eu.ngrok.io,12345;DATABASE=master;UID=sa;PWD=ACTUAL_SA_PASSWORD;Connection Timeout=3"
```

> **Important:** SQL Server uses comma (not colon) for port: `SERVER=host,port`

### 3.4 Verify Database Connection

```bash
curl https://garageai-bridge-xxxxx-ew.a.run.app/api/db/customers
# Should return customer data from the live WinCar database
```

---

## Phase 4: Twilio Phone Integration (Optional)

Skip this phase if you only want to test via the web dashboard microphone.

### 4.1 Create a TwiML Bin

1. Go to **Twilio Console** > **Developer Tools** > **TwiML Bins**
2. Create new with name: `GarageAI Stream`
3. Paste this TwiML (replace domain):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://garageai-bridge-xxxxx-ew.a.run.app/ws/twilio" />
    </Connect>
</Response>
```

### 4.2 Point Your Phone Number

1. Go to **Phone Numbers** > **Active Numbers**
2. Click your Dutch number
3. Under **Voice** > **A Call Comes In**: select **TwiML Bin** > `GarageAI Stream`
4. Save

### 4.3 Test

Call your Twilio number. Harry should answer in Dutch.

---

## Phase 5: Testing via Web Dashboard (No Twilio needed)

The dashboard has a built-in voice widget with microphone support.

1. Open the Vercel dashboard URL on any device with a microphone
2. Click **Connect** — this opens a WebSocket to the Cloud Run backend
3. Click **Unmute** — your mic starts streaming 16kHz PCM to Gemini
4. Speak to Harry — he'll respond via your speakers
5. The Live Stream panel shows the transcript in real-time
6. The Vehicle Context panel populates when a kenteken is mentioned
7. The Action Queue shows pending werkorders from the conversation

### Troubleshooting Web Mic
- **Browser blocks mic**: Ensure the Vercel URL uses HTTPS (it does by default)
- **No audio playback**: Click anywhere on the page first (browser autoplay policy)
- **"OFFLINE" status**: Check that `NEXT_PUBLIC_BRIDGE_URL` points to your Cloud Run URL

---

## On-Site at the Garage — Day 1 Checklist

### Before Arriving
- [ ] Cloud Run backend deployed and returning health check
- [ ] Vercel dashboard deployed and loading
- [ ] Twilio TwiML Bin configured (if using phone)
- [ ] ngrok installed on your laptop as backup

### At the Garage
1. **Access the WinCar server**
   - [ ] Confirm SQL Server is running on port 1433
   - [ ] Get the `sa` password (or a read-only SQL account)
   - [ ] Install ngrok on the server

2. **Start the tunnel**
   ```cmd
   ngrok tcp 1433
   ```
   - [ ] Note the forwarding address

3. **Update Cloud Run env vars** with the tunnel address (from your laptop)

4. **Test the connection**
   - [ ] Open the dashboard: `curl YOUR_CLOUD_RUN_URL/api/db/customers`
   - [ ] Verify customer data appears

5. **Demo to the garage owner**
   - [ ] Open dashboard on a tablet/laptop
   - [ ] Click Connect + Unmute
   - [ ] Say: "Hallo, ik bel over mijn auto met kenteken XX-YY-ZZ"
   - [ ] Observe Harry identifying the customer and vehicle in the dashboard
   - [ ] Ask: "Wat is de status van mijn werkorder?"
   - [ ] Show the live transcript, vehicle context, and action queue

6. **Phone test** (if Twilio is set up)
   - [ ] Call the Twilio number
   - [ ] Observe the dashboard showing the call in progress
   - [ ] Verify Harry responds in Dutch

### If ngrok Disconnects
The free tier gives a random URL each restart. After restarting ngrok:
1. Copy the new forwarding address
2. Update Cloud Run: `gcloud run services update garageai-bridge --update-env-vars "WINCAR_DB_CONNECTION=..."`
3. Wait ~30 seconds for Cloud Run to redeploy

**Tip:** Consider upgrading to ngrok's paid plan ($8/mo) for a fixed TCP address.

---

## Environment Variables Reference

### Cloud Run (backend)
| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `WINCAR_DB_CONNECTION` | Yes | SQL Server connection string for WinCarLive |
| `WINCAR_DB_MASTER_CONNECTION` | No | SQL Server connection to `master` DB (for init only) |
| `CORS_ORIGIN` | Yes | Vercel production URL |
| `TWILIO_ACCOUNT_SID` | No | Twilio SID (for phone integration) |
| `TWILIO_AUTH_TOKEN` | No | Twilio auth token |

### Vercel (frontend)
| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_BRIDGE_URL` | Yes | Cloud Run service URL (e.g., `https://garageai-bridge-xxx.a.run.app`) |

---

## Cost Estimate (Pilot)

| Service | Free Tier | Expected Cost |
|---|---|---|
| Cloud Run | 2M requests/month free | ~$0 for pilot |
| Vercel | Hobby plan free | $0 |
| Gemini API | Free tier available | ~$5-10/month for testing |
| ngrok | Free tier (random URLs) | $0 (or $8/mo for fixed address) |
| Twilio | Pay-as-you-go | ~$1/mo for number + ~$0.02/min |
