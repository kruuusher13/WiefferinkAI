# GarageAI

Voice-enabled customer service assistant for Dutch automotive garages. Harry, the AI receptionist, handles inbound calls — looking up vehicle status, booking appointments, and checking parts inventory — in real-time Dutch conversation via phone.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph |
| AI | Google Gemini 2.0 Flash (Live API) |
| Telephony | Twilio, WebSockets |
| Database | SQL Server (Azure SQL Edge via Docker) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 20+, pnpm, Docker Desktop, ODBC Driver 17 for SQL Server

```bash
cp .env.example .env        # set GOOGLE_API_KEY
./start_all.sh
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

For Twilio phone calls, expose the backend:
```bash
ngrok http 8000
```

---

## Project Structure

```
GarageAI/
├── app/
│   ├── graph.py            # LangGraph agent + Harry system prompt
│   ├── tools.py            # 10 tools (WinCar, RDW, web search)
│   ├── init_db.py          # Database init on startup
│   └── mock_wincar_db.sql  # SQL seed data
│
├── bridge/
│   ├── api.py              # FastAPI app, REST endpoints, CORS
│   ├── telephony.py        # WebSocket handlers (Twilio + Web), Gemini Live
│   └── audio.py            # Audio conversion (mu-law ↔ PCM, resampling)
│
├── garage-ai-command-center/   # Next.js dashboard
│   ├── app/                    # App router
│   ├── components/command-center/  # Live Stream, Vehicle Context, Action Queue
│   └── next.config.mjs         # API proxy → :8000
│
├── _bmad/                  # BMAD workflow system (agents, workflows, templates)
├── tests/                  # Pytest suite
├── deployment/             # Docker + Cloud Run configs
├── docker-compose.yml      # SQL Server container
├── requirements.txt        # Python deps
└── start_all.sh            # One-command full-stack startup
```

---

## Backend

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/api/db/{table}` | DB table data for dashboard |
| GET | `/api/rdw-lookup/{kenteken}` | RDW vehicle lookup |
| POST | `/api/werkorder` | Create work order from dashboard |
| WS | `/ws/web` | Browser WebSocket (PCM 16k/24k) |
| WS | `/ws/twilio` | Twilio media stream (mu-law 8k) |

Valid `{table}` values: `customers`, `vehicles`, `werkorders`, `lines`, `stock`, `categories`, `services`, `rates`, `invoices`

### Tools

| Tool | Source | Purpose |
|---|---|---|
| `identify_customer` | WinCar | Customer lookup by phone |
| `check_werkorder_status` | WinCar | Work order status by licence plate |
| `check_part_stock` | WinCar | Parts availability and price |
| `schedule_appointment` | WinCar | Book service appointment |
| `generate_payment_link` | WinCar | Create Mollie payment link |
| `get_service_price` | WinCar | Labour rates and service costs |
| `lookup_vehicle_rdw` | RDW | Vehicle specs by licence plate |
| `check_apk_status` | RDW | MOT expiry date |
| `get_vehicle_recalls` | RDW | Active vehicle recalls |
| `web_search` | DuckDuckGo | General web search |

### Audio Pipeline

```
Twilio  →  8 kHz µ-law  →  16 kHz PCM  →  Gemini Live
Gemini  →  24 kHz PCM   →  8 kHz µ-law  →  Twilio
Browser →  16 kHz PCM   →  Gemini Live
Gemini  →  24 kHz PCM   →  Browser
```

Latency budget: **< 800ms** (200ms network + 400ms Gemini + 200ms code)

---

## Database Schema

`WinCarLive` SQL Server database (auto-seeded on startup):

| Table | Module | Contents |
|---|---|---|
| `Communicatie_Relaties` | CRM | Customers |
| `Werkplaats_Voertuigen` | Workshop | Vehicles |
| `Werkplaats_Werkorders` | Workshop | Work orders |
| `Werkplaats_WerkorderRegels` | Workshop | Work order line items |
| `Magazijn_Artikelen` | Inventory | Parts stock |
| `Magazijn_Categorieen` | Inventory | Part categories |
| `Diensten_Services` | Services | Service definitions |
| `Diensten_Tarieven` | Services | Labour rates |
| `Financieel_Facturen` | Financial | Invoices |

---

## Frontend

Next.js dashboard (`garage-ai-command-center/`) with three panels:

- **Live Stream** — real-time call transcript with keyword highlighting and audio waveform
- **Vehicle Context** — RDW vehicle intelligence (specs, MOT, recalls)
- **Action Queue** — Kanban board for AI-generated tasks pending human approval

API calls proxy to the FastAPI backend via `next.config.mjs`. WebSocket connects directly to `ws://localhost:8000`.

```bash
cd garage-ai-command-center
pnpm install && pnpm dev   # dev on :3000
pnpm build                 # production build
```

---

## Development

### Running tests

```bash
pytest tests/
```

### Backend only

```bash
python -m uvicorn bridge.api:app --port 8000 --reload
```

### Adding a tool

```python
# app/tools.py
class NewToolInput(BaseModel):
    param: str = Field(description="Description for the AI")

@tool("tool_name", args_schema=NewToolInput)
def tool_name(param: str) -> str:
    """WinCar Module: [MODULE] - What this tool does."""
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ...", param)
        row = cursor.fetchone()
        return f"Result: {row.Column}" if row else "Niet gevonden."
    finally:
        conn.close()
```

Then add it to the tools list in `app/graph.py`.

### Conventions

- Code comments: English
- Customer-facing responses: Dutch
- Type hints on all functions
- DB connections always closed in `finally` blocks

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `TWILIO_ACCOUNT_SID` | Phone only | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Phone only | Twilio auth token |

---

## BMAD Workflow System

BMAD is the multi-agent development system built into this project. Use Claude CLI commands:

| Command | Agent | Role |
|---|---|---|
| `/bmad` | Master | Menu + orchestration |
| `/bmad-pm` | Jan | Requirements, PRDs |
| `/bmad-architect` | Willem | System design |
| `/bmad-dev` | Sophie | Implementation |
| `/bmad-voice` | Harry | Telephony, audio |
| `/bmad-db` | Pieter | SQL, WinCar schema |
| `/bmad-quick` | Barry | Fast-track dev |
| `/bmad-test` | Tessa | QA, test plans |
| `/bmad-feature` | — | Full feature workflow |
| `/bmad-bugfix` | — | Bug investigation |
| `/bmad-review` | — | Code review |
| `/bmad-release` | — | Release prep |

Agent definitions: `_bmad/garage/agents/` | Workflows: `_bmad/garage/workflows/`

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'app.graph'`**
Set `PYTHONPATH` to the project root, or add it to `.env`.

**Connection refused on WebSocket**
Verify the server is running: `curl http://localhost:8000/`

**Gemini API key error**
Check `.env` has `GOOGLE_API_KEY=...` and restart the server.

**Pydantic validation error**
Ensure Pydantic v2: `pip install --upgrade "pydantic>=2.0" pydantic-settings`
