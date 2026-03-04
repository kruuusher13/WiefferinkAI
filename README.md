# TorxFlow

Voice-enabled AI receptionist (Harry) for Dutch automotive garages. Real-time phone and web conversations via the Gemini Live API, looking up vehicle data from RDW, managing appointment requests with Google Calendar, and notifying owners via email — all with sub-800ms latency.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  GOOGLE CLOUD (europe-west4)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Cloud Run: garageai-bridge                                  ││
│  │  FastAPI :8080  +  Static Next.js frontend                   ││
│  │                                                              ││
│  │  Gemini Live API (voice AI)                                  ││
│  │  Twilio WebSocket (phone)                                    ││
│  │  Google Calendar API (OAuth2)                                ││
│  │  Resend (email notifications)                                ││
│  │  GCS (transcript storage)                                    ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  Browser (mic/speaker)  ─── WebSocket ───▶  /ws/web              │
│  Twilio (phone)         ─── WebSocket ───▶  /ws/twilio           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agent | Python 3.12, LangGraph, LangChain, Google Gemini 2.5 Flash Live API |
| Backend | FastAPI, WebSockets |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Zustand |
| Telephony | Twilio Media Streams |
| Calendar | Google Calendar API (OAuth2) |
| Email | Resend |
| Vehicle Data | RDW Open Data API |
| Storage | Google Cloud Storage (transcripts) |
| Deployment | Google Cloud Run, Docker |

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — set GOOGLE_API_KEY at minimum

# 2. Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Frontend dependencies
cd garage-ai-command-center
pnpm install
cd ..

# 4. Start everything
./start_all.sh
```

This starts:
- **Backend**: FastAPI on `http://localhost:8000` ([API docs](http://localhost:8000/docs))
- **Frontend**: Next.js on `http://localhost:3000`

## Commands

### Start

```bash
# Start everything (backend + frontend)
./start_all.sh

# Backend only
python -m uvicorn bridge.api:app --port 8000 --reload

# Frontend only (from repo root)
cd garage-ai-command-center && pnpm dev
```

### Stop / Kill Processes

```bash
# Stop everything started by start_all.sh
# Press Ctrl+C in the terminal running start_all.sh

# Kill processes on specific ports
lsof -i :8000 -t | xargs kill -9   # Kill backend (port 8000)
lsof -i :3000 -t | xargs kill -9   # Kill frontend (port 3000)

# Kill both at once
lsof -i :8000,:3000 -t | xargs kill -9

# See what's running on a port
lsof -i :8000
lsof -i :3000
```

### Build & Deploy

```bash
# Build frontend for production
cd garage-ai-command-center && pnpm build

# Build Docker image locally
docker build -t torxflow .

# Deploy to Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/garageai-bridge
gcloud run deploy garageai-bridge \
  --image gcr.io/PROJECT_ID/garageai-bridge \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --timeout 300 \
  --session-affinity \
  --set-env-vars "GOOGLE_API_KEY=xxx,TRANSCRIPT_BUCKET=torxflow-transcripts"
```

> `--session-affinity` is required for WebSocket connections.

### Useful Dev Commands

```bash
# Check backend logs
tail -f server.log

# Check frontend logs
tail -f frontend.log

# Install a new Python package
pip install <package> && pip freeze | grep <package> >> requirements.txt

# Install a new frontend package
cd garage-ai-command-center && pnpm add <package>
```

## Google Calendar Setup (OAuth2)

The dashboard uses OAuth2 so each client can connect their own Google Calendar with one click — no service account sharing needed.

### 1. Create OAuth Credentials in Google Cloud Console

1. Go to [APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. Choose **External** user type → Create
3. Add scope: `https://www.googleapis.com/auth/calendar.events`
4. Add the client's Google email to **Test Users** (required until app is verified)
5. Go to [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
6. **Create Credentials → OAuth client ID → Web application**
7. Add **Authorized redirect URIs**:
   - Local: `http://localhost:8000/api/calendar/callback`
   - Production: `https://your-domain.run.app/api/calendar/callback`
8. Copy the **Client ID** and **Client Secret**

### 2. Configure Environment

Add to `.env`:

```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-your-secret
GOOGLE_CALENDAR_ID=primary    # or a specific calendar ID
```

### 3. Connect from the Dashboard

1. Start the app (`./start_all.sh`)
2. Open `http://localhost:3000`
3. Click **Connect Calendar** in the top nav bar
4. Sign in with Google and grant calendar access
5. You'll be redirected back — the nav shows a green **Calendar** pill when connected

Tokens are stored locally in `google_calendar_tokens.json` (auto-excluded from git and Docker).

To disconnect: click the **X** on the green Calendar pill in the nav bar.

## Project Structure

```
torxflow/
├── app/                        # AI agent logic
│   ├── graph.py                # LangGraph state machine + Harry system prompt
│   └── tools.py                # 6 tools (RDW, appointments, cars, web search)
│
├── bridge/                     # FastAPI interface layer
│   ├── api.py                  # REST endpoints + CORS + static file serving
│   ├── telephony.py            # WebSocket handlers (Twilio + Web) + Gemini Live
│   ├── audio.py                # Audio codec conversion (µ-law ↔ PCM)
│   ├── calendar.py             # Google Calendar integration
│   ├── calendar_auth.py        # OAuth2 token storage + flow helpers
│   ├── email.py                # Resend email notifications
│   ├── state.py                # Persistent custom instructions
│   └── transcripts.py          # Transcript storage (GCS or local filesystem)
│
├── garage-ai-command-center/   # Next.js dashboard
│   ├── app/
│   │   ├── layout.tsx          # Root layout (Inter + JetBrains Mono)
│   │   ├── page.tsx            # Command Center (single route)
│   │   ├── history/            # Transcript history page
│   │   ├── calendar/           # Calendar management page
│   │   └── globals.css         # Light theme tokens
│   ├── components/
│   │   ├── nav.tsx             # Top nav (calendar connect, Talk to Harry)
│   │   └── command-center/     # Panel components
│   ├── lib/
│   │   ├── store.ts            # Zustand store (WebSocket, audio, calendar, takeover)
│   │   ├── audio-engine.ts     # Browser audio capture + playback
│   │   └── utils.ts            # Tailwind cn() helper
│   ├── cloudbuild.yaml         # Cloud Build config
│   └── next.config.mjs         # API proxy (dev) + standalone output (prod)
│
├── Dockerfile                  # Backend: Python + static frontend
├── requirements.txt            # Python dependencies
├── start_all.sh                # Launch backend + frontend locally
└── .env                        # Environment variables (not committed)
```

## What Harry Can Do

| Capability | How |
|---|---|
| Vehicle lookup | RDW open data API (Dutch vehicle registry) |
| Check APK status | MOT expiry date + days remaining with urgency levels |
| Vehicle recalls | Active recall notices from RDW |
| Request appointments | Creates proposal for owner review (min 3 weeks out) |
| Search used cars | Scrapes dealer website inventory in real-time |
| Web search | DuckDuckGo for general automotive questions |

### Appointment Flow

1. Harry collects: name, phone, email, kenteken (optional), date/time, description
2. `request_appointment` tool validates date (≥3 weeks) and creates a proposal
3. Owner receives email notification (via Resend)
4. Harry tells customer: "We sturen u een bevestigingsmail zodra de afspraak is bevestigd"
5. Call ends naturally — no waiting for owner approval
6. Owner reviews proposal in Action Queue panel → clicks Accept
7. Google Calendar event created + confirmation email sent to customer

### Live Call Monitoring

The dashboard auto-connects in **monitor mode** on page load, streaming all Twilio call data live:

1. Phone call arrives → Harry answers immediately and greets the caller
2. All transcripts, tool calls, vehicle data, and sentiment stream to the dashboard in real time
3. During any active call, owner can click **Take Over** to intervene

### Takeover Mode

The garage owner can take over a live Twilio call:

1. Click **Take Over** in the nav bar during an active call
2. Harry goes silent (Gemini suppressed), owner speaks directly to the customer
3. Owner's mic audio is resampled (16kHz PCM → 8kHz µ-law) and forwarded to Twilio
4. Click **Return to Harry** to hand the conversation back

## Twilio Phone Integration

Optional — the web dashboard mic works without Twilio.

1. Configure your Twilio phone number's **Voice** webhook to:
   `https://garageai-bridge-xxx-ew.a.run.app/twilio/voice`

2. Add env vars:
```bash
gcloud run services update garageai-bridge \
  --region europe-west4 \
  --update-env-vars "TWILIO_ACCOUNT_SID=xxx,TWILIO_AUTH_TOKEN=xxx"
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `GOOGLE_OAUTH_CLIENT_ID` | For calendar | Google OAuth2 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | For calendar | Google OAuth2 client secret |
| `GOOGLE_CALENDAR_ID` | For calendar | Calendar ID (default: `primary`) |
| `RESEND_API_KEY` | For email | Resend API key (`re_xxx`) |
| `FROM_EMAIL` | For email | Sender address (default: `harry@torxflow.nl`) |
| `GARAGE_OWNER_EMAIL` | For email | Owner notification email |
| `GARAGE_NAME` | No | Display name (default: `Garage Wiefferink`) |
| `GARAGE_ADDRESS` | No | Physical address for confirmation emails |
| `GARAGE_PHONE` | No | Phone number for confirmation emails |
| `TRANSCRIPT_BUCKET` | Prod | GCS bucket for transcript storage (falls back to local filesystem) |
| `CORS_ORIGIN` | Prod | Dashboard URL for CORS |
| `TWILIO_ACCOUNT_SID` | No | Twilio SID (phone integration) |
| `TWILIO_AUTH_TOKEN` | No | Twilio auth token |
| `NEXT_PUBLIC_BRIDGE_URL` | Build time | Backend URL (Next.js build-time variable) |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/rdw-lookup/{kenteken}` | Structured RDW vehicle data |
| `GET` | `/api/calendar/status` | Check if Google Calendar is connected |
| `GET` | `/api/calendar/auth` | Redirect to Google OAuth consent screen |
| `GET` | `/api/calendar/callback` | OAuth callback (exchanges code for tokens) |
| `POST` | `/api/calendar/disconnect` | Remove stored OAuth tokens |
| `GET` | `/api/calendar/events?days=30` | List upcoming Google Calendar events |
| `POST` | `/api/appointment/accept` | Accept proposal → create calendar event + send email |
| `GET` | `/api/custom-instructions` | Get current custom instructions |
| `POST` | `/api/custom-instructions` | Save custom instructions |
| `GET` | `/api/transcripts` | List saved transcripts |
| `GET` | `/api/transcripts/{id}` | Get full transcript |
| `WS` | `/ws/twilio` | Twilio Media Stream WebSocket |
| `WS` | `/ws/web` | Web dashboard WebSocket (talk mode) |
| `WS` | `/ws/web?mode=monitor` | Dashboard monitor WebSocket (live call broadcast) |

## Audio Pipeline

```
Phone caller  →  8kHz µ-law  →  16kHz PCM  →  Gemini Live API
Gemini        →  24kHz PCM   →  8kHz µ-law  →  Phone caller

Browser       →  16kHz PCM   →  Gemini Live API
Gemini        →  24kHz PCM   →  Browser

Takeover      →  16kHz PCM   →  8kHz µ-law  →  Phone caller (bypasses Gemini)
```

Target latency: **< 800ms** end-to-end (200ms network + 400ms Gemini + 200ms code).

## Troubleshooting

| Issue | Fix |
|---|---|
| OFFLINE in dashboard | Check backend is running, verify CORS_ORIGIN env var |
| No audio playback | Click anywhere on the page first (browser autoplay policy) |
| WebSocket drops | Cloud Run idle timeout; `--timeout 300` helps |
| Browser blocks mic | Ensure HTTPS (Cloud Run provides it) or localhost |
| Calendar "not connected" | Click Connect Calendar in nav; check OAuth client ID/secret in `.env` |
| Calendar OAuth error | Verify redirect URI matches in Google Cloud Console |
| Emails not sending | Verify RESEND_API_KEY and FROM_EMAIL domain is verified in Resend |
| Port already in use | `lsof -i :8000 -t \| xargs kill -9` (or `:3000` for frontend) |

## Cost Estimate (Pilot)

| Service | Free Tier | Expected Cost |
|---|---|---|
| Cloud Run | 2M requests/month free | ~$0 for pilot |
| Cloud Build | 120 min/day free | ~$0 |
| Gemini API | Free tier available | ~$5-10/month |
| Google Calendar API | Free | $0 |
| Google Cloud Storage | 5 GB free | ~$0 |
| Resend | 100 emails/day free | $0 |
| Twilio | Pay-as-you-go | ~$1/mo + ~$0.02/min |
