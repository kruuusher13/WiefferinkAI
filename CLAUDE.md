# CLAUDE.md - GarageAI Project Guide

## Project Overview

**GarageAI** is a voice-enabled customer service assistant for Dutch automotive garages (Garage Wiefferink). Harry, the AI receptionist, handles real-time phone conversations via Twilio with <800ms latency.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph, LangChain |
| AI | Google Gemini 2.0 Flash, Gemini Live API |
| Database | SQL Server (Azure SQL Edge), pyodbc |
| Telephony | Twilio, WebSockets |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |

## Project Structure

```
GarageAI/
├── app/                    # Core agent logic (LangGraph)
│   ├── graph.py            # State machine + Harry system prompt
│   ├── tools.py            # 10 tools (WinCar, RDW, web search)
│   ├── init_db.py          # Database initialization
│   └── mock_wincar_db.sql  # SQL seed data
│
├── bridge/                 # Interface layer
│   ├── api.py              # FastAPI app + CORS + DB endpoints
│   ├── telephony.py        # WebSocket handlers (Twilio + Web), Gemini Live
│   └── audio.py            # Audio codec conversion (mu-law ↔ PCM)
│
├── garage-ai-command-center/   # Next.js dashboard (port 3000)
│   ├── components/command-center/  # Live Stream, Vehicle Context, Action Queue
│   └── next.config.mjs     # Proxies /api/* → localhost:8000
│
├── _bmad/                  # BMAD workflow system
│   ├── core/               # Config + master agent
│   └── garage/             # Agents, workflows, templates
│
├── tests/                  # Pytest suite
├── deployment/             # Docker + Cloud Run configs
├── docker-compose.yml      # SQL Server (wincar_sql container)
└── start_all.sh            # Start backend + frontend in one command
```

## Common Commands

```bash
./start_all.sh                                       # Start everything
python -m uvicorn bridge.api:app --port 8000 --reload  # Backend only
cd garage-ai-command-center && pnpm dev              # Frontend only (port 3000)
pytest tests/                                        # Run tests
docker-compose up -d                                 # DB only
```

## Code Patterns

### Adding a New Tool (app/tools.py)

```python
class NewToolInput(BaseModel):
    param: str = Field(description="Description for AI")

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

Then add the function to the tools list in `app/graph.py`.

### Adding a New API Endpoint (bridge/api.py)

```python
@app.get("/api/new_endpoint/{param}")
async def new_endpoint(param: str):
    try:
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Important Constraints

1. **Latency Budget**: 800ms total (200ms network + 400ms Gemini + 200ms code)
2. **Audio Formats**: Twilio 8kHz µ-law · Gemini input 16kHz PCM · Gemini output 24kHz PCM
3. **Language**: Code comments English · Customer-facing responses Dutch · Docs English
4. **Database Safety**: Read ops safe · Write ops need review · Always close connections in `finally`

## Key Files

| File | Purpose |
|---|---|
| `app/graph.py` | LangGraph agent + system prompt |
| `app/tools.py` | All database and API tools |
| `bridge/telephony.py` | WebSocket handlers + Gemini Live integration |
| `bridge/audio.py` | Audio codec conversion |
| `garage-ai-command-center/components/command-center/` | Dashboard UI panels |

## BMAD Workflow System

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

- Agents: `_bmad/garage/agents/*.md`
- Workflows: `_bmad/garage/workflows/`
- Config: `_bmad/core/config.yaml`

## Current Focus

- **Next milestone**: User Acceptance Testing (UAT) + Latency Optimization
- **Dashboard**: Command Center (Next.js) connected at http://localhost:3000
