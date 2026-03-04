# CLAUDE.md - TorxFlow

## Overview

Voice-enabled AI receptionist (Harry) for Dutch automotive garages. Real-time phone + web conversations via Gemini Live API with <800ms latency.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph, LangChain |
| AI | Google Gemini 2.5 Flash Live API |
| Calendar | Google Calendar API (service account) |
| Email | Resend |
| Vehicle Data | RDW Open Data API |
| Telephony | Twilio Media Streams, WebSockets |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Zustand |
| Deployment | Google Cloud Run, Docker |

## Structure

```
app/graph.py          # LangGraph state machine + Harry system prompt
app/tools.py          # 6 tools (RDW, appointments, cars, web search)
bridge/api.py         # FastAPI REST endpoints + CORS
bridge/telephony.py   # WebSocket handlers (Twilio + Web) + Gemini Live + takeover
bridge/audio.py       # Audio codec conversion (µ-law ↔ PCM)
bridge/calendar.py    # Google Calendar integration
bridge/email.py       # Resend email notifications
bridge/state.py       # Persistent custom instructions
bridge/transcripts.py # Transcript storage (GCS or local fallback)
garage-ai-command-center/
  app/page.tsx        # Single route: Command Center
  components/command-center/  # 8 panel components
  lib/store.ts        # Zustand store (WebSocket, audio, takeover)
  lib/audio-engine.ts # Browser audio capture + playback
```

## Commands

```bash
./start_all.sh                                        # Start everything
python -m uvicorn bridge.api:app --port 8000 --reload  # Backend only
cd garage-ai-command-center && pnpm dev                # Frontend only
```

## Code Patterns

### New Tool (app/tools.py)

```python
class NewToolInput(BaseModel):
    param: str = Field(description="Description for AI")

@tool("tool_name", args_schema=NewToolInput)
def tool_name(param: str) -> str:
    """What this tool does."""
    # implementation
    return "Result"
```

Then add to the tools list in `app/graph.py` and add to `TOOLS_SCHEMA` + `_execute_tool()` in `bridge/telephony.py`.

### New API Endpoint (bridge/api.py)

```python
@app.get("/api/new_endpoint/{param}")
async def new_endpoint(param: str):
    try:
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Changelog

### 2026-03-04
- **Dashboard live monitoring**: Dashboard auto-connects in monitor mode on page load. All Twilio call data (transcripts, tool calls, vehicle data, sentiment) streams to the dashboard in real time.
- **Takeover from dashboard**: Owner can take over a live Twilio call from the dashboard (Take Over / Return to Harry).
- **Harry answers immediately**: Removed 15s ringing window — Harry picks up Twilio calls instantly with a greeting.
- **Async tool execution**: Tools run in `asyncio.to_thread()` to prevent blocking the WebSocket event loop (fixes call drops during tool use like `search_available_cars`).
- **Greeting trigger for Twilio**: Added explicit greeting trigger so Harry greets callers immediately instead of waiting for audio input.

## Constraints

1. **Latency**: 800ms total (200ms network + 400ms Gemini + 200ms code)
2. **Audio**: Twilio 8kHz µ-law · Gemini input 16kHz PCM · Gemini output 24kHz PCM
3. **Language**: Code/docs English · Customer-facing responses Dutch
4. **Appointments**: Minimum 3 weeks out · Creates proposals (not confirmed) · Owner accepts from dashboard
