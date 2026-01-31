# CLAUDE.md - GarageAI Project Guide

This file helps Claude Code understand the GarageAI project and work effectively with it.

## Project Overview

**GarageAI v2.0** is a voice-enabled customer service assistant for Dutch automotive garages (Garage Wiefferink). It enables real-time voice conversations with customers about appointments, vehicle status, and parts.

### Key Features
- Voice AI assistant ("Harry" persona)
- Real-time phone conversations via Twilio (<800ms latency)
- WinCar DMS database integration
- Web dashboard for testing and monitoring

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, LangGraph, LangChain |
| AI | Google Gemini 2.0 Flash, Gemini Live API |
| Database | SQL Server (Azure SQL Edge), pyodbc |
| Telephony | Twilio, WebSockets |
| Frontend | HTML/CSS/JavaScript, WebAudio API |

## Project Structure

```
GarageAI/
├── app/                    # Core Agent Logic (LangGraph)
│   ├── graph.py           # LangGraph state machine + system prompt
│   ├── tools.py           # WinCar database tools (6 tools)
│   ├── init_db.py         # Database initialization
│   └── mock_wincar_db.sql # SQL seed data
│
├── bridge/                 # Interface Layer
│   ├── api.py             # FastAPI main app + endpoints
│   ├── telephony.py       # WebSocket handlers (Twilio + Web)
│   └── audio.py           # Audio resampling (8kHz/16kHz/24kHz)
│
├── web_test/               # Browser Dashboard
│   ├── index.html         # Premium UI
│   └── static/client.js   # WebSocket + audio client
│
├── docs/                   # Documentation
├── deployment/             # Docker + Cloud Run configs
├── tests/                  # Test files
│
├── _bmad/                  # BMAD Workflow System
│   ├── core/              # Core BMAD (config, master agent)
│   ├── garage/            # GarageAI-specific agents & workflows
│   └── _config/           # Manifests and agent registry
│
└── .agent/workflows/       # Claude Code slash commands
```

## Common Commands

```bash
# Run the server
python -m uvicorn bridge.api:app --port 8000 --reload

# Run tests
pytest tests/

# Start Docker services (SQL Server)
docker-compose up -d

# Open dashboard
open http://localhost:8000/web/index.html
```

## Code Patterns

### Adding a New Tool (app/tools.py)

```python
class NewToolInput(BaseModel):
    param: str = Field(description="Description for AI")

@tool("tool_name", args_schema=NewToolInput)
def tool_name(param: str) -> str:
    """
    WinCar Module: [MODULE_NAME]
    Description - AI reads this to know when to use the tool.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ...", param)
        row = cursor.fetchone()
        if row:
            return f"Result: {row.Column}"
        return "Niet gevonden."  # Dutch for customer-facing
    finally:
        conn.close()
```

### Adding a New API Endpoint (bridge/api.py)

```python
@app.get("/api/new_endpoint/{param}")
async def new_endpoint(param: str):
    """Endpoint description."""
    try:
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Important Constraints

1. **Latency Budget**: 800ms total
   - ~200ms network
   - ~400ms Gemini
   - ~200ms our code

2. **Audio Formats**:
   - Twilio: 8kHz µ-law
   - Gemini input: 16kHz PCM
   - Gemini output: 24kHz PCM

3. **Language**:
   - Code comments: English
   - User-facing AI responses: Dutch
   - Documentation: English

4. **Database Safety**:
   - Read operations are safe
   - Write operations need careful review
   - Always close connections in `finally` blocks

---

## BMAD Workflow System

GarageAI uses **BMAD (Break Me And Deploy)** - a multi-agent workflow system with specialized AI personas.

### Quick Start

Use these slash commands:

| Command | Description |
|---------|-------------|
| `/bmad` | Start BMAD Master (main menu) |
| `/bmad-help` | Get guidance on what to use |
| `/bmad-pm` | Jan - Product Manager (requirements) |
| `/bmad-architect` | Willem - System Architect (design) |
| `/bmad-dev` | Sophie - Developer (implementation) |
| `/bmad-voice` | Harry - Voice Specialist (audio/Twilio) |
| `/bmad-db` | Pieter - Database Expert (SQL/WinCar) |
| `/bmad-quick` | Barry - Quick Dev (fast-track) |
| `/bmad-test` | Tessa - Testing Agent (QA/testing) |
| `/bmad-feature` | Full feature workflow |
| `/bmad-bugfix` | Bug fix workflow |
| `/bmad-review` | Code review workflow |
| `/bmad-release` | Release/deploy workflow |

### When to Use BMAD

| Scenario | Approach |
|----------|----------|
| New feature idea | `/bmad-pm` → `/bmad-architect` → `/bmad-dev` |
| Quick feature addition | `/bmad-quick` |
| Bug fix | `/bmad-bugfix` |
| Code review | `/bmad-review` |
| Architecture question | `/bmad-architect` |
| Database question | `/bmad-db` |
| Audio/telephony issue | `/bmad-voice` |
| Testing/QA | `/bmad-test` |
| Ready to deploy | `/bmad-release` |

### BMAD File Locations

- Config: `_bmad/core/config.yaml`
- Agents: `_bmad/garage/agents/*.md`
- Workflows: `_bmad/garage/workflows/*/workflow.md`
- Templates: `_bmad/garage/templates/*.md`
- Output: `_bmad/_output/` (generated documents)

---

## Tips for Working with This Codebase

1. **Follow existing patterns** - Look at how similar features are implemented
2. **Type hints everywhere** - All functions should have type annotations
3. **Dutch for users** - Customer-facing text must be in Dutch
4. **Test the voice path** - Changes might affect latency
5. **Check both Twilio and Web** - Test on both paths when relevant
6. **Use BMAD agents** - They know the codebase patterns

## Key Files to Know

| File | Purpose |
|------|---------|
| `app/graph.py` | LangGraph agent + system prompt |
| `app/tools.py` | All database tools |
| `bridge/telephony.py` | WebSocket handlers |
| `bridge/audio.py` | Audio codec conversion |
| `web_test/static/client.js` | Browser audio client |

## Current Focus

[Update this section as you work on features]

- Active feature: None
- Known issues: None
- Next milestone: None
